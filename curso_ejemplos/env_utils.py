"""
env_utils.py · El chequeo de entorno del curso
===============================================
FINALIDAD:
  Responder de una sola vez a la pregunta del día 1: **"¿está todo listo?"**.
  Antes de este archivo, el alumno solo lo descubría cuando `01_primer_modelo.py`
  reventaba — y un `ModuleNotFoundError` y una llave mal pegada se parecen
  demasiado cuando es tu primera tarde programando.

USO:
    uv run python env_utils.py           # chequeo completo SIN gastar cuota
    uv run python env_utils.py --ping    # además, UNA llamada real al proveedor

LÓGICA:
  Siete comprobaciones, de la más básica a la más específica. Ninguna llama a la
  API salvo la última, y esa solo con `--ping`:

    1. Versión de Python (el curso pide >= 3.11).
    2. Estás parado en curso_ejemplos/ (la regla de oro de uv).
    3. Las librerías base importan, y con qué versión.
    4. Existe el archivo .env (no el .env.example: el .env de verdad).
    5. LLM_PROVIDER es un proveedor que el curso conoce.
    6. La llave de ESE proveedor está puesta y no es el texto de relleno.
    7. Los embeddings tienen con qué calcularse (solo avisa; el RAG llega en m11).

  Cada línea sale como:  ✔ (bien) · ▲ (aviso, no te frena) · ✘ (roto, con arreglo)
  y el script termina en código 1 si hay algún ✘, para que sirva también en CI.

⚠️ NO importa nada del curso al arrancar. Los imports pesados (langchain, util)
   van DENTRO de cada comprobación, porque el escenario que este archivo tiene
   que sobrevivir es justamente aquel en que esos imports fallan.
"""

import os
import sys
from pathlib import Path

# ==================================================================
# LA CARPETA DEL CURSO
# ==================================================================
# La de este archivo, no la del terminal. Así el script dice la verdad aunque
# lo llames desde fuera: `uv run python curso_ejemplos/env_utils.py`.
AQUI = Path(__file__).resolve().parent

# Lo que trae la instalación BASE (`uv sync`). Los extras (fastembed, fastapi,
# qdrant…) NO se comprueban aquí: son opcionales y llegan en su módulo.
LIBRERIAS_BASE = [
    ("langchain", "el paquete paraguas de LangChain v1 (create_agent, middleware)"),
    ("langchain_core", "mensajes, prompts, runnables"),
    ("langgraph", "grafos de estado y memoria de agentes"),
    ("langchain_google_genai", "el cliente de Gemini"),
    ("langchain_openai", "el cliente de Groq / Ollama / OpenAI (mismo dialecto)"),
    ("dotenv", "leer el .env"),
    ("pydantic", "los moldes de la salida estructurada"),
]

# Cómo huele una llave sin rellenar. El .env.example trae `tu_llave_secreta_aqui`
# y variantes por proveedor; pegar el archivo tal cual y no tocarlo es, con
# diferencia, el error número uno del primer día.
RELLENOS = ("tu_llave", "tu_api_key", "tu_llave_secreta", "aqui", "aquí", "xxxx")

MINIMO_PYTHON = (3, 11)


# ==================================================================
# PRESENTACIÓN
# ==================================================================
# Un contador global de fallos en vez de excepciones: queremos que el alumno vea
# TODAS las cosas que le faltan de una pasada, no la primera y a repetir.
_fallos: list[str] = []


def ok(texto: str) -> None:
    print(f"  ✔ {texto}")


def aviso(texto: str, detalle: str = "") -> None:
    print(f"  ▲ {texto}")
    if detalle:
        print(f"      {detalle}")


def error(texto: str, arreglo: str = "") -> None:
    """Un ✘ SIEMPRE va con su arreglo. Un error sin salida no enseña nada."""
    _fallos.append(texto)
    print(f"  ✘ {texto}")
    if arreglo:
        print(f"      → {arreglo}")


def titulo(n: int, texto: str) -> None:
    print(f"\n{n}. {texto}")


# ==================================================================
# 1 · PYTHON
# ==================================================================
def comprobar_python() -> None:
    titulo(1, "Python")
    v = sys.version_info
    actual = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= MINIMO_PYTHON:
        ok(f"Python {actual}")
    else:
        error(
            f"Python {actual}: el curso necesita {MINIMO_PYTHON[0]}.{MINIMO_PYTHON[1]} o superior",
            "uv lo resuelve solo:  uv python install 3.12  y luego  uv sync",
        )


