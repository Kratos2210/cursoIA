import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# LangGraph: agentes con memoria listos para usar
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# ==========================================
# 1. CONFIGURACIÓN DEL CEREBRO
# ==========================================
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,  # un toque de naturalidad para conversar
)

# ==========================================
# 2. HERRAMIENTAS DEL NEGOCIO
# ==========================================
@tool
def consultar_disponibilidad(sede: str, especialidad: str) -> str:
    """
    Útil para consultar si hay horarios disponibles en una ciudad para una especialidad médica.
    Ingresa la 'sede' (ej. Lima, Cusco, Arequipa) y la 'especialidad' (ej. Fisioterapia, Psicología).
    """
    sedes_activas = ["lima", "cusco", "arequipa"]
    if sede.lower() in sedes_activas:
        return f"✅ Sistema: Hay 3 horarios disponibles para {especialidad} esta semana en {sede.capitalize()}."
    return f"❌ Sistema: Lo sentimos, aún no tenemos sede en {sede.capitalize()}."


cinturon_herramientas = [consultar_disponibilidad]

# ==========================================
# 3. MEMORIA (LangGraph)
# ==========================================
memoria = MemorySaver()

# ==========================================
# 4. AGENTE CONVERSACIONAL CON PERSONALIDAD ⭐
# ==========================================
# MEJORA 1: el parámetro `prompt` le da ROL, TONO y REGLAS al bot.
# Esto es lo que convierte un demo en un asistente de marca.
INSTRUCCIONES = """
Eres 'Salud+', el asistente virtual de una red de clínicas de fisioterapia en Perú.
Reglas:
- Sé cálido, cercano y profesional. Trata al paciente por su nombre si lo conoces.
- Cuando pregunten por horarios, USA la herramienta consultar_disponibilidad.
- Nunca inventes disponibilidad: si la herramienta dice que no hay sede, ofrece alternativas.
- Responde siempre en español, breve y claro.
"""

agente_bot = create_react_agent(
    llm,
    tools=cinturon_herramientas,
    checkpointer=memoria,
    prompt=INSTRUCCIONES,  # <- la "personalidad" del agente
)


# ==========================================
# 5. FUNCIÓN AUXILIAR PARA HABLAR CON EL BOT
# ==========================================
def hablar(texto_usuario: str, config: dict) -> None:
    """Envía un mensaje al agente y muestra su respuesta. Maneja errores."""
    try:
        respuesta = agente_bot.invoke(
            {"messages": [("user", texto_usuario)]},
            config,
        )
        print(f"🤖 Salud+: {respuesta['messages'][-1].content}\n")
    except Exception as e:
        # MEJORA 2: si Gemini falla (cuota, red), avisamos en vez de reventar
        print(f"⚠️  Ocurrió un error al hablar con el bot: {e}\n")


# ==========================================
# 6. PRUEBA AUTOMÁTICA (memoria + herramienta)
# ==========================================
# El thread_id identifica la sesión (como el número de WhatsApp del paciente)
configuracion_chat = {"configurable": {"thread_id": "paciente_001"}}

print("--- MENSAJE 1 ---")
hablar(
    "Hola, me llamo Roberto y necesito ayuda con un dolor de espalda, busco fisioterapia.",
    configuracion_chat,
)

print("--- MENSAJE 2 (prueba de MEMORIA + HERRAMIENTA) ---")
# Fíjate: no repite "fisioterapia". El bot lo recuerda gracias a la memoria del thread.
hablar("¿Tienen disponibilidad en Arequipa para lo que necesito?", configuracion_chat)


# ==========================================
# 7. (OPCIONAL) MODO CHAT INTERACTIVO ⭐
# ==========================================
# MEJORA 3: descomenta este bloque para chatear tú mismo y SENTIR la memoria.
# Escribe 'salir' para terminar.
#
# print("--- MODO CHAT (escribe 'salir' para terminar) ---")
# while True:
#     entrada = input("Tú: ")
#     if entrada.strip().lower() in ("salir", "exit", "chau"):
#         print("👋 ¡Hasta pronto!")
#         break
#     hablar(entrada, configuracion_chat)
