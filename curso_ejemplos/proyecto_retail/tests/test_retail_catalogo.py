"""
test_retail_catalogo.py · La fuente del catálogo y qué pasa cuando falla
========================================================================
El invariante del proyecto es que el precio NUNCA se lo inventa el modelo: sale
del catálogo. Eso convierte "de dónde viene el catálogo" en una cuestión de
corrección, no de infraestructura.

Lo que más se prueba aquí es la ASIMETRÍA entre arrancar y refrescar:

    al arrancar con `live`, si falla la descarga  → el servicio NO arranca
    al refrescar, si falla la descarga            → se conserva el bueno

Caer al catálogo demo cuando el real no está disponible serviría los precios de
doce productos de mentira como si fueran los de la tienda: inventar el precio
por otra vía, y encima en silencio.

Nada de red: `bajar` se inyecta en todas las funciones.
"""
import asyncio

import pytest

from proyecto_retail.app import catalogo as catalogo_mod
from proyecto_retail.app.config import settings

pytestmark = pytest.mark.offline

PRODUCTOS = [{"titulo": "Aretes dorados", "precio": 39.9, "stock": 5,
              "categoria": "aretes"}]


@pytest.fixture
def modo_live(monkeypatch):
    monkeypatch.setattr(settings, "catalogo_fuente", "live")


@pytest.fixture
def modo_demo(monkeypatch):
    monkeypatch.setattr(settings, "catalogo_fuente", "demo")


class TestCargaInicial:
    def test_en_modo_demo_no_toca_la_red(self, modo_demo):
        def explotar(url):
            raise AssertionError("no debería bajar nada en modo demo")

        catalogo = catalogo_mod.cargar_inicial(bajar=explotar)
        assert len(catalogo) > 0        # el fichero de demo tiene productos

    def test_en_modo_live_usa_lo_que_baja(self, modo_live):
        catalogo = catalogo_mod.cargar_inicial(bajar=lambda url: PRODUCTOS)
        assert catalogo == PRODUCTOS

    def test_si_la_descarga_falla_el_servicio_NO_arranca(self, modo_live):
        """⭐ LA DECISIÓN CENTRAL DEL MÓDULO.

        Degradar al catálogo demo aquí sería servir precios de mentira a
        clientes de verdad. Un servicio caído se ve; un precio equivocado no.
        """
        def falla(url):
            raise ConnectionError("la tienda no responde")

        with pytest.raises(ConnectionError):
            catalogo_mod.cargar_inicial(bajar=falla)

    def test_un_catalogo_vacio_tambien_impide_arrancar(self, modo_live):
        # Una lista vacía es tan peligrosa como un error: el asistente diría
        # "no tengo nada" a todo, y eso parece un fallo de producto, no de red.
        with pytest.raises(RuntimeError, match="vacío"):
            catalogo_mod.cargar_inicial(bajar=lambda url: [])

    def test_el_fallo_no_se_disfraza_de_catalogo_demo(self, modo_live):
        # El test que fija la asimetría: comprobamos que NO cayó al demo.
        def falla(url):
            raise ConnectionError("caída")

        with pytest.raises(ConnectionError):
            catalogo_mod.cargar_inicial(bajar=falla)


class TestRefresco:
    """Aquí la política se INVIERTE: ya hay un catálogo bueno que preservar."""

    def _correr_un_ciclo(self, estado, bajar):
        """Ejecuta exactamente una vuelta del bucle y corta."""
        ciclos = {"n": 0}

        async def dormir_una_vez(_s):
            ciclos["n"] += 1
            if ciclos["n"] > 1:
                raise asyncio.CancelledError    # sale del while tras un ciclo

        async def correr():
            with pytest.raises(asyncio.CancelledError):
                await catalogo_mod.refrescar_periodicamente(
                    estado, 0.0, bajar=bajar, dormir=dormir_una_vez)

        asyncio.run(correr())

    def test_sustituye_el_catalogo_por_el_nuevo(self):
        estado = {"catalogo": [{"titulo": "viejo", "precio": 1.0}]}
        self._correr_un_ciclo(estado, bajar=lambda url: PRODUCTOS)
        assert estado["catalogo"] == PRODUCTOS

    def test_si_la_descarga_falla_conserva_el_anterior(self):
        # ⭐ Al revés que al arrancar: servir datos de hace diez minutos es un
        #    problema mucho menor que quedarse sin servicio por un hipo de red.
        viejo = [{"titulo": "vigente", "precio": 10.0}]
        estado = {"catalogo": viejo}

        def falla(url):
            raise ConnectionError("hipo de red")

        self._correr_un_ciclo(estado, bajar=falla)
        assert estado["catalogo"] == viejo

    def test_un_refresco_vacio_no_borra_el_catalogo(self):
        # Un catálogo vacío sustituyendo a uno bueno dejaría al asistente sin
        # nada que decir, que es peor que servirlo ligeramente viejo.
        viejo = [{"titulo": "vigente", "precio": 10.0}]
        estado = {"catalogo": viejo}
        self._correr_un_ciclo(estado, bajar=lambda url: [])
        assert estado["catalogo"] == viejo


class TestCableadoEnElArranque:
    def test_en_modo_demo_no_se_lanza_tarea_de_refresco(self, modo_demo, monkeypatch):
        # El fichero de demo no cambia solo: una tarea de fondo ahí solo gasta.
        from fastapi.testclient import TestClient

        from proyecto_retail.app.main import crear_app
        from proyecto_retail.tests.test_retail_api import ResponderFalso

        creadas = []
        original = asyncio.create_task
        monkeypatch.setattr(asyncio, "create_task",
                            lambda coro, **kw: creadas.append(coro) or original(coro, **kw))

        app = crear_app(responder=ResponderFalso(), catalogo=[{"titulo": "x", "precio": 1.0}])
        with TestClient(app):
            pass
        assert creadas == []
