"""
PROYECTO FINAL · Asistente de Gobierno de Datos (financiera)
============================================================
FINALIDAD:
  El punto de entrada. Arma el agente y simula una conversación de 2 turnos.

  Este es el mismo asistente del app.py original, pero repartido en módulos:

      config.py        -> rutas, modelos, constantes (nada se ejecuta al importar)
      rag.py           -> trocear la normativa, vectorizarla, recuperar contexto
      audit.py         -> el molde HallazgoCalidad y el log de auditoría
      tools.py         -> las dos tools del agente (fábrica con inyección)
      state.py         -> el estado que viaja por el grafo
      persistence.py   -> dónde vive la memoria (MemorySaver hoy, Postgres mañana)
      graph_builder.py -> ensambla modelo + tools + memoria
      main.py          -> esto: la demo

  Por qué molestarse: el archivo único no se podía testear (al importarlo
  llamaba a la API) ni cambiar de base de datos sin tocar la lógica. Ahora
  proyecto_final/tests/ verifica el 80% del proyecto SIN gastar cuota.

LÓGICA (paso a paso):
  1) construir_agente_real(): valida la llave, crea el modelo, indexa la normativa.
  2) Turno 1: una consulta -> el agente elige buscar_normativa (RAG).
  3) Turno 2: evaluar una regla -> elige evaluar_regla_calidad
     (RAG + salida estructurada + escritura en el log de auditoría).
  4) Mostramos el log que quedó.

Requisitos: uv sync   +   .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/proyecto_final/main.py
"""

import audit
import config
import graph_builder

# El thread_id separa conversaciones (como el ID de cada analista).
# Mismo thread_id = el agente recuerda; distinto = empieza de cero.
CONFIG_HILO = {"configurable": {"thread_id": "analista_ana"}}

TURNOS = [
    ("Turno 1: consulta de normativa",
     "¿Cuántos años se conservan los registros transaccionales?"),
    ("Turno 2: evaluar una regla",
     "Evalúa esta regla: 'Los datos personales deben cifrarse en reposo con AES-256'."),
]


def conversar(agente, pregunta: str) -> str:
    """Un turno de conversación. Devuelve el texto de la última respuesta."""
    resultado = agente.invoke({"messages": [("user", pregunta)]}, CONFIG_HILO)
    return resultado["messages"][-1].content


def main():
    agente = graph_builder.construir_agente_real()

    for titulo, pregunta in TURNOS:
        print(f"=== {titulo} ===")
        print("GobData:", conversar(agente, pregunta), "\n")

    # ---- Mostrar el log de auditoría generado ----
    lineas = audit.leer_auditoria()
    if lineas:
        print(f"=== 🧾 Log de auditoría ({config.RUTA_AUDITORIA.name}) ===")
        print("\n".join(lineas))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if config.es_error_cuota(error):
            print(config.mensaje_cuota())
        else:
            print(f"❌ Error inesperado: {error}")
