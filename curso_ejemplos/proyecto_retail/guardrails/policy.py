"""
policy.py · Reglas declarativas del asistente (un solo sitio de verdad)
========================================================================
FINALIDAD:
  Centralizar QUÉ se bloquea a la entrada y el vocabulario común de los
  guardrails. Si mañana cambia la política, se toca ESTE archivo y nada más.

  ⭐ Patrón "policy as data": las reglas son DATOS, no código. Se auditan, se
     versionan y se cambian sin redeploy de lógica.

LÓGICA:
  - ResultadoGuard    : el veredicto que devuelven los guardrails.
  - FRASES_INYECCION  : patrones de prompt injection (la entrada).
  - TOPICOS_FUERA     : temas fuera del scope del asistente de compras.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResultadoGuard:
    """Lo que un guardrail decide sobre un texto.

    permitido : ¿sigue la request, o la cortamos aquí?
    texto     : el texto a usar aguas abajo (saneado si hizo falta).
    motivo    : si se bloqueó, por qué. Va al usuario y al log.
    acciones  : qué se tocó/saltó ('bloqueo_inyeccion', 'precio_inventado'…),
                para las métricas.
    """
    permitido: bool
    texto: str
    motivo: str | None = None
    acciones: tuple[str, ...] = field(default_factory=tuple)


# ------------------------------------------------------------------
# PROMPT INJECTION (entrada)
# ------------------------------------------------------------------
# Intentos burdos de "desprogramar" al asistente. La heurística no es perfecta
# (un LLM guardián lo haría mejor), pero atrapa lo evidente SIN gastar tokens.
FRASES_INYECCION: tuple[str, ...] = (
    "ignora las instrucciones",
    "ignora tus instrucciones",
    "ignora lo anterior",
    "olvida tus instrucciones",
    "actúa como",
    "actua como",
    "system prompt",
    "revela tu prompt",
    "muestra tu prompt",
    "modo desarrollador",
    "jailbreak",
    "ignore previous",
    "you are now",
    # Retail-específico: intentos de forzar un precio o un descuento.
    "dame un descuento",
    "ponle precio",
    "invéntate un precio",
    "inventate un precio",
    "regálamelo",
    "regalamelo",
)

# ------------------------------------------------------------------
# TÓPICOS FUERA DE SCOPE (entrada)
# ------------------------------------------------------------------
# El asistente recomienda productos del catálogo. No opina de política, no da
# consejo médico ni legal. Fuera de eso, deriva a un humano.
TOPICOS_FUERA: tuple[str, ...] = (
    "consejo médico", "consejo medico", "diagnóstico", "diagnostico",
    "asesoría legal", "asesoria legal", "por quién voto", "por quien voto",
)


def es_inyeccion(texto: str) -> bool:
    """¿El texto parece un intento de prompt injection? Heurística barata y PURA."""
    t = texto.lower()
    return any(frase in t for frase in FRASES_INYECCION)


def es_topico_fuera(texto: str) -> bool:
    """¿Pide algo fuera del scope del asistente de compras?"""
    t = texto.lower()
    return any(topico in t for topico in TOPICOS_FUERA)
