"""
config.py · Settings centralizados del asistente de compras retail
===================================================================
FINALIDAD:
  Un ÚNICO sitio de verdad para toda la configuración del servicio. Lee las
  variables de entorno (o .env) y las valida con pydantic-settings: si falta algo
  obligatorio o viene con tipo erróneo, falla AQUÍ y con un mensaje claro, no a
  mitad de una request.

  ⭐ pydantic-settings convierte los strings del .env en tipos de Python (int,
     float, bool) y aplica defaults. Es la versión "tipada" de os.getenv.

  Mismo patrón que proyecto_llmops/app/config.py: cada módulo importa `settings`
  en vez de leer el entorno por su cuenta, y los valores caros (crear el modelo)
  siguen en funciones — importar este módulo NO debe gastar cuota.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# La carpeta del proyecto (proyecto_retail/). Para resolver rutas relativas.
CARPETA = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Toda la configuración, cargada desde variables de entorno o .env."""

    model_config = SettingsConfigDict(
        env_file=str(CARPETA / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- MODELO DE CHAT ----
    # El proveedor se elige AQUÍ, desde el .env. Dos caminos:
    #   llm_provider="openai"  → cualquier API compatible con OpenAI (Groq,
    #                            Ollama, Together, OpenAI…). Usa llm_base_url + llm_api_key.
    #   llm_provider="google"  → Gemini, como el resto del curso. Usa google_api_key.
    llm_provider: str = "openai"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = Field(default="", description="Llave del proveedor OpenAI-compatible (p.ej. Groq)")
    llm_modelo: str = "qwen/qwen3-32b"
    llm_temperatura: float = 0.0

    google_api_key: str = Field(default="", description="Llave de Google AI Studio (si llm_provider=google)")

    @property
    def llm_es_google(self) -> bool:
        return self.llm_provider.lower() == "google"

    # ---- CATÁLOGO ----
    # El asistente lee de un catálogo con la FORMA del products.json de Shopify.
    #   "demo" → el catálogo offline versionado (data/catalogo_demo.json). Cero red.
    #   "live" → se baja del endpoint público real (ver data/fetch_catalogo.py).
    #            Es lo que se hace en el ejercicio "con los datos de verdad".
    catalogo_fuente: str = "demo"
    catalogo_url: str = "https://sifrah.com/products.json?limit=250"
    # k productos que devuelve la búsqueda como máximo.
    busqueda_top_k: int = 3

    # ---- CACHÉ SEMÁNTICO ----
    # Una pregunta repetida ("aretes dorados baratos") se sirve sin llamar al LLM.
    cache_umbral_similitud: float = Field(
        default=0.92, ge=0.0, le=1.0,
        description="Por encima de esto, dos peticiones se consideran la misma",
    )

    # ---- LANGFUSE (observabilidad, opcional) ----
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    @property
    def langfuse_activo(self) -> bool:
        """Solo mandamos trazas si están AMBAS llaves."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    # ---- REDIS (backend opcional del caché) ----
    redis_host: str = "localhost"
    redis_port: int = 6380

    # ---- EVALUACIÓN ----
    eval_umbral_aprobacion: float = Field(
        default=0.9, ge=0.0, le=1.0,
        description="% mínimo de casos fieles para aprobar un deploy",
    )
    eval_muestra: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Fracción del dataset que evalúa la CI (1.0 = todo)",
    )

    # ---- API ----
    app_port: int = 8000

    # ---- OBSERVABILIDAD ----
    # Verbosidad del log estructurado (ver observability/logs.py). DEBUG para
    # desarrollar, INFO en producción, WARNING si el volumen aprieta. Se cambia
    # por entorno: subir la verbosidad de un servicio vivo no debe exigir un
    # redeploy del código.
    log_level: str = "INFO"

    # ---- AUTENTICACIÓN ----
    # Credenciales válidas separadas por comas: "clave1,clave2".
    # VACÍO = servicio abierto (el modo del curso). Ver app/auth.py.
    #
    # ⚠️ Aquí NO hay roles, a diferencia de proyecto_llmops ("clave:rol,..."):
    #    el catálogo es público y todo el mundo ve lo mismo, así que solo hay
    #    autenticación (¿te dejo entrar?), no autorización (¿qué puedes ver?).
    #
    # ⚠️ Es un `str` y no una lista a propósito: pydantic-settings intentaría
    #    parsear un campo complejo como JSON, y "clave1,clave2" no lo es.
    api_keys: str = ""

    # Orígenes que pueden llamar a la API desde un navegador, separados por
    # comas. Vacío = no se instala CORS (mismo origen, que es lo que hace la
    # demo: el frontend lo sirve este mismo servicio en `/`).
    # ⚠️ "*" con credenciales es una combinación que los navegadores rechazan,
    #    y aquí además sería regalar la API a cualquier página. Sé explícito:
    #    CORS_ORIGINS=https://sifrah.com
    cors_origins: str = ""

    @property
    def lista_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ---- RUTAS ----
    @property
    def ruta_catalogo_demo(self) -> Path:
        return CARPETA / "data" / "catalogo_demo.json"

    @property
    def ruta_prompts(self) -> Path:
        return CARPETA / "prompts"

    @property
    def ruta_dataset(self) -> Path:
        return CARPETA / "evals" / "dataset.jsonl"


@lru_cache
def _construir_settings() -> Settings:
    return Settings()


settings = _construir_settings()
