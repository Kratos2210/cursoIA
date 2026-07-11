"""
test_frontend.py · La página de chat: se sirve, es autocontenida y no rompe nada
================================================================================
El frontend es un archivo estático (`app/static/chat.html`) que `GET /` sirve tal
cual. No hay lógica de servidor que probar aquí: lo que se comprueba es el
CONTRATO de esa página con el servicio —que llame a `/chat` y a `/feedback`, que
tenga los elementos clave— y dos invariantes que son fáciles de romper sin darse
cuenta:

  · que sea AUTOCONTENIDA (ni un `<script src="http…">`, ni un CDN): tiene que
    abrir en un navegador SIN internet, porque es la demo del curso;
  · que servir `GET /` NO altere los endpoints que ya existían.

Todo offline: `GET /` no necesita agente ni caché, así que la app se levanta con
`crear_app()` a secas (sus piezas caras quedan en None y jamás se tocan).
"""
import pytest
from fastapi.testclient import TestClient

from app import frontend
from app.main import crear_app

pytestmark = pytest.mark.offline


@pytest.fixture
def cliente():
    """La app SIN piezas caras: `GET /` sirve un string ya cargado en memoria.

    No se usa `with TestClient(...)` (que dispara el lifespan) porque el lifespan
    construiría el agente y el caché reales. Sin el `with`, no corre el startup:
    perfecto, porque estas rutas no lo necesitan.
    """
    return TestClient(crear_app())


class TestSirveLaPagina:
    def test_get_raiz_devuelve_html(self, cliente):
        respuesta = cliente.get("/")
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"].startswith("text/html")

    def test_lo_servido_coincide_con_la_constante(self, cliente):
        # `GET /` devuelve exactamente lo que `frontend.PAGINA_CHAT` tiene cargado.
        assert cliente.get("/").text == frontend.PAGINA_CHAT


class TestLaConstanteEsImportable:
    def test_pagina_chat_no_vacia(self):
        # Importable SIN levantar nada: un string, no un FileResponse.
        assert isinstance(frontend.PAGINA_CHAT, str)
        assert len(frontend.PAGINA_CHAT) > 500
        assert "<!DOCTYPE html>" in frontend.PAGINA_CHAT


class TestElHtmlLlevaLosElementosClave:
    def test_consume_chat_por_fetch(self, cliente):
        html = cliente.get("/").text
        # El cliente habla con /chat por POST vía fetch (no EventSource).
        assert 'fetch("/chat"' in html
        assert 'method: "POST"' in html

    def test_tiene_botones_de_feedback_y_endpoint(self, cliente):
        html = cliente.get("/").text
        assert 'fetch("/feedback"' in html   # cierra el lazo del A/B
        assert "👍" in html and "👎" in html

    def test_tiene_input_de_mensaje_y_selector_de_rol(self, cliente):
        html = cliente.get("/").text
        assert 'id="entrada"' in html        # el input donde se escribe
        assert 'id="rol"' in html            # el selector de rol (RBAC)
        for rol in ("public", "analyst", "compliance"):
            assert rol in html

    def test_parsea_los_eventos_sse_del_servicio(self, cliente):
        # El parser reconoce los tres eventos que emite app/streaming.py.
        html = cliente.get("/").text
        assert '"fin"' in html
        assert '"bloqueado"' in html
        assert '"error"' in html


class TestEsAutocontenida:
    def test_sin_scripts_ni_recursos_externos(self, cliente):
        html = cliente.get("/").text
        # Ni un CDN, ni un <script src="http…">, ni un <link href="http…">.
        assert 'src="http' not in html
        assert 'href="http' not in html
        assert "http://" not in html
        assert "https://" not in html


class TestNoRompeLosEndpointsExistentes:
    def test_health_sigue_respondiendo(self, cliente):
        # Añadir `GET /` no debe tocar el resto de la API.
        respuesta = cliente.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "ok"
