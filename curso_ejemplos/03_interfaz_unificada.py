"""
TEMA 03 · La interfaz unificada: invoke / batch / stream
==========================================================
FINALIDAD:
  Ver las 3 formas de ejecutar la MISMA cadena, sin reescribirla.

LÓGICA (paso a paso):
  1) Creamos una cadena normal (prompt -> modelo -> texto).
  2) invoke  -> una entrada, una respuesta.
  3) batch   -> muchas entradas a la vez (en paralelo, más rápido).
  4) stream  -> la respuesta llega por trozos (token a token).

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/03_interfaz_unificada.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from dotenv import load_dotenv              # cargar .env
from util import mensaje_cuota, crear_llm, requiere_llm_key   # el modelo, del proveedor que diga el .env
from langchain_core.prompts import ChatPromptTemplate       # plantillas de prompt
from langchain_core.output_parsers import StrOutputParser   # respuesta -> texto plano


def main():
    # ---- 1) Preparar llave, modelo y cadena -------------
    load_dotenv()
    # requiere_llm_key() valida la llave del proveedor ACTIVO: GOOGLE_API_KEY
    # con Gemini, GROQ_API_KEY con Groq, ninguna con Ollama.
    if (error := requiere_llm_key()):
        raise SystemExit(error)
    llm = crear_llm(temperature=0.3)
    prompt = ChatPromptTemplate.from_template(
        "Clasifica el sentimiento de esta reseña en una sola palabra.\nReseña: {review}"
    )
    cadena = prompt | llm | StrOutputParser()

    # ---- 2) invoke: UNA entrada -> UNA respuesta --------
    print("=== 1) invoke (una) ===")
    print(cadena.invoke({"review": "Muy buena atención."}), "\n")

    # ---- 3) batch: MUCHAS a la vez (en paralelo) --------
    print("=== 2) batch (muchas en paralelo) ===")
    reseñas = [
        {"review": "Me encantó, súper rápido."},
        {"review": "Pésima atención al cliente."},
        {"review": "Cumple, nada especial."},
    ]
    for r in cadena.batch(reseñas):
        print("-", r)
    print()

    # ---- 4) stream: la respuesta llega por trozos -------
    print("=== 3) stream (token a token) ===")
    prompt_largo = ChatPromptTemplate.from_template("Escribe 3 tips para {tema}.")
    cadena_larga = prompt_largo | llm | StrOutputParser()
    for trozo in cadena_larga.stream({"tema": "atender clientes por WhatsApp"}):
        print(trozo, end="", flush=True)   # end="" para que se vea continuo
    print()

    # Nota: cada verbo tiene su gemelo async con 'a' delante:
    # ainvoke, abatch, astream (lo verás en el TEMA 09).


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
