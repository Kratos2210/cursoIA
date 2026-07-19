"""
FRAMEWORKS · El MISMO RAG del curso, ahora en LlamaIndex
=========================================================
FINALIDAD:
  El m11/m12 te enseñaron RAG con LangChain, a mano: trocear, indexar, recuperar.
  LlamaIndex hace ESO con menos andamiaje —"los datos primero"— y es lo que verás
  en muchos repos ajenos. Este anexo vuelve EJECUTABLE el snippet que el m26 solo
  mostraba como "sabor de otra API": indexa el mismo `datos_rag.txt` y responde.

  La lección NO es "LlamaIndex es mejor", es reconocer la MISMA idea con otra piel:
  cargar -> indexar -> consultar. Cambia la ergonomía, no el concepto (m26).

  ⭐ FUERA DEL GATE OFFLINE (ver docs/adr/0006): vive en un extra opcional
     (`uv sync --extra llamaindex`) y NO se testea en la CI. Necesita una API de
     LLM con cuota (el endpoint OpenAI-compatible del .env: Groq/OpenRouter/Ollama).

Ejecuta:  uv run --extra llamaindex python frameworks/rag_llamaindex.py
"""
from __future__ import annotations

import os
from pathlib import Path

# LlamaIndex trae su propio cableado de modelos; no reusa util.crear_llm() (que
# es de LangChain). Lo apuntamos al MISMO endpoint OpenAI-compatible del .env,
# así un solo proveedor sirve para todo el curso. VERIFICA los ids en su web.
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.llms.openai_like import OpenAILike

CORPUS = Path(__file__).resolve().parent.parent / "datos_rag.txt"


def _configurar_modelos() -> None:
    """Enchufa LLM + embeddings globales de LlamaIndex (su patrón `Settings`).

    - LLM: el endpoint OpenAI-compatible del .env (LLM_BASE_URL + su API key).
    - Embeddings: fastembed LOCAL (ONNX, sin cuota) — el MISMO que usa el curso
      en el m11/proyecto final. Así el RAG no depende de que el proveedor de chat
      ofrezca embeddings (Groq no los ofrece; ver util.py).
    """
    Settings.llm = OpenAILike(
        model=os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),  # VERIFICA el id
        api_base=os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        api_key=os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY", ""),
        is_chat_model=True,
        temperature=0,
    )
    Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")


def construir_indice() -> VectorStoreIndex:
    """Cargar -> trocear -> indexar, en TRES líneas (el "menos andamiaje").

    Lo que en el m11 fueron varias piezas (loader + splitter + embeddings +
    vector store) aquí lo resuelve `from_documents`: LlamaIndex trocea e indexa
    con sus valores por defecto. Menos control, menos código.
    """
    documentos = SimpleDirectoryReader(input_files=[str(CORPUS)]).load_data()
    return VectorStoreIndex.from_documents(documentos)


def main() -> None:
    _configurar_modelos()
    indice = construir_indice()
    motor = indice.as_query_engine(similarity_top_k=3)  # recupera 3 chunks y responde

    for pregunta in ("¿Cuál es el horario de atención?",
                     "¿Atienden los sábados?",
                     "¿Dónde tiene su sede la empresa?"):
        respuesta = motor.query(pregunta)
        print(f"\n❓ {pregunta}\n💬 {respuesta}")

    # ¿La misma idea del curso? Sí: `as_query_engine` hace recuperar+prompt+LLM,
    # justo el pipeline del m11. La diferencia es cuánto ves y tocas por dentro.


if __name__ == "__main__":
    main()
