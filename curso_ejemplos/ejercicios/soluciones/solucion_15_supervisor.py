"""
SOLUCIÓN · Ejercicio 15 — Un tercer especialista, y predice a quién enruta
==========================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Añadir el especialista `redactor` al equipo del TEMA 15 y mostrar que el
  enrutado de una petición ambigua ("redacta un informe que evalúe…") no lo
  decide "qué pesa más", sino el ORDEN de los `if` en decidir().

  100% offline: el grafo de LangGraph es real; el cerebro del supervisor decide
  con reglas, así que su salida es predecible al detalle.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_15_supervisor.py
"""

from typing import Literal, TypedDict

from langgraph.graph import StateGraph, START, END


# ============ 1) EL ESTADO ============
class EstadoEquipo(TypedDict):
    pregunta: str
    siguiente: str
    respuesta: str
    quien_respondio: str


# ⭐ El Literal ahora incluye "redactor". No es cosmética: en el modo LLM, la
#    salida estructurada rechaza cualquier destino que no esté aquí.
Destino = Literal["consultor", "evaluador", "redactor", "FIN"]


# ============ 2) EL CEREBRO DEL SUPERVISOR (función pura) ============
PALABRAS_DE_EVALUACION = ("evalúa", "evalua", "evaluar", "verifica", "verificar",
                          "puntúa", "puntua", "cumple")
# ⭐ NUEVO: las palabras que mandan una petición al redactor.
PALABRAS_DE_REDACCION = ("redacta", "redactar", "informe", "comunicado",
                         "documenta", "documentar", "notifica")


def decidir(pregunta: str, ya_respondido: bool) -> Destino:
    """¿A quién le toca? La política de enrutado del supervisor, con 3 destinos.

    Regla 1: si un especialista YA respondió -> FIN. Corta el bucle infinito.
    Regla 2: si piden REDACTAR -> redactor.
    Regla 3: si piden EVALUAR/VERIFICAR -> evaluador.
    Regla 4: en cualquier otro caso (una duda) -> consultor.

    ⭐ EL DESEMPATE VIVE EN EL ORDEN DE LOS `if`. Una petición que menciona
       redacción Y evaluación ("redacta un informe que evalúe la regla 3") cae en
       el PRIMER `if` que casa: aquí, el de redacción. Si intercambiaras los dos
       bloques, esa misma petición iría al evaluador. No hay una respuesta
       "correcta" universal: hay la que tu orden de reglas decide.
    """
    if ya_respondido:
        return "FIN"
    texto = pregunta.lower()
    if any(palabra in texto for palabra in PALABRAS_DE_REDACCION):
        return "redactor"
    if any(palabra in texto for palabra in PALABRAS_DE_EVALUACION):
        return "evaluador"
    return "consultor"


# ============ 3) LOS NODOS ============
def supervisor(state: EstadoEquipo) -> dict:
    """No hace el trabajo: decide quién lo hace."""
    destino = decidir(state["pregunta"], ya_respondido=bool(state["respuesta"]))
    print(f"  [supervisor] -> {destino}")
    return {"siguiente": destino}


def consultor(state: EstadoEquipo) -> dict:
    """Especialista 1: responde dudas sobre la normativa. (Simulado.)"""
    print("  [consultor]  consultando la normativa…")
    return {
        "respuesta": ("La Regla 2 fija la retención: los registros transaccionales "
                      "se conservan un mínimo de 10 años."),
        "quien_respondio": "consultor",
    }


def evaluador(state: EstadoEquipo) -> dict:
    """Especialista 2: evalúa una regla de calidad y la clasifica. (Simulado.)"""
    print("  [evaluador]  puntuando la regla…")
    return {
        "respuesta": "cumple=True · severidad=alta · respaldada por la Regla 1 (AES-256).",
        "quien_respondio": "evaluador",
    }


def redactor(state: EstadoEquipo) -> dict:
    """⭐ ESPECIALISTA NUEVO: redacta el comunicado de un hallazgo. (Simulado.)

    En el proyecto final, este nodo llamaría al LLM con un prompt de redacción;
    aquí devolvemos un borrador fijo para poder probar el ENRUTADO sin cuota.
    """
    print("  [redactor]   redactando el comunicado…")
    return {
        "respuesta": ("COMUNICADO (borrador): se ha detectado un incumplimiento "
                      "que se notifica al regulador conforme a la normativa vigente."),
        "quien_respondio": "redactor",
    }


