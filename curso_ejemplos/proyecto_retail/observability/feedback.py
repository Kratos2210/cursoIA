"""
feedback.py · El voto de la clienta, agregado por variante
===========================================================
FINALIDAD:
  Cerrar el lazo del A/B. `prompts/experimentos.py` reparte a las clientas entre
  variantes del prompt de la vendedora; aquí recogemos su 👍/👎 y lo AGREGAMOS
  POR VARIANTE. Comparar la `tasa_aprobacion` de A contra B es lo que decide el
  experimento (con suficientes votos, no con tres y una corazonada).

  ⭐ Un pulgar y no una nota de 1 a 5: una escala invita a pensar, un pulgar se
     pulsa. Más señal, menos fricción.

⚠️ EN MEMORIA, POR PROCESO: con varios workers cada uno acumula lo suyo. Sirve
   para el dashboard local y los tests; en producción el voto va a una tabla.
   (Espejo del feedback.py de proyecto_llmops.)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Voto:
    """Un voto sobre una respuesta. Inmutable. util=True es 👍; util=False, 👎."""
    variante: str
    util: bool
    thread_id: str = "demo"
    comentario: str | None = None


@dataclass
class ColectorFeedback:
    """Acumula Votos y los agrega por variante. En memoria, por proceso."""
    votos: list[Voto] = field(default_factory=list)

    def registrar(self, variante: str, util: bool, thread_id: str = "demo",
                  comentario: str | None = None) -> Voto:
        voto = Voto(variante=variante, util=util, thread_id=thread_id, comentario=comentario)
        self.votos.append(voto)
        return voto

    def resumen(self) -> dict:
        """Agrega por variante: 👍, 👎, total y tasa_aprobacion (👍/total)."""
        agregado: dict[str, dict] = {}
        for voto in self.votos:
            casilla = agregado.setdefault(
                voto.variante, {"util": 0, "no_util": 0, "total": 0, "tasa_aprobacion": 0.0})
            casilla["util" if voto.util else "no_util"] += 1
            casilla["total"] += 1
        for casilla in agregado.values():
            casilla["tasa_aprobacion"] = round(casilla["util"] / casilla["total"], 3)
        return agregado
