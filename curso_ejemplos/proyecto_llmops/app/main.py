"""
main.py · El servicio: donde las cuatro capas se hilvanan
==========================================================
FINALIDAD:
  Exponer el agente GobData por HTTP con TODA la maquinaria LLMOps en el camino.
  Este archivo no implementa ninguna de las cuatro capas: las ORDENA. Y el orden
  es la mitad del diseño.

      POST /chat
        │
        1. input_guard   → ¿ataque? corta aquí. CERO tokens gastados.
        │                  ¿PII?    anonimiza y sigue.
        2. semantic_cache→ ¿ya respondimos esto (a este rol)? HIT: coste $0.
        │
        3. agente        → RAG sobre pgvector + RBAC + tools + memoria.
        │                  Se emite token a token (SSE).
        4. output_guard  → vigila el stream con un buffer de retención.
        │
        5. cache.guardar → solo si el guardrail dejó pasar la respuesta.
        6. métricas      → tokens, coste, TTFT, latencia → Langfuse.

  ⭐ POR QUÉ ESE ORDEN, y no otro:
     - El guardrail va ANTES del caché: no queremos ni siquiera vectorizar un
       intento de inyección, y menos aún cachearlo.
     - El caché va ANTES del agente: es lo único que puede evitar la llamada cara.
     - El caché guarda DESPUÉS del guardrail de salida: se cachea lo saneado.
       Cachear la respuesta cruda serviría, en el siguiente HIT, el texto sin
       filtrar — el guardrail se ejecutaría una vez y se esquivaría para siempre.

LÓGICA — inyección de dependencias, igual que en proyecto_final:
  `crear_app(...)` recibe agente, caché y colector POR PARÁMETRO. Por eso
  `tests/test_smoke_api.py` levanta la API entera con un agente falso: sin
  Gemini, sin Postgres, sin Redis. Si esto construyera el agente al importarse,
  no habría manera de testearlo (y el `--reload` de uvicorn tardaría 10s).

Levantar:
    uv sync --extra llmops
    docker compose -f proyecto_llmops/docker-compose.yml up -d
    uv run uvicorn proyecto_llmops.app.main:app --reload --port 8000

Probar:
    curl -N -X POST http://localhost:8000/chat \\
      -H 'Content-Type: application/json' \\
      -d '{"mensaje":"¿Cuántos años se conservan los registros?","rol":"analyst"}'
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import streaming
from app.config import settings
from guardrails import input_guard
from observability import metrics, tracing
from observability.cost_model import Uso


# ==================================================================
# Los contratos de la API (pydantic los valida antes de tocar el código)
# ==================================================================
class PeticionChat(BaseModel):
    """Lo que el cliente manda. Un campo mal tipado se rechaza con un 422."""
    mensaje: str = Field(min_length=1, max_length=4000)
    # El rol decide qué normativa puede ver (RBAC) y en qué caché se busca.
    rol: str = Field(default="analyst")
    # El hilo de conversación: la memoria del agente cuelga de aquí.
    thread_id: str = Field(default="demo")

    # ⚠️ En producción el `rol` NO llega en el body: se deriva del token de
    #    autenticación. Un rol que manda el cliente es un rol que el cliente
    #    elige, y el RBAC entero se vuelve decorativo. Aquí viene en el body
    #    para que el curso sea ejecutable sin montar un proveedor de identidad.


def crear_app(agente=None, cache=None, colector=None) -> FastAPI:
    """Construye la API. Todo lo caro entra por parámetro.

    agente   : el grafo de LangGraph. Si es None, se construye el real (lento).
    cache    : un SemanticCache. Si es None, se construye con el backend que haya.
    colector : dónde se acumulan las métricas del proceso.
    """
    # `estado` guarda las piezas caras. Construir el agente tarda segundos (carga
    # el modelo de embeddings, conecta a Postgres), así que se hace en el
    # arranque del servidor, no al importar este módulo.
    estado = {
        "agente": agente,
        "cache": cache,
        "colector": colector if colector is not None else metrics.ColectorMetricas(),
    }

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """Lo caro se paga UNA vez, al arrancar, no en la primera request.

        Si se construyera dentro del endpoint, el primer usuario esperaría los
        diez segundos de todos los demás. Un arranque lento es aceptable; una
        primera request lenta, no.

        Todo lo que va ANTES del `yield` corre al arrancar; lo de después, al
        apagar. Ahí vaciamos el buffer de trazas: un proceso que muere con el
        buffer lleno pierde en silencio las trazas de sus últimas requests.
        """
        if estado["agente"] is None:          # pragma: no cover - requiere API real
            from app.agent import construir_agente_real
            estado["agente"] = construir_agente_real()
        if estado["cache"] is None:           # pragma: no cover - requiere embeddings
            from app.embeddings import crear_embeddings
            from cache.cache_backends import crear_backend
            from cache.semantic_cache import SemanticCache
            estado["cache"] = SemanticCache(crear_embeddings(), crear_backend())

        yield                                  # ← aquí el servicio atiende

        tracing.vaciar()

    app = FastAPI(
        title="GobData — servicio LLMOps",
        description="Agente de gobierno de datos con guardrails, caché semántico y tracing.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # GET /health — ¿está vivo el servicio?
    # ------------------------------------------------------------------
    @app.get("/health")
    def health() -> dict:
        """Lo que mira el orquestador (Kubernetes, docker-compose) cada pocos
        segundos. Debe ser BARATO: si el health check llama al LLM, un pico de
        latencia del proveedor tumba tus pods sanos.
        """
        return {
            "estado": "ok",
            "modelo": settings.llm_modelo_cheap,
            "tracing": tracing.activo(),
            "agente_listo": estado["agente"] is not None,
        }

    # ------------------------------------------------------------------
    # GET /metrics — el resumen del proceso
    # ------------------------------------------------------------------
    @app.get("/metrics")
    def metricas() -> dict:
        """Tokens, coste, p95 y tasa de aciertos del caché.

        ⚠️ Por proceso. Con varios workers, cada uno reporta LO SUYO. El total
           agregado lo da Langfuse (ver observability/tracing.py).
        """
        resumen = estado["colector"].resumen()
        if estado["cache"] is not None:
            resumen["cache_tasa_aciertos"] = round(estado["cache"].tasa_aciertos, 3)
        return resumen

    # ------------------------------------------------------------------
    # POST /chat — el camino completo
    # ------------------------------------------------------------------
    @app.post("/chat")
    async def chat(peticion: PeticionChat) -> StreamingResponse:
        """Responde en streaming SSE, atravesando las cuatro capas."""
        return StreamingResponse(
            _flujo(peticion, estado),
            media_type="text/event-stream",
            # Sin esto, un proxy (nginx) bufferiza la respuesta entera y el
            # streaming deja de serlo: el usuario recibe todo de golpe al final.
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


async def _flujo(peticion: PeticionChat, estado: dict):
    """El generador que produce los eventos SSE. Aquí vive el orden de las capas."""
    colector: metrics.ColectorMetricas = estado["colector"]
    cache = estado["cache"]

    with metrics.Cronometro() as crono:
        # ---- 1) GUARDRAIL DE ENTRADA -------------------------------------
        # Antes de vectorizar, antes de cachear, antes de todo.
        entrada = input_guard.revisar_entrada(peticion.mensaje)
        if not entrada.permitido:
            colector.registrar(metrics.MetricasRequest(
                modelo=settings.llm_modelo_cheap, uso=Uso(), latencia_ms=crono.latencia_ms,
                acciones_guardrail=entrada.acciones,
            ))
            yield streaming.evento_sse({"error": entrada.motivo}, evento="bloqueado")
            return

        # A partir de aquí se usa el texto SANEADO. Nunca `peticion.mensaje`.
        pregunta = entrada.texto

        # ---- 2) CACHÉ SEMÁNTICO ------------------------------------------
        # Por rol: un 'analyst' no puede recibir lo que se generó para
        # 'compliance'. Ver el aviso en cache/semantic_cache.py.
        if cache is not None:
            acierto = cache.buscar(pregunta, rol=peticion.rol)
            if acierto is not None:
                crono.primer_token()
                yield streaming.evento_sse({"token": acierto.respuesta})
                yield streaming.evento_sse(
                    {"cache_hit": True, "similitud": round(acierto.similitud, 4)},
                    evento="fin",
                )
                colector.registrar(metrics.MetricasRequest(
                    modelo=settings.llm_modelo_cheap, uso=Uso(),
                    latencia_ms=crono.latencia_ms, ttft_ms=crono.ttft_ms,
                    cache_hit=True, acciones_guardrail=entrada.acciones,
                ))
                return

        # ---- 3 y 4) AGENTE + GUARDRAIL DE SALIDA sobre el stream ----------
        guardia = streaming.GuardiaDeStream(rol=peticion.rol)
        try:
            async for token in streaming.tokens_del_agente(
                estado["agente"], pregunta, peticion.thread_id,
                callbacks=tracing.callbacks(),
            ):
                crono.primer_token()
                trozo = guardia.empujar(token)
                if guardia.bloqueado:
                    yield streaming.evento_sse({"error": guardia.motivo}, evento="bloqueado")
                    break
                if trozo:
                    yield streaming.evento_sse({"token": trozo})
            else:
                # `else` de un for: solo corre si NO hubo break, es decir, si el
                # guardrail no bloqueó. Vaciamos la cola retenida.
                cola = guardia.cerrar()
                if guardia.bloqueado:
                    yield streaming.evento_sse({"error": guardia.motivo}, evento="bloqueado")
                else:
                    if cola:
                        yield streaming.evento_sse({"token": cola})

                    # ---- 5) CACHEAR LO SANEADO, no lo crudo -----------------
                    if cache is not None:
                        cache.guardar(pregunta, guardia.texto_completo, rol=peticion.rol)

                    yield streaming.evento_sse({"cache_hit": False}, evento="fin")
        except Exception as error:  # pragma: no cover - depende del proveedor
            # Un 429 del proveedor, un timeout, Postgres caído. El cliente ya
            # tiene la cabecera 200 y el stream abierto: no podemos devolver un
            # 503. Se lo decimos por el canal de eventos.
            yield streaming.evento_sse({"error": str(error)}, evento="error")

    # ---- 6) MÉTRICAS --------------------------------------------------
    # Fuera del `with`: el cronómetro ya se cerró y la latencia es la final.
    metrica = metrics.MetricasRequest(
        modelo=settings.llm_modelo_cheap,
        uso=Uso(),          # el conteo real lo aporta el callback de Langfuse
        latencia_ms=crono.latencia_ms,
        ttft_ms=crono.ttft_ms,
        cache_hit=False,
        acciones_guardrail=(*entrada.acciones, *(("bloqueo_fuga_nivel",) if guardia.bloqueado else ())),
    )
    colector.registrar(metrica)
    tracing.registrar_uso("chat", metrica)


# El objeto que busca uvicorn: `uvicorn proyecto_llmops.app.main:app`.
# Se crea sin agente: lo construye el evento de startup, no el import.
app = crear_app()
