"""
SOLUCIÓN · Ejercicio 16 — Casos trampa: cuando la métrica te miente
==========================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Ampliar el dataset del TEMA 16 con tres casos TRAMPA (preguntas sin respuesta
  en el corpus) y añadir una segunda métrica —la tasa de ABSTENCIÓN— que la
  métrica de contenido no puede darte. Demuestra que "el puntaje subió" no
  significa "el sistema mejoró".

LÓGICA:
  - La métrica offline (contenido + abstención) corre SIN llave: es el criterio
    de aceptación del ejercicio.
  - El juez LLM es opcional, igual que en 16_evaluacion.py: si hay llave del
    proveedor activo, califica; si no, se omite y no pasa nada.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_16_evaluacion.py
          (sin llave corre igual: solo omite el juez LLM)
"""

import os
import re
import sys
from collections import Counter
from pathlib import Path

# La carpeta del curso (donde vive datos_rag.txt y util.py) está dos niveles
# arriba de esta solución. La añadimos al path para poder importar util cuando
# —y solo si— haga falta el juez LLM.
CARPETA_CURSO = Path(__file__).resolve().parents[2]


# ============ 1) LA "APP" QUE EVALUAMOS: un mini-RAG extractivo ============
def cargar_chunks() -> list[str]:
    ruta = CARPETA_CURSO / "datos_rag.txt"
    return [p.strip() for p in ruta.read_text(encoding="utf-8").split("\n\n") if p.strip()]


def tokenizar(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-záéíóúüñ0-9]+", texto.lower()) if len(p) > 3}


def responder(pregunta: str, chunks: list[str]) -> str:
    """La función bajo prueba: devuelve el chunk más solapado, o se abstiene.

    ⭐ La abstención vive aquí: si el mejor chunk NO comparte ni un token con la
       pregunta, admitimos no saber en vez de soltar el chunk menos malo.
    """
    palabras = tokenizar(pregunta)
    mejor = max(chunks, key=lambda c: len(palabras & tokenizar(c)))
    if not palabras & tokenizar(mejor):
        return "No tengo esa información en el contexto."
    return mejor


# ============ 2) EL DATASET: ahora con TRES trampas nuevas ============
# Los casos normales miden CONTENIDO. Los que llevan "debe_abstenerse" miden si
# el sistema supo callarse: su respuesta correcta es admitir que no sabe.
DATASET = [
    {"pregunta": "¿Cuál es el horario de atención?",
     "esperado": ["lunes", "viernes", "9:00", "18:00"]},
    {"pregunta": "¿Hasta cuándo puedo pedir un reembolso completo?",
     "esperado": ["7 días", "reembolso"]},
    {"pregunta": "¿Qué formas de pago aceptan?",
     "esperado": ["transferencia", "yape", "plin"]},
    {"pregunta": "¿Qué recibo al finalizar un proyecto?",
     "esperado": ["código fuente", "manual", "capacitación", "soporte"]},
    # --- Casos TRAMPA: la respuesta correcta es la abstención ---
    # (1) Dato inexistente: el corpus acepta transferencia, pero no da un número.
    {"pregunta": "¿Cuál es el número de cuenta bancaria para pagar?",
     "esperado": ["no tengo esa información"], "debe_abstenerse": True},
    # (2) Producto que no existe en el corpus.
    {"pregunta": "¿Cuánto cuesta el plan Enterprise?",
     "esperado": ["no tengo esa información"], "debe_abstenerse": True},
    # (3) Trampa LÉXICA: comparte el token literal "pago" con el chunk de formas
    #     de pago, así que el retrieval lo trae y responder() NO se abstiene,
    #     aunque el corpus no diga nada de criptomonedas.
    {"pregunta": "¿Aceptan pago con criptomonedas?",
     "esperado": ["no tengo esa información"], "debe_abstenerse": True},
]


# ============ 3) LAS DOS MÉTRICAS OFFLINE ============
def evaluar_contenido(respuesta: str, esperado: list[str]) -> float:
    """Fracción de términos esperados presentes en la respuesta (0.0 a 1.0)."""
    r = respuesta.lower()
    return sum(1 for t in esperado if t.lower() in r) / len(esperado)


FRASE_ABSTENCION = "no tengo esa información"


def evaluo_abstencion(respuesta: str) -> bool:
    """¿El sistema admitió no saber? True si se abstuvo.

    Deliberadamente boba: busca la frase con la que responder() se rinde. En
    producción sería un clasificador o un juez LLM, pero la IDEA es la misma:
    medir la abstención es una métrica APARTE de medir el contenido.
    """
    return FRASE_ABSTENCION in respuesta.lower()


