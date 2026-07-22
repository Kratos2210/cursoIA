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
# un cupo mucho más generoso y sirve modelos abiertos que bastan de sobra para
# todo lo que se practica aquí.
#
# ⚠️ LOS PROVEEDORES APAGAN MODELOS. Los IDs de esta tabla son una FOTO CON
#    FECHA, no una verdad permanente: si un día tu proveedor responde
#    "model not found" o "model_decommissioned", NO es tu código — es que
#    retiraron ese modelo. La salida son 30 segundos: copia un ID vigente de la
#    página oficial del proveedor y ponlo en `LLM_MODELO` de tu .env, que gana
#    sobre esta tabla (ver `modelo_por_defecto()` más abajo). Sin tocar código.
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
#   LLM_PROVIDER=groq       → el modelo abierto por defecto de Groq (ver la tabla
#                             de abajo). Llave gratis en
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
#   LLM_PROVIDER=kimi       → kimi-k2.6, de Moonshot. De pago. Llave en
#                             https://platform.kimi.ai  (MOONSHOT_API_KEY).
#                             ⚠️ NO acepta temperature=0 (ver más abajo): sirve
#                             para explorarlo, no para los ejemplos del curso.
PROVEEDOR_POR_DEFECTO = "google"

# El modelo que usa cada proveedor si no dices otro (LLM_MODELO en el .env).
# Verificado contra las páginas oficiales de cada proveedor el 2026-07-21.
MODELOS_POR_DEFECTO = {
    "google": "gemini-3.1-flash-lite",
    # OJO: aquí vivía `qwen/qwen3-32b` hasta que Groq lo retiró (2026-07).
    # gpt-oss-120b es su reemplazo abierto: mismo perfil (razona antes de
    # responder) y más barato ($0.15/$0.60 por 1M tokens, 131K de contexto).
    "groq": "openai/gpt-oss-120b",
    "ollama": "qwen3:8b",
    "openai": "gpt-5.4-mini",
    "anthropic": "claude-haiku-4-5",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    # OJO: `deepseek-chat` y `deepseek-reasoner` son alias que DeepSeek deprecó
    # el 2026-07-24. Apuntamos al nombre real: v4-flash sirve los dos modos.
    "deepseek": "deepseek-v4-flash",
    # Kimi (Moonshot). Ponemos el tier BARATO, como en los demás proveedores de
    # pago: `kimi-k2.6` cuesta $0.95/$4.00 por 1M (256K de contexto) frente a los
    # $3.00/$15.00 del flagship `kimi-k3`. Y NO ponemos `kimi-k2.5`, que es más
    # barato todavía ($0.60/$3.00): Moonshot ya lo cerró a las cuentas nuevas y lo
    # apaga del todo el 2026-08-31 — un default que caduca en un mes no es un
    # default. Consultado el 2026-07-21 en platform.kimi.ai/docs/pricing.
    "kimi": "kimi-k2.6",
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
    # OJO al desajuste de nombres, y no es una errata: el proveedor se llama
    # `kimi` porque así se llama el producto, pero la EMPRESA es Moonshot AI y su
    # SDK espera la llave en `MOONSHOT_API_KEY`. Copiar el nombre de la variable
    # de la doc oficial, y no deducirlo del nombre del modelo, es la diferencia
    # entre que funcione a la primera y un 401 que nadie sabe de dónde sale.
    "kimi": ("https://api.moonshot.ai/v1", "MOONSHOT_API_KEY"),
}


def proveedor() -> str:
    """Qué proveedor toca, según LLM_PROVIDER. Por defecto, Google."""
    return os.getenv("LLM_PROVIDER", PROVEEDOR_POR_DEFECTO).strip().lower()


def modelo_por_defecto(nombre_proveedor: str | None = None) -> str:
    """El modelo de ese proveedor. LLM_MODELO en el .env manda sobre esto.

    Ese orden —primero el .env, después la tabla— es el que te salva cuando un
    proveedor apaga un modelo: pones el ID nuevo en `LLM_MODELO` y sigues, sin
    esperar a que actualicemos el curso.
    """
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
# pensamiento. El problema es DÓNDE la devuelve cada proveedor: si llega DENTRO
# del contenido, envuelta en <think>…</think>, ensucia todas las salidas del
# curso; si llega en un campo aparte, no molesta a nadie.
#
# `reasoning_format: "hidden"` le dice a Groq que la descarte. ⚠️ Es un parámetro
# específico de Groq y **solo lo aceptan algunos modelos**: mandárselo a
# llama-3.3-70b devuelve un 400 ("`reasoning_format` is not supported with this
# model"). Por eso se envía únicamente cuando el modelo coincide con esta lista.
_MODELOS_DE_RAZONAMIENTO = ("qwen3", "deepseek-r1", "gpt-oss")

# …y dentro de esa lista, la familia gpt-oss es la EXCEPCIÓN de Groq: es de
# razonamiento, pero NO acepta `reasoning_format` (la doc de Groq lo dice
# explícitamente) y usa `include_reasoning` en su lugar. Además su razonamiento
# ya viaja en un campo APARTE (`message.reasoning`), así que el contenido sale
# limpio de todos modos — como con deepseek-v4-flash. Confundir los dos
# parámetros es un 400 en la primera llamada, que es justo lo que no queremos
# que le pase a nadie el día 1 del curso.
_SIN_REASONING_FORMAT_EN_GROQ = ("gpt-oss",)


