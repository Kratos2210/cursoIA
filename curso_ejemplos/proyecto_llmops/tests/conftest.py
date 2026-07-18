"""
conftest.py · Los dobles de prueba del proyecto LLMOps
=======================================================
FINALIDAD:
  Ejercitar el servicio completo (agente, RBAC, caché, evaluación) sin llamar a
  Gemini, sin levantar Postgres y sin Redis. Todo lo caro entra por parámetro,
  así que en los tests le pasamos un doble:

    - ModeloFalso       : recita un guion en vez de pensar.
    - EvaluadorFalso    : se hace pasar por llm.with_structured_output(...).
    - RetrieverFalso    : devuelve fragmentos fijos, CON metadatos de
                          confidencialidad (para poder probar el RBAC).
    - EmbeddingsFalsos  : vectores deterministas, sin API. El semantic cache
                          necesita embeddings; aquí no cuestan nada.
    - AgenteFalso       : imita el `astream(stream_mode="messages")` de LangGraph
                          y va soltando los tokens de un guion. Con él, la API
                          entera (guardrails + caché + SSE) se prueba sin modelo.

LÓGICA — por qué duplicamos los dobles de proyecto_final:
  Podríamos importarlos de `proyecto_final/tests/conftest.py`, pero eso acopla
  dos suites: un cambio en los tests del prototipo rompería los del servicio.
  Cada proyecto es autónomo. La duplicación aquí es una decisión, no un descuido.
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
    """Devuelve, en orden, las respuestas del guion que le demos.

    Implementa lo mínimo que LangGraph le exige a un modelo:
      - _generate(): la siguiente respuesta del guion.
      - bind_tools(): el agente le "entrega" sus tools; no las necesita,
        porque el guion ya trae decididos los tool_calls.
    """

    respuestas: list[AIMessage]
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
        return self


class EvaluadorFalso:
    """Se hace pasar por llm.with_structured_output(HallazgoCalidad)."""

    def __init__(self, resultado):
        self.resultado = resultado
        self.invocaciones = []

    def invoke(self, entrada, *args, **kwargs):
        self.invocaciones.append(entrada)
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


# ==================================================================
# Doble 2 · Un retriever con metadatos de confidencialidad
# ==================================================================
class RetrieverFalso:
    """Devuelve siempre los mismos Documents, con su nivel de confidencialidad.

    A diferencia del de proyecto_final, aquí los fragmentos SÍ llevan
    `metadata["confidentiality"]`: es lo que el RBAC filtra después.
    """

    def __init__(self, fragmentos: list[tuple[str, str]]):
        # fragmentos: lista de (texto, nivel)
        self.fragmentos = fragmentos
        self.preguntas = []

    def invoke(self, pregunta: str, *args, **kwargs) -> list[Document]:
        self.preguntas.append(pregunta)
        return [
            Document(page_content=texto, metadata={"confidentiality": nivel})
            for texto, nivel in self.fragmentos
        ]


# ==================================================================
# Doble 3 · Embeddings deterministas (el semantic cache los necesita)
# ==================================================================
class EmbeddingsFalsos:
    """Imita la interfaz de GoogleGenerativeAIEmbeddings sin llamar a la API.

    Devuelve el vector que le hayamos asociado a cada texto. Si el texto no está
    en la tabla, devuelve un vector nulo: así una pregunta desconocida nunca
    "se parece" a nada y el caché falla (MISS), que es lo que queremos probar.
    """

    def __init__(self, tabla: dict[str, list[float]], dimensiones: int = 3):
        self.tabla = tabla
        self.dimensiones = dimensiones
        self.llamadas = []

    def embed_query(self, texto: str) -> list[float]:
        self.llamadas.append(texto)
        return self.tabla.get(texto, [0.0] * self.dimensiones)

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in textos]


# ==================================================================
# Doble 4 · Un agente de LangGraph que emite tokens de un guion
# ==================================================================
class AgenteFalso:
    """Imita `create_react_agent(...).astream(..., stream_mode="messages")`.

    LangGraph emite pares `(fragmento, metadatos)`. Los metadatos dicen de qué
    nodo del grafo salió el fragmento, y `app/streaming.py` los usa para
    descartar los del nodo 'tools'. Aquí reproducimos esa forma exacta: si el
    doble mintiera sobre el formato, el test pasaría y la app fallaría.
    """

    def __init__(self, tokens: list[str], nodo: str = "agent", uso: tuple | None = None):
        self.tokens = tokens
        self.nodo = nodo
        # `uso=(entrada, salida)` reproduce lo que hace un proveedor real en
        # streaming: el conteo NO viaja en cada chunk, llega solo en el último.
        self.uso = uso
        self.invocaciones: list[dict] = []

    async def astream(self, entrada, config=None, stream_mode=None):
        self.invocaciones.append({
            "entrada": entrada, "config": config, "stream_mode": stream_mode,
        })
        for indice, token in enumerate(self.tokens):
            ultimo = indice == len(self.tokens) - 1
            yield (_FragmentoFalso(token, self.uso if (ultimo and self.uso) else None),
                   {"langgraph_node": self.nodo})


class _FragmentoFalso:
    """Un chunk de mensaje: streaming.py le mira `.content` y `.usage_metadata`."""

    def __init__(self, content: str, uso: tuple | None = None):
        self.content = content
        # Los chunks intermedios NO tienen el atributo, igual que los reales:
        # por eso `extraer_uso` usa getattr con default y no revienta.
        if uso is not None:
            self.usage_metadata = {
                "input_tokens": uso[0],
                "output_tokens": uso[1],
                "total_tokens": uso[0] + uso[1],
            }


# ==================================================================
# Fixtures
# ==================================================================
@pytest.fixture
def retriever_falso():
    """Dos reglas públicas y una restringida: material para probar el RBAC."""
    return RetrieverFalso([
        (
            "Regla 1 — Cifrado en reposo:\nTodos los datos personales de clientes "
            "deben almacenarse cifrados en reposo usando AES-256.",
            "public",
        ),
        (
            "Regla 4 — Control de acceso:\nTodo acceso debe quedar registrado en "
            "un log de auditoría.",
            "internal",
        ),
        (
            "Anexo confidencial:\nLas claves maestras se custodian en el HSM del "
            "centro de datos de Lima.",
            "restricted",
        ),
    ])


@pytest.fixture
def ruta_log(tmp_path):
    """Un log de auditoría temporal: nunca tocamos el del proyecto."""
    return tmp_path / "hallazgos_auditoria.log"


@pytest.fixture
def hallazgo_ejemplo():
    """Un hallazgo válido, el que el 'modelo' habría producido."""
    from app.audit_import import HallazgoCalidad

    return HallazgoCalidad(
        regla="Los datos personales deben cifrarse en reposo con AES-256",
        cumple=True,
        severidad="alta",
        justificacion="La Regla 1 de la normativa lo exige explícitamente.",
    )


@pytest.fixture
def fabrica_agente():
    """La CLASE AgenteFalso, para que un test la instancie con su propio guion.

    Se expone por fixture y no por `from .conftest import AgenteFalso` porque
    las carpetas tests/ no son paquetes (no tienen __init__.py): el import
    relativo fallaría. Las fixtures son el canal que pytest sí garantiza.
    """
    return AgenteFalso


@pytest.fixture
def embeddings_falsos():
    """Dos preguntas casi idénticas (coseno ~1) y una distinta (coseno 0)."""
    return EmbeddingsFalsos({
        "¿Hay que cifrar los datos?": [1.0, 0.0, 0.0],
        "¿Los datos se cifran?": [0.99, 0.14, 0.0],   # casi el mismo vector
        "¿Cuál es el horario de la oficina?": [0.0, 0.0, 1.0],
    })
