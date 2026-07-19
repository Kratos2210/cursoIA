# ADR-0005 — Cómo escala: de solape de términos a embeddings + vector DB

- **Estado:** aceptado (con disparadores de revisión)
- **Fecha:** 2026-07-11
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

La búsqueda de hoy (`app/search.py`) rankea por **solape de términos**: entre los
productos que pasan los filtros duros, sube el que contiene el color pedido y, a
igualdad, el más barato. El caché semántico usa un embedder local de **bolsa de
palabras con hashing** (`app/embeddings.py`). Ambos son didácticos a propósito:
cero dependencias, deterministas, suficientes para un catálogo de decenas o
cientos de productos.

No captan **sinónimos** ni **semántica**: "aros" ≈ "aretes" solo funciona porque
lo resolvemos con una lista de sinónimos en `intent.py`; "algo elegante para una
boda" no encuentra nada aunque el catálogo tenga la pieza perfecta.

La pregunta no es "¿está mal?", sino "¿cuándo deja de bastar, y qué se cambia?".

## Decisión

> Mantener el solape de términos y el embedder de bolsa **mientras el catálogo y
> el tráfico sean pequeños**, con las costuras puestas para escalar sin reescribir:
>
> - El ranking vive AISLADO en la función `afinidad` de `app/search.py`.
>   Sustituirla por **embeddings + re-ranking (m12)** no toca los filtros duros
>   ni el pipeline.
> - El caché depende de la INTERFAZ `embed_query`/`embed_documents`
>   (`app/embeddings.py`), no de una implementación. Cambiar a un modelo real de
>   embeddings es cambiar `crear_embeddings()`.
> - El backend del caché es un `Protocol` (`cache/cache_backends.py`): la
>   búsqueda lineal en memoria/Redis se cambia por un índice vectorial
>   (RediSearch/HNSW) o **pgvector (m24)** implementando el mismo contrato.

## Disparadores de revisión (cuándo dar el salto)

1. **El catálogo pasa de ~unos miles de productos** → la búsqueda por filtros +
   solape empieza a dejar fuera piezas que un usuario esperaría. Cambiar a
   embeddings + búsqueda híbrida + RRF (m12).
2. **Los usuarios buscan por descripción, no por categoría** ("algo para una
   boda", "un regalo económico y elegante") → embeddings de verdad; el solape de
   términos no entiende intención.
3. **El caché supera ~decenas de miles de entradas** → la búsqueda lineal deja de
   ser ruido frente a la latencia del LLM. Índice vectorial en Redis o pgvector.
4. **Búsqueda por foto** ("quiero algo como esto") → visión (m22) + embeddings
   multimodales.

## Consecuencias

- Hoy el proyecto corre offline, sin GPU, sin servicios: se puede aprender y
  testear entero en una laptop.
- El día que el volumen lo exija, el cambio es **localizado** (tres costuras), no
  una reescritura. Esa es la diferencia entre un prototipo y un prototipo que
  escala: no que ya escale, sino que sepa DÓNDE va a doler y lo tenga aislado.
- **Coste asumido:** hasta que se dé un disparador, el asistente no entiende
  sinónimos fuera de la lista de `intent.py`. Es un límite conocido y documentado,
  no una sorpresa de producción.
