"""
test_retail_etl.py · El ETL: del products.json crudo a un producto usable.
"""
import pytest

from proyecto_retail.app import etl

pytestmark = pytest.mark.offline


def test_el_precio_string_se_vuelve_float(catalogo):
    assert all(isinstance(p["precio"], float) for p in catalogo)


def test_promo_cuando_compare_at_es_mayor():
    con = etl.normalizar_producto({
        "title": "X", "product_type": "Joyería", "tags": [],
        "variants": [{"sku": "T-1", "price": "12.90", "compare_at_price": "39.90", "available": True}]})
    sin = etl.normalizar_producto({
        "title": "X", "product_type": "Joyería", "tags": [],
        "variants": [{"sku": "T-2", "price": "12.90", "compare_at_price": None, "available": True}]})
    assert con["en_promo"] is True
    assert sin["en_promo"] is False


def test_la_categoria_se_deriva_no_se_confia():
    """product_type dice 'Joyería' hasta en la mochila; la categoría real sale
    del título+tags."""
    mochila = etl.normalizar_producto({
        "title": "Mochila 2 en 1 Travel Fucsia", "product_type": "Joyería",
        "tags": ["Mochila"],
        "variants": [{"sku": "T-3", "price": "12.90", "compare_at_price": None, "available": True}]})
    assert mochila["categoria"] == "mochilas"          # NO "joyería"


def test_el_cepillo_es_belleza_no_cabello(catalogo):
    """'Cepillo de Cabello' contiene 'cabello', pero su categoría real es belleza:
    el orden de las reglas del ETL importa."""
    cepillo = next(p for p in catalogo if p["sku"] == "BE-001")
    assert cepillo["categoria"] == "belleza"


def test_el_catalogo_demo_tiene_doce_productos(catalogo):
    assert len(catalogo) == 12
