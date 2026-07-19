"""
feedback_backends.py · Dónde viven los votos 👍/👎 cuando el proceso muere
==========================================================================
FINALIDAD:
  El gemelo de `metrics_backends.py`, para el otro extremo del A/B. El feedback
  vivía en una lista de Python dentro del proceso, con las mismas dos
  consecuencias —y la segunda, otra vez, peor que la primera:

    1) Un reinicio borraba todos los votos acumulados.
    2) Con N workers de uvicorn hay N colectores que NO se suman: `/feedback`
       devuelve los votos que vio ESE worker, o sea una fracción del total. Y el
       A/B de prompts (ADR-0006) decide el ganador sobre esos datos parciales:
       elegir variante con tres votos de un worker no es significancia, es una
       corazonada con barniz.

LÓGICA — el MISMO patrón que `metrics_backends.py` y `cache_backends.py`, a
  propósito: un Protocol, una implementación en memoria y otra sobre Postgres.
  Quien registra un voto no sabe cuál tiene delante.

      EnMemoria   Una lista. Cero dependencias, cero persistencia. Lo correcto
                  para los tests y para estudiar el curso.
      Postgres    La tabla `feedback_voto`. Sobrevive al reinicio y la comparten
                  todos los workers, así que `/feedback` vuelve a hablar del
                  experimento entero y no de un proceso suelto.

⚠️ Reutiliza el Postgres que el compose ya levanta para pgvector: no se añade
   infraestructura. Y usa `psycopg.connect(pg_dsn)` directo, como métricas —el
   voto se registra en un endpoint síncrono, no hay async que justificar aquí.
"""
from __future__ import annotations

from typing import Iterable, Protocol

from observability.feedback import Voto

# Cuántos votos recientes entran en el resumen. Acota memoria y SELECT: un
# experimento con meses de historia no debe traerse entero en cada `/feedback`.
LIMITE_RESUMEN = 100_000


class FeedbackBackend(Protocol):
    """Lo que el colector necesita de su almacén de votos. Nada más."""

    def registrar(self, voto: Voto) -> None: ...
    def leer(self, limite: int = LIMITE_RESUMEN) -> Iterable[Voto]: ...
    def limpiar(self) -> None: ...


class EnMemoria:
    """Una lista de Votos. Lo que había antes, ahora con nombre y contrato.

    Sigue siendo lo correcto para los tests y el curso: no requiere Postgres
    levantado y hace la suite instantánea.
    """

    def __init__(self):
        self._votos: list[Voto] = []

    def registrar(self, voto: Voto) -> None:
        self._votos.append(voto)

    def leer(self, limite: int = LIMITE_RESUMEN) -> Iterable[Voto]:
        return self._votos[-limite:]

    def limpiar(self) -> None:
        self._votos.clear()


class Postgres:
    """Los votos en una tabla. Compartida entre workers, sobrevive al deploy.

    ⚠️ DEGRADA EN VEZ DE TUMBAR EL SERVICIO. Igual que `metrics_backends.Postgres`
       y que `tracing.py`: si la base no responde, se registra el fallo y la
       petición sigue. Perder un voto es un mal día; devolver un 500 a un usuario
       que solo quería pulsar 👍, no.
    """

    DDL = """
    CREATE TABLE IF NOT EXISTS feedback_voto (
        id          BIGSERIAL PRIMARY KEY,
        creado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
        variante    TEXT        NOT NULL,
        util        BOOLEAN     NOT NULL,
        thread_id   TEXT        NOT NULL DEFAULT 'demo',
        comentario  TEXT
    );
    -- El resumen agrega por variante; este índice evita recorrer la tabla
    -- entera cada vez que alguien abre /feedback.
    CREATE INDEX IF NOT EXISTS ix_feedback_variante
        ON feedback_voto (variante);
    """

    def __init__(self, dsn: str | None = None, conectar=None):
        from app.config import settings
        self._dsn = dsn or settings.pg_dsn
        # `conectar` se inyecta en los tests para no depender de una base real.
        self._conectar = conectar or self._conectar_psycopg
        self._preparada = False

    def _conectar_psycopg(self):
        import psycopg
        return psycopg.connect(self._dsn)

    def _asegurar_tabla(self, cur) -> None:
        """Crea la tabla la primera vez. Idempotente por el IF NOT EXISTS.

        Se hace aquí y no en un script de migración por lo mismo que en
        `metrics_backends`: el proyecto no tiene (todavía) herramienta de
        migraciones, y pgvector y las métricas ya se autocrean así.
        """
        if self._preparada:
            return
        cur.execute(self.DDL)
        self._preparada = True

    def registrar(self, voto: Voto) -> None:
        from observability import logs
        try:
            with self._conectar() as conexion:
                with conexion.cursor() as cur:
                    self._asegurar_tabla(cur)
                    cur.execute(
                        "INSERT INTO feedback_voto "
                        "(variante, util, thread_id, comentario) "
                        "VALUES (%s, %s, %s, %s)",
                        (voto.variante, voto.util, voto.thread_id, voto.comentario))
        except Exception:
            logs.obtener_logger(__name__).exception(
                "no se pudo persistir el voto; la petición sigue")

    def leer(self, limite: int = LIMITE_RESUMEN) -> Iterable[Voto]:
        from observability import logs
        try:
            with self._conectar() as conexion:
                with conexion.cursor() as cur:
                    self._asegurar_tabla(cur)
                    cur.execute(
                        "SELECT variante, util, thread_id, comentario "
                        "FROM feedback_voto ORDER BY creado_en DESC LIMIT %s",
                        (limite,))
                    filas = cur.fetchall()
        except Exception:
            logs.obtener_logger(__name__).exception(
                "no se pudieron leer los votos; se informa un resumen vacío")
            return []

        return [
            Voto(variante=f[0], util=f[1], thread_id=f[2], comentario=f[3])
            for f in filas
        ]

    def limpiar(self) -> None:
        with self._conectar() as conexion:
            with conexion.cursor() as cur:
                self._asegurar_tabla(cur)
                cur.execute("TRUNCATE feedback_voto")


def crear_backend() -> FeedbackBackend:
    """El backend que diga la configuración. Igual que `metrics_backends`.

    Por defecto, memoria: el curso corre con un `uvicorn` y sin Docker.
    `FEEDBACK_BACKEND=postgres` lo cambia sin tocar código.
    """
    from app.config import settings
    if settings.feedback_backend.lower() == "postgres":
        return Postgres()
    return EnMemoria()
