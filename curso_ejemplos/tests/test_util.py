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
        assert util.modelo_por_defecto("groq") == "openai/gpt-oss-120b"
        assert util.modelo_por_defecto("google") == "gemini-3.1-flash-lite"
        assert util.modelo_por_defecto("ollama") == "qwen3:8b"
        # Los cuatro proveedores nuevos, cada uno con su default (ver el plan):
        assert util.modelo_por_defecto("openai") == "gpt-5.4-mini"
        assert util.modelo_por_defecto("anthropic") == "claude-haiku-4-5"
        assert util.modelo_por_defecto("openrouter") == "meta-llama/llama-3.3-70b-instruct:free"
        assert util.modelo_por_defecto("deepseek") == "deepseek-v4-flash"
        # Kimi entra con el tier BARATO (k2.6), no con el flagship k3.
        assert util.modelo_por_defecto("kimi") == "kimi-k2.6"

    def test_LLM_MODELO_manda_sobre_el_default(self, monkeypatch):
        monkeypatch.setenv("LLM_MODELO", "llama-3.3-70b-versatile")
        assert util.modelo_por_defecto("groq") == "llama-3.3-70b-versatile"

    def test_un_proveedor_inventado_falla_claro(self, monkeypatch):
        monkeypatch.delenv("LLM_MODELO", raising=False)
        # OJO: 'cohere' es un proveedor REAL, pero el curso no lo soporta; sirve
        # justo por eso como "inventado". (Antes aquí ponía 'openrouter', que
        # dejó de valer como ejemplo el día que 'openrouter' pasó a ser real.)
        with pytest.raises(ValueError, match="no existe"):
            util.modelo_por_defecto("cohere")

    def test_cada_proveedor_lee_SU_variable_de_llave(self):
        assert util.variable_de_llave("google") == "GOOGLE_API_KEY"
        assert util.variable_de_llave("groq") == "GROQ_API_KEY"
        assert util.variable_de_llave("ollama") == "OLLAMA_API_KEY"
        # Los nuevos: cada proveedor con SU variable, sin colisiones.
        assert util.variable_de_llave("openai") == "OPENAI_API_KEY"
        assert util.variable_de_llave("anthropic") == "ANTHROPIC_API_KEY"
        assert util.variable_de_llave("openrouter") == "OPENROUTER_API_KEY"
        assert util.variable_de_llave("deepseek") == "DEEPSEEK_API_KEY"
        # El desajuste a propósito: el proveedor es `kimi`, la empresa es Moonshot
        # y la variable que espera su API es MOONSHOT_API_KEY. Deducirla del
        # nombre del producto (KIMI_API_KEY) da un 401.
        assert util.variable_de_llave("kimi") == "MOONSHOT_API_KEY"


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

    def test_con_anthropic_pide_ANTHROPIC_API_KEY_y_no_otra(self, monkeypatch):
        # Claude es un proveedor NATIVO (rama propia, como Gemini): su llave sale
        # de _PROVEEDORES_NATIVOS, no de _COMPATIBLES_OPENAI. El mensaje tiene que
        # nombrar SU variable, no la de otro proveedor que el alumno tenga puesta.
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("OPENAI_API_KEY", "sk_la_de_openai_no_sirve_aqui")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        aviso = util.requiere_llm_key()
        assert "ANTHROPIC_API_KEY" in aviso
        assert "OPENAI_API_KEY" not in aviso

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
        assert llm.model_name == "openai/gpt-oss-120b"
        assert "groq.com" in str(llm.openai_api_base)
        assert llm.temperature == 0.3

    def test_groq_oculta_el_bloque_think_de_los_modelos_de_razonamiento(self, monkeypatch):
        # qwen3.6 es de RAZONAMIENTO y devuelve su cadena de pensamiento dentro
        # del contenido, envuelta en <think>…</think>. `reasoning_format: hidden`
        # le dice a Groq que la descarte; sin esto, TODAS las salidas del curso
        # salen contaminadas.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.setenv("LLM_MODELO", "qwen/qwen3.6-27b")
        assert util.crear_llm().extra_body == {"reasoning_format": "hidden"}

    def test_a_un_modelo_SIN_razonamiento_no_se_le_manda_ese_parametro(self, monkeypatch):
        # Groq devuelve 400 si se lo mandas a llama-3.3: "`reasoning_format` is
        # not supported with this model".
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.setenv("LLM_MODELO", "llama-3.3-70b-versatile")
        assert util.crear_llm().extra_body is None

    def test_a_gpt_oss_NUNCA_se_le_manda_reasoning_format(self, monkeypatch):
        # ⭐ LA REGRESIÓN QUE NOS COSTÓ UN 400. gpt-oss ES de razonamiento, pero
        #    la doc de Groq dice que NO acepta `reasoning_format` (usa
        #    `include_reasoning`, y son mutuamente excluyentes). Como gpt-oss es
        #    el default de Groq del curso, mandárselo rompía la PRIMERA llamada
        #    de cualquier alumno. Este test vigila que no vuelva a colarse.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)  # el default: gpt-oss
        extra = util.crear_llm().extra_body
        assert "reasoning_format" not in extra
        # Su razonamiento ya viaja en un campo aparte; lo apagamos igualmente
        # para no pagar tokens que nadie va a leer.
        assert extra == {"include_reasoning": False}

    def test_gpt_oss_respeta_GROQ_RAZONAMIENTO_raw(self, monkeypatch):
        # El interruptor didáctico sigue funcionando, traducido a su parámetro.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        monkeypatch.setenv("GROQ_RAZONAMIENTO", "raw")
        assert util.crear_llm().extra_body == {"include_reasoning": True}

    def test_structured_output_usa_function_calling_no_json_schema(self, monkeypatch):
        # ⭐ Groq solo soporta response_format=json_schema en ALGUNOS modelos, y
        #    el default del curso nunca ha estado entre ellos: el TEMA 05 se caía
        #    con un 400. function_calling da el mismo resultado por otro camino y
        #    funciona en todo modelo con tool calling, sea cual sea el default.
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
class TestProveedoresNuevos:
    """Los cuatro proveedores que se añadieron al conmutador: openai, anthropic,
    openrouter y deepseek.

    Tres hablan el dialecto de OpenAI (openai/openrouter/deepseek) y se
    construyen con `ChatOpenAI` + su `base_url`, igual que Groq y Ollama. El
    cuarto, anthropic, es NATIVO: tiene su propia clase, como Gemini. Estos tests
    inspeccionan el cliente ya construido (sin llamar a la API), como
    `TestCrearLlm`: `model_name`, `openai_api_base` y `extra_body`.
    """

    def test_openai_apunta_a_su_base_url_con_gpt_5_mini(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)

        from langchain_openai import ChatOpenAI

        llm = util.crear_llm()
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-5.4-mini"
        assert "api.openai.com" in str(llm.openai_api_base)

    def test_openrouter_apunta_a_su_base_url_con_el_llama_gratis(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)

        llm = util.crear_llm()
        assert llm.model_name == "meta-llama/llama-3.3-70b-instruct:free"
        assert "openrouter.ai" in str(llm.openai_api_base)

    def test_deepseek_apunta_a_su_base_url_con_v4_flash(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)

        llm = util.crear_llm()
        assert llm.model_name == "deepseek-v4-flash"
        assert "api.deepseek.com" in str(llm.openai_api_base)

    def test_openai_no_lleva_ningun_parche_en_extra_body(self, monkeypatch):
        # OpenAI no necesita esconder ningún <think>: sus modelos no lo escupen
        # dentro del contenido. Mandarle un parche que no espera sería pedir un 400.
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        assert util.crear_llm().extra_body is None

    def test_deepseek_no_lleva_ningun_parche_en_extra_body(self, monkeypatch):
        # deepseek-v4-flash no razona por defecto, y en modo pensante devuelve el
        # razonamiento en un campo APARTE del contenido: nunca hace falta parche.
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        assert util.crear_llm().extra_body is None

    def test_anthropic_construye_un_ChatAnthropic(self, monkeypatch):
        # Claude NO habla el dialecto de OpenAI: rama propia con su clase, como
        # Gemini. La llave tiene que estar ANTES de construir (si no, SystemExit).
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)

        llm = util.crear_llm()
        assert type(llm).__name__ == "ChatAnthropic"

    def test_anthropic_sin_llave_aborta_nombrando_ANTHROPIC_API_KEY(self, monkeypatch):
        # Mejor un SystemExit con instrucciones que un 401 críptico a mitad de
        # la primera llamada. Y el mensaje debe nombrar SU variable.
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY"):
            util.crear_llm()

    def test_reasoning_format_es_EXCLUSIVO_de_groq(self, monkeypatch):
        # `reasoning_format` es un parámetro SOLO de Groq. A un modelo de
        # razonamiento servido por OpenRouter (aquí un gpt-oss) NO se le puede
        # mandar: OpenRouter no lo entiende. El parche correcto es otro (ver el
        # test siguiente). Aquí blindamos que ese nombre no se cuele.
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or_de_prueba")
        monkeypatch.setenv("LLM_MODELO", "openai/gpt-oss-120b")
        extra = util.crear_llm().extra_body or {}
        assert "reasoning_format" not in extra

    def test_openrouter_con_modelo_razonador_usa_reasoning_exclude(self, monkeypatch):
        # OpenRouter unifica el "esconde el <think>" bajo `reasoning`: el
        # equivalente al "hidden" de Groq es {"exclude": True}.
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or_de_prueba")
        monkeypatch.setenv("LLM_MODELO", "openai/gpt-oss-120b")
        assert util.crear_llm().extra_body == {"reasoning": {"exclude": True}}


