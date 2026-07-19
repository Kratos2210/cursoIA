# ADR-0009 — El companion de DB vectorial real usa Qdrant en Docker

- **Estado:** aceptado
- **Fecha:** 2026-07-17
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El m24 implementa **a mano** el dedup por hash y el índice **IVFFlat** para que el
alumno toque el trade-off recall↔velocidad. El propio módulo cierra diciendo que
"en producción NO escribes esto a mano: lo dan `pgvector`, **Qdrant** o Milvus", y
que el índice por defecto real suele ser **HNSW**, no IVFFlat.

Esa frase se queda sin comprobar: el alumno nunca ve la versión de producción del
ejercicio que acaba de hacer. Faltaba un companion que corra el **mismo ejercicio**
contra una DB vectorial de verdad.

Había que elegir motor. El curso ya usa **pgvector** dentro de `proyecto_llmops`
(vía `langchain-postgres`), pero allí está *integrado* en un stack grande; se
buscaba algo aislado, que se levante en un comando y deje **ver** la colección.

## Decisión

> El companion del m24 es `vectordb/qdrant_companion.py` contra **Qdrant** en
> Docker (`vectordb/docker-compose.yml`, imagen **pineada**), con un extra
> opcional `qdrant` (`qdrant-client`) y embeddings **reales** de fastembed
> (extra `emb`). **Fuera** del gate offline: necesita Docker, no se testea en la
> CI. El m24 y su ejemplo a mano **no cambian**.

El companion está escrito para que cada decisión del m24 reaparezca como
**parámetro**: el dedup por hash se convierte en un **id determinista** derivado
del contenido (upsert idempotente), el `nprobe` de IVFFlat se convierte en
`hnsw_ef`, y el coseno a mano en `Distance.COSINE`.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Qdrant en Docker** | Un comando para levantarlo; sin cuenta ni nube; dashboard web para *ver* la colección; HNSW por defecto (lo que dice el m24) | Otro contenedor | ✅ **Elegida** |
| Supabase (pgvector gestionado) | Cercano al stack habitual de Alberto | Requiere **cuenta y red**; no se puede levantar offline | Peor para un companion de curso |
| pgvector local (reusar `proyecto_llmops`) | No añade motor nuevo | Ya está enseñado ahí; el companion no aportaría un ángulo distinto | Menos didáctico |
| No hacer companion | Cero trabajo | La frase "en producción no lo escribes a mano" queda sin comprobar | No cierra el gap |

## Consecuencias

**Positivas**
- El alumno corre el **mismo ejercicio** del m24 contra una DB real y comprueba
  que sus decisiones no desaparecen: se vuelven parámetros (`hnsw_ef`, `Distance`).
- El **dedup** se entiende mejor: correr el script dos veces no duplica nada,
  porque el `id` se deriva del contenido. La idempotencia sustituye al set de hashes.
- Se puede **mirar** la colección en `localhost:6333/dashboard`.

**Negativas**
- **No está cubierto por tests** y depende de Docker + de la API de
  `qdrant-client` (se verificó contra la 1.18: `query_points`, `SearchParams`,
  `collection_exists`). La imagen va **pineada** (`v1.12.4`) porque `latest`
  rompe sin avisar.
- Suma un extra (`qdrant`) y un `docker-compose.yml` más al repo; queda trazado
  aquí junto al resto de material fuera del gate
  ([ADR-0003](0003-notebook-lora-fuera-del-gate.md),
  [ADR-0004](0004-canal-whatsapp-fuera-del-gate.md),
  [ADR-0008](0008-re-ranker-real-companion.md)).

**Cuándo revisar**

Si el curso adoptara un stack de vector DB único para todo (p. ej. pgvector en
todas partes), este companion debería migrar a ese motor para no enseñar dos.
