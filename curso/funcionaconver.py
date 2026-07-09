import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# 🌟 LA NUEVA MAGIA: Importaciones de LangGraph para Agentes con Memoria
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# ==========================================
# 1. CONFIGURACIÓN DEL CEREBRO
# ==========================================
load_dotenv()

# Usamos Gemini 2.0 Flash con temperatura baja para que sea un asistente preciso
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1
)

# ==========================================
# 2. CREACIÓN DE HERRAMIENTAS DEL NEGOCIO
# ==========================================
@tool
def consultar_disponibilidad(sede: str, especialidad: str) -> str:
    """
    Útil para consultar si hay horarios disponibles en una ciudad para una especialidad médica.
    Ingresa la 'sede' (ej. Lima, Cusco, Arequipa) y la 'especialidad' (ej. Fisioterapia, Psicología).
    """
    # Simulamos una consulta a tu base de datos real
    sedes_activas = ["lima", "cusco", "arequipa"]
    
    if sede.lower() in sedes_activas:
        return f"✅ Sistema: Hay 3 horarios disponibles para {especialidad} esta semana en {sede.capitalize()}."
    else:
        return f"❌ Sistema: Lo sentimos, aún no tenemos sede en {sede.capitalize()}."

cinturon_herramientas = [consultar_disponibilidad]

# ==========================================
# 3. CONFIGURACIÓN DE LA MEMORIA (LangGraph)
# ==========================================
# Creamos un "disco duro" temporal en la memoria RAM para guardar las charlas
memoria = MemorySaver()

# ==========================================
# 4. CREACIÓN DEL AGENTE CONVERSACIONAL
# ==========================================
# LangGraph une el cerebro, las herramientas y la memoria automáticamente
agente_bot = create_react_agent(
    llm, 
    tools=cinturon_herramientas, 
    checkpointer=memoria
)

# ==========================================
# 5. PRUEBA DEL HILO DE CONVERSACIÓN
# ==========================================
# Creamos un "identificador de sesión" (Como el ID del chat de WhatsApp de un paciente)
configuracion_chat = {"configurable": {"thread_id": "paciente_001"}}

print("--- MENSAJE 1 ---")
respuesta_1 = agente_bot.invoke(
    {"messages": [("user", "Hola, me llamo Roberto y necesito ayuda con un dolor de espalda, busco fisioterapia.")]}, 
    configuracion_chat
)
# Extraemos y mostramos la respuesta final de la IA
print(f"🤖 Bot: {respuesta_1['messages'][-1].content}\n")

print("--- MENSAJE 2 (Prueba de Memoria y Herramienta) ---")
respuesta_2 = agente_bot.invoke(
    {"messages": [("user", "¿Tienen disponibilidad en Arequipa para lo que necesito?")]}, 
    configuracion_chat
)
print(f"🤖 Bot: {respuesta_2['messages'][-1].content}\n")