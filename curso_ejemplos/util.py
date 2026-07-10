"""
util.py · Funciones de apoyo compartidas por los ejemplos del curso
===================================================================
FINALIDAD:
  Centralizar dos piezas de lógica PURA (sin LLM) que se repiten en casi
  todos los ejemplos, para:
    a) No duplicar el mismo bloque try/except en 10 archivos.
    b) Poder TESTEAR esa lógica sin llamar a la API (ver tests/test_util.py).

  Estos ejemplos siguen siendo autónomos: si los corres tal cual,
  funcionan. Al importar de aquí simplemente evitan repetirse.

LÓGICA:
  - es_error_cuota(exc)  : reconoce un error 429 / RESOURCE_EXHAUSTED.
  - mensaje_cuota()      : el texto amable que mostramos al estudiante.
  - trocear_parrafos(texto): parte un texto en fragmentos por párrafo.
  - crear_llm()          : el modelo de chat del proveedor que diga el .env.
"""

import os

# ==================================================================
# EL PROVEEDOR DEL MODELO DE CHAT
# ==================================================================
# La cuota gratuita de Gemini es MUY corta: unas pocas decenas de llamadas por
# minuto y un tope diario que se agota en una tarde de ejercicios. Groq regala
# un cupo mucho más generoso y sirve `qwen/qwen3-32b`, que basta de sobra para
# todo lo que se practica aquí.
#
# ⭐ POR QUÉ UNA SOLA CLASE SIRVE PARA CASI TODOS. Casi todo el mercado (Groq,
#    Ollama, Together, OpenAI, OpenRouter, DeepSeek) habla el MISMO dialecto:
#    la API de OpenAI. Por eso `ChatOpenAI` + `base_url` los cubre a todos.
#    Gemini y Claude NO lo hablan, y por eso tienen su propia rama. No es que
#    LangChain tenga un adaptador por proveedor: es que el mercado convergió
#    en un protocolo.
#
# Cambiar de proveedor es cambiar el .env, NO el código:
#
#   LLM_PROVIDER=groq       → qwen/qwen3-32b vía Groq. Llave gratis en
#                             https://console.groq.com/keys  (GROQ_API_KEY)
#   LLM_PROVIDER=google     → Gemini, el proveedor por defecto del curso.
#   LLM_PROVIDER=ollama     → un modelo en tu máquina. Sin llave y sin cuota.
#   LLM_PROVIDER=openai     → gpt-5.4-mini. Llave (de pago) en
#                             https://platform.openai.com/api-keys  (OPENAI_API_KEY)
#   LLM_PROVIDER=anthropic  → claude-haiku-4-5. Rama propia, como Gemini. Llave en
#                             https://console.anthropic.com/settings/keys  (ANTHROPIC_API_KEY)
#   LLM_PROVIDER=openrouter → agregador: UNA llave para cientos de modelos, con
#                             variantes ':free'. https://openrouter.ai/keys  (OPENROUTER_API_KEY)
#   LLM_PROVIDER=deepseek   → deepseek-v4-flash. De pago, pero muy barato. Llave en
#                             https://platform.deepseek.com/api_keys  (DEEPSEEK_API_KEY)
PROVEEDOR_POR_DEFECTO = "google"

# El modelo que usa cada proveedor si no dices otro (LLM_MODELO en el .env).
MODELOS_POR_DEFECTO = {
    "google": "gemini-2.0-flash",
    "groq": "qwen/qwen3-32b",
    "ollama": "qwen3:8b",
    "openai": "gpt-5.4-mini",
    "anthropic": "claude-haiku-4-5",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    # OJO: `deepseek-chat` y `deepseek-reasoner` son alias que DeepSeek deprecó
    # el 2026-07-24. Apuntamos al nombre real: v4-flash sirve los dos modos.
    "deepseek": "deepseek-v4-flash",
}

