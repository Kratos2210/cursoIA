"""
rag.py · Recuperación sobre la normativa (el "libro abierto" del agente)
=========================================================================
FINALIDAD:
  Convertir normativa.txt en algo que se pueda BUSCAR, y entregar al agente
  solo los fragmentos relevantes a cada pregunta.

LÓGICA (paso a paso):
  1) trocear(texto)        -> parte la normativa en fragmentos (uno por regla).
  2) construir_retriever() -> vectoriza esos fragmentos y devuelve el buscador.
  3) contexto(retriever, pregunta) -> los fragmentos relevantes, ya en texto.

  Fíjate en el reparto: (1) y (3) son funciones PURAS o casi — se testean
  gratis. Solo (2) toca la API. Esa separación es lo que hace testeable un RAG.
"""

from langchain_core.documents import Document

import config


def trocear(texto: str) -> list[Document]:
    """Parte la normativa en fragmentos, uno por párrafo (= una regla).

    Un párrafo por regla es un troceado perfecto para este documento: cada
    fragmento es autocontenido. En un PDF de 200 páginas usarías un
    RecursiveCharacterTextSplitter con solapamiento (ver TEMA 12 del curso).
    """
    return [Document(page_content=p.strip()) for p in texto.split("\n\n") if p.strip()]


def leer_normativa(ruta=None) -> str:
    """Lee el archivo de normativa. Por defecto, el del proyecto."""
    ruta = ruta or config.RUTA_NORMATIVA
    return ruta.read_text(encoding="utf-8")


def construir_retriever(ruta=None, *, vector_store=None, k=None):
    """Vectoriza la normativa y devuelve el buscador. ⚠️ Llama a la API.

    InMemoryVectorStore guarda los vectores en RAM: perfecto para un curso,
    inútil tras reiniciar. En producción: Chroma, Qdrant o pgvector.

    Parámetros solo-por-nombre (los usa proyecto_llmops/):
      vector_store: un store YA poblado (p.ej. pgvector). Si viene, no
                    vectorizamos nada aquí: solo pedimos su retriever.
      k           : cuántos fragmentos devolver. None = el del config.

    Con ambos en None el comportamiento es el de siempre. Ese default es lo que
    permite cambiar de base de datos vectorial sin tocar el resto del proyecto
    (es la promesa que hace el ADR-0001).
    """
    k = k or config.FRAGMENTOS_POR_CONSULTA
    if vector_store is None:
        fragmentos = trocear(leer_normativa(ruta))
        from langchain_core.vectorstores import InMemoryVectorStore
        vector_store = InMemoryVectorStore.from_documents(
            fragmentos, embedding=config.crear_embeddings()
        )
    return vector_store.as_retriever(search_kwargs={"k": k})


def unir(docs) -> str:
    """Pega los fragmentos en un solo texto, separados por línea en blanco."""
    return "\n\n".join(d.page_content for d in docs)


def contexto(retriever, pregunta: str) -> str:
    """Los fragmentos de normativa más relevantes para la pregunta, ya en texto.

    Es lo que se inyecta en el prompt como "libro abierto".
    """
    return unir(retriever.invoke(pregunta))
