"""
persistence.py · Dónde vive la memoria del agente
==================================================
FINALIDAD:
  Aislar UNA decisión: dónde se guarda el estado de cada conversación.
  Hoy es la RAM. Mañana será Postgres. El resto del código no debe enterarse.

LÓGICA:
  El 'checkpointer' es la pieza de LangGraph que, después de cada nodo,
  guarda una foto del estado bajo un thread_id. Gracias a eso el agente:
    - recuerda los turnos anteriores de esa conversación, y
    - puede pausarse con interrupt() y reanudarse horas después (TEMA 13b).

  ⚠️ MemorySaver guarda en un diccionario en RAM: si el proceso muere, la
     conversación se pierde. Sirve para un curso y para tests. NO para producción.

CÓMO CAMBIARLO A UNA BASE DE DATOS REAL:

  1) SQLite (un archivo local, ideal para una app de escritorio o un piloto):

         # uv pip install langgraph-checkpoint-sqlite
         from langgraph.checkpoint.sqlite import SqliteSaver
         with SqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
             agente = construir_agente(checkpointer=saver)

  2) PostgreSQL (varios procesos, varios servidores: lo de producción):

         # uv pip install langgraph-checkpoint-postgres
         from langgraph.checkpoint.postgres import PostgresSaver
         with PostgresSaver.from_conn_string(os.environ["DATABASE_URL"]) as saver:
             saver.setup()          # crea las tablas la primera vez
             agente = construir_agente(checkpointer=saver)

  Fíjate en que AMBOS son gestores de contexto ('with'): abren y cierran una
  conexión. Por eso esta función devuelve el checkpointer y no lo esconde: el
  día que migres, main.py envuelve la llamada en un 'with' y ya está.
"""

from langgraph.checkpoint.memory import MemorySaver


def crear_checkpointer():
    """Devuelve el checkpointer del agente (hoy, memoria RAM).

    Único punto del proyecto que decide dónde persiste la conversación.
    """
    return MemorySaver()
