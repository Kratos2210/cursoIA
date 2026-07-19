# ADR-0002 — El grounding de precios es determinista, no un LLM-judge

- **Estado:** aceptado
- **Fecha:** 2026-07-11
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El riesgo #1 del asistente es citar un precio que no existe en el catálogo. Hay
que verificar, en cada respuesta, que todo `S/xx.xx` mencionado sea un precio de
un producto recuperado. La tentación LLMOps es usar un "LLM-as-judge": otro
modelo que lea la respuesta y diga si los precios son correctos.

Pero aquí hay una asimetría con el detector de alucinaciones del m28. Aquel
desconfía por **dispersión** (muestrea la misma pregunta y mira si diverge)
porque NO tiene la verdad a mano. En el retail, la verdad SÍ existe y es
estructurada: el catálogo recuperado.

## Decisión

> La fidelidad de precios se verifica con **código determinista**
> (`guardrails/price_guard.py`): se extraen los `S/xx.xx` de la respuesta con una
> regex y se comprueba que cada uno esté en el conjunto de precios de los
> productos recuperados. Nada de LLM en este paso.

El LLM-judge (`evals/judge.py`) se reserva para lo SUBJETIVO —¿el tono es cálido?,
¿la respuesta es útil?—, que no se puede comprobar con la verdad a mano.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Verificación determinista (regex + set)** | Barata, repetible byte a byte, sin cuota, sin falsos positivos | Solo cubre precios citados con el formato `S/xx.xx` | ✅ **Elegida** |
| LLM-judge de precios | "Entiende" formatos raros | Paga una llamada para hacer una resta; no repetible; puede alucinar al juzgar | Poner un LLM a comprobar una igualdad numérica es el sitio equivocado |
| Confiar en el prompt ("no inventes precios") | Cero código | El prompt es una petición educada, no un control | Un LLM obedece "casi siempre"; en retail, casi = reclamo |

## Consecuencias

- El guardrail es **infalible dentro de su alcance**: si un precio no está en el
  catálogo recuperado, no pasa. Y el fallback determinista (`armar_respuesta`) es
  fiel por construcción, así que una respuesta infiel nunca llega al cliente.
- **Límite honesto:** solo ve los precios escritos como `S/xx.xx`. Un precio
  escrito "diecinueve noventa" se le escapa. El prompt pide el formato con SKU y
  precio exactos, y el fallback lo garantiza; aun así, el alcance es el del regex.
- La división de trabajo queda clara: lo verificable con la verdad a mano → código;
  lo subjetivo → LLM-judge (opcional, fuera del CI gate).
