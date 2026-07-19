"""
SOLUCIÓN · Ejercicio 27 — Fundamentos: qué significan de verdad tus parámetros
===============================================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Calcular —no opinar— las cinco partes del ejercicio con las funciones del
  27_fundamentos_llm.py. Cada afirmación importante va con un `assert`: si
  alguna dejara de ser cierta, este archivo revienta en vez de mentir.

  Las morales, en corto:
    · P1: BPE fusiona lo FRECUENTE; el plural (y los idiomas raros) cuestan más.
    · P2: t=0.1 ES t=0 en la práctica; t=10 aplana pero JAMÁS reordena.
    · P3: top_p por debajo de la prob. del token top = greedy disfrazado.
    · P4: perplejidad N = "indeciso entre N opciones"; inf = 'lo creía imposible'.
    · P5: la perplejidad como filtro es una señal, nunca un bloqueo.

  100% offline: todo son funciones puras y deterministas. No gasta cuota.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_27_fundamentos.py
"""

import importlib.util
import math
import os
import random
from collections import Counter

# ---- Cargamos el ejemplo 27 (su nombre empieza por número: no se puede importar) ----
CARPETA_CURSO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cargar_tema27():
    ruta = os.path.join(CARPETA_CURSO, "27_fundamentos_llm.py")
    spec = importlib.util.spec_from_file_location("tema27", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


t27 = cargar_tema27()

LOGITS = [2.0, 1.0, 0.2, -1.0]


# ==================================================================
# PARTE 1 · El plural que cuesta un token
# ==================================================================
def parte_1():
    print("\n[P1] BPE · 'proyecto' vs 'proyectos'")
    corpus = ["proyecto", "objeto", "efecto", "afecto", "insecto", "dialecto"]
    merges = t27.aprender_merges(corpus, n_merges=12)
    singular = t27.tokenizar_bpe("proyecto", merges)
    plural = t27.tokenizar_bpe("proyectos", merges)
    print(f"     'proyecto'  → {singular}  ({len(singular)} tokens)")
    print(f"     'proyectos' → {plural}  ({len(plural)} tokens)")

    # El plural cuesta EXACTAMENTE un token más: la 's' final nunca se fusionó
    # con nada porque 'proyectos' no estaba en el corpus.
    assert len(plural) == len(singular) + 1

    # 'ecto' es una sola pieza (aparece en casi todo el corpus y se fusiona en
    # cadena to→cto→ecto); 'proy' sigue partido porque solo existe en UNA palabra.
    assert "ecto" in singular and "proy" not in singular

    print("     → 'ecto' se fusionó (frecuente en el corpus); 'proy' no (aparece 1 vez).")
    print("     → Moraleja de factura: un idioma mal representado en el corpus del")
    print("       tokenizador paga 2–3× más tokens por decir lo mismo.")


# ==================================================================
# PARTE 2 · La temperatura que no cambia nada
# ==================================================================
def parte_2():
    print("\n[P2] softmax_con_temperatura sobre", LOGITS)
    for t in (0, 0.1, 0.5, 1.0, 2.0, 10.0):
        probs = t27.softmax_con_temperatura(LOGITS, t)
        print(f"     t={t:<4} → {[round(p, 4) for p in probs]}")

    # 1) A 4 decimales, t=0.1 YA es indistinguible de t=0: dividir por 0.1
    #    multiplica los logits por 10 y el token 0 se lleva ~el 99.995%.
    p0 = [round(p, 4) for p in t27.softmax_con_temperatura(LOGITS, 0)]
    p01 = [round(p, 4) for p in t27.softmax_con_temperatura(LOGITS, 0.1)]
    assert p0 == p01
    print("     → t=0.1 == t=0 con 4 decimales: 'casi determinista' es determinista.")

    # 2) Con t=10 se ACERCA a lo uniforme (0.25) pero no llega: el orden se
    #    conserva siempre, softmax es monótona. La temperatura aplana, no reordena.
    p10 = t27.softmax_con_temperatura(LOGITS, 10.0)
    assert p10[0] > 0.25 > p10[3]
    assert p10 == sorted(p10, reverse=True)
    ventaja = p10[0] - p10[3]
    print(f"     → t=10: el token 0 aún le saca {ventaja:.4f} al token 3. No es uniforme.")

    # 3) temperature=0 no apaga "la creatividad": apaga el MUESTREO. El modelo
    #    sigue sabiendo lo mismo; solo deja de tirar el dado.
    print("     → t=0 no apaga la creatividad: apaga el dado.")


# ==================================================================
# PARTE 3 · El top_p que es un top_k=1 disfrazado
# ==================================================================
def parte_3():
    print("\n[P3] muestrear_top_p, 2000 tiradas por valor de p")
    conteos = {}
    for p in (0.5, 0.9, 1.0):
        rng = random.Random(42)
        conteos[p] = Counter(t27.muestrear_top_p(LOGITS, p, rng) for _ in range(2000))
        print(f"     p={p:<4} → {dict(sorted(conteos[p].items()))}")

    # Con t=1, el token 0 tiene prob ~0.63 ≥ 0.5: el núcleo se cierra con UN
    # solo token y el muestreo es greedy puro. p=0.5 aquí ES top_k=1.
    assert set(conteos[0.5]) == {0}
    # Con p=0.9 y p=1.0 sí sale más de un token.
    assert len(conteos[0.9]) > 1 and len(conteos[1.0]) > 1

    probs = t27.softmax_con_temperatura(LOGITS, 1.0)
    print(f"     → prob(token 0) = {probs[0]:.4f} ≥ 0.5: el núcleo tiene UN token.")
    print("     → Al compañero: top_p no es un dial de creatividad, es un recorte")
    print("       de cola. BAJARLO da menos variedad, no más.")


# ==================================================================
# PARTE 4 · La perplejidad tiene unidades
# ==================================================================
def parte_4():
    print("\n[P4] calcular_perplejidad")
    dudaba = t27.calcular_perplejidad([0.25, 0.25, 0.25, 0.25])
    certeza = t27.calcular_perplejidad([1.0, 1.0])
    imposible = t27.calcular_perplejidad([0.5, 0.0])
    print(f"     [0.25]*4   → {dudaba}")
    print(f"     [1.0, 1.0] → {certeza}")
    print(f"     [0.5, 0.0] → {imposible}")

    # exp(-media(log 1/N)) = N: perplejidad 4 = "al azar entre 4 opciones".
    assert dudaba == 4.0
    # Certeza absoluta = 1.0, el mínimo posible: una sola opción efectiva.
    assert certeza == 1.0
    # Un token con prob 0 que SÍ apareció = sorpresa infinita. No es un bug:
    # el modelo consideraba imposible algo que pasó; inf propaga esa señal.
    assert math.isinf(imposible)

    print("     → «una perplejidad de N = tan indeciso como si eligiera al azar")
    print("        entre N opciones equiprobables». inf = 'lo creía imposible'.")


# ==================================================================
# PARTE 5 · El filtro de perplejidad y su falso positivo
# ==================================================================
def parte_5():
    print("\n[P5] la perplejidad como guardarraíl (conecta con m28 y m23)")
    # Un sufijo adversarial generado por gradiente está lleno de tokens
    # improbables → perplejidad altísima → umbral → señal de sospecha.
    print("     Filtro: perplejidad(prompt) > umbral → marcar como sospechoso.")
    # El falso positivo que lo mata como BLOQUEO: lo legítimamente raro —código,
    # logs, ids, jerga, idiomas minoritarios o mezclados—. El sesgo del
    # tokenizador (P1) reaparece como sesgo del filtro de seguridad.
    print("     Falso positivo: usuarios legítimos con texto 'raro' (código, ids,")
    print("     quechua, jerga limeña). Por eso es UNA señal para puntuar, nunca")
    print("     un bloqueo por sí sola — igual que el regex del m23.")


def main() -> None:
    print("=" * 64)
    print("SOLUCIÓN 27 · parámetros calculados, no opinados (100% OFFLINE)")
    print("=" * 64)
    parte_1()
    parte_2()
    parte_3()
    parte_4()
    parte_5()
    print("\nTodo comprobado con asserts. ✅")


if __name__ == "__main__":
    main()
