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

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from proyecto_retail.app import frontend, streaming
from proyecto_retail.app.config import settings
from proyecto_retail.guardrails import input_guard
from proyecto_retail.observability import metrics, tracing
from proyecto_retail.observability.cost_model import Uso
from proyecto_retail.observability.feedback import ColectorFeedback
from proyecto_retail.prompts.experimentos import Experimento

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
            from proyecto_retail.app.etl import cargar_catalogo_demo
            estado["catalogo"] = cargar_catalogo_demo()
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
        tracing.vaciar()

    app = FastAPI(
        title="Sifrah — asistente de compras (LLMOps)",
        description="Asistente de compras retail con guardrail de precios, caché semántico, A/B de prompts y tracing.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/", response_class=HTMLResponse)
    def pagina_chat() -> str:
        """Sirve la SPA de app/static/chat.html, ya cargada en memoria."""
        return frontend.PAGINA_CHAT

    @app.get("/health")
    def health() -> dict:
        """Lo que mira el orquestador cada pocos segundos. BARATO: no llama al LLM."""
        return {
            "estado": "ok",
            "modelo": settings.llm_modelo,
            "tracing": tracing.activo(),
            "listo": estado["responder"] is not None,
        }

    @app.get("/metrics")
    def metricas() -> dict:
        """Tokens, coste, p95 y tasa de aciertos del caché (por proceso)."""
        resumen = estado["colector"].resumen()
        if estado["cache"] is not None:
            resumen["cache_tasa_aciertos"] = round(estado["cache"].tasa_aciertos, 3)
        return resumen

    @app.post("/feedback")
    def registrar_feedback(voto: Feedback) -> dict:
        """Registra un voto y lo agrega por variante. Si el cliente no manda
        `variante`, se deriva del thread_id con la MISMA asignación pegajosa."""
        variante = voto.variante or EXPERIMENTO_PROMPT.variante_de(voto.thread_id)
        estado["feedback"].registrar(
            variante=variante, util=voto.util,
            thread_id=voto.thread_id, comentario=voto.comentario)
        return {"ok": True}

    @app.get("/feedback")
    def resumen_feedback() -> dict:
        """👍/👎, total y tasa_aprobacion por variante (el resultado del A/B)."""
        return estado["feedback"].resumen()

    @app.post("/chat")
    async def chat(peticion: PeticionChat) -> StreamingResponse:
        """Responde en streaming SSE, atravesando las capas."""
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
