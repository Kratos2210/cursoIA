"""
TEMA 06 · Runnables de composición
==========================================================
FINALIDAD:
  Armar flujos que no son una línea recta: ramas en paralelo,
  funciones propias y "dejar pasar" datos. Es la base del RAG.

LÓGICA (paso a paso):
  1) Creamos dos cadenas distintas sobre el mismo texto.
  2) RunnableParallel las corre A LA VEZ y junta el resultado.
  3) RunnableLambda mete una función normal de Python en la cadena.
  4) RunnablePassthrough deja pasar la entrada sin tocarla.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/06_runnables.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from dotenv import load_dotenv              # cargar .env
from util import mensaje_cuota, crear_llm, requiere_llm_key   # el modelo, del proveedor que diga el .env
from langchain_core.prompts import ChatPromptTemplate       # plantillas de prompt
from langchain_core.output_parsers import StrOutputParser   # respuesta -> texto plano
# Los tres "conectores" de composición:
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda


def main():
    # ---- 1) Preparar llave y modelo ---------------------
    load_dotenv()
    # requiere_llm_key() valida la llave del proveedor ACTIVO: GOOGLE_API_KEY
    # con Gemini, GROQ_API_KEY con Groq, ninguna con Ollama.
    if (error := requiere_llm_key()):
        raise SystemExit(error)
    llm = crear_llm(temperature=0)

    # Dos cadenas distintas sobre el MISMO texto
    cadena_resumen = ChatPromptTemplate.from_template("Resume en 5 palabras: {texto}") | llm | StrOutputParser()
    cadena_sentimiento = ChatPromptTemplate.from_template("Sentimiento (1 palabra) de: {texto}") | llm | StrOutputParser()

    # ---- 2) RunnableParallel: las corre a la vez --------
    # Devuelve un diccionario con ambas salidas.
    analisis = RunnableParallel(resumen=cadena_resumen, sentimiento=cadena_sentimiento)
    print("=== RunnableParallel (dos ramas en paralelo) ===")
    print(analisis.invoke({"texto": "El servicio fue rapidísimo pero un poco caro."}), "\n")

    # ---- 3) RunnableLambda: función propia como eslabón --
    print("=== RunnableLambda (función propia en la cadena) ===")
    a_mayusculas = RunnableLambda(lambda x: x.upper())
    print(a_mayusculas.invoke("hola mundo"), "\n")

    # ---- 4) RunnablePassthrough: deja pasar la entrada ---
    # Muy usado en RAG: una rama busca contexto y otra conserva la pregunta.
    print("=== RunnablePassthrough (deja pasar el dato) ===")
    demo = RunnableParallel(original=RunnablePassthrough(), gritado=a_mayusculas)
    print(demo.invoke("importante"))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
