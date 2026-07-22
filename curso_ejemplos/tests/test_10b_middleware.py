"""
test_10b_middleware.py · El middleware de agentes, sin gastar un token
======================================================================
FINALIDAD:
  Verificar NUESTRO código del TEMA 10b: que el middleware propio
  (GuardaDeContexto) observe sin romper nada, y que construir el agente con los
  tres middleware enchufados compile de verdad. Nada de esto llama a la API:
  usamos un modelo falso para el armado y probamos el hook en aislamiento.
"""
import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

pytestmark = pytest.mark.offline


@pytest.fixture(scope="module")
def m10b(importar_ejemplo):
    return importar_ejemplo("10b_middleware")


class TestGuardaDeContexto:
    """El middleware propio: un hook before_model que solo observa."""

    def test_before_model_cuenta_las_llamadas_y_los_mensajes(self, m10b):
        guarda = m10b.GuardaDeContexto()
        # Primera "vuelta": el modelo vería 1 mensaje.
        assert guarda.before_model({"messages": [("user", "hola")]}, None) is None
        # Segunda "vuelta": ahora 3 mensajes.
        guarda.before_model({"messages": [("user", "a"), ("ai", "b"), ("user", "c")]}, None)
        assert guarda.llamadas_al_modelo == 2
        assert guarda.max_mensajes_vistos == 3

    def test_es_un_AgentMiddleware(self, m10b):
        from langchain.agents.middleware import AgentMiddleware
        assert isinstance(m10b.GuardaDeContexto(), AgentMiddleware)

    def test_observar_no_muta_el_estado(self, m10b):
        # Devolver None es el contrato de "no toques el estado"; un dict lo mutaría.
        guarda = m10b.GuardaDeContexto()
        assert guarda.before_model({"messages": []}, None) is None


class TestConstruccionDelAgente:
    """El agente se arma con los tres middleware SIN llamar a la API."""

    def _fake(self):
        # Un modelo falso: construir el agente no lo invoca, así que no gasta cuota.
        return GenericFakeChatModel(messages=iter([]))

    def test_construir_agente_compila_un_grafo(self, m10b):
        agente = m10b.construir_agente_con_middleware(self._fake())
        # create_agent devuelve un grafo de LangGraph ya compilado.
        assert type(agente).__name__ == "CompiledStateGraph"

    def test_acepta_una_guarda_inyectada(self, m10b):
        guarda = m10b.GuardaDeContexto()
        agente = m10b.construir_agente_con_middleware(self._fake(), guarda)
        assert type(agente).__name__ == "CompiledStateGraph"
        # Es la MISMA instancia que le pasamos (para poder leer sus contadores).
        assert guarda.llamadas_al_modelo == 0   # aún no ha corrido ninguna vuelta

    def test_la_tool_de_envio_responde_offline(self, m10b):
        # La tool no necesita modelo ni red. Es un StructuredTool (@tool), así que
        # se ejecuta con .invoke({...}), no llamándola directamente.
        assert "S/ 10" in m10b.calcular_envio.invoke({"ciudad": "Lima"})
        assert "estándar" in m10b.calcular_envio.invoke({"ciudad": "Cusco"})
