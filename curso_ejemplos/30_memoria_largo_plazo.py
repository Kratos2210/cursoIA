"""
TEMA 30 · Memoria de largo plazo: recordar ENTRE conversaciones
================================================================
FINALIDAD:
  El checkpointer del m10/m13 da memoria CONVERSACIONAL: recuerda lo dicho
  dentro de un mismo `thread_id`. Pero abre una conversación nueva (otro
  `thread_id`) y el agente no sabe quién eres. La memoria de LARGO PLAZO
  resuelve eso: hechos del usuario que sobreviven a la conversación —"me llamo
  Ana", "soy alérgica al maní", "prefiero respuestas cortas"— y que el agente
  recupera la próxima vez, aunque sea otro día y otro hilo.

  En LangGraph esto es el STORE (`langgraph.store`), una pieza APARTE del
  checkpointer:
    - checkpointer  → estado por `thread_id`      (memoria de trabajo, se olvida)
    - store         → datos por `namespace`+clave (memoria de largo plazo, persiste)

  ⭐ El núcleo (guardar / recuperar / extraer preferencias) es 100% OFFLINE y
     determinista: el `InMemoryStore` no llama a ninguna API. La parte REAL
     —un agente que consulta su memoria con una tool— va en `__main__`,
     protegida por la API key (sin llave imprime la demo y no gasta cuota).

  📐 API (verificada contra el paquete instalado, no de memoria):
       store.put(namespace: tuple, key: str, value: dict)      # guardar
       store.get(namespace: tuple, key: str) -> Item | None    # leer una
       store.search(namespace_prefix: tuple) -> list[Item]     # leer todas
     El `namespace` es una TUPLA que agrupa: usamos ("memorias", user_id) para
     que las memorias de un usuario nunca se mezclen con las de otro.

LÓGICA (paso a paso):
  1) guardar_hecho() / recuperar_hechos(): el CRUD mínimo sobre el store.
  2) extraer_preferencia(): de una frase del usuario saca (clave, valor) si hay
     algo que valga la pena recordar (determinista → testeable byte a byte).
  3) construir_agente_con_memoria(): un create_react_agent con `store=` y una
     tool que lee la memoria del usuario (la parte que SÍ usa el LLM).
  4) main(): demuestra el contraste —dos `thread_id` distintos comparten el
     store pero no el checkpointer— y, si hay llave, corre el agente real.

Requisitos: ninguno extra (solo Python + lo ya instalado).  Sin llave NO llama a la API.
Ejecuta:    uv run python 30_memoria_largo_plazo.py
"""

import re

from langgraph.store.memory import InMemoryStore


# La raíz del namespace de memorias. La tupla final es ("memorias", user_id):
# así las memorias quedan separadas POR usuario y nunca se pisan entre sí.
NAMESPACE_RAIZ = "memorias"


# ============ 1) EL CRUD MÍNIMO SOBRE EL STORE ============
def namespace_de(user_id: str) -> tuple[str, str]:
    """El cajón de memorias de UN usuario: ("memorias", user_id).

    POR QUÉ una tupla: el store organiza los datos en namespaces jerárquicos,
    como carpetas. Meter el user_id en el namespace es lo que garantiza que la
    búsqueda de un usuario jamás devuelva memorias de otro.
    """
    return (NAMESPACE_RAIZ, user_id)


def guardar_hecho(store: InMemoryStore, user_id: str, clave: str, valor: str) -> None:
    """Guarda UN hecho del usuario (p. ej. clave='nombre', valor='Ana').

    El valor va como dict porque el store guarda JSON, no strings sueltos: eso
    deja espacio para enriquecerlo luego (fecha, fuente, confianza) sin cambiar
    la forma de leerlo.
    """
    store.put(namespace_de(user_id), clave, {"dato": valor})


def recuperar_hechos(store: InMemoryStore, user_id: str) -> dict[str, str]:
    """Devuelve TODO lo que el agente recuerda de un usuario: {clave: valor}.

    `search` sobre el namespace del usuario trae todos sus items; los aplanamos
    al {clave: valor} que el prompt del agente puede leer de un vistazo.
    """
    items = store.search(namespace_de(user_id))
    return {item.key: item.value["dato"] for item in items}