# Proveedores con CLASE PROPIA en LangChain (no hablan el dialecto de OpenAI),
# y de qué variable de entorno sale su llave. `variable_de_llave()` mira aquí
# PRIMERO; los demás proveedores se resuelven por _COMPATIBLES_OPENAI.
_PROVEEDORES_NATIVOS = {
    "google": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

# Dónde vive la API de cada proveedor compatible con OpenAI, y de qué variable
# de entorno sale su llave.
_COMPATIBLES_OPENAI = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "ollama": ("http://localhost:11434/v1", "OLLAMA_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
}


def proveedor() -> str:
    """Qué proveedor toca, según LLM_PROVIDER. Por defecto, Google."""
    return os.getenv("LLM_PROVIDER", PROVEEDOR_POR_DEFECTO).strip().lower()


def modelo_por_defecto(nombre_proveedor: str | None = None) -> str:
    """El modelo de ese proveedor. LLM_MODELO en el .env manda sobre esto."""
    nombre_proveedor = nombre_proveedor or proveedor()
    if (elegido := os.getenv("LLM_MODELO")):
        return elegido
    if nombre_proveedor not in MODELOS_POR_DEFECTO:
        raise ValueError(
            f"LLM_PROVIDER='{nombre_proveedor}' no existe. "
            f"Opciones: {', '.join(sorted(MODELOS_POR_DEFECTO))}."
        )
    return MODELOS_POR_DEFECTO[nombre_proveedor]


def variable_de_llave(nombre_proveedor: str | None = None) -> str:
    """Cómo se llama la variable de entorno con la llave de ese proveedor."""
    nombre_proveedor = nombre_proveedor or proveedor()
    if nombre_proveedor in _PROVEEDORES_NATIVOS:
        return _PROVEEDORES_NATIVOS[nombre_proveedor]
    if nombre_proveedor in _COMPATIBLES_OPENAI:
        return _COMPATIBLES_OPENAI[nombre_proveedor][1]
    raise ValueError(f"LLM_PROVIDER='{nombre_proveedor}' no existe.")


def requiere_llm_key() -> str | None:
    """Mensaje de error si falta la llave del proveedor activo; None si está ok.

    La versión de `requiere_api_key()` que entiende de proveedores. Ollama corre
    en tu máquina y no necesita llave: ahí siempre devuelve None.
    """
    activo = proveedor()
    if activo == "ollama":
        return None
    variable = variable_de_llave(activo)
    if not os.getenv(variable):
        return (f"❌ Falta {variable} (LLM_PROVIDER={activo}). "
                f"Copia .env.example a .env y pon tu llave.")
    return None


# Modelos "de razonamiento": antes de responder escriben su cadena de
# pensamiento. En Groq, esa cadena llega DENTRO del contenido, envuelta en
# <think>…</think>, y ensucia todas las salidas del curso.
#
# `reasoning_format: "hidden"` le dice a Groq que la descarte y devuelva solo la
# respuesta. ⚠️ Es un parámetro específico de Groq y **solo lo aceptan los
# modelos de razonamiento**: mandárselo a llama-3.3-70b devuelve un 400
# ("`reasoning_format` is not supported with this model"). Por eso se envía
# únicamente cuando el nombre del modelo coincide con esta lista.
_MODELOS_DE_RAZONAMIENTO = ("qwen3", "deepseek-r1", "gpt-oss")


def _es_modelo_de_razonamiento(modelo: str) -> bool:
    m = modelo.lower()
    return any(marca in m for marca in _MODELOS_DE_RAZONAMIENTO)


def _crear_chat_openai_compatible(modelo: str, temperature: float, activo: str):
    """Un ChatOpenAI apuntado a Groq/Ollama/… con dos parches necesarios."""
    from langchain_openai import ChatOpenAI

    base_url, variable = _COMPATIBLES_OPENAI[activo]

    extra: dict = {}
    # ⚠️ Cada proveedor esconde el <think> con SU parámetro; no son intercambiables
    #    (mandarle `reasoning_format` a quien no es Groq devuelve un 400).
    if activo == "groq" and _es_modelo_de_razonamiento(modelo):
        # "hidden" descarta el <think>; "raw" lo deja dentro del contenido.
        # `reasoning_format` es EXCLUSIVO de Groq.
        extra["reasoning_format"] = os.getenv("GROQ_RAZONAMIENTO", "hidden")
    elif activo == "openrouter" and _es_modelo_de_razonamiento(modelo):
        # OpenRouter unifica el suyo bajo `reasoning`: {"exclude": True} descarta
        # la cadena de pensamiento (el equivalente al "hidden" de Groq).
        # DeepSeek y OpenAI no necesitan parche: deepseek-v4-flash sale en modo
        # NO pensante por defecto (el modo pensante se pide con `thinking`), y
        # cuando piensa devuelve el razonamiento en un campo APARTE del
        # contenido, así que no ensucia las salidas del curso.
        extra["reasoning"] = {"exclude": True}

    class _ChatCompatible(ChatOpenAI):
        """ChatOpenAI con `with_structured_output` en modo function_calling.

        ⚠️ POR QUÉ ESTE PARCHE. Por defecto, `with_structured_output()` pide al
        proveedor un `response_format: json_schema`. OpenAI lo soporta; **Groq
        solo lo soporta en algunos modelos**, y `qwen/qwen3-32b` no está entre
        ellos: devuelve un 400 y el TEMA 05 del curso se cae en seco.

        `method="function_calling"` obtiene el mismo resultado por otro camino:
        le declara al modelo una herramienta con la forma del esquema y le pide
        que la llame. Funciona en todos los modelos con tool calling, que son
        justo los que este curso necesita de todas formas.
        """

        def with_structured_output(self, schema, *, method="function_calling", **kwargs):
            return super().with_structured_output(schema, method=method, **kwargs)

    return _ChatCompatible(
        model=modelo,
        temperature=temperature,
        base_url=os.getenv("LLM_BASE_URL", base_url),
        # Ollama no valida la llave, pero el cliente de OpenAI exige que exista.
        api_key=os.getenv(variable, "no-hace-falta"),
        extra_body=extra or None,
    )


def crear_llm(temperature: float = 0.0, modelo: str | None = None):
    """El modelo de chat del proveedor que diga el .env.

    Todo el curso llama a ESTO en vez de instanciar `ChatGoogleGenerativeAI`
    a mano. Así, cuando la cuota de Gemini se agote a mitad de una tarde, basta
    con cambiar dos líneas del .env para seguir practicando con Groq.

    Los imports van dentro a propósito: quien corre con Groq no debería pagar
    el coste de importar `langchain-google-genai`, ni al revés.
    """
    activo = proveedor()
    modelo = modelo or modelo_por_defecto(activo)

    if (error := requiere_llm_key()):
        raise SystemExit(error)

    if activo == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=modelo, temperature=temperature)

    if activo == "anthropic":
        # Claude, como Gemini, NO habla el dialecto de OpenAI → rama propia con
        # su clase de LangChain. El import va dentro a propósito, por el mismo
        # motivo que las demás ramas: quien corre con otro proveedor no paga el
        # coste de importar `langchain-anthropic`.
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=modelo, temperature=temperature)

    return _crear_chat_openai_compatible(modelo, temperature, activo)


