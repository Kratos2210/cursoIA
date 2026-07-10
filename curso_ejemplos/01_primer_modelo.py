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
from dotenv import load_dotenv              # 'dotenv': volcar el archivo .env a las variables de entorno
from util import mensaje_cuota, crear_llm, requiere_llm_key   # el modelo, del proveedor que diga el .env
from langchain_core.messages import SystemMessage, HumanMessage  # los "roles" de la conversación


def main():
    # ---- 1) Preparar la llave (robustez) ----------------
    load_dotenv()  # busca .env en el proyecto y carga sus variables
    # requiere_llm_key() valida la llave del proveedor ACTIVO: GOOGLE_API_KEY
    # con Gemini, GROQ_API_KEY con Groq, ninguna con Ollama.
    if (error := requiere_llm_key()):
        raise SystemExit(error)

    # ---- 2) Crear el modelo -----------------------------
    # temperature=0 -> respuestas precisas y estables (poco creativas).
    llm = crear_llm(temperature=0)

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
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
