"""
conftest.py · Los dobles de prueba del proyecto final
======================================================
FINALIDAD:
  Poder ejercitar el agente COMPLETO (grafo, tools, auditoría) sin llamar a
  Gemini. Para eso fabricamos dos "dobles":

    - ModeloFalso    : se hace pasar por un ChatGoogleGenerativeAI, pero en vez
                       de pensar, recita un guion de respuestas que le damos.
    - RetrieverFalso : en vez de buscar por vectores, devuelve los fragmentos
                       que le pongamos.

LÓGICA — por qué esto es posible:
  Porque graph_builder.construir_agente() recibe el modelo y el retriever por
  parámetro (inyección de dependencias) en vez de crearlos por dentro. Ese
  detalle de diseño es lo que separa un proyecto testeable de uno que no lo es.

  El app.py monolítico original NO se podía testear: al importarlo ya llamaba
  a la API. Este es el beneficio concreto de haberlo modularizado.
"""
from typing import Any, Optional

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


# ==================================================================
# Doble 1 · Un modelo de chat que recita un guion
# ==================================================================
class ModeloFalso(BaseChatModel):
    """Un ChatModel que devuelve, en orden, las respuestas del guion.

    Implementa lo mínimo que LangChain/LangGraph le exigen a un modelo:
      - _generate(): producir la siguiente respuesta.
      - bind_tools(): aceptar tools. Nuestro guion ya trae los tool_calls
        decididos de antemano, así que aquí solo devolvemos el mismo modelo.
    """

    # 'respuestas' es el guion: una lista de AIMessage (con o sin tool_calls).
    respuestas: list[AIMessage]
    # Cuántas veces se le ha pedido una respuesta (para ir avanzando el guion).
    llamadas: int = 0

    @property
    def _llm_type(self) -> str:
        return "modelo-falso"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.llamadas >= len(self.respuestas):
            raise AssertionError(
                f"El agente pidió {self.llamadas + 1} respuestas, pero el guion "
                f"solo tiene {len(self.respuestas)}. ¿Un bucle infinito de tools?"
            )
        mensaje = self.respuestas[self.llamadas]
        self.llamadas += 1
        return ChatResult(generations=[ChatGeneration(message=mensaje)])

    def bind_tools(self, tools, **kwargs):
        """El agente nos 'entrega' sus tools. No las necesitamos: ya sabemos
        qué vamos a contestar. Devolvemos el mismo modelo para encadenar."""
        return self


class EvaluadorFalso:
    """Se hace pasar por llm.with_structured_output(HallazgoCalidad).

    Devuelve siempre el hallazgo que le demos (o lanza la excepción que le demos).
    """

    def __init__(self, resultado):
        self.resultado = resultado
        self.invocaciones = []

    def invoke(self, entrada, *args, **kwargs):
        self.invocaciones.append(entrada)
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


# ==================================================================
# Doble 2 · Un retriever que no busca nada
# ==================================================================
class RetrieverFalso:
    """Devuelve siempre los mismos fragmentos, sin vectores ni API."""

    def __init__(self, fragmentos: list[str]):
        self.fragmentos = fragmentos
        self.preguntas = []   # guardamos qué se le preguntó (para asertar)

    def invoke(self, pregunta: str, *args, **kwargs) -> list[Document]:
        self.preguntas.append(pregunta)
        return [Document(page_content=f) for f in self.fragmentos]


# ==================================================================
# Fixtures
# ==================================================================
@pytest.fixture
def retriever_falso():
    """Un retriever con dos reglas de la normativa real."""
    return RetrieverFalso([
        "Regla 1 — Cifrado en reposo:\nTodos los datos personales de clientes "
        "deben almacenarse cifrados en reposo usando AES-256.",
        "Regla 4 — Control de acceso:\nTodo acceso debe quedar registrado en "
        "un log de auditoría.",
    ])


@pytest.fixture
def ruta_log(tmp_path):
    """Un log de auditoría temporal: nunca tocamos el del proyecto."""
    return tmp_path / "hallazgos_auditoria.log"


@pytest.fixture
def hallazgo_ejemplo():
    """Un hallazgo válido, el que el 'modelo' habría producido."""
    import audit
    return audit.HallazgoCalidad(
        regla="Los datos personales deben cifrarse en reposo con AES-256",
        cumple=True,
        severidad="alta",
        justificacion="La Regla 1 de la normativa lo exige explícitamente.",
    )
