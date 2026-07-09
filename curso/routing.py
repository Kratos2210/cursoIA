import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# ==========================================
# 1. CONFIGURACIÓN DEL CEREBRO
# ==========================================
load_dotenv()

# Usamos temperatura 0 porque queremos precisión al usar herramientas
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)

# ==========================================
# 2. CREACIÓN DE LA HERRAMIENTA (TOOL)
# ==========================================
# El decorador @tool convierte la función en algo que Gemini puede entender
@tool
def obtener_clima_actual(latitud: float, longitud: float) -> str:
    """
    Obtiene la temperatura actual en grados Celsius para unas coordenadas específicas.
    Útil para cuando el usuario pregunta por el clima o la temperatura de un lugar.
    """
    url_base = "https://api.open-meteo.com/v1/forecast"
    parametros = {
        'latitude': latitud,
        'longitude': longitud,
        'current_weather': True
    }
    
    respuesta = requests.get(url_base, params=parametros)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        temperatura = datos['current_weather']['temperature']
        return f"La temperatura actual es {temperatura}°C"
    else:
        return "Error al consultar la API del clima."

# ==========================================
# 3. EQUIPAR A LA IA (BINDING)
# ==========================================
# Aquí le entregamos el "cinturón de herramientas" a Gemini
herramientas = [obtener_clima_actual]
llm_con_herramientas = llm.bind_tools(herramientas)

# ==========================================
# 4. PRUEBAS DE ENRUTAMIENTO (ROUTING)
# ==========================================
print("--- PRUEBA 1: Pregunta normal (Sin usar herramientas) ---")
respuesta_1 = llm_con_herramientas.invoke("Hola, ¿qué es la Inteligencia Artificial?")
print(f"Respuesta de la IA: {respuesta_1.content}\n")

print("--- PRUEBA 2: Pregunta que requiere una herramienta (Enrutamiento) ---")
# Coordenadas de Arequipa, Perú
respuesta_2 = llm_con_herramientas.invoke("¿Cuál es el clima actual en las coordenadas -16.40 y -71.53?")

# Verificamos si Gemini decidió "enrutar" la petición hacia una herramienta
if respuesta_2.tool_calls:
    print("🤖 ¡La IA decidió usar una herramienta!")
    llamada = respuesta_2.tool_calls[0]
    print(f"Herramienta elegida: {llamada['name']}")
    print(f"Argumentos extraídos: {llamada['args']}")
    
    # Ejecutamos la herramienta con los datos que la IA preparó
    resultado_herramienta = obtener_clima_actual.invoke(llamada['args'])
    print(f"Resultado real de la API: {resultado_herramienta}")
else:
    print(respuesta_2.content)