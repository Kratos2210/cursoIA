"""
embeddings.py · Vectorizar sin depender de ningún proveedor
============================================================
FINALIDAD:
  Convertir texto en vectores para que el RAG pueda buscar por significado.

  Aquí hay una asimetría que conviene entender: el **chat** se puede cambiar de
  proveedor con una variable de entorno (ver llm.py), pero los **embeddings**
  no. Groq, por ejemplo, no ofrece endpoint de embeddings. Y cambiar de modelo
  de embeddings no es cambiar de proveedor: invalida el índice entero, porque
  los vectores viejos y los nuevos viven en espacios distintos.

  ⭐ Por eso los calculamos SIEMPRE en local. Cero cuota, cero red (tras la
     primera descarga), y el índice de pgvector no depende de que una empresa
     mantenga vivo un endpoint.

LÓGICA:
  Un mismo modelo multilingüe, dos motores intercambiables desde el .env:

    EMBEDDINGS_PROVIDER=huggingface
        langchain_huggingface.HuggingFaceEmbeddings → sentence-transformers → PyTorch.
        Lo estándar y lo más fácil de sustituir por otro modelo del Hub.
        Coste: ~16 paquetes y un torch de varios cientos de MB.
        Instalar con:  uv sync --extra llmops --extra hf

    EMBEDDINGS_PROVIDER=fastembed   (por defecto: config.py y .env.example)
        El MISMO modelo, ejecutado en ONNX. Sin PyTorch (~70 MB).
        Es lo que instala la CI. El ADR-0002 ya rechazó arrastrar torch al
        curso por este mismo motivo.

  Ambos devuelven vectores de 384 dimensiones y respetan la interfaz Embeddings
  de LangChain (`embed_documents`, `embed_query`), así que el resto del proyecto
  no sabe cuál está usando.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings


class EmbeddingsFastEmbed:
    """Adaptador mínimo de fastembed a la interfaz Embeddings de LangChain.

    fastembed devuelve generadores de np.ndarray; LangChain espera list[list[float]].
    Traducir entre ambos es todo lo que hace esta clase.
    """

    def __init__(self, modelo: str):
        from fastembed import TextEmbedding
        self._modelo = TextEmbedding(modelo)

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._modelo.embed(textos)]

    def embed_query(self, texto: str) -> list[float]:
        # embed() siempre trabaja en lote: le pasamos uno y sacamos el primero.
        return self.embed_documents([texto])[0]


def _crear_huggingface(modelo: str):
    """HuggingFaceEmbeddings. Import diferido: torch tarda segundos en cargar.

    Ojo: falta `langchain_huggingface` (ImportError en el import) y falta
    `sentence_transformers` (ImportError en el CONSTRUCTOR) son dos fallos
    distintos. Los dos significan lo mismo para quien lo sufre, así que el
    try cubre ambos.
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=modelo)
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ImportError(
            "EMBEDDINGS_PROVIDER=huggingface necesita el extra 'hf' "
            "(langchain-huggingface + sentence-transformers + PyTorch).\n"
            "  Instálalo:  uv sync --extra llmops --extra hf\n"
            "  O cambia a: EMBEDDINGS_PROVIDER=fastembed  (mismo modelo, sin PyTorch)"
        ) from exc


def _crear_fastembed(modelo: str):
    """El mismo modelo, en ONNX, sin PyTorch."""
    try:
        return EmbeddingsFastEmbed(modelo)
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ImportError(
            "EMBEDDINGS_PROVIDER=fastembed necesita el paquete 'fastembed'.\n"
            "  Instálalo:  uv sync --extra llmops"
        ) from exc


_MOTORES = {
    "huggingface": _crear_huggingface,
    "fastembed": _crear_fastembed,
}


@lru_cache
def crear_embeddings():
    """El modelo de embeddings que dicte el .env.

    Cacheado: cargar el modelo cuesta segundos y memoria. Se hace una vez por
    proceso, no una vez por documento.

    ⚠️ La primera llamada descarga el modelo (~220 MB) a la caché local.
    """
    motor = settings.embeddings_provider.lower()
    if motor not in _MOTORES:
        raise ValueError(
            f"EMBEDDINGS_PROVIDER='{settings.embeddings_provider}' no existe. "
            f"Opciones: {', '.join(sorted(_MOTORES))}."
        )
    return _MOTORES[motor](settings.embeddings_modelo)
