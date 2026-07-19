"""
test_retail_auth.py · Que no cualquiera gaste tu cuota
=======================================================
El agujero que cierra `app/auth.py` era este:

    while true; do curl -X POST .../chat -d '{"mensaje":"hola"}'; done

y el servidor contestaba a todo el mundo, pagando cada token. Y `/metrics`
publicaba de paso cuánto tráfico manejas y cuánto te cuesta.

Aquí se prueban las dos mitades:
  1) Con credenciales configuradas, sin clave válida no se entra.
  2) Sin credenciales (el modo del curso), todo sigue funcionando como antes —
     porque romper la ejecutabilidad del material no era una opción.

⚠️ Este módulo NO prueba roles, y no es un olvido: retail no los tiene. El
   catálogo es público (está en sifrah.com/products.json), así que solo hay
   autenticación. El equivalente con RBAC es proyecto_llmops/tests/test_auth.py.
"""
import pytest
from fastapi.testclient import TestClient

from proyecto_retail.app import auth
from proyecto_retail.app.config import settings
from proyecto_retail.app.embeddings import EmbeddingsBolsa
from proyecto_retail.app.main import crear_app
from proyecto_retail.cache.cache_backends import InMemoryCache
from proyecto_retail.cache.semantic_cache import SemanticCache
from proyecto_retail.tests.test_retail_api import ResponderFalso

pytestmark = pytest.mark.offline

CLAVES = "clave-de-la-web,clave-del-bot"


@pytest.fixture
def con_auth(monkeypatch):
    """Servicio con dos credenciales configuradas."""
    monkeypatch.setattr(settings, "api_keys", CLAVES)


@pytest.fixture
def sin_auth(monkeypatch):
    """Servicio abierto: el modo en el que se estudia el curso."""
    monkeypatch.setattr(settings, "api_keys", "")


@pytest.fixture
def cliente():
    app = crear_app(responder=ResponderFalso(), catalogo=[],
                    cache=SemanticCache(EmbeddingsBolsa(), InMemoryCache()))
    with TestClient(app) as c:
        yield c


# ==================================================================
# El parseo de API_KEYS
# ==================================================================
class TestParseo:
    def test_lee_varias_credenciales(self, con_auth):
        assert auth.claves_configuradas() == ["clave-de-la-web", "clave-del-bot"]

    def test_los_espacios_no_cuentan(self, monkeypatch):
        # Un .env editado a mano trae espacios tras las comas. Si no se
        # recortaran, la clave registrada sería " clave-b" y la buena fallaría.
        monkeypatch.setattr(settings, "api_keys", "clave-a , clave-b")
        assert auth.claves_configuradas() == ["clave-a", "clave-b"]

    def test_una_coma_de_mas_no_registra_una_clave_vacia(self, monkeypatch):
        # ⭐ Si el vacío se colara, mandar `X-API-Key: ` valdría por una clave
        #    buena y la auth quedaría abierta creyéndose cerrada.
        monkeypatch.setattr(settings, "api_keys", "clave-a,,clave-b,")
        assert auth.claves_configuradas() == ["clave-a", "clave-b"]

    def test_sin_claves_el_servicio_esta_abierto(self, sin_auth):
        assert auth.auth_activa() is False

    def test_solo_espacios_sigue_siendo_modo_abierto(self, monkeypatch):
        # API_KEYS="   " es un .env a medio rellenar, no una credencial.
        monkeypatch.setattr(settings, "api_keys", "   ")
        assert auth.auth_activa() is False


# ==================================================================
# La validación de la credencial — el corazón del asunto
# ==================================================================
class TestCredencialValida:
    def test_una_clave_de_la_lista_vale(self, con_auth):
        assert auth.credencial_valida("clave-de-la-web") is True
        assert auth.credencial_valida("clave-del-bot") is True

    def test_una_clave_inventada_no_vale(self, con_auth):
        assert auth.credencial_valida("clave-inventada") is False

    def test_sin_clave_no_vale(self, con_auth):
        assert auth.credencial_valida(None) is False
        assert auth.credencial_valida("") is False

    def test_un_prefijo_correcto_no_vale(self, con_auth):
        # La comparación es de la clave ENTERA. Un `startswith` mal puesto
        # dejaría entrar con el primer carácter acertado.
        assert auth.credencial_valida("clave-de-la-we") is False
        assert auth.credencial_valida("clave-de-la-web-y-mas") is False


