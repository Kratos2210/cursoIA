"""
test_util.py · Tests de util.py (lógica compartida pura)
==========================================================
Estos tests verifican las funciones de apoyo SIN tocar el LLM ni la API.
Son la primera red de seguridad: si algo aquí falla, los ejemplos mostrarán
errores crípticos en producción.
"""
import pytest
from util import es_error_cuota, mensaje_cuota, trocear_parrafos, requiere_api_key


# ------------------------------------------------------------------
# es_error_cuota: reconocimiento del error 429 / RESOURCE_EXHAUSTED
# ------------------------------------------------------------------
@pytest.mark.offline
class TestEsErrorCuota:
    def test_resource_exhausted(self):
        """El texto exacto que devuelve Gemini al agotar cuota."""
        exc = Exception("Error 429: RESOURCE_EXHAUSTED. Quota exceeded.")
        assert es_error_cuota(exc) is True

    def test_solo_429(self):
        """Algunos errores traen solo el código, sin el texto."""
        assert es_error_cuota(Exception("HTTP 429")) is True

    def test_otro_error_no_es_cuota(self):
        """Un error de red o de autenticación NO debe confundirse con cuota."""
        assert es_error_cuota(Exception("Authentication failed 401")) is False
        assert es_error_cuota(Exception("Connection refused")) is False

    def test_excepcion_sin_texto(self):
        assert es_error_cuota(ValueError("algo")) is False

    def test_none(self):
        """Un None (cuando se captura mal) no debe romper."""
        assert es_error_cuota(None) is False


# ------------------------------------------------------------------
# mensaje_cuota: el texto amable para el estudiante
# ------------------------------------------------------------------
@pytest.mark.offline
class TestMensajeCuota:
    def test_menciona_429(self):
        msg = mensaje_cuota()
        assert "429" in msg
        # Guía al estudiante hacia una solución concreta:
        assert "gemini-2.5-flash" in msg


# ------------------------------------------------------------------
# trocear_parrafos: el troceado que usan RAG, híbrido y el proyecto final
# ------------------------------------------------------------------
@pytest.mark.offline
class TestTrocearParrafos:
    def test_texto_simple(self):
        texto = "Primer párrafo.\n\nSegundo párrafo.\n\nTercero."
        assert trocear_parrafos(texto) == ["Primer párrafo.", "Segundo párrafo.", "Tercero."]

    def test_ignora_vacios_y_strip(self):
        """Líneas en blanco extra y espacios a los bordes no generan chunks basura."""
        texto = "  hola  \n\n\n\n  mundo  "
        assert trocear_parrafos(texto) == ["hola", "mundo"]

    def test_un_solo_parrafo(self):
        assert trocear_parrafos("solo uno") == ["solo uno"]

    def test_vacio(self):
        assert trocear_parrafos("") == []
        assert trocear_parrafos("\n\n\n") == []

    def test_datos_rag_reales(self, chunks_datos_rag):
        """datos_rag.txt debe partirse en 7 fragmentos (la base del RAG).

        Son 7 y no 6 porque el TÍTULO ('Manual de la empresa Datawith.AI')
        queda como su propio fragmento: está separado del resto por una línea
        en blanco. Es un chunk 'de ruido' — no responde ninguna pregunta.
        Ese es justo el problema que el TEMA 12 ataca con el re-ranking.
        """
        assert len(chunks_datos_rag) == 7
        # Ningún chunk debe quedar vacío tras el troceado.
        assert all(len(c) > 0 for c in chunks_datos_rag)
        # El primer fragmento es el título suelto (chunk de ruido).
        assert chunks_datos_rag[0] == "Manual de la empresa Datawith.AI"


# ------------------------------------------------------------------
# requiere_api_key: validación de la llave
# ------------------------------------------------------------------
@pytest.mark.offline
class TestRequiereApiKey:
    def test_falta_key(self, monkeypatch):
        """Si no hay GOOGLE_API_KEY, devuelve un mensaje de error (no None)."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        assert requiere_api_key() is not None
        assert "GOOGLE_API_KEY" in requiere_api_key()

    def test_hay_key(self, monkeypatch):
        """Si la llave está presente, devuelve None (todo ok)."""
        monkeypatch.setenv("GOOGLE_API_KEY", "una_llave_de_prueba")
        assert requiere_api_key() is None
