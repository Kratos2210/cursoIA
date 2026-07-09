"""
state.py · El estado que viaja por el grafo
============================================
FINALIDAD:
  Declarar, en un solo sitio, la "carpeta" que los nodos del agente se pasan
  entre sí. En LangGraph, el estado ES el contrato del grafo.

LÓGICA:
  Un agente conversacional necesita, como mínimo, la lista de mensajes.
  LangGraph trae ese estado ya hecho: MessagesState.

  ⭐ El detalle que confunde a todo el mundo: los campos del estado no se
     REEMPLAZAN, se COMBINAN según su 'reducer'. El campo 'messages' usa el
     reducer add_messages, que AÑADE los mensajes nuevos a los viejos en vez
     de pisarlos. Por eso un nodo devuelve {"messages": [respuesta]} y no
     pierde la conversación anterior.

  create_react_agent (el que usa graph_builder.py) construye por dentro un
  grafo con exactamente este estado. Lo declaramos explícito aquí para que
  puedas ver qué hay dentro y, si quieres, extenderlo.
"""

from langgraph.graph import MessagesState


class EstadoAgente(MessagesState):
    """El estado del asistente GobData.

    Hereda de MessagesState, que ya aporta:
        messages: Annotated[list[BaseMessage], add_messages]

    Para EXTENDERLO (ejercicio del curso), añade campos aquí. Por ejemplo,
    llevar la cuenta de los hallazgos de la sesión:

        hallazgos_registrados: int

    Y entonces un nodo podría devolver {"hallazgos_registrados": n + 1}.
    Ojo: sin un reducer, un campo nuevo se REEMPLAZA en cada actualización.
    """
