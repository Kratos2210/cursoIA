"""
metrics_backends.py · Dónde viven las métricas cuando el proceso muere
=======================================================================
FINALIDAD:
  Cerrar L3 de la auditoría: métricas y feedback vivían en una lista de Python,
  dentro del proceso. Dos consecuencias, y la segunda es peor que la primera:

    1) Un reinicio (un deploy, un OOM, un `docker compose restart`) borraba
       todo el historial de coste y latencia.
    2) Con N workers de uvicorn hay N colectores que NO se suman. `/metrics`
       devuelve lo que vio el worker que atendió ESA petición, o sea una
       fracción arbitraria del tráfico. El A/B de prompts (ADR-0006) decidía
       sobre esos datos parciales.

LÓGICA — el mismo patrón que `cache/cache_backends.py`, y a propósito:
  un Protocol, una implementación en memoria y una sobre la infraestructura
  real. Quien escribe métricas no sabe cuál tiene delante.

      EnMemoria   Lo de siempre. Cero dependencias, cero persistencia.
                  Es lo correcto para los tests y para estudiar el curso.
      Postgres    La tabla `metricas_request`. Sobrevive al reinicio y la
                  comparten todos los workers, así que /metrics vuelve a
                  hablar del servicio y no de un proceso suelto.

⚠️ EL RESUMEN SE CALCULA EN PYTHON, leyendo las últimas N filas. Es honesto
   decir por qué: los percentiles exactos sobre millones de filas se calculan en
   SQL (`percentile_cont`), no trayéndolas. Con el volumen de este proyecto —y
   con `LIMITE_RESUMEN` acotando la lectura— traerlas es más simple y se lee
   mejor, que es lo que pide un curso. Si el tráfico crece, el cambio está
   localizado en `Postgres.leer()`.
"""
from __future__ import annotations

from typing import Iterable, Protocol

from observability.cost_model import Uso

# Cuántas peticiones recientes entran en el resumen. Acota tanto la memoria
# como el SELECT: un servicio con meses de historia no debe traerla entera
# cada vez que alguien abre /metrics.
LIMITE_RESUMEN = 10_000


class MetricasBackend(Protocol):
    """Lo que el colector necesita de su almacén. Nada más."""

    def registrar(self, metrica) -> None: ...
    def leer(self, limite: int = LIMITE_RESUMEN) -> Iterable: ...
    def limpiar(self) -> None: ...


class EnMemoria:
    """Una lista. Lo que había antes, ahora con nombre y contrato.

    Sigue siendo la opción correcta para los tests y para el curso: no requiere
    Postgres levantado y hace la suite instantánea.
    """

    def __init__(self):
        self._metricas: list = []

    def registrar(self, metrica) -> None:
        self._metricas.append(metrica)

    def leer(self, limite: int = LIMITE_RESUMEN) -> Iterable:
        return self._metricas[-limite:]

    def limpiar(self) -> None:
        self._metricas.clear()


class Postgres:
    """Las métricas en una tabla. Compartida entre workers, sobrevive al deploy.

    Reutiliza el Postgres que ya levanta el docker-compose para pgvector: no se
    añade infraestructura, se aprovecha la que hay.

    ⚠️ DEGRADA EN VEZ DE TUMBAR EL SERVICIO. Si la base no está disponible, se
       registra el fallo y la petición sigue su curso. Es la misma política que
       `observability/tracing.py`: un fallo del sistema que OBSERVA no puede
       tumbar el sistema OBSERVADO. Perder una métrica es un mal día; devolver
       un 500 al usuario porque no pudimos apuntar su latencia, no.
    """

    DDL = """
    CREATE TABLE IF NOT EXISTS metricas_request (
        id           BIGSERIAL PRIMARY KEY,
        creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
        modelo       TEXT        NOT NULL,
        entrada      INTEGER     NOT NULL DEFAULT 0,
        salida       INTEGER     NOT NULL DEFAULT 0,
        latencia_ms  DOUBLE PRECISION NOT NULL,
        ttft_ms      DOUBLE PRECISION,
        cache_hit    BOOLEAN     NOT NULL DEFAULT FALSE,
        acciones     TEXT[]      NOT NULL DEFAULT '{}'
    );
    -- El resumen siempre pide las más recientes: sin este índice, cada
    -- /metrics haría un recorrido completo de la tabla.
    CREATE INDEX IF NOT EXISTS ix_metricas_creado_en
        ON metricas_request (creado_en DESC);
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

        Se hace aquí y no en un script de migración porque el proyecto no tiene
        (todavía) herramienta de migraciones; el ADR-0003 ya asume este estilo
        para pgvector, que también se autocrea.
        """
        if self._preparada:
            return
        cur.execute(self.DDL)
        self._preparada = True

    def registrar(self, metrica) -> None:
        from observability import logs
        try:
            with self._conectar() as conexion:
                with conexion.cursor() as cur:
                    self._asegurar_tabla(cur)
                    cur.execute(
                        "INSERT INTO metricas_request "
                        "(modelo, entrada, salida, latencia_ms, ttft_ms, cache_hit, acciones) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (metrica.modelo, metrica.uso.entrada, metrica.uso.salida,
                         metrica.latencia_ms, metrica.ttft_ms, metrica.cache_hit,
                         list(metrica.acciones_guardrail)))
        except Exception:
            logs.obtener_logger(__name__).exception(
                "no se pudo persistir la métrica; la petición sigue")

    def leer(self, limite: int = LIMITE_RESUMEN) -> Iterable:
        from observability import logs
        from observability.metrics import MetricasRequest
        try:
            with self._conectar() as conexion:
                with conexion.cursor() as cur:
                    self._asegurar_tabla(cur)
                    cur.execute(
                        "SELECT modelo, entrada, salida, latencia_ms, ttft_ms, "
                        "cache_hit, acciones FROM metricas_request "
                        "ORDER BY creado_en DESC LIMIT %s", (limite,))
                    filas = cur.fetchall()
        except Exception:
            logs.obtener_logger(__name__).exception(
                "no se pudieron leer las métricas; se informa un resumen vacío")
            return []

        return [
            MetricasRequest(modelo=f[0], uso=Uso(entrada=f[1], salida=f[2]),
                            latencia_ms=f[3], ttft_ms=f[4], cache_hit=f[5],
                            acciones_guardrail=tuple(f[6] or ()))
            for f in filas
        ]

    def limpiar(self) -> None:
        with self._conectar() as conexion:
            with conexion.cursor() as cur:
                self._asegurar_tabla(cur)
                cur.execute("TRUNCATE metricas_request")


def crear_backend() -> MetricasBackend:
    """El backend que diga la configuración. Igual que `cache_backends`.

    Por defecto, memoria: el curso tiene que correr con un `uvicorn` y sin
    Docker. `METRICAS_BACKEND=postgres` lo cambia sin tocar código.
    """
    from app.config import settings
    if settings.metricas_backend.lower() == "postgres":
        return Postgres()
    return EnMemoria()
