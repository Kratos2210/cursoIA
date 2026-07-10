"""
TEMA 08 · Routing (el ciclo completo de un agente, a mano)
==========================================================
FINALIDAD:
  Ver los 4 pasos que hacen funcionar una herramienta:
  (A) el humano pregunta, (B) el modelo decide usar una tool,
  (C) TÚ la ejecutas, (D) el modelo responde con el dato real.

LÓGICA (paso a paso):
  1) Damos la tool al modelo con bind_tools().
  2) invoke -> el modelo puede pedir tools (ai.tool_calls).
  3) Ejecutamos cada tool y devolvemos su resultado con ToolMessage.
  4) invoke otra vez -> ahora redacta la respuesta final.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/08_routing.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from dotenv import load_dotenv              # cargar .env
from util import mensaje_cuota, crear_llm, requiere_llm_key   # el modelo, del proveedor que diga el .env
from langchain_core.tools import tool                       # decorador de herramientas
from langchain_core.messages import HumanMessage, ToolMessage  # mensajes del humano y de la tool


@tool
def calculadora_descuentos(precio: float, porcentaje: float) -> float:
    """Calcula el precio final tras aplicar un descuento."""
    return precio - (precio * porcentaje / 100)


def main():
    # ---- 1) Preparar modelo + cinturón de herramientas --
    load_dotenv()
    # requiere_llm_key() valida la llave del proveedor ACTIVO: GOOGLE_API_KEY
    # con Gemini, GROQ_API_KEY con Groq, ninguna con Ollama.
    if (error := requiere_llm_key()):
        raise SystemExit(error)
    llm = crear_llm(temperature=0)

    herramientas = [calculadora_descuentos]
    mapa = {t.name: t for t in herramientas}   # nombre -> función (para ejecutarla luego)
    llm_tools = llm.bind_tools(herramientas)   # le entregamos el "cinturón"

    # ---- 2) (A) El humano pregunta ----------------------
    mensajes = [HumanMessage(content="¿Cuánto pago por 3500 soles con 18% de descuento?")]

    # ---- 3) (B) El modelo decide ------------------------
    ai = llm_tools.invoke(mensajes)
    mensajes.append(ai)   # guardamos su decisión en el historial

    if not ai.tool_calls:
        print("El modelo respondió directo:", ai.content)
        return

    # ---- 4) (C) Ejecutamos lo que pidió -----------------
    print("🤖 El modelo pidió herramienta(s):")
    for llamada in ai.tool_calls:
        print(f"   -> {llamada['name']} con {llamada['args']}")
        resultado = mapa[llamada["name"]].invoke(llamada["args"])
        # ToolMessage devuelve el resultado, atado por tool_call_id al pedido
        mensajes.append(ToolMessage(content=str(resultado), tool_call_id=llamada["id"]))

    # ---- 5) (D) El modelo redacta la respuesta final ----
    final = llm_tools.invoke(mensajes)
    print("\n💬 Respuesta final:", final.content)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print(mensaje_cuota())   # el mensaje depende del proveedor activo
        else:
            print(f"❌ Error inesperado: {error}")
