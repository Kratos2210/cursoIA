"""
graph_builder.py · El armado del agente
========================================
FINALIDAD:
  Juntar las piezas (modelo + tools + memoria + personalidad) y devolver un
  agente listo para conversar. Nada más. Este archivo no lee archivos, no
  pide llaves y no imprime: solo ensambla.

LÓGICA:
  create_react_agent construye por dentro un StateGraph con este ciclo:

        START -> [agente] --¿pidió una tool?--> [tools] --+
                    ^                                     |
                    +-------------------------------------+
                    |
                    +--¿respondió?--> END

  El modelo mira los mensajes, decide si necesita una tool, la llama, ve el
  resultado (un ToolMessage) y vuelve a decidir. Repite hasta que responde.
  Es el patrón ReAct: Razonar -> Actuar -> Observar.

  ⭐ construir_agente() recibe TODO por parámetro (inyección de dependencias).
     Por eso un test puede armarlo con un modelo falso y un retriever falso,
     y verificar el cableado del grafo sin gastar un solo token.
"""

from langgraph.prebuilt import create_react_agent

import config
import persistence
import tools as tools_mod


def construir_agente(llm, evaluador, retriever, checkpointer=None, ruta_auditoria=None):
    """Ensambla el agente GobData.

    Parámetros:
      llm         : modelo de chat que conversa y decide.
      evaluador   : llm.with_structured_output(HallazgoCalidad).
      retriever   : el buscador sobre la normativa.
      checkpointer: dónde persiste la conversación (None = MemorySaver).
      ruta_auditoria: dónde escribir el log (None = la ruta del proyecto).
    """
    return create_react_agent(
        llm,
        tools=tools_mod.crear_tools(llm, evaluador, retriever, ruta_auditoria),
        # Sin checkpointer, el agente olvida todo entre invocaciones.
        checkpointer=checkpointer or persistence.crear_checkpointer(),
        prompt=config.INSTRUCCIONES_AGENTE,
    )


def construir_agente_real():
    """El agente de verdad: modelo Gemini + RAG sobre normativa.txt.

    ⚠️ Llama a la API (vectoriza la normativa). Requiere GOOGLE_API_KEY.
    Es el único sitio del proyecto donde se juntan las piezas 'caras'.
    """
    import audit
    import rag

    config.validar_entorno()
    llm = config.crear_llm()
    evaluador = llm.with_structured_output(audit.HallazgoCalidad)
    retriever = rag.construir_retriever()
    return construir_agente(llm, evaluador, retriever)
