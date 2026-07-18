# ADR-0003 — El hands-on de LoRA vive en un notebook de Colab, fuera del gate offline

- **Estado:** aceptado
- **Fecha:** 2026-07-17
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El TEMA 21 (`fine-tuning vs RAG`) enseña la **decisión**: cuándo afinar y cuándo
hacer RAG, y el espectro de adaptación (prompt → few-shot → RAG → LoRA/QLoRA →
full fine-tuning). Todo ello es 100% offline y testeado (`21_fine_tuning.py`).

Falta la otra mitad que un currículo comparable (p. ej. Codecademy) sí cubre: el
**hands-on** de afinar de verdad un modelo con LoRA. La auditoría 2026-07 lo marcó
como gap ("solo la decisión, no la práctica").

Hay una tensión con la **constitución del curso**: todo ejemplo es *offline-first*
— corre en la CI sin red, sin GPU y sin cuota, en segundos. Un fine-tuning real
rompe las tres restricciones a la vez:

- Necesita una **GPU** (ni la CI ni el portátil promedio la tienen).
- Arrastra **PyTorch + transformers + peft + bitsandbytes** (varios GB).
- La ejecución tarda **minutos**, no milisegundos.

Meter esto en `pyproject.toml` y en `tests/` contaminaría el entorno de *todos*
los alumnos —incluidos los que solo quieren la parte conceptual— y volvería la CI
lenta y frágil. Pero no enseñar la práctica deja el tema a medias.

## Decisión

> El hands-on de LoRA/QLoRA vive en un **notebook de Colab**
> (`docs/notebooks/21b_lora_colab.ipynb`) y en un **módulo de lectura** (m21b),
> **fuera** del gate offline: no se añade ninguna dependencia a `pyproject.toml`,
> no se testea en la CI y su fila en el #mapa lleva "—". El alumno lo corre en la
> GPU gratuita de Colab, no en su máquina.

Es una **excepción consciente y acotada** a la regla offline-first, no una grieta:
el resto del curso sigue intacto y ejecutable sin nada especial.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Notebook Colab, fuera del gate** | Enseña el hands-on real con GPU gratis; cero impacto en deps/CI del resto | No corre en la CI; no se testea | ✅ **Elegida** |
| Añadir `peft`+`transformers` a `pyproject` y un ejemplo `.py` | Coherente con el resto de temas | +varios GB para todos; imposible sin GPU; CI lenta/frágil | Rompe la constitución para todos por una minoría |
| Simularlo offline (como el re-ranker del [ADR-0002](0002-re-ranker.md)) | Testeable, sin deps | Un LoRA "de mentira" no enseña el hands-on que se pide; la mecánica no es didáctica como sí lo es el RRF | No cumple el objetivo (practicar de verdad) |
| No cubrirlo | Cero trabajo | El gap sigue abierto | No enseñar no es una opción |

## Consecuencias

**Positivas**
- El alumno **afina un modelo de verdad** con GPU gratis, sin instalar nada en su
  máquina ni tocar el entorno del resto del curso.
- La constitución offline-first del repo **no cambia**: `uv run pytest -m offline`
  sigue verde y sin GPU; ningún alumno paga PyTorch por un tema opcional.
- La decisión queda documentada aquí, así que la excepción es *visible* y no un
  atajo silencioso que alguien descubre después.

**Negativas** (hay que decirlas)
- El notebook **no está cubierto por tests**: puede quedar desactualizado cuando
  cambien las APIs de `transformers`/`peft` o el modelo base elegido. Se marca como
  material de lectura, con fecha y con ids de modelo *verificables*, no canónicos.
- El alumno **depende de Colab** (o de una GPU propia): sin ella, el m21b se lee
  pero no se ejecuta. Es lectura + práctica-si-puedes, no ejecutable universal.
- Introduce una **segunda categoría** de material ("fuera del gate") que hay que
  señalizar bien para no confundir con el resto (por eso la fila "—" en el #mapa).

**Cuándo revisar esta decisión**

Cuando el curso tenga un entorno con GPU preprovisionado (Colab enlazado, o un
Codespace con aceleración) donde ejecutar el notebook sea el flujo por defecto.
Ahí el m21b podría ganar un smoke test que corra el notebook con un modelo
diminuto y pocos pasos, dejando de ser "solo lectura".
