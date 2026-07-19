"""
test_persistence_checkpointer.py · La memoria del agente, ahora persistente
===========================================================================
`app/persistence.abrir_checkpointer` es el context manager que decide DÓNDE vive
la conversación: en RAM (MemorySaver, el default del curso) o en Postgres
(AsyncPostgresSaver, para que sobreviva al deploy y la compartan los workers).

Dos capas de prueba:
  · offline  → el default es MemorySaver y no abre ningún recurso.
  · Postgres → con `PYTEST_PG_DSN`, un round-trip REAL: se escribe un checkpoint,
               se CIERRA el pool, se reabre otro y el checkpoint sigue ahí. Eso
               —sobrevivir a cerrar la conexión— es justo lo que MemorySaver no
               hace y lo que ningún test unitario ve. Es la familia de L7/L8/L9:
               código correcto, verificable solo contra la infraestructura real.

⚠️ Sin plugin de asyncio en la suite (ver conftest): los flujos async se conducen
   con `asyncio.run` desde tests síncronos, como el resto del proyecto.
"""
import asyncio
import os
import urllib.parse

import pytest
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.memory import MemorySaver

from app import persistence

pytestmark = pytest.mark.offline

PG_DSN = os.environ.get("PYTEST_PG_DSN")

# Un thread fijo (no se puede aleatorizar en esta suite) y reconocible, que el
# teardown limpia para que el test sea repetible.
THREAD = "test-checkpointer-round-trip"
CONFIG = {"configurable": {"thread_id": THREAD, "checkpoint_ns": ""}}


class TestPorDefectoEsMemoria:
    def test_el_default_cede_un_memorysaver(self, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "checkpointer_backend", "memoria")

        async def run():
            async with persistence.abrir_checkpointer() as saver:
                return saver

        assert isinstance(asyncio.run(run()), MemorySaver)

    def test_un_backend_desconocido_tambien_cae_en_memoria(self, monkeypatch):
        # Cualquier cosa que no sea exactamente "postgres" es memoria: un typo en
        # el .env no debe intentar (ni fallar) abriendo un pool a Postgres.
        from app.config import settings
        monkeypatch.setattr(settings, "checkpointer_backend", "sqlite")

        async def run():
            async with persistence.abrir_checkpointer() as saver:
                return saver

        assert isinstance(asyncio.run(run()), MemorySaver)


@pytest.mark.skipif(not PG_DSN, reason="sin PYTEST_PG_DSN: no hay Postgres al que conectarse")
class TestPostgresRoundTrip:
    """La conversación sobrevive a cerrar el pool. Contra Postgres de verdad.

    Correr con:
        PYTEST_PG_DSN=postgresql://gobdata:gobdata@localhost:5433/gobdata \\
            uv run pytest proyecto_llmops/tests/test_persistence_checkpointer.py
    """

    @pytest.fixture(autouse=True)
    def _apuntar_settings_a_pg(self, monkeypatch):
        # abrir_checkpointer construye su DSN desde settings.pg_*, no desde
        # PYTEST_PG_DSN: apuntamos esos campos al mismo destino que usa el resto
        # de la suite de integración.
        from app.config import settings
        u = urllib.parse.urlparse(PG_DSN)
        monkeypatch.setattr(settings, "checkpointer_backend", "postgres")
        monkeypatch.setattr(settings, "pg_host", u.hostname)
        monkeypatch.setattr(settings, "pg_port", u.port or 5432)
        monkeypatch.setattr(settings, "pg_user", u.username)
        monkeypatch.setattr(settings, "pg_password", u.password)
        monkeypatch.setattr(settings, "pg_db", u.path.lstrip("/"))
        yield
        self._limpiar_thread()

    def _limpiar_thread(self):
        import psycopg
        with psycopg.connect(PG_DSN, autocommit=True) as con:
            with con.cursor() as cur:
                for tabla in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
                    # Las tablas existen tras el primer setup(); si aún no, no hay
                    # nada que limpiar. Con autocommit cada DELETE es su propia
                    # transacción, así que el fallo de una no envenena a la
                    # siguiente.
                    try:
                        cur.execute(f"DELETE FROM {tabla} WHERE thread_id = %s", (THREAD,))
                    except psycopg.errors.UndefinedTable:
                        pass

    def test_el_checkpoint_sobrevive_a_reabrir_el_pool(self):
        # 1) Escribir un checkpoint con un pool, y CERRARLO al salir del `with`.
        async def escribir():
            async with persistence.abrir_checkpointer() as saver:
                chk = empty_checkpoint()
                await saver.aput(CONFIG, chk, {"source": "test"}, {})
                return chk["id"]

        id_escrito = asyncio.run(escribir())

        # 2) Reabrir OTRO pool (nueva conexión) y leerlo. Si viviera en RAM como
        #    MemorySaver, aquí no habría nada: el primer pool ya se cerró.
        async def leer():
            async with persistence.abrir_checkpointer() as saver:
                return await saver.aget_tuple(CONFIG)

        tupla = asyncio.run(leer())
        assert tupla is not None, "el checkpoint no sobrevivió: ¿se guardó en RAM?"
        assert tupla.checkpoint["id"] == id_escrito

    def test_un_thread_inexistente_no_devuelve_nada(self):
        # La consulta viaja a Postgres (prueba pool + setup + conexión reales) y
        # devuelve None sin reventar.
        async def leer():
            async with persistence.abrir_checkpointer() as saver:
                cfg = {"configurable": {"thread_id": "no-existe-jamas",
                                        "checkpoint_ns": ""}}
                return await saver.aget_tuple(cfg)

        assert asyncio.run(leer()) is None
