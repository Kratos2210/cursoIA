import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# ==========================================
# 1. CONFIGURACIÓN DEL CEREBRO
# ==========================================
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,  # 0 = máxima precisión, ideal para decidir/usar herramientas
)

# ==========================================
# 2. CREACIÓN DE LA HERRAMIENTA (TOOL)
# ==========================================
@tool
def obtener_clima_actual(latitud: float, longitud: float) -> str:
    """
    Obtiene la temperatura actual en grados Celsius para unas coordenadas específicas.
    Útil para cuando el usuario pregunta por el clima o la temperatura de un lugar.
    """
    url_base = "https://api.open-meteo.com/v1/forecast"
    parametros = {
        "latitude": latitud,
        "longitude": longitud,
        "current_weather": True,
    }

    try:
        # MEJORA 1: timeout SIEMPRE. Si la API tarda >10s, cortamos y no colgamos el programa.
        respuesta = requests.get(url_base, params=parametros, timeout=10)
        respuesta.raise_for_status()  # lanza excepción si el status NO es 2xx
        datos = respuesta.json()
        temperatura = datos["current_weather"]["temperature"]
        return f"La temperatura actual es {temperatura}°C"
    except requests.exceptions.RequestException as e:
        # MEJORA 2: capturamos errores de red (sin internet, timeout, status malo)
        return f"Error al consultar la API del clima: {e}"
    except KeyError:
        # Por si la API cambia el formato y no viene 'current_weather'
        return "La API respondió pero no encontré el dato de temperatura."


# ==========================================
# 3. EQUIPAR A LA IA (BINDING)
# ==========================================
herramientas = [obtener_clima_actual]
# MEJORA 3: un diccionario nombre -> función para ejecutar CUALQUIER tool que pida el modelo,
# sin escribir if/else por cada una. Escala a 50 herramientas igual de fácil.
mapa_herramientas = {t.name: t for t in herramientas}
llm_con_herramientas = llm.bind_tools(herramientas)

# ==========================================
# 4. PRUEBA 1: Pregunta normal (no necesita herramientas)
# ==========================================
print("--- PRUEBA 1: Pregunta normal (Sin usar herramientas) ---")
respuesta_1 = llm_con_herramientas.invoke("Hola, ¿qué es la Inteligencia Artificial?")
print(f"Respuesta de la IA: {respuesta_1.content}\n")

# ==========================================
# 5. PRUEBA 2: EL CICLO COMPLETO DE UN AGENTE ⭐
# ==========================================
# Este es el corazón del aprendizaje: un agente NO es solo "el modelo pide una tool".
# El ciclo completo tiene 4 pasos:
#   (A) El humano pregunta
#   (B) El LLM decide usar una o más tools (routing)
#   (C) TÚ ejecutas las tools y le devuelves los resultados al LLM
#   (D) El LLM redacta la respuesta final en lenguaje natural
print("--- PRUEBA 2: Ciclo completo (routing + ejecución + respuesta natural) ---")

# (A) Guardamos la conversación como una LISTA de mensajes (así el LLM tiene contexto)
mensajes = [
    HumanMessage(content="¿Cuál es el clima actual en las coordenadas -16.40 y -71.53?")
]

# (B) El LLM decide. Puede devolver texto o pedir herramientas (tool_calls)
respuesta_ia = llm_con_herramientas.invoke(mensajes)
mensajes.append(respuesta_ia)  # guardamos su decisión en el historial

if respuesta_ia.tool_calls:
    print("🤖 ¡La IA decidió usar herramienta(s)!")

    # (C) Iteramos TODAS las tools que pidió (puede pedir varias a la vez)
    for llamada in respuesta_ia.tool_calls:
        print(f"   → Herramienta: {llamada['name']} | Args: {llamada['args']}")

        tool_elegida = mapa_herramientas[llamada["name"]]
        resultado = tool_elegida.invoke(llamada["args"])
        print(f"   → Resultado real de la API: {resultado}")

        # Clave: devolvemos el resultado como ToolMessage, enlazado por tool_call_id.
        # Ese id le dice al LLM "esta respuesta corresponde a la tool que pediste".
        mensajes.append(
            ToolMessage(content=str(resultado), tool_call_id=llamada["id"])
        )

    # (D) Segundo invoke: ahora el LLM ya "vio" el resultado y redacta la respuesta final
    respuesta_final = llm_con_herramientas.invoke(mensajes)
    print(f"\n💬 Respuesta final natural: {respuesta_final.content}")
else:
    # Si no pidió tools, su respuesta directa ya es la final
    print(respuesta_ia.content)
