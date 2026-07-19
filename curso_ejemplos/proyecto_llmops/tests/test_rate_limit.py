"""
test_rate_limit.py · El freno que evita que un bucle te vacíe la cuenta
=======================================================================
`LimitadorVentana` es una máquina de estados PURA con el reloj INYECTADO. Eso es
lo que permite probar de verdad un límite "por minuto" sin que la suite duerma
sesenta segundos — una suite que tarda un minuto en probar esto es una suite que
nadie corre.

El test que más importa es `test_no_permite_el_doble_en_el_borde`: es la razón
de ser de la ventana deslizante frente al contador que se reinicia en punto.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import crear_app
from app.rate_limit import LimitadorVentana, identificar
from cache.cache_backends import InMemoryCache
from cache.semantic_cache import SemanticCache

pytestmark = pytest.mark.offline


class TestVentanaDeslizante:
    def test_deja_pasar_hasta_el_limite(self):
        lim = LimitadorVentana(limite=3, ventana_s=60)
        assert [lim.permitir("ana", ahora=0) for _ in range(3)] == [True] * 3

    def test_la_siguiente_se_rechaza(self):
        lim = LimitadorVentana(limite=3, ventana_s=60)
        for _ in range(3):
            lim.permitir("ana", ahora=0)
        assert lim.permitir("ana", ahora=0) is False

    def test_al_salir_de_la_ventana_vuelve_a_permitir(self):
        lim = LimitadorVentana(limite=2, ventana_s=60)
        lim.permitir("ana", ahora=0)
        lim.permitir("ana", ahora=10)
        assert lim.permitir("ana", ahora=30) is False   # aún dentro
        assert lim.permitir("ana", ahora=61) is True    # la de t=0 ya expiró

    def test_no_permite_el_doble_en_el_borde(self):
        """⭐ EL TEST QUE JUSTIFICA LA VENTANA DESLIZANTE.

        Un contador que se reinicia "en punto" permitiría 3 peticiones al final
        de un minuto y otras 3 al principio del siguiente: 6 en dos segundos
        respetando "3 por minuto". Aquí eso no pasa.
        """
        lim = LimitadorVentana(limite=3, ventana_s=60)
        for _ in range(3):
            assert lim.permitir("ana", ahora=59) is True
        # Dos segundos después, en el "minuto siguiente": siguen contando.
        assert lim.permitir("ana", ahora=61) is False

    def test_cada_cliente_tiene_su_propio_cubo(self):
        lim = LimitadorVentana(limite=1, ventana_s=60)
        assert lim.permitir("ana", ahora=0) is True
        assert lim.permitir("beto", ahora=0) is True    # a beto no le afecta ana
        assert lim.permitir("ana", ahora=0) is False

    def test_limite_cero_significa_sin_limite(self):
        lim = LimitadorVentana(limite=0, ventana_s=60)
        assert all(lim.permitir("ana", ahora=0) for _ in range(100))


class TestFugaDeMemoria:
    def test_olvida_a_los_clientes_inactivos(self):
        # ⚠️ Sin esto el diccionario crece con cada cliente y no se vacía nunca:
        #    una fuga lenta que solo se nota tras semanas de uptime.
        lim = LimitadorVentana(limite=5, ventana_s=60)
        lim.permitir("ana", ahora=0)
        lim.permitir("beto", ahora=50)

        assert lim.olvidar_inactivos(ahora=70) == 1     # ana sí, beto todavía no
        assert "ana" not in lim._marcas
        assert "beto" in lim._marcas

    def test_el_que_sigue_activo_no_pierde_su_cuenta(self):
        lim = LimitadorVentana(limite=2, ventana_s=60)
        lim.permitir("ana", ahora=0)
        lim.permitir("ana", ahora=59)
        lim.olvidar_inactivos(ahora=59)
        # Si la limpieza le hubiera borrado el historial, esta pasaría.
        assert lim.permitir("ana", ahora=59) is False


class TestIdentificacion:
    def test_la_credencial_manda_sobre_la_ip(self, fabrica_request):
        # La clave identifica mejor: no cambia si el cliente salta de red.
        quien = identificar(fabrica_request(api_key="secreta-123456", ip="1.2.3.4"))
        assert quien.startswith("key:")

    def test_la_clave_no_se_guarda_en_claro(self, fabrica_request):
        # Aparecería en cualquier volcado de estado o log de depuración.
        quien = identificar(fabrica_request(api_key="secreta-123456", ip="1.2.3.4"))
        assert "secreta" not in quien

    def test_sin_credencial_se_usa_la_ip(self, fabrica_request):
        assert identificar(fabrica_request(ip="1.2.3.4")) == "ip:1.2.3.4"


@pytest.fixture
def fabrica_request():
    """Un doble mínimo de Request: `identificar` solo mira cabeceras y cliente."""
    class ClienteFalso:
        def __init__(self, host): self.host = host

    class RequestFalso:
        def __init__(self, api_key=None, ip=None):
            self.headers = {"X-API-Key": api_key} if api_key else {}
            self.client = ClienteFalso(ip) if ip else None

    return RequestFalso


class TestPorHTTP:
    """El límite aplicado de verdad, sobre el servicio montado."""

    @pytest.fixture
    def cliente(self, monkeypatch, fabrica_agente, embeddings_falsos):
        monkeypatch.setattr(settings, "rate_limit_peticiones", 3)
        monkeypatch.setattr(settings, "rate_limit_ventana_s", 60.0)
        app = crear_app(agente=fabrica_agente(["ok"]),
                        cache=SemanticCache(embeddings_falsos, InMemoryCache()))
        with TestClient(app) as c:
            yield c

    def test_a_la_cuarta_responde_429(self, cliente):
        for _ in range(3):
            assert cliente.get("/").status_code == 200
        assert cliente.get("/").status_code == 429

    def test_el_429_trae_retry_after(self, cliente):
        # Parte del contrato del 429: sin ella, un cliente reintenta de
        # inmediato y empeora justo el problema que provocó el límite.
        for _ in range(3):
            cliente.get("/")
        assert cliente.get("/").headers["Retry-After"] == "60"

    def test_el_429_sale_como_429_y_no_como_500(self, cliente):
        # ⚠️ Una HTTPException lanzada dentro de un middleware NO la maneja
        #    nadie: el manejador de FastAPI vive más adentro, en el routing.
        #    Sin la conversión a JSONResponse, esto sería un 500.
        for _ in range(3):
            cliente.get("/")
        respuesta = cliente.get("/")
        assert respuesta.status_code == 429
        assert "error" in respuesta.json()

    def test_health_no_se_limita(self, cliente):
        # Lo llama el orquestador cada pocos segundos; un 429 ahí se leería
        # como "servicio caído" y dispararía un reinicio.
        for _ in range(10):
            assert cliente.get("/health").status_code == 200

    def test_el_429_tambien_lleva_request_id(self, cliente):
        for _ in range(3):
            cliente.get("/")
        assert cliente.get("/").headers.get("X-Request-ID")
