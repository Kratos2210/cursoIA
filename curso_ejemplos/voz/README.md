# voz/ — el agente de voz en tiempo real, con servicios de verdad

El m22b enseña el pipeline de voz como generador determinista y offline
(STT parcial → LLM token a token → TTS por frases), con el audio "de mentira"
para poder testearlo. `agente_voz_realtime.py` cambia las mentiras por servicios
reales **sin cambiar la forma del flujo**:

```
micrófono ─▶ Deepgram STT (streaming) ─▶ LLM (util.crear_llm, .stream)
                                                 │
                    Deepgram TTS ◀── por frase ──┘   (baja la latencia percibida)
```

La clave (m22b): sintetizar EN CUANTO hay una frase completa —no al final—.
Reutiliza el troceo por frases del m22b (`_dividir_en_frases`), sin duplicarlo.

## Cómo se corre

```bash
uv run --extra voice python voz/agente_voz_realtime.py
```

Necesita micrófono, una API key de [Deepgram](https://deepgram.com) y una de LLM.

## Por qué está fuera del gate offline

Decidido en [ADR-0007](../docs/adr/0007-voz-realtime-fuera-del-gate.md): extra
opcional (`uv sync --extra voice`), no se testea en la CI. La versión offline y
testeable del mismo pipeline es el m22b (`22b_voz.py`).
