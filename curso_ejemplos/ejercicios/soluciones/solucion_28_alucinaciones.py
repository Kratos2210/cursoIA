"""
SOLUCIÓN · Ejercicio 28 — Alucinaciones: mide la sospecha, no la confíes
=========================================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Poner números (y asserts) a los cuatro hallazgos del ejercicio:
    · P1: la tilde parte "Paris"/"parís" en dos → score 0.5, no 0.25.
    · P2: 5 respuestas idénticas y FALSAS dan 0.0 — consistencia ≠ verdad.
    · P3: "En 1969" no se unifica con "1969" → fragilidad sobre-reportada.
    · P4: la taxonomía se consulta con código, no se recita.

  100% offline: aritmética sobre strings. No gasta cuota.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_28_alucinaciones.py
"""

import importlib.util
import os

# ---- Cargamos el ejemplo 28 (su nombre empieza por número: no se puede importar) ----
CARPETA_CURSO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cargar_tema28():
    ruta = os.path.join(CARPETA_CURSO, "28_alucinaciones.py")
    spec = importlib.util.spec_from_file_location("tema28", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


t28 = cargar_tema28()


# ==================================================================
# PARTE 1 · Predice el score (y la trampa de la tilde)
# ==================================================================
def parte_1():
    print("\n[P1] cuatro muestras de '¿capital de Francia?'")
    respuestas = ["París.", " parís ", "Paris", "Lyon"]
    score = t28.detectar_inconsistencia(respuestas)
    print(f"     respuestas: {respuestas}")
    print(f"     score = {score} · es_sospechosa = {t28.es_sospechosa(respuestas)}")

    # La predicción ingenua es 0.25 ('tres dicen París'). Pero _normalizar
    # quita puntuación y mayúsculas, NO tildes: 'paris' ≠ 'parís'.
    # Conteo real: parís×2, paris×1, lyon×1 → 1 - 2/4 = 0.5 → sospechosa.
    assert score == 0.5
    assert t28.es_sospechosa(respuestas) is True
    print("     → la tilde parte la mayoría en dos: comparar strings ≠ comparar")
    print("       significados. (El 29 usa _sin_tildes para esto mismo.)")


# ==================================================================
# PARTE 2 · Consistencia perfecta, falsedad perfecta
# ==================================================================
def parte_2():
    print("\n[P2] el error sistemático es invisible para el self-check")
    mentira_convencida = ["Lima fue fundada en 1540"] * 5     # fue en 1535
    score = t28.detectar_inconsistencia(mentira_convencida)
    print(f"     5× la misma respuesta falsa → score = {score}")
    assert score == 0.0

    # El detector mide DISPERSIÓN. Si el modelo se aprendió mal el dato, lo
    # repite igual de convencido en cada muestra: score 0.0, indistinguible de
    # saberlo bien. Contra ESO no hay self-check: hay grounding (m11, RAG con
    # la fuente delante) — y la taxonomía lo dice con datos:
    causas_m11 = t28.causas_por_modulo("m11")
    print(f"     causas que mitiga el m11 según la taxonomía: {causas_m11}")
    assert causas_m11, "la taxonomía debería mapear causas al m11"
    print("     → consistencia ≠ verdad; el error sistemático se ataca con RAG.")


# ==================================================================
# PARTE 3 · Fragilidad sobre-reportada
# ==================================================================
def parte_3():
    print("\n[P3] ¿cuántas respuestas 'distintas' hay aquí?")
    respuestas = ["1969", "En 1969", "1969."]
    n = t28.medir_fragilidad(respuestas)
    print(f"     {respuestas} → medir_fragilidad = {n} · es_fragil = {t28.es_fragil(respuestas)}")

    # '1969.' se unifica con '1969' (puntuación de borde); 'En 1969' NO
    # (queda 'en 1969'). Tres respuestas que dicen lo mismo cuentan como 2.
    assert n == 2
    assert t28.es_fragil(respuestas) is True
    print("     → sobre-reporta: para texto libre haría falta similitud semántica")
    print("       (m11/m12) o extraer el dato con salida estructurada (m05).")


# ==================================================================
# PARTE 4 · La taxonomía se consulta, no se recita
# ==================================================================
def parte_4():
    print("\n[P4] el mapa causa→módulo, desde los datos")
    modulos = sorted(t28.modulos_de_mitigacion())
    for modulo in modulos:
        print(f"     {modulo:>5} → {t28.causas_por_modulo(modulo)}")
    assert modulos, "la taxonomía no puede estar vacía"
    print("     → si tu predicción coincidió al 100%, tocaba elegir módulos más raros.")


def main() -> None:
    print("=" * 64)
    print("SOLUCIÓN 28 · el detector, con sus puntos ciegos (100% OFFLINE)")
    print("=" * 64)
    parte_1()
    parte_2()
    parte_3()
    parte_4()
    print("\nTodo comprobado con asserts. ✅")


if __name__ == "__main__":
    main()
