"""
judge.py · LLM-as-judge para la calidad SUBJETIVA (opcional)
=============================================================
FINALIDAD:
  La fidelidad de precios se mide con código (guardrails/price_guard.py): es
  binaria y no necesita un LLM. Pero "¿la respuesta es útil y suena a vendedora
  amable?" es subjetivo, y ahí sí ayuda un juez.

  ⭐ DIVISIÓN DE TRABAJO (ver docs/adr/0002): lo verificable con la verdad a mano
     —el precio— se comprueba con código, barato y determinista. Lo subjetivo
     —el tono, la utilidad— se delega a un juez LLM. Poner al juez a comprobar un
     precio sería pagar una llamada para hacer una resta; dejar el tono a un regex
     sería fingir que la calidad se mide contando palabras.

  ⚠️ Este juez NO forma parte del CI gate (ese es determinista). Es para calibrar
     el tono entre variantes del prompt (el A/B) con más señal que el 👍/👎.

  El juez usa `with_structured_output` (m05) a temperatura 0: un veredicto tipado
  y repetible, no un párrafo que interpretar.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class VeredictoTono(BaseModel):
    """La nota subjetiva de una respuesta del asistente."""
    utilidad: int = Field(ge=1, le=5, description="¿Ayuda a decidir la compra? 1-5")
    amabilidad: int = Field(ge=1, le=5, description="¿Suena a vendedora cálida y cercana? 1-5")
    justificacion: str = Field(description="Una frase que explique la nota")

    @property
    def promedio(self) -> float:
        return (self.utilidad + self.amabilidad) / 2


_INSTRUCCION = (
    "Eres un evaluador de calidad de un asistente de compras de una tienda de "
    "bisutería. Puntúa la RESPUESTA del asistente ante la PETICIÓN de la clienta. "
    "No juzgues si los precios son correctos (eso lo verifica otro sistema): "
    "juzga solo la UTILIDAD (¿ayuda a decidir?) y la AMABILIDAD (¿tono cálido y "
    "cercano?)."
)


def crear_juez(llm):
    """Un juez que puntúa tono/utilidad. `llm` se inyecta (real en prod, falso en test)."""
    evaluador = llm.with_structured_output(VeredictoTono)

    def juzgar(peticion: str, respuesta: str) -> VeredictoTono:
        return evaluador.invoke(
            f"{_INSTRUCCION}\n\nPETICIÓN: {peticion}\n\nRESPUESTA: {respuesta}")

    return juzgar
