"""
SOLUCIÓN · Ejercicio 04 — Memoria: ventana y resumen
==========================================================
⚠️ No leas esto hasta haberlo intentado.

Las tres estrategias de memoria, en un solo archivo, para que puedas
compararlas: historial completo, ventana deslizante y resumen.

Requisitos: .env con GOOGLE_API_KEY
Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_04_memoria.py
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

# Cuántos mensajes conserva la ventana (2 intercambios = 4 mensajes).
VENTANA = 4
# A partir de cuántos mensajes empezamos a resumir lo viejo.
UMBRAL_RESUMEN = 6


def crear_cadena(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres un asistente amable."),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])
    return prompt | llm


# ==================================================================
# ESTRATEGIA 1 · Historial completo (el original)
# ==================================================================
def hacer_chatear_completo(llm):
    cadena, historial = crear_cadena(llm), []

    def chatear(texto):
        r = cadena.invoke({"input": texto, "history": historial})
        historial.append(HumanMessage(content=texto))
        historial.append(AIMessage(content=r.content))
        return r.content

    return chatear, historial


# ==================================================================
# ESTRATEGIA 2 · Ventana deslizante (Parte 2)
# ==================================================================
def hacer_chatear_ventana(llm, ventana=VENTANA):
    cadena, historial = crear_cadena(llm), []

    def chatear(texto):
        r = cadena.invoke({"input": texto, "history": historial})
        historial.append(HumanMessage(content=texto))
        historial.append(AIMessage(content=r.content))

        # ⭐ Recortamos IN PLACE. Reasignar (historial = historial[-4:]) crearía
        #    una lista nueva que el closure de fuera ya no vería.
        if ventana <= 0:
            historial.clear()      # ⚠️ 'del historial[:-0]' NO borra nada: [:-0] == [:0]
        else:
            del historial[:-ventana]
        return r.content

    return chatear, historial


# ==================================================================
# ESTRATEGIA 3 · Resumir lo viejo (Parte 3)
# ==================================================================
def hacer_chatear_resumen(llm, umbral=UMBRAL_RESUMEN):
    cadena, historial = crear_cadena(llm), []

    def resumir(mensajes):
        conversacion = "\n".join(f"{m.type}: {m.content}" for m in mensajes)
        # ⭐ El prompt pide EXPLÍCITAMENTE conservar nombres y datos. Un resumen
        #    genérico ("hablaron de comida") destruiría justo lo que la memoria
        #    tenía que recordar. Este detalle es toda la diferencia.
        resumen = llm.invoke(
            "Resume esta conversación en 2 frases, conservando NOMBRES y DATOS "
            f"concretos (fechas, ciudades, preferencias):\n{conversacion}"
        )
        return AIMessage(content=f"[Resumen de lo anterior] {resumen.content}")

    def chatear(texto):
        r = cadena.invoke({"input": texto, "history": historial})
        historial.append(HumanMessage(content=texto))
        historial.append(AIMessage(content=r.content))

        if len(historial) > umbral:
            viejos, recientes = historial[:-4], historial[-4:]
            historial[:] = [resumir(viejos), *recientes]
        return r.content

    return chatear, historial


# ==================================================================
# La demo comparativa
# ==================================================================
TURNOS = [
    "Me llamo Beto y mi comida favorita es la pizza.",
    "Vivo en Lima, Perú.",
    "Trabajo como ingeniero de datos.",
    "Mi color favorito es el verde.",
    # La pregunta trampa: solo se responde recordando el turno 1 Y el turno 2.
    "¿Recuerdas mi nombre y en qué ciudad vivo?",
]


def demo(nombre, fabrica, llm):
    print(f"\n{'=' * 62}\n{nombre}\n{'=' * 62}")
    chatear, historial = fabrica(llm)
    for turno in TURNOS[:-1]:
        chatear(turno)
    respuesta = chatear(TURNOS[-1])
    print(f"🙋 {TURNOS[-1]}")
    print(f"🤖 {respuesta}")
    print(f"\n   mensajes en memoria al final: {len(historial)}")
    recuerda = "beto" in respuesta.lower() and "lima" in respuesta.lower()
    print(f"   ¿recuerda nombre Y ciudad? {'✅ sí' if recuerda else '❌ no'}")
    return recuerda


def main():
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("❌ Falta GOOGLE_API_KEY. Este ejercicio sí llama al modelo.")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.5)

    demo("ESTRATEGIA 1 · Historial completo", hacer_chatear_completo, llm)
    demo("ESTRATEGIA 2 · Ventana de 4 mensajes", hacer_chatear_ventana, llm)
    demo("ESTRATEGIA 3 · Resumen de lo viejo", hacer_chatear_resumen, llm)

    print("""
======================================================================
CONCLUSIÓN

  1. Historial completo — recuerda todo. El prompt crece sin límite y pagas
     por cada token del historial en CADA turno. Un día no cabe.

  2. Ventana de 4 — coste constante. Y no recuerda: los turnos 1 y 2 ya se
     tiraron. Ese olvido NO es un bug; es el precio exacto de la ventana.

  3. Resumen — coste constante + una llamada extra al modelo. Recuerda lo
     esencial si el prompt del resumen pidió conservar nombres y datos.
     Pierde los detalles que el resumen no salvó, y ese olvido es silencioso.

  En producción se combinan las tres: ventana de mensajes recientes + resumen
  de lo viejo + un RAG sobre el histórico completo para recuperar lo que haga
  falta bajo demanda.
======================================================================
""")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). Espera unos minutos.")
        else:
            print(f"❌ Error inesperado: {error}")
