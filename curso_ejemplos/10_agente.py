"""
TEMA 10 · Agente con LangGraph (prebuilt)
==========================================================
FINALIDAD:
  Que LangGraph haga el ciclo del TEMA 08 automáticamente, con
  memoria y personalidad. Incluye respuesta en streaming.

LÓGICA (paso a paso):
  1) Creamos el modelo y una herramienta.
  2) create_agent une cerebro + tools + memoria.
  3) Con un thread_id, el agente recuerda la conversación.
  4) Turno 2 en streaming: la respuesta aparece token a token.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/10_agente.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from dotenv import load_dotenv              # cargar .env
from util import mensaje_cuota, crear_llm, requiere_llm_key   # el modelo, del proveedor que diga el .env
from langchain_core.tools import tool                       # decorador de herramientas
from langchain_core.messages import AIMessageChunk          # "trozo" de respuesta (para streaming)
from langchain.agents import create_agent                   # crea el agente ya armado (estándar v1)
from langgraph.checkpoint.memory import MemorySaver         # memoria del agente (en RAM)


@tool
def calculadora_descuentos(precio: float, porcentaje: float) -> float:
    """Calcula el precio final tras aplicar un descuento."""
    return precio - (precio * porcentaje / 100)


def main():
    # ---- 1) Preparar llave y modelo ---------------------
    load_dotenv()
    # requiere_llm_key() valida la llave del proveedor ACTIVO: GOOGLE_API_KEY
    # con Gemini, GROQ_API_KEY con Groq, ninguna con Ollama.
    if (error := requiere_llm_key()):
        raise SystemExit(error)
    llm = crear_llm(temperature=0)

    # ---- 2) Crear el agente -----------------------------
    memoria = MemorySaver()   # recuerda la charla (indexada por thread_id)
    agente = create_agent(
        llm,
        tools=[calculadora_descuentos],
        checkpointer=memoria,
        system_prompt="Eres un asesor de ventas claro y amable.",   # en v1 es `system_prompt` (antes `prompt`)
    )

    # El thread_id identifica la conversación (como el chat de un cliente)
    config = {"configurable": {"thread_id": "cliente_001"}}

    # ---- 3) Turno 1: usa la herramienta sola ------------
    print("=== Turno 1 ===")
    r1 = agente.invoke(
        {"messages": [("user", "Hola, ¿cuánto pago por 3500 soles con 18% de descuento?")]},
        config,
    )
    print("Bot:", r1["messages"][-1].content, "\n")

    # ---- 4) Turno 2: prueba de MEMORIA + streaming ------
    # No repetimos el precio: el agente lo recuerda del turno anterior.
    print("=== Turno 2 (streaming) ===\nBot: ", end="", flush=True)
    for chunk, meta in agente.stream(
        {"messages": [("user", "¿Y si el descuento fuera del 25%?")]},
        config,
        stream_mode="messages",   # emite trozos de texto a medida que se generan
    ):
        if isinstance(chunk, AIMessageChunk) and chunk.content:
            print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
