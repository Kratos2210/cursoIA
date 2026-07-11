"""
TEMA 27 · Fundamentos: qué hay DENTRO de la caja
================================================
FINALIDAD:
  Durante 26 módulos usaste el modelo como una caja negra: le pasabas texto y
  te devolvía texto. Este módulo la ABRE. No para que entrenes uno (eso son
  millones de dólares en GPUs), sino para que entiendas las cuatro piezas que
  explican todo lo que ya viste:

    1) TOKENIZACIÓN (BPE): el modelo no lee letras ni palabras, lee "tokens"
       —trozos de palabra. Un mini-BPE didáctico muestra por qué "proyectos"
       cuesta un token MÁS que "proyecto" (y por eso se cobra por token: m16b).
    2) SOFTMAX CON TEMPERATURA: qué hace de VERDAD `temperature=0`. El modelo no
       "elige" una palabra: produce un logit por cada token posible; softmax los
       vuelve probabilidades y la temperatura decide si la distribución se
       concentra (t→0, determinista) o se aplana (t alta, creativa/arriesgada).
    3) MUESTREO top_k / top_p: cómo se saca UNA palabra de esa distribución sin
       caer siempre en la más probable ni en cualquier disparate improbable.
    4) PERPLEJIDAD: "qué tan sorprendido está el modelo" por un texto. Es la
       métrica clásica de fluidez —y en el m28 reaparece como filtro defensivo:
       un prompt adversarial "sorprende" al modelo (perplejidad alta).

  Y una quinta, conceptual: ATENCIÓN —"a qué palabras mira cada palabra"— como
  un producto punto entre vectores, el mismo espíritu de los vectores de
  frecuencia del m12/m24.

  ⭐ 100% OFFLINE. Todo son FUNCIONES PURAS de números y texto: sin red, sin
     API, sin llave. Se pueden testear byte a byte. No hay parte online: aquí no
     se llama a ningún modelo, se explica cómo funciona por dentro el que ya usas.

LÓGICA (paso a paso):
  1) aprender_merges() + tokenizar_bpe(): el mini-tokenizador BPE.
  2) softmax_con_temperatura(): logits → probabilidades, moduladas por t.
  3) muestrear_top_k() / muestrear_top_p(): sacar un índice con un Random inyectado.
  4) calcular_perplejidad(): exp(-media de log-probabilidades).
  5) pesos_atencion(): softmax de productos punto (a qué mira cada palabra).

Requisitos: ninguno extra (solo Python).  No usa red.
Ejecuta:    uv run python 27_fundamentos_llm.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import math                          # exp/log para softmax y perplejidad
import random                        # solo el tipo Random inyectado (determinista)
from collections import Counter      # contar pares adyacentes al aprender BPE


# ==================================================================
# 1) TOKENIZACIÓN · el modelo lee TROZOS de palabra, no letras
# ==================================================================
# BPE (Byte-Pair Encoding) parte de caracteres sueltos y, de forma repetida,
# FUSIONA el par adyacente más frecuente en un token nuevo. Así los trozos que
# aparecen mucho ("proyect", "to") se vuelven una sola pieza y los raros quedan
# partidos. Es —simplificado— lo que hacen GPT, Gemini o Claude por dentro.

def _aplicar_merge(secuencia: list[str], a: str, b: str) -> list[str]:
    """Recorre la secuencia y fusiona cada aparición del par (a, b) en 'a+b'."""
    salida: list[str] = []
    i = 0
    while i < len(secuencia):
        # Si el token actual y el siguiente son justo el par a fusionar, únelos.
        if i < len(secuencia) - 1 and secuencia[i] == a and secuencia[i + 1] == b:
            salida.append(a + b)
            i += 2
        else:
            salida.append(secuencia[i])
            i += 1
    return salida


def aprender_merges(corpus: list[str], n_merges: int) -> list[tuple[str, str]]:
    """Aprende hasta `n_merges` fusiones a partir de un corpus de palabras.

    POR QUÉ funciona: si un par de símbolos ("t","o") aparece en muchas palabras,
    conviene tratarlo como UNA pieza —es información que se repite—. Repitiendo la
    fusión del par más frecuente, el vocabulario acaba lleno de los trozos útiles
    del idioma. Determinista: a igualdad de frecuencia, gana el par menor
    alfabéticamente, así el resultado no depende del azar y se puede testear.
    """
    secuencias = [list(palabra) for palabra in corpus]  # cada palabra, en caracteres
    merges: list[tuple[str, str]] = []
    for _ in range(n_merges):
        pares: Counter = Counter()
        for secuencia in secuencias:
            for a, b in zip(secuencia, secuencia[1:]):
                pares[(a, b)] += 1
        if not pares:
            break  # ya no quedan pares que fusionar
        # Más frecuente primero (-conteo); empate → par menor alfabéticamente.
        mejor = min(pares.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        merges.append(mejor)
        secuencias = [_aplicar_merge(s, *mejor) for s in secuencias]
    return merges


def tokenizar_bpe(palabra: str, merges: list[tuple[str, str]]) -> list[str]:
    """Aplica las fusiones aprendidas, EN ORDEN, para tokenizar una palabra.

    El orden importa: cada merge se apoya en los anteriores (primero "t"+"o"→"to",
    luego "ec"+"to"→"ecto"…). Una palabra nueva reutiliza los trozos que quepan;
    lo que no encaje se queda en piezas pequeñas —por eso un plural ("proyectos")
    suele costar un token más que su singular ("proyecto").
    """
    secuencia = list(palabra)
    for a, b in merges:
        secuencia = _aplicar_merge(secuencia, a, b)
    return secuencia


# ==================================================================
# 2) SOFTMAX CON TEMPERATURA · qué hace de verdad temperature=0
# ==================================================================
def softmax_con_temperatura(logits: list[float], t: float) -> list[float]:
    """Convierte logits (puntajes crudos) en probabilidades que suman 1.

    El modelo NO elige una palabra: para cada token posible emite un logit. Softmax
    los vuelve probabilidades. La temperatura `t` las modula ANTES de normalizar:
      · t → 0  : la distribución se concentra en el logit mayor (determinista).
                 En el límite es 'greedy': siempre el token más probable. Eso es
                 lo que hace `temperature=0` del m01, no "apagar la creatividad".
      · t = 1  : la distribución tal cual la aprendió el modelo.
      · t alta : se aplana hacia lo uniforme (más azar, más riesgo de disparate).

    Determinista y estable: restamos el máximo antes de exp() para no desbordar.
    """
    if not logits:
        return []
    if t <= 0:
        # Límite t→0: toda la masa en el logit máximo (el primero, si hay empate).
        indice = max(range(len(logits)), key=lambda i: logits[i])
        return [1.0 if i == indice else 0.0 for i in range(len(logits))]
    escalados = [x / t for x in logits]
    tope = max(escalados)                       # estabilidad numérica
    exp = [math.exp(x - tope) for x in escalados]
    suma = sum(exp)
    return [e / suma for e in exp]


# ==================================================================
# 3) MUESTREO · sacar UN token de la distribución (top_k / top_p)
# ==================================================================
# Elegir siempre el más probable (greedy) hace el texto plano y repetitivo;
# muestrear de TODA la distribución deja pasar disparates improbables. Los dos
# recortes de siempre: top_k (los k mejores) y top_p (los que suman prob. p).

def _muestrear_de(indices: list[int], logits: list[float], rng: random.Random) -> int:
    """Muestrea un índice de `indices` con prob. ∝ softmax de sus logits.

    Usa el método de la ruleta acumulada con el Random inyectado: mismo `rng`
    (misma semilla) → misma salida, así el muestreo es testeable sin ser trivial.
    """
    sub_probs = softmax_con_temperatura([logits[i] for i in indices], 1.0)
    umbral = rng.random()
    acumulado = 0.0
    for indice, p in zip(indices, sub_probs):
        acumulado += p
        if umbral <= acumulado:
            return indice
    return indices[-1]  # por redondeo del acumulado; cae en el último candidato


def muestrear_top_k(logits: list[float], k: int, rng: random.Random) -> int:
    """Muestrea SOLO entre los `k` tokens de mayor logit (el resto, descartado).

    POR QUÉ: acota el azar a los candidatos razonables. Con k=1 es greedy puro;
    subir k admite más variedad sin abrir la puerta a los tokens absurdos de la
    cola. El índice devuelto SIEMPRE está entre esos k mejores.
    """
    k = max(1, min(k, len(logits)))
    mejores = sorted(range(len(logits)), key=lambda i: logits[i], reverse=True)[:k]
    return _muestrear_de(mejores, logits, rng)


def muestrear_top_p(logits: list[float], p: float, rng: random.Random) -> int:
    """Muestreo de núcleo: el menor conjunto de tokens cuya prob. suma ≥ `p`.

    POR QUÉ es mejor que top_k fijo: el tamaño del conjunto se ADAPTA. Si el modelo
    está segurísimo, uno o dos tokens ya suman p y apenas hay azar; si duda, el
    núcleo se ensancha solo. El índice devuelto está dentro de ese núcleo.
    """
    probs = softmax_con_temperatura(logits, 1.0)
    orden = sorted(range(len(logits)), key=lambda i: probs[i], reverse=True)
    nucleo: list[int] = []
    acumulado = 0.0
    for indice in orden:
        nucleo.append(indice)
        acumulado += probs[indice]
        if acumulado >= p:
            break
    return _muestrear_de(nucleo, logits, rng)


# ==================================================================
# 4) PERPLEJIDAD · "qué tan sorprendido está el modelo" por un texto
# ==================================================================
def calcular_perplejidad(probabilidades: list[float]) -> float:
    """Perplejidad = exp(-media de log-probabilidades) de los tokens observados.

    Cada número es la probabilidad que el modelo le dio al token que REALMENTE
    apareció. Si a un texto fluido le asignó probabilidades altas, la perplejidad
    es baja ("no me sorprende, esto lo esperaba"); si tuvo que apostar por tokens
    que creía improbables, la perplejidad se dispara.

    Conecta con el m28: un prompt adversarial o basura tiene tokens improbables →
    perplejidad alta → un 'filtro de perplejidad' puede marcarlo como sospechoso.
    Contrato: lista vacía o alguna prob. ≤ 0 (sorpresa infinita) → inf.
    """
    if not probabilidades or any(p <= 0 for p in probabilidades):
        return float("inf")
    log_medio = sum(math.log(p) for p in probabilidades) / len(probabilidades)
    return math.exp(-log_medio)


# ==================================================================
# 5) ATENCIÓN · a qué palabras mira cada palabra (producto punto)
# ==================================================================
def _producto_punto(u: list[float], v: list[float]) -> float:
    """Producto punto: cuánto se parecen dos vectores (el mismo del coseno del m12)."""
    return sum(a * b for a, b in zip(u, v))


def pesos_atencion(consulta: list[float], claves: list[list[float]]) -> list[float]:
    """Cuánta atención pone una 'consulta' en cada 'clave': softmax de sus similitudes.

    Idea del transformer, sin frameworks: cada palabra pregunta "¿con cuáles de las
    demás me relaciono?". La afinidad es el producto punto entre su vector-consulta
    y el vector-clave de cada palabra; softmax lo vuelve un reparto de atención que
    suma 1. La clave más parecida a la consulta se lleva el peso mayor.
    """
    afinidades = [_producto_punto(consulta, clave) for clave in claves]
    return softmax_con_temperatura(afinidades, 1.0)


# ==================================================================
# main() · demostración 100% OFFLINE (no toca la red)
# ==================================================================
def main() -> None:
    print("=" * 64)
    print("FUNDAMENTOS DEL LLM · qué hay dentro de la caja (100% OFFLINE)")
    print("=" * 64)

    # --- Tokenización: por qué el plural cuesta un token más ---
    corpus = ["proyecto", "objeto", "efecto", "afecto", "insecto", "dialecto"]
    merges = aprender_merges(corpus, n_merges=12)
    singular = tokenizar_bpe("proyecto", merges)
    plural = tokenizar_bpe("proyectos", merges)
    print("\n[1] TOKENIZACIÓN (BPE) · el modelo lee trozos, no palabras:")
    print(f"    'proyecto'  → {singular}  ({len(singular)} tokens)")
    print(f"    'proyectos' → {plural}  ({len(plural)} tokens)")
    print("    → el plural cuesta un token MÁS: por eso se cobra por token (m16b).")

    # --- Softmax: qué hace la temperatura ---
    logits = [2.0, 1.0, 0.2, -1.0]
    fria = softmax_con_temperatura(logits, 0.5)
    tibia = softmax_con_temperatura(logits, 1.0)
    caliente = softmax_con_temperatura(logits, 2.0)
    print("\n[2] SOFTMAX CON TEMPERATURA · sobre logits", logits)
    print(f"    t=0.5 (fría)    : {[round(p, 3) for p in fria]}  ← se concentra")
    print(f"    t=1.0 (normal)  : {[round(p, 3) for p in tibia]}")
    print(f"    t=2.0 (caliente): {[round(p, 3) for p in caliente]}  ← se aplana")

    # --- Muestreo: top_k y top_p con un Random determinista ---
    rng = random.Random(42)
    top_k = [muestrear_top_k(logits, 2, rng) for _ in range(6)]
    rng = random.Random(42)
    top_p = [muestrear_top_p(logits, 0.9, rng) for _ in range(6)]
    print("\n[3] MUESTREO (Random(42), determinista) · índice del token elegido:")
    print(f"    top_k=2  → {top_k}   (solo salen los 2 mejores: índices 0 y 1)")
    print(f"    top_p=.9 → {top_p}")

    # --- Perplejidad: fluido vs basura ---
    fluido = [0.9, 0.85, 0.8, 0.92]        # el modelo esperaba estos tokens
    basura = [0.05, 0.1, 0.02, 0.08]       # tuvo que apostar por improbables
    print("\n[4] PERPLEJIDAD · exp(-media de log-prob):")
    print(f"    texto fluido  {fluido} → {calcular_perplejidad(fluido):.2f}  (baja = no sorprende)")
    print(f"    texto basura  {basura} → {calcular_perplejidad(basura):.2f}  (alta = sospechoso, ver m28)")

    # --- Atención: a qué mira la palabra 'consulta' ---
    consulta = [1.0, 0.0, 1.0]             # vector de la palabra que "pregunta"
    claves = [[1.0, 0.0, 1.0],             # palabra muy afín
              [0.0, 1.0, 0.0],             # ortogonal (nada que ver)
              [0.5, 0.0, 0.5]]             # medianamente afín
    pesos = pesos_atencion(consulta, claves)
    print("\n[5] ATENCIÓN · reparto de atención de la consulta sobre 3 palabras:")
    print(f"    pesos = {[round(p, 3) for p in pesos]}  → mira sobre todo a la 1ª (la más afín)")
    print("\n→ Esto es lo que hay bajo `crear_llm()`: tokens, logits, softmax y atención.")


if __name__ == "__main__":
    main()
