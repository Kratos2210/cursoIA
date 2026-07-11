"""
test_retail_agent.py · El lazo completo con un ModeloFalso: redactar → verificar
→ reintento → fallback. Sin cuota, sin red.
"""
import pytest

from proyecto_retail.app import agent, intent
from proyecto_retail.app.intent import FiltrosCompra

pytestmark = pytest.mark.offline

# Extraer con reglas evita depender del LLM para los filtros: aislamos el lazo
# de redacción/grounding, que es lo que este archivo prueba.
_REGLA = lambda _llm, peticion: intent.extraer_filtros_regla(peticion)


def test_respuesta_fiel_pasa_tal_cual(catalogo, modelo_falso):
    """Si el LLM redacta con un precio del catálogo, esa respuesta se sirve."""
    llm = modelo_falso(redacciones="Te va a encantar: Aretes Argolla Mediana Dorado a S/19.90 (SKU AR-001).")
    r = agent.responder_con_guardrail(llm, "aretes dorados por menos de 25 soles",
                                      catalogo, extraer=_REGLA)
    assert "S/19.90" in r.texto
    assert r.acciones == ()


def test_precio_inventado_reintenta_y_se_recupera(catalogo, modelo_falso):
    """1ª redacción inventa S/99.90 → guardrail salta → 2ª redacción correcta."""
    llm = modelo_falso(redacciones=[
        "Llévate esto a S/99.90, una ganga.",                       # inventado
        "Mejor: Aretes Argolla Mediana Dorado a S/19.90 (SKU AR-001).",  # fiel
    ])
    r = agent.responder_con_guardrail(llm, "aretes dorados por menos de 25 soles",
                                      catalogo, extraer=_REGLA)
    assert "S/19.90" in r.texto and "S/99.90" not in r.texto
    assert "reintento_grounding" in r.acciones


def test_si_el_modelo_insiste_gana_el_fallback_determinista(catalogo, modelo_falso):
    """Dos redacciones inventadas → se sirve la plantilla determinista, fiel."""
    llm = modelo_falso(redacciones=["A S/99.90", "A S/88.80"])
    r = agent.responder_con_guardrail(llm, "aretes dorados por menos de 25 soles",
                                      catalogo, extraer=_REGLA)
    from proyecto_retail.guardrails.price_guard import respuesta_es_fiel
    assert respuesta_es_fiel(r.texto, r.productos) is True          # NUNCA sale infiel
    assert "fallback_determinista" in r.acciones


def test_sin_resultados_responde_honesto_sin_llamar_a_redactar(catalogo, modelo_falso):
    """Si nada cumple, ni se redacta: la honestidad determinista basta."""
    llm = modelo_falso(redacciones="esto no debería usarse")
    r = agent.responder_con_guardrail(llm, "un collar de zircón por menos de 10 soles",
                                      catalogo, extraer=_REGLA)
    assert r.productos == []
    assert "no encontré" in r.texto.lower()
    assert llm.invocaciones == []                                   # el LLM no se llamó a redactar


def test_agente_compras_es_compatible_con_el_eval(catalogo, modelo_falso):
    """El closure devuelve (productos, texto), la forma que espera el eval."""
    llm = modelo_falso(redacciones="Aretes Argolla Mediana Dorado a S/19.90 (SKU AR-001).")
    responder = agent.agente_compras(llm, extraer=_REGLA)
    productos, texto = responder("aretes dorados por menos de 25 soles", catalogo)
    assert isinstance(productos, list) and "S/19.90" in texto
