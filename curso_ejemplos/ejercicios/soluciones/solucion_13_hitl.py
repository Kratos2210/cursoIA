"""
SOLUCIÓN · Ejercicio 13 — Escalar cuando el humano rechaza
==========================================================
⚠️ No leas esto hasta haberlo intentado.

El grafo original moría al rechazar un hallazgo. Ahora lo ESCALA:

                              ┌── aprobado ──> registrar ──> END
    START -> detectar -> aprobar ─┤
                              └── rechazado ─> escalar ───> END

100% offline: no usa LLM ni gasta cuota.
Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_13_hitl.py
"""

from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command


# ============ 1) EL ESTADO ============
class EstadoAuditoria(TypedDict):
    hallazgo: str
    severidad: str          # "alta" | "baja"
    aprobado: bool
    motivo_rechazo: str     # ⭐ NUEVO: por qué el humano dijo que no
    escalado_a: str         # ⭐ NUEVO: a quién sube el caso
    registro: str


SUPERVISOR = "jefatura de riesgos"


# ============ 2) LOS NODOS ============
def detectar(state: EstadoAuditoria):
    print("  [detectar]  hallazgo:", state["hallazgo"])
    return {}


def aprobar(state: EstadoAuditoria):
    """Severidad alta -> pausa y espera a un humano."""
    if state["severidad"] != "alta":
        print("  [aprobar]   severidad baja: se aprueba solo")
        return {"aprobado": True, "motivo_rechazo": ""}

    # ⭐ interrupt() puede devolver CUALQUIER cosa, no solo un string.
    #    Aquí esperamos un dict: {"respuesta": "si"|"no", "motivo": "..."}.
    decision = interrupt({
        "accion": "marcar incumplimiento regulatorio",
        "hallazgo": state["hallazgo"],
        "pregunta": "¿Apruebas registrar este incumplimiento? (si/no + motivo)",
    })

    # Aceptamos tanto un dict como un string suelto (retrocompatibilidad).
    if isinstance(decision, dict):
        respuesta = str(decision.get("respuesta", "")).strip().lower()
        motivo = decision.get("motivo", "")
    else:
        respuesta, motivo = str(decision).strip().lower(), ""

    return {"aprobado": respuesta == "si", "motivo_rechazo": motivo}


def registrar(state: EstadoAuditoria):
    veredicto = f"REGISTRADO: {state['hallazgo']} (aprobado)"
    print("  [registrar]", veredicto)
    return {"registro": veredicto}


def escalar(state: EstadoAuditoria):
    """⭐ EL NODO NUEVO. Un rechazo no borra el hallazgo: lo sube de nivel."""
    motivo = state["motivo_rechazo"] or "sin motivo declarado"
    veredicto = (f"ESCALADO a {SUPERVISOR}: {state['hallazgo']} "
                 f"(rechazado por el analista — motivo: {motivo})")
    print("  [escalar]  ", veredicto)
    return {"registro": veredicto, "escalado_a": SUPERVISOR}


# ============ 3) EL ENRUTADOR ============
def tras_aprobar(state: EstadoAuditoria) -> str:
    """Devuelve la ETIQUETA de la arista a seguir tras el nodo 'aprobar'."""
    return "registrar" if state["aprobado"] else "escalar"


def construir_grafo():
    grafo = StateGraph(EstadoAuditoria)
    grafo.add_node("detectar", detectar)
    grafo.add_node("aprobar", aprobar)
    grafo.add_node("registrar", registrar)
    grafo.add_node("escalar", escalar)

    grafo.add_edge(START, "detectar")
    grafo.add_edge("detectar", "aprobar")

    # ⚠️ OJO: aquí ya NO va grafo.add_edge("aprobar", "registrar").
    #    Si lo dejaras, el grafo iría SIEMPRE a registrar, además de a donde
    #    diga la condicional. Es el error más común al añadir una bifurcación.
    grafo.add_conditional_edges(
        "aprobar",
        tras_aprobar,
        {"registrar": "registrar", "escalar": "escalar"},
    )
    grafo.add_edge("registrar", END)
    grafo.add_edge("escalar", END)

    return grafo.compile(checkpointer=MemorySaver())


# ============ 4) UNA AYUDA PARA PROBARLO ============
ESTADO_INICIAL = {
    "hallazgo": "El 12% de los RUC del reporte de junio están vacíos",
    "severidad": "alta",
    "aprobado": False,
    "motivo_rechazo": "",
    "escalado_a": "",
    "registro": "",
}


def correr(severidad: str, respuesta=None, hilo: str = "demo") -> EstadoAuditoria:
    """Corre el grafo entero. Si se pausa, lo reanuda con 'respuesta'."""
    app = construir_grafo()
    config = {"configurable": {"thread_id": hilo}}
    resultado = app.invoke({**ESTADO_INICIAL, "severidad": severidad}, config)

    if "__interrupt__" in resultado:
        peticion = resultado["__interrupt__"][0].value
        print("  ⏸️  PAUSADO —", peticion["pregunta"])
        resultado = app.invoke(Command(resume=respuesta), config)
    return resultado


def main():
    print("=== Caso 1: severidad ALTA, el humano APRUEBA ===")
    r = correr("alta", {"respuesta": "si"}, hilo="caso1")
    print("  ->", r["registro"], "\n")

    print("=== Caso 2: severidad ALTA, el humano RECHAZA (con motivo) ===")
    r = correr("alta", {"respuesta": "no", "motivo": "falta evidencia del muestreo"},
               hilo="caso2")
    print("  ->", r["registro"])
    print("  -> escalado_a:", r["escalado_a"], "\n")

    print("=== Caso 3: severidad BAJA, nadie pregunta a nadie ===")
    r = correr("baja", hilo="caso3")
    print("  ->", r["registro"])
    print("  -> escalado_a:", repr(r["escalado_a"]), "(vacío: nunca pasó por 'escalar')\n")

    print("💡 Fíjate en lo que NO cambió: ni el modelo, ni el prompt, ni las tools.")
    print("   Solo el grafo. Eso es exactamente para lo que sirve LangGraph.")


# ============ 5) LOS TESTS QUE PEDÍA EL EJERCICIO ============
# Cópialos a tests/ y córrelos con:  uv run pytest -m offline
#
#   def test_aprobado_se_registra():
#       final = correr("alta", {"respuesta": "si"}, hilo="t1")
#       assert final["registro"].startswith("REGISTRADO")
#       assert final["escalado_a"] == ""
#
#   def test_rechazado_se_escala_con_motivo():
#       final = correr("alta", {"respuesta": "no", "motivo": "falta evidencia"}, hilo="t2")
#       assert final["registro"].startswith("ESCALADO")
#       assert "falta evidencia" in final["registro"]
#       assert final["escalado_a"] == SUPERVISOR
#
#   def test_severidad_baja_no_pausa_ni_escala():
#       final = correr("baja", hilo="t3")
#       assert "__interrupt__" not in final
#       assert final["registro"].startswith("REGISTRADO")
#       assert final["escalado_a"] == ""


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n(Interrumpido)")
