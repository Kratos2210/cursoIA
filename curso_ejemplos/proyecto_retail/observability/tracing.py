"""
tracing.py · Langfuse, y cómo no depender de Langfuse
======================================================
FINALIDAD:
  Que cada consulta deje una traza forense (el prompt exacto, los productos
  recuperados, la respuesta, tokens, latencia). Cuando alguien reporte "el
  asistente me dio un precio raro el martes", la traza es la única forma de saber
  qué pasó de verdad.

LÓGICA — la degradación graceful es la tesis: el tracing es un EXTRA, nunca un
  requisito. Si Langfuse no está, o no hay llaves, el servicio responde igual.
  Aquí eso es un no-op. El código de negocio llama siempre igual; la decisión se
  toma una vez, aquí. (Espejo del tracing.py de proyecto_llmops.)

⚠️ Un observador que tumba lo observado no es observabilidad. Por eso todo aquí
   captura Exception y sigue: es de los poquísimos sitios donde un except pass
   está justificado, y conviene decir por qué.
"""
from __future__ import annotations

from proyecto_retail.app.config import settings


def activo() -> bool:
    """¿Mandamos trazas? Solo si están AMBAS llaves en el .env."""
    return settings.langfuse_activo


def crear_handler():
    """El CallbackHandler de Langfuse, o None si no hay tracing (no revienta)."""
    if not activo():
        return None
    try:
        from langfuse.callback import CallbackHandler
        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:  # pragma: no cover - depende del entorno
        return None


def callbacks() -> list:
    """La lista lista para `config={"callbacks": callbacks()}`. [] si no hay tracing."""
    handler = crear_handler()
    return [handler] if handler is not None else []


def vaciar() -> None:
    """Fuerza el envío de las trazas pendientes. Un script corto muere antes de
    que el lote de fondo salga; llamar a esto al final lo evita."""
    if not activo():
        return
    try:  # pragma: no cover - depende del entorno
        from langfuse.decorators import langfuse_context
        langfuse_context.flush()
    except Exception:  # pragma: no cover
        pass
