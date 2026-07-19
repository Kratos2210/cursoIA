"""
ci_gate.py · El semáforo que bloquea un deploy malo
====================================================
FINALIDAD:
  Ser el paso del pipeline que dice NO. Corre la evaluación retail y sale con:
      exit 0 → el deploy sigue.
      exit 1 → el deploy se detiene.

  ⭐ Aquí está la diferencia entre "tenemos evaluación" y "tenemos LLMOps". Un
     dashboard con métricas que nadie mira no impide nada; un `exit 1` sí. La
     evaluación solo vale si tiene PODER DE VETO.

LÓGICA — dos puertas:
  1. PUERTA DE LA MEDIA: el % de casos fieles >= EVAL_UMBRAL_APROBACION (0.9).
  2. PUERTA DEL MÍNIMO: CERO tolerancia a un precio inventado. Un solo caso que
     cite un precio fuera del catálogo bloquea el deploy, aunque el resto vaya
     perfecto. En retail, un precio inventado no es "un caso flojo": es un reclamo.

  ⚠️ Sin la segunda puerta, 9 casos perfectos y uno que alucina un precio dan un
     0.90 y el deploy pasa. La media es exactamente la estadística que oculta el
     fallo que más importa.

⚠️ ESTE GATE GASTA CUOTA: llama al asistente una vez por caso. Por eso NO corre en
   cada push (para eso están los tests offline), sino antes de un deploy.

Correr:
    uv run python proyecto_retail/evals/ci_gate.py
    echo $?      # 0 = aprobado, 1 = bloqueado
"""
from __future__ import annotations

import sys

from proyecto_retail.app.config import settings
from proyecto_retail.evals.retail_metric import Reporte


def evaluar_puertas(reporte: Reporte, umbral_media: float) -> tuple[bool, list[str]]:
    """¿Pasa el deploy? Devuelve (aprobado, motivos_del_bloqueo). FUNCIÓN PURA.

    Que sea pura permite testear el gate ENTERO sin llamar a un LLM: se le
    construye un Reporte a mano y se comprueba que veta lo que debe vetar.
    """
    motivos: list[str] = []

    if not reporte.resultados:
        return False, ["El dataset de evaluación está vacío: no hay nada que aprobar."]

    # ---- Puerta 1: la media ----
    if reporte.score < umbral_media:
        motivos.append(
            f"Score {reporte.score:.0%} < umbral {umbral_media:.0%}: "
            f"el asistente respeta menos casos de los exigidos.")

    # ---- Puerta 2: cero precios inventados (la que la media esconde) ----
    infieles = [r for r in reporte.resultados if not r.fiel]
    for r in infieles:
        motivos.append(
            f"PRECIO INVENTADO en '{r.peticion[:50]}': cita un precio fuera del "
            f"catálogo. Cero tolerancia — en retail es un reclamo.")

    return not motivos, motivos


def main() -> int:  # pragma: no cover - requiere API
    """Corre la evaluación real y decide. Este es el exit code del pipeline."""
    from proyecto_retail.app.agent import construir_responder_real
    from proyecto_retail.app.etl import cargar_catalogo_demo
    from proyecto_retail.evals.run_evals import cargar_dataset, evaluar_casos, imprimir_reporte, muestrear
    from proyecto_retail.observability import tracing

    casos = muestrear(cargar_dataset(), settings.eval_muestra)
    reporte = evaluar_casos(casos, construir_responder_real(), cargar_catalogo_demo())
    imprimir_reporte(reporte, settings.eval_umbral_aprobacion)
    tracing.vaciar()

    aprobado, motivos = evaluar_puertas(reporte, settings.eval_umbral_aprobacion)
    if aprobado:
        print("✅ GATE APROBADO — el deploy puede continuar.\n")
        return 0
    print("❌ GATE BLOQUEADO — el deploy se detiene:\n")
    for motivo in motivos:
        print(f"   · {motivo}")
    print()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
