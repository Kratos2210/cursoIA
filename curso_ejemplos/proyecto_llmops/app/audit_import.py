"""
audit_import.py · Puente al molde HallazgoCalidad de proyecto_final
===================================================================
FINALIDAD:
  Reutilizar el molde Pydantic `HallazgoCalidad` que YA existe y está testeado
  en `proyecto_final/audit.py`, en vez de duplicarlo. El DRY (Don't Repeat
  Yourself) también aplica a los modelos de datos.

  El proyecto LLMOps no redefine qué es un hallazgo: es el MISMO concepto del
  prototipo. Si mañana evoluciona (p.ej. añadir un campo 'evidencia'), cambia
  en un sitio y ambos proyectos se benefician.

LÓGICA:
  Exposición PEREZOSA de verdad, con `__getattr__` a nivel de módulo (PEP 562):
  el molde se carga la primera vez que alguien escribe `audit_import.HallazgoCalidad`,
  no al importar este archivo.

  ¿Por qué importa? Porque cargar el módulo del prototipo arrastra sus imports.
  Un test que solo quiere comprobar el RBAC no debería pagar ese coste.
"""
from __future__ import annotations

from typing import Any

# Nombres que este módulo sabe resolver perezosamente.
_PEREZOSOS = ("HallazgoCalidad", "registrar_auditoria", "leer_auditoria", "formatear_linea")


def __getattr__(nombre: str) -> Any:
    """Se ejecuta SOLO cuando el atributo no existe ya en el módulo (PEP 562).

    Python lo llama la primera vez; después, el valor queda cacheado en el
    diccionario del módulo y este `__getattr__` no vuelve a entrar.
    """
    if nombre not in _PEREZOSOS:
        raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")

    from app._proyecto_final import audit   # el puente resuelve el sys.path

    valor = getattr(audit, nombre)
    globals()[nombre] = valor               # cachea: la próxima vez no pasa por aquí
    return valor


def __dir__() -> list[str]:
    """Para que autocompletado e `inspect` vean los nombres perezosos."""
    return sorted([*globals().keys(), *_PEREZOSOS])
