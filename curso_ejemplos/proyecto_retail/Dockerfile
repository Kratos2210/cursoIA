# ==========================================================
# Dockerfile · La imagen del asistente de compras Sifrah
# ==========================================================
# FINALIDAD:
#   Convertir "corre en mi máquina" en un artefacto que se despliega. Hasta
#   ahora el docker-compose levantaba solo Redis y la app se arrancaba a mano
#   con `uvicorn --reload`. Eso no es desplegable: no hay nada que subir a un
#   servidor.
#
# ⚠️ EL CONTEXTO DE BUILD ES `curso_ejemplos/`, NO ESTA CARPETA.
#    Se construye así (fíjate en el punto final):
#
#      docker build -f proyecto_retail/Dockerfile -t sifrah-retail .
#
#    Tiene que ser así por dos razones. Una: el `pyproject.toml` y el `uv.lock`
#    viven arriba y son el canon de dependencias del curso. Y dos, la de fondo:
#    este proyecto se importa con el prefijo COMPLETO (`proyecto_retail.app…`),
#    justo para no chocar con el `app`/`guardrails` de proyecto_llmops. Para que
#    ese import funcione, `proyecto_retail` tiene que ser un paquete visible
#    desde la RAÍZ — así que la raíz es el WORKDIR y no hay PYTHONPATH que
#    valga. Es la misma resolución que usa pytest desde `.`.
#
#    ⚠️ A diferencia del Dockerfile de proyecto_llmops, aquí NO se copia
#       `proyecto_final/`: retail es autónomo (trae su propio agente, su propio
#       catálogo y sus propios embeddings) y no importa nada del prototipo.
#
# MULTI-STAGE, y por qué importa:
#   La etapa `builder` trae uv y compila el entorno; la final solo copia el
#   `.venv` ya resuelto. Así la imagen que se publica no lleva uv, ni cachés de
#   pip, ni herramientas de compilación — menos peso y, sobre todo, menos
#   superficie de ataque. Lo que no está en la imagen no se puede explotar.
# ==========================================================

# ---------- ETAPA 1: construir el entorno ----------
FROM python:3.12-slim AS builder

# uv oficial, copiado desde su propia imagen: sin `pip install uv`, sin red
# extra y con la versión fijada (no un 'latest' que cambia bajo tus pies).
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv

WORKDIR /srv

# Solo los manifiestos primero. Docker cachea por capa: mientras estos dos
# archivos no cambien, la instalación de dependencias (lo lento, minutos) se
# reutiliza aunque hayas tocado el código. Copiar el código antes tiraría esa
# caché en cada edición.
COPY pyproject.toml uv.lock ./

# --frozen: instala EXACTAMENTE lo del lock. Si el lock no cuadra con el
#           pyproject, falla aquí en vez de resolver algo distinto en silencio.
#           Un build reproducible es la mitad de un despliegue predecible.
# --extra llmops: retail NO tiene un extra propio en el pyproject, y este es el
#           que cubre TODAS sus dependencias reales: fastapi, uvicorn,
#           pydantic-settings, jinja2, pyyaml, redis y langfuse.
#           Es un superconjunto (arrastra pgvector y psycopg, que retail no usa)
#           y esa grasa es consciente: un extra 'retail' duplicado sería otra
#           lista de versiones que mantener sincronizada, y la divergencia entre
#           dos listas casi iguales cuesta más que unos MB de imagen.
#           No se instala `hf` (arrastra PyTorch, ~2 GB) ni `dev`: en producción
#           no se corren los tests. Ver ADR-0002.
#           ⭐ Los embeddings del caché semántico son PROPIOS y puros
#           (app/embeddings.py: bolsa de palabras, cero dependencias), así que
#           esta imagen no descarga ningún modelo — a diferencia de la de llmops.
# --no-install-project: el curso no es un paquete instalable (package = false).
RUN uv sync --frozen --extra llmops --no-install-project --no-dev

# ---------- ETAPA 2: la imagen que se despliega ----------
FROM python:3.12-slim

# Un usuario sin privilegios. Por defecto un contenedor corre como root, y un
# root dentro del contenedor es un root a un descuido de distancia del host.
RUN useradd --create-home --uid 10001 sifrah

WORKDIR /srv

# El entorno ya resuelto de la etapa anterior. Nada de uv aquí.
COPY --from=builder /srv/.venv /srv/.venv
ENV PATH="/srv/.venv/bin:$PATH"

# El código, como paquete colgando de la raíz: /srv/proyecto_retail/. Con
# WORKDIR=/srv, `import proyecto_retail.app.main` resuelve sin PYTHONPATH.
COPY --chown=sifrah:sifrah proyecto_retail/ ./proyecto_retail/

# PYTHONUNBUFFERED: sin esto, Python bufferiza stdout y los logs aparecen a
# ráfagas o se PIERDEN si el contenedor muere de golpe. Justo cuando más
# falta hacen. Es la otra mitad del logging estructurado de observability/logs.py.
ENV PYTHONUNBUFFERED=1

USER sifrah

EXPOSE 8000

# Sin --reload (recarga en cada cambio de archivo: es para desarrollar) y sin
# --workers: en contenedores se escala con más RÉPLICAS, no con más procesos
# dentro de una. Un proceso por contenedor es lo que hace que el orquestador
# pueda contarlos, matarlos y reponerlos.
#
# ⚠️ La ruta del módulo es la COMPLETA (`proyecto_retail.app.main`), igual que
#    en el `uvicorn` del README. `app.main:app` a secas importaría el paquete
#    equivocado en cuanto los dos proyectos convivan.
CMD ["uvicorn", "proyecto_retail.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
