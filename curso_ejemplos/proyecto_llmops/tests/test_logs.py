"""
test_logs.py · El log estructurado y el hilo que cose una petición
==================================================================
Dos cosas se prueban aquí, y la segunda es la que de verdad cuesta:

  1) Que cada línea sea UN JSON válido con los campos acordados.
  2) Que el `request_id` NO se filtre entre peticiones concurrentes. Es el fallo
     clásico de correlacionar con una variable global: con un ContextVar mal
     usado, la petición B hereda el id de la A y los logs mienten justo cuando
     los estás usando para investigar.
"""
import asyncio
import io
import json
import logging

import pytest

from observability import logs

pytestmark = pytest.mark.offline


@pytest.fixture
def raiz_limpia():
    """Aísla el logger raíz: cada test empieza sin handlers y los restaura al
    salir. Sin esto, el handler del primer test sobrevive a los demás (y el de
    pytest se mezcla con el nuestro)."""
    raiz = logging.getLogger()
    previos, nivel = raiz.handlers[:], raiz.level
    raiz.handlers = []
    yield raiz
    raiz.handlers, raiz.level = previos, nivel


@pytest.fixture
def capturar(raiz_limpia):
    """Configura el logging contra un buffer y devuelve un lector de sus líneas.

    Se inyecta un StringIO en vez de leer stdout porque `capsys` sustituye
    `sys.stdout` en cada test, y el handler se queda con la referencia que
    tenía al crearse.
    """
    buffer = io.StringIO()
    logs.configurar_logging("DEBUG", stream=buffer)

    def leer() -> list[dict]:
        return [json.loads(l) for l in buffer.getvalue().splitlines() if l.strip()]

    return leer


class TestFormatoJSON:
    def test_cada_linea_es_un_json_con_los_campos_base(self, capturar):
        logs.obtener_logger("prueba").info("algo pasó")

        (linea,) = capturar()
        assert linea["mensaje"] == "algo pasó"
        assert linea["nivel"] == "INFO"
        assert linea["logger"] == "prueba"
        assert linea["ts"].endswith("Z")      # UTC explícito, no hora local

    def test_los_campos_extra_llegan_al_json(self, capturar):
        logs.obtener_logger("prueba").info("request", extra={"rol": "analyst",
                                                            "estado": 200})
        (linea,) = capturar()
        assert linea["rol"] == "analyst"
        assert linea["estado"] == 200

    def test_el_traceback_va_dentro_del_json_no_en_crudo(self, capturar):
        # ⭐ Un traceback multilínea escupido en crudo rompería la promesa de
        #    "una línea = un evento" y el recolector lo trocearía en basura.
        try:
            raise ValueError("reventó")
        except ValueError:
            logs.obtener_logger("prueba").exception("falló")

        lineas = capturar()
        assert len(lineas) == 1
        assert "ValueError: reventó" in lineas[0]["excepcion"]

    def test_un_objeto_raro_no_tumba_el_logging(self, capturar):
        # Un log que revienta al reportar un fallo te deja ciego justo cuando
        # más falta hace. Degrada a repr, no a excepción.
        class Raro:
            pass

        logs.obtener_logger("prueba").info("ok", extra={"cosa": Raro()})
        assert "Raro" in capturar()[0]["cosa"]

    def test_no_se_acumulan_handlers_al_reconfigurar(self, capturar):
        # uvicorn --reload reimporta el módulo. Sin la guarda de idempotencia,
        # cada recarga duplicaría todas las líneas.
        logs.configurar_logging("DEBUG")
        logs.configurar_logging("DEBUG")
        logs.obtener_logger("prueba").info("una sola vez")

        assert len(capturar()) == 1


class TestRequestId:
    def test_fuera_de_una_peticion_no_hay_campo(self, capturar):
        logs.obtener_logger("prueba").info("arranque del servicio")
        # El log del arranque no pertenece a ninguna petición: inventarle un id
        # sería mentir.
        assert "request_id" not in capturar()[0]

    def test_dentro_de_una_peticion_todas_las_lineas_lo_llevan(self, capturar):
        token = logs.fijar_request_id("abc123")
        try:
            logs.obtener_logger("prueba").info("primera")
            logs.obtener_logger("otro").info("segunda")
        finally:
            logs.reiniciar_request_id(token)

        assert [l["request_id"] for l in capturar()] == ["abc123", "abc123"]

    def test_al_reiniciar_deja_de_aparecer(self, capturar):
        token = logs.fijar_request_id("abc123")
        logs.reiniciar_request_id(token)
        logs.obtener_logger("prueba").info("ya fuera")

        assert "request_id" not in capturar()[0]

    def test_dos_peticiones_concurrentes_no_se_mezclan(self, capturar):
        """⭐ EL TEST QUE JUSTIFICA EL ContextVar.

        Con una variable global normal, la tarea que escribe última gana y las
        dos peticiones acaban con el mismo id. Aquí cada una ve el suyo aunque
        se intercalen en el mismo hilo.
        """
        async def peticion(rid: str, espera: float):
            token = logs.fijar_request_id(rid)
            try:
                await asyncio.sleep(espera)      # cede el control a la otra
                logs.obtener_logger("prueba").info("respondiendo")
            finally:
                logs.reiniciar_request_id(token)

        async def ambas():
            # La 'A' se duerme MÁS: si hubiera fuga, escribiría con el id de 'B'.
            await asyncio.gather(peticion("id-A", 0.02), peticion("id-B", 0.001))

        asyncio.run(ambas())

        # Solo las nuestras: en DEBUG, asyncio también escribe (y sus líneas no
        # pertenecen a ninguna petición, así que no llevan request_id).
        mias = [l for l in capturar() if l["logger"] == "prueba"]
        assert sorted(l["request_id"] for l in mias) == ["id-A", "id-B"]


