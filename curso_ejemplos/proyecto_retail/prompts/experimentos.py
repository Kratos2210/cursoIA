"""
experimentos.py · A/B de prompts: bucketing determinista y PEGAJOSO por hash
=============================================================================
FINALIDAD:
  Repartir a las clientas entre dos variantes del prompt de la vendedora para
  COMPARARLAS con datos, no con opiniones. Cada conversación ve UNA variante, y
  el feedback 👍/👎 se agrega por variante.

  ⭐ PEGAJOSO (sticky): el mismo `thread_id` cae SIEMPRE en la misma variante. Si
     cambiara por request, la clienta vería un asistente que cambia de
     personalidad a media charla y el voto no se podría atribuir.

  ⭐ POR HASH (no un contador ni random): reproducible entre workers sin estado
     compartido, y uniforme. `hash()` de Python se aleatoriza por proceso
     (PYTHONHASHSEED); sha256 no.

Sin dependencias: `hashlib` es de la stdlib (y ya se usa en el curso, tema 24).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


def asignar_variante(clave: str, variantes: list[str]) -> str:
    """La variante que le toca a `clave`, de forma determinista y uniforme. PURA."""
    if not variantes:
        raise ValueError("Se necesita al menos una variante para asignar.")
    digest = hashlib.sha256(clave.encode("utf-8")).hexdigest()
    indice = int(digest, 16) % len(variantes)
    return variantes[indice]


@dataclass(frozen=True)
class Experimento:
    """Un experimento A/B con nombre y sus variantes. Inmutable."""
    nombre: str
    variantes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.variantes:
            raise ValueError(f"El experimento '{self.nombre}' no tiene variantes.")

    def variante_de(self, clave: str) -> str:
        """La variante que le toca a `clave`. Pegajosa: misma clave, misma variante."""
        return asignar_variante(clave, list(self.variantes))
