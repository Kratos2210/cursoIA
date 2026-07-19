"""
embeddings.py · Los vectores del caché semántico (locales, cero cuota)
=======================================================================
FINALIDAD:
  El caché semántico necesita convertir una petición en un vector para comparar
  significados. Aquí vive esa pieza.

  ⭐ POR QUÉ UN EMBEDDER PROPIO Y NO UNA API. El caché no puede costar más que lo
     que ahorra: vectorizar cada pregunta con una API de embeddings pagaría una
     llamada para evitar otra. Por eso se calcula EN LOCAL.

  ⭐ EL EMBEDDER DE DEMO ES UN STAND-IN DIDÁCTICO. `EmbeddingsBolsa` es una bolsa
     de palabras con hashing (bag-of-words): cero dependencias, determinista,
     suficiente para demostrar el mecanismo del caché (dos frases con las mismas
     palabras clave caen cerca). NO capta sinónimos ("aros"≈"aretes"): para eso,
     en producción, se enchufa un modelo real de embeddings (m12) — la interfaz
     `embed_query`/`embed_documents` es la misma, así el caché no se entera.
     Ver docs/adr/0005-escalabilidad-embeddings-vector-db.md.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(texto: str) -> list[str]:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                         if unicodedata.category(c) != "Mn")
    return _TOKEN.findall(sin_tildes)


class EmbeddingsBolsa:
    """Bolsa de palabras con hashing → vector de frecuencias. Determinista, PURA.

    Cada token cae en un bucket fijo (hash estable con blake2b, no el `hash()` de
    Python que se aleatoriza por proceso). El vector es el conteo por bucket. Dos
    frases con el mismo vocabulario apuntan en la misma dirección (coseno alto).
    """

    def __init__(self, dimensiones: int = 128):
        self.dimensiones = dimensiones

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest()
        return int(digest, 16) % self.dimensiones

    def embed_query(self, texto: str) -> list[float]:
        vector = [0.0] * self.dimensiones
        for token in _tokens(texto):
            vector[self._bucket(token)] += 1.0
        return vector

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in textos]


def crear_embeddings():
    """El embedder del caché. Hoy el local de demo; en producción, uno real (m12)."""
    return EmbeddingsBolsa()
