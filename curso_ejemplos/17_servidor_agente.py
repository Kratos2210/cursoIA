"""
TEMA 17 · Servir el agente: de un script a una API que alguien usa
==========================================================
FINALIDAD:
  Hasta ahora tu agente vive en una terminal. Nadie lo usa así. Este ejemplo
  cierra el círculo: lo pone detrás de una API HTTP con FastAPI, que es lo que
  consumiría una web, una app móvil o un bot de WhatsApp.

  Aquí aparecen los tres problemas que NO existen en un script:
    1. CONCURRENCIA — varios usuarios a la vez, cada uno con su conversación.
       Se resuelve con el thread_id del checkpointer (¡ya lo sabes!).
    2. ARRANQUE CARO — indexar el RAG tarda. No puedes hacerlo en cada petición.
       Se resuelve construyendo el agente UNA vez, al arrancar el servidor.
    3. ERRORES — un 429 no puede tumbar el servidor. Debe volverse un HTTP 503.

LÓGICA (paso a paso):
  1) Definimos el contrato de la API con Pydantic (mismo Pydantic del TEMA 05):
     qué entra (ConsultaEntrada) y qué sale (RespuestaSalida).
  2) 'lifespan': construimos el agente al arrancar y lo guardamos. Una sola vez.
  3) POST /chat: recibe {pregunta, usuario}; el 'usuario' se convierte en el
     thread_id, así cada persona tiene su propia memoria.
  4) GET /salud: el endpoint que mira el balanceador para saber si estás vivo.

  ⭐ Los imports de FastAPI están DENTRO de las funciones, no arriba. Así este
     archivo se puede importar (y testear) aunque no tengas FastAPI instalado.

Requisitos: uv sync --extra ui          (añade fastapi + uvicorn)
            + .env con GOOGLE_API_KEY   (el agente sí llama a la API)

Ejecuta:    uv run python curso_ejemplos/17_servidor_agente.py
Y en otra terminal:
    curl -X POST http://127.0.0.1:8000/chat \\
         -H 'Content-Type: application/json' \\
         -d '{"pregunta": "¿Cuántos años se conservan los registros?", "usuario": "ana"}'

Documentación automática (gratis, la genera FastAPI desde los moldes Pydantic):
    http://127.0.0.1:8000/docs
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os        # comprobar la llave y la disponibilidad de FastAPI
import sys       # salir con un mensaje útil si falta una dependencia

# Pydantic sí lo importamos arriba: ya es una dependencia del curso.
from pydantic import BaseModel, Field


# ============ 1) EL CONTRATO DE LA API ============
# FastAPI usa estos moldes para: validar la entrada, serializar la salida
# Y generar la documentación de /docs. Un molde, tres trabajos.
class ConsultaEntrada(BaseModel):
    """Lo que el cliente envía en el cuerpo del POST /chat."""
    pregunta: str = Field(description="La consulta del usuario", min_length=1)
    # El usuario identifica la conversación: mismo usuario = misma memoria.
    usuario: str = Field(default="anonimo", description="Identifica la conversación")


class RespuestaSalida(BaseModel):
    """Lo que el servidor devuelve."""
    respuesta: str
    usuario: str


# ============ 2) EL AGENTE: se construye UNA vez ============
# Un diccionario a nivel de módulo hace de "estado del servidor". El agente
# vive aquí desde que arranca hasta que muere el proceso.
ESTADO: dict = {"agente": None}


def construir_agente():
    """Arma el agente del proyecto final. ⚠️ Caro: indexa la normativa (llama a la API).

    Reutilizamos el proyecto final tal cual. Ese es el premio de haberlo
    modularizado: se importa desde otro sitio sin copiar una sola línea.
    """
    ruta_proyecto = os.path.join(os.path.dirname(__file__), "proyecto_final")
    if ruta_proyecto not in sys.path:
        sys.path.insert(0, ruta_proyecto)
    import graph_builder            # noqa: E402 — el import debe ir tras tocar sys.path
    return graph_builder.construir_agente_real()


def responder(agente, pregunta: str, usuario: str) -> str:
    """Un turno de conversación para 'usuario'.

    ⭐ Aquí está toda la concurrencia del sistema: el thread_id. Dos usuarios
    distintos usan el mismo agente y el mismo checkpointer, pero sus historiales
    no se mezclan porque cada uno tiene su hilo.
    """
    config = {"configurable": {"thread_id": usuario}}
    resultado = agente.invoke({"messages": [("user", pregunta)]}, config)
    return resultado["messages"][-1].content


# ============ 3) LA APLICACIÓN FASTAPI ============
def crear_app():
    """Construye la app. El import de FastAPI vive aquí dentro (ver docstring)."""
    try:
        from contextlib import asynccontextmanager
        from fastapi import FastAPI, HTTPException
    except ImportError:
        raise SystemExit(
            "❌ Falta FastAPI. Instálalo con:  uv sync --extra ui\n"
            "   (o:  uv pip install 'fastapi>=0.115' uvicorn)"
        )

    @asynccontextmanager
    async def lifespan(app):
        """Se ejecuta UNA vez al arrancar, y otra al apagar.

        Todo lo caro va aquí. Si construyéramos el agente dentro de /chat,
        cada petición re-indexaría la normativa: lento y carísimo.
        """
        print("🚀 Arrancando: indexando la normativa (esto tarda unos segundos)…")
        ESTADO["agente"] = construir_agente()
        print("✅ Agente listo. Documentación en http://127.0.0.1:8000/docs")
        yield                       # <-- aquí el servidor atiende peticiones
        print("\n👋 Apagando el servidor.")

    app = FastAPI(
        title="GobData — Asistente de Gobierno de Datos",
        description="El proyecto final del curso, servido por HTTP.",
        lifespan=lifespan,
    )

    @app.get("/salud")
    def salud():
        """Health check: lo que consulta un balanceador o Kubernetes.

        Responde 200 solo si el agente ya terminó de construirse.
        """
        listo = ESTADO["agente"] is not None
        return {"estado": "ok" if listo else "arrancando", "agente_listo": listo}

    @app.post("/chat", response_model=RespuestaSalida)
    def chat(consulta: ConsultaEntrada):
        """El endpoint principal. FastAPI ya validó la entrada por nosotros."""
        agente = ESTADO["agente"]
        if agente is None:
            # 503 = "aún no puedo atenderte, vuelve en un momento".
            raise HTTPException(status_code=503, detail="El agente todavía está arrancando.")

        try:
            respuesta = responder(agente, consulta.pregunta, consulta.usuario)
        except Exception as error:
            # ⭐ Un 429 del proveedor NO debe tumbar el servidor ni devolver un
            #    500 críptico. Lo traducimos a un 503 con un mensaje honesto.
            if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
                raise HTTPException(
                    status_code=503,
                    detail="Cuota del modelo agotada (429). Reintenta en unos minutos.",
                )
            raise HTTPException(status_code=500, detail=f"Error interno: {error}")

        return RespuestaSalida(respuesta=respuesta, usuario=consulta.usuario)

    return app


def main():
    """Levanta el servidor con uvicorn."""
    try:
        import uvicorn
    except ImportError:
        raise SystemExit("❌ Falta uvicorn. Instálalo con:  uv sync --extra ui")

    if not os.getenv("GOOGLE_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("❌ Falta GOOGLE_API_KEY: el agente no puede arrancar sin llave.")

    print("💡 Prueba, en otra terminal:")
    print("   curl -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \\")
    print("        -d '{\"pregunta\": \"¿Cuántos años se conservan los registros?\", \"usuario\": \"ana\"}'")
    print("   Repite con el mismo 'usuario' y verás que el agente RECUERDA.\n")

    # reload=False: con reload, lifespan correría dos veces (dos indexados).
    uvicorn.run(crear_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n(Servidor detenido)")
