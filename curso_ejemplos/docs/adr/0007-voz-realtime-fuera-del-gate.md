# ADR-0007 — El agente de voz en tiempo real vive fuera del gate offline

- **Estado:** aceptado
- **Fecha:** 2026-07-17
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El m22b enseña el pipeline de voz en tiempo real (STT parcial → LLM en streaming
→ TTS por frases) como un **generador determinista y offline**
(`pipeline_voz_streaming`): el audio y el `responder` van de mentira, así se puede
**testear** el ORDEN de los eventos sin red ni micrófono. Es la mitad conceptual.

El benchmark de mercado pedía la otra mitad: un agente de voz que **de verdad**
escuche por micrófono y responda hablando, con servicios reales de baja latencia
(Deepgram). Eso rompe la constitución offline-first en las tres restricciones a la
vez:

- Necesita **micrófono** (hardware) y un stream de audio en vivo.
- Necesita **APIs con cuota**: Deepgram (STT/TTS) y un LLM.
- Es intrínsecamente **asíncrono y con websockets**: no encaja en un test unitario
  determinista.

## Decisión

> El agente de voz en tiempo real vive en `voz/agente_voz_realtime.py`, en un
> **extra opcional** `voice` (`deepgram-sdk`), **fuera** del gate offline, y en un
> **módulo de lectura** (m33). La CI corre `uv sync --extra dev`, así que no lo
> instala ni lo testea. Fila "—" en el #mapa.

El artefacto **reutiliza** la lógica testeable del m22b (`_dividir_en_frases` y la
misma FORMA de `pipeline_voz_streaming`): cambia las mentiras por servicios reales
sin cambiar el flujo. Así la parte que importa didácticamente —el orden STT →
LLM → TTS-por-frase— sigue cubierta por tests en el m22b, y el anexo solo añade el
cableado real. Los ids de modelo de Deepgram son **placeholders verificables**.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Anexo fuera del gate (extra `voice`), reutilizando el m22b** | Agente de voz real; la lógica clave sigue testeada en el m22b | No corre en la CI; necesita micrófono + cuota | ✅ **Elegida** |
| Meter Deepgram + audio en `tests/` | Coherente con el resto | Imposible sin micrófono/cuota/websockets en la CI | Rompe la constitución para todos |
| Quedarse solo con el m22b (simulado) | Ya es testeable | No hay agente de voz real; el gap sigue | El m22b es la base, no el cierre del gap |

## Consecuencias

**Positivas**
- El alumno tiene un agente de voz **real** que reutiliza el pipeline que ya
  entendió (y testeó) en el m22b: cambia servicios, no la forma.
- El gate offline **no cambia**: la lógica de orden STT→LLM→TTS sigue verde y sin
  micrófono en `TestTema22bVoz`.

**Negativas**
- El agente real **no está cubierto por tests** y depende de Deepgram: puede
  desfasarse si su SDK o sus ids de modelo cambian. Se marca como lectura +
  ejecución-si-tienes-micrófono, con ids verificables.
- La captura de micrófono queda como **esqueleto documentado** (`escuchar_microfono`
  lanza `NotImplementedError` con la pista): depende del hardware del alumno.

**Cuándo revisar**

Si Deepgram (u otro proveedor) ofreciera un modo de reproducir un archivo de audio
fijo como si fuese streaming, el pipeline real podría ganar un smoke test con un
WAV de prueba y sin micrófono.
