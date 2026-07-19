# ==========================================================
# Dockerfile · La imagen del servicio LLMOps de GobData
# ==========================================================
# FINALIDAD:
#   Convertir "corre en mi máquina" en un artefacto que se despliega. Hasta
#   ahora el docker-compose levantaba solo la INFRAESTRUCTURA (Postgres, Redis,
#   Langfuse) y la app se arrancaba a mano con `uvicorn --reload`. Eso no es
#   desplegable: no hay nada que subir a un servidor.
#
# ⚠️ EL CONTEXTO DE BUILD ES `curso_ejemplos/`, NO ESTA CARPETA.
#    Se construye así (fíjate en el punto final):
#
#      docker build -f proyecto_llmops/Dockerfile -t gobdata-llmops .
#
#    Tiene que ser así porque el servicio necesita TRES cosas del nivel de
#    arriba: el `pyproject.toml` (que es el canon de dependencias del curso),
#    el `uv.lock` y la carpeta `proyecto_final/` — llmops REUTILIZA el agente
#    del prototipo (ver app/_proyecto_final.py) y lee su `normativa.txt`.
#    Esa relación de hermandad entre carpetas se conserva dentro de la imagen.
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
# --extra llmops: FastAPI, pgvector, redis, langfuse, fastembed.
#           No se instala `hf` (arrastra PyTorch, ~2 GB) ni `dev`: en producción
#           no se corren los tests. Ver ADR-0002.
# --no-install-project: el curso no es un paquete instalable (package = false).
RUN uv sync --frozen --extra llmops --no-install-project --no-dev

# ---------- ETAPA 2: la imagen que se despliega ----------
FROM python:3.12-slim

# Un usuario sin privilegios. Por defecto un contenedor corre como root, y un
# root dentro del contenedor es un root a un descuido de distancia del host.
RUN useradd --create-home --uid 10001 gobdata

WORKDIR /srv

# El entorno ya resuelto de la etapa anterior. Nada de uv aquí.
COPY --from=builder /srv/.venv /srv/.venv
ENV PATH="/srv/.venv/bin:$PATH"

# El código. `proyecto_final` NO es opcional: llmops importa su
# `construir_agente()` y lee su `normativa.txt` (ver app/_proyecto_final.py).
COPY --chown=gobdata:gobdata proyecto_final/ ./proyecto_final/
COPY --chown=gobdata:gobdata proyecto_llmops/ ./proyecto_llmops/

# Para que `import app.config` funcione igual que bajo pytest (que lo resuelve
# con el `pythonpath` del pyproject, config que uvicorn no lee).
ENV PYTHONPATH=/srv/proyecto_llmops

# PYTHONUNBUFFERED: sin esto, Python bufferiza stdout y los logs aparecen a
# ráfagas o se PIERDEN si el contenedor muere de golpe. Justo cuando más
# falta hacen. Es la otra mitad del logging estructurado de observability/logs.py.
ENV PYTHONUNBUFFERED=1

# El modelo de embeddings (~220 MB) se descarga la primera vez y se cachea aquí.
# Con un volumen montado en esta ruta, no se re-descarga en cada arranque.
ENV FASTEMBED_CACHE_PATH=/srv/.cache/fastembed
RUN mkdir -p /srv/.cache/fastembed && chown -R gobdata:gobdata /srv/.cache

USER gobdata

EXPOSE 8000

# Sin --reload (recarga en cada cambio de archivo: es para desarrollar) y sin
# --workers: en contenedores se escala con más RÉPLICAS, no con más procesos
# dentro de una. Un proceso por contenedor es lo que hace que el orquestador
# pueda contarlos, matarlos y reponerlos.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
