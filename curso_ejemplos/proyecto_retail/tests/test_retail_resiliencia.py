"""
test_resiliencia.py · Timeouts y reintentos: que un proveedor caído no te tumbe
===============================================================================
Sin `timeout`, el cliente espera INDEFINIDAMENTE a un proveedor que acepta la
conexión y no contesta. La request queda colgada y con ella el worker que la
atiende; suficientes así y el servicio deja de responder sin un solo error que
registrar. Es el fallo más difícil de diagnosticar precisamente porque no
produce ninguna señal.

Estos tests no llaman a ningún proveedor: comprueban que la configuración LLEGA
hasta el cliente HTTP que hará la llamada. Es lo que se puede verificar sin red,
y es exactamente donde estaba el agujero (los valores existían en el .env pero
nadie los pasaba al constructor).
"""
import pytest

from proyecto_retail.app import llm
from proyecto_retail.app.config import settings

pytestmark = pytest.mark.offline


@pytest.fixture(autouse=True)
def llave_falsa(monkeypatch):
    """`crear_modelo` exige una llave para no fallar tarde. No se usa: no hay red."""
    monkeypatch.setattr(settings, "llm_api_key", "llave-de-prueba")


class TestTimeout:
    def test_el_timeout_llega_al_cliente(self):
        modelo = llm.crear_llm()
        assert modelo.request_timeout == settings.llm_timeout_s

    def test_el_timeout_llega_hasta_el_sdk_por_debajo(self):
        # ⭐ Lo que importa no es el atributo de LangChain, sino que el cliente
        #    HTTP que hace la llamada de verdad lo tenga. Un parámetro aceptado
        #    y no propagado se ve igual desde fuera... hasta que cuelga.
        modelo = llm.crear_llm()
        assert modelo.root_client.timeout == settings.llm_timeout_s

    def test_es_configurable_desde_el_entorno(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_timeout_s", 5.0)
        assert llm.crear_llm().request_timeout == 5.0

    def test_un_timeout_no_positivo_se_rechaza_al_configurar(self):
        # pydantic valida en el arranque (gt=0): un timeout de 0 significaría
        # "ríndete siempre" y uno negativo no significa nada.
        from pydantic import ValidationError

        from proyecto_retail.app.config import Settings
        with pytest.raises(ValidationError):
            Settings(llm_timeout_s=0)


class TestReintentos:
    def test_los_reintentos_llegan_al_sdk(self):
        modelo = llm.crear_llm()
        assert modelo.root_client.max_retries == settings.llm_max_reintentos

    def test_se_pueden_desactivar(self, monkeypatch):
        # 0 es un valor legítimo: quien ponga la cascada delante puede preferir
        # saltar al modelo fuerte inmediatamente en vez de insistir con el cheap.
        monkeypatch.setattr(settings, "llm_max_reintentos", 0)
        assert llm.crear_llm().root_client.max_retries == 0

    def test_no_se_aceptan_reintentos_negativos(self):
        from pydantic import ValidationError

        from proyecto_retail.app.config import Settings
        with pytest.raises(ValidationError):
            Settings(llm_max_reintentos=-1)


class TestLaSubclaseNoPierdeLaConfiguracion:
    def test_ChatCompatible_conserva_timeout_y_reintentos(self):
        # ⚠️ retail no usa ChatOpenAI a pelo: lo subclasea (_ChatCompatible) para
        #    forzar `function_calling` en with_structured_output. Una subclase es
        #    justo donde un parámetro se pierde sin que nadie lo note.
        modelo = llm.crear_llm()
        assert type(modelo).__name__ == "_ChatCompatible"
        assert modelo.request_timeout == settings.llm_timeout_s
        assert modelo.root_client.max_retries == settings.llm_max_reintentos
