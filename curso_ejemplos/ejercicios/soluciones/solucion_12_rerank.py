"""
SOLUCIÓN · Ejercicio 12 — Predice el ranking
==========================================================
⚠️ No leas esto hasta haberlo intentado. En serio.

Este archivo resuelve las 4 partes del ejercicio y las EJECUTA, para que puedas
comparar tus predicciones con la realidad.

Es 100% offline: no gasta cuota.
Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_12_rerank.py
"""

import importlib.util
import os
from collections import Counter

# ---- Cargamos el ejemplo 12 (su nombre empieza por número: no se puede importar) ----
CARPETA_CURSO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cargar_tema12():
    ruta = os.path.join(CARPETA_CURSO, "12_rag_hibrido_rerank.py")
    spec = importlib.util.spec_from_file_location("tema12", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


t12 = cargar_tema12()
CHUNKS = t12.cargar_chunks()


# ==================================================================
# PARTE 1 · Una pregunta donde los buscadores discrepan
# ==================================================================
def parte_1():
    print("=" * 70)
    print("PARTE 1 · '¿Puedo pagar en cuotas un proyecto grande?'")
    print("=" * 70)
    pregunta = "¿Puedo pagar en cuotas un proyecto grande?"

    bm25 = t12.ordenar(t12.puntuar_bm25(pregunta, CHUNKS))
    vect = t12.ordenar(t12.puntuar_vectorial(pregunta, CHUNKS))
    hibrido = t12.fusionar_rrf(bm25, vect)
    final = t12.re_rankear(pregunta, CHUNKS, hibrido[:5], top_n=3)

    print(f"  BM25      : {bm25[:3]}")
    print(f"  Vectorial : {vect[:3]}")
    print(f"  RRF       : {hibrido[:3]}")
    print(f"  Re-rankeado: {final}")
    print(f"\n  El chunk correcto es el 6 (Formas de pago), que dice 'dos cuotas'.")
    print(f"  Ganador final: chunk {final[0]} -> {CHUNKS[final[0]].splitlines()[0]}")
    print("""
  ANÁLISIS (probablemente NO era lo que predijiste):

    Los TRES buscadores coinciden en poner primero el chunk 5 (Entregables),
    que es el EQUIVOCADO. No discrepan: se equivocan juntos. Y el híbrido, que
    solo fusiona sus opiniones, hereda el error. Fusionar dos buscadores que
    fallan igual no arregla nada.

    ¿Por qué gana el 5?
      · El chunk 5 contiene 'proyecto' DOS veces ('Entregables de un proyecto:
        Al finalizar un proyecto…'). El TF de BM25 lo premia.
      · El chunk 6 dice 'proyectoS' (plural) y 'pago' (no 'pagar'). Para un
        tokenizador que compara palabras exactas, 'proyecto' != 'proyectos'.
        Solo casa 'cuotas'.

    ¿Quién lo salva? EL RE-RANKER, y por un accidente instructivo: puntúa con
    `palabra in texto`, es decir por SUBCADENA. Y 'proyecto' SÍ está dentro de
    'proyectos'. Cobertura del chunk 6 = 2/5 ('cuotas' + 'proyecto');
    del chunk 5 = 1/5 (solo 'proyecto').

    LA LECCIÓN: el 'proyecto' vs 'proyectos' que rompió a BM25 es MORFOLOGÍA.
    Un buscador de producción la resuelve con stemming/lematización antes de
    indexar. Aquí la resolvió, por casualidad, una comparación de subcadenas.
    Cuenta con que en tu corpus real esa casualidad no te salvará.
""")


# ==================================================================
# PARTE 2 · El fallo que BM25 y el "vectorial" comparten
# ==================================================================
def parte_2():
    print("=" * 70)
    print("PARTE 2 · Sinónimos: 'devolución del dinero' vs 'reembolso'")
    print("=" * 70)
    pregunta = "¿Cómo pido la devolución de mi dinero?"
    correcto = 3   # el chunk de "Política de reembolsos"

    puntajes_bm25 = t12.puntuar_bm25(pregunta, CHUNKS)
    puntajes_vect = t12.puntuar_vectorial(pregunta, CHUNKS)
    rank_bm25 = t12.ordenar(puntajes_bm25)
    rank_vect = t12.ordenar(puntajes_vect)
    hibrido = t12.fusionar_rrf(rank_bm25, rank_vect)
    final = t12.re_rankear(pregunta, CHUNKS, hibrido[:5], top_n=3)

    print(f"  Chunk correcto (3): {CHUNKS[correcto].splitlines()[0]}\n")
    print(f"  BM25      : {rank_bm25}   (el 3 queda en puesto {rank_bm25.index(correcto) + 1})")
    print(f"  Vectorial : {rank_vect}   (el 3 queda en puesto {rank_vect.index(correcto) + 1})")
    print(f"  RRF       : {hibrido}")
    print(f"  Re-rankeado: {final}   ->  el chunk 3 NO aparece.")

    # La demostración cruda: 'devolución' y 'reembolso' no comparten nada.
    v1 = Counter(t12.tokenizar("devolución del dinero"))
    v2 = Counter(t12.tokenizar("reembolso completo"))
    print(f"\n  coseno('devolución del dinero', 'reembolso completo') = "
          f"{t12.similitud_coseno(v1, v2):.4f}")
    print(f"  palabras compartidas entre la pregunta y el chunk 3: "
          f"{set(t12.tokenizar(pregunta)) & set(t12.tokenizar(CHUNKS[correcto]))}")
    print("""
  ANÁLISIS — aquí hay TRES fallos, no uno:

  (1) SINÓNIMOS. 'devolución' y 'reembolso' no comparten ni una letra útil:
      su coseno es exactamente 0. El chunk correcto es invisible para ambos
      buscadores. Y fíjate en por qué el 'vectorial' falla igual que BM25:
      convierte cada texto en un vector de CONTEO DE PALABRAS, así que solo
      mide coincidencia léxica, con otra fórmula. NO entiende significado.
      Los embeddings reales (gemini-embedding-001) sí: colocan 'devolución'
      y 'reembolso' cerca en un espacio aprendido de millones de textos.
      Este ejemplo enseña la MECÁNICA de un RAG híbrido, no el PODER de los
      embeddings. Confundirlos es el error más común al aprender RAG.

  (2) STOPWORDS. ¿Quién gana entonces? El chunk 0, el TÍTULO, que no responde
      nada. Lo único que comparte con la pregunta es la palabra 'de'. Pero el
      chunk 0 es muy CORTO, y la normalización por longitud de BM25 (el
      parámetro b) premia enormemente a los documentos cortos que casan.
      Resultado: el chunk de ruido gana por una preposición.
      En producción, lo primero que se hace es eliminar stopwords.

  (3) EMPATES SILENCIOSOS. El re-ranker calcula la cobertura con las palabras
      de más de 3 letras: 'cómo', 'pido', 'devolución', 'dinero'. Ninguna
      aparece en NINGÚN chunk. Todos puntúan 0.0, y `puntuados.sort(reverse=True)`
      desempata por el ÍNDICE del chunk, de mayor a menor. Por eso devuelve
      [5, 4, 2]: un orden completamente arbitrario que parece un ranking.

      Este es el fallo más peligroso de los tres, porque NO se nota: el sistema
      devuelve tres fragmentos con toda la confianza del mundo. Un re-ranker de
      producción debe devolver también el PUNTAJE, para que quien lo llame pueda
      decir "todos por debajo del umbral: no tengo respuesta".
""")


# ==================================================================
# PARTE 3 · Mide, no opines: precision@1
# ==================================================================
# Un mini-dataset: pregunta -> índice del chunk que DEBERÍA quedar primero.
#
# Las 4 primeras son FÁCILES: usan las mismas palabras que el documento.
# Las 2 últimas son las de las Partes 1 y 2 — las difíciles. Un dataset con
# solo preguntas fáciles da 100% en todas las configuraciones y no distingue
# nada: es el error nº1 al construir un set de evaluación.
DATASET = [
    ("¿Cuál es el horario de atención?", 2),
    ("¿Quién controla las llaves de API?", 4),
    ("¿Qué formas de pago aceptan?", 6),
    ("¿Qué recibo al finalizar un proyecto?", 5),
    # Difícil 1 — morfología: 'proyecto' vs 'proyectos'.
    ("¿Puedo pagar en cuotas un proyecto grande?", 6),
    # Difícil 2 — sinónimos: 'devolución' vs 'reembolso'.
    ("¿Cómo pido la devolución de mi dinero?", 3),
]


def precision_en_1(ranquear) -> float:
    """Fracción de preguntas cuyo chunk correcto queda en 1er lugar."""
    aciertos = sum(1 for pregunta, correcto in DATASET
                   if ranquear(pregunta)[0] == correcto)
    return aciertos / len(DATASET)


def parte_3():
    print("=" * 70)
    print("PARTE 3 · precision@1 de las cuatro configuraciones")
    print("=" * 70)

    solo_bm25 = lambda p: t12.ordenar(t12.puntuar_bm25(p, CHUNKS))          # noqa: E731
    solo_vect = lambda p: t12.ordenar(t12.puntuar_vectorial(p, CHUNKS))     # noqa: E731
    hibrido = lambda p: t12.fusionar_rrf(solo_bm25(p), solo_vect(p))        # noqa: E731
    completo = lambda p: t12.re_rankear(p, CHUNKS, hibrido(p)[:5], top_n=3)  # noqa: E731

    configuraciones = [
        ("Solo BM25", solo_bm25),
        ("Solo vectorial", solo_vect),
        ("Híbrido (RRF)", hibrido),
        ("Híbrido + re-ranking", completo),
    ]

    print(f"\n  {'Configuración':<24} precision@1")
    print(f"  {'-' * 24} -----------")
    for nombre, funcion in configuraciones:
        print(f"  {nombre:<24} {precision_en_1(funcion):.0%}")

    # ¿Dónde falla cada una? Ese detalle enseña más que el número global.
    print("\n  Desglose por pregunta (chunk que quedó 1º):")
    print(f"  {'pregunta':<42} {'ok':>4} {'bm25':>5} {'vect':>5} {'rrf':>5} {'full':>5}")
    for pregunta, correcto in DATASET:
        print(f"  {pregunta[:40]:<42} {correcto:>4} "
              f"{solo_bm25(pregunta)[0]:>5} {solo_vect(pregunta)[0]:>5} "
              f"{hibrido(pregunta)[0]:>5} {completo(pregunta)[0]:>5}")

    print("""
  ANÁLISIS honesto (lee esto entero, es lo más importante del ejercicio):

    · Con las 4 preguntas FÁCILES, las cuatro configuraciones dan 100%. Un
      dataset así no mide nada: no puede distinguir un buen retriever de uno
      malo. Si solo hubieras probado esas 4, habrías concluido que tu RAG es
      perfecto. Es EL error nº1 al construir un set de evaluación.

    · Al añadir las 2 difíciles aparece la verdad: BM25, el vectorial y el
      híbrido fallan en AMBAS. El re-ranking rescata una (la de morfología) y
      no puede con la otra (la de sinónimos), porque el problema no está en el
      orden: está en que el chunk correcto nunca llegó a los candidatos.

    · El HÍBRIDO NO MEJORA a sus dos componentes. Ni un punto. ¿Por qué?
      Porque RRF fusiona OPINIONES, y aquí las dos opiniones son la misma
      (ambos buscadores miden coincidencia léxica). Fusionar dos buscadores
      que se equivocan igual no arregla nada: solo promedia el mismo error.
      Un híbrido de verdad combina señales INDEPENDIENTES — léxica (BM25) y
      semántica (embeddings reales). Este ejemplo no tiene la segunda.

    · Y con 6 preguntas, cada una vale un 16.7%. Estos números no demuestran
      nada estadísticamente. En producción, un dataset de menos de ~50 ejemplos
      te dirá que tu cambio 'mejoró un 4%' cuando no cambió nada.

    Lo que SÍ puedes concluir: 'no puedo arreglar en el re-ranking lo que
    perdí en la recuperación'. Si el chunk correcto no está entre los
    candidatos, ningún reordenamiento lo va a inventar.
""")


# ==================================================================
# PARTE 4 · Romper el RRF
# ==================================================================
def parte_4():
    print("=" * 70)
    print("PARTE 4 · El parámetro k de RRF")
    print("=" * 70)

    # Dos listas que discrepan al máximo: el 0 es 1º para uno y último para otro.
    lista_a = [0, 1, 2]
    lista_b = [2, 1, 0]

    for k in (0, 60, 1000):
        ranking = t12.fusionar_rrf(lista_a, lista_b, k=k)
        puntajes = {}
        for lista in (lista_a, lista_b):
            for puesto, idx in enumerate(lista):
                puntajes[idx] = puntajes.get(idx, 0.0) + 1.0 / (k + puesto + 1)
        detalle = "  ".join(f"doc{i}={puntajes[i]:.6f}" for i in sorted(puntajes))
        print(f"  k={k:<5} ranking={ranking}   {detalle}")

    print("""
  ANÁLISIS:
    · k=0    -> ser 1º vale 1/1=1.0 y ser 2º vale 1/2=0.5. La diferencia entre
               puestos es brutal: un buscador entusiasta catapulta a su favorito.
               RRF se vuelve FRÁGIL.
    · k=1000 -> ser 1º vale 1/1001 y ser 2º, 1/1002. Casi idéntico. El puesto
               deja de importar y todo se decide por EN CUÁNTAS listas apareces.
               RRF degenera en un recuento de votos.
    · k=60   -> el valor del paper original: el puesto importa, pero no lo decide todo.

  LA SUTILEZA (esta sorprende a todos):
    Con k=60, doc0 (1º y 3º) puntúa 0.032266 y doc1 (2º y 2º) puntúa 0.032258.
    ¡Gana el "extremista", no el "consistente"! Porque 1/(k+r) es una curva
    CONVEXA: el promedio de los extremos supera al del medio.

    Así que RRF NO premia la consistencia. Lo que premia es ESTAR PRESENTE en
    ambas listas: un doc ausente de una lista no suma nada por ella, y eso sí
    lo hunde. Compruébalo:
""")
    # doc 7 es 2º en ambas; doc 0 es 1º en una y no aparece en la otra.
    print(f"    fusionar_rrf([0, 7], [3, 7]) = {t12.fusionar_rrf([0, 7], [3, 7])}")
    print("    -> gana el 7 (2º y 2º) sobre el 0 (1º, pero ausente de la otra lista).\n")


def main():
    print(f"\nDocumento troceado en {len(CHUNKS)} chunks:")
    for i, chunk in enumerate(CHUNKS):
        print(f"  [{i}] {chunk.splitlines()[0][:60]}")
    print()
    parte_1()
    parte_2()
    parte_3()
    parte_4()


if __name__ == "__main__":
    main()
