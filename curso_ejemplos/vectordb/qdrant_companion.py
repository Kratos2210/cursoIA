"""
PROFUNDIDAD · El m24 contra una DB vectorial DE VERDAD (Qdrant)
===============================================================
FINALIDAD:
  El m24 implementó a mano el dedup por hash y el índice IVFFlat para que TOQUES
  el trade-off recall↔velocidad. El propio módulo lo avisa: "en producción NO
  escribes esto a mano; lo dan pgvector, Qdrant o Milvus". Este companion cierra
  esa frase: el MISMO ejercicio, ahora contra un Qdrant real en Docker.

  Lo que verás, punto por punto, es que las decisiones del m24 siguen ahí — solo
  que ahora son PARÁMETROS en vez de código tuyo:

    m24 (a mano)                 Qdrant (producción)
    ------------------------     ---------------------------------------------
    dedup por hash               `id` determinista del punto → upsert idempotente
    índice IVFFlat + nprobe      HNSW + `hnsw_ef` (la misma perilla recall↔ms)
    coseno a mano                `Distance.COSINE` al crear la colección
    "vectores didácticos"        embeddings reales (fastembed, ONNX, sin cuota)

  ⭐ FUERA DEL GATE OFFLINE (ver docs/adr/0009): necesita Docker (Qdrant) y
     descarga el modelo de embeddings. NO se testea en la CI.

Levanta Qdrant:  docker compose -f vectordb/docker-compose.yml up -d
Ejecuta:         uv run --extra qdrant --extra emb python vectordb/qdrant_companion.py
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "datos_rag.txt"
COLECCION = "curso_m24"
URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


def cargar_chunks() -> list[str]:
    """Un chunk por párrafo — el mismo troceo del m11/m12."""
    return [p.strip() for p in CORPUS.read_text(encoding="utf-8").split("\n\n") if p.strip()]


def id_determinista(texto: str) -> int:
    """El dedup del m24, ahora como ID del punto.

    En el m24 guardabas un set de hashes para no indexar dos veces lo mismo. En
    Qdrant no hace falta ese set: si el `id` se DERIVA del contenido, reindexar el
    mismo chunk sobrescribe el mismo punto en vez de duplicarlo. El dedup deja de
    ser código tuyo y pasa a ser una propiedad del upsert (idempotencia).
    """
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)          # Qdrant admite ids enteros o UUID


def main() -> None:
    from fastembed import TextEmbedding
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, SearchParams, VectorParams

    chunks = cargar_chunks()

    # 1) Embeddings REALES (ONNX, local, sin cuota) — no los vectores por
    #    frecuencia de palabras del m24.
    modelo = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    vectores = [v.tolist() for v in modelo.embed(chunks)]

    cliente = QdrantClient(url=URL)

    # 2) La colección: aquí eliges la distancia (el coseno que calculaste a mano)
    #    y el tipo de índice. Qdrant usa HNSW por defecto — justo lo que dice la
    #    caja del m24 ("en producción el índice por defecto suele ser HNSW").
    if not cliente.collection_exists(COLECCION):
        cliente.create_collection(
            collection_name=COLECCION,
            vectors_config=VectorParams(size=len(vectores[0]), distance=Distance.COSINE),
        )

    # 3) Upsert idempotente: córrelo dos veces y NO se duplica nada (el dedup).
    cliente.upsert(
        collection_name=COLECCION,
        points=[
            PointStruct(id=id_determinista(c), vector=v, payload={"texto": c})
            for c, v in zip(chunks, vectores)
        ],
    )
    total = cliente.count(COLECCION, exact=True).count
    print(f"📦 Colección '{COLECCION}': {total} puntos "
          f"(corre este script 2 veces: el número NO sube — eso es el dedup).\n")

    # 4) Buscar. `hnsw_ef` es la MISMA perilla que el `nprobe` del m24: más alto,
    #    mejor recall y más lento. Se decide por consulta, no al crear el índice.
    pregunta = "¿Me devuelven la plata si no me gusta?"
    consulta = next(iter(modelo.embed([pregunta]))).tolist()

    for ef in (8, 128):
        encontrados = cliente.query_points(
            collection_name=COLECCION, query=consulta, limit=3,
            search_params=SearchParams(hnsw_ef=ef),
        ).points
        print(f"── hnsw_ef={ef} (la perilla recall↔velocidad del m24) ──")
        for punto in encontrados:
            print(f"  [{punto.score:.3f}] {punto.payload['texto'][:70]}…")
        print()


if __name__ == "__main__":
    main()
