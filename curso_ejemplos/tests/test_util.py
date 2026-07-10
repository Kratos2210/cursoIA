"""
test_util.py · Tests de util.py (lógica compartida pura)
==========================================================
Estos tests verifican las funciones de apoyo SIN tocar el LLM ni la API.
Son la primera red de seguridad: si algo aquí falla, los ejemplos mostrarán
errores crípticos en producción.
"""
import pytest
import util
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


# ------------------------------------------------------------------
# crear_llm: elegir proveedor sin tocar el código
# ------------------------------------------------------------------
# La cuota gratuita de Gemini se agota a mitad de una tarde de ejercicios. Estos
# tests fijan que `LLM_PROVIDER=groq` sea una salida de verdad, no un adorno.
#
# Construir el modelo NO llama a la API: solo instancia el cliente. Por eso
# estos tests son offline aunque toquen `crear_llm()`.
@pytest.mark.offline
class TestProveedor:
    def test_por_defecto_es_google(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        assert util.proveedor() == "google"

    def test_lo_decide_el_entorno(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "GROQ")   # mayúsculas y espacios sobran
        assert util.proveedor() == "groq"

    def test_cada_proveedor_tiene_su_modelo(self, monkeypatch):
        monkeypatch.delenv("LLM_MODELO", raising=False)
        assert util.modelo_por_defecto("groq") == "qwen/qwen3-32b"
        assert util.modelo_por_defecto("google") == "gemini-2.0-flash"

    def test_LLM_MODELO_manda_sobre_el_default(self, monkeypatch):
        monkeypatch.setenv("LLM_MODELO", "llama-3.3-70b-versatile")
        assert util.modelo_por_defecto("groq") == "llama-3.3-70b-versatile"

    def test_un_proveedor_inventado_falla_claro(self, monkeypatch):
        monkeypatch.delenv("LLM_MODELO", raising=False)
        with pytest.raises(ValueError, match="no existe"):
            util.modelo_por_defecto("openrouter")

    def test_cada_proveedor_lee_SU_variable_de_llave(self):
        assert util.variable_de_llave("google") == "GOOGLE_API_KEY"
        assert util.variable_de_llave("groq") == "GROQ_API_KEY"


@pytest.mark.offline
class TestRequiereLlmKey:
    def test_con_groq_pide_GROQ_API_KEY_no_la_de_google(self, monkeypatch):
        # El fallo clásico al cambiar de proveedor: seguir validando la llave vieja.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GOOGLE_API_KEY", "la_de_google_no_sirve_aqui")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        assert "GROQ_API_KEY" in util.requiere_llm_key()

    def test_con_la_llave_correcta_no_se_queja(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        assert util.requiere_llm_key() is None

    def test_ollama_no_necesita_llave(self, monkeypatch):
        # Corre en tu máquina: no hay a quién autenticarse.
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        assert util.requiere_llm_key() is None


@pytest.mark.offline
class TestCrearLlm:
    def test_groq_construye_un_cliente_openai_apuntando_a_groq(self, monkeypatch):
        # ⭐ Una sola clase sirve para Groq, Ollama y OpenAI: todos hablan el
        #    mismo dialecto. Lo que cambia es la base_url, no el código.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)

        from langchain_openai import ChatOpenAI

        llm = util.crear_llm(temperature=0.3)
        # Es un ChatOpenAI (subclase: ver _crear_chat_openai_compatible).
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "qwen/qwen3-32b"
        assert "groq.com" in str(llm.openai_api_base)
        assert llm.temperature == 0.3

    def test_groq_oculta_el_bloque_think_de_los_modelos_de_razonamiento(self, monkeypatch):
        # qwen3 escribe su cadena de pensamiento dentro del contenido, envuelta
        # en <think>…</think>. `reasoning_format: hidden` le dice a Groq que la
        # descarte. Sin esto, TODAS las salidas del curso salen contaminadas.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        assert util.crear_llm().extra_body == {"reasoning_format": "hidden"}

    def test_a_un_modelo_SIN_razonamiento_no_se_le_manda_ese_parametro(self, monkeypatch):
        # Groq devuelve 400 si se lo mandas a llama-3.3: "`reasoning_format` is
        # not supported with this model".
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.setenv("LLM_MODELO", "llama-3.3-70b-versatile")
        assert util.crear_llm().extra_body is None

    def test_structured_output_usa_function_calling_no_json_schema(self, monkeypatch):
        # ⭐ qwen/qwen3-32b NO soporta response_format=json_schema en Groq: el
        #    TEMA 05 se caía con un 400. function_calling da el mismo resultado
        #    por otro camino y funciona en todo modelo con tool calling.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        from pydantic import BaseModel

        class Molde(BaseModel):
            nombre: str

        capturado = {}
        llm = util.crear_llm()
        original = type(llm).__mro__[1].with_structured_output

        def espia(self, schema, *, method="json_schema", **kw):
            capturado["method"] = method
            return "runnable-falso"

        monkeypatch.setattr(type(llm).__mro__[1], "with_structured_output", espia)
        llm.with_structured_output(Molde)
        assert capturado["method"] == "function_calling"

    def test_google_sigue_siendo_el_camino_por_defecto(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("LLM_MODELO", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "de_prueba")

        llm = util.crear_llm()
        assert type(llm).__name__ == "ChatGoogleGenerativeAI"

    def test_sin_llave_aborta_antes_de_construir_nada(self, monkeypatch):
        # Mejor un SystemExit con instrucciones que un 401 críptico a mitad de
        # la primera llamada.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(SystemExit, match="GROQ_API_KEY"):
            util.crear_llm()


@pytest.mark.offline
class TestMensajeCuotaPorProveedor:
    def test_con_gemini_ofrece_groq_como_salida(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        assert "groq" in mensaje_cuota().lower()

    def test_con_groq_no_recomienda_un_modelo_de_gemini(self, monkeypatch):
        # Decirle "usa gemini-2.5-flash" a quien corre contra Groq no le sirve.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        assert "gemini" not in mensaje_cuota().lower()
        assert "429" in mensaje_cuota()


@pytest.mark.offline
class TestRequiereApiKeyEsUnAlias:
    """`requiere_api_key()` se quedó como alias histórico de `requiere_llm_key()`.

    Antes miraba GOOGLE_API_KEY a secas. Ahora que TODOS los ejemplos respetan
    LLM_PROVIDER, validar la llave de Google cuando el alumno corre contra Groq
    sería mentirle.
    """

    def test_delega_en_el_proveedor_activo(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GOOGLE_API_KEY", "la_de_google_no_sirve_aqui")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        assert "GROQ_API_KEY" in requiere_api_key()

    def test_con_google_se_comporta_como_siempre(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        assert "GOOGLE_API_KEY" in requiere_api_key()


# ------------------------------------------------------------------
# crear_embeddings: donde la analogía con el chat se rompe
# ------------------------------------------------------------------
@pytest.mark.offline
class TestCrearEmbeddings:
    def test_por_defecto_son_los_de_google(self, monkeypatch):
        monkeypatch.delenv("EMBEDDINGS_PROVIDER", raising=False)
        assert util.proveedor_embeddings() == "google"

    def test_sin_llave_de_google_explica_las_DOS_salidas(self, monkeypatch):
        # Groq no ofrece embeddings: el mensaje tiene que decir qué hacer.
        monkeypatch.delenv("EMBEDDINGS_PROVIDER", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(SystemExit) as error:
            util.crear_embeddings()
        assert "fastembed" in str(error.value)
        assert "--extra emb" in str(error.value)

    def test_un_motor_inventado_falla_claro(self, monkeypatch):
        monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openai")
        with pytest.raises(ValueError, match="no existe"):
            util.crear_embeddings()

    def test_los_embeddings_NO_siguen_a_LLM_PROVIDER(self, monkeypatch):
        # ⭐ Cambiar el chat a Groq no cambia los embeddings. Y no es un
        #    descuido: cambiar de modelo de embeddings invalida el índice.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.delenv("EMBEDDINGS_PROVIDER", raising=False)
        assert util.proveedor_embeddings() == "google"
