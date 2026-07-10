"""
judge.py · Un LLM que califica a otro LLM
==========================================
FINALIDAD:
  Evaluar respuestas en lenguaje natural. No hay `assert respuesta == esperada`
  que valga: dos redacciones distintas pueden ser igual de correctas, y una
  copia literal de la respuesta esperada puede ser una alucinación afortunada.

  La salida clásica es el **LLM-as-a-judge**: otro modelo, con una rúbrica
  explícita, puntúa la respuesta. No es perfecto. Es reproducible, barato y
  escala — y esas tres cosas no las tiene un humano revisando 200 respuestas.

LÓGICA:
  - Veredicto: el molde Pydantic. El juez NO devuelve prosa: devuelve un número
    y una justificación. `with_structured_output` lo obliga.
  - crear_juez(llm): envuelve el modelo.
  - juzgar(juez, rubrica, **campos): renderiza la rúbrica y pide el veredicto.

⭐ POR QUÉ SALIDA ESTRUCTURADA Y NO TEXTO. Un juez que responde "me parece que
   está bastante bien, un 8 sobre 10 quizá" no se puede promediar, ni comparar
   entre ejecuciones, ni meter en un umbral de CI. El `with_structured_output`
   convierte una opinión en un dato.

⚠️ LOS SESGOS DEL JUEZ, que hay que conocer antes de confiar en él:
   - **Sesgo de posición**: si le das dos respuestas a comparar, tiende a
     preferir la primera. Por eso aquí se puntúa UNA respuesta contra una
     rúbrica, no dos entre sí.
   - **Sesgo de verbosidad**: puntúa más alto lo largo. La rúbrica lo contrarresta
     diciendo explícitamente que la longitud no suma.
   - **Auto-preferencia**: un modelo puntúa mejor lo que él mismo escribiría.
     Lo honesto es que el juez sea de una familia distinta a la del generador.
   - **Temperatura**: el juez va a 0. Un juez creativo es un juez que cambia de
     opinión entre dos ejecuciones idénticas, y entonces tu CI parpadea.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Veredicto(BaseModel):
    """La respuesta del juez. Un número y su razón, nunca prosa suelta."""

    puntuacion: float = Field(
        ge=0.0, le=1.0,
        description="0.0 = falla por completo; 1.0 = cumple el criterio del todo",
    )
    justificacion: str = Field(
        description="Una o dos frases explicando la puntuación, citando el texto",
    )

    @property
    def aprueba(self) -> bool:
        """Un aprobado laxo (>= 0.7). El umbral duro lo pone `ci_gate.py`."""
        return self.puntuacion >= 0.7


# La instrucción común a todas las rúbricas. Va delante de cada una.
#
# Lo que hace cada línea:
#   - "Sé estricto": los jueces son blandos por defecto; sin esto casi todo saca 0.9.
#   - "La longitud no suma": contrarresta el sesgo de verbosidad.
#   - "0.0 y 1.0 son válidas": si no, el juez se refugia en el 0.5 y el CI gate
#     deja de discriminar.
PREAMBULO = (
    "Eres un evaluador experto en gobierno de datos. Puntúas de 0.0 a 1.0.\n"
    "Sé ESTRICTO: solo lo que cumple el criterio del todo merece 1.0.\n"
    "La longitud de la respuesta NO suma puntos. Una respuesta corta y correcta "
    "vale más que una larga y vaga.\n"
    "Las puntuaciones 0.0 y 1.0 son válidas y esperadas; no te refugies en el 0.5.\n"
)


def crear_juez(llm):
    """El modelo, obligado a devolver un Veredicto.

    Recibe el llm por parámetro (inyección) para que los tests le pasen un juez
    falso y la evaluación corra sin cuota y sin red.
    """
    return llm.with_structured_output(Veredicto)


def juzgar(juez, rubrica: str, **campos: str) -> Veredicto:
    """Renderiza la rúbrica con los campos y pide el veredicto.

    La rúbrica es un string con marcadores `{pregunta}`, `{respuesta}`… Se usa
    `str.format` y no Jinja2 a propósito: aquí no hay lógica, solo sustitución.
    (Los prompts del AGENTE sí van en Jinja2; ver `prompts/loader.py`.)
    """
    return juez.invoke(PREAMBULO + "\n" + rubrica.format(**campos))
