"""
loader.py · Prompts como código: cargar, validar y renderizar
==============================================================
FINALIDAD:
  Sacar los prompts del código Python y meterlos en YAML versionado. Un prompt
  hardcodeado dentro de una f-string es un prompt que nadie revisa en el PR,
  que no tiene versión, y que cuando falla no se puede correlacionar con nada.

  ⭐ El prompt es el archivo de configuración más importante de un sistema de
     IA, y en la mayoría de los proyectos es el único que no está versionado.

LÓGICA:
  - Prompt      : el molde. Nombre, versión, plantilla, variables, metadatos.
  - cargar()    : lee el .yaml y lo valida.
  - render()    : sustituye las variables con Jinja2.

⚠️ POR QUÉ JINJA2 Y NO f-strings NI str.format:
   El prompt tiene CONDICIONALES ({% if rol == "compliance" %}). Con `.format()`
   habría que montar el texto en Python, y volveríamos al punto de partida: la
   lógica del prompt viviendo en el código. Con Jinja2 el YAML se basta solo.

⚠️ POR QUÉ StrictUndefined:
   Por defecto, Jinja2 renderiza una variable que no existe como cadena VACÍA.
   Aplicado a un prompt, eso significa que un typo en `{{ rol }}` no da error:
   produce un prompt mutilado, el modelo responde algo plausible, y nadie se
   entera. `StrictUndefined` convierte ese silencio en una excepción.

Uso:
    from prompts.loader import cargar
    plantilla = cargar("agente_gobdata")
    texto = plantilla.render(rol="analyst")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined, TemplateError

# Un entorno de Jinja2, creado una vez. `StrictUndefined` es el ajuste que
# convierte un typo silencioso en un error ruidoso.
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
        """'agente_gobdata@v3'. Es lo que se manda a Langfuse y se cita en un
        incidente: sin él, "el prompt falló" no señala a ninguna versión."""
        return f"{self.nombre}@v{self.version}"

    def render(self, **valores) -> str:
        """Sustituye las variables. Falla si falta alguna o si sobra una.

        Las dos comprobaciones son distintas y las dos importan:
          - FALTA una → el prompt saldría mutilado. Error.
          - SOBRA una → o el YAML se quedó atrás, o quien llama se equivocó de
            prompt. En ambos casos alguien cree estar pasando un dato que el
            modelo nunca verá. Error también.
        """
        faltan = set(self.variables) - set(valores)
        if faltan:
            raise ValueError(
                f"{self.identificador}: faltan variables {sorted(faltan)}. "
                f"El YAML las declara en `variables:`."
            )
        sobran = set(valores) - set(self.variables)
        if sobran:
            raise ValueError(
                f"{self.identificador}: variables no declaradas {sorted(sobran)}. "
                f"Añádelas a `variables:` en el YAML o quítalas de la llamada."
            )

        try:
            return _ENTORNO.from_string(self.plantilla).render(**valores)
        except TemplateError as error:
            raise ValueError(f"{self.identificador}: plantilla inválida: {error}") from error


def _carpeta_por_defecto() -> Path:
    from app.config import settings
    return settings.ruta_prompts


def cargar(nombre: str, carpeta: Path | None = None) -> Prompt:
    """Lee `<carpeta>/<nombre>.yaml` y lo valida.

    Sin caché: en desarrollo quieres editar el YAML y ver el cambio sin
    reiniciar. En producción se carga una vez, al arrancar (ver `cargar_cacheado`).
    """
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

    # ⚠️ El nombre del archivo manda. Si el YAML dice otra cosa, alguien copió
    #    un prompt y olvidó renombrarlo: dos prompts distintos reportarían el
    #    mismo identificador a Langfuse y las métricas se mezclarían.
    if datos["nombre"] != nombre:
        raise ValueError(
            f"{ruta}: el campo `nombre: {datos['nombre']}` no coincide con el "
            f"archivo ({nombre}.yaml)."
        )

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
    """`cargar()` memoizado, para la app en producción.

    Leer y parsear un YAML en cada request es un desperdicio, y además haría que
    un despliegue a medias (archivo copiado a la mitad) rompiera requests vivas.
    """
    return cargar(nombre)


def listar(carpeta: Path | None = None) -> list[str]:
    """Los prompts disponibles. Útil en el runbook y para un test de humo."""
    carpeta = carpeta if carpeta is not None else _carpeta_por_defecto()
    return sorted(p.stem for p in carpeta.glob("*.yaml"))
