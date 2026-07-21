"""
llm.py · Arquitectura en cascada: modelo barato → caro, con fallback
=====================================================================
FINALIDAD:
  Resolver la tensión eterna de producción: "¿uso el modelo caro que razona
  mejor, o el barato que cuesta 10 veces menos?". Respuesta LLMOps: **los dos,
  en cascada**.

  La idea: intenta primero el modelo BARATO (rápido, económico). Si falla o si
  la complejidad del caso lo exige, escala solo al modelo FUERTE. Así la mayoría
  de las requests cuestan poco, y solo las difíciles pagan más.

  El proveedor NO está cableado aquí: sale del .env. Una sola variable
  (LLM_PROVIDER) decide si hablamos con Groq, con Ollama o con Gemini.

LÓGICA:
  - crear_modelo(nombre) : la fábrica. Traduce el .env en un ChatModel.
  - crear_llm_cheap()   : el modelo de uso cotidiano.
  - crear_llm_strong()  : el de mayor razonamiento. Se usa solo cuando hace falta.
  - crear_cascada()     : el cheap envuelto con with_fallbacks([strong]).
                          Si el cheap falla (429, error), salta al strong solo.
  - crear_cascada_con_guardrail() : versión que escala por COMPLEJIDAD, no solo
                          por error.

⭐ with_fallbacks es el mecanismo de LangChain para "si este falla, prueba este
   otro". Es la pieza que hace que una caída de un modelo NO tire tu servicio.

⭐ Cambiar de proveedor es cambiar el .env, no el código. Casi todo el mercado
   habla el dialecto de la API de OpenAI, así que un único cliente
   (ChatOpenAI + base_url) sirve para Groq, Ollama, Together u OpenAI.
   Gemini no lo habla, y por eso tiene su propia rama.

RESILIENCIA — los dos parámetros que separan un demo de un servicio:

  timeout      Sin él, el cliente espera INDEFINIDAMENTE. Un proveedor que
               acepta la conexión y no contesta nunca deja la request colgada, y
               con ella el worker que la atiende. Suficientes requests así y el
               servicio deja de responder sin que nada haya "fallado": no hay
               error que registrar, solo trabajadores esperando para siempre.

  max_retries  Un 429 (cuota por minuto) o un 503 son TRANSITORIOS: el mismo
               request funciona un segundo después. Reintentar es correcto;
               reintentar *inmediatamente* no, porque añade carga justo al
               proveedor que ya está saturado.

  ⭐ EL BACKOFF NO HAY QUE ESCRIBIRLO: el cliente `openai` ya reintenta con
     retraso EXPONENCIAL y jitter, y —mejor aún— si la respuesta trae la
     cabecera `Retry-After`, respeta el tiempo que pide el proveedor en vez de
     inventarse uno. Por eso aquí no hay `tenacity` ni un bucle propio: añadir
     una capa de reintentos por encima multiplicaría los intentos (3 tuyos × 3
     suyos = 9 llamadas por una) y estropearía la que ya funciona bien.

  ⚠️ Los reintentos y `with_fallbacks` se COMPONEN: el cheap agota sus
     reintentos y solo entonces salta al strong. Con valores altos, el peor caso
     de latencia es (reintentos × timeout) por CADA modelo de la cascada. Por eso
     el default de reintentos es 2 y no 10: quien espera al otro lado es una
     persona con un navegador abierto.
"""
from __future__ import annotations

from app.config import settings


def crear_modelo(nombre_modelo: str):
    """Construye un ChatModel del proveedor que diga el .env.

    Parámetro:
      nombre_modelo: p.ej. 'openai/gpt-oss-120b' (Groq) o 'gemini-3.1-flash-lite' (Google).

    Los imports van dentro para no pagar el coste de librerías que no se usan:
    quien corre con Groq no necesita tener instalado langchain-google-genai.
    """
    if settings.llm_es_google:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=nombre_modelo,
            temperature=settings.llm_temperatura,
            google_api_key=settings.google_api_key or None,
            timeout=settings.llm_timeout_s,
            max_retries=settings.llm_max_reintentos,
        )

    # Cualquier API compatible con OpenAI. Groq es el default del .env.example.
    from langchain_openai import ChatOpenAI
    if not settings.llm_api_key:
        raise ValueError(
            f"Falta LLM_API_KEY para el proveedor '{settings.llm_provider}' "
            f"({settings.llm_base_url}). Ponla en proyecto_llmops/.env"
        )
    return ChatOpenAI(
        model=nombre_modelo,
        temperature=settings.llm_temperatura,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        # Ver el bloque RESILIENCIA del docstring: sin estos dos, un proveedor
        # colgado se lleva por delante el worker que le esperaba.
        timeout=settings.llm_timeout_s,
        max_retries=settings.llm_max_reintentos,
    )


