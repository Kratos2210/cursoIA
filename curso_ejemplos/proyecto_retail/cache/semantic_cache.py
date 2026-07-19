"""
semantic_cache.py · Responder sin llamar al modelo
===================================================
FINALIDAD:
  Un caché exacto (dict) acierta solo con la pregunta EXACTA. Pero "aretes
  dorados baratos" y "unos aros dorados económicos" son la misma petición. El
  caché SEMÁNTICO compara SIGNIFICADOS: vectoriza la petición y busca una ya
  respondida que se le parezca lo bastante.

  El ahorro es doble: coste (~$0 en un acierto) y latencia (milisegundos en vez
  de segundos, que se nota más que el dinero).

⚠️ EL FALSO POSITIVO ES UNA RESPUESTA INCORRECTA, NO UNA LENTITUD. Con un umbral
   bajo, "aretes por menos de 25" y "aretes por menos de 250" se parecen mucho, y
   la clienta recibe con aplomo la respuesta a una pregunta que no hizo. Por eso
   el umbral por defecto es 0.92: ante la duda, un MISS caro es infinitamente
   mejor que un HIT equivocado. (Espejo de proyecto_llmops, sin el eje de rol.)

⭐ Todo entra por parámetro (embeddings, backend, umbral) → se testea con vectores
   deterministas, sin red, sin Redis y sin cuota.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from proyecto_retail.cache.cache_backends import CacheBackend, EntradaCache, InMemoryCache


def coseno(a, b) -> float:
    """Similitud coseno: 1.0 = idénticos, 0.0 = ortogonales. PURA, sin numpy.

    Un vector nulo no tiene dirección: devolvemos 0.0 en vez de dividir por cero.
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
    """Un HIT: qué respuesta se sirvió, de qué pregunta y con cuánto parecido."""
    respuesta: str
    pregunta_original: str
    similitud: float


class SemanticCache:
    """El caché semántico. Inyecta embeddings y backend; nada se crea aquí dentro."""

    def __init__(self, embeddings, backend: CacheBackend | None = None, umbral: float | None = None):
        self.embeddings = embeddings
        self.backend = backend if backend is not None else InMemoryCache()
        if umbral is None:
            from proyecto_retail.app.config import settings
            umbral = settings.cache_umbral_similitud
        self.umbral = umbral
        self.aciertos = 0
        self.fallos = 0

    def buscar(self, pregunta: str) -> Acierto | None:
        """La respuesta cacheada más parecida, o None si ninguna llega al umbral."""
        vector = tuple(self.embeddings.embed_query(pregunta))
        mejor: Acierto | None = None
        for entrada in self.backend.entradas():
            similitud = coseno(vector, entrada.vector)
            if similitud >= self.umbral and (mejor is None or similitud > mejor.similitud):
                mejor = Acierto(entrada.respuesta, entrada.pregunta, similitud)

        if mejor is None:
            self.fallos += 1
        else:
            self.aciertos += 1
        return mejor

    def guardar(self, pregunta: str, respuesta: str) -> None:
        """Cachea una respuesta recién generada.

        ⚠️ Nunca guardes una respuesta que el guardrail bloqueó: cachear un
           precio inventado lo convierte en permanente para toda pregunta parecida.
        """
        vector = tuple(self.embeddings.embed_query(pregunta))
        self.backend.guardar(EntradaCache(pregunta, respuesta, vector))

    @property
    def tasa_aciertos(self) -> float:
        total = self.aciertos + self.fallos
        return self.aciertos / total if total else 0.0
