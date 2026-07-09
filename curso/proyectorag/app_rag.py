import os
import pypdf
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# [PASO 1] Cargar la API Key de Google de forma segura
load_dotenv()

# [PASO 2] Configurar el Traductor Matemático de Google
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

# [PASO 3] EXTRACCIÓN Y FRACCIONAMIENTO CON PYTHON PURO
carpeta_documentos = "docs"

# CLAVE DE LA SOLUCIÓN: Creamos la lista vacía aquí para que Python sepa qué es
fragmentos_finales = []

print("=== [1] Leyendo y fraccionando PDFs de la carpeta docs ===")

if not os.path.exists(carpeta_documentos):
    print(f"❌ ERROR: No encuentro la carpeta '{carpeta_documentos}'")
else:
    for nombre_archivo in os.listdir(carpeta_documentos):
        if nombre_archivo.endswith(".pdf"):
            ruta_completa = os.path.join(carpeta_documentos, nombre_archivo)
            print(f"📄 Procesando archivo: {nombre_archivo}")
            
            # Abrimos el PDF físico
            lector_pdf = pypdf.PdfReader(ruta_completa)
            
            # Recorremos cada página del documento
            for indice_pag, pagina in enumerate(lector_pdf.pages):
                texto_completo_pagina = pagina.extract_text()

                # [MEJORA 4] Si la página está vacía (p. ej. escaneada sin OCR),
                # extract_text() puede devolver None o "". La saltamos para no
                # crear fragmentos basura ni gastar cupo de embeddings en vacío.
                if not texto_completo_pagina:
                    continue

                # Configuración de nuestro fraccionador manual
                tamano_bloque = 500  # Máximo 500 caracteres por pedazo
                solapamiento = 50   # 50 caracteres de carrerilla para el contexto

                # [MEJORA 3] Guarda contra bucle infinito: si el solapamiento
                # fuese >= al tamaño del bloque, el puntero nunca avanzaría y el
                # while se colgaría para siempre. Este paso siempre debe ser > 0.
                paso_avance = tamano_bloque - solapamiento
                if paso_avance <= 0:
                    raise ValueError("El solapamiento debe ser menor que el tamaño del bloque")

                inicio = 0
                while inicio < len(texto_completo_pagina):
                    fin = inicio + tamano_bloque
                    trozo_texto = texto_completo_pagina[inicio:fin]
                    
                    # Empacamos el fragmento como un Documento de LangChain
                    objeto_documento = Document(
                        page_content=trozo_texto,
                        metadata={
                            "fuente": nombre_archivo, 
                            "pagina": indice_pag + 1
                        }
                    )
                    
                    # Ahora sí, guardamos el fragmento en la lista existente
                    fragmentos_finales.append(objeto_documento)
                    
                    # Avanzamos el puntero calculando el solapamiento
                    inicio += paso_avance

print(f"\n✂️ ¡Éxito total! Se crearon {len(fragmentos_finales)} fragmentos usando Python puro.")

# [PASO 4] Guardar en el Archivador Inteligente (RAM)
vectorstore = InMemoryVectorStore.from_documents(fragmentos_finales, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# [PASO 5] Definir el Prompt del Asistente Corporativo
template = """Actúa como un asistente de soporte experto para Datawith.AI. 
Responde la consulta del usuario basándote únicamente en el contexto provisto.
Si no sabes la respuesta o si no está explícitamente en el contexto, di amablemente que no posees esa información.

Contexto extraído de los PDFs:
{context}

Pregunta del usuario: {question}
Respuesta Institucional:"""

prompt = ChatPromptTemplate.from_template(template)
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.1)

# [MEJORA 1] Formateo del contexto.
# El retriever devuelve una LISTA de objetos Document. Si esa lista entra tal
# cual al prompt, Gemini recibe texto ruidoso como:
#   [Document(metadata={...}, page_content='...'), Document(...)]
# Con esta función convertimos esa lista en texto plano y limpio: solo el
# contenido de cada fragmento, separado por líneas en blanco. Así el modelo
# lee el contexto sin metadatos que lo distraigan.
def formatear_documentos(docs):
    return "\n\n".join(documento.page_content for documento in docs)

# [PASO 6] Línea de Ensamblaje LCEL
# Nota el nuevo paso "retriever | formatear_documentos": primero recuperamos los
# fragmentos más parecidos y luego los convertimos a texto limpio antes del prompt.
chain = (
    {
        "context": retriever | formatear_documentos,
        "question": RunnablePassthrough()
    }
    | prompt
    | model
    | StrOutputParser()
)

# [MEJORA 2] Helper con manejo del error de cupo (429 RESOURCE_EXHAUSTED).
# El plan gratuito de Gemini tiene un cupo diario de peticiones. Si se agota,
# la API lanza un 429. En vez de que el script "explote" con un traceback feo,
# lo capturamos y mostramos un mensaje claro para seguir estudiando con calma.
def preguntar_al_rag(pregunta):
    print(f"\n🙋‍♂️ Consulta: {pregunta}")
    try:
        respuesta = chain.invoke(pregunta)
        print(f"🤖 Gemini dice: {respuesta}")
    except Exception as error:
        # Detectamos el caso típico de cupo agotado para dar una pista útil.
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cupo de la API agotado (429). Espera unos segundos/minutos "
                  "o revisa tu límite diario en https://ai.dev/rate-limit")
        else:
            print(f"❌ Error inesperado al consultar: {error}")

# === [PASO 7] Ejecución de tus consultas reales ===
print("\n=== [2] Iniciando Consultas al RAG ===")

preguntar_al_rag("¿Quién mantiene el control de las llaves de API y credenciales del cliente?")
preguntar_al_rag("¿Qué entregables recibo al finalizar el proyecto?")