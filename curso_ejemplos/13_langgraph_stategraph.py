"""
TEMA 13 · LangGraph a fondo (StateGraph desde cero)
==========================================================
FINALIDAD:
  Construir "a mano" el motor de un agente para entenderlo por dentro:
  estado, nodos, aristas y una arista CONDICIONAL que crea el ciclo.

LÓGICA (paso a paso):
  1) Definimos nodos (funciones que reciben y devuelven el estado).
  2) La arista condicional decide: ¿usar una tool o terminar?
  3) Conectamos: START -> modelo -> (¿tool?) -> tools -> modelo -> END.
  4) Compilamos con memoria y lo ejecutamos viendo cada paso.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/13_langgraph_stategraph.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from dotenv import load_dotenv              # cargar .env
from util import mensaje_cuota, crear_llm, requiere_llm_key   # el modelo, del proveedor que diga el .env
from langchain_core.tools import tool                       # decorador de herramientas
# Piezas de LangGraph para construir el grafo:
from langgraph.graph import StateGraph, START, END, MessagesState  # grafo, inicio/fin y el estado
from langgraph.prebuilt import ToolNode                     # nodo listo que ejecuta las tools
from langgraph.checkpoint.memory import MemorySaver         # memoria (checkpointer)


@tool
def calculadora_descuentos(precio: float, porcentaje: float) -> float:
    """Calcula el precio final tras aplicar un descuento."""
    return precio - (precio * porcentaje / 100)


def main():
    # ---- 1) Preparar modelo + tools ---------------------
    load_dotenv()
    # requiere_llm_key() valida la llave del proveedor ACTIVO: GOOGLE_API_KEY
    # con Gemini, GROQ_API_KEY con Groq, ninguna con Ollama.
    if (error := requiere_llm_key()):
        raise SystemExit(error)
    herramientas = [calculadora_descuentos]
    llm = crear_llm(temperature=0)
    llm_tools = llm.bind_tools(herramientas)

    # ---- 2) Los NODOS (funciones sobre el estado) -------
    # El estado (MessagesState) es, en esencia, la lista de mensajes.
    def nodo_modelo(state: MessagesState):
        # el modelo mira toda la conversación y responde (o pide una tool)
        return {"messages": [llm_tools.invoke(state["messages"])]}

    nodo_tools = ToolNode(herramientas)   # ejecuta las tools que pidió el modelo

    # ---- 3) La arista CONDICIONAL (la decisión) ---------
    def decidir(state: MessagesState):
        ultimo = state["messages"][-1]
        return "tools" if ultimo.tool_calls else END   # ¿usar tool o terminar?

    # ---- 4) Construir y conectar el grafo ---------------
    grafo = StateGraph(MessagesState)
    grafo.add_node("modelo", nodo_modelo)
    grafo.add_node("tools", nodo_tools)
    grafo.add_edge(START, "modelo")                 # empieza pensando
    grafo.add_conditional_edges("modelo", decidir)  # bifurca según la decisión
    grafo.add_edge("tools", "modelo")               # CICLO: tras la tool, vuelve a pensar
    app = grafo.compile(checkpointer=MemorySaver())

    # ---- 5) Ejecutar y ver los pasos --------------------
    config = {"configurable": {"thread_id": "demo_grafo"}}
    print("=== El agente piensa, actúa y responde ===")
    for paso in app.stream(
        {"messages": [("user", "¿Cuánto pago por 3500 soles con 18% de descuento?")]},
        config,
    ):
        for nodo, salida in paso.items():
            ultimo = salida["messages"][-1]
            if ultimo.content:
                print(f"[{nodo}] {ultimo.content}")
            elif getattr(ultimo, "tool_calls", None):
                print(f"[{nodo}] pidió tool -> {ultimo.tool_calls[0]['name']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
