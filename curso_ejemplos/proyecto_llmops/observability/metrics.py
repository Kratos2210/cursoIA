"""
metrics.py · Qué medimos de cada request (y por qué esas cuatro cosas)
======================================================================
FINALIDAD:
  Registrar, por cada llamada al servicio, las señales que permiten responder a
  las preguntas de producción:

    "¿va lento?"          → latencia total y **TTFT** (time to first token).
    "¿cuánto gastamos?"   → tokens de entrada/salida y coste en dólares.
    "¿sirve el caché?"    → tasa de aciertos (hit rate).
    "¿saltan los guards?" → cuántas requests se bloquean o se sanean.

  ⭐ TTFT vs latencia total. Con streaming, el usuario percibe la velocidad del
     PRIMER token, no la del último. Un servicio con 4s de latencia total y 300ms
     de TTFT se siente rápido; uno con 2s de latencia y 2s de TTFT se siente
     roto. Si solo mides el total, optimizarás lo que nadie nota.

  ⭐ Por qué p95 y no la media. La media la aplasta el caso feliz: con 95
     requests de 200ms y 5 de 10s, la media dice 690ms y "todo va bien". El p95
     dice 10s, que es lo que sufre 1 de cada 20 usuarios. **Las medias esconden
     precisamente a la gente que se va.**

LÓGICA:
  - MetricasRequest: el registro inmutable de UNA request.
  - Cronometro: mide latencia y TTFT sin ensuciar el código que envuelve.
  - ColectorMetricas: acumula en memoria y agrega (p50, p95, coste total).

Todo es local y sin dependencias: la agregación de verdad la hace Langfuse
(tracing.py). Esto es la instrumentación mínima que funciona aunque Langfuse
esté caído — y que se puede testear sin levantar nada.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from observability.cost_model import Uso, estimar_costo, formatear_costo, precio_de


def _backend_por_defecto():
    """El backend configurado. Import diferido para no crear un ciclo:
    `metrics_backends` reconstruye MetricasRequest, que se define aquí."""
    from observability.metrics_backends import crear_backend
    return crear_backend()


@dataclass(frozen=True)
class MetricasRequest:
    """Todo lo observable de una sola request. Inmutable: es un hecho pasado."""
    modelo: str
    uso: Uso
    latencia_ms: float
    ttft_ms: float | None = None      # None si no hubo streaming
    cache_hit: bool = False
    acciones_guardrail: tuple[str, ...] = ()

    @property
    def costo(self) -> float:
        """El coste en dólares. Un cache_hit NO llamó al modelo: cuesta 0."""
        if self.cache_hit:
            return 0.0
        return estimar_costo(self.uso, self.modelo)

    @property
    def modelo_desconocido(self) -> bool:
        """¿Estamos midiendo el coste de un modelo que no está en la tabla?

        Importa porque `estimar_costo` devuelve 0.0 en ese caso, y un 0.0 así
        es indistinguible de "fue gratis" si nadie pregunta.
        """
        return precio_de(self.modelo) is None


class Cronometro:
    """Mide latencia total y TTFT. Se usa como context manager.

        with Cronometro() as crono:
            for token in stream:
                crono.primer_token()     # idempotente: solo cuenta la 1ª vez
                yield token
        crono.latencia_ms, crono.ttft_ms

    Usa `perf_counter` y no `time()`: el reloj de pared puede saltar hacia atrás
    (NTP, cambio de hora) y darte una latencia negativa. El monotónico, no.
    """

    def __init__(self):
        self._inicio: float | None = None
        self._primer_token: float | None = None
        self._fin: float | None = None

    def __enter__(self) -> "Cronometro":
        self._inicio = time.perf_counter()
        return self

    def __exit__(self, *_excepcion) -> None:
        self._fin = time.perf_counter()
        # No silenciamos excepciones: devolver None (falsy) las deja propagar.
        # Una request que falla también consumió tiempo, y también se mide.

    def primer_token(self) -> None:
        """Marca el instante del primer token. Llamarla varias veces no molesta."""
        if self._primer_token is None:
            self._primer_token = time.perf_counter()

    @property
    def latencia_ms(self) -> float:
        if self._inicio is None:
            return 0.0
        fin = self._fin if self._fin is not None else time.perf_counter()
        return (fin - self._inicio) * 1000

    @property
    def ttft_ms(self) -> float | None:
        if self._inicio is None or self._primer_token is None:
            return None
        return (self._primer_token - self._inicio) * 1000


def percentil(valores: list[float], p: float) -> float:
    """El percentil p (0-100) de una lista, por el método del vecino más cercano.

    FUNCIÓN PURA. Sin numpy a propósito: son cuatro líneas y así este módulo no
    arrastra una dependencia para calcular una mediana.

    Con [200, 200, 10000] y p=95 devuelve 10000: el peor caso NO se promedia.
    """
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    # ceil(p/100 * n) - 1, acotado al rango válido de índices.
    indice = int(round((p / 100) * len(ordenados) + 0.5)) - 1
    return ordenados[max(0, min(indice, len(ordenados) - 1))]


@dataclass
class ColectorMetricas:
    """Acumula MetricasRequest y las agrega. Dónde las guarda lo decide el backend.

    Por defecto, en memoria y por proceso — lo de siempre, y lo correcto para el
    curso y los tests. Con `METRICAS_BACKEND=postgres` pasan a una tabla
    compartida y entonces, y solo entonces, `/metrics` habla del SERVICIO y no
    del proceso que atendió esa petición.

    ⚠️ Con el backend en memoria sigue vigente el aviso de siempre: varios
       workers de uvicorn son varios colectores que no se suman, y ninguno ve el
       total. La agregación entre procesos la da Langfuse, o el backend de
       Postgres (ver observability/metrics_backends.py).
    """
    backend: object = field(default_factory=lambda: _backend_por_defecto())

    @property
    def registros(self) -> list[MetricasRequest]:
        """Las métricas vigentes, vengan de donde vengan.

        Es una property y no una lista para que el colector no dependa de dónde
        estén guardadas: todos los agregados de abajo siguen escritos igual.
        """
        return list(self.backend.leer())

    def registrar(self, metrica: MetricasRequest) -> None:
        self.backend.registrar(metrica)

    # ---- Agregados ----
    @property
    def total_requests(self) -> int:
        return len(self.registros)

    @property
    def costo_total(self) -> float:
        return sum(r.costo for r in self.registros)

    @property
    def tokens_totales(self) -> Uso:
        return Uso(
            entrada=sum(r.uso.entrada for r in self.registros),
            salida=sum(r.uso.salida for r in self.registros),
        )

    @property
    def tasa_cache(self) -> float:
        """Fracción de requests servidas desde caché (0.0 - 1.0)."""
        if not self.registros:
            return 0.0
        return sum(1 for r in self.registros if r.cache_hit) / len(self.registros)

    @property
    def tasa_bloqueo(self) -> float:
        """Fracción de requests que algún guardrail bloqueó."""
        if not self.registros:
            return 0.0
        bloqueadas = sum(
            1 for r in self.registros
            if any(a.startswith("bloqueo_") for a in r.acciones_guardrail)
        )
        return bloqueadas / len(self.registros)

    def latencia(self, p: float = 95) -> float:
        return percentil([r.latencia_ms for r in self.registros], p)

    def ttft(self, p: float = 95) -> float:
        """Percentil del TTFT, contando solo las requests que lo midieron.

        Las no-streaming aportan None; incluirlas como 0 mentiría a la baja.
        """
        medidos = [r.ttft_ms for r in self.registros if r.ttft_ms is not None]
        return percentil(medidos, p)

    def resumen(self) -> dict:
        """El diccionario que se imprime, se loguea o se manda a un dashboard."""
        tokens = self.tokens_totales
        return {
            "requests": self.total_requests,
            "tokens_entrada": tokens.entrada,
            "tokens_salida": tokens.salida,
            "costo_total": self.costo_total,
            "costo_legible": formatear_costo(self.costo_total),
            "latencia_p50_ms": round(self.latencia(50), 1),
            "latencia_p95_ms": round(self.latencia(95), 1),
            "ttft_p95_ms": round(self.ttft(95), 1),
            "tasa_cache": round(self.tasa_cache, 3),
            "tasa_bloqueo": round(self.tasa_bloqueo, 3),
        }
