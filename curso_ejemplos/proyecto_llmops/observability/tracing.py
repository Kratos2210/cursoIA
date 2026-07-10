"""
tracing.py · Langfuse, y cómo no depender de Langfuse
======================================================
FINALIDAD:
  Que cada request deje una **traza forense**: el prompt exacto, los documentos
  recuperados, las tools invocadas, la respuesta, los tokens, la latencia de
  cada paso. Cuando alguien reporte "el asistente me dijo algo raro el martes",
  la traza es la única forma de saber qué pasó de verdad.

  Un log de texto no basta. Una llamada a un agente es un ÁRBOL (agente → tool →
  RAG → modelo → agente otra vez) y hay que poder abrirlo por ramas.

LÓGICA — la degradación graceful es la tesis del módulo:
  El tracing es un **extra**, nunca un requisito. Si Langfuse no está instalado,
  o no hay llaves, o el contenedor está caído, el servicio debe seguir
  respondiendo. Aquí eso se implementa con un no-op:

    crear_handler()  → el CallbackHandler de Langfuse, o None.
    observar(nombre) → el decorador @observe de Langfuse, o la función tal cual.

  ⭐ El código de negocio NO pregunta si hay tracing. Llama siempre igual. La
     decisión se toma una vez, aquí, y el resto del sistema no se entera.

⚠️ Un observador que tumba lo observado no es observabilidad, es un fallo con
   dashboard. Por eso todo aquí captura Exception y sigue: es de los poquísimos
   sitios donde un `except Exception: pass` está justificado, y conviene decir
   por qué en vez de dejarlo suelto.

Instalar: uv sync --extra llmops     (langfuse v2; ver el ADR-0004)
Levantar: docker compose -f proyecto_llmops/docker-compose.yml up -d langfuse
UI:       http://localhost:3000  → Settings → API Keys → péganlas en el .env
"""
from __future__ import annotations

from app.config import settings


def activo() -> bool:
    """¿Mandamos trazas? Solo si están AMBAS llaves en el .env.

    Con una sola llave, el SDK de Langfuse fallaría al autenticarse en cada
    request. Es mejor no arrancarlo que arrancarlo roto.
    """
    return settings.langfuse_activo


def crear_handler():
    """El CallbackHandler de Langfuse, o None si no hay tracing.

    Se le pasa a LangChain en `config={"callbacks": [handler]}`. LangChain se
    encarga entonces de reportar cada span del árbol: cadenas, tools, modelo.

    Devuelve None —y no revienta— si:
      - el paquete `langfuse` no está instalado (falta el extra llmops),
      - faltan las llaves,
      - el constructor falla por cualquier otra razón.
    """
    if not activo():
        return None
    try:
        # Import diferido: quien corre los tests offline no paga por importar
        # langfuse, y quien no instaló el extra no ve un ImportError.
        from langfuse.callback import CallbackHandler
        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:  # pragma: no cover - depende del entorno
        # Falta el paquete, o el host no responde, o la versión cambió la API.
        # Ninguna de las tres debe impedir que el servicio conteste.
        return None


def callbacks() -> list:
    """La lista lista para `config={"callbacks": callbacks()}`.

    Devuelve [] cuando no hay tracing, y LangChain lo acepta sin rechistar. Así
    el llamador escribe siempre la misma línea, haya Langfuse o no.
    """
    handler = crear_handler()
    return [handler] if handler is not None else []


def observar(nombre: str | None = None):
    """Decorador: convierte una función en un span de la traza.

        @observar("recuperar_normativa")
        def recuperar(...): ...

    Si Langfuse no está disponible, devuelve la función **intacta**. No un
    wrapper que no hace nada: la función misma. Sin coste, sin stack extra.
    """
    def decorador(func):
        if not activo():
            return func
        try:  # pragma: no cover - depende del entorno
            from langfuse.decorators import observe
            return observe(name=nombre or func.__name__)(func)
        except Exception:  # pragma: no cover
            return func
    return decorador


def registrar_uso(nombre: str, metrica) -> None:
    """Adjunta a la traza actual las métricas que calculó `metrics.py`.

    Langfuse ya cuenta tokens por su cuenta cuando el callback envuelve al
    modelo. Esto añade lo que Langfuse NO puede saber: si hubo cache_hit, qué
    guardrails saltaron, cuál fue el TTFT medido por nosotros.

    Silencioso por diseño: si falla, se pierde una métrica, no una respuesta.
    """
    if not activo():
        return
    try:  # pragma: no cover - depende del entorno
        from langfuse.decorators import langfuse_context
        langfuse_context.update_current_observation(
            name=nombre,
            metadata={
                "modelo": metrica.modelo,
                "cache_hit": metrica.cache_hit,
                "latencia_ms": round(metrica.latencia_ms, 1),
                "ttft_ms": round(metrica.ttft_ms, 1) if metrica.ttft_ms else None,
                "costo_usd": metrica.costo,
                "acciones_guardrail": list(metrica.acciones_guardrail),
            },
        )
    except Exception:  # pragma: no cover
        pass


def vaciar() -> None:
    """Fuerza el envío de las trazas pendientes.

    El SDK de Langfuse encola y manda en lotes, en un hilo de fondo. Un script
    corto (`run_evals.py`, `ci_gate.py`) termina antes de que ese lote salga, y
    las trazas se pierden en silencio. Llamar a esto al final lo evita.

    ⭐ Es el fallo clásico de la observabilidad en procesos efímeros: no es que
       no se instrumentara, es que el proceso murió con el buffer lleno.
    """
    if not activo():
        return
    try:  # pragma: no cover - depende del entorno
        from langfuse.decorators import langfuse_context
        langfuse_context.flush()
    except Exception:  # pragma: no cover
        pass
