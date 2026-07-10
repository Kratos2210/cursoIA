"""
TEMA 21 · Fine-tuning vs RAG: ¿enseñar CONOCIMIENTO o COMPORTAMIENTO?
=====================================================================
FINALIDAD:
  La pregunta que todo el mundo se hace mal: "¿hago fine-tuning para que el
  modelo sepa lo de mi empresa?". Casi siempre la respuesta es NO — eso es RAG.
  Este módulo te da un modelo mental claro y una utilidad de DECISIÓN, más el
  formato exacto en el que se entrega un dataset de fine-tuning por chat.

  MODELO MENTAL:
    • RAG = darle una BIBLIOTECA. Conocimiento fresco, que cambia, verificable.
      El modelo lo LEE en el momento de responder (examen a libro abierto).
    • Fine-tuning = mandarlo a la ESCUELA. Le enseñas COMPORTAMIENTO: un formato
      de salida fijo, un tono, un estilo, una forma de razonar. NO le metes datos
      nuevos ni actualizables — para eso está la biblioteca.

  ⭐ Este ejemplo es 100% OFFLINE: reglas deterministas + armado de dataset.
     No entrena nada (entrenar cuesta dinero y GPUs); construye lo que le darías
     a la plataforma de fine-tuning y lo valida.

LÓGICA (paso a paso):
  1) recomendar_enfoque(): a partir de unas señales del proyecto, decide entre
     "RAG", "fine-tuning", "ambos" o "prompt".
  2) preparar_dataset_chat(): convierte pares (usuario, respuesta) al formato de
     chat que esperan OpenAI/Gemini para fine-tuning.
  3) a_jsonl(): serializa esos registros a JSONL (una línea JSON por ejemplo).

Requisitos: ninguno extra (solo Python).  Este script NO llama a la API.
Ejecuta:    uv run python 21_fine_tuning.py
"""

import json


# ============ 1) LA DECISIÓN: ¿RAG, fine-tuning, ambos o prompt? ============
def recomendar_enfoque(senales: dict) -> str:
    """Recomienda el enfoque según las señales del proyecto. Reglas deterministas.

    Señales que lee (todas booleanas, con default False):
      • conocimiento_cambia_seguido   → los datos se actualizan (precios, stock,
        políticas). Eso es CONOCIMIENTO fresco: territorio de RAG, no de fine-tuning.
      • necesita_formato_o_estilo_fijo → hay que responder siempre con una forma
        concreta (JSON estricto, un tono de marca, una plantilla). Eso es
        COMPORTAMIENTO: lo que sí enseña el fine-tuning.
      • hay_ejemplos_etiquetados       → tienes un dataset de calidad y suficiente.
        Sin él, el fine-tuning no es una opción real todavía.
      • presupuesto_bajo               → entrenar y servir un modelo afinado cuesta;
        si el presupuesto aprieta, primero se intenta con prompt/few-shot.

    Devuelve uno de: "RAG" | "fine-tuning" | "ambos" | "prompt".
    """
    conocimiento = bool(senales.get("conocimiento_cambia_seguido"))
    formato = bool(senales.get("necesita_formato_o_estilo_fijo"))
    ejemplos = bool(senales.get("hay_ejemplos_etiquetados"))
    presupuesto_bajo = bool(senales.get("presupuesto_bajo"))

    # Solo es viable AFINAR si además de querer un comportamiento fijo tienes el
    # dataset para enseñarlo. Sin ejemplos etiquetados, el fine-tuning no existe aún.
    puede_afinar = formato and ejemplos and not presupuesto_bajo

    # Necesitas conocimiento fresco Y un comportamiento fijo enseñable → las dos cosas.
    if conocimiento and puede_afinar:
        return "ambos"
    # Conocimiento que cambia: biblioteca, no escuela. RAG gana aunque quieras formato
    # (el formato barato lo das con el prompt encima del RAG).
    if conocimiento:
        return "RAG"
    # Comportamiento fijo, con dataset y presupuesto: el caso de libro del fine-tuning.
    if puede_afinar:
        return "fine-tuning"
    # Quieres un formato/estilo fijo pero NO puedes afinar (sin dataset o sin
    # presupuesto): consíguelo con instrucciones y few-shot en el prompt.
    if formato:
        return "prompt"
    # Nada especial: no compliques. Un buen prompt basta.
    return "prompt"


