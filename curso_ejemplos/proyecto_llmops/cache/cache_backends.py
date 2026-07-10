"""
cache_backends.py · Dónde se guarda el caché (y por qué eso es una interfaz)
=============================================================================
FINALIDAD:
  Separar QUÉ se cachea (semantic_cache.py) de DÓNDE se guarda (este archivo).
  El caché semántico no sabe si detrás hay una lista de Python o un Redis; solo
  sabe pedir "dame las entradas" y "guarda esta".

  ⭐ Esa frontera es lo que permite que los tests corran sin Docker. El backend
     in-memory NO es un juguete: es el mismo contrato, con otra implementación.

LÓGICA:
  - EntradaCache : (pregunta, respuesta, vector, rol). Inmutable.
  - CacheBackend : el contrato (Protocol). Tres métodos y nada más.
  - InMemoryCache: una lista. Muere con el proceso. Perfecta para tests.
  - RedisCache   : persistente y compartida entre workers. La de producción.

⚠️ SOBRE RedisCache Y LA BÚSQUEDA LINEAL. Este backend trae TODAS las entradas y
   compara vector a vector en el cliente. Con 500 preguntas cacheadas va sobrado;
   con 500.000 es un desastre — cada MISS recorrería medio millón de vectores.
   Lo correcto a esa escala es un índice vectorial dentro de Redis (RediSearch,
   HNSW) o directamente pgvector. Se hace así aquí porque el objetivo es enseñar
   el mecanismo del caché semántico, no la estructura de datos que lo indexa.
   Un curso que esconde ese límite forma gente que lo descubre en producción.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class EntradaCache:
    """Una pregunta ya respondida, con su vector y el rol que la hizo.

    ⚠️ El `rol` NO es un adorno. Ver el aviso de seguridad en semantic_cache.py:
       un caché sin rol le sirve a un 'analyst' la respuesta que se generó para
       un 'compliance', con el material restringido dentro. El RBAC se salta por
       la puerta de atrás.
    """
    pregunta: str
    respuesta: str
    vector: tuple[float, ...]
    rol: str = "analyst"

    def a_json(self) -> str:
        """Para persistir en Redis, que solo guarda bytes y strings."""
        return json.dumps({
            "pregunta": self.pregunta,
            "respuesta": self.respuesta,
            "vector": list(self.vector),
            "rol": self.rol,
        })

    @classmethod
    def de_json(cls, crudo: str | bytes) -> "EntradaCache":
        datos = json.loads(crudo)
        return cls(
            pregunta=datos["pregunta"],
            respuesta=datos["respuesta"],
            vector=tuple(datos["vector"]),
            rol=datos.get("rol", "analyst"),
        )


class CacheBackend(Protocol):
    """El contrato. Tres métodos: leer todo, añadir una, vaciar.

    Un Protocol de Python es "tipado estructural": cualquier clase con estos
    métodos vale, sin heredar de nada. Es la versión mínima de la inyección de
    dependencias — el caché depende de la FORMA, no de la clase.
    """

    def entradas(self, rol: str) -> Iterable[EntradaCache]: ...
    def guardar(self, entrada: EntradaCache) -> None: ...
    def limpiar(self) -> None: ...


class InMemoryCache:
    """Una lista en memoria. Muere con el proceso.

    Es el backend de los tests y el fallback cuando Redis no responde. Con
    varios workers de uvicorn cada uno tendría el suyo: no comparten nada, y la
    tasa de aciertos se divide entre el número de procesos. Ese es exactamente
    el motivo por el que producción usa Redis.
    """

    def __init__(self, maximo: int = 1000):
        self._entradas: list[EntradaCache] = []
        # Sin tope, un caché es una fuga de memoria con buena prensa.
        self.maximo = maximo

    def entradas(self, rol: str) -> Iterable[EntradaCache]:
        # El filtro por rol se aplica AQUÍ, en el backend: así ninguna capa de
        # arriba puede olvidarse de aplicarlo.
        return [e for e in self._entradas if e.rol == rol]

    def guardar(self, entrada: EntradaCache) -> None:
        self._entradas.append(entrada)
        if len(self._entradas) > self.maximo:
            # Política FIFO: se va la más antigua. Un LRU sería mejor, pero
            # exige contar accesos y aquí no aporta a lo que se enseña.
            self._entradas.pop(0)

    def limpiar(self) -> None:
        self._entradas.clear()


class RedisCache:
    """Backend persistente y COMPARTIDO entre workers. El de producción.

    Guarda una lista por rol (`gobdata:cache:<rol>`). Que las claves estén
    separadas por rol no es solo orden: es el aislamiento del RBAC hecho de
    infraestructura, no de un `if` que alguien puede borrar.

    Levantar Redis:  docker compose -f proyecto_llmops/docker-compose.yml up -d redis
    """

    def __init__(self, cliente=None, prefijo: str = "gobdata:cache", ttl_segundos: int = 86_400):
        # El cliente entra por parámetro (inyección) para poder pasarle un doble
        # en los tests. Si no lo dan, lo construimos del .env.
        if cliente is None:
            cliente = self._cliente_por_defecto()
        self.cliente = cliente
        self.prefijo = prefijo
        # ⭐ El TTL no es opcional. La normativa cambia; una respuesta cacheada
        #    para siempre es una respuesta obsoleta servida con confianza.
        self.ttl_segundos = ttl_segundos

    @staticmethod
    def _cliente_por_defecto():
        import redis  # import diferido: solo lo paga quien usa Redis
        from app.config import settings
        return redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )

    def _clave(self, rol: str) -> str:
        return f"{self.prefijo}:{rol}"

    def entradas(self, rol: str) -> Iterable[EntradaCache]:
        crudas = self.cliente.lrange(self._clave(rol), 0, -1)
        return [EntradaCache.de_json(c) for c in crudas]

    def guardar(self, entrada: EntradaCache) -> None:
        clave = self._clave(entrada.rol)
        self.cliente.rpush(clave, entrada.a_json())
        # El TTL se renueva con cada escritura: un caché activo no expira,
        # uno abandonado sí.
        self.cliente.expire(clave, self.ttl_segundos)

    def limpiar(self) -> None:
        for clave in self.cliente.scan_iter(f"{self.prefijo}:*"):
            self.cliente.delete(clave)


def crear_backend() -> CacheBackend:
    """Redis si responde; memoria si no. Degradación graceful.

    ⭐ Un caché caído debe degradar el COSTE, nunca la CORRECCIÓN. Si Redis no
       está, el servicio responde igual: más caro y más lento, pero responde.
       Por eso este `except` no es pereza — es la política.
    """
    try:
        backend = RedisCache()
        backend.cliente.ping()      # ¿de verdad hay alguien al otro lado?
        return backend
    except Exception:               # pragma: no cover - depende del entorno
        # Ni redis instalado, ni contenedor levantado, ni red. Da igual cuál:
        # la respuesta es la misma.
        return InMemoryCache()
