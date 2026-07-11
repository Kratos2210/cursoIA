"""
test_retail_evals.py · La métrica retail, el runner y el CI gate. Sin cuota.
"""
import pytest

from proyecto_retail.app.agent import armar_respuesta
from proyecto_retail.app.intent import extraer_filtros_regla
from proyecto_retail.app.search import buscar_productos
from proyecto_retail.evals import ci_gate, run_evals
from proyecto_retail.evals.retail_metric import Reporte, ResultadoCaso, evaluar_dataset

pytestmark = pytest.mark.offline


def _honesto(peticion, catalogo):
    """El asistente honesto: filtros duros + respuesta determinista (fiel)."""
    productos = buscar_productos(extraer_filtros_regla(peticion), catalogo)
    return productos, armar_respuesta(productos)


def _descuidado(peticion, catalogo):
    """El anti-ejemplo: ignora el presupuesto (recomienda lo más caro que haya)."""
    filtros = extraer_filtros_regla(peticion)
    filtros["presupuesto"] = None
    productos = sorted(buscar_productos(filtros, catalogo, k=2),
                       key=lambda p: p["precio"], reverse=True)
    return productos, armar_respuesta(productos)


CASOS = [
    "aretes dorados por menos de 25 soles",
    "un collar hasta S/35",
    "algo para el pelo, máximo 8 soles",
    "una cartera hasta S/80",
]


def test_el_honesto_aprueba_todo(catalogo):
    assert evaluar_dataset(CASOS, _honesto, catalogo).score == 1.0


def test_la_metrica_atrapa_al_descuidado(catalogo):
    assert evaluar_dataset(CASOS, _descuidado, catalogo).score < 1.0


def test_el_dataset_versionado_carga_y_evalua(catalogo):
    """El dataset.jsonl real, con el asistente honesto, sale 100%."""
    casos = run_evals.cargar_dataset()
    assert len(casos) >= 8
    reporte = run_evals.evaluar_casos(casos, _honesto, catalogo)
    assert reporte.score == 1.0


def test_muestreo_es_reproducible():
    casos = run_evals.cargar_dataset()
    assert run_evals.muestrear(casos, 0.5) == run_evals.muestrear(casos, 0.5)


class TestGate:
    def test_aprueba_cuando_todo_es_fiel(self):
        reporte = Reporte([ResultadoCaso("x", True, True, True, 1)])
        aprobado, motivos = ci_gate.evaluar_puertas(reporte, 0.9)
        assert aprobado is True and motivos == []

    def test_un_precio_inventado_bloquea_aunque_la_media_pase(self):
        """9 casos perfectos y uno infiel: la media es 0.90 pero el gate veta."""
        reporte = Reporte([ResultadoCaso(f"ok{i}", True, True, True, 1) for i in range(9)]
                          + [ResultadoCaso("infiel", True, True, False, 1)])
        aprobado, motivos = ci_gate.evaluar_puertas(reporte, 0.9)
        assert aprobado is False
        assert any("PRECIO INVENTADO" in m for m in motivos)

    def test_dataset_vacio_no_aprueba(self):
        aprobado, _ = ci_gate.evaluar_puertas(Reporte([]), 0.9)
        assert aprobado is False