# ============ 2) ARMAR EL DATASET DE FINE-TUNING (formato chat) ============
def preparar_dataset_chat(pares: list[tuple[str, str]], sistema: str) -> list[dict]:
    """Convierte pares (usuario, respuesta) al formato de fine-tuning por chat.

    Cada ejemplo de entrenamiento es una CONVERSACIÓN completa de tres turnos:
      {"messages": [
          {"role": "system",    "content": <instrucción fija>},
          {"role": "user",      "content": <lo que pregunta el usuario>},
          {"role": "assistant", "content": <la respuesta MODELO que quieres imitar>},
      ]}
    Es el esquema que consumen las plataformas de fine-tuning por chat (OpenAI,
    Gemini). El mensaje 'assistant' es el ejemplo a imitar: su calidad ES la
    calidad del modelo afinado.
    """
    return [
        {
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
                {"role": "assistant", "content": respuesta},
            ]
        }
        for usuario, respuesta in pares
    ]


# ============ 3) SERIALIZAR A JSONL ============
def a_jsonl(registros: list[dict]) -> str:
    """Serializa una lista de registros a JSONL: UNA línea JSON por registro.

    JSONL (JSON Lines) es el formato que piden estas plataformas: un objeto por
    línea, sin comas ni corchete envolvente. `ensure_ascii=False` conserva las
    tildes y la ñ legibles en el archivo.
    """
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in registros)


def main() -> None:
    print("== ¿RAG, fine-tuning, ambos o prompt? Cuatro casos ==\n")
    casos = {
        "Catálogo con precios que cambian cada semana":
            {"conocimiento_cambia_seguido": True},
        "Responder SIEMPRE en un JSON estricto (con 500 ejemplos etiquetados)":
            {"necesita_formato_o_estilo_fijo": True, "hay_ejemplos_etiquetados": True},
        "Tono de marca fijo, pero sin dataset todavía":
            {"necesita_formato_o_estilo_fijo": True, "hay_ejemplos_etiquetados": False},
        "FAQ que cambia + formato fijo con dataset":
            {"conocimiento_cambia_seguido": True,
             "necesita_formato_o_estilo_fijo": True, "hay_ejemplos_etiquetados": True},
    }
    for descripcion, senales in casos.items():
        print(f"  • {descripcion}\n      → {recomendar_enfoque(senales)}")

    print("\n== Armar un dataset de fine-tuning por chat ==\n")
    sistema = "Eres el asistente de soporte de Datawith.AI. Responde en una sola frase clara."
    pares = [
        ("¿Atienden sábados?", "No: atendemos de lunes a viernes, de 9:00 a 18:00 (hora de Perú)."),
        ("¿Puedo pagar en cuotas?", "Sí, en proyectos mayores a 5000 soles ofrecemos pago en dos cuotas."),
    ]
    dataset = preparar_dataset_chat(pares, sistema)
    print(f"  {len(dataset)} ejemplos, cada uno con {len(dataset[0]['messages'])} turnos "
          "(system + user + assistant).")

    print("\n== El archivo .jsonl que subirías a la plataforma ==\n")
    print(a_jsonl(dataset))

    print("\n💡 Regla de oro: si el dato CAMBIA o hay que CITARLO, es RAG (biblioteca).")
    print("   Si lo que quieres fijar es el FORMATO, el TONO o el ESTILO, es fine-tuning")
    print("   (escuela) — y solo si tienes un dataset de calidad. Cuando dudes, prueba")
    print("   primero con un buen prompt: es gratis y muchas veces alcanza.")


if __name__ == "__main__":
    main()
