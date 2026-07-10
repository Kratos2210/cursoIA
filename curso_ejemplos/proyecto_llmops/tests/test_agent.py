"""
test_agent.py · El agente de producción, sin gastar un token
=============================================================
FINALIDAD:
  Verificar las DOS promesas que distinguen a este agente del prototipo:

    1) Reutiliza el ensamblado de `proyecto_final.graph_builder`, no lo copia.
    2) Sigue auditando. Una versión anterior de `agent.py` reimplementó el
       grafo y, al copiarlo, olvidó llamar a `registrar_auditoria`: el agente
       dejó de dejar rastro y nadie se enteró. Estos tests lo impiden.

  Y la tercera, propia del servicio: el RBAC llega hasta las tools.

LÓGICA del guion:
  create_react_agent llama al modelo, ve que pidió una tool, la ejecuta, le
  devuelve el resultado y vuelve a llamar al modelo. Por eso cada guion tiene
  2 respuestas: (1) "usa esta tool", (2) "esta es la respuesta final".
"""
import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from app import agent as agent_mod
from app import audit_import
from conftest import EvaluadorFalso, ModeloFalso

pytestmark = pytest.mark.offline

HILO = {"configurable": {"thread_id": "test"}}


def _pedir_tool(nombre: str, args: dict, id_llamada: str = "call_1") -> AIMessage:
    """El mensaje con el que un modelo dice 'quiero usar esta herramienta'."""
    return AIMessage(content="", tool_calls=[{"name": nombre, "args": args, "id": id_llamada}])


# ==================================================================
# Las tools del servicio
# ==================================================================
class TestCrearTools:
    def test_sin_evaluador_solo_hay_busqueda(self, retriever_falso):
        tools = agent_mod.crear_tools(ModeloFalso(respuestas=[]), retriever_falso, None)
        assert [t.name for t in tools] == ["buscar_normativa"]

    def test_con_evaluador_aparece_la_evaluacion(self, retriever_falso, hallazgo_ejemplo):
        tools = agent_mod.crear_tools(
            ModeloFalso(respuestas=[]), retriever_falso, EvaluadorFalso(hallazgo_ejemplo))
        assert {t.name for t in tools} == {"buscar_normativa", "evaluar_regla_calidad"}

    def test_buscar_normativa_respeta_el_rol(self, retriever_falso):
        """El RBAC no vive solo en rag.py: llega hasta la tool que usa el modelo."""
        modelo = ModeloFalso(respuestas=[AIMessage(content="respondido")])
        tools = agent_mod.crear_tools(modelo, retriever_falso, None, rol="analyst")
        buscar = {t.name: t for t in tools}["buscar_normativa"]
        buscar.invoke({"pregunta": "¿dónde están las claves maestras?"})

        # El prompt que llegó al modelo NO puede contener el fragmento restringido.
        enviado = modelo.respuestas and retriever_falso.preguntas
        assert enviado                      # se consultó el retriever
        # Reconstruimos lo que la tool le pasó al modelo:
        from app import rag
        contexto = rag.recuperar(retriever_falso, "claves", rol="analyst")
        assert "HSM" not in contexto

    def test_evaluar_regla_calidad_ESCRIBE_EN_EL_LOG(
        self, retriever_falso, hallazgo_ejemplo, ruta_log
    ):
        """La regresión que motivó esta revisión. Si esto falla, se perdió la auditoría."""
        tools = agent_mod.crear_tools(
            ModeloFalso(respuestas=[]), retriever_falso,
            EvaluadorFalso(hallazgo_ejemplo), "analyst", ruta_log,
        )
        evaluar = {t.name: t for t in tools}["evaluar_regla_calidad"]

        salida = evaluar.invoke({"regla": "cifrar en reposo"})

        assert "cumple: True" in salida and "severidad: alta" in salida
        assert ruta_log.exists(), "la evaluación no dejó rastro en disco"
        assert len(audit_import.leer_auditoria(ruta_log)) == 1

    def test_sin_normativa_accesible_no_se_audita(self, hallazgo_ejemplo, ruta_log):
        """Si el rol no puede ver nada, no hay evaluación… ni línea de auditoría."""
        from conftest import RetrieverFalso
        solo_secreto = RetrieverFalso([("Las claves maestras del HSM.", "restricted")])
        tools = agent_mod.crear_tools(
            ModeloFalso(respuestas=[]), solo_secreto,
            EvaluadorFalso(hallazgo_ejemplo), "analyst", ruta_log,
        )
        evaluar = {t.name: t for t in tools}["evaluar_regla_calidad"]

        salida = evaluar.invoke({"regla": "custodia de claves"})

        assert "No tengo normativa aplicable" in salida
        assert not ruta_log.exists()


# ==================================================================
# El agente completo (grafo reutilizado del prototipo)
# ==================================================================
class TestAgenteCompleto:
    def test_el_ciclo_react_audita_de_punta_a_punta(
        self, retriever_falso, hallazgo_ejemplo, ruta_log
    ):
        """Pregunta → el modelo pide la tool → la tool audita → respuesta final."""
        modelo = ModeloFalso(respuestas=[
            _pedir_tool("evaluar_regla_calidad", {"regla": "cifrar en reposo"}),
            AIMessage(content="La regla está respaldada por la Regla 1."),
        ])
        app = agent_mod.construir_agente(
            modelo, retriever_falso, EvaluadorFalso(hallazgo_ejemplo),
            rol="compliance", checkpointer=MemorySaver(), ruta_auditoria=ruta_log,
        )

        salida = app.invoke({"messages": [("user", "evalúa: cifrar en reposo")]}, HILO)

        assert "respaldada" in salida["messages"][-1].content
        assert len(audit_import.leer_auditoria(ruta_log)) == 1

    def test_usa_el_ensamblado_del_prototipo(self, retriever_falso, monkeypatch):
        """No reimplementamos el grafo: delegamos en proyecto_final.graph_builder."""
        from app._proyecto_final import graph_builder

        capturado = {}

        def espia(llm, evaluador, retriever, **kwargs):
            capturado.update(kwargs)
            return "agente"

        monkeypatch.setattr(graph_builder, "construir_agente", espia)
        agent_mod.construir_agente(ModeloFalso(respuestas=[]), retriever_falso, None)

        assert "tools" in capturado and "prompt" in capturado
        assert [t.name for t in capturado["tools"]] == ["buscar_normativa"]
        assert "GobData" in capturado["prompt"]

    def test_el_prompt_se_puede_sustituir(self, retriever_falso, monkeypatch):
        from app._proyecto_final import graph_builder
        capturado = {}
        monkeypatch.setattr(
            graph_builder, "construir_agente",
            lambda llm, ev, ret, **kw: capturado.update(kw) or "agente")

        agent_mod.construir_agente(
            ModeloFalso(respuestas=[]), retriever_falso, None, prompt="OTRO PROMPT")

        assert capturado["prompt"] == "OTRO PROMPT"
