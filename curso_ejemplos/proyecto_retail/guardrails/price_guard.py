"""
price_guard.py · La regla de oro del retail, hecha código determinista
=======================================================================
FINALIDAD:
  Verificar que CADA precio citado en la respuesta existe en los productos
  recuperados del catálogo. Es el guardrail que salva del riesgo #1 del retail:
  el PRECIO INVENTADO.

  ⭐ En retail, PRECIO y STOCK jamás salen del modelo. El LLM entiende la
     intención y redacta; el catálogo pone los hechos. Un chatbot que inventa un
     precio no es un bug simpático: es un reclamo — y en Perú, un problema con
     Indecopi.

  ⭐ POR QUÉ DETERMINISTA Y NO OTRO LLM (ver docs/adr/0002). El detector de
     alucinaciones del m28 desconfía por dispersión porque NO tiene la verdad a
     mano. Aquí SÍ la hay —el catálogo—, así que se verifica contra ella con
     código: barato, repetible byte a byte y sin cuota. Poner un LLM a juzgar si
     un precio es correcto es pagar una llamada para comprobar una resta.

⚠️ La anécdota que este guardrail atrapa: la primera versión de la respuesta
   ECOABA la petición ("Para «...hasta S/80» te recomiendo…") y el guardrail
   saltó, porque ese S/80 del usuario no es un precio del catálogo. La cura es no
   re-inyectar el texto del usuario en la salida (misma higiene que el m23 pide
   contra la inyección). Un guardrail que te muerde a ti antes que al cliente
   está haciendo su trabajo.
"""
from __future__ import annotations

import re

from proyecto_retail.guardrails.policy import ResultadoGuard

# Captura los S/xx.xx que un texto menciona. "S/ 19.90", "S/19.90", "S/6".
_RE_PRECIO = re.compile(r"S/\s?(\d+(?:\.\d+)?)")


def precios_citados(texto: str) -> set[float]:
    """Todos los S/xx.xx que un texto menciona. Es la mitad del guardrail. PURA."""
    return {float(m) for m in _RE_PRECIO.findall(texto)}


def respuesta_es_fiel(texto: str, productos: list[dict]) -> bool:
    """¿Cada precio citado existe en los productos recuperados? PURA.

    `productos` son los del catálogo que la búsqueda devolvió: la única fuente de
    precios legítima para esta respuesta.
    """
    permitidos = {round(p["precio"], 2) for p in productos}
    return all(round(precio, 2) in permitidos for precio in precios_citados(texto))


def revisar_precios(texto: str, productos: list[dict]) -> ResultadoGuard:
    """El veredicto del guardrail de salida del retail. FUNCIÓN PURA → sin LLM.

    - permitido=False → la respuesta cita un precio que no está en el catálogo.
      El llamador debe reintentar o caer al fallback determinista; JAMÁS servir
      esta respuesta.
    - permitido=True  → todos los precios son del catálogo. Segura de emitir.
    """
    if respuesta_es_fiel(texto, productos):
        return ResultadoGuard(permitido=True, texto=texto)

    permitidos = sorted({round(p["precio"], 2) for p in productos})
    inventados = sorted(precios_citados(texto) - set(permitidos))
    return ResultadoGuard(
        permitido=False,
        texto=texto,
        motivo=(f"La respuesta cita precios que no están en el catálogo "
                f"recuperado: {inventados}. Precios permitidos: {permitidos}."),
        acciones=("precio_inventado",),
    )
