"""
feedback.py · El voto del usuario, agregado por variante
========================================================
FINALIDAD:
  Cerrar el lazo del A/B. El motor de `prompts/experimentos.py` reparte a los
  usuarios entre variantes; aquí recogemos su 👍/👎 y lo AGREGAMOS POR VARIANTE.
  El sentido del experimento es comparar la `tasa_aprobacion` de A contra la de
  B: sin un voto que atribuir a cada variante, el A/B no mide nada.

  ⭐ Por qué un pulgar y no una nota de 1 a 5. Una escala invita a pensar; un
     pulgar se pulsa. Más señal, menos fricción. Y para comparar dos variantes
     basta con "¿le sirvió?": la tasa de 👍 ya ordena A frente a B.

LÓGICA:
  - Voto            : el registro inmutable de UN voto (es un hecho pasado).
  - ColectorFeedback: registra votos y los agrega por variante. DÓNDE los guarda
                      lo decide el backend (memoria o Postgres), igual que
                      `ColectorMetricas`.

⚠️ CON EL BACKEND EN MEMORIA (el default) sigue vigente el aviso de siempre: con
   varios workers de uvicorn, cada uno acumula LOS SUYOS y ninguno ve el total.
   Sirve para un dashboard local y para los tests. Con `FEEDBACK_BACKEND=postgres`
   el voto va a una TABLA compartida, persiste entre despliegues y se puede
   decidir el ganador con SIGNIFICANCIA ESTADÍSTICA —no con tres votos y una
   corazonada—. Ver observability/feedback_backends.py y
   docs/adr/0006-ab-testing-y-feedback.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _backend_por_defecto():
    """El backend configurado. Import diferido para no crear un ciclo:
    `feedback_backends` importa `Voto`, que se define en este módulo."""
    from observability.feedback_backends import crear_backend
    return crear_backend()


@dataclass(frozen=True)
class Voto:
    """Un voto sobre una respuesta. Inmutable: es un hecho pasado.

    util=True es 👍; util=False es 👎. `variante` es a cuál de las variantes del
    A/B pertenece la respuesta votada (es lo que permite agregar por variante).
    `comentario` es opcional: texto libre para el "¿por qué?" cuando lo haya.
    """
    variante: str
    util: bool
    thread_id: str = "demo"
    comentario: str | None = None


@dataclass
class ColectorFeedback:
    """Registra Votos y los agrega por variante. Dónde los guarda lo decide el
    backend: en memoria (default) o en Postgres (`FEEDBACK_BACKEND=postgres`).

    Se inyecta en la app igual que `ColectorMetricas`: por parámetro, para poder
    darle uno limpio en cada test y no arrastrar estado entre ellos.
    """
    backend: object = field(default_factory=lambda: _backend_por_defecto())

    @property
    def votos(self) -> list[Voto]:
        """Los votos vigentes, vengan de donde vengan.

        Es una property y no una lista para que el colector no dependa de dónde
        estén guardados: la agregación de `resumen()` se escribe igual con
        memoria o con Postgres.
        """
        return list(self.backend.leer())

    def registrar(
        self,
        variante: str,
        util: bool,
        thread_id: str = "demo",
        comentario: str | None = None,
    ) -> Voto:
        """Anota un voto y lo devuelve. `util=True` es 👍; `util=False`, 👎."""
        voto = Voto(variante=variante, util=util, thread_id=thread_id, comentario=comentario)
        self.backend.registrar(voto)
        return voto

    def resumen(self) -> dict:
        """Agrega POR VARIANTE: 👍, 👎, total y `tasa_aprobacion` (👍/total).

        Devuelve un dict {variante: {util, no_util, total, tasa_aprobacion}}.
        Comparar la `tasa_aprobacion` entre variantes es el resultado del A/B.
        Una variante sin votos tiene tasa 0.0 (no se divide entre cero).
        """
        agregado: dict[str, dict] = {}
        for voto in self.votos:
            casilla = agregado.setdefault(
                voto.variante, {"util": 0, "no_util": 0, "total": 0, "tasa_aprobacion": 0.0}
            )
            casilla["util" if voto.util else "no_util"] += 1
            casilla["total"] += 1
        for casilla in agregado.values():
            # tasa_aprobacion = 👍 / total. Es la métrica que ordena A frente a B.
            casilla["tasa_aprobacion"] = round(casilla["util"] / casilla["total"], 3)
        return agregado
