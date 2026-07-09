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
"""

import os


def es_error_cuota(exc: BaseException) -> bool:
    """¿Es esta excepción un error de cuota de Gemini (429)?

    El plan gratuito devuelve 'RESOURCE_EXHAUSTED' (código HTTP 429) cuando
    gastas el cupo por minuto o por día. No es un bug del código: solo hay
    que esperar o cambiar de modelo. Esta función lo distingue de otros errores.
    """
    texto = str(exc)
    return "RESOURCE_EXHAUSTED" in texto or "429" in texto


def mensaje_cuota() -> str:
    """El mensaje amable que mostramos cuando se agota la cuota."""
    return ("⏳ Cuota de Gemini agotada (429). "
            "Espera unos minutos o usa 'gemini-2.5-flash'.")


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
    """
    if not os.getenv("GOOGLE_API_KEY"):
        return ("❌ Falta GOOGLE_API_KEY. Copia .env.example a .env y pon tu llave.")
    return None
