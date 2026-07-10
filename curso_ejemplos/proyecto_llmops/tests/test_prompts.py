"""
test_prompts.py · El prompt es código, y el código se testea
=============================================================
Un prompt roto no lanza una excepción: produce una respuesta plausible y
equivocada. Por eso lo que aquí se comprueba no es "el modelo responde bien"
(eso lo mide `evals/`), sino que el prompt **llega entero al modelo**:

  · que ninguna variable se quede sin sustituir en silencio,
  · que las condicionales por rol se rendericen como toca,
  · que el prompt real del repo declare lo que usa.
"""
import pytest

from prompts import loader

pytestmark = pytest.mark.offline


@pytest.fixture
def carpeta_yaml(tmp_path):
    """Un prompt mínimo, escrito a mano, para probar el loader."""
    (tmp_path / "saludo.yaml").write_text(
        "nombre: saludo\n"
        "version: 2\n"
        "variables:\n"
        "  - nombre\n"
        "plantilla: |\n"
        "  Hola {{ nombre }}.\n"
        "  {% if nombre == 'jefe' %}Un placer.{% endif %}\n",
        encoding="utf-8",
    )
    return tmp_path


class TestCargar:
    def test_lee_los_campos(self, carpeta_yaml):
        prompt = loader.cargar("saludo", carpeta_yaml)
        assert prompt.version == 2
        assert prompt.variables == ("nombre",)

    def test_el_identificador_cita_la_version(self, carpeta_yaml):
        # 'saludo@v2' es lo que se manda a Langfuse. Sin él, "el prompt falló"
        # no señala a ninguna versión concreta.
        assert loader.cargar("saludo", carpeta_yaml).identificador == "saludo@v2"

    def test_un_prompt_inexistente_dice_cuales_hay(self, carpeta_yaml):
        with pytest.raises(FileNotFoundError, match="saludo"):
            loader.cargar("no_existe", carpeta_yaml)

    def test_falta_un_campo_obligatorio(self, tmp_path):
        (tmp_path / "malo.yaml").write_text("nombre: malo\nversion: 1\n", encoding="utf-8")
        with pytest.raises(ValueError, match="plantilla"):
            loader.cargar("malo", tmp_path)

    def test_el_nombre_debe_coincidir_con_el_archivo(self, tmp_path):
        # Alguien copió un prompt y olvidó renombrarlo: dos prompts distintos
        # reportarían el mismo identificador y las métricas se mezclarían.
        (tmp_path / "copia.yaml").write_text(
            "nombre: original\nversion: 1\nplantilla: x\n", encoding="utf-8")
        with pytest.raises(ValueError, match="no coincide"):
            loader.cargar("copia", tmp_path)

    def test_listar_devuelve_los_disponibles(self, carpeta_yaml):
        assert loader.listar(carpeta_yaml) == ["saludo"]


class TestRender:
    def test_sustituye_la_variable(self, carpeta_yaml):
        assert "Hola Ana." in loader.cargar("saludo", carpeta_yaml).render(nombre="Ana")

    def test_la_condicional_se_evalua_en_el_yaml(self, carpeta_yaml):
        prompt = loader.cargar("saludo", carpeta_yaml)
        assert "Un placer." in prompt.render(nombre="jefe")
        assert "Un placer." not in prompt.render(nombre="Ana")

    def test_una_variable_que_FALTA_es_un_error(self, carpeta_yaml):
        # ⭐ Sin esto, Jinja2 renderizaría "Hola ." y el modelo respondería algo
        #    plausible. El fallo más caro es el que no hace ruido.
        with pytest.raises(ValueError, match="faltan variables"):
            loader.cargar("saludo", carpeta_yaml).render()

    def test_una_variable_que_SOBRA_tambien_es_un_error(self, carpeta_yaml):
        # Quien llama cree estar pasando un dato que el modelo nunca verá.
        with pytest.raises(ValueError, match="no declaradas"):
            loader.cargar("saludo", carpeta_yaml).render(nombre="Ana", rol="analyst")


class TestPromptRealDelAgente:
    """El prompt que la app usa de verdad. Si esto falla, el agente arranca roto."""

    @pytest.fixture
    def prompt(self):
        return loader.cargar("agente_gobdata")

    def test_declara_la_variable_rol(self, prompt):
        assert prompt.variables == ("rol",)

    def test_se_renderiza_para_cada_rol(self, prompt):
        for rol in ("public", "analyst", "compliance"):
            texto = prompt.render(rol=rol)
            assert rol in texto
            assert "{{" not in texto      # nada sin sustituir

    def test_solo_compliance_recibe_la_nota_de_los_anexos(self, prompt):
        # La condicional vive en el YAML, no en un `if` de Python.
        assert "nota_compliance" in prompt.render(rol="compliance")
        assert "nota_compliance" not in prompt.render(rol="analyst")

    def test_prohibe_inventar_normativa(self, prompt):
        # Regresión: la v2 del prompt nació de un fallo de faithfulness.
        assert "Nunca inventes normativa" in prompt.render(rol="analyst")

    def test_prohibe_especular_sobre_lo_que_no_puede_leer(self, prompt):
        # Regresión: la v3 nació porque el agente describía los anexos
        # restringidos aunque el RBAC no le dejara citarlos.
        assert "NO especules" in prompt.render(rol="analyst")

    def test_el_changelog_documenta_cada_version(self, prompt):
        # Un `version: 3` sin changelog no sirve para investigar un incidente.
        assert len(prompt.metadata["cambios"]) == prompt.version


class TestElAgenteUsaElYAML:
    def test_prompt_por_defecto_sale_del_yaml_y_depende_del_rol(self):
        from app.agent import prompt_por_defecto

        assert "nota_compliance" in prompt_por_defecto("compliance")
        assert "nota_compliance" not in prompt_por_defecto("analyst")
