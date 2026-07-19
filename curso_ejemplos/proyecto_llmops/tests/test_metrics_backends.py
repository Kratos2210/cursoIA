"""
test_metrics_backends.py · El contrato que los dos backends deben cumplir
=========================================================================
Cierra L3: las métricas vivían en una lista dentro del proceso, así que un
reinicio las borraba y con N workers había N colectores que no se sumaban —
`/metrics` informaba de una fracción arbitraria del tráfico y el A/B de prompts
(ADR-0006) decidía sobre esos datos parciales.

⭐ LA FORMA DE ESTE ARCHIVO ES LO IMPORTANTE. `TestContratoBackend` está escrito
   contra la INTERFAZ, no contra una implementación, y recibe el backend por
   fixture. Hoy corre contra `EnMemoria`; el día que haya un Postgres levantado,
   los MISMOS tests corren contra la tabla real sin escribir una línea más
   (`PYTEST_PG_DSN=postgresql://... uv run pytest`). Un backend que pase estos
   tests es sustituible por el otro, que es justo lo que promete el Protocol.

⚠️ ESTADO HONESTO: sin `PYTEST_PG_DSN`, la clase de Postgres se SALTA (no pasa:
   se salta) y lo único verificado del backend real es que degrada sin tumbar el
   servicio. El upsert, el DDL y el SELECT contra una base de verdad siguen
   pendientes — el daemon de Docker no respondía cuando se escribió esto.
"""
import os

import pytest

from observability.cost_model import Uso
from observability.metrics import ColectorMetricas, MetricasRequest
from observability.metrics_backends import EnMemoria, Postgres

pytestmark = pytest.mark.offline

PG_DSN = os.environ.get("PYTEST_PG_DSN")


def metrica(modelo="gemini-2.0-flash", entrada=100, salida=50, latencia=120.0,
            ttft=None, cache_hit=False, acciones=()):
    return MetricasRequest(modelo=modelo, uso=Uso(entrada, salida),
                           latencia_ms=latencia, ttft_ms=ttft,
                           cache_hit=cache_hit, acciones_guardrail=acciones)


# ==================================================================
# El contrato · se aplica a CUALQUIER backend
# ==================================================================
class ContratoBackend:
    """Lo que promete `MetricasBackend`. Se hereda, no se corre directamente."""

    def test_lo_registrado_se_lee(self, backend):
        backend.registrar(metrica(entrada=10, salida=5))
        leidas = list(backend.leer())
        assert len(leidas) == 1
        assert (leidas[0].uso.entrada, leidas[0].uso.salida) == (10, 5)

    def test_conserva_todos_los_campos(self, backend):
        backend.registrar(metrica(modelo="qwen/qwen3-32b", latencia=250.5,
                                  ttft=80.25, cache_hit=True,
                                  acciones=("bloqueo_pii", "anonimizado")))
        (m,) = list(backend.leer())
        assert m.modelo == "qwen/qwen3-32b"
        assert m.latencia_ms == pytest.approx(250.5)
        assert m.ttft_ms == pytest.approx(80.25)
        assert m.cache_hit is True
        assert set(m.acciones_guardrail) == {"bloqueo_pii", "anonimizado"}

    def test_un_ttft_ausente_sigue_ausente(self, backend):
        # None significa "no hubo streaming". Convertirlo en 0.0 al persistir
        # metería un cero falso en el percentil de TTFT y lo hundiría.
        backend.registrar(metrica(ttft=None))
        assert list(backend.leer())[0].ttft_ms is None

    def test_registra_varias(self, backend):
        for i in range(5):
            backend.registrar(metrica(entrada=i))
        assert len(list(backend.leer())) == 5

    def test_el_limite_acota_la_lectura(self, backend):
        for i in range(10):
            backend.registrar(metrica(entrada=i))
        assert len(list(backend.leer(limite=3))) == 3

    def test_limpiar_deja_el_almacen_vacio(self, backend):
        backend.registrar(metrica())
        backend.limpiar()
        assert list(backend.leer()) == []

    def test_el_colector_agrega_sobre_el_backend(self, backend):
        # La integración que importa: los agregados del colector no saben (ni
        # deben saber) dónde están guardadas las métricas.
        colector = ColectorMetricas(backend=backend)
        colector.registrar(metrica(entrada=100, salida=50, cache_hit=False))
        colector.registrar(metrica(entrada=200, salida=80, cache_hit=True))

        assert colector.total_requests == 2
        assert colector.tokens_totales == Uso(300, 130)
        assert colector.tasa_cache == pytest.approx(0.5)


class TestEnMemoria(ContratoBackend):
    """El backend de siempre, ahora con contrato explícito."""

    @pytest.fixture
    def backend(self):
        return EnMemoria()


@pytest.mark.skipif(not PG_DSN, reason="sin PYTEST_PG_DSN: no hay Postgres al que conectarse")
class TestPostgres(ContratoBackend):
    """Los MISMOS tests contra la tabla real.

    Correr con:
        PYTEST_PG_DSN=postgresql://gobdata:gobdata@localhost:5433/gobdata \\
            uv run pytest proyecto_llmops/tests/test_metrics_backends.py
    """

    @pytest.fixture
    def backend(self):
        pg = Postgres(dsn=PG_DSN)
        pg.limpiar()            # cada test parte de una tabla vacía
        yield pg
        pg.limpiar()


# ==================================================================
# La degradación · esto SÍ se puede probar sin Postgres
# ==================================================================
class TestDegradacion:
    """Un fallo del sistema que OBSERVA no puede tumbar el sistema OBSERVADO."""

    def _backend_roto(self):
        def conectar_falla():
            raise ConnectionError("Postgres no está disponible")
        return Postgres(dsn="postgresql://noexiste", conectar=conectar_falla)

    def test_registrar_no_propaga_el_fallo(self):
        # ⭐ Perder una métrica es un mal día; devolverle un 500 al usuario
        #    porque no pudimos apuntar su latencia, no. Misma política que
        #    observability/tracing.py.
        self._backend_roto().registrar(metrica())    # no debe lanzar

    def test_leer_devuelve_vacio_en_vez_de_reventar(self):
        assert list(self._backend_roto().leer()) == []

    def test_el_endpoint_de_metricas_sigue_respondiendo(self):
        # Con la base caída, /metrics informa ceros — pero responde.
        colector = ColectorMetricas(backend=self._backend_roto())
        colector.registrar(metrica())
        resumen = colector.resumen()
        assert resumen["requests"] == 0
        assert resumen["costo_total"] == 0
