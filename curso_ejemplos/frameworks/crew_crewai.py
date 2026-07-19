"""
FRAMEWORKS · Orquestación por ROLES con CrewAI (el "bus con conductor")
=======================================================================
FINALIDAD:
  El m15 te enseñó el patrón supervisor en LangGraph, a mano: tú defines el grafo,
  los nodos y las transiciones. CrewAI sube el nivel de abstracción: describes
  ROLES y TAREAS, y la "crew" coordina quién hace qué. Este anexo vuelve
  EJECUTABLE el snippet que el m26 solo mostraba de forma ilustrativa.

  La lección (m26): "más alto nivel = menos control". Aquí no ves el grafo; das
  roles y confías en que CrewAI encadene investigador -> redactor. Cómodo para
  prototipar una colaboración legible; malo cuando necesitas auditar cada paso.

  ⭐ FUERA DEL GATE OFFLINE (ver docs/adr/0006): extra opcional
     (`uv sync --extra crewai`), NO se testea en la CI. Necesita una API de LLM
     con cuota (el endpoint OpenAI-compatible del .env).

Ejecuta:  uv run --extra crewai python frameworks/crew_crewai.py
"""
from __future__ import annotations

import os

from crewai import Agent, Crew, Process, Task, LLM


def _llm() -> LLM:
    """El LLM de CrewAI apuntado al MISMO endpoint OpenAI-compatible del .env.

    CrewAI usa LiteLLM por dentro: el modelo se nombra `proveedor/modelo`.
    VERIFICA el id actual en la web del proveedor (aquí, Groq como ejemplo).
    """
    return LLM(
        model=os.environ.get("CREWAI_MODEL", "groq/llama-3.3-70b-versatile"),  # VERIFICA
        base_url=os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        api_key=os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY", ""),
        temperature=0,
    )


def construir_crew() -> Crew:
    """Dos roles y sus tareas; la 'crew' los ejecuta en secuencia.

    Fíjate en lo que NO escribes: ni grafo, ni estado, ni aristas condicionales.
    Das el `role`/`goal`/`backstory` y CrewAI arma el prompt y encadena. Es el
    m15 (investigador -> redactor) sin el `StateGraph` a la vista.
    """
    llm = _llm()

    investigador = Agent(
        role="Investigador",
        goal="Reunir 3 datos concretos y fiables sobre el tema pedido",
        backstory="Analista meticuloso al que le encanta citar la fuente exacta.",
        llm=llm,
        verbose=True,
    )
    redactor = Agent(
        role="Redactor",
        goal="Convertir los hallazgos en un párrafo claro para un cliente",
        backstory="Escribes simple y directo; odias la jerga vacía.",
        llm=llm,
        verbose=True,
    )

    investigar = Task(
        description="Investiga el estado del arte de los agentes de IA en 2026.",
        expected_output="3 hallazgos en viñetas, cada uno con su fuente.",
        agent=investigador,
    )
    redactar = Task(
        description="Redacta un párrafo de 4 frases a partir de los hallazgos.",
        expected_output="Un párrafo claro, sin viñetas, listo para enviar.",
        agent=redactor,
        context=[investigar],   # el redactor recibe la salida del investigador
    )

    return Crew(
        agents=[investigador, redactor],
        tasks=[investigar, redactar],
        process=Process.sequential,   # investigador -> redactor, en orden
    )


def main() -> None:
    resultado = construir_crew().kickoff()   # el alto nivel: das roles, no el grafo
    print("\n===== RESULTADO DE LA CREW =====\n")
    print(resultado)


if __name__ == "__main__":
    main()
