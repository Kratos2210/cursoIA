"""
TEMA 01 · Tu primer modelo
==========================================================
FINALIDAD:
  Aprender a "hablarle" a un modelo de IA (Gemini) y entender los
  tipos de mensaje (System / Human) que forman una conversación.

LÓGICA (paso a paso):
  1) Cargamos la llave secreta desde .env y verificamos que exista.
  2) Creamos el modelo (el "cerebro").
  3) Le mandamos un mensaje simple con .invoke() y leemos .content.
  4) Repetimos, pero ahora con un SystemMessage que le da personalidad.

Requisitos: pip install -r curso_ejemplos/requirements.txt
            y un archivo .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/01_primer_modelo.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                                   # 'os': leer variables de entorno (tu llave API)
from dotenv import load_dotenv              # 'dotenv': volcar el archivo .env a esas variables
from langchain_google_genai import ChatGoogleGenerativeAI  # el modelo Gemini (el cerebro)
from langchain_core.messages import SystemMessage, HumanMessage  # los "roles" de la conversación


def main():
    # ---- 1) Preparar la llave (robustez) ----------------
    load_dotenv()  # busca .env en el proyecto y carga sus variables
    if not os.getenv("GOOGLE_API_KEY"):
        # Fallar temprano con un mensaje claro es mejor que un error críptico después.
        raise SystemExit("❌ Falta GOOGLE_API_KEY. Copia .env.example a .env y pon tu llave.")

    # ---- 2) Crear el modelo -----------------------------
    # temperature=0 -> respuestas precisas y estables (poco creativas).
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    # ---- 3) Llamada simple: una pregunta suelta ---------
    # .invoke() recibe una LISTA de mensajes y devuelve un objeto con .content
    print("=== Ejemplo A: pregunta simple ===")
    respuesta = llm.invoke([HumanMessage(content="Explica qué es un LLM en una frase.")])
    print(respuesta.content, "\n")

    # ---- 4) Con SystemMessage: le damos personalidad ----
    # SystemMessage = las "reglas del juego" (rol, tono, estilo).
    # HumanMessage  = lo que dice el usuario.
    print("=== Ejemplo B: con personalidad (SystemMessage) ===")
    mensajes = [
        SystemMessage(content="Eres un tutor paciente. Responde con un ejemplo simple."),
        HumanMessage(content="¿Qué es un vector?"),
    ]
    print(llm.invoke(mensajes).content)

    # Idea clave: cada .invoke() es independiente; el modelo NO recuerda
    # nada entre llamadas. Eso se resuelve en el TEMA 04 (memoria).


# ---- Arranque robusto: capturamos errores comunes -------
if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). Espera unos minutos o usa 'gemini-2.5-flash'.")
        else:
            print(f"❌ Error inesperado: {error}")
