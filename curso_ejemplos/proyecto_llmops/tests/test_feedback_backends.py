"""
test_feedback_backends.py · El contrato que los dos backends de voto cumplen
============================================================================
El gemelo de `test_metrics_backends.py`, para el otro extremo del A/B. Los votos
👍/👎 vivían en una lista dentro del proceso: un reinicio los borraba y con N
workers había N colectores que no se sumaban, así que `/feedback` decidía el
ganador del experimento (ADR-0006) sobre una fracción del tráfico.

⭐ MISMA FORMA QUE EL DE MÉTRICAS, Y A PROPÓSITO. `ContratoBackend` se escribe
   contra la INTERFAZ y recibe el backend por fixture: hoy corre contra
   `EnMemoria`; con un Postgres levantado, los MISMOS tests corren contra la
   tabla real sin una línea más (`PYTEST_PG_DSN=postgresql://... uv run pytest`).

⚠️ Sin `PYTEST_PG_DSN`, la clase de Postgres se SALTA (no pasa: se salta). Lo
   único verificado del backend real sin base es que degrada sin tumbar el
   servicio.
"""
import os

import pytest

from observability.feedback import ColectorFeedback, Voto
from observability.feedback_backends import EnMemoria, Postgres

pytestmark = pytest.mark.offline

PG_DSN = os.environ.get("PYTEST_PG_DSN")


def voto(variante="A", util=True, thread_id="demo", comentario=None):
    return Voto(variante=variante, util=util, thread_id=thread_id,
                comentario=comentario)


# ==================================================================
# El contrato · se aplica a CUALQUIER backend
# ==================================================================
class ContratoBackend:
    """Lo que promete `FeedbackBackend`. Se hereda, no se corre directamente."""

    def test_lo_registrado_se_lee(self, backend):
        backend.registrar(voto(variante="B", util=False))
        (v,) = list(backend.leer())
        assert v.variante == "B"
        assert v.util is False

    def test_conserva_todos_los_campos(self, backend):
        backend.registrar(voto(variante="agente_gobdata_conciso", util=True,
                               thread_id="hilo-9", comentario="clarísimo"))
        (v,) = list(backend.leer())
        assert v.variante == "agente_gobdata_conciso"
        assert v.util is True
        assert v.thread_id == "hilo-9"
        assert v.comentario == "clarísimo"

    def test_un_comentario_ausente_sigue_ausente(self, backend):
        backend.registrar(voto(comentario=None))
        assert list(backend.leer())[0].comentario is None

    def test_registra_varios(self, backend):
        for i in range(5):
            backend.registrar(voto(thread_id=f"h{i}"))
        assert len(list(backend.leer())) == 5

    def test_el_limite_acota_la_lectura(self, backend):
        for i in range(10):
            backend.registrar(voto(thread_id=f"h{i}"))
        assert len(list(backend.leer(limite=3))) == 3

    def test_limpiar_deja_el_almacen_vacio(self, backend):
        backend.registrar(voto())
        backend.limpiar()
        assert list(backend.leer()) == []

    def test_el_colector_agrega_sobre_el_backend(self, backend):
        # La integración que importa: la tasa por variante del colector no sabe
        # (ni debe saber) dónde están guardados los votos.
        colector = ColectorFeedback(backend=backend)
        colector.registrar(variante="A", util=True)
        colector.registrar(variante="A", util=True)
        colector.registrar(variante="A", util=False)
        colector.registrar(variante="B", util=True)

        resumen = colector.resumen()
        assert resumen["A"]["total"] == 3
        assert resumen["A"]["tasa_aprobacion"] == pytest.approx(0.667, abs=0.001)
        assert resumen["B"]["tasa_aprobacion"] == pytest.approx(1.0)


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
            uv run pytest proyecto_llmops/tests/test_feedback_backends.py
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
        # ⭐ Perder un voto es un mal día; devolverle un 500 a quien solo quería
        #    pulsar 👍, no. Misma política que observability/tracing.py.
        self._backend_roto().registrar(voto())    # no debe lanzar

    def test_leer_devuelve_vacio_en_vez_de_reventar(self):
        assert list(self._backend_roto().leer()) == []

    def test_el_endpoint_de_feedback_sigue_respondiendo(self):
        # Con la base caída, /feedback informa un resumen vacío — pero responde.
        colector = ColectorFeedback(backend=self._backend_roto())
        colector.registrar(variante="A", util=True)
        assert colector.resumen() == {}
