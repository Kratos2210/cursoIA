# ADR-0002 — Implementar el re-ranker a mano en vez de usar un cross-encoder

- **Estado:** aceptado
- **Fecha:** 2026-07-09
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El TEMA 12 enseña las dos técnicas que más mejoran un RAG de producción:
búsqueda **híbrida** (BM25 + vectorial, fusionadas con RRF) y **re-ranking**.

En producción, un re-ranker es un *cross-encoder*: un modelo que lee la
pregunta y el fragmento **juntos** y devuelve un puntaje de relevancia. El
estándar es `BAAI/bge-reranker-base` vía `sentence-transformers`.

Restricciones:

- Traer `sentence-transformers` arrastra **PyTorch** (~2 GB) y descarga pesos
  del modelo la primera vez. En el Mac Intel del autor, fijar la versión de
  `torch` ya ha dado problemas en otros proyectos.
- El tema debe correr en la **CI**, sin red y sin GPU, en segundos.
- El objetivo didáctico no es *tener* un re-ranker: es **entender por qué el
  orden de los fragmentos cambia la respuesta del modelo**.

Hay una tensión de fondo: un ejemplo que el alumno no puede ejecutar no enseña
nada, y una librería que tarda 20 minutos en instalarse es un ejemplo que el
alumno no ejecuta.

## Decisión

> En `12_rag_hibrido_rerank.py` implementaremos BM25, la similitud coseno, la
> fusión RRF y el re-ranking **a mano, en Python puro**, sin dependencias.
> El ejemplo es 100% offline. Las librerías reales se nombran en los comentarios
> y en el curso HTML, pero no se instalan.

El re-ranker didáctico puntúa por **cobertura** (qué proporción de las palabras
de la pregunta aparecen en el fragmento) más un **bono de frase**.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Fórmulas a mano** | Cero dependencias; corre en la CI en milisegundos; el alumno **ve** el IDF y el `1/(k+rank)` | No es un re-ranker de verdad: no entiende semántica | ✅ **Elegida** |
| `rank_bm25` + `sentence-transformers` | Es lo real; puntajes de calidad | ~2 GB de descarga; PyTorch frágil en Mac Intel; imposible en la CI | El coste de instalación mata el ejemplo |
| Usar el LLM como re-ranker | Sin dependencias nuevas; funciona bien | Gasta cuota en cada consulta; con un plan gratuito es un 429 asegurado | Rompe la promesa de "ejemplo offline" |
| Saltarse el re-ranking | Menos código | El alumno se queda sin la técnica que más sube la precisión | No enseñar no es una opción |

## Consecuencias

**Positivas**
- El tema 12 corre **sin llave, sin red y sin cuota**. Es el ejemplo que un
  alumno puede tocar mientras espera a que se le reponga el límite de Gemini.
- `puntuar_bm25`, `similitud_coseno`, `fusionar_rrf` y `re_rankear` son funciones
  puras: 25 tests las cubren en `tests/test_offline.py`, incluyendo un test de
  regresión de `precision@1` sobre el pipeline completo.
- El alumno entiende que RRF fusiona **puestos**, no puntajes — la razón por la
  que se pueden combinar dos buscadores con escalas incomparables.

**Negativas** (importantes: hay que decirlas en clase)
- Nuestro re-ranker **es léxico**. Si la pregunta dice "coste" y el documento
  dice "precio", no encuentra nada. Un cross-encoder real sí. El ejemplo
  *muestra la mecánica del reordenamiento*, no la calidad de un re-ranker.
- Nuestro "buscador vectorial" usa vectores de **frecuencia de palabras**, no
  embeddings. Comparte la misma limitación: no captura significado. Es una
  analogía honesta de la mecánica (medir el ángulo entre dos vectores), no del
  poder de `gemini-embedding-001`.
- Un alumno podría copiar `puntuar_bm25()` a producción creyendo que es
  suficiente. Por eso el archivo termina apuntando explícitamente a
  `rank_bm25`, Chroma y `BAAI/bge-reranker`.

**Cuándo revisar esta decisión**

Cuando el curso tenga un entorno preinstalado (Codespaces, Docker, Colab) donde
el peso de PyTorch ya no lo pague el alumno. Ahí, `12_rag_hibrido_rerank.py`
pasa a ser el "cómo funciona por dentro" y se añade un `12b` con las librerías
reales, para comparar los dos rankings lado a lado.