# ==================================================================
# 2 · DÓNDE ESTÁS PARADO
# ==================================================================
# La regla de oro de uv: elige el entorno buscando el pyproject.toml más cercano
# hacia arriba. Por eso el MISMO comando funciona en una carpeta y falla en la de
# al lado, y por eso este chequeo va tan arriba.
def comprobar_carpeta() -> None:
    titulo(2, "La carpeta de trabajo")

    if (AQUI / "pyproject.toml").exists() and (AQUI / "util.py").exists():
        ok(f"estás en la carpeta del curso: {AQUI}")
    else:
        error(
            f"no encuentro pyproject.toml ni util.py junto a este archivo ({AQUI})",
            "este script vive dentro de curso_ejemplos/. Haz:  cd curso_ejemplos",
        )
        return

    # ¿El intérprete que corre esto es el .venv de ESTA carpeta?
    prefijo = Path(sys.prefix).resolve()
    if prefijo == (AQUI / ".venv").resolve():
        ok("usando el entorno virtual de esta carpeta (.venv)")
    else:
        aviso(
            f"el entorno activo no es {AQUI / '.venv'} sino {prefijo}",
            "no siempre es un problema, pero si algún import falla, empieza por aquí: "
            "cd curso_ejemplos && uv sync",
        )


# ==================================================================
# 3 · LAS LIBRERÍAS
# ==================================================================
def comprobar_librerias() -> None:
    titulo(3, "Las librerías (instalación base)")
    from importlib.metadata import PackageNotFoundError, version

    # El nombre del módulo que se importa no siempre es el del paquete que se
    # instala: `import dotenv` viene de `python-dotenv`.
    paquete_de = {"dotenv": "python-dotenv"}

    faltan = []
    for modulo, para_que in LIBRERIAS_BASE:
        try:
            __import__(modulo)
        except ImportError:
            faltan.append(modulo)
            error(f"falta {modulo} ({para_que})")
            continue
        try:
            v = version(paquete_de.get(modulo, modulo.replace("_", "-")))
        except PackageNotFoundError:      # instalado, pero sin metadatos
            v = "?"
        ok(f"{modulo} {v}")

    if faltan:
        print(
            "      → no instalaste las dependencias, o estás en otra carpeta.\n"
            "        Arreglo:  cd curso_ejemplos && uv sync"
        )


# ==================================================================
# 4 · EL ARCHIVO .env
# ==================================================================
def comprobar_env() -> bool:
    """Devuelve True si se pudo cargar el .env (lo necesitan los pasos 5-7)."""
    titulo(4, "El archivo .env")

    ruta = AQUI / ".env"
    if not ruta.exists():
        error(
            "no existe curso_ejemplos/.env",
            "cp .env.example .env   (y luego pega tu llave dentro)",
        )
        return False
    ok(".env encontrado")

    try:
        from dotenv import load_dotenv
    except ImportError:
        error("no puedo leerlo: falta python-dotenv", "cd curso_ejemplos && uv sync")
        return False

    # override=True porque una variable ya exportada en la terminal ganaría al
    # .env, y entonces este chequeo estaría validando algo distinto de lo que
    # van a ver los ejemplos.
    load_dotenv(ruta, override=True)
    ok(".env cargado")
    return True


# ==================================================================
# 5 y 6 · EL PROVEEDOR Y SU LLAVE
# ==================================================================
def _es_relleno(valor: str) -> bool:
    v = valor.strip().strip("'\"").lower()
    return any(marca in v for marca in RELLENOS)


def comprobar_proveedor() -> None:
    titulo(5, "El proveedor del modelo")
    try:
        import util
    except ImportError:
        error("no puedo importar util.py", "corre el script desde curso_ejemplos/")
        return

    activo = util.proveedor()
    if activo not in util.MODELOS_POR_DEFECTO:
        error(
            f"LLM_PROVIDER='{activo}' no existe",
            f"opciones válidas: {', '.join(sorted(util.MODELOS_POR_DEFECTO))}",
        )
        # Sin proveedor válido no hay llave que comprobar, pero el paso 6 se
        # imprime igual: un número que se salta parece un bug del script.
        titulo(6, "La llave")
        aviso("no puedo comprobarla hasta que LLM_PROVIDER sea válido")
        return
    ok(f"LLM_PROVIDER={activo}")

    # El modelo es informativo, nunca un error: un ID caducado no se detecta
    # leyendo el .env, solo llamando (--ping).
    modelo = util.modelo_por_defecto(activo)
    origen = "de tu .env" if os.getenv("LLM_MODELO") else "por defecto del curso"
    ok(f"modelo: {modelo}  ({origen})")

    titulo(6, "La llave")
    if activo == "ollama":
        ok("ollama corre en tu máquina: no necesita llave")
        aviso("necesita `ollama serve` corriendo y el modelo descargado (ollama list)")
        return

    variable = util.variable_de_llave(activo)
    valor = os.getenv(variable, "")
    if not valor.strip():
        error(
            f"falta {variable} (el proveedor activo es {activo})",
            f"abre curso_ejemplos/.env y pon la línea:  {variable}=tu_llave_real",
        )
    elif _es_relleno(valor):
        error(
            f"{variable} sigue con el texto de relleno del .env.example",
            "copiaste el archivo pero no pegaste tu llave. "
            "Gemini: https://aistudio.google.com · Groq: https://console.groq.com/keys",
        )
    else:
        # Nunca imprimimos la llave. Los primeros caracteres bastan para que el
        # alumno reconozca cuál pegó (AIza… de Google, gsk_… de Groq).
        ok(f"{variable} presente ({valor.strip()[:6]}…, {len(valor.strip())} caracteres)")