# ==================================================================
# El servicio entero, por HTTP
# ==================================================================
class TestEndpoints:
    def test_chat_sin_credencial_es_401(self, con_auth, cliente):
        assert cliente.post("/chat", json={"mensaje": "hola"}).status_code == 401

    def test_chat_con_credencial_responde(self, con_auth, cliente):
        respuesta = cliente.post("/chat", json={"mensaje": "aretes dorados"},
                                 headers={"X-API-Key": "clave-de-la-web"})
        assert respuesta.status_code == 200

    def test_chat_con_credencial_invalida_es_401(self, con_auth, cliente):
        # ⚠️ Un 401 de verdad, no un 200 con un evento SSE de error dentro. Por
        #    eso la dependencia va en el decorador y no dentro del generador:
        #    una vez abierto el stream, la cabecera ya se mandó.
        respuesta = cliente.post("/chat", json={"mensaje": "hola"},
                                 headers={"X-API-Key": "no-soy-una-clave"})
        assert respuesta.status_code == 401

    def test_metrics_esta_protegido(self, con_auth, cliente):
        # Cuánto tráfico manejas y cuánto te cuesta es información de negocio.
        assert cliente.get("/metrics").status_code == 401
        assert cliente.get("/metrics",
                           headers={"X-API-Key": "clave-del-bot"}).status_code == 200

    def test_feedback_esta_protegido(self, con_auth, cliente):
        # El POST abierto dejaría a un bot decidir el A/B a base de 👎.
        assert cliente.post("/feedback", json={"util": True}).status_code == 401
        assert cliente.get("/feedback").status_code == 401
        assert cliente.post("/feedback", json={"util": True},
                            headers={"X-API-Key": "clave-del-bot"}).status_code == 200

    def test_health_NO_esta_protegido(self, con_auth, cliente):
        # El orquestador no tiene credenciales. Si /health exigiera una, un error
        # de configuración parecería un servicio caído y lo reiniciaría en bucle.
        respuesta = cliente.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.json()["auth_activa"] is True

    def test_health_publica_que_el_servicio_esta_abierto(self, sin_auth, cliente):
        # El modo abierto debe poder detectarse desde FUERA, no solo leyendo
        # el .env del servidor.
        assert cliente.get("/health").json()["auth_activa"] is False

    def test_sin_auth_todo_sigue_abierto(self, sin_auth, cliente):
        # La garantía de que el curso se sigue pudiendo estudiar sin configurar.
        assert cliente.post("/chat", json={"mensaje": "hola"}).status_code == 200
        assert cliente.get("/metrics").status_code == 200
        assert cliente.get("/feedback").status_code == 200


class TestCORS:
    def _app(self):
        return crear_app(responder=ResponderFalso(), catalogo=[],
                         cache=SemanticCache(EmbeddingsBolsa(), InMemoryCache()))

    def test_sin_origenes_no_se_instala_cors(self, monkeypatch):
        monkeypatch.setattr(settings, "cors_origins", "")
        with TestClient(self._app()) as c:
            respuesta = c.get("/health", headers={"Origin": "https://malicioso.com"})
        # Sin CORS, el navegador no recibe permiso para leer la respuesta.
        assert "access-control-allow-origin" not in respuesta.headers

    def test_solo_los_origenes_declarados_pasan(self, monkeypatch):
        monkeypatch.setattr(settings, "cors_origins", "https://sifrah.com")
        with TestClient(self._app()) as c:
            bueno = c.get("/health", headers={"Origin": "https://sifrah.com"})
            malo = c.get("/health", headers={"Origin": "https://malicioso.com"})

        assert bueno.headers["access-control-allow-origin"] == "https://sifrah.com"
        assert "access-control-allow-origin" not in malo.headers
