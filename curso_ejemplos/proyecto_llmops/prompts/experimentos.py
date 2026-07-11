"""
experimentos.py · A/B de prompts: bucketing determinista y PEGAJOSO por hash
=============================================================================
FINALIDAD:
  Repartir a los usuarios entre dos (o más) variantes de un prompt para poder
  COMPARARLAS con datos, no con opiniones. La variante A es el prompt actual; la
  B, una alternativa (más breve, otro tono, otra estructura). Cada usuario ve
  UNA de las dos, y el feedback 👍/👎 se agrega por variante (ver
  `observability/feedback.py`). Comparar la `tasa_aprobacion` entre A y B es el
  lazo A/B completo.

  ⭐ POR QUÉ PEGAJOSO (sticky). El MISMO `thread_id` debe caer SIEMPRE en la
     misma variante. Si en una request ve A y en la siguiente B, el usuario
     percibe un asistente que cambia de personalidad a mitad de conversación —y,
     peor, el experimento deja de medir nada: no sabrías a qué variante atribuir
     su voto. Pegajoso = la variante es una FUNCIÓN del `thread_id`, no un
     sorteo por request.

  ⭐ POR QUÉ POR HASH (y no un contador o `random`). El hash da tres cosas a la
     vez, y las tres importan en un servicio con varios workers:
       - REPRODUCIBLE: la misma clave da el mismo índice en cualquier proceso,
         sin compartir estado. Un contador `0,1,0,1…` exigiría coordinar los
         workers (un Redis, un lock); el hash no coordina con nadie.
       - SIN ESTADO: no hay que guardar "a quién le tocó qué". La asignación se
         RECALCULA a partir del `thread_id` cada vez.
       - UNIFORME: sha256 esparce las claves de forma pareja, así que el reparto
         entre variantes queda equilibrado sin esfuerzo.

LÓGICA:
  - asignar_variante(clave, variantes) : función PURA. hash(clave) → índice.
  - Experimento(nombre, variantes)     : empaqueta un experimento con nombre,
    para citarlo en trazas/feedback; `.variante_de(clave)` delega en la función.

Sin dependencias: `hashlib` es de la stdlib (y ya se usa en el curso, tema 24).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


def asignar_variante(clave: str, variantes: list[str]) -> str:
    """Devuelve, de forma DETERMINISTA y uniforme, la variante que le toca a `clave`.

    La misma `clave` (típicamente el `thread_id`) devuelve SIEMPRE la misma
    variante: por eso el experimento es pegajoso. FUNCIÓN PURA — no toca red, ni
    reloj, ni estado global; solo depende de sus argumentos.

    Cómo: sha256(clave) es un entero de 256 bits repartido de forma uniforme.
    Su módulo con el número de variantes da un índice pareado entre ellas. No se
    usa `hash()` de Python porque está aleatorizado por proceso (PYTHONHASHSEED):
    dos workers asignarían al mismo usuario variantes distintas, rompiendo la
    pegajosidad justo donde más importa —entre procesos.
    """
    if not variantes:
        raise ValueError("Se necesita al menos una variante para asignar.")
    digest = hashlib.sha256(clave.encode("utf-8")).hexdigest()
    # El hexdigest es un entero en base 16; su módulo reparte uniforme.
    indice = int(digest, 16) % len(variantes)
    return variantes[indice]


@dataclass(frozen=True)
class Experimento:
    """Un experimento A/B con nombre y sus variantes. Inmutable.

    El `nombre` existe para citar el experimento en una traza o en un voto
    ("prompt_conciso"), igual que el prompt tiene su `identificador`. Sin un
    nombre, "la variante B" no dice de qué experimento.
    """
    nombre: str
    variantes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.variantes:
            raise ValueError(f"El experimento '{self.nombre}' no tiene variantes.")

    def variante_de(self, clave: str) -> str:
        """La variante que le toca a `clave`. Pegajosa: misma clave, misma variante."""
        return asignar_variante(clave, list(self.variantes))
