"""
TEMA 13b · Human-in-the-loop: el agente pausa y pide permiso
==========================================================
FINALIDAD:
  Ver funcionando el patrón más importante de los agentes en producción:
  ante una decisión delicada, el grafo se CONGELA con interrupt(), espera
  la aprobación de un humano (pueden pasar minutos o días) y luego REANUDA
  exactamente donde quedó, gracias al checkpointer.

  ⭐ Este ejemplo es 100% OFFLINE: no usa ningún LLM ni gasta cuota.
     El grafo es real (LangGraph de verdad); solo simulamos el "hallazgo"
     para concentrarnos en la mecánica pausa -> humano -> reanudar.

LÓGICA (paso a paso):
  1) Definimos el estado: un hallazgo de calidad de datos y su severidad.
  2) Nodo "detectar": produce el hallazgo (simulado, sin API).
  3) Nodo "aprobar": si la severidad es ALTA, llama a interrupt() ->
     el grafo SE DETIENE y devuelve el control a este programa.
  4) Le preguntamos al humano por consola (tú) y reanudamos el grafo
     con Command(resume=respuesta): el nodo "aprobar" continúa desde ahí.
  5) Nodo "registrar": escribe el resultado final según la decisión.

Requisitos: pip install -r curso_ejemplos/requirements.txt   (este NO llama a la API)
Ejecuta:    uv run python curso_ejemplos/13b_human_in_the_loop.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import sys                                        # detectar si hay un humano en la consola (tty)
from typing import TypedDict                      # definir la forma del estado del grafo
from langgraph.graph import StateGraph, START, END  # construir el grafo: nodos, aristas, inicio y fin
from langgraph.checkpoint.memory import MemorySaver  # el checkpointer: sin él, interrupt() no puede reanudar
from langgraph.types import interrupt, Command   # 'interrupt': pausar y esperar; 'Command': reanudar


# ============ 1) EL ESTADO: la "carpeta" que viaja por el grafo ============
class EstadoAuditoria(TypedDict):
    hallazgo: str      # qué se encontró
    severidad: str     # "alta" | "baja"
    aprobado: bool     # la decisión (humana o automática)
    registro: str      # el resultado final que quedaría en el log


# ============ 2) LOS NODOS: cada uno recibe el estado y lo actualiza ============
def detectar(state: EstadoAuditoria):
    """Simula la detección de un problema de calidad de datos (sin API)."""
    print("  [nodo detectar]  hallazgo encontrado:", state["hallazgo"])
    return {}   # no cambia nada: el hallazgo ya venía en el estado inicial


def aprobar(state: EstadoAuditoria):
    """El nodo clave: severidad alta -> PAUSA y espera a un humano."""
    if state["severidad"] != "alta":
        print("  [nodo aprobar]   severidad baja: se aprueba solo, sin molestar a nadie")
        return {"aprobado": True}

    # ⭐ interrupt() CONGELA el grafo aquí. El diccionario que le pasamos
    #    es lo que verá el humano para decidir. La ejecución NO sigue de
    #    esta línea hasta que alguien reanude con Command(resume=...).
    decision = interrupt({
        "accion": "marcar incumplimiento regulatorio",
        "hallazgo": state["hallazgo"],
        "pregunta": "¿Apruebas registrar este incumplimiento? (si/no)",
    })
    # Cuando el grafo se reanuda, interrupt() DEVUELVE la respuesta del humano.
    return {"aprobado": str(decision).strip().lower() == "si"}


def registrar(state: EstadoAuditoria):
    """Escribe el desenlace según la decisión tomada."""
    if state["aprobado"]:
        veredicto = f"REGISTRADO: {state['hallazgo']} (aprobado)"
    else:
        veredicto = f"DESCARTADO: {state['hallazgo']} (rechazado por el humano)"
    print("  [nodo registrar]", veredicto)
    return {"registro": veredicto}


# ============ 3) ARMAR EL GRAFO ============
# Está fuera de main() para poder construirlo desde un test y ejercitar el
# ciclo pausa -> reanudar sin consola (ver tests/test_offline.py).
def construir_grafo():
    """START -> detectar -> aprobar -> registrar -> END, con checkpointer."""
    grafo = StateGraph(EstadoAuditoria)
    grafo.add_node("detectar", detectar)
    grafo.add_node("aprobar", aprobar)
    grafo.add_node("registrar", registrar)
    grafo.add_edge(START, "detectar")
    grafo.add_edge("detectar", "aprobar")
    grafo.add_edge("aprobar", "registrar")
    grafo.add_edge("registrar", END)

    # ⭐ El checkpointer es OBLIGATORIO para interrupt(): guarda el estado
    #    del grafo pausado para poder retomarlo (aquí en RAM; en producción,
    #    SqliteSaver/PostgresSaver para sobrevivir reinicios).
    return grafo.compile(checkpointer=MemorySaver())


def main():
    app = construir_grafo()
    config = {"configurable": {"thread_id": "auditoria_001"}}   # id de esta ejecución

    # ---- 4) Primera invocación: corre hasta toparse con interrupt() ----
    print("=== Corriendo el grafo (hallazgo de severidad ALTA) ===")
    resultado = app.invoke(
        {"hallazgo": "El 12% de los RUC del reporte de junio están vacíos",
         "severidad": "alta", "aprobado": False, "registro": ""},
        config,
    )

    if "__interrupt__" in resultado:
        # El grafo está PAUSADO. Esto es lo que el nodo mandó para el humano:
        peticion = resultado["__interrupt__"][0].value
        print("\n⏸️  GRAFO PAUSADO — esperando aprobación humana")
        print("   acción  :", peticion["accion"])
        print("   hallazgo:", peticion["hallazgo"])

        # Preguntar por consola; si no hay humano (ej. test automático), aprobar solo.
        if sys.stdin.isatty():
            respuesta = input(f"   {peticion['pregunta']} ")
        else:
            respuesta = "si"
            print("   (sin consola interactiva: respondo 'si' automáticamente)")

        # ---- 5) REANUDAR: el mismo invoke, pero con Command(resume=...) ----
        # El grafo despierta DENTRO del nodo 'aprobar', justo donde se pausó.
        print("\n▶️  Reanudando el grafo con la respuesta del humano…")
        resultado = app.invoke(Command(resume=respuesta), config)

    print("\n=== Resultado final ===")
    print(resultado["registro"])
    print("\n💡 Esto mismo, con un LLM decidiendo la severidad y PostgresSaver como")
    print("   checkpointer, es el nodo de aprobación del proyecto final (Módulo 18).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n(Interrumpido por el usuario)")
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
