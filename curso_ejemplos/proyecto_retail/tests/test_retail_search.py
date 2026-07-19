"""
test_retail_search.py · Filtros DUROS primero (precio, stock, categoría), ranking después.
"""
import pytest

from proyecto_retail.app.search import buscar_productos

pytestmark = pytest.mark.offline


def test_respeta_el_presupuesto(catalogo):
    r = buscar_productos({"presupuesto": 25.0, "categoria": "aretes", "color": None}, catalogo)
    assert r and all(p["precio"] <= 25.0 for p in r)


def test_excluye_lo_no_disponible(catalogo):
    """AR-003 (aretes zircón) está agotado: no debe recomendarse jamás."""
    r = buscar_productos({"presupuesto": None, "categoria": "aretes", "color": None}, catalogo)
    assert all(p["sku"] != "AR-003" for p in r)


def test_el_color_pedido_sube_al_primer_lugar(catalogo):
    r = buscar_productos({"presupuesto": 25.0, "categoria": "aretes", "color": "dorado"}, catalogo)
    assert "dorado" in r[0]["texto"]


def test_sin_candidatos_devuelve_vacio_no_inventa(catalogo):
    """'Nada cumple' es una respuesta válida; un sustituto fuera de presupuesto no."""
    r = buscar_productos({"presupuesto": 5.0, "categoria": "carteras", "color": None}, catalogo)
    assert r == []
