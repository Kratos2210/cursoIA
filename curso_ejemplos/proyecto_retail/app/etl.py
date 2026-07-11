"""
etl.py · El dato real nunca llega listo (la primera trampa del retail)
=======================================================================
FINALIDAD:
  Convertir un producto crudo del `products.json` de Shopify en la forma que usa
  el asistente. En el catálogo real de Sifrah, TODO llega sucio:
    - `price` es un STRING ("12.90"), no un número.
    - la promoción está escondida (compare_at_price > price).
    - `product_type` MIENTE: dice "Joyería" en los 250 productos, la mochila y el
      cepillo incluidos. La categoría de verdad hay que DERIVARLA del título+tags.

  ⭐ Esta es la lección que ningún tutorial con datos limpios da: el ETL no es
     burocracia — es la diferencia entre un asistente y un bochorno. Quien se lo
     salta termina comparando strings y clasificando mochilas como joyas.

  Es la misma lógica del módulo suelto `29_caso_retail.py`, aquí aislada en su
  propio módulo del paquete para poder testearla, evolucionarla y escalarla
  (ver docs/adr/0005-escalabilidad-embeddings-vector-db.md) por separado.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

# La categoría REAL se deriva del título+tags, no del product_type (que miente).
# Orden: la primera palabra clave que aparezca gana. "gancho"/"colet" van antes
# que "cabello" para que el cepillo (belleza) no se cuele como accesorio de cabello.
CATEGORIAS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("aretes",   ("arete", "argolla")),
    ("collares", ("collar", "dije")),
    ("anillos",  ("anillo",)),
    ("pulseras", ("pulsera",)),
    ("carteras", ("cartera", "bolso", "crossbody")),
    ("mochilas", ("mochila",)),
    ("cabello",  ("gancho", "colet", "accesorio de cabello", "clip")),
    ("belleza",  ("cepillo", "espejo", "belleza")),
)

# Las categorías válidas, para el molde tipado del m05 (ver app/intent.py).
NOMBRES_CATEGORIA: tuple[str, ...] = tuple(nombre for nombre, _ in CATEGORIAS)


def sin_tildes(texto: str) -> str:
    """'zircón' → 'zircon': compara sin tildes para que la búsqueda no dependa de
    si quien escribe acentúa (nadie acentúa en un chat)."""
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def derivar_categoria(texto_normalizado: str) -> str:
    """La categoría real, a partir del título+tags ya normalizados. PURA."""
    for nombre, claves in CATEGORIAS:
        if any(clave in texto_normalizado for clave in claves):
            return nombre
    return "otros"


def normalizar_producto(crudo: dict) -> dict:
    """ETL de UN producto: de la forma del endpoint a la forma del asistente.

    FUNCIÓN PURA → testeable byte a byte sin red ni cuota.
    """
    variante = crudo["variants"][0]
    precio = float(variante["price"])                      # "12.90" → 12.9
    antes = variante.get("compare_at_price")
    texto = sin_tildes(f"{crudo['title']} {' '.join(crudo['tags'])}".lower())

    return {
        "sku": variante["sku"],
        "titulo": crudo["title"],
        "categoria": derivar_categoria(texto),             # derivada, no confiada
        "precio": precio,
        "en_promo": antes is not None and float(antes) > precio,
        "disponible": bool(variante["available"]),
        "texto": texto,                                    # lo indexable
    }


def cargar_catalogo(crudos: list[dict]) -> list[dict]:
    """El catálogo normalizado desde una lista de productos crudos. Inyectable."""
    return [normalizar_producto(p) for p in crudos]


def cargar_catalogo_demo(ruta: Path | None = None) -> list[dict]:
    """El catálogo offline versionado (data/catalogo_demo.json), ya normalizado.

    Calca la FORMA del endpoint real con una docena de productos fijos, para que
    el pipeline entero corra sin red. Es lo que usan los tests y la demo.
    """
    if ruta is None:
        from proyecto_retail.app.config import settings
        ruta = settings.ruta_catalogo_demo
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return cargar_catalogo(datos["products"])