@pytest.mark.offline
class TestKimi:
    """Kimi (Moonshot): otro compatible con OpenAI, con una trampa propia.

    Habla el dialecto de OpenAI —así que es una `base_url` más—, pero FIJA los
    parámetros de muestreo: mandarle `temperature=0.0`, que es lo que pide todo
    el curso, es un 400. Estos tests blindan las tres cosas que hay que acertar:
    la base_url, la variable de llave (que NO se llama como el producto) y la
    temperatura omitida.
    """

    def _entorno(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "kimi")
        monkeypatch.setenv("MOONSHOT_API_KEY", "sk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)

    def test_kimi_apunta_a_moonshot_con_el_tier_barato(self, monkeypatch):
        self._entorno(monkeypatch)
        llm = util.crear_llm()
        assert llm.model_name == "kimi-k2.6"
        assert "api.moonshot.ai" in str(llm.openai_api_base)

    def test_kimi_sin_llave_aborta_nombrando_MOONSHOT_API_KEY(self, monkeypatch):
        # El nombre de la variable no se deduce del proveedor: el aviso tiene que
        # decir MOONSHOT_API_KEY, o el alumno buscará una KIMI_API_KEY que no existe.
        monkeypatch.setenv("LLM_PROVIDER", "kimi")
        monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
        with pytest.raises(SystemExit, match="MOONSHOT_API_KEY"):
            util.crear_llm()

    def test_a_kimi_NUNCA_se_le_manda_temperature(self, monkeypatch):
        # REGRESIÓN. La doc de Moonshot fija la temperatura (k3 la clava en 1.0 y
        # pide OMITIR el campo; k2.6 solo admite 1.0 o 0.6). `crear_llm` recibe
        # 0.0 de todo el curso, y aquí NO puede reenviarlo.
        #
        # Por qué `is None` prueba que se omite: `ChatOpenAI._default_params`
        # construye el payload con un `exclude_if_none`, así que un campo en None
        # no llega a viajar en el JSON. `None` aquí ES "no mandar el kwarg".
        self._entorno(monkeypatch)
        llm = util.crear_llm(temperature=0.0)
        assert llm.temperature is None
        assert "temperature" not in llm._default_params

    def test_los_demas_proveedores_SIGUEN_recibiendo_la_temperatura(self, monkeypatch):
        # La otra mitad de la regresión: la excepción de Kimi no puede haberle
        # quitado la temperatura —y con ella la reproducibilidad— a nadie más.
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
        monkeypatch.delenv("LLM_MODELO", raising=False)
        assert util.crear_llm(temperature=0.0).temperature == 0.0

    def test_kimi_no_lleva_ningun_parche_en_extra_body(self, monkeypatch):
        # Las ramas de `extra_body` son de Groq y OpenRouter: sus nombres de
        # parámetro NO son intercambiables, y mandarle uno ajeno a Moonshot sería
        # otro 400. Si algún día hace falta esconder el razonamiento de kimi-k3,
        # será con el parámetro que diga SU doc, no reciclando el de otro.
        self._entorno(monkeypatch)
        assert util.crear_llm().extra_body is None


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
