"""
VOZ · Agente de voz en TIEMPO REAL (Deepgram STT → LLM → TTS por streaming)
===========================================================================
FINALIDAD:
  El m22b enseñó el pipeline de voz en tiempo real como un GENERADOR determinista
  y offline (`pipeline_voz_streaming`): STT parcial → LLM token a token → TTS por
  frases. Ahí `responder` y el audio iban de mentira, para poder testearlo. Este
  anexo cambia las MENTIRAS por servicios REALES sin cambiar la FORMA del flujo:

    micrófono ─▶ Deepgram STT (streaming) ─▶ LLM (util.crear_llm, .stream)
                                                     │
                        Deepgram TTS ◀── por frase ──┘   (baja la latencia percibida)

  La clave (m22b): sintetizar EN CUANTO hay una frase completa —no al final— para
  que la respuesta "empiece" casi al toque. Reutilizamos el MISMO troceo por
  frases del m22b (`_dividir_en_frases`) para no duplicar esa lógica.

  ⭐ FUERA DEL GATE OFFLINE (ver docs/adr/0007): extra opcional
     (`uv sync --extra voice`), NO se testea en la CI. Necesita micrófono, una
     API key de Deepgram y una de LLM. La versión offline y testeable es el m22b.

Ejecuta:  uv run --extra voice python voz/agente_voz_realtime.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path

# Reutilizamos el troceo por frases del m22b (mismo criterio, sin duplicar). El
# archivo empieza por dígito, así que se carga por ruta (como el fixture de los
# tests: importar_ejemplo("22b_voz")).
_ruta_22b = Path(__file__).resolve().parent.parent / "22b_voz.py"
_spec = importlib.util.spec_from_file_location("voz_m22b", _ruta_22b)
_m22b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m22b)
dividir_en_frases = _m22b._dividir_en_frases   # el MISMO del m22b


# ------------------------------------------------------------------
# 1) EL CEREBRO — el LLM del curso, en streaming (igual que en todo el curso)
# ------------------------------------------------------------------
_SISTEMA = ("Eres un asistente de voz: responde en UNA o dos frases, natural y "
            "hablado, sin listas ni markdown. Si no sabes algo, dilo.")


def responder_stream(transcripcion: str):
    """Transcripción → tokens del LLM, uno a uno (para no esperar la respuesta entera)."""
    import util
    llm = util.crear_llm(temperature=0.3)
    for chunk in llm.stream([("system", _SISTEMA), ("human", transcripcion)]):
        if chunk.content:
            yield chunk.content


# ------------------------------------------------------------------
# 2) SALIDA — TTS real por frase (Deepgram). Se sintetiza en cuanto la frase cierra
# ------------------------------------------------------------------
async def sintetizar(texto: str) -> bytes:
    """Texto → audio con Deepgram TTS. Devuelve los bytes de audio de UNA frase."""
    from deepgram import DeepgramClient, SpeakOptions

    dg = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
    opciones = SpeakOptions(model=os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-es"))  # VERIFICA el id
    respuesta = await dg.speak.asyncrest.v("1").stream_memory({"text": texto}, opciones)
    return respuesta.stream_memory.getvalue()


# ------------------------------------------------------------------
# 3) ORQUESTACIÓN — la MISMA forma del m22b, con servicios reales
# ------------------------------------------------------------------
async def conversar(fragmentos_audio) -> None:
    """STT parcial → LLM en streaming → TTS por frase. El flujo del m22b, en vivo.

    `fragmentos_audio` es un iterable ASÍNCRONO de transcripciones parciales que
    entrega Deepgram STT (ver `escuchar_microfono`). Aquí no simulamos: cada
    evento viene de un servicio real, pero el ORDEN (parcial → final → tokens →
    audio por frase) es idéntico al generador testeable del m22b.
    """
    # 1) STT incremental: Deepgram va entregando transcripción parcial.
    transcripcion = ""
    async for parcial in fragmentos_audio:
        transcripcion = parcial
        print(f"\r🎙️  {transcripcion}", end="", flush=True)
    print()

    # 2) LLM en streaming + 3) TTS por frase EN CUANTO cada frase cierra.
    buffer = ""
    for token in responder_stream(transcripcion):
        buffer += token
        # ¿Se completó una frase? Sintetiza esa y sigue acumulando el resto.
        *completas, buffer = _partir_incremental(buffer)
        for frase in completas:
            audio = await sintetizar(frase)
            print(f"🔊 ({len(audio)} bytes) {frase}")
    if buffer.strip():                                   # la última frase sin cierre
        audio = await sintetizar(buffer.strip())
        print(f"🔊 ({len(audio)} bytes) {buffer.strip()}")


def _partir_incremental(texto: str):
    """Devuelve [frases completas..., resto_sin_cerrar] usando el criterio del m22b."""
    trozos = list(dividir_en_frases(texto))
    if not trozos:
        return [""]
    # Si el texto NO acaba en puntuación, el último trozo aún está a medias.
    if texto.rstrip()[-1:] not in ".!?":
        return trozos            # último elemento = resto (buffer)
    return trozos + [""]         # todo cerrado: no queda resto


async def escuchar_microfono():
    """Abre el micrófono y hace STT streaming con Deepgram; yield de parciales.

    Esqueleto del cableado real (deepgram-sdk v3, live transcription). Se deja
    documentado porque depende del micrófono del alumno; el resto del pipeline sí
    corre con cualquier fuente de parciales.
    """
    raise NotImplementedError(
        "Conecta aquí el micrófono con deepgram.listen.asyncwebsocket y haz "
        "`yield` de cada `result.channel.alternatives[0].transcript` parcial. "
        "Para probar el pipeline sin micrófono, pásale un async-iterable de strings."
    )


async def _demo() -> None:
    """Demo sin micrófono: parciales de mentira, STT/TTS/LLM reales."""
    async def parciales_falsos():
        for t in ("¿cuál", "¿cuál es", "¿cuál es la capital", "¿cuál es la capital de Perú?"):
            yield t
            await asyncio.sleep(0.15)

    await conversar(parciales_falsos())


if __name__ == "__main__":
    asyncio.run(_demo())
