# ADR-0008 — El re-ranker REAL es un companion ONNX, no un reemplazo del didáctico

- **Estado:** aceptado (complementa, no revierte, el [ADR-0002](0002-re-ranker.md))
- **Fecha:** 2026-07-17
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El [ADR-0002](0002-re-ranker.md) decidió implementar el re-ranking **a mano, en
Python puro** (cobertura de palabras + bono de frase) para que el m12 fuese 100%
offline y sin dependencias. Esa decisión sigue siendo correcta para *enseñar la
mecánica*, y el propio m12 confiesa su límite: si ninguna palabra de la pregunta
aparece en el chunk, **todos puntúan 0.0** y el orden resultante es arbitrario.

Falta la otra mitad: ver un re-ranker **de verdad** acertando justo donde el
didáctico falla (sinónimos). El snippet que el m12 ya muestra usa
`HuggingFaceCrossEncoder`, que arrastra **PyTorch** — y PyTorch **no publica
wheels para macOS Intel** (es exactamente el aviso del extra `hf` en
`pyproject.toml`). Es decir: el camino "real" que el curso enseñaba **no se puede
ejecutar** en una de las plataformas del curso.

## Decisión

> El re-ranker real vive en `rerank/rerank_real.py` como **companion** del m12,
> usando el **cross-encoder ONNX de fastembed** (`TextCrossEncoder`) en vez de la
> vía PyTorch. Reutiliza el extra **`emb` que ya existe** (no se añade uno nuevo)
> y va **fuera** del gate offline: descarga un modelo (~80 MB) la primera vez y
> no se testea en la CI. El re-ranker didáctico del m12 **se queda como está**.

El companion **importa** el corpus y el re-ranker didáctico del propio
`12_rag_hibrido_rerank.py` (cargado por ruta, como el fixture `importar_ejemplo`
de los tests) y ejecuta los dos **sobre la misma pregunta**, para que la
diferencia se vea en la misma pantalla en vez de contarse.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Companion ONNX (fastembed), extra `emb` reutilizado** | Corre en TODAS las plataformas del curso (incl. macOS Intel); sin torch; sin extra nuevo | Descarga ~80 MB; no se testea | ✅ **Elegida** |
| Companion con `HuggingFaceCrossEncoder` (PyTorch) | Es el snippet que el m12 ya muestra | **No funciona en macOS Intel**; +varios GB | Rompe en la plataforma del autor |
| Reemplazar el re-ranker didáctico por el real | Un solo camino | Mata la lección de mecánica del ADR-0002 y el offline del m12 | Contradice el ADR-0002 |
| Dejarlo solo como snippet ilustrativo | Cero trabajo | No se ejecuta; el fallo de los sinónimos nunca se ve | No cierra el gap |

## Consecuencias

**Positivas**
- El alumno **ve** el fallo del re-ranker léxico y su cura, en la misma corrida:
  con "¿me devuelven la plata si no me gusta?" (cobertura 0.00) el didáctico
  devuelve "formas de pago" y el real acierta "Política de reembolsos".
- El m12 y su gate offline **no cambian**: `-m offline` sigue verde sin descargar
  nada, y el ADR-0002 sigue vigente.
- Documenta que la vía PyTorch del snippet **no es ejecutable en macOS Intel**, un
  detalle que de otro modo el alumno descubre a los 20 minutos de instalar.

**Negativas**
- El companion **no está cubierto por tests** y depende de que fastembed siga
  exponiendo `TextCrossEncoder` y del id del modelo. Se marca como material fuera
  del gate, con el id **verificable** vía `TextCrossEncoder.list_supported_models()`.
- Los puntajes son **logits** (negativos), no probabilidades: se documenta en el
  archivo para que nadie copie un umbral de otro proyecto.

**Cuándo revisar**

Si el curso dejara de soportar macOS Intel, la vía HuggingFace volvería a ser
viable y el companion podría ofrecer las dos implementaciones lado a lado.
