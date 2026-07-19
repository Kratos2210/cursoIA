"""
retail_metric.py · La misma métrica para el honesto y el descuidado (m16)
==========================================================================
FINALIDAD:
  Convertir "creo que va mejor" en un número comparable entre commits. Un caso
  APRUEBA solo si TODO lo recomendado:
    - respeta el presupuesto de la petición,
    - está disponible (stock), y
    - no cita precios fuera del catálogo recuperado (fidelidad, el price_guard).

  ⭐ Es el ritual del m16 en versión retail: la MISMA métrica juzga al asistente
     honesto (filtros duros + grounding) y al descuidado (ignora el presupuesto).
     Si un cambio baja la nota, es una regresión — y sin eval, a la regresión la
     atrapa un cliente.

  `responder` entra POR PARÁMETRO: por eso se evalúa el agente real, la maqueta o
  un ModeloFalso con la misma función.
"""
from __future__ import annotations

from dataclasses import dataclass

from proyecto_retail.app.intent import extraer_filtros_regla
from proyecto_retail.guardrails.price_guard import respuesta_es_fiel


@dataclass(frozen=True)
class ResultadoCaso:
    """El veredicto de un caso: qué respetó y qué no."""
    peticion: str
    respeta_presupuesto: bool
    respeta_stock: bool
    fiel: bool
    n_productos: int

    @property
    def aprobado(self) -> bool:
        return self.respeta_presupuesto and self.respeta_stock and self.fiel

    @property
    def motivo_fallo(self) -> str:
        fallos = []
        if not self.respeta_presupuesto:
            fallos.append("presupuesto")
        if not self.respeta_stock:
            fallos.append("stock")
        if not self.fiel:
            fallos.append("precio inventado")
        return ", ".join(fallos) or "—"


def evaluar_caso(peticion: str, responder, catalogo: list[dict]) -> ResultadoCaso:
    """Corre el asistente sobre una petición y verifica las tres reglas. PURA
    respecto a `responder` (lo que sea que se le inyecte)."""
    productos, texto = responder(peticion, catalogo)
    presupuesto = extraer_filtros_regla(peticion)["presupuesto"]
    respeta_precio = (all(p["precio"] <= presupuesto for p in productos)
                      if presupuesto is not None else True)
    return ResultadoCaso(
        peticion=peticion,
        respeta_presupuesto=respeta_precio,
        respeta_stock=all(p["disponible"] for p in productos),
        fiel=respuesta_es_fiel(texto, productos),
        n_productos=len(productos),
    )


@dataclass
class Reporte:
    """El resultado de evaluar todo el dataset."""
    resultados: list[ResultadoCaso]

    @property
    def score(self) -> float:
        """Fracción de casos aprobados. El número del CI gate."""
        if not self.resultados:
            return 0.0
        return sum(1 for r in self.resultados if r.aprobado) / len(self.resultados)

    def fallidos(self) -> list[ResultadoCaso]:
        return [r for r in self.resultados if not r.aprobado]


def evaluar_dataset(peticiones: list[str], responder, catalogo: list[dict]) -> Reporte:
    """Evalúa cada petición con la métrica. Devuelve un Reporte."""
    return Reporte([evaluar_caso(p, responder, catalogo) for p in peticiones])
