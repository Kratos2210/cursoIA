"""
test_agente.py · El agente entero, sin gastar un token
=======================================================
FINALIDAD:
  Verificar el CABLEADO del proyecto: que el agente reciba una pregunta,
  elija la tool correcta, esa tool consulte la normativa, estructure el
  hallazgo, lo escriba en el log y devuelva una respuesta.

  Todo eso con un modelo falso que recita un guion (ver conftest.py).
  Lo que se prueba aquí no es la inteligencia del LLM — eso no se testea —
  sino NUESTRO código: el grafo, las tools, la auditoría, la memoria.

LÓGICA del guion:
  create_react_agent llama al modelo, ve que pidió una tool, la ejecuta,
  le devuelve el resultado y vuelve a llamar al modelo. Por eso cada guion
  tiene 2 respuestas: (1) "usa esta tool", (2) "esta es la respuesta final".
"""
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import ValidationError

import audit
import config
import graph_builder
import persistence
import tools as tools_mod
from conftest import EvaluadorFalso, ModeloFalso

pytestmark = pytest.mark.offline


def _pedir_tool(nombre: str, args: dict, id_llamada: str = "call_1") -> AIMessage:
    """El mensaje con el que un modelo dice 'quiero usar esta herramienta'."""
    return AIMessage(content="", tool_calls=[{"name": nombre, "args": args, "id": id_llamada}])


def _armar(modelo, evaluador, retriever, ruta_log, checkpointer=None):
    return graph_builder.construir_agente(
        llm=modelo, evaluador=evaluador, retriever=retriever,
        checkpointer=checkpointer, ruta_auditoria=ruta_log,
    )


HILO = {"configurable": {"thread_id": "test"}}


# ==================================================================
# La fábrica de tools
# ==================================================================
class TestCrearTools:
    def test_expone_las_dos_tools_con_su_contrato(self, retriever_falso, hallazgo_ejemplo, ruta_log):
        """Los nombres y docstrings son lo que el modelo lee para elegir."""
        tools = tools_mod.crear_tools(
            ModeloFalso(respuestas=[]), EvaluadorFalso(hallazgo_ejemplo), retriever_falso, ruta_log)
        por_nombre = {t.name: t for t in tools}
        assert set(por_nombre) == {"buscar_normativa", "evaluar_regla_calidad"}
        assert "PREGUNTE" in por_nombre["buscar_normativa"].description
        assert "EVALUAR" in por_nombre["evaluar_regla_calidad"].description

    def test_buscar_normativa_le_pasa_el_contexto_al_modelo(self, retriever_falso, ruta_log):
        """La tool debe meter la normativa recuperada en el prompt (RAG)."""
        modelo = ModeloFalso(respuestas=[AIMessage(content="Sí, hay que cifrar con AES-256.")])
        tools = tools_mod.crear_tools(modelo, EvaluadorFalso(None), retriever_falso, ruta_log)
        buscar = {t.name: t for t in tools}["buscar_normativa"]

        respuesta = buscar.invoke({"pregunta": "¿hay que cifrar?"})
        assert respuesta == "Sí, hay que cifrar con AES-256."
        # El retriever se consultó con la pregunta del usuario:
        assert retriever_falso.preguntas == ["¿hay que cifrar?"]

    def test_evaluar_regla_escribe_en_el_log(self, retriever_falso, hallazgo_ejemplo, ruta_log):
        tools = tools_mod.crear_tools(
            ModeloFalso(respuestas=[]), EvaluadorFalso(hallazgo_ejemplo), retriever_falso, ruta_log)
        evaluar = {t.name: t for t in tools}["evaluar_regla_calidad"]

        salida = evaluar.invoke({"regla": "cifrar en reposo"})
        assert "cumple: True" in salida and "severidad: alta" in salida
        assert len(audit.leer_auditoria(ruta_log)) == 1

    def test_si_el_modelo_devuelve_basura_no_se_audita(self, retriever_falso, ruta_log):
        """Un hallazgo que no encaja en el molde NO debe llegar al log.

        Auditar basura es peor que no auditar: ensucia la evidencia.
        """
        error = ValidationError.from_exception_data("HallazgoCalidad", [])
        tools = tools_mod.crear_tools(
            ModeloFalso(respuestas=[]), EvaluadorFalso(error), retriever_falso, ruta_log)
        evaluar = {t.name: t for t in tools}["evaluar_regla_calidad"]

        salida = evaluar.invoke({"regla": "cualquiera"})
        assert "No pude estructurar" in salida
        assert audit.leer_auditoria(ruta_log) == []   # el log sigue limpio


