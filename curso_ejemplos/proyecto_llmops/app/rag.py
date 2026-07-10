"""
rag.py · RAG con pgvector + clasificación de confidencialidad
==============================================================
FINALIDAD:
  La versión de PRODUCCIÓN del `proyecto_final/rag.py`. Dos diferencias clave:

  1) VECTOR STORE PERSISTENTE: en vez de InMemoryVectorStore (que se pierde al
     reiniciar y re-vectoriza en cada arranque), usamos **pgvector** sobre
     Postgres. El índice sobrevive a reinicios; la normativa se vectoriza UNA vez.
     (Se cumplió el tercer disparador del ADR-0001: desplegamos con más de un
     proceso. El ADR-0003 explica por qué pgvector y no Chroma.)

  2) CLASIFICACIÓN DE CONFIDENCIALIDAD: cada fragmento lleva un metadato
     `confidentiality` (public | internal | restricted). Ese metadato es lo que
     alimenta el RBAC (guardrails/rbac.py): un rol bajo no recupera documentos
     restringidos, por más que sean semánticamente relevantes.

LÓGICA (paso a paso):
  - clasificar_confidencialidad(texto): heurística que etiqueta cada fragmento.
    Es una FUNCIÓN PURA → testeable sin Postgres ni API.
  - trocear_con_metadata(texto): trocea + etiqueta cada fragmento.
  - construir_retriever(): crea/conecta al vector store pgvector y devuelve el
    buscador. ⚠️ Requiere Postgres levantado (docker-compose).
  - recuperar(retriever, pregunta, rol): busca respetando el RBAC.

Degradación graceful: si pgvector no está disponible (p.ej. en un test),
`construir_retriever_memoria()` cae a InMemoryVectorStore para no bloquear.
"""
from __future__ import annotations

from langchain_core.documents import Document

from app.config import settings
from app.embeddings import crear_embeddings
# El RBAC vive en guardrails/: es gobernanza, no recuperación. Aquí solo
# etiquetamos los fragmentos; quién puede verlos se decide allí.
from guardrails.rbac import NIVELES_CONFIDENCIALIDAD, filtrar_por_rol  # noqa: F401

# Marcadores EXPLÍCITOS de un fragmento restringido.
#
# ⚠️ La primera versión de esta heurística buscaba palabras temáticas
#    ("cifrado", "personal", "auditoría"). Resultado: las 5 reglas de la
#    normativa quedaban 'restricted' y un 'analyst' —el rol por defecto— no
#    recuperaba NADA. Un clasificador que lo marca todo como secreto no protege
#    nada: rompe el producto. Ahora exigimos una marca deliberada en el texto.
_MARCADORES_RESTRINGIDOS = (
    "confidencial", "secreto", "restringido", "no divulgar",
    "clave maestra", "hsm",
)

# Un fragmento se declara público solo si lo dice. Una normativa interna, por
# defecto, es interna: ese es el nivel prudente para el resto.
_MARCADORES_PUBLICOS = ("[público]", "[public]", "uso público")


def clasificar_confidencialidad(texto: str) -> str:
    """Etiqueta un fragmento como public | internal | restricted.

    Heurística barata y determinista (sin LLM), y por tanto PURA: mismo texto →
    misma etiqueta, sin red ni cuota. Reglas, en orden:

      1) ¿lleva una marca explícita de confidencialidad? → restricted
      2) ¿se declara de uso público?                     → public
      3) en cualquier otro caso                          → internal

    El orden importa: lo restringido gana. Y el caso por defecto es 'internal',
    no 'public': ante la duda, un documento normativo no se publica.

    ⭐ En producción esto sería un clasificador entrenado o un LLM. Lo que NO
       cambia es dónde vive la decisión: en una función pura, testeable y
       auditable, separada del retriever.
    """
    t = texto.lower()
    if any(m in t for m in _MARCADORES_RESTRINGIDOS):
        return "restricted"
    if any(m in t for m in _MARCADORES_PUBLICOS):
        return "public"
    return "internal"


def trocear_con_metadata(texto: str) -> list[Document]:
    """Trocea por párrafo y etiqueta cada fragmento con su confidencialidad.

    Cada Document lleva en `metadata['confidentiality']` su nivel. El retriever
    puede entonces filtrar por rol antes de devolver resultados.
    """
    fragmentos = []
    for parrafo in texto.split("\n\n"):
        limpio = parrafo.strip()
        if not limpio:
            continue
        fragmentos.append(Document(
            page_content=limpio,
            metadata={"confidentiality": clasificar_confidencialidad(limpio)},
        ))
    return fragmentos


def leer_normativa(ruta=None, incluir_anexo: bool = True) -> str:
    """La normativa compartida con proyecto_final, más los anexos del servicio.

    El prototipo solo tenía la política pública. El servicio añade anexos
    confidenciales (claves maestras, umbrales de sanción): son ellos los que
    dan sentido al RBAC, porque un 'analyst' no debe verlos.

    Con `ruta` explícita se lee solo ese archivo: así los tests controlan
    exactamente qué entra.
    """
    if ruta is not None:
        return ruta.read_text(encoding="utf-8")

    texto = settings.ruta_normativa.read_text(encoding="utf-8")
    if incluir_anexo and settings.ruta_anexo.exists():
        texto += "\n\n" + settings.ruta_anexo.read_text(encoding="utf-8")
    return texto


def unir(docs) -> str:
    """Pega los fragmentos en un solo texto, separados por línea en blanco."""
    return "\n\n".join(d.page_content for d in docs)


def construir_retriever_pgvector(ruta=None, tabla="normativa", k=3):
    """Vector store PERSISTENTE sobre pgvector. ⚠️ Requiere Postgres levantado.

    PGVector crea la tabla y la columna de vectores automáticamente la primera
    vez. Las llamadas siguientes reutilizan el índice ya vectorizado.
    """
    from langchain_postgres import PGVector
    fragmentos = trocear_con_metadata(leer_normativa(ruta))
    vectorstore = PGVector(
        embeddings=crear_embeddings(),
        connection=settings.pg_dsn,
        collection_name=tabla,
        use_jsonb=True,
    )
    # add_documents es idempotente a nivel de contenido en la práctica del curso;
    # en producción usarías un hash por documento para evitar duplicados.
    if fragmentos:
        vectorstore.add_documents(fragmentos, ids=None)
    return vectorstore.as_retriever(search_kwargs={"k": k})


def construir_retriever_memoria(ruta=None, k=3):
    """Fallback didáctico: InMemoryVectorStore (no requiere Postgres).

    Reutiliza `proyecto_final.rag.construir_retriever()` inyectándole el store ya
    poblado: mismo código de ensamblado, distinto contenido (aquí los fragmentos
    llevan metadata de confidencialidad).
    """
    from langchain_core.vectorstores import InMemoryVectorStore
    fragmentos = trocear_con_metadata(leer_normativa(ruta))
    vs = InMemoryVectorStore.from_documents(fragmentos, embedding=crear_embeddings())
    return vs.as_retriever(search_kwargs={"k": k})


def recuperar(retriever, pregunta: str, rol: str = "analyst") -> str:
    """Los fragmentos relevantes para la pregunta, FILTRADOS por el rol del usuario.

    1) El retriever trae los k más similares (similitud semántica).
    2) filtrar_por_rol aplica la autorización (RBAC a nivel documento).
    3) Se unen en un texto para inyectar como contexto del prompt.
    """
    docs = retriever.invoke(pregunta)
    docs_permitidos = filtrar_por_rol(docs, rol)
    return unir(docs_permitidos)
