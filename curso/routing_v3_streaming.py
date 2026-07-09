import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# ============================================================
# ROUTING v3 — Ciclo completo del agente + STREAMING
# ------------------------------------------------------------
# Novedad vs v2: la respuesta final NO aparece de golpe.
# La "vemos escribirse" token a token, como en ChatGPT.
# ============================================================

# ==========================================
# 1. CONFIGURACIÓN DEL CEREBRO
# ==========================================
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,  # precisión máxima para decidir/usar herramientas
)

# ==========================================
# 2. HERRAMIENTA (TOOL)
# ==========================================
@tool
def obtener_clima_actual(latitud: float, longitud: float) -> str:
    """
    Obtiene la temperatura actual en grados Celsius para unas coordenadas específicas.
    Útil para cuando el usuario pregunta por el clima o la temperatura de un lugar.
    """
    url_base = "https://api.open-meteo.com/v1/forecast"
    parametros = {"latitude": latitud, "longitude": longitud, "current_weather": True}
    try:
        respuesta = requests.get(url_base, params=parametros, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return f"La temperatura actual es {datos['current_weather']['temperature']}°C"
    except requests.exceptions.RequestException as e:
        return f"Error al consultar la API del clima: {e}"
    except KeyError:
        return "La API respondió pero no encontré el dato de temperatura."


# ==========================================
# 3. EQUIPAR A LA IA (BINDING)
# ==========================================
herramientas = [obtener_clima_actual]
mapa_herramientas = {t.name: t for t in herramientas}
llm_con_herramientas = llm.bind_tools(herramientas)


# ==========================================
# 4. FUNCIÓN REUTILIZABLE: EL CICLO COMPLETO CON STREAMING ⭐
# ==========================================
def responder_con_agente(pregunta: str) -> None:
    """
    Ejecuta el ciclo de 4 pasos de un agente:
      (A) humano pregunta -> (B) LLM decide tools -> (C) ejecutamos -> (D) respuesta final EN STREAMING
    """
    # (A) La conversación es una LISTA de mensajes
    mensajes = [HumanMessage(content=pregunta)]

    # (B) El LLM decide. Aquí usamos invoke (no stream) porque necesitamos
    #     ver los tool_calls COMPLETOS antes de ejecutar nada.
    respuesta_ia = llm_con_herramientas.invoke(mensajes)
    mensajes.append(respuesta_ia)

    # Caso simple: no pidió herramientas -> su texto ya es la respuesta final.
    if not respuesta_ia.tool_calls:
        print(f"💬 {respuesta_ia.content}")
        return

    # (C) Ejecutamos TODAS las herramientas que pidió
    print("🤖 La IA decidió usar herramienta(s):")
    for llamada in respuesta_ia.tool_calls:
        print(f"   → {llamada['name']} | args: {llamada['args']}")
        tool_elegida = mapa_herramientas[llamada["name"]]
        resultado = tool_elegida.invoke(llamada["args"])
        print(f"   → resultado: {resultado}")
        mensajes.append(ToolMessage(content=str(resultado), tool_call_id=llamada["id"]))

    # (D) STREAMING de la respuesta final ⭐
    #     .stream() devuelve "trocitos" (AIMessageChunk). Imprimimos cada .content
    #     sin salto de línea (end="") y forzamos que salga al instante (flush=True).
    print("\n💬 Respuesta final (streaming): ", end="", flush=True)
    for chunk in llm_con_herramientas.stream(mensajes):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print("\n")  # salto de línea al terminar


# ==========================================
# 5. PRUEBAS
# ==========================================
print("--- PRUEBA 1: Pregunta normal (sin herramientas) ---")
responder_con_agente("Hola, ¿qué es la Inteligencia Artificial en una frase?")

print("--- PRUEBA 2: Pregunta de clima (ciclo completo + streaming) ---")
responder_con_agente("¿Cuál es el clima actual en las coordenadas -16.40 y -71.53?")
