"""
test_smoke_despliegue.py · El contenedor arrancado, visto desde fuera
=====================================================================
FINALIDAD:
  La capa que los 322 tests unitarios NO tienen. Todos ellos ejercitan el código
  con dobles: sin Docker, sin Postgres, sin el .env real. Y así fue como tres
  fallos (L7, L8, L9) pasaron la suite en verde y solo aparecieron al ARRANCAR
  EL CONTENEDOR de verdad. Todos eran configuración que únicamente se evalúa al
  desplegar: el código estaba bien, el valor que recibía no.

  Este smoke test cierra ese hueco por el único sitio por el que se puede: le
  pega por HTTP a un contenedor YA ARRANCADO y AFIRMA sobre lo que responde.

CÓMO SE CORRE (no en la CI offline: necesita el stack levantado):

    docker compose -f proyecto_llmops/docker-compose.yml --profile app up -d
    SMOKE_URL=http://localhost:8000 uv run pytest \\
        proyecto_llmops/tests/test_smoke_despliegue.py -v

  Sin `SMOKE_URL`, TODO el archivo se SALTA —igual que los tests de Postgres sin
  `PYTEST_PG_DSN`—: la suite normal no depende de que haya nada escuchando.

VARIABLES OPCIONALES:
    SMOKE_API_KEY       una credencial válida, si el despliegue tiene auth.
    SMOKE_EXPECT_TRACING  "1" o "0": afirma que /health dice la VERDAD sobre el
                          tracing (esto es exactamente lo que L8 mentía).
    SMOKE_CHAT          "1": ejercita /chat de punta a punta (gasta tokens y
                          exige una LLM_API_KEY real en el contenedor).

⚠️ EFECTO DE BORDE HONESTO: la prueba de /feedback ESCRIBE un voto con la
   variante "__smoke__", reconocible y filtrable. Es el precio de verificar que
   el camino de escritura (y su persistencia) vive de verdad en el contenedor.
"""
import os

import httpx
import pytest

pytestmark = pytest.mark.offline

SMOKE_URL = os.environ.get("SMOKE_URL")
SMOKE_API_KEY = os.environ.get("SMOKE_API_KEY")


@pytest.fixture
def cliente():
    if not SMOKE_URL:
        pytest.skip("sin SMOKE_URL: no hay contenedor al que pegarle")
    with httpx.Client(base_url=SMOKE_URL, timeout=15.0) as c:
        yield c


# ==================================================================
# 1 · /health — vivo Y sin mentir sobre su configuración
# ==================================================================
class TestHealth:
    def test_responde_ok_y_con_el_agente_listo(self, cliente):
        r = cliente.get("/health")
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["estado"] == "ok"
        # El lifespan construye los agentes ANTES de aceptar tráfico. Si esto
        # fuera False, el contenedor estaría "vivo" pero incapaz de responder.
        assert cuerpo["agente_listo"] is True
        assert cuerpo["modelo"]

    def test_tracing_y_auth_son_booleanos_reales(self, cliente):
        # No un string "true", no ausentes: booleanos. /health es lo que un
        # operador consulta para saber en qué modo corre el servicio.
        cuerpo = cliente.get("/health").json()
        assert isinstance(cuerpo["tracing"], bool)
        assert isinstance(cuerpo["auth_activa"], bool)

    def test_health_dice_la_verdad_sobre_el_tracing(self, cliente):
        # ⭐ L8 EN PERSONA: el contenedor arrancaba con llaves de mentira y
        #    /health anunciaba "tracing": true mientras las trazas se perdían.
        #    Si el despliegue declara qué esperar, lo afirmamos.
        esperado = os.environ.get("SMOKE_EXPECT_TRACING")
        if esperado is None:
            pytest.skip("define SMOKE_EXPECT_TRACING=1|0 para afirmar sobre el tracing")
        assert cliente.get("/health").json()["tracing"] is (esperado == "1")


# ==================================================================
# 2 · /metrics — coherente con lo que /health dice de la auth
# ==================================================================
class TestMetricasRespetaLaAuth:
    def test_metrics_exige_credencial_si_health_dice_que_hay_auth(self, cliente):
        # ⭐ Cruce de coherencia: si /health dice auth_activa=true, /metrics DEBE
        #    rechazar sin credencial. Un /health que dice una cosa y un /metrics
        #    que hace otra es la misma clase de mentira que L8.
        hay_auth = cliente.get("/health").json()["auth_activa"]
        r = cliente.get("/metrics")
        if hay_auth:
            assert r.status_code in (401, 403)
        else:
            assert r.status_code == 200

    def test_metrics_responde_con_credencial(self, cliente):
        if not SMOKE_API_KEY:
            pytest.skip("sin SMOKE_API_KEY: no se puede consultar /metrics protegido")
        r = cliente.get("/metrics", headers={"X-API-Key": SMOKE_API_KEY})
        assert r.status_code == 200
        cuerpo = r.json()
        # Las claves que el resumen SIEMPRE trae (las fijan los tests unitarios).
        for clave in ("requests", "costo_total", "latencia_p95_ms"):
            assert clave in cuerpo


# ==================================================================
# 3 · /feedback — el camino de escritura vive y PERSISTE en el contenedor
# ==================================================================
class TestFeedbackRoundTrip:
    def test_un_voto_escrito_se_lee_de_vuelta(self, cliente):
        # ⭐ Esto habría cazado un L9 del feedback: si el backend no persistiera
        #    (o cada worker guardara lo suyo), el voto no volvería en el GET. El
        #    round-trip completo —POST y luego GET— viaja por el Postgres del
        #    contenedor, no por una lista en RAM de un proceso de test.
        antes = cliente.get("/feedback")
        assert antes.status_code == 200
        conteo_antes = antes.json().get("__smoke__", {}).get("util", 0)

        r = cliente.post("/feedback", json={"util": True, "variante": "__smoke__",
                                            "comentario": "smoke test de despliegue"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        despues = cliente.get("/feedback").json()
        assert despues["__smoke__"]["util"] == conteo_antes + 1


# ==================================================================
# 4 · /chat — el pipeline entero, solo si se pide (gasta tokens)
# ==================================================================
class TestChatOpcional:
    def test_el_stream_llega_hasta_el_evento_fin(self, cliente):
        if os.environ.get("SMOKE_CHAT") != "1":
            pytest.skip("define SMOKE_CHAT=1 para ejercitar /chat (gasta tokens)")
        headers = {"X-API-Key": SMOKE_API_KEY} if SMOKE_API_KEY else {}
        cuerpo = {"mensaje": "¿Cuántos años se conservan los registros?",
                  "rol": "analyst", "thread_id": "smoke-chat"}
        eventos = []
        with cliente.stream("POST", "/chat", json=cuerpo, headers=headers) as r:
            assert r.status_code == 200
            for linea in r.iter_lines():
                if linea.startswith("event: "):
                    eventos.append(linea[len("event: "):])
        # El pipeline llegó al final (o bloqueó a propósito), no se cayó a mitad.
        assert "fin" in eventos or "bloqueado" in eventos
        assert "error" not in eventos