# ==================================================================
# 7 · LOS EMBEDDINGS (solo importan a partir del m11)
# ==================================================================
# Nunca es un ✘: quien está en el m00 no ha llegado al RAG y no debe salir de
# aquí creyendo que tiene el entorno roto.
def comprobar_embeddings() -> None:
    titulo(7, "Los embeddings (los usa el RAG, desde el m11)")
    try:
        import util
    except ImportError:
        return

    proveedor_emb = util.proveedor_embeddings()
    if proveedor_emb == "fastembed":
        try:
            __import__("fastembed")
            ok("fastembed instalado: embeddings en tu máquina, sin cuota")
        except ImportError:
            aviso(
                "EMBEDDINGS_PROVIDER=fastembed pero fastembed no está instalado",
                "uv sync --extra emb    (descarga ~220 MB la primera vez)",
            )
    elif (clave := os.getenv("GOOGLE_API_KEY", "")).strip() and not _es_relleno(clave):
        ok("embeddings de Gemini (usan GOOGLE_API_KEY)")
    else:
        aviso(
            "los embeddings van a Gemini y no hay una GOOGLE_API_KEY usable",
            "sin prisa: solo te frena en el m11. Entonces: pon GOOGLE_API_KEY, o "
            "uv sync --extra emb  +  EMBEDDINGS_PROVIDER=fastembed",
        )


# ==================================================================
# 8 · LA LLAMADA DE VERDAD (solo con --ping)
# ==================================================================
# Todo lo anterior comprueba que la llave ESTÁ. Solo esto comprueba que SIRVE —
# y es también lo único que distingue un ID de modelo vigente de uno apagado.
# Va detrás de un flag porque gasta una llamada de cuota.
def comprobar_ping() -> None:
    titulo(8, "Llamada real al proveedor (--ping)")
    try:
        import util
    except ImportError:
        error("no puedo importar util.py", "corre el script desde curso_ejemplos/")
        return

    try:
        llm = util.crear_llm(temperature=0.0)
        respuesta = llm.invoke("Responde solo con la palabra: listo")
    except Exception as exc:                       # noqa: BLE001 — aquí queremos TODO
        if util.es_error_cuota(exc):
            aviso(
                "el proveedor respondió 429 (cuota agotada)",
                "tu llave FUNCIONA — es el cupo. Pásate a Groq en el .env, o corre "
                "los ejemplos offline: 07, 12, 13b, 14, 15, 16 y 16b.",
            )
            return
        texto = str(exc).lower()
        if "not found" in texto or "decommissioned" in texto or "deprecated" in texto:
            error(
                f"el modelo '{util.modelo_por_defecto()}' ya no existe en el proveedor",
                "no es tu código: lo apagaron. Copia un ID vigente de la página "
                "oficial del proveedor y ponlo en LLM_MODELO de tu .env.",
            )
            return
        error(f"la llamada falló: {type(exc).__name__}: {exc}",
              "si habla de autenticación, la llave está mal pegada (sin comillas "
              "ni espacios alrededor del '=').")
        return

    # `.text` (propiedad, no método) es la forma de langchain-core 1.x de sacar el
    # texto plano aunque la respuesta venga en content_blocks.
    ok(f"el modelo respondió: {respuesta.text.strip()[:60]!r}")
    ok("tu entorno habla con el LLM. Ya puedes correr 01_primer_modelo.py")


# ==================================================================
# EL PROGRAMA
# ==================================================================
def main() -> int:
    ping = "--ping" in sys.argv

    print("=" * 62)
    print("  Chequeo de entorno del curso")
    print("=" * 62)

    comprobar_python()
    comprobar_carpeta()
    comprobar_librerias()
    if comprobar_env():
        comprobar_proveedor()
        comprobar_embeddings()
        if ping:
            comprobar_ping()

    print("\n" + "=" * 62)
    if _fallos:
        print(f"  ✘ {len(_fallos)} cosa(s) por arreglar:")
        for f in _fallos:
            print(f"      · {f}")
        print("\n  Arregla la primera y vuelve a correr este script.")
        print("  Todos los casos, con su causa, en SETUP.md")
        print("=" * 62)
        return 1

    print("  ✔ Entorno listo.")
    if not ping:
        print("\n  Esto comprueba que la llave ESTÁ, no que sirva. Para confirmarlo")
        print("  con una llamada real (gasta 1 de cuota):")
        print("      uv run python env_utils.py --ping")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