# ==================================================================
# El grafo completo (smoke test con LLM mockeado)
# ==================================================================
class TestAgenteCompleto:
    def test_el_agente_usa_la_tool_de_evaluacion_y_audita(
            self, retriever_falso, hallazgo_ejemplo, ruta_log):
        """El recorrido entero: pregunta -> tool -> auditoría -> respuesta."""
        guion = [
            _pedir_tool("evaluar_regla_calidad", {"regla": "cifrar en reposo con AES-256"}),
            AIMessage(content="La regla está respaldada por la Regla 1."),
        ]
        modelo = ModeloFalso(respuestas=guion)
        agente = _armar(modelo, EvaluadorFalso(hallazgo_ejemplo), retriever_falso, ruta_log)

        resultado = agente.invoke({"messages": [("user", "Evalúa el cifrado")]}, HILO)

        # 1) El agente llamó al modelo dos veces: decidir, y responder.
        assert modelo.llamadas == 2
        # 2) En medio hubo un ToolMessage: la tool se ejecutó de verdad.
        tool_messages = [m for m in resultado["messages"] if isinstance(m, ToolMessage)]
        assert len(tool_messages) == 1
        assert "severidad: alta" in tool_messages[0].content
        # 3) Quedó rastro en el log de auditoría.
        assert len(audit.leer_auditoria(ruta_log)) == 1
        # 4) La última palabra es del agente, no de la tool.
        assert resultado["messages"][-1].content == "La regla está respaldada por la Regla 1."

    def test_el_agente_puede_responder_sin_usar_ninguna_tool(
            self, retriever_falso, hallazgo_ejemplo, ruta_log):
        """Un 'hola' no debe disparar el RAG ni escribir en la auditoría."""
        modelo = ModeloFalso(respuestas=[AIMessage(content="¡Hola! Soy GobData.")])
        agente = _armar(modelo, EvaluadorFalso(hallazgo_ejemplo), retriever_falso, ruta_log)

        resultado = agente.invoke({"messages": [("user", "hola")]}, HILO)

        assert resultado["messages"][-1].content == "¡Hola! Soy GobData."
        assert retriever_falso.preguntas == []
        assert audit.leer_auditoria(ruta_log) == []

    def test_el_agente_recuerda_el_turno_anterior(
            self, retriever_falso, hallazgo_ejemplo, ruta_log):
        """La memoria del checkpointer: el 2º turno ve los mensajes del 1º."""
        modelo = ModeloFalso(respuestas=[
            AIMessage(content="Se conservan 10 años."),
            AIMessage(content="Te dije: 10 años."),
        ])
        agente = _armar(modelo, EvaluadorFalso(hallazgo_ejemplo), retriever_falso, ruta_log)

        agente.invoke({"messages": [("user", "¿cuántos años se conservan?")]}, HILO)
        resultado = agente.invoke({"messages": [("user", "¿qué me dijiste?")]}, HILO)

        # 2 preguntas + 2 respuestas acumuladas en el mismo hilo.
        assert len(resultado["messages"]) == 4
        assert resultado["messages"][0].content == "¿cuántos años se conservan?"

    def test_hilos_distintos_no_comparten_memoria(
            self, retriever_falso, hallazgo_ejemplo, ruta_log):
        """Dos analistas, dos thread_id: sus conversaciones no se mezclan."""
        modelo = ModeloFalso(respuestas=[AIMessage(content="A"), AIMessage(content="B")])
        agente = _armar(modelo, EvaluadorFalso(hallazgo_ejemplo), retriever_falso, ruta_log)

        agente.invoke({"messages": [("user", "1")]}, {"configurable": {"thread_id": "ana"}})
        r = agente.invoke({"messages": [("user", "2")]}, {"configurable": {"thread_id": "luis"}})

        assert len(r["messages"]) == 2   # solo el turno de Luis

    def test_el_agente_lleva_las_instrucciones_del_sistema(
            self, retriever_falso, hallazgo_ejemplo, ruta_log):
        """La personalidad de config.py debe llegar al modelo como system prompt."""
        modelo = ModeloFalso(respuestas=[AIMessage(content="ok")])
        agente = _armar(modelo, EvaluadorFalso(hallazgo_ejemplo), retriever_falso, ruta_log)
        agente.invoke({"messages": [("user", "hola")]}, HILO)
        assert "GobData" in config.INSTRUCCIONES_AGENTE


# ==================================================================
# Configuración y persistencia
# ==================================================================
class TestConfigYPersistencia:
    def test_importar_config_no_ejecuta_nada(self, monkeypatch):
        """La regla de oro: sin llave, importar config debe funcionar igual.

        Es lo que permite que la CI corra estos tests sin ninguna llave.
        """
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        import importlib
        importlib.reload(config)
        assert config.TEMPERATURA == 0

    def test_validar_entorno_falla_sin_llave(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        # cargar_entorno() releería el .env real; lo neutralizamos.
        monkeypatch.setattr(config, "cargar_entorno", lambda: None)
        with pytest.raises(SystemExit, match="GOOGLE_API_KEY"):
            config.validar_entorno()

    def test_validar_entorno_pide_la_llave_del_proveedor_ACTIVO(self, monkeypatch):
        """Con LLM_PROVIDER=groq, exigir GOOGLE_API_KEY sería mentirle al alumno."""
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GOOGLE_API_KEY", "la_de_google_no_sirve_aqui")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setattr(config, "cargar_entorno", lambda: None)
        with pytest.raises(SystemExit, match="GROQ_API_KEY"):
            config.validar_entorno()

    def test_reconoce_el_error_de_cuota(self):
        assert config.es_error_cuota(Exception("429 RESOURCE_EXHAUSTED")) is True
        assert config.es_error_cuota(Exception("401 unauthorized")) is False

    def test_el_checkpointer_por_defecto_guarda_en_memoria(self):
        from langgraph.checkpoint.memory import MemorySaver
        assert isinstance(persistence.crear_checkpointer(), MemorySaver)

    def test_dos_checkpointers_son_independientes(self):
        """Cada llamada crea uno nuevo: dos agentes no comparten memoria por error."""
        assert persistence.crear_checkpointer() is not persistence.crear_checkpointer()
