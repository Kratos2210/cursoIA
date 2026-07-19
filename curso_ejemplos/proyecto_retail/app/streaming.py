"""
streaming.py · Verificar-y-luego-emitir (el orden correcto para el retail)
===========================================================================
FINALIDAD:
  Emitir la respuesta por SSE (Server-Sent Events) para que la clienta la vea
  aparecer progresivamente. El TTFT (time to first token) es lo que el ojo mide.

⭐ POR QUÉ AQUÍ ES "VERIFICAR-Y-LUEGO-EMITIR", NO "EMITIR-CON-BUFFER". El
   proyecto_llmops sanea el stream token a token con una ventana de retención,
   porque su guardrail (términos sensibles, PII) actúa sobre SUBCADENAS. El del
   retail NO: "¿cada precio citado existe en el catálogo?" es una pregunta sobre
   la respuesta ENTERA. No se puede decidir con media frase.

   Por eso el pipeline (app/agent.py) genera la respuesta COMPLETA, la verifica
   (con reintento y fallback), y RECIÉN DESPUÉS este módulo la trocea y la emite.
   El texto que llega al stream ya es fiel por construcción: no hay forma de que
   un precio inventado se escape a mitad de emisión, porque no se emite nada
   hasta que el guardrail dio el visto bueno.

  El precio: el TTFT es el tiempo de generar la respuesta entera, no el del
  primer token del modelo. Para respuestas de 1-3 líneas es imperceptible, y a
  cambio la fidelidad es total. En retail, esa es la compensación correcta.
"""
from __future__ import annotations

import json


def evento_sse(datos: dict, evento: str | None = None) -> str:
    """Formatea un evento SSE. FUNCIÓN PURA.

    SSE es texto sobre HTTP: líneas `campo: valor` y una línea EN BLANCO que
    cierra el evento (sin ella, el navegador espera para siempre).
    """
    lineas = []
    if evento:
        lineas.append(f"event: {evento}")
    lineas.append(f"data: {json.dumps(datos, ensure_ascii=False)}")
    return "\n".join(lineas) + "\n\n"


def trocear(texto: str, tam: int = 24) -> list[str]:
    """Parte un texto YA VERIFICADO en trozos, para emitirlo progresivamente.

    Trocea por palabras (no corta a media palabra) acumulando hasta ~`tam`
    caracteres. Es cosmético: la respuesta ya está completa y es fiel; esto solo
    la hace llegar poco a poco para la UX.
    """
    if not texto:
        return []
    trozos, actual = [], ""
    for palabra in texto.split(" "):
        candidato = f"{actual} {palabra}".strip()
        if len(candidato) >= tam:
            trozos.append(candidato + " ")
            actual = ""
        else:
            actual = candidato
    if actual:
        trozos.append(actual)
    return trozos