# ==================================================================
# LOS EMBEDDINGS · donde la analogía con el chat se rompe
# ==================================================================
# El CHAT se cambia de proveedor con una variable de entorno. Los EMBEDDINGS,
# no. Hay dos razones, y las dos importan:
#
#   1) **Groq no ofrece endpoint de embeddings.** Ni Ollama por defecto. Si
#      mueves el chat a Groq, el RAG (temas 11, 12 y el proyecto final) se queda
#      sin quien vectorice.
#
#   2) ⚠️ **Cambiar de modelo de embeddings INVALIDA el índice entero.** No es
#      como cambiar de modelo de chat, donde la peor consecuencia es una
#      respuesta distinta. Los vectores de `gemini-embedding-001` y los de
#      MiniLM viven en espacios distintos: comparar unos con otros no da un
#      resultado peor, da un resultado SIN SENTIDO. Hay que reindexar.
#
# Por eso hay una salida propia: calcular los embeddings **en tu máquina**.
# Cero cuota, cero red (tras la primera descarga), y sin depender de que ningún
# proveedor mantenga vivo un endpoint.
#
#   EMBEDDINGS_PROVIDER=google     → gemini-embedding-001. Por defecto. Gasta cuota.
#   EMBEDDINGS_PROVIDER=fastembed  → un modelo multilingüe en ONNX, en local.
#                                    Requiere: uv sync --extra emb
EMBEDDINGS_POR_DEFECTO = "google"

# Multilingüe a propósito: los documentos del curso están en español.
MODELO_FASTEMBED = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODELO_EMBEDDINGS_GOOGLE = "gemini-embedding-001"


class _EmbeddingsFastEmbed:
    """Adaptador mínimo de fastembed a la interfaz Embeddings de LangChain.

    fastembed devuelve generadores de `np.ndarray`; LangChain espera
    `list[list[float]]`. Traducir entre ambos es todo lo que hace esta clase.
    """

    def __init__(self, modelo: str):
        from fastembed import TextEmbedding
        self._modelo = TextEmbedding(modelo)

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._modelo.embed(textos)]

    def embed_query(self, texto: str) -> list[float]:
        # embed() siempre trabaja en lote: le pasamos uno y sacamos el primero.
        return self.embed_documents([texto])[0]