# ============ 4) EL ENRUTADOR Y EL GRAFO ============
def hacia_donde(state: EstadoEquipo) -> Destino:
    """LangGraph llama a esto para elegir la siguiente arista."""
    return state["siguiente"]


def construir_grafo():
    """START -> supervisor -> (consultor | evaluador | redactor) -> supervisor -> END."""
    grafo = StateGraph(EstadoEquipo)
    grafo.add_node("supervisor", supervisor)
    grafo.add_node("consultor", consultor)
    grafo.add_node("evaluador", evaluador)
    grafo.add_node("redactor", redactor)      # ⭐ registrar el nodo nuevo

    grafo.add_edge(START, "supervisor")

    grafo.add_conditional_edges(
        "supervisor",
        hacia_donde,
        # ⭐ el mapa incluye ahora la entrada "redactor"
        {"consultor": "consultor", "evaluador": "evaluador",
         "redactor": "redactor", "FIN": END},
    )

    # ⭐ el redactor DEVUELVE EL CONTROL al supervisor, igual que los otros dos.
    #    Sin esta arista, el grafo no sabría cómo terminar tras redactar.
    grafo.add_edge("consultor", "supervisor")
    grafo.add_edge("evaluador", "supervisor")
    grafo.add_edge("redactor", "supervisor")

    return grafo.compile()


def responder(pregunta: str) -> EstadoEquipo:
    """Una vuelta completa del equipo."""
    grafo = construir_grafo()
    return grafo.invoke({
        "pregunta": pregunta, "siguiente": "", "respuesta": "", "quien_respondio": "",
    })


# ============ 5) LA TABLA DE PREDICCIÓN, RESUELTA ============
PREGUNTAS_DE_PRUEBA = [
    "¿Cuántos años se conservan los registros?",             # -> consultor
    "Evalúa esta regla: cifrado AES-256.",                   # -> evaluador
    "Redacta el comunicado del incumplimiento de junio.",    # -> redactor
    "Documenta qué dice la norma sobre el consentimiento.",  # -> redactor ('documenta')
    "Redacta un informe que evalúe la regla 3.",             # -> redactor (¡el desempate!)
]


def main():
    print("=== Enrutado de cada pregunta (predícelo antes de leer) ===\n")
    for pregunta in PREGUNTAS_DE_PRUEBA:
        destino = decidir(pregunta, ya_respondido=False)
        print(f"  {destino:10s} <- {pregunta}")

    print("\n=== El desempate de la fila 5, al desnudo ===")
    ambigua = "Redacta un informe que evalúe la regla 3."
    print(f"  Pregunta: {ambigua}")
    print(f"  Con REDACCIÓN antes que evaluación en decidir(): -> {decidir(ambigua, False)}")
    print("  Si intercambiaras los dos `if`, la MISMA pregunta iría al 'evaluador'.")
    print("  No cambió la pregunta: cambió tu regla de desempate.\n")

    print("=== El grafo entero, de punta a punta ===")
    estado = responder("Redacta el comunicado del incumplimiento de junio.")
    print(f"🤖 [{estado['quien_respondio']}] {estado['respuesta']}")
    print(f"   siguiente={estado['siguiente']}  (FIN: el grafo terminó, sin bucle)\n")

    print("💡 Añadir el redactor NO alargó el prompt del consultor ni del evaluador.")
    print("   Cada especialista sigue con su trabajo. Eso compra el patrón supervisor.")


# ============ 6) TESTS QUE PEDÍA EL EJERCICIO ============
# Cópialos a tests/ (con un fixture que importe este módulo) y córrelos con
# `uv run pytest -m offline`:
#
#   def test_redaccion_va_al_redactor(sol15):
#       assert sol15.decidir("Redacta el comunicado del incumplimiento", False) == "redactor"
#
#   def test_el_desempate_lo_gana_quien_va_primero(sol15):
#       # Con redacción antes que evaluación en decidir(), gana el redactor.
#       assert sol15.decidir("Redacta un informe que evalúe la regla 3", False) == "redactor"
#
#   def test_las_dudas_siguen_yendo_al_consultor(sol15):
#       assert sol15.decidir("¿Qué dice la norma sobre el consentimiento?", False) == "consultor"
#
#   def test_el_grafo_enruta_y_termina(sol15):
#       estado = sol15.responder("Redacta el comunicado del incumplimiento")
#       assert estado["quien_respondio"] == "redactor"
#       assert estado["siguiente"] == "FIN"


if __name__ == "__main__":
    main()
