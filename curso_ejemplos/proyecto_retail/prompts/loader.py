"""
loader.py · Prompts como código: cargar, validar y renderizar
==============================================================
FINALIDAD:
  Sacar los prompts del código y meterlos en YAML versionado. Un prompt
  hardcodeado en una f-string es un prompt que nadie revisa en el PR, que no
  tiene versión, y que cuando falla no se puede correlacionar con nada.

  ⭐ El prompt es el archivo de configuración más importante de un sistema de IA,
     y en la mayoría de los proyectos es el único que no está versionado.

⚠️ StrictUndefined: por defecto Jinja2 renderiza una variable inexistente como
   cadena vacía. En un prompt, un typo en `{{ tono }}` produciría un prompt
   mutilado en silencio. StrictUndefined convierte ese silencio en una excepción.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined, TemplateError

_ENTORNO = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


@dataclass(frozen=True)
class Prompt:
    """Un prompt versionado, listo para renderizar."""
    nombre: str
    version: int
    plantilla: str
    variables: tuple[str, ...] = ()
    descripcion: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def identificador(self) -> str:
        """'vendedora@v2'. Lo que se cita en un incidente: sin él, 'el prompt
        falló' no señala a ninguna versión."""
        return f"{self.nombre}@v{self.version}"

    def render(self, **valores) -> str:
        """Sustituye las variables. Falla si falta alguna o si sobra una."""
        faltan = set(self.variables) - set(valores)
        if faltan:
            raise ValueError(
                f"{self.identificador}: faltan variables {sorted(faltan)}. "
                f"El YAML las declara en `variables:`.")
        sobran = set(valores) - set(self.variables)
        if sobran:
            raise ValueError(
                f"{self.identificador}: variables no declaradas {sorted(sobran)}.")
        try:
            return _ENTORNO.from_string(self.plantilla).render(**valores)
        except TemplateError as error:
            raise ValueError(f"{self.identificador}: plantilla inválida: {error}") from error


def _carpeta_por_defecto() -> Path:
    from proyecto_retail.app.config import settings
    return settings.ruta_prompts


def cargar(nombre: str, carpeta: Path | None = None) -> Prompt:
    """Lee `<carpeta>/<nombre>.yaml` y lo valida."""
    carpeta = carpeta if carpeta is not None else _carpeta_por_defecto()
    ruta = carpeta / f"{nombre}.yaml"
    if not ruta.exists():
        disponibles = ", ".join(sorted(p.stem for p in carpeta.glob("*.yaml"))) or "ninguno"
        raise FileNotFoundError(f"No existe el prompt '{nombre}' en {carpeta}. Hay: {disponibles}")

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta}: el YAML debe ser un diccionario en la raíz.")
    for campo in ("nombre", "version", "plantilla"):
        if campo not in datos:
            raise ValueError(f"{ruta}: falta el campo obligatorio '{campo}'.")
    # El nombre del archivo manda: si el YAML dice otra cosa, alguien copió un
    # prompt y olvidó renombrarlo, y las métricas de las dos variantes se mezclarían.
    if datos["nombre"] != nombre:
        raise ValueError(
            f"{ruta}: el campo `nombre: {datos['nombre']}` no coincide con el "
            f"archivo ({nombre}.yaml).")

    return Prompt(
        nombre=datos["nombre"],
        version=int(datos["version"]),
        plantilla=datos["plantilla"],
        variables=tuple(datos.get("variables", ())),
        descripcion=datos.get("descripcion", ""),
        metadata=datos.get("metadata", {}),
    )


@lru_cache
def cargar_cacheado(nombre: str) -> Prompt:
    """`cargar()` memoizado, para la app en producción."""
    return cargar(nombre)


def listar(carpeta: Path | None = None) -> list[str]:
    """Los prompts disponibles. Útil en el runbook y en un test de humo."""
    carpeta = carpeta if carpeta is not None else _carpeta_por_defecto()
    return sorted(p.stem for p in carpeta.glob("*.yaml"))
