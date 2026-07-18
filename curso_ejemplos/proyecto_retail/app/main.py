"""
main.py · El servicio: donde las capas se hilvanan
===================================================
FINALIDAD:
  Exponer el asistente de compras por HTTP con la maquinaria LLMOps en el camino.
  Este archivo no implementa las capas: las ORDENA. Y el orden es la mitad del diseño.

      POST /chat
        │
        1. input_guard   → ¿inyección / forzar precio? corta aquí. CERO tokens.
        2. semantic_cache→ ¿ya respondimos esto? HIT: coste $0.
        3. agente        → intención (m05) → búsqueda → redacción → GROUNDING de
        │                  precios (con reintento y fallback). La respuesta que
        │                  sale de aquí YA es fiel por construcción.
        4. streaming     → se emite la respuesta verificada, troceada (SSE).
        5. cache.guardar → se cachea la respuesta fiel.
        6. métricas      → latencia, TTFT, coste, guardrails → Langfuse.

  ⭐ POR QUÉ ESE ORDEN:
     - El guardrail de entrada va ANTES del caché: no cacheamos ni vectorizamos
       un intento de forzar un precio.
     - El caché va ANTES del agente: es lo único que evita la llamada cara.
     - El grounding de precios vive DENTRO del agente (no como buffer de stream):
       "¿cada precio existe?" es una pregunta sobre la respuesta entera. Por eso
       se verifica-y-luego-se-emite (ver app/streaming.py y app/agent.py).

LÓGICA — inyección de dependencias, igual que en proyecto_llmops:
  `crear_app(...)` recibe responder, catálogo, caché y colectores POR PARÁMETRO.
  Por eso `tests/test_retail_api.py` levanta la API entera con un responder falso:
  sin LLM, sin Redis. Si esto construyera el agente al importarse, no habría manera
  de testearlo (y el --reload de uvicorn tardaría segundos).

Levantar:
    uv run uvicorn proyecto_retail.app.main:app --reload --port 8000
Probar:
    curl -N -X POST http://localhost:8000/chat \\
      -H 'Content-Type: application/json' \\
      -d '{"mensaje":"aretes dorados por menos de 25 soles"}'
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from proyecto_retail.app import auth
from proyecto_retail.app import catalogo as catalogo_mod
from proyecto_retail.app import frontend, rate_limit, streaming
from proyecto_retail.app.config import settings
from proyecto_retail.guardrails import input_guard
from proyecto_retail.observability import logs, metrics, tracing
from proyecto_retail.observability.cost_model import Uso
from proyecto_retail.observability.feedback import ColectorFeedback
from proyecto_retail.prompts.experimentos import Experimento

log = logs.obtener_logger(__name__)

# El A/B: A = la vendedora cálida (vendedora.yaml), B = la directa
# (vendedora_directa.yaml). El thread_id fija cuál ve cada clienta, de forma
# pegajosa. La variante elige el prompt y se anuncia en el evento `fin` para que
# el voto 👍/👎 se atribuya. Lazo A/B cerrado.
EXPERIMENTO_PROMPT = Experimento(
    nombre="tono_vendedora",
    variantes=("vendedora", "vendedora_directa"),
)


class PeticionChat(BaseModel):
    """Lo que manda el cliente. Un campo mal tipado se rechaza con un 422."""
    mensaje: str = Field(min_length=1, max_length=500)
    thread_id: str = Field(default="demo")


class Feedback(BaseModel):
    """El voto 👍/👎 sobre una respuesta. Cierra el lazo del A/B."""
    thread_id: str = Field(default="demo")
    util: bool
    variante: str | None = None
    comentario: str | None = Field(default=None, max_length=500)


def crear_app(responder=None, catalogo=None, cache=None,
              colector=None, feedback=None) -> FastAPI:
    """Construye la API. Todo lo caro entra por parámetro.

    responder : callable(peticion:str, variante:str) -> RespuestaAgente. Si es
                None, se construye al arrancar con el LLM del .env.
    catalogo  : la lista de productos normalizados. Si es None, se carga el demo.
    cache     : un SemanticCache. Si es None, se construye con lo que haya.
    colector  : dónde se acumulan las métricas del proceso.
    feedback  : dónde se acumulan los votos 👍/👎 del A/B.
    """
    # Lo primero de todo: si algo falla más abajo, queremos que el fallo salga
    # ya en formato legible por máquina y no en un print perdido.
    logs.configurar_logging(settings.log_level)
    # Y que quede dicho, en el arranque, si el servicio está abierto de par en par.
    auth.avisar_del_modo_abierto()

    # Un limitador POR APLICACIÓN (no global de módulo): así cada test tiene el
    # suyo y no hereda las peticiones que contó el anterior.
    limitador = rate_limit.crear_limitador()

    estado = {
        "responder": responder,
        "catalogo": catalogo,
        "cache": cache,
        "colector": colector if colector is not None else metrics.ColectorMetricas(),
        "feedback": feedback if feedback is not None else ColectorFeedback(),
    }

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """Lo caro se paga UNA vez, al arrancar. Todo antes del yield corre al
        arrancar; lo de después, al apagar (ahí se vacía el buffer de trazas)."""
        if estado["catalogo"] is None:
            # Respeta CATALOGO_FUENTE (demo|live). Con 'live', un fallo aquí
            # impide arrancar a propósito: ver app/catalogo.py.
            estado["catalogo"] = catalogo_mod.cargar_inicial()

        # El refresco solo tiene sentido si la fuente es externa y el intervalo
        # es positivo. En modo demo el fichero no cambia solo.
        tarea_refresco = None
        if settings.catalogo_fuente == "live" and settings.catalogo_refresco_s > 0:
            tarea_refresco = asyncio.create_task(
                catalogo_mod.refrescar_periodicamente(
                    estado, settings.catalogo_refresco_s))
        if estado["responder"] is None:      # pragma: no cover - requiere API real
            from proyecto_retail.app import agent
            from proyecto_retail.app.llm import crear_llm
            llm = crear_llm()

            def _responder(peticion: str, variante: str):
                return agent.responder_con_guardrail(
                    llm, peticion, estado["catalogo"], variante=variante)
            estado["responder"] = _responder
        if estado["cache"] is None:          # pragma: no cover - requiere embeddings
            from proyecto_retail.app.embeddings import crear_embeddings
            from proyecto_retail.cache.cache_backends import crear_backend
            from proyecto_retail.cache.semantic_cache import SemanticCache
            estado["cache"] = SemanticCache(crear_embeddings(), crear_backend())

        yield

        # Al apagar: se cancela el refresco ANTES de vaciar las trazas. Una
        # tarea de fondo que sigue viva tras el shutdown mantiene el proceso
        # colgado y el orquestador acaba matándolo a la fuerza.
        if tarea_refresco is not None:
            tarea_refresco.cancel()
            with suppress(asyncio.CancelledError):
                await tarea_refresco

        tracing.vaciar()

    app = FastAPI(
        title="Sifrah — asistente de compras (LLMOps)",
        description="Asistente de compras retail con guardrail de precios, caché semántico, A/B de prompts y tracing.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # CORS · qué páginas pueden llamar a esta API desde un navegador
    # ------------------------------------------------------------------
    # Solo si hay orígenes configurados. La demo sirve su propio frontend en `/`,
    # así que es el MISMO origen y no necesita CORS: instalarlo "por si acaso"
    # con "*" sería abrir la API a cualquier página de internet. En cuanto el
    # widget viva en sifrah.com y el backend en otro dominio, aquí va ese origen
    # y solo ese.
    if settings.lista_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.lista_cors,
            allow_credentials=True,
            allow_methods=["GET", "POST"],      # lo que la API usa, nada más
            allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        )

    # ------------------------------------------------------------------
    # MIDDLEWARE · el request_id que cose los logs de una misma petición
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def correlacionar_y_registrar(request, call_next):
        """Le pone un id a cada petición y registra cómo acabó.

        ⭐ El id se RESPETA si viene de fuera (`X-Request-ID`). Así, cuando haya
           un reverse proxy o el widget de la tienda delante, el mismo
           identificador cose la traza de punta a punta y no empieza de cero en
           cada salto.

        Se devuelve también en la respuesta: cuando una clienta reporta "me
        dijo un precio raro", con su `X-Request-ID` encontramos SU petición
        entre millones.
        """
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = logs.fijar_request_id(rid)
        try:
            # El freno va ANTES de llamar a nada: el sentido de limitar es no
            # gastar. /health queda fuera — lo llama el orquestador cada pocos
            # segundos y un 429 ahí se leería como "servicio caído".
            #
            # ⚠️ Se captura y se convierte a JSONResponse a mano porque una
            #    HTTPException lanzada DENTRO de un middleware no la maneja
            #    nadie: el manejador de FastAPI vive más adentro, en el routing.
            #    Sin este try, el 429 saldría como un 500.
            if request.url.path != "/health":
                try:
                    rate_limit.revisar(limitador, request)
                except HTTPException as limite:
                    respuesta = JSONResponse(status_code=limite.status_code,
                                             content={"error": limite.detail},
                                             headers=limite.headers)
                    respuesta.headers["X-Request-ID"] = rid
                    return respuesta

            respuesta = await call_next(request)
            respuesta.headers["X-Request-ID"] = rid
            # /health lo llama el orquestador cada pocos segundos: registrarlo
            # ahogaría el log real en ruido.
            #
            # ⚠️ Este log va DENTRO del try, antes del `finally`. Si se emitiera
            #    después, el ContextVar ya estaría limpio y la línea saldría sin
            #    `request_id` — justo la que más lo necesita.
            if request.url.path != "/health":
                log.info("request", extra={
                    "ruta": request.url.path,
                    "metodo": request.method,
                    "estado": respuesta.status_code,
                })
            return respuesta
        except Exception:
            # `exception()` mete el traceback dentro del JSON. Sin esto, un 500
            # aparece en los logs sin una sola pista de dónde se rompió.
            log.exception("request falló", extra={
                "ruta": request.url.path, "metodo": request.method})
            raise
        finally:
            logs.reiniciar_request_id(token)

    @app.get("/", response_class=HTMLResponse)
    def pagina_chat() -> str:
        """Sirve la SPA de app/static/chat.html, ya cargada en memoria.

        ⚠️ La PÁGINA se sirve abierta a propósito (es HTML, no datos), pero el
           /chat que consume ya exige credencial si `API_KEYS` está configurado.
        """
        return frontend.PAGINA_CHAT

    @app.get("/health")
    def health() -> dict:
        """Lo que mira el orquestador cada pocos segundos. BARATO: no llama al LLM.

        Va SIN auth: el orquestador no tiene credenciales, y si /health exigiera
        una, un fallo de configuración de las claves parecería un servicio caído
        y desataría un reinicio en bucle.
        """
        return {
            "estado": "ok",
            "modelo": settings.llm_modelo,
            "tracing": tracing.activo(),
            "listo": estado["responder"] is not None,
            # Que el modo abierto sea VISIBLE. Un servicio sin auth debe poder
            # detectarse desde fuera, no solo leyendo el .env del servidor.
            "auth_activa": auth.auth_activa(),
        }

    @app.get("/metrics", dependencies=[Depends(auth.requiere_credencial)])
    def metricas() -> dict:
        """Tokens, coste, p95 y tasa de aciertos del caché (por proceso).

        Detrás de auth: el consumo de tokens y la latencia de un servicio son
        información de negocio. Publicarlos abiertamente le dice a cualquiera
        cuánto tráfico manejas y cuánto te cuesta.
        """
        resumen = estado["colector"].resumen()
        if estado["cache"] is not None:
            resumen["cache_tasa_aciertos"] = round(estado["cache"].tasa_aciertos, 3)
        return resumen

    @app.post("/feedback", dependencies=[Depends(auth.requiere_credencial)])
    def registrar_feedback(voto: Feedback) -> dict:
        """Registra un voto y lo agrega por variante. Si el cliente no manda
        `variante`, se deriva del thread_id con la MISMA asignación pegajosa."""
        variante = voto.variante or EXPERIMENTO_PROMPT.variante_de(voto.thread_id)
        estado["feedback"].registrar(
            variante=variante, util=voto.util,
            thread_id=voto.thread_id, comentario=voto.comentario)
        return {"ok": True}

    @app.get("/feedback", dependencies=[Depends(auth.requiere_credencial)])
    def resumen_feedback() -> dict:
        """👍/👎, total y tasa_aprobacion por variante (el resultado del A/B).

        Protegido por lo mismo que /metrics: el resultado de tu experimento de
        prompts es información de negocio, y el POST hermano deja de poder
        envenenarse desde fuera (un bot votando 👎 mil veces decidiría el A/B).
        """
        return estado["feedback"].resumen()

    @app.post("/chat", dependencies=[Depends(auth.requiere_credencial)])
    async def chat(peticion: PeticionChat) -> StreamingResponse:
        """Responde en streaming SSE, atravesando las capas.

        ⚠️ La credencial se comprueba AQUÍ, en la dependencia, y no dentro de
           `_flujo`: un 401 debe salir como un 401 de verdad. Una vez abierto el
           stream SSE la cabecera ya se mandó, y solo se podría avisar por el
           canal de eventos — con un 200 en el status, que es mentir.
        """
        return StreamingResponse(
            _flujo(peticion, estado),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


async def _flujo(peticion: PeticionChat, estado: dict):
    """El generador de eventos SSE. Aquí vive el orden de las capas."""
    colector: metrics.ColectorMetricas = estado["colector"]
    cache = estado["cache"]
    variante = EXPERIMENTO_PROMPT.variante_de(peticion.thread_id)

    with metrics.Cronometro() as crono:
        # ---- 1) GUARDRAIL DE ENTRADA ----
        entrada = input_guard.revisar_entrada(peticion.mensaje)
        if not entrada.permitido:
            colector.registrar(metrics.MetricasRequest(
                modelo=settings.llm_modelo, uso=Uso(), latencia_ms=crono.latencia_ms,
                acciones_guardrail=entrada.acciones))
            yield streaming.evento_sse({"error": entrada.motivo}, evento="bloqueado")
            return
        pregunta = entrada.texto

        # ---- 2) CACHÉ SEMÁNTICO ----
        if cache is not None:
            acierto = cache.buscar(pregunta)
            if acierto is not None:
                crono.primer_token()
                for trozo in streaming.trocear(acierto.respuesta):
                    yield streaming.evento_sse({"token": trozo})
                yield streaming.evento_sse(
                    {"cache_hit": True, "similitud": round(acierto.similitud, 4),
                     "variante": variante}, evento="fin")
                colector.registrar(metrics.MetricasRequest(
                    modelo=settings.llm_modelo, uso=Uso(),
                    latencia_ms=crono.latencia_ms, ttft_ms=crono.ttft_ms,
                    cache_hit=True, acciones_guardrail=entrada.acciones))
                return

        # ---- 3) AGENTE (con grounding de precios ya cerrado dentro) ----
        try:
            respuesta = estado["responder"](pregunta, variante)
        except Exception as error:  # pragma: no cover - depende del proveedor
            # Un 429 de Groq, un timeout, el catálogo live caído. El cliente ya
            # tiene la cabecera 200 y el stream abierto: no podemos devolver un
            # 503. Se lo decimos por el canal de eventos.
            #
            # Y lo dejamos en el log CON traceback: el cliente ve un mensaje, el
            # operador necesita la pila. Antes esta rama era muda y un fallo del
            # proveedor no dejaba ni una línea. El `request_id` del middleware ya
            # viaja aquí, así que este fallo se cruza con el resto de la petición.
            log.exception("el agente falló al responder",
                          extra={"variante": variante})
            yield streaming.evento_sse({"error": str(error)}, evento="error")
            return

        # ---- 4) STREAMING de la respuesta YA verificada ----
        for trozo in streaming.trocear(respuesta.texto):
            crono.primer_token()
            yield streaming.evento_sse({"token": trozo})

        # ---- 5) CACHEAR la respuesta fiel ----
        if cache is not None:
            cache.guardar(pregunta, respuesta.texto)

        yield streaming.evento_sse({"cache_hit": False, "variante": variante}, evento="fin")

    # ---- 6) MÉTRICAS ----
    # El uso REAL viaja dentro de la respuesta del agente (suma de redacción +
    # reintento). Antes iba `Uso()` vacío y /metrics reportaba coste 0 siempre.
    colector.registrar(metrics.MetricasRequest(
        modelo=settings.llm_modelo, uso=respuesta.uso,
        latencia_ms=crono.latencia_ms, ttft_ms=crono.ttft_ms, cache_hit=False,
        acciones_guardrail=(*entrada.acciones, *respuesta.acciones)))


# El objeto que busca uvicorn: `uvicorn proyecto_retail.app.main:app`.
app = crear_app()
