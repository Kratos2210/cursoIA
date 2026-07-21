"""
llm.py · El modelo de chat, del proveedor que diga el .env
===========================================================
FINALIDAD:
  Una sola fábrica de modelo para todo el proyecto. Cambiar de proveedor es
  cambiar el .env, no el código: casi todo el mercado (Groq, Ollama, Together,
  OpenAI) habla el dialecto de la API de OpenAI, así que un único cliente
  (ChatOpenAI + base_url) los cubre. Gemini no lo habla y tiene su rama propia.

  Es el mismo patrón que `util.py` del curso, aquí como módulo del paquete para
  que el proyecto sea autónomo (no depende de la raíz de curso_ejemplos/).

⚠️ EL PARCHE function_calling. Por defecto `with_structured_output()` pide al
   proveedor `response_format: json_schema`. OpenAI lo soporta; Groq solo en
   algunos modelos, y no hay garantía de que el que tengas en el .env sea uno de
   ellos. `method="function_calling"` obtiene lo mismo declarando una tool con la
   forma del esquema: funciona en todos los modelos con tool calling.
"""
from __future__ import annotations

from proyecto_retail.app.config import settings


def crear_llm():
    """Construye el ChatModel del proveedor activo (temperatura del .env)."""
    if settings.llm_es_google:
        # Gemini, como en el resto del curso. Import diferido: quien corre con
        # Groq no paga por importar langchain-google-genai.
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.llm_modelo,
            temperature=settings.llm_temperatura,
            google_api_key=settings.google_api_key or None,
            timeout=settings.llm_timeout_s,
            max_retries=settings.llm_max_reintentos,
        )

    from langchain_openai import ChatOpenAI

    if not settings.llm_api_key:
        raise ValueError(
            f"Falta LLM_API_KEY para el proveedor '{settings.llm_provider}' "
            f"({settings.llm_base_url}). Ponla en proyecto_retail/.env"
        )

    class _ChatCompatible(ChatOpenAI):
        """ChatOpenAI con with_structured_output en modo function_calling."""

        def with_structured_output(self, schema, *, method="function_calling", **kwargs):
            return super().with_structured_output(schema, method=method, **kwargs)

    return _ChatCompatible(
        model=settings.llm_modelo,
        temperature=settings.llm_temperatura,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        # RESILIENCIA. Sin `timeout`, el cliente espera indefinidamente a un
        # proveedor que acepta la conexión y no contesta: la request queda
        # colgada y con ella el worker, sin un solo error que registrar.
        # `max_retries` cubre los transitorios (429 de cuota, 503). No hace
        # falta escribir el backoff: el cliente `openai` ya reintenta con
        # retraso exponencial + jitter y respeta la cabecera `Retry-After`
        # cuando el proveedor la manda. Envolver esto en otra capa de
        # reintentos solo multiplicaría las llamadas.
        timeout=settings.llm_timeout_s,
        max_retries=settings.llm_max_reintentos,
    )
