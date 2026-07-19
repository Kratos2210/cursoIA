"""
config.py · Settings centralizados del proyecto LLMOps
=======================================================
FINALIDAD:
  Un ÚNICO sitio de verdad para toda la configuración del servicio.
  Lee las variables de entorno (o .env) y las valida con pydantic-settings:
  si falta algo obligatorio o viene con tipo erróneo, falla AQUÍ y con un
  mensaje claro, no a mitad de una request.

  ⭐ pydantic-settings convierte strings del .env en tipos de Python (int,
     float, bool) y aplica defaults. Es la versión "tipada" de os.getenv.

LÓGICA:
  - Settings() carga todo al instanciarse. Lo hace UNA vez (singletón más abajo).
  - Cada módulo importa `settings` en vez de leer el entorno por su cuenta.
  - Los valores caros (crear el modelo Gemini) siguen en funciones, como en
    proyecto_final/config.py: importar este módulo NO debe gastar cuota.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# La carpeta del proyecto (proyecto_llmops/). Para resolver rutas relativas.
CARPETA = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Toda la configuración, cargada desde variables de entorno o .env.

    Cada campo lleva:
      - un tipo (str, int, float) que pydantic valida,
      - un default razonable, para que la app arranque con lo mínimo.
    """

    model_config = SettingsConfigDict(
        env_file=str(CARPETA / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",        # ignora vars del entorno que no estén aquí
    )

    # ---- MODELO DE CHAT ----
    # El proveedor se elige AQUÍ, desde el .env. Dos caminos:
    #   llm_provider="openai"  → cualquier API compatible con OpenAI: Groq
    #                            (https://api.groq.com/openai/v1), Ollama,
    #                            Together, OpenAI… Se usa llm_base_url + llm_api_key.
    #   llm_provider="google"  → Gemini, como el resto del curso. Usa google_api_key.
    #
    # Por defecto: Groq con Qwen3-32B. Es rápido, barato y no consume la cuota
    # (mucho más ajustada) del plan gratuito de Gemini.
    llm_provider: str = "openai"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = Field(default="", description="Llave del proveedor OpenAI-compatible (p.ej. Groq)")
    # La cascada necesita DOS modelos distintos: si cheap == strong,
    # with_fallbacks() reintenta con el mismo modelo y no sirve de nada.
    llm_modelo_cheap: str = "qwen/qwen3-32b"
    llm_modelo_strong: str = "llama-3.3-70b-versatile"
    llm_temperatura: float = 0.0

    # ---- RESILIENCIA DEL CLIENTE LLM (ver app/llm.py) ----
    # Segundos antes de dar por perdida una llamada. Sin timeout, el cliente
    # espera indefinidamente y un proveedor colgado bloquea al worker.
    # 30 s es holgado para una respuesta larga y corto frente a "para siempre".
    llm_timeout_s: float = Field(default=30.0, gt=0)
    # Reintentos ante errores transitorios (429, 503). El cliente ya los espacia
    # con backoff exponencial + jitter, y respeta `Retry-After` si el proveedor
    # lo manda. Bajo a propósito: se COMPONE con la cascada cheap→strong, así
    # que el peor caso de espera es (reintentos × timeout) por cada modelo.
    llm_max_reintentos: int = Field(default=2, ge=0)

    # Solo se usa si llm_provider="google".
    google_api_key: str = Field(default="", description="Llave de Google AI Studio")

    # ---- EMBEDDINGS (siempre locales, nunca una API) ----
    # Groq no tiene endpoint de embeddings, y el RAG los necesita. En vez de atar
    # el proyecto a otro proveedor, los calculamos en esta máquina: cero cuota.
    # Dos motores para el MISMO modelo (multilingüe, porque la normativa es en
    # español), y se elige desde el .env:
    #   "fastembed"   → el modelo en ONNX, sin PyTorch (~70 MB). El DEFAULT:
    #                   es lo que usa la CI y lo único que corre en macOS Intel.
    #   "huggingface" → langchain_huggingface.HuggingFaceEmbeddings. El estándar
    #                   del Hub, pero arrastra sentence-transformers y PyTorch.
    #                   Instalar: uv sync --extra llmops --extra hf
    #                   ⚠️ No resuelve en macOS Intel (ver pyproject y ADR-0002).
    #
    # Los dos cargan el MISMO modelo y producen el mismo vector: son
    # intercambiables sin reindexar.
    embeddings_provider: str = "fastembed"
    embeddings_modelo: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    @property
    def llm_es_google(self) -> bool:
        return self.llm_provider.lower() == "google"

    # ---- POSTGRES + pgvector ----
    pg_host: str = "localhost"
    pg_port: int = 5433
    pg_user: str = "gobdata"
    pg_password: str = "gobdata"
    pg_db: str = "gobdata"

    @property
    def pg_dsn(self) -> str:
        """El connection string que espera psycopg (el driver, a pelo)."""
        return (f"postgresql://{self.pg_user}:{self.pg_password}"
                f"@{self.pg_host}:{self.pg_port}/{self.pg_db}")

    @property
    def pg_dsn_sqlalchemy(self) -> str:
        """El MISMO destino, pero nombrando el driver. Para langchain-postgres.

        ⚠️ No es un capricho de formato. langchain-postgres no habla con psycopg
           directamente: construye un engine de SQLAlchemy, y SQLAlchemy elige el
           driver a partir del ESQUEMA de la URL. 'postgresql://' a secas
           significa psycopg2 — la versión 2, que este proyecto NO instala (solo
           `psycopg[binary]`, que es la 3). Resultado: un ModuleNotFoundError de
           'psycopg2' al construir el retriever, con Postgres perfectamente vivo.

           'postgresql+psycopg://' es lo que pide la v3. El DSN de arriba se
           queda como está porque `psycopg.connect()` (metrics_backends) no
           entiende el sufijo del dialecto: son dos consumidores distintos con
           dos formatos distintos, y por eso son dos propiedades y no una.
        """
        return self.pg_dsn.replace("postgresql://", "postgresql+psycopg://", 1)

    # ---- REDIS ----
    redis_host: str = "localhost"
    redis_port: int = 6380
    cache_umbral_similitud: float = Field(
        default=0.92, ge=0.0, le=1.0,
        description="Por encima de esto, una pregunta se sirve desde caché",
    )

    # ---- LANGFUSE ----
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    @property
    def langfuse_activo(self) -> bool:
        """Solo mandamos trazas si están AMBAS llaves."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    # ---- EVALUACIÓN ----
    eval_umbral_aprobacion: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Score mínimo de la tríada RAG para aprobar un deploy",
    )
    eval_muestra: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Fracción del dataset que evalúa la CI (1.0 = todo)",
    )

    # ---- API ----
    app_port: int = 8000
    app_rol_por_defecto: str = "analyst"

    # ---- PERSISTENCIA DE MÉTRICAS ----
    # "memoria" (por defecto) o "postgres". En memoria, cada worker cuenta lo
    # suyo y un reinicio borra el historial; en postgres, la tabla la comparten
    # todos los workers y /metrics vuelve a hablar del servicio entero.
    # Reutiliza el Postgres que ya levanta el compose para pgvector.
    metricas_backend: str = "memoria"

    # ---- PERSISTENCIA DEL FEEDBACK 👍/👎 (A/B de prompts) ----
    # Mismo problema y misma solución que las métricas: en "memoria" cada worker
    # acumula sus votos y un reinicio los borra, así que el A/B decide sobre una
    # fracción del tráfico. Con "postgres" los votos van a una tabla compartida y
    # se puede elegir variante con significancia estadística. Ver ADR-0006 y
    # observability/feedback_backends.py.
    feedback_backend: str = "memoria"

    # ---- PERSISTENCIA DE LA CONVERSACIÓN (checkpointer de LangGraph) ----
    # "memoria" (por defecto): MemorySaver, la conversación vive en RAM y un
    # reinicio la pierde — lo correcto para el curso y los tests.
    # "postgres": AsyncPostgresSaver, la conversación sobrevive al deploy y la
    # comparten todos los workers. Ver app/persistence.py.
    checkpointer_backend: str = "memoria"
    # Conexiones del pool del checkpointer Postgres. Cada petición en vuelo toma
    # una mientras lee/escribe el estado; con astream concurrente, 1 no basta.
    checkpointer_pool_max: int = Field(default=10, ge=1)

    # ---- LOGGING ----
    # DEBUG en desarrollo, INFO en producción. Cambiar la verbosidad de un
    # servicio no debería requerir tocar código ni reconstruir la imagen.
    log_level: str = "INFO"

    # ---- AUTENTICACIÓN ----
    # Credenciales y el rol que otorga cada una: "clave:rol,otra:rol".
    # VACÍO = servicio abierto y el rol viaja en el body (el modo del curso).
    # Ver app/auth.py: con claves configuradas, el rol deja de ser un dato de
    # entrada y pasa a deducirse de la credencial.
    #
    # ⚠️ Es un `str` y no un dict a propósito: pydantic-settings intentaría
    #    parsear un campo complejo como JSON, y "clave:rol,otra:rol" no lo es.
    api_keys: str = ""

    # ---- LÍMITE DE PETICIONES (ver app/rate_limit.py) ----
    # Peticiones permitidas por cliente y ventana. 0 = sin límite.
    # 30/minuto es holgado para una persona conversando y corta en seco un
    # bucle: cada request a /chat cuesta dinero real.
    rate_limit_peticiones: int = Field(default=30, ge=0)
    rate_limit_ventana_s: float = Field(default=60.0, gt=0)

    # Orígenes que pueden llamar a la API desde un navegador, separados por
    # comas. Vacío = no se instala CORS (mismo origen, que es lo que hace la
    # demo: el frontend lo sirve este mismo servicio en `/`).
    # ⚠️ "*" con credenciales es una combinación que los navegadores rechazan,
    #    y aquí además sería regalar la API a cualquier página. Sé explícito.
    cors_origins: str = ""

    @property
    def lista_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ---- RUTAS ----
    @property
    def ruta_normativa(self) -> Path:
        """La normativa compartida con proyecto_final (mismo dominio)."""
        # CARPETA ya es proyecto_llmops/, así que un solo salto llega a
        # curso_ejemplos/. Subir dos apuntaba fuera del repo.
        return CARPETA.parent / "proyecto_final" / "normativa.txt"

    @property
    def ruta_anexo(self) -> Path:
        """Anexos propios del servicio: material restringido que el prototipo no
        tenía. Sin algo que ocultar, el RBAC no se puede demostrar."""
        return CARPETA / "normativa_anexo.txt"

    @property
    def ruta_prompts(self) -> Path:
        return CARPETA / "prompts"

    @property
    def ruta_dataset(self) -> Path:
        return CARPETA / "evals" / "dataset.jsonl"


# El singletón: todo el mundo importa `settings`, no `Settings()`.
@lru_cache
def _construir_settings() -> Settings:
    return Settings()


settings = _construir_settings()