# ============ 2) DECIDIR QUÉ VALE LA PENA RECORDAR ============
# Patrones deterministas: de una frase del usuario a (clave, valor). Es la
# versión simple y testeable; en producción esta extracción suele hacerla el
# propio LLM con salida estructurada (m05), pero la IDEA es la misma: no guardes
# la conversación entera, guarda el HECHO destilado.
_PATRONES = [
    (re.compile(r"\bme llamo\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)", re.I), "nombre"),
    (re.compile(r"\bsoy alérgic[oa]\s+a[l]?\s+([A-Za-zÁÉÍÓÚÑáéíóúñ ]+)", re.I), "alergia"),
    (re.compile(r"\b(?:prefiero|me gustan)\s+(?:las?\s+)?respuestas?\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)", re.I), "estilo"),
    (re.compile(r"\bvivo en\s+([A-Za-zÁÉÍÓÚÑáéíóúñ ]+)", re.I), "ciudad"),
]


def extraer_preferencia(texto: str) -> tuple[str, str] | None:
    """De una frase saca (clave, valor) si contiene un hecho memorable, o None.

    Ejemplos:
        "hola, me llamo Ana"          -> ("nombre", "Ana")
        "soy alérgica al maní"        -> ("alergia", "maní")
        "prefiero respuestas cortas"  -> ("estilo", "cortas")
    Devolver None es la respuesta correcta cuando NO hay nada que recordar: no
    todo turno aporta un hecho, y guardar ruido ensucia la memoria.
    """
    for patron, clave in _PATRONES:
        m = patron.search(texto)
        if m:
            return clave, m.group(1).strip().rstrip(".")
    return None


# ============ 3) EL AGENTE QUE CONSULTA SU MEMORIA (parte real) ============
def construir_agente_con_memoria(llm, store: InMemoryStore, user_id: str):
    """Un create_react_agent con `store=` y una tool que lee la memoria del usuario.

    La tool usa `get_store()` para alcanzar el MISMO store que le pasamos al
    agente, sin recibirlo por parámetro: LangGraph lo inyecta en tiempo de
    ejecución. Así el modelo puede decir "según recuerdo, te llamas Ana" en una
    conversación nueva, porque el store sobrevive al cambio de `thread_id`.
    """
    from langchain_core.tools import tool
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.config import get_store
    from langgraph.prebuilt import create_react_agent

    @tool
    def recordar_sobre_el_usuario() -> str:
        """Devuelve lo que se sabe del usuario (nombre, alergias, preferencias)."""
        hechos = recuperar_hechos(get_store(), user_id)
        if not hechos:
            return "No recuerdo nada de este usuario todavía."
        return "; ".join(f"{k}: {v}" for k, v in sorted(hechos.items()))

    return create_react_agent(
        llm,
        tools=[recordar_sobre_el_usuario],
        store=store,                 # la memoria de largo plazo
        checkpointer=MemorySaver(),  # la memoria de la conversación (por hilo)
    )


def main() -> None:
    import util

    store = InMemoryStore()
    ana = "user-ana"

    # --- Conversación 1: el usuario se presenta y contamos lo que aprendemos ---
    print("== Conversación 1 (thread_id='dia-1') ==\n")
    for frase in ["hola, me llamo Ana", "vivo en Lima", "soy alérgica al maní",
                  "¿qué tal el clima?"]:
        pref = extraer_preferencia(frase)
        if pref:
            guardar_hecho(store, ana, *pref)
            print(f"  «{frase}»  → recuerdo {pref[0]}={pref[1]!r}")
        else:
            print(f"  «{frase}»  → (nada que recordar)")

    # --- Conversación 2: OTRO thread_id. El checkpointer no sabría nada... ---
    print("\n== Conversación 2 (thread_id='dia-2', otro hilo) ==")
    print("  El agente abre un hilo NUEVO. La memoria de trabajo está vacía,")
    print("  pero la de largo plazo (el store) sigue ahí:")
    print(f"  recuerdo del usuario → {recuperar_hechos(store, ana)}")

    # La llamada REAL solo si hay llave: sin ella, no gastamos cuota.
    if util.requiere_llm_key() is not None:
        print("\n(⏸️  Sin API key: no llamo al modelo. Pon la llave en .env para verlo en acción.)")
        return

    print("\n== El agente real recupera la memoria en un hilo nuevo ==\n")
    try:
        agente = construir_agente_con_memoria(util.crear_llm(), store, ana)
        salida = agente.invoke(
            {"messages": [("user", "¿Qué recuerdas de mí? Dame una recomendación segura.")]},
            config={"configurable": {"thread_id": "dia-2"}},
        )
        print(f"  Respuesta: {salida['messages'][-1].content}")
    except Exception as error:  # noqa: BLE001 — cuota, red o proveedor
        if util.es_error_cuota(error):
            print(util.mensaje_cuota())
        else:
            print(f"❌ El modelo no pudo responder: {error}")


if __name__ == "__main__":
    main()