def proveedor_embeddings() -> str:
    """Qué motor de embeddings toca, según EMBEDDINGS_PROVIDER."""
    return os.getenv("EMBEDDINGS_PROVIDER", EMBEDDINGS_POR_DEFECTO).strip().lower()


def crear_embeddings():
    """El modelo que convierte texto en vectores, según el .env.

    Los ejemplos de RAG llaman a ESTO. Si corres con Groq y no quieres gastar la
    cuota de Gemini solo para vectorizar, pon `EMBEDDINGS_PROVIDER=fastembed`.

    ⚠️ Si cambias de motor con un índice ya construido, **reconstrúyelo**. Los
       ejemplos del curso lo reconstruyen en cada arranque, así que aquí no
       muerde; en producción sí (ver `proyecto_llmops/app/embeddings.py`).
    """
    motor = proveedor_embeddings()

    if motor == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise SystemExit(
                "❌ Falta GOOGLE_API_KEY: los embeddings por defecto son de Gemini.\n"
                "   Groq no ofrece embeddings. Dos salidas:\n"
                "     a) pon GOOGLE_API_KEY en el .env (el chat puede seguir en Groq), o\n"
                "     b) calcúlalos en local:  uv sync --extra emb\n"
                "        y añade al .env:      EMBEDDINGS_PROVIDER=fastembed"
            )
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model=os.getenv("EMBEDDINGS_MODELO", MODELO_EMBEDDINGS_GOOGLE)
        )

    if motor == "fastembed":
        try:
            return _EmbeddingsFastEmbed(os.getenv("EMBEDDINGS_MODELO", MODELO_FASTEMBED))
        except ImportError as exc:
            raise SystemExit(
                "❌ EMBEDDINGS_PROVIDER=fastembed necesita el paquete 'fastembed'.\n"
                "   Instálalo:  uv sync --extra emb\n"
                "   (la primera vez descarga el modelo, ~220 MB; después va offline)"
            ) from exc

    raise ValueError(
        f"EMBEDDINGS_PROVIDER='{motor}' no existe. Opciones: google, fastembed."
    )


def es_error_cuota(exc: BaseException) -> bool:
    """¿Es esta excepción un error de cuota de Gemini (429)?

    El plan gratuito devuelve 'RESOURCE_EXHAUSTED' (código HTTP 429) cuando
    gastas el cupo por minuto o por día. No es un bug del código: solo hay
    que esperar o cambiar de modelo. Esta función lo distingue de otros errores.
    """
    texto = str(exc)
    return "RESOURCE_EXHAUSTED" in texto or "429" in texto


def mensaje_cuota() -> str:
    """El mensaje amable que mostramos cuando se agota la cuota.

    Cambia según el proveedor: decirle "usa gemini-2.5-flash" a quien está
    corriendo contra Groq no le sirve de nada.
    """
    if proveedor() == "google":
        return ("⏳ Cuota de Gemini agotada (429). Espera unos minutos, usa "
                "'gemini-2.5-flash', o pásate a Groq: LLM_PROVIDER=groq en tu .env "
                "(cupo gratuito mucho más generoso).")
    return (f"⏳ Cuota agotada (429) en el proveedor '{proveedor()}'. "
            f"Espera unos minutos o cambia LLM_MODELO en tu .env.")


def trocear_parrafos(texto: str) -> list[str]:
    """Parte un texto en fragmentos por párrafo (separados por línea en blanco).

    Es el mismo troceado que usan el TEMA 11 (RAG), el TEMA 12 (híbrido) y
    el proyecto final: split por '\\n\\n' descartando vacíos y quitando
    espacios a los bordes. Centralizarlo aquí permite testearlo una sola vez.
    """
    return [p.strip() for p in texto.split("\n\n") if p.strip()]


def cargar_var_entorno() -> None:
    """Carga el .env si existe. Es idempotente (no falla si ya estaba cargado)."""
    from dotenv import load_dotenv
    load_dotenv()


def requiere_api_key() -> str | None:
    """Alias histórico de `requiere_llm_key()`. Mismo comportamiento.

    Antes comprobaba GOOGLE_API_KEY a secas, porque el curso solo hablaba con
    Gemini. Ahora todos los ejemplos respetan `LLM_PROVIDER`, así que validar la
    llave de Google cuando el alumno corre contra Groq sería mentirle.

    Se mantiene el nombre para no romper el código que alguien ya haya copiado.
    """
    return requiere_llm_key()
