"""
metrics.py · Qué medimos de cada request (y por qué esas cosas)
================================================================
FINALIDAD:
  Registrar, por cada consulta al asistente, las señales de producción:

    "¿va lento?"          → latencia total y TTFT (time to first token).
    "¿cuánto gastamos?"   → tokens de entrada/salida y coste en dólares.
    "¿sirve el caché?"    → tasa de aciertos.
    "¿saltan los guards?" → cuántas requests se bloquean (inyección, precio inventado).

  ⭐ TTFT vs latencia total: con streaming, el usuario percibe la velocidad del
     PRIMER token. Un servicio de 4s totales y 300ms de TTFT se siente rápido.
  ⭐ p95 y no la media: con 95 requests de 200ms y 5 de 10s, la media dice 690ms
     y "todo va bien"; el p95 dice 10s, que es lo que sufre 1 de cada 20 usuarios.

Todo local y sin dependencias; la agregación entre procesos la haría Langfuse.
Es la instrumentación mínima que funciona aunque Langfuse esté caído — y que se
testea sin levantar nada. (Espejo del metrics.py de proyecto_llmops.)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from proyecto_retail.observability.cost_model import Uso, estimar_costo, formatear_costo, precio_de


@dataclass(frozen=True)
class MetricasRequest:
    """Todo lo observable de una sola request. Inmutable: es un hecho pasado."""
    modelo: str
    uso: Uso
    latencia_ms: float
    ttft_ms: float | None = None
    cache_hit: bool = False
    acciones_guardrail: tuple[str, ...] = ()

    @property
    def costo(self) -> float:
        """Un cache_hit NO llamó al modelo: cuesta 0."""
        if self.cache_hit:
            return 0.0
        return estimar_costo(self.uso, self.modelo)

    @property
    def modelo_desconocido(self) -> bool:
        return precio_de(self.modelo) is None


class Cronometro:
    """Mide latencia total y TTFT. Context manager. Usa perf_counter (monotónico)."""

    def __init__(self):
        self._inicio: float | None = None
        self._primer_token: float | None = None
        self._fin: float | None = None

    def __enter__(self) -> "Cronometro":
        self._inicio = time.perf_counter()
        return self

    def __exit__(self, *_exc) -> None:
        self._fin = time.perf_counter()

    def primer_token(self) -> None:
        """Marca el primer token. Idempotente: solo cuenta la 1ª vez."""
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
    """El percentil p (0-100), por el vecino más cercano. PURA, sin numpy.

    Con [200, 200, 10000] y p=95 devuelve 10000: el peor caso NO se promedia.
    """
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = int(round((p / 100) * len(ordenados) + 0.5)) - 1
    return ordenados[max(0, min(indice, len(ordenados) - 1))]


@dataclass
class ColectorMetricas:
    """Acumula MetricasRequest y las agrega. En memoria, por proceso.

    ⚠️ Con varios workers de uvicorn cada uno tiene su colector: sirve para un
       dashboard local y para los tests; el total agregado lo daría Langfuse.
    """
    registros: list[MetricasRequest] = field(default_factory=list)

    def registrar(self, metrica: MetricasRequest) -> None:
        self.registros.append(metrica)

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
        if not self.registros:
            return 0.0
        return sum(1 for r in self.registros if r.cache_hit) / len(self.registros)

    @property
    def tasa_bloqueo(self) -> float:
        if not self.registros:
            return 0.0
        bloqueadas = sum(
            1 for r in self.registros
            if any(a.startswith("bloqueo_") for a in r.acciones_guardrail))
        return bloqueadas / len(self.registros)

    def latencia(self, p: float = 95) -> float:
        return percentil([r.latencia_ms for r in self.registros], p)

    def ttft(self, p: float = 95) -> float:
        medidos = [r.ttft_ms for r in self.registros if r.ttft_ms is not None]
        return percentil(medidos, p)

    def resumen(self) -> dict:
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
