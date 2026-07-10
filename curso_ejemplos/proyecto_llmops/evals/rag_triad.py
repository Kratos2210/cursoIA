"""
rag_triad.py · Las tres preguntas que diagnostican un RAG
==========================================================
FINALIDAD:
  "El RAG responde mal" no es un diagnóstico: es una queja. La tríada RAG la
  convierte en un diagnóstico, porque separa TRES fallos distintos que producen
  el mismo síntoma:

    1. FAITHFULNESS (fidelidad) — ¿la respuesta se sostiene SOLO en el contexto?
       Baja → el modelo **alucina**: se inventa lo que el contexto no dice.
       Se arregla en el PROMPT (o cambiando de modelo).

    2. ANSWER RELEVANCE (pertinencia) — ¿responde a la pregunta que se hizo?
       Baja → el modelo divaga: dice cosas ciertas que no vienen a cuento.
       Se arregla en el PROMPT.

    3. CONTEXT PRECISION (precisión del contexto) — ¿los fragmentos recuperados
       eran los correctos?
       Baja → el fallo está en el **RETRIEVER**, no en el modelo. Cambiar de LLM
       no arreglaría nada: le estás dando los párrafos equivocados.

  ⭐ Ese es el valor de las tres juntas: te dicen DÓNDE mirar. Con una sola
     métrica global, un equipo pasa semanas afinando prompts cuando el problema
     era el chunking.

  ⭐ El triángulo cierra: pregunta ←→ contexto ←→ respuesta. Cada métrica cubre
     un lado. Si las tres son altas, no queda por dónde colarse un fallo.

LÓGICA:
  Cada métrica es una rúbrica distinta para el mismo juez (`judge.py`), y cada
  una mira solo DOS de los tres vértices:

      faithfulness      : contexto  + respuesta   (no mira la pregunta)
      answer_relevance  : pregunta  + respuesta   (no mira el contexto)
      context_precision : pregunta  + contexto    (no mira la respuesta)

  Que cada una ignore un vértice es lo que las hace independientes. Si las tres
  vieran los tres, medirían lo mismo tres veces.
"""
from __future__ import annotations

from dataclasses import dataclass

from evals.judge import Veredicto, juzgar

# ------------------------------------------------------------------
# LAS TRES RÚBRICAS
# ------------------------------------------------------------------
RUBRICA_FAITHFULNESS = """\
CRITERIO: fidelidad al contexto (¿alucina?).

Lee el CONTEXTO y la RESPUESTA. Puntúa 1.0 si CADA afirmación de la respuesta se
deduce del contexto. Puntúa 0.0 si la respuesta afirma algo que el contexto no
dice, aunque sea verdad en el mundo real.

Decir "no está en la normativa" cuando efectivamente no está es FIEL: 1.0.

CONTEXTO:
{contexto}

RESPUESTA:
{respuesta}
"""

RUBRICA_ANSWER_RELEVANCE = """\
CRITERIO: pertinencia (¿responde a lo que se preguntó?).

Lee la PREGUNTA y la RESPUESTA. Puntúa 1.0 si la respuesta aborda directamente
la pregunta. Puntúa bajo si divaga, si responde a otra pregunta parecida, o si
añade material cierto pero irrelevante.

NO juzgues aquí si la respuesta es correcta: solo si es pertinente.

PREGUNTA:
{pregunta}

RESPUESTA:
{respuesta}
"""

RUBRICA_CONTEXT_PRECISION = """\
CRITERIO: precisión del contexto recuperado (¿el retriever hizo su trabajo?).

Lee la PREGUNTA y los FRAGMENTOS que recuperó el buscador. Puntúa 1.0 si todos
los fragmentos son necesarios para responder. Baja la nota por cada fragmento
irrelevante que se coló: el ruido en el contexto empuja al modelo a alucinar.

Un contexto VACÍO cuando la pregunta era respondible vale 0.0.

PREGUNTA:
{pregunta}

FRAGMENTOS RECUPERADOS:
{contexto}
"""


@dataclass(frozen=True)
class ResultadoTriada:
    """Las tres notas de un ejemplo, más su media."""
    pregunta: str
    faithfulness: Veredicto
    answer_relevance: Veredicto
    context_precision: Veredicto

    @property
    def score(self) -> float:
        """La media aritmética de las tres. Es lo que mira el CI gate.

        ⚠️ Promediar esconde. Un ejemplo con faithfulness=0.0 (alucinó del todo)
           y las otras dos a 1.0 saca un 0.67, que con umbral 0.6 aprobaría. Por
           eso `peor_metrica` existe y `run_evals.py` la reporta aparte: la media
           dice si el sistema va bien; el mínimo dice si algo está roto.
        """
        return (self.faithfulness.puntuacion
                + self.answer_relevance.puntuacion
                + self.context_precision.puntuacion) / 3

    @property
    def peor_metrica(self) -> tuple[str, float]:
        """La métrica más baja y su valor: el diagnóstico, no el promedio."""
        notas = {
            "faithfulness": self.faithfulness.puntuacion,
            "answer_relevance": self.answer_relevance.puntuacion,
            "context_precision": self.context_precision.puntuacion,
        }
        nombre = min(notas, key=notas.__getitem__)
        return nombre, notas[nombre]

    def a_dict(self) -> dict:
        return {
            "pregunta": self.pregunta,
            "faithfulness": self.faithfulness.puntuacion,
            "answer_relevance": self.answer_relevance.puntuacion,
            "context_precision": self.context_precision.puntuacion,
            "score": self.score,
        }


# ------------------------------------------------------------------
# LAS TRES MÉTRICAS
# ------------------------------------------------------------------
def faithfulness(juez, respuesta: str, contexto: str) -> Veredicto:
    """¿Se sostiene la respuesta SOLO en el contexto? (detecta alucinación)"""
    return juzgar(juez, RUBRICA_FAITHFULNESS, contexto=contexto, respuesta=respuesta)


def answer_relevance(juez, pregunta: str, respuesta: str) -> Veredicto:
    """¿Responde a lo que se preguntó? (detecta divagación)"""
    return juzgar(juez, RUBRICA_ANSWER_RELEVANCE, pregunta=pregunta, respuesta=respuesta)


def context_precision(juez, pregunta: str, contexto: str) -> Veredicto:
    """¿Recuperó el retriever los fragmentos correctos? (detecta fallo de RAG)"""
    return juzgar(juez, RUBRICA_CONTEXT_PRECISION, pregunta=pregunta, contexto=contexto)


def evaluar_triada(juez, pregunta: str, respuesta: str, contexto: str) -> ResultadoTriada:
    """Las tres métricas de un ejemplo. Tres llamadas al juez, no una.

    ⭐ Podríamos pedirle las tres notas en un solo prompt y ahorrar dos llamadas.
       Sería más barato y peor: el juez arrastraría su impresión de la primera
       métrica a las otras dos (efecto halo) y las tres notas dejarían de ser
       independientes. Se paga el triple para conservar la señal.
    """
    return ResultadoTriada(
        pregunta=pregunta,
        faithfulness=faithfulness(juez, respuesta, contexto),
        answer_relevance=answer_relevance(juez, pregunta, respuesta),
        context_precision=context_precision(juez, pregunta, contexto),
    )
