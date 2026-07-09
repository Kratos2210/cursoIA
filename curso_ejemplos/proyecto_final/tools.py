"""
tools.py · Las manos del agente
================================
FINALIDAD:
  Las dos capacidades que el agente puede decidir usar por su cuenta:
    - buscar_normativa(pregunta): responde dudas leyendo la normativa (RAG).
    - evaluar_regla_calidad(regla): la evalúa, la estructura y la AUDITA.

LÓGICA:
  Las tools necesitan cosas de fuera (el modelo, el retriever, la ruta del
  log). En vez de usar variables globales — que hacen imposible el testeo —
  usamos una FÁBRICA: crear_tools(...) recibe esas piezas y devuelve las tools
  ya "cableadas" con ellas (esto se llama inyección de dependencias).

  Así, un test puede pasarle un modelo falso y un log temporal, y verificar
  el comportamiento sin llamar a Gemini ni ensuciar el log real.

  ⭐ El docstring de cada tool NO es documentación: es el texto que el modelo
     lee para decidir cuál usar. Escríbelo pensando en él, no en ti.
"""

from langchain_core.tools import tool
from pydantic import ValidationError

import audit
import rag


def crear_tools(llm, evaluador, retriever, ruta_auditoria=None):
    """Devuelve la lista de tools del agente, ya cableadas.

    Parámetros:
      llm        : el modelo de chat (para redactar la respuesta del RAG).
      evaluador  : el modelo con with_structured_output(HallazgoCalidad).
      retriever  : el buscador sobre la normativa.
      ruta_auditoria : dónde escribir el log (None = la ruta del proyecto).
    """

    @tool
    def buscar_normativa(pregunta: str) -> str:
        """Responde dudas sobre la normativa de gobierno de datos.
        Úsala cuando el usuario PREGUNTE qué dice una política o regla."""
        ctx = rag.contexto(retriever, pregunta)
        # La regla anti-alucinación: "solo con esto, y si no está, dilo".
        prompt = (f"Responde SOLO con esta normativa. Si no está, dilo.\n"
                  f"Normativa:\n{ctx}\n\nPregunta: {pregunta}")
        return llm.invoke(prompt).content

    @tool
    def evaluar_regla_calidad(regla: str) -> str:
        """Evalúa si una regla de calidad de datos está respaldada por la normativa
        y GUARDA el resultado en el log de auditoría.
        Úsala cuando el usuario pida EVALUAR o VERIFICAR una regla."""
        ctx = rag.contexto(retriever, regla)
        try:
            # Salida estructurada: el modelo llena el molde HallazgoCalidad.
            hallazgo = evaluador.invoke(
                f"Con base en esta normativa:\n{ctx}\n\n"
                f"Evalúa si esta regla está respaldada: '{regla}'"
            )
        except ValidationError as error:
            # El modelo devolvió algo que no encaja en el molde (p. ej. una
            # severidad inventada). Preferimos decirlo a auditar basura.
            return f"No pude estructurar la evaluación: {error.error_count()} campo(s) inválido(s)."

        # Auditoría: dejamos rastro de la decisión (imprescindible en una financiera).
        audit.registrar_auditoria(hallazgo, ruta=ruta_auditoria)

        return (f"Evaluación -> cumple: {hallazgo.cumple} | severidad: {hallazgo.severidad}\n"
                f"Justificación: {hallazgo.justificacion}")

    return [buscar_normativa, evaluar_regla_calidad]
