"""
config.py · Toda la configuración en un solo sitio
===================================================
FINALIDAD:
  Que NINGÚN otro archivo lea variables de entorno ni invente rutas.
  Si mañana cambias de Gemini a otro proveedor, o mueves un archivo,
  tocas este módulo y nada más.

LÓGICA:
  - Las RUTAS y los NOMBRES de modelo son constantes (baratas, sin efectos).
  - Todo lo CARO (leer el .env, crear el modelo) vive dentro de funciones.

  ⭐ Regla de oro del módulo: **importar config.py no debe hacer nada**.
     Ni leer archivos, ni pedir la llave, ni abrir conexiones. Si lo hiciera,
     no podríamos importarlo desde un test sin tener una GOOGLE_API_KEY.
     Ese era justamente el problema del app.py monolítico original: al
     importarlo, construía el vector store y llamaba a la API.
"""

import os
from pathlib import Path

# ============ RUTAS ============
# Path(__file__).parent = la carpeta de este archivo. Así el proyecto funciona
# lo ejecutes desde donde lo ejecutes (no depende del directorio actual).
CARPETA = Path(__file__).resolve().parent
RUTA_NORMATIVA = CARPETA / "normativa.txt"
RUTA_AUDITORIA = CARPETA / "hallazgos_auditoria.log"

# ============ MODELOS ============
MODELO_CHAT = "gemini-2.0-flash"          # el que conversa y decide qué tool usar
MODELO_EMBEDDINGS = "gemini-embedding-001"  # el que convierte texto en vectores
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
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit(
            "❌ Falta GOOGLE_API_KEY. Copia curso_ejemplos/.env.example a .env y pon tu llave."
        )
    if not RUTA_NORMATIVA.exists():
        raise SystemExit(f"❌ No encuentro la normativa: {RUTA_NORMATIVA}")


def crear_llm():
    """El modelo de chat. Se importa aquí dentro para no pagar el import si no se usa."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=MODELO_CHAT, temperature=TEMPERATURA)


def crear_embeddings():
    """El modelo que traduce texto a vectores (para el RAG)."""
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)


def es_error_cuota(exc: BaseException) -> bool:
    """¿Es un 429 de Gemini? (el error más común del plan gratuito)."""
    texto = str(exc)
    return "RESOURCE_EXHAUSTED" in texto or "429" in texto


def mensaje_cuota() -> str:
    return ("⏳ Cuota de Gemini agotada (429). "
            "Espera unos minutos o usa 'gemini-2.5-flash'.")
