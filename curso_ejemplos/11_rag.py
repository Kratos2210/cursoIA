"""
TEMA 11 · RAG (responder desde TUS documentos)
==========================================================
FINALIDAD:
  Que el modelo responda usando el contenido de un documento tuyo
  (aquí, datos_rag.txt), sin inventar. Es un "examen a libro abierto".

LÓGICA (paso a paso):
  1) Leemos el .txt y lo partimos en fragmentos (por párrafo).
  2) Convertimos cada fragmento en números (embeddings) y los guardamos.
  3) El retriever busca los fragmentos más parecidos a la pregunta.
  4) La cadena RAG mete esos fragmentos como contexto y el modelo responde.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/11_rag.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                                   # variables de entorno + rutas de archivo
from dotenv import load_dotenv              # cargar .env
from langchain_core.documents import Document               # 'Document': envoltura de cada fragmento
from langchain_core.prompts import ChatPromptTemplate       # plantilla del prompt
from langchain_core.output_parsers import StrOutputParser   # respuesta -> texto plano
from langchain_core.runnables import RunnablePassthrough    # deja pasar la pregunta tal cual
from langchain_core.vectorstores import InMemoryVectorStore # base de datos vectorial en memoria (RAM)
# Modelo de chat + modelo de embeddings (traductor de texto a números):
from util import mensaje_cuota, crear_embeddings, crear_llm, requiere_llm_key


# ============ PIEZAS PURAS (sin LLM) ============
# Estas dos funciones viven FUERA de main() por dos motivos:
#   a) son las que de verdad definen el RAG (cómo troceas y cómo pegas), y
#   b) al estar sueltas se pueden TESTEAR sin gastar cuota (ver tests/test_offline.py).
def trocear(texto: str) -> list[Document]:
    """Parte el texto en fragmentos por párrafo y los envuelve en Document.

    Cada PÁRRAFO (separado por línea en blanco) es un fragmento.
    """
    return [Document(page_content=p.strip()) for p in texto.split("\n\n") if p.strip()]


def unir(docs) -> str:
    """El retriever devuelve una lista de Documentos; la volvemos texto limpio."""
    return "\n\n".join(d.page_content for d in docs)


def main():
    # ---- 1) Preparar llave ------------------------------
    load_dotenv()
    if (error := requiere_llm_key()):
        raise SystemExit(error)

    # ---- 2) Leer el documento y trocearlo ---------------
    ruta = os.path.join(os.path.dirname(__file__), "datos_rag.txt")
    if not os.path.exists(ruta):
        raise SystemExit(f"❌ No encuentro el documento: {ruta}")
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()
    fragmentos = trocear(texto)
    print(f"📄 Se crearon {len(fragmentos)} fragmentos.\n")

    # ---- 3) Vectorizar y guardar ------------------------
    # embeddings = traductor de texto a números; el vector store los guarda.
    #
    # ⚠️ Aquí el chat y los embeddings NO van juntos. Groq no ofrece embeddings,
    #    así que con LLM_PROVIDER=groq esta línea sigue llamando a Gemini. Si no
    #    quieres gastar esa cuota: `uv sync --extra emb` y EMBEDDINGS_PROVIDER=fastembed
    #    (los calcula en tu máquina). Ojo: cambiar de modelo de embeddings
    #    invalida cualquier índice ya construido — hay que reindexar.
    embeddings = crear_embeddings()
    vs = InMemoryVectorStore.from_documents(fragmentos, embedding=embeddings)

    # ---- 4) El retriever: trae los 2 más parecidos ------
    retriever = vs.as_retriever(search_kwargs={"k": 2})

    # ---- 5) Prompt con REGLA ANTI-ALUCINACIÓN -----------
    prompt = ChatPromptTemplate.from_template(
        "Responde SOLO con el contexto. Si la respuesta no está, dilo amablemente.\n"
        "Contexto:\n{context}\n\nPregunta: {question}"
    )
    llm = crear_llm(temperature=0)

    # ---- 6) La cadena RAG (LCEL) ------------------------
    # "context" se llena buscando en los documentos; "question" pasa tal cual.
    rag = (
        {"context": retriever | unir, "question": RunnablePassthrough()}
        | prompt | llm | StrOutputParser()
    )

    # ---- 7) Preguntar -----------------------------------
    for pregunta in [
        "¿Cuál es el horario de atención?",
        "¿Quién controla las llaves de API?",
        "¿Aceptan pago con tarjeta Visa?",   # NO está en el doc -> debe admitirlo
    ]:
        print("🙋", pregunta)
        print("🤖", rag.invoke(pregunta), "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
