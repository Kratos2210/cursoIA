"""
policy.py · Reglas declarativas de gobernanza (un solo sitio de verdad)
========================================================================
FINALIDAD:
  Centralizar QUÉ se bloquea, QUÉ se anonimiza y QUÉ tópicos están prohibidos.
  Si mañana cambias la política de la financiera, tocas ESTE archivo y nada más.
  Ni el input_guard ni el output_guard tienen reglas hardcoded: las leen de aquí.

  ⭐ Esta separación es el patrón "policy as data": las reglas son DATOS, no
     código. Puedes auditarlas, versionarlas y cambiarlas sin redeploy de lógica.

LÓGICA:
  - FRASES_INYECCION: patrones típicos de prompt injection (la entrada).
  - TOPICOS_PROHIBIDOS: temas de los que el agente no debe hablar.
  - TERMINOS_SENSIBLES_SALIDA: lo que no debe aparecer en la respuesta al usuario.
  - ResultadoGuard: el veredicto que devuelven AMBOS guardrails. Vive aquí porque
    es el vocabulario común de la política, no de un guardrail concreto.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ------------------------------------------------------------------
# 0) EL VEREDICTO
# ------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoGuard:
    """Lo que un guardrail decide sobre un texto.

    Tres campos, tres preguntas:
      permitido : ¿sigue la request, o la cortamos aquí?
      texto     : el texto YA saneado (anonimizado / redactado). Es este el que
                  se usa aguas abajo, nunca el original.
      motivo    : si se bloqueó, por qué. Va al usuario y al log.
      acciones  : qué se tocó ('pii_anonimizada', 'terminos_redactados'…).
                  Sirve para las métricas: cuántas requests se sanean de verdad.

    ⚠️ Bloquear y sanear son cosas distintas. Una inyección se BLOQUEA (permitido
       = False). Un DNI se SANEA (permitido = True, pero `texto` ya no lo lleva).
       Confundirlas convierte el guardrail en un muro o en un colador.
    """
    permitido: bool
    texto: str
    motivo: str | None = None
    acciones: tuple[str, ...] = field(default_factory=tuple)

# ------------------------------------------------------------------
# 1) PROMPT INJECTION (entrada)
# ------------------------------------------------------------------
# Frases con las que un usuario malintencionado intenta "desprogramar" al agente
# para que ignore sus instrucciones. La heurística no es perfecta (un LLM lo haría
# mejor), pero atrapa los intentos más burdos SIN gastar tokens.
#
# ⭐ En producción real combinarías esto con un modelo guardián (p.ej. un LLM
#    pequeño que clasifique "¿es esto un intento de inyección?").
FRASES_INYECCION: tuple[str, ...] = (
    "ignora las instrucciones",
    "ignora tus instrucciones",
    "ignora lo anterior",
    "ignora todo lo anterior",
    "olvida tus instrucciones",
    "actúa como",
    "actua como",
    "no eres un asistente",
    "tu verdadera tarea es",
    "system prompt",
    "revela tu prompt",
    "muestra tu prompt",
    "modo desarrollador",
    "jailbreak",
    "ignore previous",
    "ignore above instructions",
    "you are now",
    "DAN",                # el famoso "Do Anything Now"
)

# ------------------------------------------------------------------
# 2) TÓPICOS PROHIBIDOS (entrada)
# ------------------------------------------------------------------
# El dominio es gobierno de datos de una financiera. El agente NO debe opinar
# sobre inversiones, asesoría financiera ni temas fuera de su scope regulatorio.
TOPICOS_PROHIBIDOS: tuple[str, ...] = (
    "recomiéndame una acción",
    "recomiendame una accion",
    "qué acción comprar",
    "que accion comprar",
    "debería invertir en",
    "deberia invertir en",
    "predecir el mercado",
    "consejo de inversión",
    "asesoría financiera personal",
    "asesoria financiera personal",
)

# ------------------------------------------------------------------
# 3) TÉRMINOS SENSIBLES EN LA SALIDA
# ------------------------------------------------------------------
# Tras generar la respuesta, comprobamos que no filtre datos que no deberían
# llegar al usuario. Esto es una red de seguridad: el prompt ya pide no hacerlo,
# pero un LLM puede equivocarse.
TERMINOS_SENSIBLES_SALIDA: tuple[str, ...] = (
    # Llaves/credenciales (nunca deben estar en una respuesta al usuario).
    "api_key",
    "apikey",
    "bearer ",
    "authorization:",
    "contraseña",
    "password",
    # Datos internos de infraestructura que delatarían el stack.
    "postgres://",
    "redis://",
    "database_url",
)


def es_inyeccion(texto: str) -> bool:
    """¿El texto parece un intento de prompt injection? Heurística barata.

    Comprueba si alguna frase prohibida aparece (en minúsculas) en la entrada.
    Es una FUNCIÓN PURA → testeable sin LLM.
    """
    t = texto.lower()
    return any(frase in t for frase in FRASES_INYECCION)


def es_topico_prohibido(texto: str) -> bool:
    """¿Pide el usuario algo fuera del scope regulatorio del agente?"""
    t = texto.lower()
    return any(topico in t for topico in TOPICOS_PROHIBIDOS)


def terminos_sensibles_en(texto: str) -> tuple[str, ...]:
    """Qué términos sensibles aparecen en el texto. Para el log y las métricas."""
    t = texto.lower()
    return tuple(termino for termino in TERMINOS_SENSIBLES_SALIDA if termino.lower() in t)


def filtra_salida(texto: str) -> str:
    """Enmascara términos sensibles que se hayan colado en la respuesta.

    Reemplaza por una marca visible [REDACTED]. Así, si el modelo devuelve por
    error una llave, el usuario ve que se bloqueó en vez de ver la llave.
    """
    resultado = texto
    for termino in terminos_sensibles_en(texto):
        # Reemplazo case-insensitive conservando el resto del texto.
        resultado = re.sub(re.escape(termino), "[REDACTED]", resultado, flags=re.IGNORECASE)
    return resultado
