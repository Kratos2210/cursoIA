"""
test_auth.py · Que el rol deje de ser un deseo del cliente
===========================================================
El agujero que cierra `app/auth.py` era este:

    curl -d '{"mensaje":"...", "rol":"compliance"}'

y el servidor se lo creía. Con eso, el RBAC entero (guardrails/rbac.py) era
decorativo: cualquiera se autoconcedía el nivel que quisiera y los anexos
restringidos salían por la puerta.

Aquí se prueban las dos mitades:
  1) Con credenciales configuradas, el rol lo dicta la CLAVE y el body no pinta.
  2) Sin credenciales (el modo del curso), todo sigue funcionando como antes —
     porque romper la ejecutabilidad del material no era una opción.
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import auth
from app.config import settings
from app.main import crear_app
from cache.cache_backends import InMemoryCache
from cache.semantic_cache import SemanticCache

pytestmark = pytest.mark.offline

CLAVES = "clave-analista:analyst,clave-cumplimiento:compliance"


@pytest.fixture
def con_auth(monkeypatch):
    """Servicio con dos credenciales configuradas."""
    monkeypatch.setattr(settings, "api_keys", CLAVES)


@pytest.fixture
def sin_auth(monkeypatch):
    """Servicio abierto: el modo en el que se estudia el curso."""
    monkeypatch.setattr(settings, "api_keys", "")


@pytest.fixture
def cliente(fabrica_agente, embeddings_falsos):
    app = crear_app(agente=fabrica_agente(["respuesta ", "cualquiera"]),
                    cache=SemanticCache(embeddings_falsos, InMemoryCache()))
    with TestClient(app) as c:
        yield c


# ==================================================================
# El parseo de API_KEYS
# ==================================================================
class TestParseo:
    def test_lee_varias_credenciales(self, con_auth):
        assert auth.claves_configuradas() == {
            "clave-analista": "analyst",
            "clave-cumplimiento": "compliance",
        }

    def test_una_entrada_mal_formada_no_tumba_el_arranque(self, monkeypatch):
        # Un typo en el .env no debe impedir que el servicio arranque: se ignora
        # la entrada mala y las buenas siguen valiendo.
        monkeypatch.setattr(settings, "api_keys", "basura-sin-rol,buena:analyst")
        assert auth.claves_configuradas() == {"buena": "analyst"}

    def test_un_rol_inexistente_se_descarta(self, monkeypatch):
        # ⭐ Si se aceptara, `rbac.niveles_permitidos` lo degradaría a 'public' y
        #    el operador vería a su "admin" sin acceso a nada, sin saber por qué.
        monkeypatch.setattr(settings, "api_keys", "clave:superadmin")
        assert auth.claves_configuradas() == {}

    def test_sin_claves_el_servicio_esta_abierto(self, sin_auth):
        assert auth.auth_activa() is False


# ==================================================================
# La resolución del rol — el corazón del asunto
# ==================================================================
class TestResolverRol:
    def test_el_rol_sale_de_la_credencial(self, con_auth):
        assert auth.resolver_rol("clave-cumplimiento") == "compliance"
        assert auth.resolver_rol("clave-analista") == "analyst"

    def test_el_body_NO_puede_escalar_privilegios(self, con_auth):
        # ⭐ EL TEST QUE JUSTIFICA EL MÓDULO. La credencial es de analista y el
        #    body pide 'compliance': gana la credencial, siempre.
        assert auth.resolver_rol("clave-analista", "compliance") == "analyst"

    def test_una_credencial_invalida_es_401(self, con_auth):
        with pytest.raises(HTTPException) as exc:
            auth.resolver_rol("clave-inventada")
        assert exc.value.status_code == 401

    def test_sin_credencial_tambien_es_401(self, con_auth):
        # Ausente e inválida se contestan igual: no confirmamos nada.
        with pytest.raises(HTTPException) as exc:
            auth.resolver_rol(None)
        assert exc.value.status_code == 401

    def test_sin_auth_se_respeta_el_rol_del_body(self, sin_auth):
        # El modo del curso: sin configurar nada, el material sigue siendo
        # ejecutable y el rol del body vuelve a mandar.
        assert auth.resolver_rol(None, "compliance") == "compliance"

    def test_sin_auth_y_sin_rol_cae_al_por_defecto(self, sin_auth):
        assert auth.resolver_rol(None) == settings.app_rol_por_defecto


# ==================================================================
# El servicio entero, por HTTP
# ==================================================================
class TestEndpoints:
    def test_chat_sin_credencial_es_401(self, con_auth, cliente):
        assert cliente.post("/chat", json={"mensaje": "hola"}).status_code == 401

    def test_chat_con_credencial_responde(self, con_auth, cliente):
        respuesta = cliente.post("/chat", json={"mensaje": "hola"},
                                 headers={"X-API-Key": "clave-analista"})
        assert respuesta.status_code == 200

    def test_metrics_esta_protegido(self, con_auth, cliente):
        # Cuánto tráfico manejas y cuánto te cuesta es información de negocio.
        assert cliente.get("/metrics").status_code == 401
        assert cliente.get("/metrics",
                           headers={"X-API-Key": "clave-analista"}).status_code == 200

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


class TestElRolEfectivoLlegaAbajo:
    """No basta con resolver el rol: tiene que VIAJAR hasta donde se usa.

    ⭐ Un `resolver_rol` correcto cuyo resultado no se propaga al flujo dejaría
       el agujero abierto igual, y los tests de arriba seguirían en verde. Aquí
       se comprueba el recorrido completo usando el caché, que particiona sus
       entradas por rol (un 'analyst' no puede recibir lo generado para
       'compliance' — ver cache/semantic_cache.py).
    """

    def test_el_body_no_decide_en_que_particion_del_cache_se_guarda(
            self, con_auth, fabrica_agente, embeddings_falsos):
        cache = SemanticCache(embeddings_falsos, InMemoryCache())
        app = crear_app(agente=fabrica_agente(["una ", "respuesta"]), cache=cache)

        with TestClient(app) as c:
            # Credencial de analista, pero el body pide 'compliance'.
            respuesta = c.post("/chat",
                               json={"mensaje": "¿Hay que cifrar?", "rol": "compliance"},
                               headers={"X-API-Key": "clave-analista"})
            assert respuesta.status_code == 200

        # Se guardó como 'analyst' (la credencial), NO como 'compliance' (el body).
        assert list(cache.backend.entradas("analyst")) != []
        assert list(cache.backend.entradas("compliance")) == []


class TestCORS:
    def test_sin_origenes_no_se_instala_cors(self, monkeypatch, fabrica_agente,
                                             embeddings_falsos):
        monkeypatch.setattr(settings, "cors_origins", "")
        app = crear_app(agente=fabrica_agente(["ok"]),
                        cache=SemanticCache(embeddings_falsos, InMemoryCache()))
        with TestClient(app) as c:
            respuesta = c.get("/health", headers={"Origin": "https://malicioso.com"})
        # Sin CORS, el navegador no recibe permiso para leer la respuesta.
        assert "access-control-allow-origin" not in respuesta.headers

    def test_solo_los_origenes_declarados_pasan(self, monkeypatch, fabrica_agente,
                                                embeddings_falsos):
        monkeypatch.setattr(settings, "cors_origins", "https://gobdata.pe")
        app = crear_app(agente=fabrica_agente(["ok"]),
                        cache=SemanticCache(embeddings_falsos, InMemoryCache()))
        with TestClient(app) as c:
            bueno = c.get("/health", headers={"Origin": "https://gobdata.pe"})
            malo = c.get("/health", headers={"Origin": "https://malicioso.com"})

        assert bueno.headers["access-control-allow-origin"] == "https://gobdata.pe"
        assert "access-control-allow-origin" not in malo.headers
