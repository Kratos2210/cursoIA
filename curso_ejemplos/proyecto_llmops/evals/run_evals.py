"""
run_evals.py · Correr la tríada sobre el dataset versionado
============================================================
FINALIDAD:
  Convertir "creo que va mejor" en un número comparable entre commits. Se carga
  el dataset (`dataset.jsonl`), se le pide una respuesta al sistema para cada
  pregunta, y un juez puntúa las tres métricas de la tríada.

  ⭐ EL DATASET ES CÓDIGO. Vive en el repo, se versiona con git y se revisa en
     los PRs. Cuando alguien añade un caso que el agente falla, ese caso queda
     para siempre: es un test de regresión escrito en lenguaje natural.

LÓGICA:
  - cargar_dataset()  : lee el .jsonl (una línea = un ejemplo = un JSON).
  - muestrear()       : coge una fracción REPRODUCIBLE (ver abajo).
  - evaluar_dataset() : para cada ejemplo → responder() → tríada → resultado.
  - Reporte           : media, peor ejemplo y desglose por categoría.

  `responder` entra POR PARÁMETRO. Por eso los tests evalúan el dataset entero
  con un juez falso y un respondedor falso, sin cuota y en milisegundos.

⚠️ POR QUÉ EL MUESTREO ES DETERMINISTA. Con `random.sample`, dos ejecuciones del
   CI sobre el MISMO commit evalúan ejemplos distintos y dan scores distintos.
   Un gate que parpadea se acaba desactivando. Aquí el subconjunto se elige por
   el hash del `id`: mismo dataset y misma fracción → mismos ejemplos, siempre,
   en cualquier máquina.

Correr:
    uv run python proyecto_llmops/evals/run_evals.py            # dataset entero
    EVAL_MUESTRA=0.3 uv run python proyecto_llmops/evals/run_evals.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from evals.rag_triad import ResultadoTriada, evaluar_triada


@dataclass(frozen=True)
class Ejemplo:
    """Una fila del dataset."""
    id: str
    pregunta: str
    respuesta_esperada: str
    contexto: str
    rol: str = "analyst"
    categoria: str = "general"


def cargar_dataset(ruta: Path | None = None) -> list[Ejemplo]:
    """Lee el .jsonl. Una línea = un JSON = un ejemplo.

    JSONL y no un JSON gigante porque así `git diff` muestra qué ejemplo cambió,
    en vez de reindentar el archivo entero.
    """
    if ruta is None:
        from app.config import settings
        ruta = settings.ruta_dataset

    ejemplos = []
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("//"):
            continue
        try:
            ejemplos.append(Ejemplo(**json.loads(linea)))
        except (json.JSONDecodeError, TypeError) as error:
            # Un dataset roto debe fallar RUIDOSAMENTE. Saltarse la línea mala
            # en silencio significa evaluar menos casos de los que crees.
            raise ValueError(f"{ruta}:{numero} — línea inválida: {error}") from error
    return ejemplos


def muestrear(ejemplos: list[Ejemplo], fraccion: float) -> list[Ejemplo]:
    """Una fracción REPRODUCIBLE del dataset, elegida por el hash del `id`.

    Con fraccion >= 1.0 devuelve todo. Con 0.2, el 20% — siempre los MISMOS,
    en cualquier máquina y en cualquier ejecución. Un CI que evalúa ejemplos
    distintos cada vez no mide regresiones: mide el azar.

    md5 no se usa aquí como función criptográfica, sino como hash estable entre
    versiones de Python (el `hash()` de Python se aleatoriza en cada proceso).
    """
    if fraccion >= 1.0:
        return list(ejemplos)
    if fraccion <= 0.0:
        return []

    cuantos = max(1, round(len(ejemplos) * fraccion))
    ordenados = sorted(ejemplos, key=lambda e: hashlib.md5(e.id.encode()).hexdigest())
    return ordenados[:cuantos]


@dataclass
class Reporte:
    """El resultado de una evaluación completa."""
    resultados: list[ResultadoTriada]

    @property
    def score(self) -> float:
        """La media de las medias. El número del CI gate."""
        if not self.resultados:
            return 0.0
        return sum(r.score for r in self.resultados) / len(self.resultados)

    @property
    def peor(self) -> ResultadoTriada | None:
        """El ejemplo con peor score. Por donde se empieza a depurar."""
        return min(self.resultados, key=lambda r: r.score, default=None)

    def medias_por_metrica(self) -> dict[str, float]:
        """La media de cada métrica por separado. AQUÍ está el diagnóstico.

        Si `context_precision` es la baja, el problema es el retriever y no hay
        prompt que lo arregle. Ver la explicación en rag_triad.py.
        """
        if not self.resultados:
            return {"faithfulness": 0.0, "answer_relevance": 0.0, "context_precision": 0.0}
        n = len(self.resultados)
        return {
            "faithfulness": sum(r.faithfulness.puntuacion for r in self.resultados) / n,
            "answer_relevance": sum(r.answer_relevance.puntuacion for r in self.resultados) / n,
            "context_precision": sum(r.context_precision.puntuacion for r in self.resultados) / n,
        }

    def ejemplos_bajo(self, umbral: float) -> list[ResultadoTriada]:
        """Los ejemplos que no llegan al umbral. La media puede esconderlos."""
        return [r for r in self.resultados if r.score < umbral]


def evaluar_dataset(juez, ejemplos: list[Ejemplo], responder=None) -> Reporte:
    """Evalúa cada ejemplo con la tríada.

    responder: callable(pregunta, rol) -> (respuesta, contexto).
               Si es None, se usa `respuesta_esperada` y `contexto` del propio
               dataset. Eso mide **al juez**, no al sistema: sirve para calibrar
               la rúbrica (una respuesta buena debe sacar ~1.0), no para evaluar
               el agente. No lo confundas con una evaluación de verdad.
    """
    resultados = []
    for ejemplo in ejemplos:
        if responder is None:
            respuesta, contexto = ejemplo.respuesta_esperada, ejemplo.contexto
        else:
            respuesta, contexto = responder(ejemplo.pregunta, ejemplo.rol)

        resultados.append(evaluar_triada(juez, ejemplo.pregunta, respuesta, contexto))
    return Reporte(resultados)


def responder_con_agente(agente, retriever):
    """Fábrica del `responder` de verdad: pregunta al agente y captura su contexto.

    Devuelve el callable que espera `evaluar_dataset`. Se separa así porque
    construir el agente es caro y esta función no debe hacerlo: la recibe hecha.
    """
    from app import rag as rag_mod

    def responder(pregunta: str, rol: str) -> tuple[str, str]:
        # El MISMO contexto que verá el agente, filtrado por el MISMO rol.
        # Evaluar con un contexto distinto del que usó el modelo mide otra cosa.
        contexto = rag_mod.recuperar(retriever, pregunta, rol=rol)
        salida = agente.invoke(
            {"messages": [("user", pregunta)]},
            config={"configurable": {"thread_id": f"eval-{rol}"}},
        )
        return salida["messages"][-1].content, contexto

    return responder


def imprimir_reporte(reporte: Reporte, umbral: float) -> None:
    """El informe que se lee en la consola del CI."""
    print("\n" + "=" * 62)
    print(f"  EVALUACIÓN — {len(reporte.resultados)} ejemplos")
    print("=" * 62)

    for resultado in reporte.resultados:
        marca = "✅" if resultado.score >= umbral else "❌"
        metrica, valor = resultado.peor_metrica
        print(f"{marca} {resultado.score:.2f}  {resultado.pregunta[:46]:<46} "
              f"(peor: {metrica} {valor:.2f})")

    print("-" * 62)
    for nombre, media in reporte.medias_por_metrica().items():
        print(f"  {nombre:<20} {media:.3f}")
    print(f"  {'SCORE GLOBAL':<20} {reporte.score:.3f}   (umbral {umbral:.2f})")
    print("=" * 62 + "\n")


def main() -> int:  # pragma: no cover - requiere API y servicios
    """Evalúa el sistema REAL. Gasta cuota: llama al agente y al juez."""
    from app.agent import construir_agente_real
    from app.config import settings
    from app.llm import crear_llm_strong
    from evals.judge import crear_juez
    from observability import tracing

    ejemplos = muestrear(cargar_dataset(), settings.eval_muestra)
    if not ejemplos:
        print("⚠️  El dataset está vacío (o EVAL_MUESTRA=0).")
        return 1

    # ⭐ El juez usa el modelo FUERTE aunque el agente use el barato: quien
    #    corrige el examen debe saber más que quien lo hace. Y a temperatura 0,
    #    para que dos ejecuciones del CI den el mismo veredicto.
    juez = crear_juez(crear_llm_strong())

    agente = construir_agente_real()
    from app import rag as rag_mod
    retriever = rag_mod.construir_retriever_pgvector()

    reporte = evaluar_dataset(juez, ejemplos, responder_con_agente(agente, retriever))
    imprimir_reporte(reporte, settings.eval_umbral_aprobacion)

    # Las trazas viven en un buffer que se vacía en un hilo de fondo. Un script
    # que termina sin esto pierde en silencio la traza de la evaluación entera.
    tracing.vaciar()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
