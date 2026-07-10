"""
config.py · Toda la configuración en un solo sitio
===================================================
FINALIDAD:
  Que NINGÚN otro archivo lea variables de entorno ni invente rutas.
  Si mañana cambias de Gemini a otro proveedor, o mueves un archivo,
  tocas este módulo y nada más. (De hecho ya pasó: el proveedor ahora sale
  del .env, y lo único que cambió fue `crear_llm()`.)

LÓGICA:
  - Las RUTAS y los NOMBRES de modelo son constantes (baratas, sin efectos).
  - Todo lo CARO (leer el .env, crear el modelo) vive dentro de funciones.

  ⭐ Regla de oro del módulo: **importar config.py no debe hacer nada**.
     Ni leer archivos, ni pedir la llave, ni abrir conexiones. Si lo hiciera,
     no podríamos importarlo desde un test sin tener una llave.
     Ese era justamente el problema del app.py monolítico original: al
     importarlo, construía el vector store y llamaba a la API.
"""

import os
import sys
from pathlib import Path

# `util.py` vive en curso_ejemplos/, una carpeta más arriba. El proyecto se
# ejecuta desde su propia carpeta (`uv run python proyecto_final/main.py`), así
# que Python no lo encontraría solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ============ RUTAS ============
# Path(__file__).parent = la carpeta de este archivo. Así el proyecto funciona
# lo ejecutes desde donde lo ejecutes (no depende del directorio actual).
CARPETA = Path(__file__).resolve().parent
RUTA_NORMATIVA = CARPETA / "normativa.txt"
RUTA_AUDITORIA = CARPETA / "hallazgos_auditoria.log"

# ============ MODELOS ============
# El proveedor NO se cablea aquí: sale del .env (LLM_PROVIDER). Con `google`
# usa gemini-3.1-flash-lite; con `groq`, qwen/qwen3-32b. El resto del proyecto
# llama a crear_llm() y no sabe cuál hay detrás — que es justo el sentido de
# tener este módulo.
TEMPERATURA = 0                            # 0 = determinista (lo que se quiere en auditoría)

# ============ RAG ============
# Cuántos fragmentos de normativa se le pasan al modelo como contexto.
# Subirlo da más contexto pero también más ruido (y más tokens).
FRAGMENTOS_POR_CONSULTA = 3

# ============ PERSONALIDAD DEL AGENTE ============
INSTRUCCIONES_AGENTE = (
    "Eres 'GobData', asistente de gobierno de datos de una financiera. "
    "Responde en español, claro y preciso. Usa buscar_normativa para dudas "
    "y evaluar_regla_calidad para evaluar reglas. Nunca inventes normativa."
)


# ============ FUNCIONES (lo caro, bajo demanda) ============
def cargar_entorno() -> None:
    """Lee el archivo .env y mete sus valores en las variables de entorno."""
    from dotenv import load_dotenv
    load_dotenv()


def validar_entorno() -> None:
    """Falla TEMPRANO y con un mensaje claro si algo falta.

    Preferimos morir aquí, al arrancar, que a mitad de una conversación con
    un error críptico de la librería.
    """
    cargar_entorno()
    from util import requiere_llm_key
    if (error := requiere_llm_key()):
        raise SystemExit(error)
    if not RUTA_NORMATIVA.exists():
        raise SystemExit(f"❌ No encuentro la normativa: {RUTA_NORMATIVA}")


def crear_llm():
    """El modelo de chat del proveedor que diga el .env (LLM_PROVIDER).

    Se importa aquí dentro para no pagar el import si no se usa: `config.py` se
    importa desde los tests, y esos no construyen ningún modelo.
    """
    from util import crear_llm as _crear_llm
    return _crear_llm(temperature=TEMPERATURA)


def crear_embeddings():
    """El modelo que traduce texto a vectores (para el RAG).

    ⚠️ Los embeddings NO siguen a LLM_PROVIDER: Groq no los ofrece. Con
       EMBEDDINGS_PROVIDER=fastembed se calculan en local (uv sync --extra emb).
    """
    from util import crear_embeddings as _crear_embeddings
    return _crear_embeddings()


def es_error_cuota(exc: BaseException) -> bool:
    """¿Es un 429 de Gemini? (el error más común del plan gratuito)."""
    texto = str(exc)
    return "RESOURCE_EXHAUSTED" in texto or "429" in texto


def mensaje_cuota() -> str:
    from util import mensaje_cuota as _mensaje_cuota
    return _mensaje_cuota()