class TestMiddleware:
    """El cableado real: que una petición HTTP produzca una línea correlacionada.

    ⭐ POR QUÉ ESTA CLASE EXISTE: los tests de arriba prueban las piezas
       (formateador, ContextVar) y pasaban con el middleware ROTO. La primera
       versión emitía el log DESPUÉS del `finally` que limpia el ContextVar, así
       que la línea "request" salía sin `request_id` — el único campo por el que
       se investiga. Probar las piezas no prueba el montaje.
    """

    @pytest.fixture
    def cliente(self, raiz_limpia, fabrica_agente, embeddings_falsos):
        from cache.cache_backends import InMemoryCache
        from cache.semantic_cache import SemanticCache
        from fastapi.testclient import TestClient

        from app.main import crear_app

        app = crear_app(agente=fabrica_agente(["ok"]),
                        cache=SemanticCache(embeddings_falsos, InMemoryCache()))

        # DESPUÉS de crear_app y con `forzar`: crear_app instala su propio
        # handler a stdout, y pytest reordena los del raíz entre fases. Sin
        # esto, el buffer se queda vacío y el test mide el vacío.
        self.buffer = io.StringIO()
        logs.configurar_logging("INFO", stream=self.buffer, forzar=True)

        with TestClient(app) as cliente:
            yield cliente

    def _lineas(self, logger="app.main") -> list[dict]:
        todas = [json.loads(l) for l in self.buffer.getvalue().splitlines() if l.strip()]
        return [l for l in todas if l["logger"] == logger]

    def test_la_linea_de_la_peticion_lleva_su_request_id(self, cliente):
        respuesta = cliente.post("/chat", json={"mensaje": "¿Hay que cifrar?"})

        (linea,) = self._lineas()
        assert linea["request_id"] == respuesta.headers["X-Request-ID"]
        assert (linea["ruta"], linea["metodo"], linea["estado"]) == ("/chat", "POST", 200)

    def test_respeta_el_id_que_viene_de_fuera(self, cliente):
        # Con un proxy delante, el mismo id debe coser la traza de punta a punta
        # en vez de empezar de cero en cada salto.
        respuesta = cliente.get("/", headers={"X-Request-ID": "traza-externa-99"})

        assert respuesta.headers["X-Request-ID"] == "traza-externa-99"
        assert self._lineas()[0]["request_id"] == "traza-externa-99"

    def test_dos_peticiones_reciben_ids_distintos(self, cliente):
        cliente.get("/")
        cliente.get("/")

        ids = {l["request_id"] for l in self._lineas()}
        assert len(ids) == 2

    def test_health_no_ensucia_el_log(self, cliente):
        # El orquestador lo llama cada pocos segundos: si se registrara, el log
        # sería 99 % health checks.
        cliente.get("/health")
        assert self._lineas() == []

    def test_las_librerias_ruidosas_no_narran_cada_peticion(self, cliente):
        cliente.get("/")
        # httpx en INFO escribe una línea por llamada HTTP; cargar embeddings
        # dispara decenas contra el Hub y ahogarían el log del servicio.
        assert self._lineas(logger="httpx") == []


class TestNivel:
    def test_el_nivel_filtra(self, raiz_limpia):
        # En producción se sube a WARNING para que el log no sea un torrente;
        # que el filtro funcione es lo que hace viable subirlo.
        buffer = io.StringIO()
        logs.configurar_logging("WARNING", stream=buffer)

        logger = logs.obtener_logger("prueba")
        logger.info("esto no debería salir")
        logger.warning("esto sí")

        lineas = [l for l in buffer.getvalue().splitlines() if l.strip()]
        assert len(lineas) == 1
        assert json.loads(lineas[0])["nivel"] == "WARNING"
