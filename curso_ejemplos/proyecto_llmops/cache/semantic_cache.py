"""
semantic_cache.py · Responder sin llamar al modelo
===================================================
FINALIDAD:
  Un caché normal (dict) acierta solo con la pregunta EXACTA. Pero
  "¿hay que cifrar los datos?" y "¿los datos se cifran?" son la misma pregunta,
  y un dict las trata como dos. El caché **semántico** compara SIGNIFICADOS:
  vectoriza la pregunta y busca una ya respondida que se le parezca lo bastante.

  El ahorro es doble y no simétrico:
    - COSTE: un acierto vale ~$0. La llamada al LLM no ocurre.
    - LATENCIA: milisegundos en vez de segundos. Se nota más que el dinero.

LÓGICA (paso a paso):
  1. Vectorizar la pregunta (embeddings LOCALES: el caché no puede costar más
     que lo que ahorra).
  2. Comparar por **similitud coseno** con las preguntas ya cacheadas del MISMO
     rol.
  3. Si la mejor supera el umbral → HIT: se devuelve su respuesta.
  4. Si no → MISS: el llamador va al modelo y luego llama a `guardar()`.

⚠️⚠️ LOS DOS PELIGROS DE ESTE PATRÓN. Hay que decirlos, porque el caché semántico
   se vende como una optimización inocente y no lo es:

   1) EL FALSO POSITIVO ES UNA RESPUESTA INCORRECTA, NO UNA LENTITUD.
      Si el umbral es bajo, "¿debo cifrar los datos?" y "¿debo cifrar los
      backups?" se parecen mucho — y el usuario recibe, con total aplomo, la
      respuesta a una pregunta que no hizo. Un caché mal calibrado no degrada el
      rendimiento: **degrada la verdad**. Por eso el umbral por defecto es 0.92
      y no 0.80. Ante la duda, un MISS caro es infinitamente mejor que un HIT
      equivocado.

   2) EL CACHÉ ES UN CANAL LATERAL QUE SE SALTA EL RBAC.
      Si un 'compliance' pregunta por las claves maestras y su respuesta se
      cachea sin más, el siguiente 'analyst' que pregunte algo parecido recibe
      material restringido — sin pasar por el retriever, sin pasar por
      `filtrar_por_rol`. Toda la gobernanza, esquivada por una optimización.
      Por eso el rol forma parte de la clave: **cada rol tiene su propio caché**.

⭐ Todo entra por parámetro (embeddings, backend, umbral) → se testea con
   vectores deterministas, sin red, sin Redis y sin cuota.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from cache.cache_backends import CacheBackend, EntradaCache, InMemoryCache


def coseno(a: tuple[float, ...] | list[float], b: tuple[float, ...] | list[float]) -> float:
    """Similitud coseno entre dos vectores: 1.0 = idénticos, 0.0 = ortogonales.

    Mide el ÁNGULO, no la distancia. Dos textos, uno el doble de largo que el
    otro pero del mismo tema, apuntan en la misma dirección aunque sus vectores
    tengan distinta magnitud. Eso es exactamente lo que queremos.

    FUNCIÓN PURA, sin numpy: son cuatro líneas y así el módulo no arrastra una
    dependencia para hacer un producto escalar.

    Un vector nulo (todo ceros) no tiene dirección: devolvemos 0.0 en vez de
    dividir por cero. Es el caso de una pregunta que los embeddings no supieron
    representar, y no debe "parecerse" a nada.
    """
    if len(a) != len(b):
        raise ValueError(f"Vectores de distinta dimensión: {len(a)} vs {len(b)}")
    producto = sum(x * y for x, y in zip(a, b))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return producto / (norma_a * norma_b)


@dataclass(frozen=True)
class Acierto:
    """Un HIT: qué respuesta se sirvió, de qué pregunta y con cuánto parecido.

    La `similitud` no es decorativa: es lo que se loguea para calibrar el umbral
    con datos reales. Si tus aciertos rondan el 0.93, el umbral 0.92 está
    rozando el falso positivo y conviene subirlo.
    """
    respuesta: str
    pregunta_original: str
    similitud: float


class SemanticCache:
    """El caché semántico. Inyecta embeddings y backend; nada se crea aquí dentro."""

    def __init__(self, embeddings, backend: CacheBackend | None = None, umbral: float | None = None):
        """
        embeddings: cualquier objeto con `embed_query(texto) -> list[float]`.
                    En producción, los locales de app/embeddings.py (coste 0).
        backend   : dónde se guarda. Por defecto, memoria.
        umbral    : similitud mínima para considerar dos preguntas "la misma".
                    Por defecto, el del .env (CACHE_UMBRAL_SIMILITUD=0.92).
        """
        self.embeddings = embeddings
        self.backend = backend if backend is not None else InMemoryCache()
        if umbral is None:
            from app.config import settings
            umbral = settings.cache_umbral_similitud
        self.umbral = umbral
        # Contadores para las métricas. Sin ellos no se puede saber si el caché
        # sirve de algo: un caché con 2% de aciertos solo añade latencia.
        self.aciertos = 0
        self.fallos = 0

    # ---- Lectura ----
    def buscar(self, pregunta: str, rol: str = "analyst") -> Acierto | None:
        """La respuesta cacheada más parecida, o None si ninguna llega al umbral.

        Solo mira las entradas del MISMO rol (el backend ya las filtra). Un
        'analyst' no puede recibir, ni por parecido semántico, lo que se generó
        para un 'compliance'.
        """
        vector = tuple(self.embeddings.embed_query(pregunta))

        mejor: Acierto | None = None
        for entrada in self.backend.entradas(rol):
            similitud = coseno(vector, entrada.vector)
            if similitud >= self.umbral and (mejor is None or similitud > mejor.similitud):
                mejor = Acierto(
                    respuesta=entrada.respuesta,
                    pregunta_original=entrada.pregunta,
                    similitud=similitud,
                )

        if mejor is None:
            self.fallos += 1
        else:
            self.aciertos += 1
        return mejor

    # ---- Escritura ----
    def guardar(self, pregunta: str, respuesta: str, rol: str = "analyst") -> None:
        """Cachea una respuesta recién generada, bajo el rol que la pidió.

        ⚠️ Nunca guardes aquí una respuesta que un guardrail bloqueó. Cachear un
           bloqueo lo convierte en permanente para toda pregunta parecida.
        """
        vector = tuple(self.embeddings.embed_query(pregunta))
        self.backend.guardar(EntradaCache(pregunta, respuesta, vector, rol))

    # ---- Métricas ----
    @property
    def tasa_aciertos(self) -> float:
        """Fracción de búsquedas que acertaron. El número que justifica el caché."""
        total = self.aciertos + self.fallos
        return self.aciertos / total if total else 0.0
