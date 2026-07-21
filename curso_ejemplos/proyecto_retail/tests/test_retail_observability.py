"""
test_retail_observability.py · Métricas y coste. Funciones puras, sin red.
"""
import pytest

from proyecto_retail.observability import cost_model, metrics
from proyecto_retail.observability.cost_model import Uso

pytestmark = pytest.mark.offline


class TestCosto:
    def test_salida_cuesta_mas_que_entrada(self):
        """La asimetría del cost_model: el mismo número de tokens de salida cuesta
        más que de entrada."""
        modelo = "openai/gpt-oss-120b"
        solo_entrada = cost_model.estimar_costo(Uso(entrada=1000, salida=0), modelo)
        solo_salida = cost_model.estimar_costo(Uso(entrada=0, salida=1000), modelo)
        assert solo_salida > solo_entrada

    def test_modelo_desconocido_cuesta_cero_no_revienta(self):
        assert cost_model.estimar_costo(Uso(entrada=100, salida=100), "modelo-fantasma") == 0.0

    def test_cache_hit_no_cuesta(self):
        m = metrics.MetricasRequest(modelo="openai/gpt-oss-120b", uso=Uso(entrada=100, salida=100),
                                    latencia_ms=1.0, cache_hit=True)
        assert m.costo == 0.0


class TestPercentil:
    def test_p95_no_promedia_el_peor_caso(self):
        """95 rápidas y 5 lentas: la media miente, el p95 muestra el dolor."""
        assert metrics.percentil([200, 200, 10000], 95) == 10000

    def test_lista_vacia_es_cero(self):
        assert metrics.percentil([], 95) == 0.0


class TestColector:
    def test_tasa_de_bloqueo_cuenta_los_guardrails(self):
        col = metrics.ColectorMetricas()
        col.registrar(metrics.MetricasRequest("m", Uso(), 1.0, acciones_guardrail=("bloqueo_inyeccion",)))
        col.registrar(metrics.MetricasRequest("m", Uso(), 1.0))
        assert col.tasa_bloqueo == pytest.approx(0.5)

    def test_resumen_trae_las_claves_esperadas(self):
        col = metrics.ColectorMetricas()
        col.registrar(metrics.MetricasRequest("openai/gpt-oss-120b", Uso(10, 20), 5.0, ttft_ms=2.0))
        r = col.resumen()
        assert {"requests", "costo_total", "latencia_p95_ms", "tasa_cache"} <= set(r)
