"""
TEMA 16b · Observabilidad real: tracing, tokens y coste
==========================================================
FINALIDAD:
  El TEMA 16 mide la CALIDAD (¿responde bien?). Este mide el COSTE y la
  TRAZA (¿cuánto gasté? ¿qué pasó por dentro? ¿dónde se rompió?).

  Son las dos preguntas que te hará tu jefe el día que esto esté en producción:
    1. "¿Por qué esta respuesta salió mal?"  -> la traza (LangSmith).
    2. "¿Cuánto nos está costando?"          -> los tokens (usage_metadata).

LÓGICA (paso a paso) — degradación en cascada, corre siempre:
  1) Detectamos qué llaves hay disponibles:
       - LANGSMITH_API_KEY -> activamos el tracing real a LangSmith.
       - la llave del proveedor (GOOGLE_API_KEY o GROQ_API_KEY) -> modelo real.
       - ninguna           -> modo OFFLINE: simulamos la respuesta del modelo.
     El código de medición es EL MISMO en los tres casos. Eso es lo que se enseña.
  2) @traceable envuelve nuestras funciones: cada llamada se convierte en un
     "span" en el árbol de la traza (retrieval -> generación -> respuesta).
  3) De cada respuesta sacamos usage_metadata: input_tokens / output_tokens.
  4) Con una tabla de precios estimamos el coste en dólares.
  5) Un pequeño informe: tokens, coste y a dónde ir a mirar la traza.

⚠️ SOBRE LOS PRECIOS: la tabla PRECIOS de abajo es una FOTO, no una verdad
   eterna. Google los cambia. Antes de presupuestar nada, contrástalos con
   https://ai.google.dev/pricing — y trata el número como un orden de magnitud.

Requisitos: uv sync   (langsmith ya está en las dependencias)
Ejecuta:    uv run python curso_ejemplos/16b_observabilidad_langsmith.py
            (sin ninguna llave corre igual, en modo offline)

Para ver trazas de verdad:
    export LANGSMITH_API_KEY="ls__..."     # de https://smith.langchain.com
    export LANGSMITH_PROJECT="curso-langchain"
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                       # leer las llaves y activar el tracing por env vars
import re                       # tokenizar el texto para el retrieval
from dotenv import load_dotenv  # cargar el .env

from util import (crear_llm as _crear_llm_del_curso, es_error_cuota, mensaje_cuota,
                  modelo_por_defecto, requiere_llm_key, trocear_parrafos)


# ============ 1) TABLA DE PRECIOS (dólares por 1 millón de tokens) ============
# Los tokens de ENTRADA (tu prompt + el contexto del RAG) son baratos.
# Los de SALIDA (lo que escribe el modelo) cuestan varias veces más.
# Por eso un RAG con contexto gigante NO es lo caro: lo caro es una respuesta larga.
PRECIOS = {
    #  modelo                     entrada    salida     (USD por 1M de tokens)
    "gemini-2.0-flash":        {"entrada": 0.10, "salida": 0.40},
    "gemini-2.5-flash":        {"entrada": 0.30, "salida": 2.50},
    "qwen/qwen3-32b":          {"entrada": 0.29, "salida": 0.59},
    "llama-3.3-70b-versatile": {"entrada": 0.59, "salida": 0.79},
    "qwen3:8b":                {"entrada": 0.0,  "salida": 0.0},   # local: no cuesta dinero
}

# ⚠️ El modelo activo NO puede ser una constante de módulo. Sale del .env, y el
#    .env se carga en main() con load_dotenv() — que corre DESPUÉS de importar.
#    Una constante calculada aquí arriba diría "gemini-2.0-flash" mientras el
#    programa habla con Groq, y costearía con la tabla equivocada. Es una
#    función, y se pregunta cuando ya hay respuesta.
def modelo_activo() -> str:
    """El modelo del proveedor que diga el .env (LLM_PROVIDER)."""
    return modelo_por_defecto()


# ============ 2) FUNCIONES PURAS: contar y costear ============
# Están sueltas y sin efectos: se testean sin llave y sin red.
# (ver tests/test_offline.py -> TestTema16bObservabilidad)
def extraer_tokens(mensaje) -> dict[str, int]:
    """Saca el consumo de tokens de una respuesta del modelo.

    LangChain normaliza el consumo de TODOS los proveedores en
    'usage_metadata', así que este código funciona igual con Gemini, OpenAI
    o Anthropic. El campo crudo de cada proveedor vive en 'response_metadata',
    pero ahí cada uno le pone un nombre distinto: no te ates a él.

    Devuelve ceros si el proveedor no informó el consumo (pasa en streaming).
    """
    uso = getattr(mensaje, "usage_metadata", None) or {}
    return {
        "entrada": uso.get("input_tokens", 0),
        "salida": uso.get("output_tokens", 0),
        "total": uso.get("total_tokens", 0),
    }


def estimar_costo(tokens: dict[str, int], modelo: str | None = None) -> float:
    """Coste en dólares de una llamada, según la tabla PRECIOS.

    Los precios son 'por millón de tokens', de ahí el 1_000_000.
    Si el modelo no está en la tabla, devolvemos 0.0 en vez de reventar:
    un informe de costes no debe tumbar la aplicación. (Ojo: ese 0.0 significa
    "no sé cuánto costó", no "fue gratis".)
    """
    precio = PRECIOS.get(modelo or modelo_activo())
    if precio is None:
        return 0.0
    return (tokens["entrada"] * precio["entrada"] +
            tokens["salida"] * precio["salida"]) / 1_000_000


def formatear_costo(dolares: float) -> str:
    """Un coste de $0.000018 no se lee de un vistazo. Lo mostramos en su escala."""
    if dolares == 0:
        return "$0 (sin datos de consumo)"
    if dolares < 0.01:
        return f"${dolares:.6f}"
    return f"${dolares:.4f}"


# ============ 3) EL TRACING: @traceable ============
def activar_tracing() -> bool:
    """Enciende el envío de trazas a LangSmith si hay llave. Devuelve si se activó.

    LangSmith se configura por variables de entorno, no por código: cualquier
    llamada a un modelo de LangChain, en cualquier parte del programa, queda
    registrada automáticamente. No hay que instrumentar nada más.
    """
    if not os.getenv("LANGSMITH_API_KEY"):
        return False
    os.environ["LANGSMITH_TRACING"] = "true"                       # el interruptor
    os.environ.setdefault("LANGSMITH_PROJECT", "curso-langchain")  # dónde agrupar
    return True


def traceable_o_nada(func):
    """Decorador que usa @traceable si langsmith está instalado, y si no, no hace nada.

    Así el ejemplo nunca se rompe por una dependencia ausente. Es el patrón
    'degradación graceful': la observabilidad es un extra, no un requisito.
    """
    try:
        from langsmith import traceable
        return traceable(func)
    except ImportError:
        return func


# ============ 4) LA APP QUE OBSERVAMOS: un mini-RAG ============
def tokenizar(texto: str) -> set[str]:
    """Palabras útiles de un texto, en minúsculas y SIN puntuación.

    El regex es imprescindible: partir por espacios dejaría 'atención?' y
    'atención:' como palabras distintas, y el retrieval no encontraría nada.
    Descartamos las de 3 letras o menos ('de', 'la', 'es'): no discriminan.
    """
    return {p for p in re.findall(r"[a-záéíóúüñ0-9\-]+", texto.lower()) if len(p) > 3}


@traceable_o_nada
def recuperar(pregunta: str, chunks: list[str], k: int = 2) -> list[str]:
    """Paso 1 del RAG: los k fragmentos con más palabras en común.

    En la traza de LangSmith esto aparece como un span propio, con su entrada,
    su salida y su duración. Ahí es donde descubres que tu retrieval es el
    lento, o que devolvió el chunk equivocado.
    """
    palabras = tokenizar(pregunta)
    puntuados = sorted(chunks, key=lambda c: len(palabras & tokenizar(c)), reverse=True)
    return puntuados[:k]


class RespuestaSimulada:
    """Una respuesta falsa del modelo, para el modo offline.

    Imita lo justo de un AIMessage: su texto y su usage_metadata. Así el
    resto del programa (contar tokens, costear) no sabe que es falsa.
    """
    def __init__(self, content: str, entrada: int, salida: int):
        self.content = content
        self.usage_metadata = {
            "input_tokens": entrada,
            "output_tokens": salida,
            "total_tokens": entrada + salida,
        }


@traceable_o_nada
def generar(pregunta: str, contexto: str, llm=None):
    """Paso 2 del RAG: el modelo responde con el contexto recuperado.

    Si no hay modelo (modo offline), devolvemos una RespuestaSimulada con un
    consumo de tokens verosímil (≈4 caracteres por token).
    """
    prompt = (f"Responde SOLO con este contexto. Si no está, dilo.\n"
              f"Contexto:\n{contexto}\n\nPregunta: {pregunta}")
    if llm is None:
        # Modo offline: "respondemos" con el fragmento más relevante (el primero
        # que trajo el retriever). Es un RAG extractivo, como el del TEMA 16.
        primer_fragmento = contexto.split("\n\n")[0]
        texto = primer_fragmento.replace("\n", " ").strip()
        # ≈4 caracteres por token: la regla de oro para estimar sin tokenizador.
        return RespuestaSimulada(texto, entrada=len(prompt) // 4, salida=len(texto) // 4)
    return llm.invoke(prompt)


def crear_llm():
    """El modelo real, o None si no hay llave (y entonces vamos a offline).

    La llave que hace falta depende del proveedor activo: GOOGLE_API_KEY con
    Gemini, GROQ_API_KEY con Groq, ninguna con Ollama. Por eso preguntamos a
    `requiere_llm_key()` en vez de mirar una variable concreta.
    """
    if requiere_llm_key():
        return None
    return _crear_llm_del_curso(temperature=0)


# ============ 5) EL INFORME ============
def main():
    load_dotenv()

    # ---- ¿Qué modo nos toca hoy? ----
    tracing = activar_tracing()
    llm = crear_llm()
    MODELO = modelo_activo()      # ya con el .env cargado

    print("=== Configuración detectada ===")
    print(f"  tracing a LangSmith : {'✅ activo' if tracing else '➖ no (falta LANGSMITH_API_KEY)'}")
    print(f"  modelo              : {'✅ ' + MODELO if llm else '➖ offline (falta la llave del proveedor)'}")
    if not llm:
        print("\nℹ️  Modo OFFLINE: simulamos la respuesta del modelo. Los tokens son")
        print("   estimados, pero el CÓDIGO que los cuenta y los costea es el real.")
    elif MODELO not in PRECIOS:
        print(f"\n⚠️  '{MODELO}' no está en la tabla PRECIOS: el coste saldrá $0.")
        print("   Un 0 aquí significa 'no sé', no 'fue gratis'. Añade su fila.")

    ruta = os.path.join(os.path.dirname(__file__), "datos_rag.txt")
    with open(ruta, encoding="utf-8") as f:
        chunks = trocear_parrafos(f.read())

    preguntas = [
        "¿Cuál es el horario de atención?",
        "¿Quién controla las llaves de API?",
        "¿Qué formas de pago aceptan?",
    ]

    total_tokens = {"entrada": 0, "salida": 0, "total": 0}
    total_costo = 0.0

    print(f"\n=== Ejecutando {len(preguntas)} consultas ===")
    for pregunta in preguntas:
        fragmentos = recuperar(pregunta, chunks)
        try:
            respuesta = generar(pregunta, "\n\n".join(fragmentos), llm)
        except Exception as error:
            if es_error_cuota(error):
                print(f"\n{mensaje_cuota()}")
                print("   Sigo en modo offline para terminar el informe.")
                llm = None
                respuesta = generar(pregunta, "\n\n".join(fragmentos), None)
            else:
                raise

        tokens = extraer_tokens(respuesta)
        costo = estimar_costo(tokens)
        for clave in total_tokens:
            total_tokens[clave] += tokens[clave]
        total_costo += costo

        print(f"\n🙋 {pregunta}")
        print(f"🤖 {respuesta.content.strip()[:100]}…")
        print(f"   tokens: {tokens['entrada']} entrada + {tokens['salida']} salida"
              f"   ·   coste: {formatear_costo(costo)}")

    # ---- El resumen que le enseñas a tu jefe ----
    print(f"\n{'=' * 60}")
    print(f"TOTAL · {total_tokens['entrada']} tokens de entrada, "
          f"{total_tokens['salida']} de salida")
    print(f"COSTE · {formatear_costo(total_costo)} por {len(preguntas)} consultas")
    if total_costo:
        por_consulta = total_costo / len(preguntas)
        # El número que de verdad se usa para presupuestar: coste a escala.
        print(f"        ≈ {formatear_costo(por_consulta)} por consulta")
        print(f"        ≈ ${por_consulta * 1000:.2f} cada 1000 consultas")
    print("=" * 60)

    if tracing:
        proyecto = os.environ["LANGSMITH_PROJECT"]
        print(f"\n🔍 Traza enviada a LangSmith, proyecto '{proyecto}'.")
        print("   Ábrela en https://smith.langchain.com y despliega el árbol:")
        print("   verás 'recuperar' y 'generar' como pasos separados, con su duración.")
    else:
        print("\n💡 Para ver la traza de verdad, consigue una llave gratis en")
        print("   https://smith.langchain.com y exporta LANGSMITH_API_KEY. El código")
        print("   NO cambia: LangSmith se activa solo por variables de entorno.")

    print("\n💡 Lo que observas en producción: tokens (coste), latencia por paso,")
    print("   tasa de error, y el prompt EXACTO que se envió cuando algo salió mal.")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ No encuentro datos_rag.txt (debe estar junto a este script).")
    except Exception as error:
        if es_error_cuota(error):
            print(mensaje_cuota())
        else:
            print(f"❌ Error inesperado: {error}")
