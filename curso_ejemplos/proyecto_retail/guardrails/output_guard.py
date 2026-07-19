"""
output_guard.py · La última red antes de que el cliente lea la respuesta
=========================================================================
FINALIDAD:
  Revisar lo que el modelo produjo. El prompt ya le pidió no inventar precios,
  pero un LLM es probabilístico: obedece casi siempre. "Casi siempre" no es una
  garantía, y en retail la diferencia entre 99% y 100% se mide en reclamos.

  ⭐ Este módulo existe porque el prompt NO es un control de seguridad. Es una
     petición muy educada. El control es código determinista que corre después.

LÓGICA:
  La revisión de salida del retail ES la fidelidad de precios: cada S/xx.xx
  citado debe existir en los productos recuperados. Se delega en
  `guardrails/price_guard.py` (la regla de oro) para que la lógica viva en un
  solo sitio y el agente y el serving la compartan.

⚠️ DIFERENCIA CON EL STREAMING DEL PROYECTO LLMOPS. Allí el guardrail de salida se
   aplica token a token con un buffer de retención. Aquí NO se puede: "¿cada
   precio citado existe?" es una pregunta sobre la respuesta ENTERA, no sobre un
   fragmento. Por eso el retail verifica la respuesta completa (con reintento y
   fallback, ver app/agent.py) y RECIÉN DESPUÉS la emite por streaming para la UX.
   Verificar-y-luego-emitir, no emitir-y-esperar-que-salga-bien.
"""
from __future__ import annotations

from proyecto_retail.guardrails.policy import ResultadoGuard
from proyecto_retail.guardrails.price_guard import revisar_precios


def revisar_salida(texto: str, productos: list[dict]) -> ResultadoGuard:
    """Sanea/verifica la respuesta del modelo. FUNCIÓN PURA → testeable sin LLM.

    - permitido=False → hay un precio inventado; el llamador reintenta o cae al
      fallback determinista. Nunca sirve esta respuesta.
    - permitido=True  → todos los precios son del catálogo. Segura de emitir.
    """
    return revisar_precios(texto, productos)
