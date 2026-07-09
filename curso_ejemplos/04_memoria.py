"""
TEMA 04 · Memoria (que no olvide la conversación)
==========================================================
FINALIDAD:
  Hacer que el modelo "recuerde" lo dicho antes, reenviándole el
  historial de la charla en cada turno.

LÓGICA (paso a paso):
  1) El prompt reserva un hueco para el historial (MessagesPlaceholder).
  2) Guardamos la conversación en una lista de Python.
  3) En cada turno enviamos: mensaje nuevo + historial acumulado.
  4) Tras responder, agregamos el intercambio a la lista.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/04_memoria.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                                   # variables de entorno
from dotenv import load_dotenv              # cargar .env
from langchain_google_genai import ChatGoogleGenerativeAI   # modelo Gemini
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # plantilla + hueco de historial
from langchain_core.messages import HumanMessage, AIMessage  # para guardar quién dijo qué


def main():
    # ---- 1) Preparar llave y modelo ---------------------
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("❌ Falta GOOGLE_API_KEY. Copia .env.example a .env y pon tu llave.")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.5)

    # ---- 2) El prompt con hueco para el historial -------
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres un asistente amable."),
        MessagesPlaceholder("history"),   # aquí se inyecta lo ya conversado
        ("human", "{input}"),
    ])
    cadena = prompt | llm

    # ---- 3) La memoria: una simple lista ----------------
    historial = []

    def chatear(texto):
        # enviamos el texto nuevo + TODO el historial acumulado
        r = cadena.invoke({"input": texto, "history": historial})
        # guardamos el intercambio para el próximo turno
        historial.append(HumanMessage(content=texto))
        historial.append(AIMessage(content=r.content))
        return r.content

    # ---- 4) Probar que recuerda -------------------------
    print("Beto:", "Me llamo Beto y mi comida favorita es la pizza.")
    print("Bot :", chatear("Me llamo Beto y mi comida favorita es la pizza."), "\n")

    print("Beto:", "¿Recuerdas mi nombre y qué me gusta comer?")
    print("Bot :", chatear("¿Recuerdas mi nombre y qué me gusta comer?"))

    # Reto: envuelve chatear() en  while True: entrada = input("Tú: ")
    # para conversar de verdad. En el TEMA 10, LangGraph hace esto solo.


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). Espera unos minutos o usa 'gemini-2.5-flash'.")
        else:
            print(f"❌ Error inesperado: {error}")
