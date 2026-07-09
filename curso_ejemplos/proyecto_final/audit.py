"""
audit.py · El molde del hallazgo y el rastro de auditoría
=========================================================
FINALIDAD:
  En una financiera, una decisión sin rastro no existe. Este módulo define
  QUÉ es un hallazgo (el molde Pydantic que el modelo debe rellenar) y
  CÓMO se deja constancia de él en un archivo de log.

LÓGICA (paso a paso):
  1) HallazgoCalidad: el molde. El modelo lo llena con with_structured_output.
  2) formatear_linea(): convierte un hallazgo en UNA línea de log. Es una
     función pura (mismo hallazgo -> misma línea), así que se testea sola.
  3) registrar_auditoria(): añade esa línea al archivo (modo 'append': nunca
     se sobrescribe lo ya auditado).
  4) leer_auditoria(): devuelve el historial.

  El único efecto sobre el disco está en (3). Todo lo demás es puro.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

import config

# Las tres severidades que aceptamos. Si el modelo inventa otra, la rechazamos.
SEVERIDADES = ("alta", "media", "baja")

# Formato de cada línea del log. Un separador '|' que no aparece en el texto.
SEPARADOR = " | "


class HallazgoCalidad(BaseModel):
    """Resultado de evaluar una regla de calidad de datos.

    Cada 'description' NO es un comentario: es la instrucción que lee el modelo
    para saber qué poner en ese campo. Si la borras, la extracción se degrada.
    """
    regla: str = Field(description="la regla evaluada")
    cumple: bool = Field(description="True si la normativa respalda la regla")
    severidad: str = Field(description="alta | media | baja")
    justificacion: str = Field(description="por qué, citando la normativa")

    @field_validator("severidad")
    @classmethod
    def normalizar_severidad(cls, valor: str) -> str:
        """El modelo a veces responde 'Alta' o ' ALTA '. Lo normalizamos.

        Y si devuelve algo que no es una severidad ('crítica'), fallamos aquí,
        cerca del origen, en vez de escribir basura en el log de auditoría.
        """
        limpio = valor.strip().lower()
        if limpio not in SEVERIDADES:
            raise ValueError(f"severidad debe ser una de {SEVERIDADES}, no {valor!r}")
        return limpio


def formatear_linea(hallazgo: HallazgoCalidad, momento: datetime) -> str:
    """Convierte un hallazgo en una línea de log. Función PURA (testeable).

    Recibe el 'momento' como parámetro en vez de llamar a datetime.now() por
    dentro: así un test puede fijar la fecha y comparar la línea exacta.

    Aplanamos los saltos de línea de la regla para que UNA línea del archivo
    sea siempre UN hallazgo (si no, el log deja de ser parseable).
    """
    regla = " ".join(hallazgo.regla.split())
    return SEPARADOR.join([
        f"{momento:%Y-%m-%d %H:%M:%S}",
        f"cumple={hallazgo.cumple}",
        f"severidad={hallazgo.severidad}",
        regla,
    ])


def registrar_auditoria(hallazgo: HallazgoCalidad, ruta=None, momento=None) -> str:
    """Añade el hallazgo al log de auditoría y devuelve la línea escrita.

    Modo 'a' (append): jamás se pisa un registro anterior. Un log de auditoría
    solo crece; borrarlo o reescribirlo es, literalmente, destruir evidencia.
    """
    ruta = ruta or config.RUTA_AUDITORIA
    linea = formatear_linea(hallazgo, momento or datetime.now())
    with open(ruta, "a", encoding="utf-8") as log:
        log.write(linea + "\n")
    return linea


def leer_auditoria(ruta=None) -> list[str]:
    """Devuelve las líneas del log (lista vacía si aún no existe)."""
    ruta = ruta or config.RUTA_AUDITORIA
    if not ruta.exists():
        return []
    return [l for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
