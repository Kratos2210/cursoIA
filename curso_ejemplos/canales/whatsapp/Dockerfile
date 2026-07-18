# Imagen del webhook del canal WhatsApp. El contexto de build es la RAÍZ de
# curso_ejemplos (ver docker-compose.yml), para copiar util.py y canales/.
FROM python:3.12-slim

WORKDIR /app

# Solo lo que el webhook necesita — no el curso entero.
RUN pip install --no-cache-dir \
    fastapi uvicorn httpx python-dotenv \
    langchain-google-genai langchain-openai

COPY util.py .
COPY canales ./canales

EXPOSE 8080
CMD ["uvicorn", "canales.whatsapp.webhook:app", "--host", "0.0.0.0", "--port", "8080"]
