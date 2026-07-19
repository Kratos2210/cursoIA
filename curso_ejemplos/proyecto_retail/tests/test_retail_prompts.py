"""
test_retail_prompts.py · Prompts como código y A/B pegajoso. Sin cuota.
"""
import pytest

from proyecto_retail.prompts import experimentos, loader

pytestmark = pytest.mark.offline


class TestLoader:
    def test_carga_las_dos_variantes(self):
        assert set(loader.listar()) >= {"vendedora", "vendedora_directa"}

    def test_render_inyecta_los_productos(self):
        prompt = loader.cargar("vendedora")
        texto = prompt.render(productos="- Aretes a S/19.90")
        assert "S/19.90" in texto

    def test_render_falla_si_falta_una_variable(self):
        with pytest.raises(ValueError):
            loader.cargar("vendedora").render()

    def test_render_falla_si_sobra_una_variable(self):
        with pytest.raises(ValueError):
            loader.cargar("vendedora").render(productos="x", color="dorado")

    def test_el_identificador_lleva_version(self):
        assert loader.cargar("vendedora").identificador == "vendedora@v2"


class TestExperimentoAB:
    def test_es_pegajoso(self):
        exp = experimentos.Experimento("t", ("vendedora", "vendedora_directa"))
        assert exp.variante_de("hilo-42") == exp.variante_de("hilo-42")

    def test_reparte_entre_variantes(self):
        exp = experimentos.Experimento("t", ("a", "b"))
        vistas = {exp.variante_de(f"hilo-{i}") for i in range(50)}
        assert vistas == {"a", "b"}

    def test_es_reproducible_entre_procesos(self):
        """No usa hash() de Python (aleatorio por proceso): un valor fijo conocido."""
        exp = experimentos.Experimento("t", ("a", "b"))
        assert exp.variante_de("web-123") == exp.variante_de("web-123")
