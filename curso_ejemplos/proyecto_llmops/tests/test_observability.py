"""
test_observability.py · Coste, latencia y el tracing que no debe estorbar
=========================================================================
Sin Langfuse levantado, sin llaves y sin red. Dos cosas se prueban aquí:

  1) Que las cuentas (tokens → dólares, p50/p95) sean correctas.
  2) Que el tracing **degrade**: sin llaves, `observar()` devuelve la función
     intacta y `callbacks()` devuelve []. Un observador que tumba lo observado
     no es observabilidad.
"""
import pytest

from observability import cost_model, metrics, tracing
from observability.cost_model import Uso

pytestmark = pytest.mark.offline


class RespuestaConUso:
    """Imita un AIMessage de LangChain: solo lo que cost_model mira."""
    def __init__(self, entrada, salida):
        self.usage_metadata = {
            "input_tokens": entrada,
            "output_tokens": salida,
            "total_tokens": entrada + salida,
        }


# ==================================================================
# COST MODEL
# ==================================================================
class TestExtraerUso:
    def test_lee_usage_metadata(self):
        uso = cost_model.extraer_uso(RespuestaConUso(100, 50))
        assert (uso.entrada, uso.salida, uso.total) == (100, 50, 150)

    def test_sin_usage_metadata_devuelve_ceros(self):
        # Pasa de verdad en streaming: un 0 significa "no sé", no "fue gratis".
        assert cost_model.extraer_uso(object()) == Uso(0, 0)


class TestEstimarCosto:
    def test_calcula_por_millon_de_tokens(self):
        # 1M de entrada a $0.10 + 1M de salida a $0.40 = $0.50
        costo = cost_model.estimar_costo(Uso(1_000_000, 1_000_000), "gemini-2.0-flash")
        assert costo == pytest.approx(0.50)

    def test_la_salida_cuesta_mas_que_la_entrada(self):
        # ⭐ La asimetría que hay que interiorizar: lo caro es responder largo,
        #    no leer un contexto largo.
        solo_entrada = cost_model.estimar_costo(Uso(1000, 0), "gemini-2.0-flash")
        solo_salida = cost_model.estimar_costo(Uso(0, 1000), "gemini-2.0-flash")
        assert solo_salida > solo_entrada

    def test_modelo_desconocido_cuesta_cero_y_no_revienta(self):
        assert cost_model.estimar_costo(Uso(1000, 1000), "modelo-inventado-9000") == 0.0

    def test_un_modelo_local_es_gratis(self):
        assert cost_model.estimar_costo(Uso(9999, 9999), "qwen3:8b") == 0.0


class TestFormatearCosto:
    def test_los_costes_diminutos_no_se_redondean_a_cero(self):
        assert cost_model.formatear_costo(0.000018) == "$0.000018"

    def test_cero_lo_dice_explicitamente(self):
        assert "sin datos" in cost_model.formatear_costo(0)


class TestProyectarMensual:
    def test_el_numero_que_se_lleva_a_presupuesto(self):
        # $0.0002 por request no asusta; $300/mes sí. Es la misma cifra.
        assert cost_model.proyectar_mensual(0.0002, 50_000) == pytest.approx(300.0)


# ==================================================================
# MÉTRICAS
# ==================================================================
class TestPercentil:
    def test_el_p95_no_promedia_el_peor_caso(self):
        # ⭐ La media de [200,200,10000] dice 3466ms ("va bien"). El p95 dice
        #    10000ms, que es lo que sufre 1 de cada 20 usuarios.
        assert metrics.percentil([200, 200, 10000], 95) == 10000

    def test_el_p50_es_la_mediana(self):
        assert metrics.percentil([200, 200, 10000], 50) == 200

    def test_lista_vacia_no_revienta(self):
        assert metrics.percentil([], 95) == 0.0


class TestCronometro:
    def test_mide_latencia(self):
        with metrics.Cronometro() as crono:
            pass
        assert crono.latencia_ms >= 0

    def test_sin_primer_token_el_ttft_es_None(self):
        with metrics.Cronometro() as crono:
            pass
        assert crono.ttft_ms is None

    def test_el_ttft_solo_cuenta_la_primera_llamada(self):
        with metrics.Cronometro() as crono:
            crono.primer_token()
            primero = crono.ttft_ms
            crono.primer_token()          # idempotente
        assert crono.ttft_ms == primero

    def test_el_ttft_es_menor_que_la_latencia_total(self):
        with metrics.Cronometro() as crono:
            crono.primer_token()
            sum(range(100_000))           # trabajo posterior al primer token
        assert crono.ttft_ms < crono.latencia_ms

    def test_una_request_que_falla_tambien_se_mide(self):
        # __exit__ no silencia la excepción, pero sí cierra el reloj.
        crono = metrics.Cronometro()
        with pytest.raises(ValueError):
            with crono:
                raise ValueError("boom")
        assert crono.latencia_ms >= 0


