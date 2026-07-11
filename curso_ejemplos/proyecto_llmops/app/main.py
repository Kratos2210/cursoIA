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
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import frontend, streaming
from app.config import settings
from guardrails import input_guard
from observability import metrics, tracing
from observability.cost_model import Uso
from observability.feedback import ColectorFeedback
from prompts import experimentos

# Las variantes del A/B de prompts. A = el prompt actual (agente_gobdata),
# B = la variante concisa (agente_gobdata_conciso.yaml). El `thread_id` fija cuál
# ve cada usuario, de forma pegajosa (ver prompts/experimentos.py): la variante
# elige el AGENTE (cada uno con el prompt de su variante), y el feedback se agrega
# por variante. Lazo A/B cerrado de punta a punta (ver ADR-0006).
EXPERIMENTO_PROMPT = experimentos.Experimento(
    nombre="prompt_conciso",
    variantes=("agente_gobdata", "agente_gobdata_conciso"),
)


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


class Feedback(BaseModel):
    """El voto 👍/👎 sobre una respuesta. Cierra el lazo del A/B de prompts.

    thread_id : la conversación votada. Fija de forma pegajosa qué variante vio
                el usuario, así que el servidor puede recalcularla sin confiar en
                lo que mande el cliente.
    util      : 👍=true, 👎=false.
    variante  : opcional. Si el cliente no la manda, el servidor la deriva del
                thread_id (la misma asignación pegajosa del evento `fin`).
    comentario: opcional, texto libre del "¿por qué?".
    """
    thread_id: str = Field(default="demo")
    util: bool
    variante: str | None = None
    comentario: str | None = Field(default=None, max_length=2000)


def crear_app(agente=None, agentes=None, cache=None, colector=None, feedback=None) -> FastAPI:
    """Construye la API. Todo lo caro entra por parámetro.

    agente   : UN grafo de LangGraph, atajo para inyectar el mismo agente en
               todas las variantes (lo usan los tests que no miden el prompt).
    agentes  : {variante: grafo}, un agente por variante del A/B (lo que arma el
               servicio real). Si ambos son None, se construyen al arrancar.
    cache    : un SemanticCache. Si es None, se construye con el backend que haya.
    colector : dónde se acumulan las métricas del proceso.
    feedback : dónde se acumulan los votos 👍/👎 del A/B. Si es None, se crea uno
               limpio. Como las métricas, va por parámetro para poder inyectar
               uno vacío en cada test.
    """
    # Normalizamos a un mapa {variante: agente}. Un `agente` suelto se replica a
    # todas las variantes: sirve para los tests que ejercitan el pipeline sin
    # medir el efecto del prompt. `None` en ambos → se construye al arrancar.
    if agentes is not None:
        agentes_iniciales = dict(agentes)
    elif agente is not None:
        agentes_iniciales = {v: agente for v in EXPERIMENTO_PROMPT.variantes}
    else:
        agentes_iniciales = None

    # `estado` guarda las piezas caras. Construir el agente tarda segundos (carga
    # el modelo de embeddings, conecta a Postgres), así que se hace en el
    # arranque del servidor, no al importar este módulo.
    estado = {
        "agentes": agentes_iniciales,
        "cache": cache,
        "colector": colector if colector is not None else metrics.ColectorMetricas(),
        "feedback": feedback if feedback is not None else ColectorFeedback(),
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
        if estado["agentes"] is None:         # pragma: no cover - requiere API real
            from app.agent import construir_agentes_por_variante
            # Un agente por variante, con SU prompt; comparten las piezas caras.
            estado["agentes"] = construir_agentes_por_variante(
                EXPERIMENTO_PROMPT.variantes)
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
    # GET / — el frontend de chat (la cara visible del servicio)
    # ------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def pagina_chat() -> str:
        """Sirve la SPA vainilla de `app/static/chat.html`, ya cargada en memoria.

        Devolver un string ya leído (frontend.PAGINA_CHAT) es lo más barato
        posible: cero E/S por request. La página consume /chat por SSE con
        fetch+ReadableStream y vota en /feedback — el mismo servicio, con cara.

        ⚠️ En producción esto va detrás de auth y del mismo origen (o CORS
           explícito): la demo lo sirve abierto para ser ejecutable sin montar
           un proveedor de identidad, igual que el `rol` viaja en el body.
        """
        return frontend.PAGINA_CHAT

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
            "agente_listo": estado["agentes"] is not None,
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
    # POST /feedback — el voto 👍/👎 (el otro extremo del A/B)
    # ------------------------------------------------------------------
    @app.post("/feedback")
    def registrar_feedback(voto: Feedback) -> dict:
        """Registra un voto y lo agrega por variante. Vive en su PROPIO endpoint:

        no ensucia el `resumen()` de /metrics (hay tests que fijan sus claves) y
        deja claro que coste/latencia y satisfacción son dos ejes distintos.

        Si el cliente no manda `variante`, se deriva del `thread_id` con la MISMA
        asignación pegajosa del evento `fin`, para que el voto se atribuya a la
        variante que el usuario vio de verdad.
        """
        variante = voto.variante or EXPERIMENTO_PROMPT.variante_de(voto.thread_id)
        estado["feedback"].registrar(
            variante=variante,
            util=voto.util,
            thread_id=voto.thread_id,
            comentario=voto.comentario,
        )
        return {"ok": True}

    # ------------------------------------------------------------------
    # GET /feedback — la tasa de aprobación por variante (el resultado del A/B)
    # ------------------------------------------------------------------
    @app.get("/feedback")
    def resumen_feedback() -> dict:
        """👍/👎, total y `tasa_aprobacion` por variante. Comparar esa tasa entre
        A y B es lo que decide el experimento (con suficientes votos: ver ADR-0006)."""
        return estado["feedback"].resumen()

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

    # ---- 0) A/B DE PROMPTS -------------------------------------------
    # El thread_id fija la variante de forma PEGAJOSA: la misma conversación cae
    # siempre en la misma (ver prompts/experimentos.py). La variante (a) elige el
    # AGENTE que responde —cada uno con el prompt de su variante— y (b) se anuncia
    # en el evento `fin` para que el cliente la devuelva en su voto 👍/👎, y así el
    # feedback se agregue por variante. El lazo A/B queda cerrado (ver ADR-0006).
    variante = EXPERIMENTO_PROMPT.variante_de(peticion.thread_id)
    agente = estado["agentes"][variante]

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
                    {"cache_hit": True, "similitud": round(acierto.similitud, 4),
                     "variante": variante},
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
                agente, pregunta, peticion.thread_id,
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

                    yield streaming.evento_sse(
                        {"cache_hit": False, "variante": variante}, evento="fin")
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
