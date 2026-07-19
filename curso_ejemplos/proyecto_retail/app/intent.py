"""
intent.py · De la frase a filtros tipados (el m05, no un regex)
================================================================
FINALIDAD:
  "Quiero aretes dorados por menos de 25 soles" son TRES filtros disfrazados de
  frase: categoría, color, presupuesto. Este módulo los extrae.

  ⭐ La lección del caso: subir un eslabón de nivel NO reescribe el pipeline. Hay
     DOS implementaciones con la MISMA interfaz (petición → dict de filtros):
       - extraer_filtros_regla(): determinista, sin cuota. Para tests byte a byte
         y como FALLBACK cuando no hay LLM.
       - extraer_filtros_llm():   el m05 de verdad, `with_structured_output`.
         Entiende "algo lindo pa mi flaca, unos 30 lucas" mucho mejor que un regex.
     Como devuelven el mismo dict, `app/search.py` no cambia al subir de nivel.
"""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from proyecto_retail.app.etl import CATEGORIAS, sin_tildes

# ---- El molde tipado (m05) ----
# El LLM elige entre un conjunto CERRADO de categorías; no inventa una etiqueta.
Categoria = Literal[
    "aretes", "collares", "anillos", "pulseras",
    "carteras", "mochilas", "cabello", "belleza",
]


class FiltrosCompra(BaseModel):
    """La petición de la clienta, convertida en tres filtros tipados.

    `llm.with_structured_output(FiltrosCompra)` obliga al modelo a rellenarlo y
    devuelve un objeto validado, no un texto que parsear y rezar.
    """
    presupuesto: Optional[float] = Field(
        default=None,
        description="Tope de precio en soles si lo menciona ('menos de 25', "
                    "'hasta S/80'); None si no dice cifra.")
    categoria: Optional[Categoria] = Field(
        default=None,
        description="Tipo de producto, mapeado a una categoría válida. 'aros' → "
                    "aretes, 'cadena' → collares, 'algo para el pelo' → cabello. "
                    "None si no se puede inferir.")
    color: Optional[str] = Field(
        default=None,
        description="Color pedido en minúsculas (dorado, plateado, negro, "
                    "fucsia, rosa); None si no menciona color.")

    def a_dict(self) -> dict:
        """El dict que consume `app/search.py`. La interfaz común a ambas vías."""
        return {"presupuesto": self.presupuesto,
                "categoria": self.categoria, "color": self.color}


# ------------------------------------------------------------------
# Vía 1 · Reglas deterministas (fallback, y para tests sin cuota)
# ------------------------------------------------------------------
_RE_PRESUPUESTO = re.compile(
    r"(?:menos de|hasta|maximo|no mas de|tope de)\s*s?/?\.?\s*(\d+(?:\.\d+)?)")

_COLORES = ("dorado", "plateado", "negro", "fucsia", "rosa")

# La clienta no habla como el catálogo: "aros", "pelo", "cadena". Estos sinónimos
# SOLO aplican a la petición (al producto no: "cabello" clasificaría el cepillo).
_SINONIMOS_PETICION = {
    "aretes":   ("aros", "pendiente"),
    "collares": ("cadena",),
    "cabello":  ("cabello", "pelo"),
}


def extraer_filtros_regla(peticion: str) -> dict:
    """De la frase a filtros con reglas + regex. FUNCIÓN PURA → test byte a byte."""
    texto = sin_tildes(peticion.lower())
    filtros: dict = {"presupuesto": None, "categoria": None, "color": None}

    if (m := _RE_PRESUPUESTO.search(texto)):
        filtros["presupuesto"] = float(m.group(1))

    for nombre, claves in CATEGORIAS:
        claves_peticion = claves + _SINONIMOS_PETICION.get(nombre, ())
        if any(clave in texto for clave in claves_peticion):
            filtros["categoria"] = nombre
            break

    for color in _COLORES:
        if color in texto:
            filtros["color"] = color
            break

    return filtros


# ------------------------------------------------------------------
# Vía 2 · El LLM (el m05 de verdad)
# ------------------------------------------------------------------
def extraer_filtros_llm(llm, peticion: str) -> dict:
    """De la frase a filtros tipados con el LLM. Devuelve el MISMO dict que la
    vía de reglas, así el resto del pipeline no se entera de cuál se usó."""
    extractor = llm.with_structured_output(FiltrosCompra)
    filtros: FiltrosCompra = extractor.invoke(
        "Extrae los filtros de compra de esta petición de una clienta de una "
        f"tienda de bisutería y accesorios: «{peticion}»")
    return filtros.a_dict()
