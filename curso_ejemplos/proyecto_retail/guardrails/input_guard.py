"""
input_guard.py · El portero: qué entra al asistente y qué no
=============================================================
FINALIDAD:
  Inspeccionar la petición del cliente ANTES de que llegue al LLM. Si es un
  intento de inyección o algo fuera del scope de una tienda, la request muere
  aquí: cero tokens gastados.

  Ese "antes" es la tesis: un filtro que actúa después ya pagó el token y ya
  mandó el dato del usuario al proveedor. Llega tarde a las dos cosas que
  importaba evitar.

LÓGICA (el orden es la política):
  1. ¿Inyección? → BLOQUEAR. No hay petición legítima que empiece por "ignora tus
     instrucciones" o "invéntate un precio".
  2. ¿Fuera de scope? → BLOQUEAR con un mensaje que deriva a un humano.

⚠️ LÍMITE HONESTO: es una heurística de subcadenas, barata y evadible
   ("1nvéntate un precio" pasa). En producción se apila un modelo guardián
   encima. Sube el coste del ataque; no lo hace imposible.
"""
from __future__ import annotations

from proyecto_retail.guardrails import policy
from proyecto_retail.guardrails.policy import ResultadoGuard


def revisar_entrada(texto: str) -> ResultadoGuard:
    """Aplica la política de entrada. FUNCIÓN PURA → se testea sin LLM ni red."""
    if policy.es_inyeccion(texto):
        return ResultadoGuard(
            permitido=False,
            texto=texto,
            motivo="La consulta parece un intento de manipular al asistente o forzar un precio.",
            acciones=("bloqueo_inyeccion",),
        )

    if policy.es_topico_fuera(texto):
        return ResultadoGuard(
            permitido=False,
            texto=texto,
            motivo=("Soy el asistente de compras: te ayudo a encontrar productos "
                    "del catálogo. Para eso otro canal te atiende mejor."),
            acciones=("bloqueo_topico",),
        )

    return ResultadoGuard(permitido=True, texto=texto)
