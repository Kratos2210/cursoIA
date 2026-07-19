"""
test_retail_intent.py · Extraer intención: reglas (fallback) y molde tipado (m05).
"""
import pytest

from proyecto_retail.app import intent
from proyecto_retail.app.intent import FiltrosCompra

pytestmark = pytest.mark.offline


class TestReglas:
    def test_presupuesto_menos_de(self):
        assert intent.extraer_filtros_regla("aretes por menos de 25 soles")["presupuesto"] == 25.0

    def test_presupuesto_hasta_con_simbolo(self):
        assert intent.extraer_filtros_regla("una cartera hasta S/80")["presupuesto"] == 80.0

    def test_sin_presupuesto_es_none(self):
        assert intent.extraer_filtros_regla("aretes dorados")["presupuesto"] is None

    def test_categoria_y_color(self):
        f = intent.extraer_filtros_regla("quiero aretes dorados")
        assert f["categoria"] == "aretes" and f["color"] == "dorado"

    def test_sinonimos_de_la_clienta(self):
        assert intent.extraer_filtros_regla("unos aros plateados")["categoria"] == "aretes"
        assert intent.extraer_filtros_regla("algo para el pelo")["categoria"] == "cabello"


class TestMoldeTipado:
    def test_a_dict_expone_la_misma_interfaz(self):
        f = FiltrosCompra(presupuesto=25.0, categoria="aretes", color="dorado")
        assert f.a_dict() == {"presupuesto": 25.0, "categoria": "aretes", "color": "dorado"}

    def test_extraer_filtros_llm_usa_structured_output(self, modelo_falso):
        """La vía LLM devuelve el MISMO dict que la de reglas."""
        llm = modelo_falso(filtros=FiltrosCompra(presupuesto=25.0, categoria="aretes", color="dorado"))
        assert intent.extraer_filtros_llm(llm, "algo lindo pa mi flaca") == {
            "presupuesto": 25.0, "categoria": "aretes", "color": "dorado"}
