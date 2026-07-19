# vectordb/ — el m24 contra una DB vectorial de verdad (Qdrant)

El m24 implementa a mano el dedup por hash y el índice IVFFlat para que TOQUES
el trade-off recall↔velocidad, y avisa: "en producción no escribes esto a mano".
`qdrant_companion.py` cierra esa frase: el MISMO ejercicio contra un Qdrant real
en Docker. Las decisiones del m24 siguen ahí — ahora son parámetros:

| m24 (a mano) | Qdrant (producción) |
|---|---|
| dedup por hash | `id` determinista del punto → upsert idempotente |
| índice IVFFlat + nprobe | HNSW + `hnsw_ef` (la misma perilla recall↔ms) |
| coseno a mano | `Distance.COSINE` al crear la colección |
| "vectores didácticos" | embeddings reales (fastembed, ONNX, sin cuota) |

## Cómo se corre

```bash
docker compose -f vectordb/docker-compose.yml up -d       # levanta Qdrant
uv run --extra qdrant --extra emb python vectordb/qdrant_companion.py
```

Necesita Docker; no gasta cuota de API (los embeddings son locales).

## Por qué está fuera del gate offline

Decidido en [ADR-0009](../docs/adr/0009-vector-db-real-companion.md): requiere
Docker y descarga el modelo de embeddings, así que no corre en la CI. La versión
testeada y sin dependencias es `24_vector_db.py`.
