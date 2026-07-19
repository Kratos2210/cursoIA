"""
run_evals.py · Correr la métrica retail sobre el dataset versionado
====================================================================
FINALIDAD:
  Cargar el dataset (`dataset.jsonl`), pedirle una respuesta al asistente para
  cada petición, y puntuar con la métrica del retail (presupuesto + stock +
  fidelidad de precios). Convierte "va mejor" en un número comparable.

⚠️ MUESTREO DETERMINISTA. Con `random.sample`, dos ejecuciones del CI sobre el
   MISMO commit evalúan casos distintos y dan scores distintos. Un gate que
   parpadea se acaba desactivando. Aquí el subconjunto se elige por el hash del
   `id`: mismo dataset y misma fracción → mismos casos, siempre. (Mismo patrón
   que proyecto_llmops/evals/run_evals.py.)

Correr:
    uv run python proyecto_retail/evals/run_evals.py
    EVAL_MUESTRA=0.5 uv run python proyecto_retail/evals/run_evals.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from proyecto_retail.evals.retail_metric import Reporte, evaluar_dataset


@dataclass(frozen=True)
class Caso:
    """Una fila del dataset."""
    id: str
    peticion: str
    categoria: str | None = None
    sin_resultados: bool = False


def cargar_dataset(ruta: Path | None = None) -> list[Caso]:
    """Lee el .jsonl. Una línea = un JSON = un caso. Las líneas '//' son comentarios."""
    if ruta is None:
        from proyecto_retail.app.config import settings
        ruta = settings.ruta_dataset

    casos = []
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("//"):
            continue
        try:
            casos.append(Caso(**json.loads(linea)))
        except (json.JSONDecodeError, TypeError) as error:
            # Un dataset roto debe fallar RUIDOSAMENTE: saltarse la línea mala en
            # silencio significa evaluar menos casos de los que crees.
            raise ValueError(f"{ruta}:{numero} — línea inválida: {error}") from error
    return casos


def muestrear(casos: list[Caso], fraccion: float) -> list[Caso]:
    """Una fracción REPRODUCIBLE del dataset, elegida por el hash del `id`."""
    if fraccion >= 1.0:
        return list(casos)
    if fraccion <= 0.0:
        return []
    cuantos = max(1, round(len(casos) * fraccion))
    ordenados = sorted(casos, key=lambda c: hashlib.md5(c.id.encode()).hexdigest())
    return ordenados[:cuantos]


def evaluar_casos(casos: list[Caso], responder, catalogo: list[dict]) -> Reporte:
    """Puente entre las filas del dataset y la métrica (que solo quiere peticiones)."""
    return evaluar_dataset([c.peticion for c in casos], responder, catalogo)


def imprimir_reporte(reporte: Reporte, umbral: float) -> None:
    """El informe que se lee en la consola del CI."""
    print("\n" + "=" * 66)
    print(f"  EVALUACIÓN RETAIL — {len(reporte.resultados)} casos")
    print("=" * 66)
    for r in reporte.resultados:
        marca = "✅" if r.aprobado else "❌"
        print(f"{marca} {r.peticion[:44]:<44} "
              f"({r.n_productos} prod · {r.motivo_fallo})")
    print("-" * 66)
    print(f"  {'SCORE (casos fieles)':<28} {reporte.score:.0%}   (umbral {umbral:.0%})")
    print("=" * 66 + "\n")


def main() -> int:  # pragma: no cover - requiere API
    """Evalúa el asistente REAL. Gasta cuota: llama al LLM por cada caso."""
    from proyecto_retail.app.agent import construir_responder_real
    from proyecto_retail.app.config import settings
    from proyecto_retail.app.etl import cargar_catalogo_demo
    from proyecto_retail.observability import tracing

    casos = muestrear(cargar_dataset(), settings.eval_muestra)
    if not casos:
        print("⚠️  El dataset está vacío (o EVAL_MUESTRA=0).")
        return 1

    reporte = evaluar_casos(casos, construir_responder_real(), cargar_catalogo_demo())
    imprimir_reporte(reporte, settings.eval_umbral_aprobacion)
    tracing.vaciar()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
