"""
agent.py · El agente GobData en producción
==========================================
FINALIDAD:
  Ensamblar el agente con las piezas de producción: RAG con pgvector + RBAC,
  cascada de modelos (barato→caro), memoria y auditoría.

  ⭐ NO reimplementa el grafo. Llama a `proyecto_final.graph_builder.construir_agente()`
     pasándole SUS tools y SU prompt. El ciclo ReAct, el checkpointer y el
     cableado son exactamente los del prototipo, ya probados por 43 tests.

     Reimplementarlo sería el error clásico: al copiar el ensamblado se pierde
     algo por el camino. (De hecho pasó: una versión anterior de este archivo
     olvidó llamar a `registrar_auditoria` y el agente dejó de auditar.)

LÓGICA:
  create_react_agent construye por dentro el mismo ciclo ReAct:

        START -> [agente] --¿pidió una tool?--> [tools] --+
                    ^                                     |
                    +-------------------------------------+  (cicla)
                    |
                    +--¿respondió?--> END

  Lo que cambia respecto al prototipo son las TOOLS:
    - buscar_normativa      : RAG + filtro RBAC por rol del usuario.
    - evaluar_regla_calidad : salida estructurada + escritura en el log de auditoría.

⭐ construir_agente() recibe TODO por parámetro. Por eso un test puede armarlo
   con un retriever falso y un modelo falso, y verificar el cableado sin gastar
   un token ni levantar Postgres.
"""
from __future__ import annotations

from langchain_core.tools import tool

from app._proyecto_final import graph_builder
from app.config import settings


def construir_agente(
    llm,
    retriever,
    evaluador=None,
    *,
    rol: str = "analyst",
    checkpointer=None,
    prompt: str | None = None,
    ruta_auditoria=None,
):
    """Ensambla el agente GobData para producción.

    Parámetros (todos inyectados → testeables):
      llm        : modelo de chat (el barato de la cascada).
      retriever  : buscador sobre pgvector (o el in-memory de fallback).
      evaluador  : llm.with_structured_output(HallazgoCalidad). Si es None,
                   la tool de evaluación queda desactivada.
      rol        : rol del usuario que dispara esta conversación (RBAC).
      checkpointer: dónde persiste la conversación (None = MemorySaver).
      prompt     : instrucciones del agente (None = las de abajo).
      ruta_auditoria: dónde se escribe el log (None = la del prototipo).

    Delegamos el ensamblado en el prototipo: `tools` y `prompt` son los dos
    parámetros solo-por-nombre que `graph_builder` acepta justo para esto.
    """
    return graph_builder.construir_agente(
        llm,
        evaluador,
        retriever,
        checkpointer=checkpointer,
        ruta_auditoria=ruta_auditoria,
        tools=crear_tools(llm, retriever, evaluador, rol, ruta_auditoria),
        prompt=prompt or prompt_por_defecto(rol),
    )


def prompt_por_defecto(rol: str = "analyst") -> str:
    """Las instrucciones base del agente, renderizadas desde `prompts/*.yaml`.

    ⭐ El prompt NO vive aquí. Vive en `prompts/agente_gobdata.yaml`, versionado
       y con changelog. Este módulo solo lo pide y le pasa el rol. Así un cambio
       de instrucciones se revisa en el PR como lo que es —un cambio de
       comportamiento— y no como una f-string enterrada en el código.

    El prompt depende del `rol`: un 'compliance' recibe una sección extra que le
    autoriza a citar los anexos. Esa condicional vive en el YAML (Jinja2), no
    en un `if` de Python.
    """
    from prompts.loader import cargar_cacheado
    return cargar_cacheado("agente_gobdata").render(rol=rol)


def crear_tools(llm, retriever, evaluador, rol: str = "analyst", ruta_auditoria=None):
    """Las tools del agente, cableadas con el retriever y el rol del usuario.

    ⭐ buscar_normativa filtra por rol: el RAG trae lo semánticamente relevante,
       pero el RBAC quita lo que el usuario no puede ver. Así un analyst no ve
       los anexos 'restricted' aunque pregunte por ellos literalmente.
    """
    # Import diferido: rag vive en el paquete app, y así evitamos import circular.
    from app import rag as rag_mod

    @tool
    def buscar_normativa(pregunta: str) -> str:
        """Responde dudas sobre la normativa de gobierno de datos.
        Úsala cuando el usuario PREGUNTE qué dice una política o regla."""
        # recuperar() aplica el filtro RBAC según el rol inyectado aquí.
        contexto = rag_mod.recuperar(retriever, pregunta, rol=rol)
        if not contexto.strip():
            return "No encontré normativa aplicable (o no tienes acceso a ella)."
        indicacion = (
            f"Responde SOLO con esta normativa. Si no está, dilo.\n"
            f"Normativa:\n{contexto}\n\nPregunta: {pregunta}"
        )
        return llm.invoke(indicacion).content

    tools = [buscar_normativa]

    # La tool de evaluación solo se monta si hay evaluador estructurado disponible.
    if evaluador is not None:
        @tool
        def evaluar_regla_calidad(regla: str) -> str:
            """Evalúa si una regla de calidad de datos está respaldada por la
            normativa. Úsala cuando el usuario pida EVALUAR o VERIFICAR una regla."""
            # El registro de auditoría se importa aquí (perezoso): un test que
            # solo ejercita buscar_normativa no carga el módulo del prototipo.
            from app import audit_import

            contexto = rag_mod.recuperar(retriever, regla, rol=rol)
            if not contexto.strip():
                return "No tengo normativa aplicable para evaluar esa regla."

            hallazgo = evaluador.invoke(
                f"Con base en esta normativa:\n{contexto}\n\n"
                f"Evalúa si esta regla está respaldada: '{regla}'"
            )

            # ⭐ La auditoría NO es opcional: es el motivo por el que existe este
            #    agente. Cada evaluación deja rastro en disco antes de responder.
            audit_import.registrar_auditoria(hallazgo, ruta=ruta_auditoria)

            return (
                f"Evaluación -> cumple: {hallazgo.cumple} | "
                f"severidad: {hallazgo.severidad}\n"
                f"Justificación: {hallazgo.justificacion}"
            )

        tools.append(evaluar_regla_calidad)

    return tools


def construir_agente_real(rol: str | None = None, usar_pgvector: bool = True):
    """El agente de verdad: cascada de modelos + pgvector + memoria.

    ⚠️ Llama a la API del proveedor y requiere servicios levantados
    (salvo que usar_pgvector=False). Es el único sitio donde se juntan las
    piezas 'caras'.
    """
    from app import rag as rag_mod
    from app.audit_import import HallazgoCalidad
    from app.llm import crear_cascada

    llm = crear_cascada()
    evaluador = llm.with_structured_output(HallazgoCalidad)

    if usar_pgvector:
        try:
            retriever = rag_mod.construir_retriever_pgvector()
        except Exception:
            # Degradación graceful: si Postgres no responde, caemos a memoria.
            # El servicio arranca igual; pierde persistencia, no funcionalidad.
            retriever = rag_mod.construir_retriever_memoria()
    else:
        retriever = rag_mod.construir_retriever_memoria()

    return construir_agente(
        llm, retriever, evaluador, rol=rol or settings.app_rol_por_defecto
    )
