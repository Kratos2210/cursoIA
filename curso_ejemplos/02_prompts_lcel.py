"""
TEMA 02 · Prompts + LCEL (la línea de ensamblaje)
==========================================================
FINALIDAD:
  Usar plantillas de prompt (moldes con huecos) y conectar pasos con
  el operador tubería | para formar una "cadena" (chain).

LÓGICA (paso a paso):
  1) Cargamos la llave y creamos el modelo.
  2) Definimos un PROMPT con un hueco {review}.
  3) Encadenamos:  prompt -> modelo -> parser de texto.
  4) Ejecutamos pasando solo el valor del hueco.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/02_prompts_lcel.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                                   # leer variables de entorno
from dotenv import load_dotenv              # cargar el .env
from langchain_google_genai import ChatGoogleGenerativeAI       # modelo Gemini
from langchain_core.prompts import ChatPromptTemplate           # plantillas de prompt (moldes)
from langchain_core.output_parsers import StrOutputParser       # convierte la respuesta en texto plano


def main():
    # ---- 1) Preparar llave y modelo ---------------------
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("❌ Falta GOOGLE_API_KEY. Copia .env.example a .env y pon tu llave.")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    # ---- 2) El PROMPT: un molde con un hueco {review} ---
    prompt = ChatPromptTemplate.from_template(
        "Eres analista de atención al cliente. Clasifica el sentimiento "
        "(Positivo/Negativo/Neutro) de esta reseña y responde en una frase.\n"
        "Reseña: {review}"
    )

    # ---- 3) La CADENA con LCEL --------------------------
    # El | pasa la salida de cada paso al siguiente:
    #   prompt (arma el texto) -> llm (responde) -> StrOutputParser (limpia a str)
    cadena = prompt | llm | StrOutputParser()

    # ---- 4) Ejecutar: solo pasamos el valor del hueco ---
    print("=== Análisis de la reseña ===")
    resultado = cadena.invoke({"review": "El producto llegó tarde y roto."})
    print(resultado)

    # Reto: si cambias el prompt para que también traduzca al inglés,
    # la cadena NO cambia. Ese es el poder de LCEL.


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). Espera unos minutos o usa 'gemini-2.5-flash'.")
        else:
            print(f"❌ Error inesperado: {error}")