class TestMetricasRequest:
    def test_un_cache_hit_cuesta_cero(self):
        # Aunque el registro traiga tokens: no se llamó al modelo.
        m = metrics.MetricasRequest(
            modelo="gemini-2.0-flash", uso=Uso(1_000_000, 1_000_000),
            latencia_ms=5, cache_hit=True,
        )
        assert m.costo == 0.0

    def test_avisa_de_un_modelo_fuera_de_la_tabla(self):
        m = metrics.MetricasRequest(modelo="gpt-nuevo", uso=Uso(10, 10), latencia_ms=1)
        assert m.modelo_desconocido is True
        assert m.costo == 0.0        # y por eso el 0.0 no significa "gratis"


class TestColector:
    @pytest.fixture
    def colector(self):
        c = metrics.ColectorMetricas()
        c.registrar(metrics.MetricasRequest("gemini-2.0-flash", Uso(1000, 500), 200, ttft_ms=50))
        c.registrar(metrics.MetricasRequest("gemini-2.0-flash", Uso(0, 0), 5, cache_hit=True))
        c.registrar(metrics.MetricasRequest(
            "gemini-2.0-flash", Uso(0, 0), 3,
            acciones_guardrail=("bloqueo_inyeccion",),
        ))
        return c

    def test_suma_los_tokens(self, colector):
        assert colector.tokens_totales == Uso(1000, 500)

    def test_la_tasa_de_cache(self, colector):
        assert colector.tasa_cache == pytest.approx(1 / 3)

    def test_la_tasa_de_bloqueo_solo_cuenta_bloqueos(self, colector):
        # 'pii_anonimizada' sanea, no bloquea: no debe contar aquí.
        colector.registrar(metrics.MetricasRequest(
            "gemini-2.0-flash", Uso(10, 10), 100, acciones_guardrail=("pii_anonimizada",),
        ))
        assert colector.tasa_bloqueo == pytest.approx(1 / 4)

    def test_el_ttft_ignora_las_requests_sin_streaming(self, colector):
        # Solo una midió TTFT (50ms). Contar las otras como 0 mentiría a la baja.
        assert colector.ttft(95) == 50

    def test_el_resumen_trae_lo_que_va_al_dashboard(self, colector):
        resumen = colector.resumen()
        assert resumen["requests"] == 3
        assert resumen["tokens_salida"] == 500
        assert resumen["latencia_p95_ms"] == 200.0

    def test_un_colector_vacio_no_divide_por_cero(self):
        vacio = metrics.ColectorMetricas()
        assert vacio.resumen()["tasa_cache"] == 0.0
        assert vacio.costo_total == 0.0


# ==================================================================
# TRACING · la degradación graceful
# ==================================================================
class TestTracingDegrada:
    """Sin llaves de Langfuse, nada de esto debe estorbar ni fallar."""

    def test_sin_llaves_no_esta_activo(self, monkeypatch):
        monkeypatch.setattr(tracing.settings, "langfuse_public_key", "", raising=False)
        monkeypatch.setattr(tracing.settings, "langfuse_secret_key", "", raising=False)
        assert tracing.activo() is False

    def test_hacen_falta_LAS_DOS_llaves(self, monkeypatch):
        # Con una sola, el SDK fallaría al autenticarse en cada request.
        monkeypatch.setattr(tracing.settings, "langfuse_public_key", "pk-123", raising=False)
        monkeypatch.setattr(tracing.settings, "langfuse_secret_key", "", raising=False)
        assert tracing.activo() is False

    def test_sin_tracing_los_callbacks_son_lista_vacia(self, monkeypatch):
        monkeypatch.setattr(tracing, "activo", lambda: False)
        assert tracing.callbacks() == []

    def test_sin_tracing_el_decorador_devuelve_la_funcion_intacta(self, monkeypatch):
        # ⭐ No un wrapper que no hace nada: la función MISMA. Sin coste.
        monkeypatch.setattr(tracing, "activo", lambda: False)

        def recuperar():
            return "ok"

        assert tracing.observar("span")(recuperar) is recuperar

    def test_registrar_uso_sin_tracing_no_falla(self, monkeypatch):
        monkeypatch.setattr(tracing, "activo", lambda: False)
        m = metrics.MetricasRequest("gemini-2.0-flash", Uso(1, 1), 1)
        tracing.registrar_uso("chat", m)     # no debe lanzar

    def test_vaciar_sin_tracing_no_falla(self, monkeypatch):
        monkeypatch.setattr(tracing, "activo", lambda: False)
        tracing.vaciar()
