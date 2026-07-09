"""
TEMA 16 · Evaluación: medir la calidad de tu RAG con un dataset
==========================================================
FINALIDAD:
  "Funciona" no es una métrica. Aquí construyes la pieza central de la
  observabilidad: un DATASET de preguntas con respuesta esperada, y una
  evaluación repetible que te dice QUÉ TAN BIEN responde tu sistema.
  Si mañana cambias el prompt o el modelo y el puntaje baja: hay REGRESIÓN.

LÓGICA (paso a paso):
  1) La "app a evaluar": un mini-RAG sobre datos_rag.txt (retrieval simple).
  2) El dataset: preguntas + palabras clave que la respuesta DEBE contener
     (mismo espíritu que proyectorag/preguntas.txt, pero con esperados).
  3) Evaluador 1 (offline, gratis): ¿la respuesta contiene lo esperado?
  4) Evaluador 2 (opcional, si hay GOOGLE_API_KEY): un LLM actúa de JUEZ
     y califica cada respuesta — es la idea de "LLM-as-judge" que LangSmith
     usa en grande (openevals + CORRECTNESS_PROMPT).
  5) Reporte final con el puntaje total: tu línea base contra regresiones.

Requisitos: pip install -r curso_ejemplos/requirements.txt
Ejecuta:    uv run python curso_ejemplos/16_evaluacion.py
            (sin llave corre igual: solo omite el juez LLM)
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                        # leer GOOGLE_API_KEY y construir rutas
import re                        # tokenizar para el retrieval simple
from collections import Counter  # contar palabras (retrieval por solapamiento)
from dotenv import load_dotenv   # cargar la llave desde el archivo .env


# ============ 1) LA "APP" QUE VAMOS A EVALUAR ============
# Un mini-RAG extractivo: recupera el chunk con más palabras en común con la
# pregunta y lo devuelve como respuesta. (En tu app real, aquí iría tu cadena
# RAG completa: retriever + prompt + LLM. La evaluación no cambia.)
def cargar_chunks() -> list[str]:
    ruta = os.path.join(os.path.dirname(__file__), "datos_rag.txt")
    with open(ruta, "r", encoding="utf-8") as f:
        return [p.strip() for p in f.read().split("\n\n") if p.strip()]


def tokenizar(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-záéíóúüñ0-9]+", texto.lower()) if len(p) > 3}


def responder(pregunta: str, chunks: list[str]) -> str:
    """La función bajo prueba: recibe una pregunta, devuelve una respuesta."""
    palabras = tokenizar(pregunta)
    mejor = max(chunks, key=lambda c: len(palabras & tokenizar(c)))
    if not palabras & tokenizar(mejor):
        return "No tengo esa información en el contexto."   # ⭐ anti-alucinación
    return mejor


# ============ 2) EL DATASET: pregunta + lo que DEBE contener ============
# En LangSmith esto sería client.create_dataset(...) + create_examples(...).
# La estructura es la misma: entradas (pregunta) y salidas esperadas.
DATASET = [
    {"pregunta": "¿Cuál es el horario de atención?",
     "esperado": ["lunes", "viernes", "9:00", "18:00"]},
    {"pregunta": "¿Hasta cuándo puedo pedir un reembolso completo?",
     "esperado": ["7 días", "reembolso"]},
    {"pregunta": "¿Qué formas de pago aceptan?",
     "esperado": ["transferencia", "yape", "plin"]},
    {"pregunta": "¿Qué recibo al finalizar un proyecto?",
     "esperado": ["código fuente", "manual", "capacitación", "soporte"]},
    # Pregunta TRAMPA: no está en el documento. La respuesta correcta es admitirlo.
    {"pregunta": "¿Cuál es la capital de Australia?",
     "esperado": ["no tengo esa información"]},
]


# ============ 3) EVALUADOR OFFLINE: ¿contiene lo esperado? ============
def evaluar_contenido(respuesta: str, esperado: list[str]) -> float:
    """Devuelve la fracción de términos esperados presentes (0.0 a 1.0)."""
    r = respuesta.lower()
    aciertos = sum(1 for termino in esperado if termino.lower() in r)
    return aciertos / len(esperado)


# ============ 4) EVALUADOR OPCIONAL: LLM COMO JUEZ ============
def crear_juez():
    """Devuelve una función juez si hay llave; si no, None (y no pasa nada)."""
    if not os.getenv("GOOGLE_API_KEY"):
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI
    from pydantic import BaseModel, Field

    class Veredicto(BaseModel):
        """Calificación del juez sobre una respuesta."""
        correcta: bool = Field(description="¿La respuesta contesta bien la pregunta?")
        motivo: str = Field(description="Justificación en una frase")

    # temperature=0: un juez debe ser consistente, no creativo
    juez = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    juez_estructurado = juez.with_structured_output(Veredicto)

    def juzgar(pregunta: str, respuesta: str) -> str:
        veredicto = juez_estructurado.invoke(
            f"Pregunta del usuario: {pregunta}\n"
            f"Respuesta del sistema: {respuesta}\n"
            "¿La respuesta contesta correctamente la pregunta? "
            "Si la información no existe, admitirlo también cuenta como correcto."
        )
        return f"{'✅' if veredicto.correcta else '❌'} juez: {veredicto.motivo}"

    return juzgar


def main():
    load_dotenv()
    chunks = cargar_chunks()
    juzgar = crear_juez()
    if juzgar is None:
        print("ℹ️  Sin GOOGLE_API_KEY: corro solo la evaluación offline (suficiente para aprender).")

    # ---- 5) Correr la app contra TODO el dataset y puntuar ----
    print(f"\n=== Evaluando {len(DATASET)} preguntas ===")
    puntaje_total = 0.0
    for caso in DATASET:
        respuesta = responder(caso["pregunta"], chunks)
        puntaje = evaluar_contenido(respuesta, caso["esperado"])
        puntaje_total += puntaje

        print(f"\n· {caso['pregunta']}")
        print(f"  respuesta: {respuesta[:80]}…" if len(respuesta) > 80
              else f"  respuesta: {respuesta}")
        print(f"  contenido esperado: {puntaje:.0%}")
        if juzgar:
            try:
                print(f"  {juzgar(caso['pregunta'], respuesta)}")
            except Exception as error:
                if "429" in str(error) or "RESOURCE_EXHAUSTED" in str(error):
                    print("  ⚠️ Cuota agotada (429): el juez descansa, la métrica offline sigue.")
                    juzgar = None      # no insistir en las siguientes preguntas
                else:
                    raise

    # ---- El número que vigilas en cada cambio ----
    promedio = puntaje_total / len(DATASET)
    print(f"\n{'=' * 46}")
    print(f"PUNTAJE GLOBAL: {promedio:.0%}  ({puntaje_total:.1f} de {len(DATASET)} puntos)")
    print("Guarda este número. Si tras cambiar el prompt/modelo baja: REGRESIÓN.")
    print("En producción: este mismo flujo es evaluate(...) de LangSmith con")
    print("un dataset versionado y un juez openevals (CORRECTNESS_PROMPT).")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ No encuentro datos_rag.txt (debe estar junto a este script).")
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
