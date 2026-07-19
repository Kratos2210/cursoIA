"""
fetch_catalogo.py · Bajar el catálogo REAL de Shopify (el ejercicio de verdad)
===============================================================================
FINALIDAD:
  El proyecto corre 100% offline con `data/catalogo_demo.json` (una docena de
  productos con la FORMA del endpoint real). Este script baja el catálogo REAL y
  lo normaliza con el MISMO ETL, para el ejercicio que enseña lo que ningún
  tutorial con datos limpios da: el dato real llega sucio y rompe cosas.

  ⭐ El ejercicio: corre esto, pasa el resultado por el pipeline y VERÁS fallar
     cosas — categorías nuevas que las reglas del ETL no conocen, títulos con
     formatos raros. Ajustar el ETL hasta que el eval vuelva a 100% ES el
     ejercicio (ver el módulo 29 del curso, caja "Para practicar").

⚠️ RESPETO AL ENDPOINT PÚBLICO. Una descarga puntual para aprender es razonable;
   scraping agresivo o uso comercial de datos ajenos, no. La regla del m23 aplica
   también a ti como consumidor de datos.

Correr:
    uv run python proyecto_retail/data/fetch_catalogo.py            # imprime un resumen
    uv run python proyecto_retail/data/fetch_catalogo.py --guardar  # lo deja en data/catalogo_real.json
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


def bajar_crudo(url: str) -> list[dict]:
    """Baja el products.json y devuelve la lista `products`. Requiere red."""
    with urllib.request.urlopen(url, timeout=30) as respuesta:  # noqa: S310 (URL del .env)
        datos = json.loads(respuesta.read().decode("utf-8"))
    return datos.get("products", [])


def main() -> int:  # pragma: no cover - requiere red
    from proyecto_retail.app.config import settings
    from proyecto_retail.app.etl import cargar_catalogo

    print(f"Bajando {settings.catalogo_url} …")
    crudos = bajar_crudo(settings.catalogo_url)
    catalogo = cargar_catalogo(crudos)

    otros = [p for p in catalogo if p["categoria"] == "otros"]
    print(f"\n{len(catalogo)} productos normalizados.")
    print(f"{sum(p['en_promo'] for p in catalogo)} en promo.")
    print(f"{len(otros)} cayeron en 'otros' (categorías que tu ETL aún no conoce):")
    for p in otros[:10]:
        print(f"  · {p['titulo']}")
    if otros:
        print("\n→ Ese es el ejercicio: enséñale esas categorías al ETL (app/etl.py).")

    if "--guardar" in sys.argv:
        destino = Path(__file__).parent / "catalogo_real.json"
        destino.write_text(json.dumps({"products": crudos}, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"\nGuardado el crudo en {destino} (úsalo con CATALOGO_FUENTE=live).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
