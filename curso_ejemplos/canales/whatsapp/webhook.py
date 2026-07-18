"""
CANAL WhatsApp · webhook que le pone un canal de mensajería a tu agente
=======================================================================
FINALIDAD:
  El curso te enseñó a construir el AGENTE (m10-m15) y a servirlo por HTTP
  (m17/m25). Este anexo le pone delante un CANAL real: WhatsApp, vía
  EvolutionAPI. El agente no cambia; solo cambia por dónde entra y sale el texto.

  Arquitectura (turno a turno, NO streaming — WhatsApp es de mensajes):

    WhatsApp ──▶ EvolutionAPI ──▶ (este webhook) ──▶ responder(texto) ──▶ agente
                                        │                                    │
                                        └──── enviar_whatsapp(reply) ◀───────┘

  ⭐ FUERA DEL GATE OFFLINE (ver docs/adr/0004): necesita Docker (EvolutionAPI),
     un número de WhatsApp y una API key de LLM. No corre en la CI ni se testea.

  ⭐ El "cerebro" entra POR PARÁMETRO (`responder`), igual que el modelo se
     inyecta en todo el curso. Aquí el default es un LLM simple con
     `util.crear_llm()`; para un agente RAG de verdad, enchufa el del
     proyecto_llmops (ver la nota al final) o el `create_react_agent` del m10.

Ejecuta (local):  uv run --extra whatsapp uvicorn canales.whatsapp.webhook:app --port 8080
                  (o levanta todo con docker-compose.yml)
"""
from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Request

import util  # el mismo helper del curso: lee .env y construye el modelo activo


# ------------------------------------------------------------------
# 1) EL CEREBRO — inyectable. Default: un LLM simple. Cámbialo por tu agente.
# ------------------------------------------------------------------
_SISTEMA = (
    "Eres el asistente de la tienda por WhatsApp: responde claro, breve y amable, "
    "en el idioma del cliente. Si no sabes algo, dilo; no inventes precios ni stock."
)


def responder(texto: str, thread_id: str = "wa") -> str:
    """Convierte el mensaje del cliente en una respuesta. PUNTO DE EXTENSIÓN.

    Default: una llamada directa al LLM del `.env` (Gemini/Groq/…). Para un
    agente RAG real, reemplaza el cuerpo por una invocación a tu grafo —el mismo
    `create_react_agent` del m10 o el servicio del proyecto_llmops— usando
    `thread_id` como memoria de conversación (uno por número de WhatsApp).
    """
    llm = util.crear_llm()
    respuesta = llm.invoke([("system", _SISTEMA), ("human", texto)])
    return respuesta.content.strip()


# ------------------------------------------------------------------
# 2) SALIDA — mandar el texto de vuelta por EvolutionAPI
# ------------------------------------------------------------------
def enviar_whatsapp(numero: str, texto: str) -> None:
    """POST a EvolutionAPI para responder al remitente.

    EvolutionAPI expone `POST /message/sendText/{instancia}` con la `apikey` en
    la cabecera. `numero` es el remoteJid que llegó en el webhook.
    """
    base = os.environ["EVOLUTION_URL"].rstrip("/")
    instancia = os.environ["EVOLUTION_INSTANCE"]
    httpx.post(
        f"{base}/message/sendText/{instancia}",
        headers={"apikey": os.environ["EVOLUTION_APIKEY"]},
        json={"number": numero, "text": texto},
        timeout=30,
    ).raise_for_status()


# ------------------------------------------------------------------
# 3) ENTRADA — el webhook que EvolutionAPI llama en cada mensaje
# ------------------------------------------------------------------
def _extraer_texto(mensaje: dict) -> str:
    """WhatsApp trae el texto en `conversation` o en `extendedTextMessage.text`."""
    if "conversation" in mensaje:
        return mensaje["conversation"]
    return mensaje.get("extendedTextMessage", {}).get("text", "")


app = FastAPI(title="Canal WhatsApp del curso")


@app.get("/health")
def health() -> dict:
    return {"estado": "ok"}


@app.post("/webhook/whatsapp")
async def webhook(request: Request) -> dict:
    """Recibe el evento `messages.upsert` de EvolutionAPI y responde.

    Ignora los mensajes propios (`fromMe`) y los que no traen texto (audio,
    imagen…): este anexo enseña el canal de texto. El remoteJid es a la vez el
    destinatario de la respuesta Y la clave de memoria del hilo (un chat por
    número).
    """
    evento = await request.json()
    data = evento.get("data", {})
    clave = data.get("key", {})

    if clave.get("fromMe"):                       # no respondas a tus propios mensajes
        return {"ignorado": "fromMe"}

    texto = _extraer_texto(data.get("message", {}))
    numero = clave.get("remoteJid", "")
    if not texto or not numero:                   # sin texto (media) o sin remitente
        return {"ignorado": "sin_texto"}

    respuesta = responder(texto, thread_id=numero)
    enviar_whatsapp(numero, respuesta)
    return {"ok": True}


# --- ¿Cómo enchufo mi agente RAG del proyecto_llmops en vez del LLM simple? ---
# Construye el agente una vez al arrancar y úsalo en `responder`. Como el agente
# del LLMOps responde en streaming, junta sus tokens en un solo texto (WhatsApp
# no hace streaming):
#
#   from app.agent import construir_agente_real          # requiere el stack LLMOps
#   from app.streaming import tokens_del_agente
#   _agente = construir_agente_real(rol="analyst")
#   async def responder_rag(texto, thread_id="wa"):
#       partes = [t async for t in tokens_del_agente(_agente, texto, thread_id)]
#       return "".join(partes)
