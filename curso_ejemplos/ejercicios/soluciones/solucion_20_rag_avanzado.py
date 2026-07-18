"""
SOLUCIÓN · Ejercicio 20 — RAG avanzado: cuándo el multi-query NO ayuda
======================================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Mostrar los TRES casos que el ejemplo del módulo no enseña, porque el ejemplo
  está montado para que el multi-query gane:

    1) El caso donde GANA de forma espectacular (la pregunta cruda no recupera
       NADA y la fusión sí): el desajuste de vocabulario.
    2) El caso donde EMPATA: sin desajuste, la fusión de N copias de una lista
       es esa lista — y has pagado N búsquedas.
    3) El caso donde la compresión AMPUTA la respuesta.

  Y de paso, la aritmética de `k` en RRF, que explica por qué 60 y no 1.

  100% offline: todo es determinista sobre datos_rag.txt. No gasta cuota.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_20_rag_avanzado.py
"""

import importlib.util
import os

# ---- Cargamos el ejemplo 20 (su nombre empieza por número: no se puede importar) ----
CARPETA_CURSO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cargar_tema20():
    ruta = os.path.join(CARPETA_CURSO, "20_rag_avanzado.py")
    spec = importlib.util.spec_from_file_location("tema20", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


t20 = cargar_tema20()
CHUNKS = t20.cargar_chunks()


# ==================================================================
# PARTE 1 · Predecir: 4 variantes, y una recuperación vacía
# ==================================================================
def parte_1() -> None:
    print("=" * 68)
    print("PARTE 1 · La pregunta del ejemplo: 4 variantes y un rescate")
    print("=" * 68)

    pregunta = "¿Cómo pido la devolución de mi dinero?"
    variantes = t20.expandir_consulta(pregunta)

    print(f"\nPregunta: {pregunta}")
    print(f"Variantes: {len(variantes)}")
    for i, v in enumerate(variantes, start=1):
        print(f"   {i}. {v}")

    solo = t20.recuperar(pregunta, CHUNKS, k=3)
    fusion = t20.rag_fusion(pregunta, CHUNKS, k=3)
    print(f"\n   UNA búsqueda (pregunta cruda) → {solo}")
    print(f"   RAG-FUSION                    → {fusion}")

    print("""
   ⭐ EL DATO INCÓMODO: la pregunta cruda recupera LISTA VACÍA.

   No es que recupere "peor": es que no recupera NADA. La razón está en
   `recuperar`, que descarta los chunks con puntaje 0:

       return [i for i in orden if puntajes[i] > 0][:k]

   La pregunta, tras quitar stopwords, se queda con los términos
   {devolución, dinero}. Y NINGÚN chunk del documento contiene esas palabras:
   el documento habla de "reembolso". Solape léxico cero → puntaje cero →
   nada supera el umbral.

   Ese `> 0` es una decisión de diseño excelente: sin él, `sorted` devolvería
   los chunks en orden arbitrario de índice y el RAG respondería con basura
   con total aplomo. Preferimos "no encontré nada" a "aquí tienes lo primero".

   Y es justo lo que RAG-Fusion arregla: la variante con el sinónimo
   ("...reembolso") SÍ casa con el chunk 3, y RRF la sube al primer puesto.
   El multi-query no mejoró un ranking mediocre: rescató un fallo TOTAL.
""")

    # El caso opuesto: la deduplicación colapsa las variantes.
    print("   --- Y ahora el reverso: expandir_consulta('reembolso') ---")
    v_corta = t20.expandir_consulta("reembolso")
    print(f"   Variantes: {len(v_corta)} → {v_corta}")
    print("""
   Solo UNA. La línea culpable es la última de expandir_consulta:

       return list(dict.fromkeys(variantes))

   Deduplica conservando el orden. Con "reembolso" (una palabra, sin
   stopwords, y que YA es la forma canónica del mapa SINONIMOS), las cuatro
   candidatas construidas son la misma cadena, y quedan en una.

   Consecuencia práctica: el multi-query se "apaga solo" cuando no tiene nada
   que aportar. Es un buen diseño... pero no te ahorra el resto del andamiaje.
""")


# ==================================================================
# PARTE 2 · El caso donde RAG-Fusion EMPATA (y aun así lo pagas)
# ==================================================================
def parte_2() -> None:
    print("=" * 68)
    print("PARTE 2 · Donde la fusión NO aporta: sin desajuste de vocabulario")
    print("=" * 68)

    casos = [
        "¿Quién controla las llaves de API?",
        "¿Qué días hay de plazo?",
        "reembolso",
    ]

    print(f"\n   {'pregunta':<40} {'1 búsqueda':<14} {'fusión':<14} veredicto")
    print("   " + "-" * 82)
    for pregunta in casos:
        solo = t20.recuperar(pregunta, CHUNKS, k=3)
        fusion = t20.rag_fusion(pregunta, CHUNKS, k=3)
        n_var = len(t20.expandir_consulta(pregunta))
        veredicto = "EMPATA" if solo == fusion else "cambia"
        print(f"   {pregunta[:38]:<40} {str(solo):<14} {str(fusion):<14} "
              f"{veredicto}  ({n_var} variantes = {n_var} búsquedas)")

    print("""
   Los tres EMPATAN. El mecanismo, caso por caso:

   · "¿Quién controla las llaves de API?" — 3 variantes, pero el documento usa
     EXACTAMENTE ese vocabulario ("llaves de API"). El mapa SINONIMOS tiene
     credenciales→llaves y contraseña→llaves, pero la pregunta ya dice
     "llaves": no hay nada que sustituir. Las 3 variantes recuperan el MISMO
     ranking [4], y RRF de tres listas idénticas devuelve esa lista.

   · "¿Qué días hay de plazo?" — igual: 3 variantes, mismo ranking [3, 5].

   · "reembolso" — 1 sola variante. La "fusión" es literalmente la búsqueda
     de siempre, con el coste de haber montado el andamiaje.

   ⭐ LA REGLA: RRF sobre N copias de la misma lista es esa lista. El
      multi-query solo paga cuando las variantes recuperan cosas DISTINTAS, y
      eso solo pasa cuando hay DESAJUSTE DE VOCABULARIO entre la pregunta y el
      corpus. Sin desajuste, multiplicas el coste por N y el resultado por 1.

   ¿CÓMO DECIDIR EN PRODUCCIÓN CUÁNDO ACTIVARLO? Tres estrategias reales,
   de menos a más lista:

     1. SIEMPRE. Simple, y para corpus pequeños con latencia holgada puede
        estar bien. Pagas N embeddings + N búsquedas en cada pregunta.

     2. EN CASCADA (la que yo defendería). Busca una vez. Si el mejor puntaje
        supera un umbral de confianza, RESPONDE YA. Si no llega —o si, como
        aquí, la lista sale VACÍA—, entonces expande y fusiona. El caso fácil
        cuesta lo de siempre; el difícil paga por serlo. Es el mismo patrón de
        la cascada de modelos del proyecto_llmops (barato primero).

     3. POR CLASIFICACIÓN. Un clasificador barato decide si la pregunta usa
        vocabulario "de usuario" o "de documento". Más preciso, pero es una
        pieza más que mantener y que se desalinea con el corpus.

   La 2 es la que casi siempre gana: usa la señal que ya tienes gratis (el
   puntaje de la primera búsqueda) en vez de inventar una pieza nueva.
""")


# ==================================================================
# PARTE 3 · La aritmética de k en RRF
# ==================================================================
def parte_3() -> None:
    print("=" * 68)
    print("PARTE 3 · Qué hace k en RRF (y por qué 60)")
    print("=" * 68)

    # El escenario donde k DECIDE el ganador, y hay que construirlo a propósito:
    #   · el chunk 0 gana UNA lista (1er puesto) y no aparece en la otra.
    #   · el chunk 1 no gana ninguna, pero está en LAS DOS (3er puesto).
    # "Ganar una vez" contra "estar siempre": eso es lo que k arbitra.
    rankings = [[0, 9, 1], [2, 8, 1]]
    print(f"\n   Rankings a fusionar: {rankings}")
    print("   · chunk 0 → 1er puesto en UNA lista, ausente en la otra.")
    print("   · chunk 1 → 3er puesto, pero en LAS DOS listas.\n")

    print(f"   {'k':<10} {'ranking fusionado':<24} {'gana':<8} aporte 1º vs 2º")
    print("   " + "-" * 70)
    for k in (0, 1, 2, 60, 10000):
        fusionado = t20.fusion_rrf(rankings, k=k)
        primero = 1 / (k + 1)
        segundo = 1 / (k + 2)
        ratio = primero / segundo
        print(f"   {k:<10} {str(fusionado):<24} {str(fusionado[0]):<8} "
              f"{primero:.6f} vs {segundo:.6f}  (×{ratio:.3f})")

    print("\n   ⭐ MIRA EL FLIP: con k=0 y k=1 gana el chunk 0 (el que ganó una")
    print("      lista). Desde k=2 en adelante gana el chunk 1 (el que está en")
    print("      las dos). El MISMO input, el MISMO algoritmo, distinto ganador.")

    print("""
   La aritmética: un chunk en el puesto p (0-indexado) aporta 1/(k+p+1).

   · k=1     → 1º vale 1/2 = 0.5000 ; 2º vale 1/3 = 0.3333. El primer puesto
               vale un 50% MÁS que el segundo. Es la DICTADURA DEL PUESTO:
               ganar una lista pesa más que aparecer en varias.

   · k=10000 → 1º vale 0.00009999 ; 2º vale 0.00009998. Indistinguibles. El
               puesto DEJA DE IMPORTAR y lo único que suma es EN CUÁNTAS
               LISTAS apareces. Esto es, literalmente, VOTAR POR MAYORÍA.

   Respuesta a la pregunta del enunciado: el extremo que se parece a votar por
   mayoría es k ALTO (k=10000), no k bajo. Es el error de intuición típico —
   un k grande suena a "más peso", y es exactamente al revés: aplana el peso
   del puesto hasta borrarlo.

   Por eso 60: suficientemente grande para que un 1º puesto casual no arrase,
   suficientemente pequeño para que el orden siga significando algo.
""")


# ==================================================================
# PARTE 4 · La compresión que amputa la respuesta
# ==================================================================
def parte_4() -> None:
    print("=" * 68)
    print("PARTE 4 · Cuando comprimir_contexto borra la respuesta")
    print("=" * 68)

    # El caso: la recuperación ACIERTA de pleno y la compresión lo borra todo.
    pregunta = "¿Dan API?"
    fusion = t20.rag_fusion(pregunta, CHUNKS, k=2)
    comprimido = t20.comprimir_contexto(CHUNKS, fusion, pregunta)

    print(f"\n   Pregunta: {pregunta}")
    print(f"   Chunks recuperados: {fusion}   ← ¡el retriever ACERTÓ!")
    print("\n   --- Contexto SIN comprimir (lo que el modelo debería ver) ---")
    for idx in fusion:
        print(f"   [{idx}] {CHUNKS[idx][:150]}")
    print(f"\n   --- Contexto COMPRIMIDO (lo que el modelo VE) ---\n   {comprimido!r}")

    terminos = {t for t in t20.tokenizar(pregunta)
                if t not in t20.STOPWORDS and len(t) > 3}
    print(f"\n   Términos que sobreviven al filtro: {terminos or '(NINGUNO — conjunto vacío)'}")
    print("""
   ⭐ ESTE ES EL FALLO, y es de los que no se ven venir: el retriever hizo su
      trabajo PERFECTAMENTE (recuperó el chunk 4, el de llaves de API) y la
      compresión devolvió CADENA VACÍA.

      "¿Dan API?" tokeniza a {dan, api}. Ambos tienen 3 caracteres. El filtro
      `len(t) > 3` los tira LOS DOS. Conjunto de términos vacío → ninguna
      frase casa → contexto de cero caracteres.

      Y el modelo, obediente, responderá algo. Sobre nada.""")

    print("""
   ⭐ EL FALLO: mira el filtro de comprimir_contexto:

       terminos = {t for t in tokenizar(pregunta)
                   if t not in STOPWORDS and len(t) > 3}

   Dos coladores en serie, y ambos pueden vaciar el conjunto:

     1. STOPWORDS se lleva "qué", "con", "se"...
     2. len(t) > 3 se lleva los términos CORTOS. Y los términos cortos son
        justamente los más técnicos y discriminantes de muchos dominios:
        IVA, DNI, SLA, API, k8s, RUC. En un corpus legal o financiero, este
        filtro tira precisamente las siglas que definen la pregunta.

   Si el conjunto queda vacío, NINGUNA frase casa y la compresión devuelve
   cadena vacía: le pasas al modelo un contexto de cero caracteres y le pides
   que responda. El modelo, obediente, alucina — y el fallo es tuyo, no suyo.

   Y hay un segundo modo de fallo, más sutil: la línea siguiente añade los
   sinónimos de la PREGUNTA, pero si la frase con la respuesta usa una palabra
   del documento que no está en el mapa, el filtro no la reconoce y la tira.
   Has recuperado el chunk correcto y luego has borrado la frase correcta.

   EL ARREGLO, y lo que cuesta:

       def comprimir_seguro(chunks, indices, pregunta, minimo=80):
           comprimido = comprimir_contexto(chunks, indices, pregunta)
           if len(comprimido) < minimo:              # la red de seguridad
               return "\\n\\n".join(chunks[i] for i in indices)
           return comprimido

   Coste: los tokens que querías ahorrar, justo en los casos donde comprimir
   era arriesgado. Es el canje correcto — amputar la respuesta cuesta
   infinitamente más que unos cientos de tokens de entrada.

   Regla general de la compresión: NUNCA debe poder devolver menos contexto
   del que el modelo necesita para negarse a responder con criterio.
""")


def main() -> None:
    parte_1()
    parte_2()
    parte_3()
    parte_4()

    print("=" * 68)
    print("CIERRE")
    print("=" * 68)
    print("""
   Las tres lecciones, en una frase cada una:

   1. El multi-query no "mejora el RAG": tapa el DESAJUSTE DE VOCABULARIO.
      Sin ese problema, es coste puro (y RRF de N listas iguales lo demuestra).

   2. El k de RRF decide si el puesto importa (k bajo) o si solo importa
      aparecer en varias listas (k alto ≈ votar por mayoría).

   3. Toda compresión de contexto puede amputar la respuesta. Ponle una red
      de seguridad, porque el modo de fallo no es "responde peor": es
      "responde con seguridad sobre un contexto vacío".

   Y la meta-lección: cada técnica de RAG avanzado ataca UN problema concreto.
   Mide cuál tienes antes de elegir cuál añades.
""")


# ============ TESTS QUE PEDÍA EL EJERCICIO ============
# Cópialos a tests/ (con un fixture que cargue el tema 20) y córrelos con
# `uv run pytest -m offline`:
#
#   def test_la_pregunta_cruda_no_recupera_nada(m20, chunks):
#       # El desajuste de vocabulario: "devolución" no está en el corpus.
#       assert m20.recuperar("¿Cómo pido la devolución de mi dinero?", chunks) == []
#
#   def test_la_fusion_rescata_ese_fallo_total(m20, chunks):
#       assert m20.rag_fusion("¿Cómo pido la devolución de mi dinero?", chunks) != []
#
#   def test_sin_desajuste_la_fusion_empata(m20, chunks):
#       q = "¿Quién controla las llaves de API?"
#       assert m20.recuperar(q, chunks, k=3) == m20.rag_fusion(q, chunks, k=3)
#
#   def test_la_deduplicacion_colapsa_las_variantes(m20):
#       assert len(m20.expandir_consulta("reembolso")) == 1
#
#   def test_k_alto_borra_el_peso_del_puesto(m20):
#       # Con k enorme, 1º y 2º aportan prácticamente lo mismo.
#       assert abs(1 / 10001 - 1 / 10002) < 1e-8


if __name__ == "__main__":
    main()
