"""
cache_backends.py · Dónde se guarda el caché (y por qué eso es una interfaz)
=============================================================================
FINALIDAD:
  Separar QUÉ se cachea (semantic_cache.py) de DÓNDE se guarda (este archivo). El
  caché no sabe si detrás hay una lista de Python o un Redis; solo pide "dame las
  entradas" y "guarda esta".

  ⭐ Esa frontera es lo que permite que los tests corran sin Docker. El backend
     in-memory NO es un juguete: es el mismo contrato, con otra implementación.

⚠️ RedisCache hace búsqueda LINEAL en el cliente: trae todas las entradas y
   compara vector a vector. Con cientos de preguntas cacheadas va sobrado; a
   escala de cientos de miles habría que indexar dentro de Redis (RediSearch/HNSW)
   o pasar a pgvector. Se hace así para enseñar el mecanismo, no la estructura que
   lo indexa. (Espejo del cache_backends.py de proyecto_llmops, sin el rol: el
   asistente de compras no tiene RBAC — el catálogo es público.)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class EntradaCache:
    """Una pregunta ya respondida, con su vector. Inmutable."""
    pregunta: str
    respuesta: str
    vector: tuple[float, ...]

    def a_json(self) -> str:
        return json.dumps({"pregunta": self.pregunta, "respuesta": self.respuesta,
                           "vector": list(self.vector)})

    @classmethod
    def de_json(cls, crudo: str | bytes) -> "EntradaCache":
        datos = json.loads(crudo)
        return cls(pregunta=datos["pregunta"], respuesta=datos["respuesta"],
                   vector=tuple(datos["vector"]))


class CacheBackend(Protocol):
    """El contrato. Tres métodos: leer todo, añadir una, vaciar."""
    def entradas(self) -> Iterable[EntradaCache]: ...
    def guardar(self, entrada: EntradaCache) -> None: ...
    def limpiar(self) -> None: ...


class InMemoryCache:
    """Una lista en memoria. Muere con el proceso. El backend de los tests y el
    fallback cuando Redis no responde."""

    def __init__(self, maximo: int = 1000):
        self._entradas: list[EntradaCache] = []
        self.maximo = maximo   # sin tope, un caché es una fuga de memoria con buena prensa

    def entradas(self) -> Iterable[EntradaCache]:
        return list(self._entradas)

    def guardar(self, entrada: EntradaCache) -> None:
        self._entradas.append(entrada)
        if len(self._entradas) > self.maximo:
            self._entradas.pop(0)   # FIFO: se va la más antigua

    def limpiar(self) -> None:
        self._entradas.clear()


class RedisCache:
    """Backend persistente y compartido entre workers. El de producción."""

    def __init__(self, cliente=None, clave: str = "retail:cache", ttl_segundos: int = 86_400):
        if cliente is None:
            cliente = self._cliente_por_defecto()
        self.cliente = cliente
        self.clave = clave
        # ⭐ El TTL no es opcional. El catálogo cambia a diario; una respuesta
        #    cacheada para siempre es un precio viejo servido con confianza.
        self.ttl_segundos = ttl_segundos

    @staticmethod
    def _cliente_por_defecto():
        import redis  # import diferido: solo lo paga quien usa Redis
        from proyecto_retail.app.config import settings
        return redis.Redis(host=settings.redis_host, port=settings.redis_port,
                           decode_responses=True)

    def entradas(self) -> Iterable[EntradaCache]:
        return [EntradaCache.de_json(c) for c in self.cliente.lrange(self.clave, 0, -1)]

    def guardar(self, entrada: EntradaCache) -> None:
        self.cliente.rpush(self.clave, entrada.a_json())
        self.cliente.expire(self.clave, self.ttl_segundos)

    def limpiar(self) -> None:
        self.cliente.delete(self.clave)


def crear_backend() -> CacheBackend:
    """Redis si responde; memoria si no. Degradación graceful.

    ⭐ Un caché caído debe degradar el COSTE, nunca la CORRECCIÓN: sin Redis, el
       servicio responde igual, más caro y más lento, pero responde.
    """
    try:
        backend = RedisCache()
        backend.cliente.ping()
        return backend
    except Exception:   # pragma: no cover - depende del entorno
        return InMemoryCache()
