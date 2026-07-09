# Ejercicio 12 — Predice el ranking antes de ejecutarlo

**Ejemplo base:** `12_rag_hibrido_rerank.py` · **Gasta cuota:** ❌ **no, es 100% offline**

> Este es el ejercicio que más enseña sobre RAG. Y no cuesta un solo token.

## La regla del juego

En cada parte, **escribe tu predicción en un papel antes de ejecutar nada**.
El aprendizaje ocurre en la distancia entre lo que predijiste y lo que pasó.
Si ejecutas primero, no estás aprendiendo: estás mirando.

## Contexto

`datos_rag.txt` tiene 7 fragmentos. El índice `0` es solo el título
(*"Manual de la empresa Datawith.AI"*): un **chunk de ruido** que no responde
ninguna pregunta. Los demás son párrafos con contenido.

Con la pregunta del ejemplo (*"¿Cuál es el horario de atención de soporte?"*),
los cuatro rankings coinciden en dejar el chunk 2 (Horario) en primer lugar.
Demasiado fácil. Vamos a romperlo.

## Parte 1 — Una pregunta que rompe a los buscadores

Cambia la pregunta por:

```python
pregunta = "¿Puedo pagar en cuotas un proyecto grande?"
```

**Predice, antes de ejecutar:**
1. ¿Qué chunk **debería** ganar? (léelos: son 7)
2. ¿Lo pondrá BM25 en primer lugar? ¿Y el vectorial?
3. ¿Cambiará algo el re-ranking?

**Criterio de aceptación:** ejecuta y explica el resultado. Vas a encontrarte
con que **los tres rankings coinciden… en el chunk equivocado**, y que solo el
re-ranker lo arregla. Tu trabajo es explicar *por qué* — la respuesta tiene que
ver con `proyecto` y `proyectos`.

## Parte 2 — Fabrica un fallo de BM25

Encuentra (o inventa) una pregunta que **no comparta ninguna palabra literal**
con el chunk correcto. Por ejemplo, pregunta por *"devolución del dinero"*
cuando el documento dice *"reembolso"*.

**Predice:** ¿en qué puesto quedará el chunk de reembolsos? ¿Qué chunk ganará
en su lugar?

**Criterio de aceptación:** aquí hay **tres** fallos encadenados, no uno. Encuentra
los tres:

1. Uno de **sinónimos** (por qué el "vectorial" falla igual que BM25 pese a
   llamarse vectorial — esta es la pregunta importante del ejercicio).
2. Uno de **stopwords** (mira qué chunk gana, y cuál es la única palabra que
   comparte con la pregunta).
3. Uno de **empates** (mira qué devuelve `re_rankear` y de dónde sale ese orden).

El tercero es el más peligroso de los tres. Cuando lo veas, sabrás por qué.

## Parte 3 — Mide, no opines

Escribe una función `precision_en_1(preguntas_y_chunks_correctos)` que recorra
un mini-dataset y devuelva qué fracción de las veces el pipeline deja el chunk
correcto en primer lugar.

Mide **cuatro** configuraciones: solo BM25, solo vectorial, híbrido (RRF), e
híbrido + re-ranking.

Empieza con 4 preguntas fáciles (que usen las mismas palabras que el documento).
Luego **añade las dos preguntas difíciles de las Partes 1 y 2** y vuelve a medir.

**Criterio de aceptación:** dos tablas de 4 números. Con las fáciles, las cuatro
configuraciones empatan a 100% — y ese dataset, por tanto, **no mide nada**.
Con las difíciles aparece la diferencia.

Y entonces, la pregunta incómoda: **el híbrido no le gana a sus dos componentes.**
No lo maquilles. Explica por qué. (Pista: ¿qué señal aporta el "vectorial" que
BM25 no tuviera ya?)

## Parte 4 — Rompe el RRF

En `fusionar_rrf`, cambia `k=60` por `k=0` y por `k=1000`.

**Predice** qué le pasa al ranking en cada caso, y luego compruébalo.

---

## Pistas

<details>
<summary>Pista 1 — por qué el "vectorial" de este ejemplo también falla (Parte 2)</summary>

Míralo de cerca:

```python
def puntuar_vectorial(pregunta, chunks):
    vector_pregunta = Counter(tokenizar(pregunta))
    return [similitud_coseno(vector_pregunta, Counter(tokenizar(c))) for c in chunks]
```

El "vector" de un texto es un **conteo de sus palabras**. Dos textos solo se
parecen si **comparten palabras literales**. `"devolución"` y `"reembolso"` no
comparten ninguna letra útil: su coseno es exactamente `0.0`.

Es decir: este buscador mide la misma señal que BM25 (coincidencia léxica), solo
que con otra fórmula. **No entiende significado.**

Los embeddings reales (`gemini-embedding-001`) sí: colocan "devolución" y
"reembolso" cerca en un espacio de 3072 dimensiones aprendido de millones de
textos. Ese es el salto — y es la razón de que un RAG de verdad los necesite.

El ejemplo enseña la **mecánica** (medir el ángulo entre dos vectores), no el
**poder**. Confundir las dos cosas es el error más común al aprender RAG.

</details>

<details>
<summary>Pista 2 — el esqueleto de precision@1 (Parte 3)</summary>

```python
DATASET = [
    ("¿Cuál es el horario de atención?", 2),
    ("¿Quién controla las llaves de API?", 4),
    ("¿Qué formas de pago aceptan?", 6),
    ("¿Qué recibo al terminar el proyecto?", 5),
]

def precision_en_1(chunks, ranquear) -> float:
    """ranquear: función pregunta -> lista de índices, mejor primero."""
    aciertos = sum(1 for pregunta, correcto in DATASET
                   if ranquear(pregunta)[0] == correcto)
    return aciertos / len(DATASET)

# Y ahora las cuatro configuraciones:
solo_bm25 = lambda p: ordenar(puntuar_bm25(p, chunks))
solo_vect = lambda p: ordenar(puntuar_vectorial(p, chunks))
hibrido   = lambda p: fusionar_rrf(solo_bm25(p), solo_vect(p))
completo  = lambda p: re_rankear(p, chunks, hibrido(p)[:5], top_n=3)
```

</details>

<details>
<summary>Pista 3 — qué le pasa a RRF con k=0 y k=1000 (Parte 4)</summary>

La fórmula es `1 / (k + puesto + 1)`.

- **`k=0`**: ser 1º vale `1/1 = 1.0`; ser 2º vale `1/2 = 0.5`. La diferencia
  entre el 1º y el 2º es brutal. Un solo buscador que ame mucho a un chunk lo
  catapulta a la cima, aunque el otro buscador lo odie. **RRF se vuelve frágil.**

- **`k=1000`**: ser 1º vale `1/1001`; ser 2º, `1/1002`. Casi idéntico. Los puestos
  dejan de importar y todo se decide por **en cuántas listas apareces**. RRF se
  vuelve un simple recuento de votos.

`k=60` es el valor del paper original: un punto medio donde el puesto importa
pero no lo decide todo.

**Bonus sutil:** como `1/(k+r)` es una curva **convexa**, un documento que queda
1º y 3º puntúa *un pelín más* que uno que queda 2º y 2º (`0.032266` vs `0.032258`
con k=60). RRF no premia la consistencia: premia **estar presente en ambas
listas**. Hay un test que lo demuestra en `tests/test_offline.py`
(`TestTema12Rrf`). Compruébalo tú mismo con una calculadora.

</details>

---

## Reflexión

Todo lo que has tocado aquí son **20 líneas de Python sin dependencias**. BM25,
el coseno, RRF y el re-ranking no son magia de una librería: son aritmética que
cabe en una pizarra.

Cuando en producción uses `rank_bm25`, Chroma y `BAAI/bge-reranker`, estarás
usando estas mismas ideas, mejor implementadas. Pero sabrás **qué** están
haciendo — y, sobre todo, sabrás depurarlas cuando devuelvan el chunk equivocado.

Por qué el curso lo implementa a mano en vez de instalar las librerías reales:
[`docs/adr/0002-re-ranker.md`](../docs/adr/0002-re-ranker.md).

**Solución:** [`soluciones/solucion_12_rerank.py`](soluciones/solucion_12_rerank.py)
