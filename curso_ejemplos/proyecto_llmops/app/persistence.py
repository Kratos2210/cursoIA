"""
persistence.py · Dónde vive la memoria del agente EN PRODUCCIÓN
================================================================
FINALIDAD:
  Aislar UNA decisión —dónde persiste el estado de cada conversación— igual que
  `proyecto_final/persistence.py`, pero cerrando su TODO: el prototipo documenta
  la migración a Postgres y se queda en MemorySaver; aquí la implementa.

  El 'checkpointer' es la pieza de LangGraph que, tras cada nodo, guarda una foto
  del estado bajo un `thread_id`. Gracias a él el agente recuerda los turnos
  anteriores de esa conversación. Con MemorySaver esa foto vive en RAM: un
  reinicio (deploy, OOM, `docker compose restart`) borra TODA conversación en
  curso, y con varios workers cada uno recuerda solo lo suyo.

LÓGICA — un context manager, dos backends:
      memoria    MemorySaver. Cero dependencias, cero persistencia. Lo correcto
                 para el curso y los tests.
      postgres   AsyncPostgresSaver sobre la MISMA base que ya usa pgvector. La
                 conversación sobrevive al deploy y la comparten los workers.

  ⭐ POR QUÉ ASYNC Y CON POOL, y no el `PostgresSaver` síncrono de una conexión
     que documenta el prototipo. El servicio sirve con `agente.astream(...)`
     (app/streaming.py) y puede atender varias peticiones a la vez. Un
     checkpointer síncrono, usado desde el bucle async, correría sus consultas
     en hilos del executor; y una SOLA conexión psycopg no admite uso
     concurrente —dos peticiones a la vez la corromperían—. Es un fallo que no
     ve ningún test unitario y solo aparece al desplegar bajo carga: justo la
     familia de L7/L8/L9. Por eso: `AsyncPostgresSaver` sobre un
     `AsyncConnectionPool`, que reparte una conexión por petición en vuelo.

  ⭐ ES UN CONTEXT MANAGER PORQUE EL POOL SE ABRE Y SE CIERRA. `main.py` lo
     envuelve en un `async with` en el `lifespan`: el pool se abre al arrancar el
     servicio (una vez, no por petición) y se cierra al apagarlo. Ceder el
     checkpointer en vez de esconderlo es lo que permite ese ciclo de vida.

  ⚠️ Usa `pg_dsn` (el de psycopg a pelo), NO `pg_dsn_sqlalchemy`. Es la otra cara
     de la lección L7: langchain-postgres monta un engine de SQLAlchemy y quiere
     el driver en el esquema; el checkpointer y psycopg.connect() hablan psycopg
     directo y quieren el DSN limpio. Dos consumidores, dos formatos.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import MemorySaver


@asynccontextmanager
async def abrir_checkpointer():
    """Cede el checkpointer configurado y libera sus recursos al salir.

    memoria  → MemorySaver (RAM). No abre nada; el `async with` no cuesta nada.
    postgres → AsyncPostgresSaver sobre un pool; `.setup()` crea sus tablas la
               primera vez (idempotente) y el pool se cierra al salir del `with`.

    Se usa así, una vez, en el arranque del servicio:

        async with abrir_checkpointer() as checkpointer:
            agentes = construir_agentes_por_variante(..., checkpointer=checkpointer)
            yield            # el servicio atiende con el pool abierto
        # aquí el pool ya se cerró
    """
    from app.config import settings

    if settings.checkpointer_backend.lower() != "postgres":
        # MemorySaver no tiene recursos que liberar: se cede y ya está.
        yield MemorySaver()
        return

    # Import diferido: estas dependencias solo hacen falta con Postgres, y así
    # el curso corre sin ellas instaladas mientras use "memoria".
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    # `open=False` + el `async with` es el patrón recomendado por psycopg_pool:
    # abrir en el constructor está deprecado. `autocommit=True` lo exige el
    # checkpointer (ejecuta DDL en `.setup()` y no quiere transacciones colgando);
    # `row_factory=dict_row` es lo que AsyncPostgresSaver espera leer.
    async with AsyncConnectionPool(
        conninfo=settings.pg_dsn,
        max_size=settings.checkpointer_pool_max,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=False,
    ) as pool:
        saver = AsyncPostgresSaver(pool)
        await saver.setup()          # crea checkpoints/… la primera vez
        yield saver
