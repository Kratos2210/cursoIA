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
# ⭐ POR QUÉ UNA SOLA CLASE SIRVE PARA LOS DOS. Casi todo el mercado (Groq,
#    Ollama, Together, OpenAI) habla el MISMO dialecto: la API de OpenAI. Por
#    eso `ChatOpenAI` + `base_url` los cubre a todos. Gemini no lo habla, y por
#    eso tiene su propia rama. No es que LangChain tenga un adaptador por
#    proveedor: es que el mercado convergió en un protocolo.
#
# Cambiar de proveedor es cambiar el .env, NO el código:
#
#   LLM_PROVIDER=groq     → qwen/qwen3-32b vía Groq. Llave gratis en
#                           https://console.groq.com/keys  (GROQ_API_KEY)
#   LLM_PROVIDER=google   → Gemini, el proveedor por defecto del curso.
#   LLM_PROVIDER=ollama   → un modelo en tu máquina. Sin llave y sin cuota.
PROVEEDOR_POR_DEFECTO = "google"

# El modelo que usa cada proveedor si no dices otro (LLM_MODELO en el .env).
MODELOS_POR_DEFECTO = {
    "google": "gemini-2.0-flash",
    "groq": "qwen/qwen3-32b",
    "ollama": "qwen3:8b",
}

# Dónde vive la API de cada proveedor compatible con OpenAI, y de qué variable
# de entorno sale su llave.
_COMPATIBLES_OPENAI = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "ollama": ("http://localhost:11434/v1", "OLLAMA_API_KEY"),
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
    if nombre_proveedor == "google":
        return "GOOGLE_API_KEY"
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


def crear_llm(temperature: float = 0.0, modelo: str | None = None):
    """El modelo de chat del proveedor que diga el .env.

    Los ejercicios llaman a ESTO en vez de instanciar `ChatGoogleGenerativeAI`
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

    base_url, variable = _COMPATIBLES_OPENAI[activo]
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=modelo,
        temperature=temperature,
        base_url=os.getenv("LLM_BASE_URL", base_url),
        # Ollama no valida la llave, pero el cliente de OpenAI exige que exista.
        api_key=os.getenv(variable, "no-hace-falta"),
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
    """Devuelve un mensaje de error si FALTA GOOGLE_API_KEY; None si está ok.

    Así cada ejemplo hace:  if (err := requiere_api_key()): raise SystemExit(err)
    en una sola línea, en vez de repetir el if not os.getenv(...).

    ⚠️ Es específica de Gemini a propósito: la usan los ejemplos numerados
    (`01_…` a `16_…`), que instancian `ChatGoogleGenerativeAI` directamente.
    Los EJERCICIOS usan `crear_llm()` + `requiere_llm_key()`, que sí entienden
    de proveedores. Si pusiste LLM_PROVIDER=groq, esta función te lo recuerda
    en vez de dejarte pelear con un ImportError de Google.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        if proveedor() != "google":
            return (f"❌ Falta GOOGLE_API_KEY. Tienes LLM_PROVIDER={proveedor()} en el "
                    f".env, pero este EJEMPLO usa Gemini directamente (los ejercicios "
                    f"sí respetan LLM_PROVIDER). Pon la llave de Google, o corre los "
                    f"ejemplos offline: 07, 12, 13b, 14, 15, 16b.")
        return ("❌ Falta GOOGLE_API_KEY. Copia .env.example a .env y pon tu llave.")
    return None
