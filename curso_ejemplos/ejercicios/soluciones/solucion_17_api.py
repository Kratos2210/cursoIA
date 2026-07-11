"""
SOLUCIÓN · Ejercicio 17 — Un endpoint nuevo, probado sin API
==========================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Añadir GET /historial/{thread_id} y un /salud más rico al servidor del TEMA 17,
  y probarlos 100% OFFLINE con TestClient inyectando un agente FALSO. El agente
  real gasta cuota e indexa la normativa al arrancar; el doble de prueba imita
  solo lo que el endpoint necesita (get_state), así que las rutas se prueban en
  milisegundos y sin llave.

  El truco: TestClient(app) SIN el `with` NO ejecuta el lifespan, que es quien
  construiría el agente real. Así el arranque caro nunca corre.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_17_api.py
          (necesita fastapi:  uv sync --extra ui)
"""

import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage

CARPETA_CURSO = Path(__file__).resolve().parents[2]


# ============ 1) EL DOBLE DE PRUEBA ============
# El endpoint solo le pide al agente una cosa: get_state(config).values["messages"].
# El falso implementa exactamente eso, ni más ni menos. El endpoint no distingue
# este doble del agente real: esa es toda la idea de un test doble.
class EstadoFalso:
    def __init__(self, mensajes):
        self.values = {"messages": mensajes}


class AgenteFalso:
    HISTORIALES = {
        "ana": [
            HumanMessage("¿Cuántos años se conservan los registros?"),
            AIMessage("Diez años, según la Regla 2."),
        ],
    }

    def get_state(self, config):
        hilo = config["configurable"]["thread_id"]
        # Un hilo sin conversación devuelve lista vacía: "no hay historial" es una
        # respuesta válida, no un error.
        return EstadoFalso(self.HISTORIALES.get(hilo, []))


# ============ 2) LA APP CON LOS DOS ENDPOINTS NUEVOS ============
# Reutilizamos ESTADO y el contrato Pydantic del ejemplo 17. Añadimos las rutas
# que pedía el ejercicio. La forma de /chat, /salud y el lifespan es la del TEMA
# 17; aquí resaltamos lo NUEVO.
ESTADO: dict = {"agente": None, "atendidas": 0}


def crear_app():
    from contextlib import asynccontextmanager
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field

    # modelo_por_defecto() solo lee el .env; no habla con ningún proveedor.
    if str(CARPETA_CURSO) not in sys.path:
        sys.path.insert(0, str(CARPETA_CURSO))
    from util import modelo_por_defecto

    class ConsultaEntrada(BaseModel):
        pregunta: str = Field(min_length=1)
        usuario: str = Field(default="anonimo")

    class RespuestaSalida(BaseModel):
        respuesta: str
        usuario: str

    @asynccontextmanager
    async def lifespan(app):
        # OJO: en los tests NO usamos el `with`, así que esto NO corre. En
        # producción, aquí se construiría el agente real (caro, con llave).
        from importlib import import_module  # noqa: F401 — placeholder del ejemplo
        yield

    app = FastAPI(title="GobData — API con historial", lifespan=lifespan)

    @app.post("/chat", response_model=RespuestaSalida)
    def chat(consulta: ConsultaEntrada):
        agente = ESTADO["agente"]
        if agente is None:
            raise HTTPException(status_code=503, detail="El agente todavía está arrancando.")
        # (En el ejemplo real, aquí se invoca al agente. Para la solución offline
        #  nos basta con contar la petición y devolver un eco.)
        ESTADO["atendidas"] += 1
        return RespuestaSalida(respuesta=f"(eco) {consulta.pregunta}", usuario=consulta.usuario)

    @app.get("/salud")
    def salud():
        """Health check enriquecido: además de si está vivo, qué modelo y cuántas atendió."""
        listo = ESTADO["agente"] is not None
        return {
            "estado": "ok" if listo else "arrancando",
            "agente_listo": listo,
            "modelo": modelo_por_defecto(),      # ⭐ NUEVO
            "atendidas": ESTADO["atendidas"],    # ⭐ NUEVO
        }

    @app.get("/historial/{thread_id}")
    def historial(thread_id: str):
        """⭐ EL ENDPOINT NUEVO: devuelve la conversación guardada de un thread_id."""
        agente = ESTADO["agente"]
        if agente is None:
            raise HTTPException(status_code=503, detail="El agente todavía está arrancando.")
        config = {"configurable": {"thread_id": thread_id}}
        # .get("messages", []) -> un hilo sin historial da [] en vez de KeyError.
        mensajes = agente.get_state(config).values.get("messages", [])
        return {
            "thread_id": thread_id,
            "turnos": len(mensajes),
            "historial": [{"rol": m.type, "texto": m.content} for m in mensajes],
        }

    return app


# ============ 3) LA PRUEBA OFFLINE CON TestClient ============
def construir_cliente_de_prueba():
    """La app + un agente falso, sin disparar el lifespan (sin `with`, sin API)."""
    from fastapi.testclient import TestClient

    ESTADO["agente"] = AgenteFalso()     # inyectamos el doble
    ESTADO["atendidas"] = 0
    # SIN `with`: el lifespan no corre, así que construir_agente() nunca se llama.
    return TestClient(crear_app())


def main():
    try:
        cliente = construir_cliente_de_prueba()
    except ImportError:
        raise SystemExit("❌ Falta FastAPI. Instálalo con:  uv sync --extra ui")

    print("=== GET /historial/ana (un hilo con conversación) ===")
    r = cliente.get("/historial/ana")
    print(" ", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["turnos"] == 2
    assert r.json()["historial"][0]["rol"] == "human"
    assert r.json()["historial"][1]["rol"] == "ai"

    print("\n=== GET /historial/desconocido (un hilo sin historial) ===")
    r = cliente.get("/historial/desconocido")
    print(" ", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["turnos"] == 0          # sin historial NO es un error

    print("\n=== GET /salud (enriquecido) ===")
    r = cliente.get("/salud")
    print(" ", r.status_code, r.json())
    assert r.json()["agente_listo"] is True
    assert "modelo" in r.json()
    assert r.json()["atendidas"] == 0

    print("\n=== POST /chat y /salud otra vez (el contador sube) ===")
    cliente.post("/chat", json={"pregunta": "hola", "usuario": "ana"})
    r = cliente.get("/salud")
    print(" ", r.status_code, r.json())
    assert r.json()["atendidas"] == 1

    print("\n✅ Todos los endpoints verificados SIN llave y SIN arrancar el agente real.")
    print("💡 El agente caro nunca corrió: TestClient sin `with` no dispara el")
    print("   lifespan. Probaste tu código (las rutas), no el LLM que hay detrás.")


# ============ 4) TESTS QUE PEDÍA EL EJERCICIO ============
# Cópialos a tests/ (marca offline). Reusan construir_cliente_de_prueba():
#
#   def test_historial_de_un_hilo_con_conversacion(sol17):
#       cliente = sol17.construir_cliente_de_prueba()
#       datos = cliente.get("/historial/ana").json()
#       assert datos["turnos"] == 2
#       assert datos["historial"][0]["rol"] == "human"
#
#   def test_historial_de_un_hilo_vacio_no_es_error(sol17):
#       cliente = sol17.construir_cliente_de_prueba()
#       assert cliente.get("/historial/nadie").json()["turnos"] == 0
#
#   def test_salud_informa_modelo_y_contador(sol17):
#       cliente = sol17.construir_cliente_de_prueba()
#       cuerpo = cliente.get("/salud").json()
#       assert cuerpo["agente_listo"] is True and "modelo" in cuerpo


if __name__ == "__main__":
    main()
