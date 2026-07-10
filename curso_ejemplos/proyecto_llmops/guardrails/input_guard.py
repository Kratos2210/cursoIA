"""
input_guard.py · El portero: qué entra al modelo y qué no
==========================================================
FINALIDAD:
  Inspeccionar la pregunta del usuario ANTES de que llegue al LLM. Si es un
  intento de inyección o un tópico prohibido, la request muere aquí: **cero
  tokens gastados, cero riesgo**.

  Ese "antes" no es un detalle de implementación, es la tesis del módulo. Un
  filtro que actúa después de llamar al modelo ya pagó el token y ya mandó el
  dato del usuario al proveedor. Llega tarde a las dos cosas que importaba evitar.

LÓGICA (el orden de las comprobaciones ES la política):
  1. ¿Inyección?        → BLOQUEAR. No hay pregunta legítima que empiece por
                          "ignora tus instrucciones".
  2. ¿Tópico prohibido? → BLOQUEAR. Está fuera del scope regulatorio del agente.
  3. ¿PII?              → NO bloquear: **anonimizar**. Que alguien pegue su DNI
                          no es un ataque, es un descuido. Se le atiende, pero el
                          DNI no viaja al proveedor del modelo.

  ⭐ Bloquear lo hostil, sanear lo torpe. Bloquear el descuido enfada al usuario;
     sanear el ataque lo deja pasar. Cada riesgo tiene su respuesta.

⚠️ LÍMITES DE ESTA DEFENSA. Es una heurística de subcadenas: barata, determinista
   y sin cuota, pero **evadible** (un atacante escribe "1gnora tus 1nstrucciones"
   y pasa). En producción se apila sobre ella un modelo guardián. Un guardrail
   por lista negra sube el coste del ataque; no lo hace imposible. Quien lo
   presente como impenetrable no ha entendido el problema.
"""
from __future__ import annotations

from guardrails import pii, policy
from guardrails.policy import ResultadoGuard


def revisar_entrada(texto: str, *, anonimizar_pii: bool = True) -> ResultadoGuard:
    """Aplica la política de entrada. FUNCIÓN PURA → se testea sin LLM ni red.

    Devuelve un ResultadoGuard:
      - permitido=False → el llamador responde 400 y NO llama al modelo.
      - permitido=True  → usa `resultado.texto` (ya anonimizado), nunca el original.

    Parámetro:
      anonimizar_pii: ponlo a False solo si aguas abajo necesitas el dato real
                      (p.ej. una tool que consulta al cliente por su DNI). En ese
                      caso la anonimización debe hacerse en otro punto, no
                      olvidarse.
    """
    # ---- 1) Inyección: el ataque. Se bloquea. -------------------------------
    if policy.es_inyeccion(texto):
        return ResultadoGuard(
            permitido=False,
            texto=texto,
            motivo="La consulta parece un intento de manipular las instrucciones del asistente.",
            acciones=("bloqueo_inyeccion",),
        )

    # ---- 2) Tópico prohibido: fuera de scope. Se bloquea. --------------------
    if policy.es_topico_prohibido(texto):
        return ResultadoGuard(
            permitido=False,
            texto=texto,
            motivo=("GobData solo responde sobre gobierno y calidad de datos. "
                    "No da asesoría de inversión."),
            acciones=("bloqueo_topico",),
        )

    # ---- 3) PII: el descuido. Se sanea y se sigue. ---------------------------
    acciones: tuple[str, ...] = ()
    texto_limpio = texto
    if anonimizar_pii and pii.contiene_pii(texto):
        texto_limpio = pii.anonimizar(texto)
        acciones = ("pii_anonimizada",)

    return ResultadoGuard(permitido=True, texto=texto_limpio, acciones=acciones)


# ------------------------------------------------------------------
# El guardrail de COMPLEJIDAD (alimenta la cascada de app/llm.py)
# ------------------------------------------------------------------
# Señales de que una pregunta necesita razonar, no solo recuperar un párrafo.
#
# ⚠️ Aquí NO está "por qué", y es deliberado. Aparece en media normativa
#    ("¿por qué se conservan 5 años?") y enviaría casi todo al modelo caro:
#    la señal más obvia era la que rompía el ahorro. Una señal que dispara
#    siempre no es una señal.
_SEÑALES_COMPLEJIDAD: tuple[str, ...] = (
    "compara", "contrasta", "diferencia entre", "analiza", "evalúa", "evalua",
    "razona", "justifica", "implicaciones", "consecuencias", "paso a paso",
    "qué pasaría", "que pasaria", "trade-off", "pros y contras",
)

# Una pregunta larga suele traer varias sub-preguntas encadenadas.
_UMBRAL_PALABRAS_COMPLEJIDAD = 40


def es_pregunta_compleja(texto: str) -> bool:
    """¿Merece esta pregunta el modelo caro? Heurística barata y PURA.

    La usa `app.llm.crear_cascada_con_guardrail()` para decidir, ANTES de llamar
    a nadie, si escala del modelo barato al de mayor razonamiento.

    ⭐ La clave económica: la decisión de gastar la toma una función de coste
       cero. Si un LLM decidiera qué LLM usar, ya habrías pagado una llamada
       para ahorrarte una llamada.

    Dos señales, cualquiera basta:
      - un verbo de razonamiento ("compara", "justifica", "implicaciones"…),
      - una pregunta larga (varias sub-preguntas encadenadas).
    """
    t = texto.lower()
    if any(señal in t for señal in _SEÑALES_COMPLEJIDAD):
        return True
    return len(texto.split()) > _UMBRAL_PALABRAS_COMPLEJIDAD