# ============ 4) EL JUEZ LLM (opcional, gasta cuota) ============
def crear_juez():
    """Devuelve una función juez si hay llave; si no, None (y no pasa nada)."""
    if str(CARPETA_CURSO) not in sys.path:
        sys.path.insert(0, str(CARPETA_CURSO))
    from util import crear_llm, requiere_llm_key
    from pydantic import BaseModel, Field

    if requiere_llm_key():
        return None

    class Veredicto(BaseModel):
        """Calificación del juez sobre una respuesta."""
        correcta: bool = Field(description="¿La respuesta contesta bien la pregunta?")
        motivo: str = Field(description="Justificación en una frase")

    juez = crear_llm(temperature=0).with_structured_output(Veredicto)

    def juzgar(pregunta: str, respuesta: str) -> str:
        v = juez.invoke(
            f"Pregunta del usuario: {pregunta}\n"
            f"Respuesta del sistema: {respuesta}\n"
            "¿La respuesta contesta correctamente la pregunta? "
            "Si la información no existe, admitirlo también cuenta como correcto."
        )
        return f"{'✅' if v.correcta else '❌'} juez: {v.motivo}"

    return juzgar


# ============ 5) EL INFORME: contenido Y abstención, separados ============
def main():
    chunks = cargar_chunks()
    juzgar = crear_juez()
    if juzgar is None:
        print("ℹ️  Sin llave del proveedor: corro solo las métricas offline "
              "(suficiente para el criterio de aceptación).")

    casos_trampa = [c for c in DATASET if c.get("debe_abstenerse")]
    casos_normales = [c for c in DATASET if not c.get("debe_abstenerse")]

    print(f"\n=== Evaluando {len(DATASET)} preguntas "
          f"({len(casos_normales)} normales, {len(casos_trampa)} trampa) ===")

    contenido_total = 0.0
    abstenciones_ok = 0
    for caso in DATASET:
        respuesta = responder(caso["pregunta"], chunks)
        contenido = evaluar_contenido(respuesta, caso["esperado"])
        contenido_total += contenido
        es_trampa = caso.get("debe_abstenerse", False)
        se_abstuvo = evaluo_abstencion(respuesta)
        if es_trampa and se_abstuvo:
            abstenciones_ok += 1

        etiqueta = "🪤 TRAMPA" if es_trampa else "•"
        print(f"\n{etiqueta} {caso['pregunta']}")
        print(f"  respuesta: {respuesta[:80]}" + ("…" if len(respuesta) > 80 else ""))
        print(f"  contenido: {contenido:.0%}   ·   ¿se abstuvo?: {'sí' if se_abstuvo else 'no'}")
        if juzgar:
            try:
                print(f"  {juzgar(caso['pregunta'], respuesta)}")
            except Exception as error:
                if "429" in str(error) or "RESOURCE_EXHAUSTED" in str(error):
                    print("  ⚠️ Cuota agotada (429): el juez descansa, la métrica offline sigue.")
                    juzgar = None
                else:
                    raise

    # ---- Los DOS números que vigilas, separados ----
    print(f"\n{'=' * 56}")
    print(f"CONTENIDO  (media sobre {len(DATASET)}): {contenido_total / len(DATASET):.0%}")
    print(f"ABSTENCIÓN (trampas detectadas): {abstenciones_ok}/{len(casos_trampa)}")
    print("=" * 56)
    print("Un RAG puede sacar 100% en CONTENIDO y ser peligroso si su ABSTENCIÓN")
    print("baja: significa que responde incluso a lo que no sabe. Vigila las dos.")


# ============ 6) TESTS QUE PEDÍA EL EJERCICIO ============
# Funciones puras, offline (estilo TestTema16bObservabilidad). Cópialos a tests/:
#
#   def test_la_trampa_lexica_no_se_abstiene_pero_falla_en_contenido(sol16):
#       chunks = sol16.cargar_chunks()
#       r = sol16.responder("¿Aceptan pago con criptomonedas?", chunks)
#       # Comparte el token "pago" con el chunk de formas de pago -> NO se abstiene…
#       assert sol16.evaluo_abstencion(r) is False
#       # …pero frente a un esperado de abstención, el contenido lo marca como 0%.
#       assert sol16.evaluar_contenido(r, ["no tengo esa información"]) == 0.0
#
#   def test_una_pregunta_fuera_del_corpus_si_se_abstiene(sol16):
#       chunks = sol16.cargar_chunks()
#       r = sol16.responder("¿Cuál es la capital de Australia?", chunks)
#       assert sol16.evaluo_abstencion(r) is True


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ No encuentro datos_rag.txt (debe estar en curso_ejemplos/).")
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
