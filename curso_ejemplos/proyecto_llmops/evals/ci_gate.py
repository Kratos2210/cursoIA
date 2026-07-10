"""
ci_gate.py · El semáforo que bloquea un deploy malo
====================================================
FINALIDAD:
  Ser el paso del pipeline que dice NO. Corre la evaluación y sale con:

      exit 0 → el deploy sigue.
      exit 1 → el deploy se detiene.

  ⭐ Aquí está la diferencia entre "tenemos evaluación" y "tenemos LLMOps". Un
     dashboard con métricas que nadie mira no impide nada. Un `exit 1` en el
     pipeline sí. La evaluación solo vale si tiene **poder de veto**.

LÓGICA — dos puertas, no una:
  1. PUERTA DE LA MEDIA: el score global >= EVAL_UMBRAL_APROBACION (0.7).
     Detecta la degradación general del sistema.

  2. PUERTA DEL MÍNIMO: ningún ejemplo por debajo de UMBRAL_CRITICO (0.5).
     Detecta el caso roto que la media esconde.

  ⚠️ Sin la segunda puerta, esto no sirve. Con 20 ejemplos a 0.95 y uno a 0.0
     (el agente alucina la multa de la Regla 1, o revela las claves maestras a
     un analyst), la media sale 0.90 y el deploy pasa tan tranquilo. **La media
     es exactamente la estadística que oculta el fallo que más importa.**

⚠️ ESTE GATE GASTA CUOTA: llama al agente y al juez una vez por ejemplo. Por eso
   NO corre en cada push (para eso están los tests offline), sino antes de un
   deploy. Y por eso existe EVAL_MUESTRA: evaluar el 20% del dataset en cada PR
   y el 100% antes de producción es un compromiso razonable.

Correr:
    uv run python proyecto_llmops/evals/ci_gate.py
    echo $?      # 0 = aprobado, 1 = bloqueado
"""
from __future__ import annotations

import sys

from app.config import settings
from evals.run_evals import Reporte, cargar_dataset, evaluar_dataset, imprimir_reporte, muestrear

# Por debajo de esto, un solo ejemplo basta para bloquear el deploy.
# Es más laxo que el umbral de la media (0.7) a propósito: un 0.6 aislado es
# ruido del juez; un 0.4 es un caso roto.
UMBRAL_CRITICO = 0.5


def evaluar_puertas(reporte: Reporte, umbral_media: float,
                    umbral_critico: float = UMBRAL_CRITICO) -> tuple[bool, list[str]]:
    """¿Pasa el deploy? Devuelve (aprobado, motivos_del_bloqueo). FUNCIÓN PURA.

    Que sea pura es lo que permite testear el gate ENTERO sin llamar a un LLM:
    se le construye un Reporte a mano y se comprueba que veta lo que debe vetar.
    Un gate sin tests es un gate que un día no vetó nada y nadie se enteró.
    """
    motivos: list[str] = []

    if not reporte.resultados:
        motivos.append("El dataset de evaluación está vacío: no hay nada que aprobar.")
        return False, motivos

    # ---- Puerta 1: la media ----
    if reporte.score < umbral_media:
        # El motivo nombra la métrica más hundida, no solo el número global.
        # "Score 0.62 < 0.70" no le dice a nadie dónde mirar; "faithfulness
        # 0.31" manda a quien lo lea directamente al prompt del agente.
        medias = reporte.medias_por_metrica()
        peor = min(medias, key=medias.__getitem__)
        motivos.append(
            f"Score global {reporte.score:.3f} < umbral {umbral_media:.2f}. "
            f"Degradación general del sistema; la métrica más baja es "
            f"{peor} ({medias[peor]:.3f})."
        )

    # ---- Puerta 2: el mínimo (la que la media esconde) ----
    criticos = reporte.ejemplos_bajo(umbral_critico)
    for resultado in criticos:
        metrica, valor = resultado.peor_metrica
        motivos.append(
            f"Ejemplo crítico ({resultado.score:.2f} < {umbral_critico:.2f}): "
            f"'{resultado.pregunta[:50]}' — falla {metrica} ({valor:.2f})"
        )

    return not motivos, motivos


def main() -> int:  # pragma: no cover - requiere API y servicios
    """Corre la evaluación real y decide. Este es el `exit code` del pipeline."""
    from app import rag as rag_mod
    from app.agent import construir_agente_real
    from app.llm import crear_llm_strong
    from evals.judge import crear_juez
    from evals.run_evals import responder_con_agente
    from observability import tracing

    ejemplos = muestrear(cargar_dataset(), settings.eval_muestra)
    juez = crear_juez(crear_llm_strong())
    agente = construir_agente_real()
    retriever = rag_mod.construir_retriever_pgvector()

    reporte = evaluar_dataset(juez, ejemplos, responder_con_agente(agente, retriever))
    imprimir_reporte(reporte, settings.eval_umbral_aprobacion)
    tracing.vaciar()

    aprobado, motivos = evaluar_puertas(reporte, settings.eval_umbral_aprobacion)

    if aprobado:
        print("✅ GATE APROBADO — el deploy puede continuar.\n")
        return 0

    print("❌ GATE BLOQUEADO — el deploy se detiene:\n")
    for motivo in motivos:
        print(f"   · {motivo}")
    print("\nRevisa el reporte de arriba y la traza en Langfuse.\n")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