def crear_llm_cheap():
    """El modelo barato: rápido y económico. El de uso por defecto."""
    return crear_modelo(settings.llm_modelo_cheap)


def crear_llm_strong():
    """El modelo de mayor razonamiento. Se usa solo cuando hace falta."""
    return crear_modelo(settings.llm_modelo_strong)


def crear_cascada():
    """Cascada por FALLBACK: cheap primero, strong si el cheap falla.

    Casos típicos de salto:
      - 429 RESOURCE_EXHAUSTED del modelo cheap (cuota por minuto agotada).
      - Timeout o error transitorio del cheap.

    No escala por complejidad: para eso está crear_cascada_con_guardrail().
    """
    cheap = crear_llm_cheap()
    strong = crear_llm_strong()
    # with_fallbacks recibe la lista de "plan B" en orden. Salta al primero
    # que no falle. Si TODOS fallan, lanza el último error.
    return cheap.with_fallbacks([strong])


def crear_cascada_con_guardrail(juzgar_complejidad=None):
    """Cascada por COMPLEJIDAD: escala al strong si el guardrail lo decide.

    Aquí el cheap no se cae: responde bien, pero un guardrail (función externa)
    decide "esta pregunta es difícil, conviene el modelo fuerte" ANTES de llamar.
    Esto evita gastar tokens en el strong para preguntas triviales.

    Parámetro:
      juzgar_complejidad: callable(pregunta) -> bool. True = usar el strong.
                          Si es None, se comporta como crear_cascada() simple.

    ⭐ Esto es la arquitectura "route by complexity": la decisión de qué modelo
       usar la toma una heurística barata, no el modelo caro.
    """
    if juzgar_complejidad is None:
        return crear_cascada()

    class _CascadaConGuardrail:
        """Envoltorio que elige el modelo según la complejidad de la pregunta.

        Expone .invoke() y .with_structured_output() para que el agente lo use
        como si fuera un LLM cualquiera, sin saber que hay dos debajo.
        """
        def __init__(self):
            self._cheap = crear_llm_cheap()
            self._strong = crear_llm_strong()

        def _elegir(self, prompt):
            """¿Qué modelo uso para este prompt? Lo decide el guardrail."""
            texto = _extraer_texto(prompt)
            return self._strong if juzgar_complejidad(texto) else self._cheap

        def invoke(self, prompt, **kw):
            return self._elegir(prompt).invoke(prompt, **kw)

        def with_structured_output(self, schema, **kw):
            # Ambos modelos deben soportar structured output para que esto sea válido.
            cheap_so = self._cheap.with_structured_output(schema, **kw)
            strong_so = self._strong.with_structured_output(schema, **kw)

            class _SO:
                def invoke(self_, prompt, **k):
                    modelo = strong_so if juzgar_complejidad(_extraer_texto(prompt)) else cheap_so
                    return modelo.invoke(prompt, **k)
            return _SO()

        def bind_tools(self, tools, **kw):
            # El agente usa bind_tools; ambos modelos deben soportarlo.
            cheap_bt = self._cheap.bind_tools(tools, **kw)
            strong_bt = self._strong.bind_tools(tools, **kw)

            class _BT:
                def invoke(self_, msgs, **k):
                    modelo = strong_bt if juzgar_complejidad(_extraer_texto(msgs)) else cheap_bt
                    return modelo.invoke(msgs, **k)
            return _BT()

    return _CascadaConGuardrail()


def _extraer_texto(prompt) -> str:
    """Saca texto plano de los formatos en que llega un prompt a invoke().

    Un prompt puede ser: un string, un BaseMessage, una lista de mensajes, o un
    dict. El guardrail solo necesita el texto para juzgar complejidad.
    """
    if isinstance(prompt, str):
        return prompt
    # Lista de mensajes
    if isinstance(prompt, list):
        return " ".join(_extraer_texto(p) for p in prompt)
    # Objeto con .content (BaseMessage)
    content = getattr(prompt, "content", None)
    if content is not None:
        return content if isinstance(content, str) else str(content)
    # Dict con 'messages' o 'content'
    if isinstance(prompt, dict):
        if "messages" in prompt:
            return _extraer_texto(prompt["messages"])
        if "content" in prompt:
            return str(prompt["content"])
    return str(prompt)
