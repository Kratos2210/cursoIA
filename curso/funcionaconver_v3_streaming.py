import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import AIMessageChunk
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# ============================================================
# CONVERSACIONAL v3 — STREAMING + 2 HERRAMIENTAS
# ------------------------------------------------------------
# Novedades vs v2:
#   1) La respuesta se ve "escribirse" token a token (streaming).
#   2) Hay DOS herramientas: consultar disponibilidad y agendar cita.
#      Así estudias cómo el agente ELIGE la herramienta correcta según
#      la intención del paciente (consultar vs. reservar).
# ============================================================

# ==========================================
# 1. CEREBRO
# ==========================================
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)

# ==========================================
# 2. HERRAMIENTAS DEL NEGOCIO (ahora son DOS) ⭐
# ==========================================
@tool
def consultar_disponibilidad(sede: str, especialidad: str) -> str:
    """
    Consulta si HAY horarios disponibles en una sede para una especialidad médica.
    Úsala cuando el paciente PREGUNTA si hay cupos (aún no confirma nada).
    Ingresa 'sede' (ej. Lima, Cusco, Arequipa) y 'especialidad' (ej. Fisioterapia).
    """
    sedes_activas = ["lima", "cusco", "arequipa"]
    if sede.lower() in sedes_activas:
        return f"✅ Sistema: Hay 3 horarios para {especialidad} esta semana en {sede.capitalize()}."
    return f"❌ Sistema: Aún no tenemos sede en {sede.capitalize()}."


@tool
def agendar_cita(sede: str, especialidad: str, nombre_paciente: str, dia: str) -> str:
    """
    RESERVA/AGENDA una cita concreta. Úsala SOLO cuando el paciente CONFIRMA
    que quiere reservar y ya tienes: sede, especialidad, su nombre y el día.
    Si falta algún dato, NO la uses: pregunta primero el dato que falta.
    """
    codigo = f"CITA-{abs(hash(nombre_paciente + dia)) % 10000:04d}"
    return (
        f"📅 Sistema: Cita CONFIRMADA para {nombre_paciente} — {especialidad} "
        f"en {sede.capitalize()} el {dia}. Código de reserva: {codigo}"
    )


cinturon_herramientas = [consultar_disponibilidad, agendar_cita]

# ==========================================
# 3. MEMORIA
# ==========================================
memoria = MemorySaver()

# ==========================================
# 4. AGENTE CON PERSONALIDAD
# ==========================================
INSTRUCCIONES = """
Eres 'Salud+', el asistente virtual de una red de clínicas de fisioterapia en Perú.
Reglas:
- Sé cálido, cercano y profesional. Usa el nombre del paciente si lo conoces.
- Si PREGUNTAN si hay cupos -> usa consultar_disponibilidad.
- Si CONFIRMAN que quieren reservar -> usa agendar_cita, pero solo si tienes
  sede, especialidad, nombre y día. Si falta un dato, pídelo antes de agendar.
- Nunca inventes disponibilidad ni citas.
- Responde en español, breve y claro.
"""

agente_bot = create_react_agent(
    llm,
    tools=cinturon_herramientas,
    checkpointer=memoria,
    prompt=INSTRUCCIONES,
)


# ==========================================
# 5. FUNCIÓN DE STREAMING ⭐
# ==========================================
def hablar_streaming(texto_usuario: str, config: dict) -> None:
    """
    Envía un mensaje y muestra la respuesta EN STREAMING (token a token).

    Clave: stream_mode="messages" hace que el agente emita trocitos de mensaje
    a medida que el LLM los genera. Cada iteración devuelve una tupla:
        (chunk, metadata)
    - 'chunk' puede ser texto del LLM (AIMessageChunk) o resultado de una tool.
    - Solo imprimimos los AIMessageChunk con contenido (el texto para el paciente).
    """
    print("🤖 Salud+: ", end="", flush=True)
    try:
        for chunk, _metadata in agente_bot.stream(
            {"messages": [("user", texto_usuario)]},
            config,
            stream_mode="messages",
        ):
            # Filtramos: solo texto del asistente. Cuando el modelo está "decidiendo"
            # una herramienta, el chunk viene sin content -> lo ignoramos.
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                print(chunk.content, end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\n⚠️  Error al hablar con el bot: {e}\n")


# ==========================================
# 6. GUION DE PRUEBA (estudia qué tool elige en cada turno)
# ==========================================
configuracion_chat = {"configurable": {"thread_id": "paciente_002"}}

print("--- TURNO 1: se presenta (no debería usar ninguna tool) ---")
hablar_streaming(
    "Hola, soy Roberto y tengo un dolor de espalda; me interesa fisioterapia.",
    configuracion_chat,
)

print("--- TURNO 2: PREGUNTA cupos -> debería usar consultar_disponibilidad ---")
hablar_streaming("¿Tienen disponibilidad en Arequipa para eso?", configuracion_chat)

print("--- TURNO 3: CONFIRMA reserva -> debería usar agendar_cita ---")
# Fíjate: gracias a la memoria, el bot ya sabe que es Roberto y que quiere
# fisioterapia en Arequipa. Solo le falta el día, así que debería pedirlo o agendar.
hablar_streaming("Perfecto, resérvame una cita para el viernes.", configuracion_chat)


# ==========================================
# 7. (OPCIONAL) MODO CHAT INTERACTIVO
# ==========================================
# Descomenta para chatear tú y ver el streaming en vivo. Escribe 'salir' para terminar.
#
# print("--- MODO CHAT (escribe 'salir' para terminar) ---")
# while True:
#     entrada = input("Tú: ")
#     if entrada.strip().lower() in ("salir", "exit", "chau"):
#         print("👋 ¡Hasta pronto!")
#         break
#     hablar_streaming(entrada, configuracion_chat)