def _es_modelo_de_razonamiento(modelo: str) -> bool:
    m = modelo.lower()
    return any(marca in m for marca in _MODELOS_DE_RAZONAMIENTO)


def _acepta_reasoning_format_en_groq(modelo: str) -> bool:
    """Si el modelo razona Y Groq le admite `reasoning_format` (gpt-oss no)."""
    m = modelo.lower()
    return (
        _es_modelo_de_razonamiento(modelo)
        and not any(marca in m for marca in _SIN_REASONING_FORMAT_EN_GROQ)
    )


def _crear_chat_openai_compatible(modelo: str, temperature: float, activo: str):
    """Un ChatOpenAI apuntado a Groq/Ollama/… con dos parches necesarios."""
    from langchain_openai import ChatOpenAI

    base_url, variable = _COMPATIBLES_OPENAI[activo]

    extra: dict = {}
    # ⚠️ Cada proveedor esconde el <think> con SU parámetro; no son intercambiables
    #    (mandarle `reasoning_format` a quien no es Groq devuelve un 400).
    if activo == "groq" and _acepta_reasoning_format_en_groq(modelo):
        # "hidden" descarta el <think>; "raw" lo deja dentro del contenido.
        # `reasoning_format` es EXCLUSIVO de Groq.
        extra["reasoning_format"] = os.getenv("GROQ_RAZONAMIENTO", "hidden")
    elif activo == "groq" and _es_modelo_de_razonamiento(modelo):
        # La familia gpt-oss: mismo objetivo, otro parámetro. `include_reasoning`
        # es booleano y los dos son MUTUAMENTE EXCLUYENTES — mandar los dos, o
        # mandarle `reasoning_format`, es un 400.
        extra["include_reasoning"] = os.getenv("GROQ_RAZONAMIENTO", "hidden") == "raw"
    elif activo == "openrouter" and _es_modelo_de_razonamiento(modelo):
        # OpenRouter unifica el suyo bajo `reasoning`: {"exclude": True} descarta
        # la cadena de pensamiento (el equivalente al "hidden" de Groq).
        # DeepSeek y OpenAI no necesitan parche: deepseek-v4-flash sale en modo
        # NO pensante por defecto (el modo pensante se pide con `thinking`), y
        # cuando piensa devuelve el razonamiento en un campo APARTE del
        # contenido, así que no ensucia las salidas del curso.
        extra["reasoning"] = {"exclude": True}

    # ⚠️ KIMI FIJA LOS PARÁMETROS DE MUESTREO. La doc de Moonshot dice que
    #    `kimi-k3` trabaja siempre con `temperature=1.0` y que hay que OMITIR el
    #    campo en vez de mandar otro valor; `kimi-k2.6`/`k2.5` solo admiten 1.0
    #    (pensando) o 0.6 (sin pensar). Todo el curso llama a
    #    `crear_llm(temperature=0.0)` para que las salidas sean reproducibles, así
    #    que mandárselo tal cual a Kimi es el mismo tipo de 400 que da Groq con
    #    `reasoning_format`: cada proveedor tiene sus parámetros prohibidos.
    #
    #    Cómo se OMITE de verdad: en `ChatOpenAI` el campo es `float | None` y su
    #    `_default_params` filtra con un `exclude_if_none`, así que `None` no viaja
    #    en el JSON — es exactamente "no mandar el kwarg". (Poner `None` en un
    #    cliente que lo serializara igual NO valdría; por eso se comprueba, no se
    #    supone. El test de regresión vive en tests/test_util.py.)
    #
    #    Consecuencia pedagógica, y por eso Kimi NO es el camino recomendado del
    #    curso: con Kimi no puedes fijar `temperature=0`, o sea que pierdes la
    #    reproducibilidad de la que dependen los ejemplos y las evaluaciones.
    #
    #    ⚠️ DOS LÍMITES MÁS, conocidos y NO probados contra la API real (activar
    #    una llave de Moonshot exige recargar saldo). Anotados aquí para que quien
    #    los pise sepa que no es su código:
    #      · si `kimi-k3` devolviera su razonamiento DENTRO del contenido, haría
    #        falta una rama de `extra_body` como la de Groq; hoy no se le manda
    #        ninguna.
    #      · la doc avisa de que `kimi-k2.6` no soporta `tool_choice: "required"`,
    #        que es justo lo que suele enviar el `method="function_calling"` de
    #        aquí abajo → el TEMA 05 (salida estructurada) podría fallar con Kimi.
    temperatura_efectiva = None if activo == "kimi" else temperature

    class _ChatCompatible(ChatOpenAI):
        """ChatOpenAI con `with_structured_output` en modo function_calling.

        ⚠️ POR QUÉ ESTE PARCHE. Por defecto, `with_structured_output()` pide al
        proveedor un `response_format: json_schema`. OpenAI lo soporta; **Groq
        solo lo soporta en algunos modelos**, y no hay ninguna garantía de que
        el modelo que tengas en el .env esté entre ellos: si no lo está,
        devuelve un 400 y el TEMA 05 del curso se cae en seco.

        `method="function_calling"` obtiene el mismo resultado por otro camino:
        le declara al modelo una herramienta con la forma del esquema y le pide
        que la llame. Funciona en todos los modelos con tool calling, que son
        justo los que este curso necesita de todas formas.
        """

        def with_structured_output(self, schema, *, method="function_calling", **kwargs):
            return super().with_structured_output(schema, method=method, **kwargs)

    return _ChatCompatible(
        model=modelo,
        temperature=temperatura_efectiva,
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
