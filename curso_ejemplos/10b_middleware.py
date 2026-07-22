"""
TEMA 10b · Middleware de agentes (create_agent)
===============================================
FINALIDAD:
  En el TEMA 10 armaste un agente con `create_agent`. Aquí le enchufas
  MIDDLEWARE: piezas que se meten ENTRE el agente y el modelo para hacer cosas
  transversales sin tocar tu lógica —resumir la conversación cuando se alarga,
  tapar datos personales, pedir aprobación humana antes de una tool peligrosa—.

  ⭐ Es el patrón "hooks": `create_agent(..., middleware=[...])` corre tu código
     ANTES y DESPUÉS de cada llamada al modelo. LangChain trae middleware "de
     fábrica" (SummarizationMiddleware, PIIMiddleware, HumanInTheLoopMiddleware…)
     y tú puedes escribir el tuyo heredando de `AgentMiddleware`.

  ⭐ TODO el armado es 100% OFFLINE y testeable: construir el agente con sus
     middleware no gasta un token. La llamada REAL va en `__main__`, protegida
     por la API key (sin llave, imprime la estructura y no gasta cuota).

LÓGICA (paso a paso):
  1) GuardaDeContexto: un middleware PROPIO (hook `before_model`) que cuenta
     cuántos mensajes verá el modelo en cada vuelta. Sirve de "regla de oro":
     un before_model se ejecuta justo antes de cada llamada al modelo.
  2) construir_agente_con_middleware(): un `create_agent` con TRES middleware:
     el propio + SummarizationMiddleware (resume si la charla crece) +
     PIIMiddleware (tapa correos en lo que entra).
  3) main(): construye el agente; si hay llave, lo hace conversar.

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/10b_middleware.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import create_agent                       # el agente v1
from langchain.agents.middleware import (
    AgentMiddleware,          # clase base para escribir el tuyo
    SummarizationMiddleware,  # resume la conversación cuando se alarga
    PIIMiddleware,            # detecta/tapa datos personales (correo, tarjeta…)
)

from util import crear_llm, requiere_llm_key, mensaje_cuota, es_error_cuota


@tool
def calcular_envio(ciudad: str) -> str:
    """Devuelve el costo de envío a una ciudad del Perú."""
    tarifas = {"lima": "S/ 10", "arequipa": "S/ 18", "iquitos": "S/ 35"}
    return tarifas.get(ciudad.strip().lower(), "S/ 25 (tarifa estándar)")


# ============ 1) UN MIDDLEWARE PROPIO ============
class GuardaDeContexto(AgentMiddleware):
    """Cuenta cuántos mensajes verá el modelo ANTES de cada llamada.

    Un middleware es una clase con "hooks": métodos que LangChain llama en
    momentos fijos del ciclo. `before_model` corre justo antes de cada llamada
    al modelo; `after_model`, justo después. Aquí solo observamos (llevamos la
    cuenta y no cambiamos nada), por eso devolvemos None: devolver un dict
    ACTUALIZARÍA el estado del agente.
    """

    def __init__(self) -> None:
        super().__init__()
        self.llamadas_al_modelo = 0
        self.max_mensajes_vistos = 0

    def before_model(self, state, runtime) -> dict | None:
        self.llamadas_al_modelo += 1
        cuantos = len(state.get("messages", []))
        self.max_mensajes_vistos = max(self.max_mensajes_vistos, cuantos)
        return None   # None = "no toques el estado", solo observé


# ============ 2) ARMAR EL AGENTE CON MIDDLEWARE ============
def construir_agente_con_middleware(llm, guarda: GuardaDeContexto | None = None):
    """Un `create_agent` con tres middleware encadenados.

    El orden importa: los middleware envuelven la llamada al modelo como capas
    de cebolla. Aquí, en cada vuelta:
      · GuardaDeContexto anota cuántos mensajes hay,
      · SummarizationMiddleware resume si la charla pasa de 20 mensajes
        (y conserva los 6 últimos tal cual),
      · PIIMiddleware tapa los correos que lleguen en la entrada del usuario.

    Recibe `guarda` por parámetro (inyección de dependencias) para que un test
    pueda pasar el suyo y luego leer sus contadores.
    """
    return create_agent(
        llm,
        tools=[calcular_envio],
        system_prompt="Eres un asistente de logística claro y breve.",
        middleware=[
            guarda or GuardaDeContexto(),
            # `model=llm`: el resumen lo redacta el MISMO modelo del agente.
            SummarizationMiddleware(llm, trigger=("messages", 20), keep=("messages", 6)),
            # Tapa correos en lo que escribe el usuario antes de que el modelo lo vea.
            PIIMiddleware("email", strategy="redact", apply_to_input=True),
        ],
    )


def main() -> None:
    load_dotenv()

    guarda = GuardaDeContexto()
    agente = construir_agente_con_middleware(crear_llm(temperature=0), guarda)
    print("== Agente con middleware construido ==")
    print("  Middleware: GuardaDeContexto + SummarizationMiddleware + PIIMiddleware")

    # Sin llave: no llamamos al modelo. Demostramos el hook en aislamiento.
    if requiere_llm_key() is not None:
        estado_falso = {"messages": [("user", "hola"), ("user", "¿y a Iquitos?")]}
        guarda.before_model(estado_falso, None)
        print(f"\n(⏸️  Sin API key: no llamo al modelo. Pon la llave en .env para verlo en vivo.)")
        print(f"    Prueba del hook en seco: before_model vio {guarda.max_mensajes_vistos} mensajes.")
        return

    print("\n== Conversación real ==")
    config = {"configurable": {"thread_id": "cliente_10b"}}
    try:
        r = agente.invoke(
            {"messages": [("user", "Mi correo es ana@example.com, ¿cuánto cuesta el envío a Lima?")]},
            config,
        )
        print("  Bot:", r["messages"][-1].content)
        print(f"  (GuardaDeContexto registró {guarda.llamadas_al_modelo} llamada(s) al modelo)")
    except Exception as error:  # noqa: BLE001 — cuota, red o proveedor
        if es_error_cuota(error):
            print(mensaje_cuota())
        else:
            print(f"❌ Error inesperado: {error}")


if __name__ == "__main__":
    main()
