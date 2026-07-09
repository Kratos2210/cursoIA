"""
TEMA 15 · Multiagente: el patrón SUPERVISOR
==========================================================
FINALIDAD:
  Un solo agente con 10 herramientas se vuelve tonto: el prompt crece, se
  confunde y elige mal. La solución de producción es dividirlo en varios
  agentes ESPECIALISTAS y poner encima un SUPERVISOR que reparte el trabajo.

  Aquí montamos un equipo de gobierno de datos:
    · consultor  — sabe de normativa (responde qué dice la política).
    · evaluador  — sabe de calidad (puntúa una regla y la clasifica).
    · supervisor — no sabe de nada, pero sabe A QUIÉN preguntarle.

  ⭐ Este ejemplo es 100% OFFLINE por defecto: no gasta cuota.
     El grafo de LangGraph es real. Lo único simulado es el "cerebro" del
     supervisor, que aquí decide con reglas. Con GOOGLE_API_KEY, la misma
     decisión la toma un LLM con salida estructurada (ver decidir_con_llm).

LÓGICA (paso a paso):
  1) El estado lleva la pregunta, a quién le toca, y las respuestas del equipo.
  2) El nodo 'supervisor' mira la pregunta y decide el siguiente destino.
  3) Una arista CONDICIONAL enruta a 'consultor', a 'evaluador' o a FIN.
  4) Cada especialista responde y devuelve el control al supervisor.
  5) El supervisor ve que ya hay respuesta y termina.

     El bucle es la clave del patrón:

         START -> supervisor --+--> consultor --+
                     ^         |                |
                     |         +--> evaluador --+
                     |                          |
                     +--------------------------+
                     |
                     +--> END   (cuando ya no queda trabajo)

Requisitos: pip install -r curso_ejemplos/requirements.txt  (este NO llama a la API)
Ejecuta:    uv run python curso_ejemplos/15_supervisor_multiagente.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                                          # detectar si hay llave (modo LLM opcional)
from typing import Literal, TypedDict              # tipos del estado y de la decisión
from dotenv import load_dotenv                     # cargar el .env (aquí solo para el aviso)
from langgraph.graph import StateGraph, START, END  # el grafo: nodos, aristas, inicio y fin


# ============ 1) EL ESTADO: la carpeta que circula por el equipo ============
class EstadoEquipo(TypedDict):
    pregunta: str          # lo que pidió el usuario
    siguiente: str         # a quién le toca ("consultor" | "evaluador" | "FIN")
    respuesta: str         # lo que produjo el especialista
    quien_respondio: str   # para auditar qué agente hizo el trabajo


# Los destinos posibles. Escribirlos como Literal no es cosmética: si el
# supervisor devuelve "evaluadorr", el grafo falla al enrutar, y con un
# Literal el error salta antes, al validar la salida estructurada del LLM.
Destino = Literal["consultor", "evaluador", "FIN"]


# ============ 2) EL CEREBRO DEL SUPERVISOR (función pura) ============
# Separado del nodo para poder testearlo sin construir el grafo.
PALABRAS_DE_EVALUACION = ("evalúa", "evalua", "evaluar", "verifica", "verificar",
                          "puntúa", "puntua", "cumple")


def decidir(pregunta: str, ya_respondido: bool) -> Destino:
    """¿A quién le toca? La política de enrutamiento del supervisor.

    Regla 1: si un especialista YA respondió, se acabó el trabajo -> FIN.
             Sin esta regla el grafo entra en bucle infinito. Es EL error
             clásico del patrón supervisor.
    Regla 2: si piden EVALUAR o VERIFICAR una regla -> evaluador.
    Regla 3: en cualquier otro caso (una duda) -> consultor.
    """
    if ya_respondido:
        return "FIN"
    texto = pregunta.lower()
    if any(palabra in texto for palabra in PALABRAS_DE_EVALUACION):
        return "evaluador"
    return "consultor"


def decidir_con_llm(pregunta: str, ya_respondido: bool) -> Destino:
    """La misma decisión, pero tomada por un LLM. ⚠️ Gasta cuota.

    Es EXACTAMENTE lo que hace un supervisor en producción: salida estructurada
    sobre un Literal, para que el modelo solo pueda devolver un destino válido.
    """
    if ya_respondido:
        return "FIN"    # esta regla no se delega jamás: es la que corta el bucle

    from pydantic import BaseModel, Field
    from langchain_google_genai import ChatGoogleGenerativeAI

    class Decision(BaseModel):
        """A qué especialista enviar la petición del usuario."""
        destino: Destino = Field(description="consultor para dudas, evaluador para evaluar reglas")

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    decision = llm.with_structured_output(Decision).invoke(
        "Eres el supervisor de un equipo de gobierno de datos.\n"
        "· consultor: responde dudas sobre qué dice la normativa.\n"
        "· evaluador: evalúa/puntúa si una regla de calidad se cumple.\n"
        f"¿A quién le envías esto?: {pregunta}"
    )
    return decision.destino


# ============ 3) LOS NODOS ============
def supervisor(state: EstadoEquipo) -> dict:
    """No hace el trabajo: decide quién lo hace."""
    destino = decidir(state["pregunta"], ya_respondido=bool(state["respuesta"]))
    print(f"  [supervisor] -> {destino}")
    return {"siguiente": destino}


def consultor(state: EstadoEquipo) -> dict:
    """Especialista 1: responde dudas sobre la normativa.

    (Simulado. En el proyecto final, este nodo es un RAG sobre normativa.txt.)
    """
    print("  [consultor]  consultando la normativa…")
    return {
        "respuesta": ("La Regla 2 fija la retención: los registros transaccionales "
                      "se conservan un mínimo de 10 años."),
        "quien_respondio": "consultor",
    }


def evaluador(state: EstadoEquipo) -> dict:
    """Especialista 2: evalúa una regla de calidad y la clasifica.

    (Simulado. En el proyecto final, este nodo usa with_structured_output.)
    """
    print("  [evaluador]  puntuando la regla…")
    return {
        "respuesta": "cumple=True · severidad=alta · respaldada por la Regla 1 (AES-256).",
        "quien_respondio": "evaluador",
    }


# ============ 4) EL ENRUTADOR: lee la decisión y la ejecuta ============
def hacia_donde(state: EstadoEquipo) -> Destino:
    """LangGraph llama a esta función para elegir la siguiente arista.

    Devuelve una ETIQUETA; el mapa de add_conditional_edges la traduce a un nodo.
    """
    return state["siguiente"]


def construir_grafo():
    """START -> supervisor -> (consultor | evaluador) -> supervisor -> END."""
    grafo = StateGraph(EstadoEquipo)
    grafo.add_node("supervisor", supervisor)
    grafo.add_node("consultor", consultor)
    grafo.add_node("evaluador", evaluador)

    grafo.add_edge(START, "supervisor")

    # ⭐ La arista condicional: según lo que devuelva hacia_donde(), saltamos
    #    a un nodo u otro. El diccionario es el mapa etiqueta -> nodo.
    grafo.add_conditional_edges(
        "supervisor",
        hacia_donde,
        {"consultor": "consultor", "evaluador": "evaluador", "FIN": END},
    )

    # Cada especialista DEVUELVE EL CONTROL al supervisor. Eso cierra el bucle
    # y permite que, con más trabajo pendiente, el supervisor delegue otra vez.
    grafo.add_edge("consultor", "supervisor")
    grafo.add_edge("evaluador", "supervisor")

    return grafo.compile()


def responder(pregunta: str) -> EstadoEquipo:
    """Una vuelta completa del equipo, de la pregunta al resultado."""
    grafo = construir_grafo()
    return grafo.invoke({
        "pregunta": pregunta, "siguiente": "", "respuesta": "", "quien_respondio": "",
    })


def main():
    load_dotenv()
    if os.getenv("GOOGLE_API_KEY"):
        print("ℹ️  Hay GOOGLE_API_KEY, pero este ejemplo corre OFFLINE a propósito.")
        print("   Para que el supervisor decida con un LLM, cambia 'decidir' por")
        print("   'decidir_con_llm' dentro del nodo supervisor().\n")

    preguntas = [
        "¿Cuántos años se conservan los registros transaccionales?",   # -> consultor
        "Evalúa esta regla: los datos personales se cifran con AES-256.",  # -> evaluador
    ]

    for pregunta in preguntas:
        print(f"🙋 {pregunta}")
        estado = responder(pregunta)
        print(f"🤖 [{estado['quien_respondio']}] {estado['respuesta']}\n")

    print("💡 Por qué un supervisor y no un agente con 10 tools:")
    print("   · cada especialista tiene su propio prompt corto y sus propias tools,")
    print("   · se pueden probar (y desplegar) por separado,")
    print("   · añadir un 3er agente NO alarga el prompt de los otros dos.")
    print("\n💡 En LangGraph hay un atajo listo para esto:")
    print("   from langgraph_supervisor import create_supervisor")
    print("   Este ejemplo lo arma a mano para que veas el bucle por dentro.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). Espera unos minutos o usa 'gemini-2.5-flash'.")
        else:
            print(f"❌ Error inesperado: {error}")
