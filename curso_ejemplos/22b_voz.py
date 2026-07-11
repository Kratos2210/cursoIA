"""
TEMA 22b · Voz y multimodal generativo: audio de ENTRADA y de SALIDA
=====================================================================
FINALIDAD:
  El m22 mostró multimodal de ENTRADA con imagen (el modelo VE). El espectro
  multimodal es más ancho: el modelo también OYE (audio de entrada → texto,
  "speech-to-text" o comprensión de audio) y HABLA (texto → audio, "text-to-
  speech"). Este módulo enseña a CONSTRUIR las dos peticiones, sin gastar cuota.

  ⭐ El armado es 100% OFFLINE y testeable. Como con la imagen del m22, el audio
     de entrada viaja en un bloque de contenido; la síntesis de voz (TTS) es una
     petición aparte cuyo payload también se arma en local. La llamada REAL va
     en `__main__`, protegida por la API key.

  📐 FORMATO DEL AUDIO DE ENTRADA (verificado contra el paquete instalado, no de
     memoria: `langchain_google_genai.chat_models._convert_to_parts` lo acepta y
     lo traduce a la parte `inline_data` que la API de Gemini espera):
         {"type": "text",  "text": "..."}
         {"type": "media", "mime_type": "audio/wav", "data": "<base64>"}
     A diferencia de la imagen (que usa `image_url`), el audio/vídeo usa el
     bloque `media` con su `mime_type`.

LÓGICA (paso a paso):
  1) audio_a_bloque(): bytes de audio → bloque `media` con base64 y mime_type.
  2) mensaje_con_audio(): arma el HumanMessage [texto, audio] (comprensión/STT).
  3) peticion_tts(): arma el payload de síntesis de voz (texto → audio). Es una
     petición DISTINTA (no un mensaje de chat): devuelve audio, no texto.
  4) main(): construye ambos; si hay llave, manda el audio a un modelo que oye.

Requisitos: ninguno extra (solo Python + lo ya instalado).  Sin llave NO llama a la API.
Ejecuta:    uv run python 22b_voz.py
"""

import base64


# Un WAV mínimo (cabecera RIFF, sin muestras) embebido como base64: sirve para
# DEMOSTRAR el armado sin versionar binarios ni depender de un micrófono. No es
# audio audible; es el "sobre" con la forma correcta para probar la estructura.
WAV_DEMO = base64.b64encode(b"RIFF$\x00\x00\x00WAVEfmt ").decode("ascii")

# Voces y formatos que un proveedor de TTS suele exponer (ilustrativo).
VOCES_TTS = ("alloy", "verse", "aria")


# ============ 1) AUDIO DE ENTRADA COMO BLOQUE DE CONTENIDO ============
def audio_a_bloque(datos: bytes, mime: str = "audio/wav") -> dict:
    """Convierte bytes de audio en un bloque `media` con su base64 y mime_type.

    POR QUÉ `media` y no `image_url`: el audio (y el vídeo) viajan en el bloque
    `media`, que declara el `mime_type` para que el receptor sepa decodificarlo.
    base64 reescribe los bytes como texto ASCII para que quepan en el JSON.
    """
    b64 = base64.b64encode(datos).decode("ascii")
    return {"type": "media", "mime_type": mime, "data": b64}


# ============ 2) MENSAJE CON AUDIO (comprensión / STT) ============
def mensaje_con_audio(texto: str, datos: bytes, mime: str = "audio/wav"):
    """HumanMessage con DOS bloques: la instrucción de texto y el audio.

    Igual que la imagen del m22, el contenido pasa de string a LISTA de bloques.
    El modelo que OYE lee ambos: "escucha este audio Y haz lo que pido".
    """
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=[
        {"type": "text", "text": texto},
        audio_a_bloque(datos, mime),
    ])


# ============ 3) SÍNTESIS DE VOZ (TTS): texto → audio ============
def peticion_tts(texto: str, voz: str = "alloy", formato: str = "mp3") -> dict:
    """Arma el payload de una petición de síntesis de voz (texto → audio).

    OJO: TTS NO es un mensaje de chat. Es una petición aparte cuya RESPUESTA es
    audio (bytes), no texto. Aquí solo construimos el payload; la llamada real
    la hace el cliente de audio del proveedor. Validamos lo que sí es nuestro:
    que la voz sea una de las soportadas.
    """
    if voz not in VOCES_TTS:
        raise ValueError(f"voz desconocida: {voz!r}. Opciones: {', '.join(VOCES_TTS)}")
    return {"input": texto, "voice": voz, "format": formato}


def main() -> None:
    import util

    audio = base64.b64decode(WAV_DEMO)

    # --- Audio de ENTRADA: comprensión / transcripción ---
    mensaje = mensaje_con_audio("Transcribe este audio y resume su idea.", audio)
    print("== Mensaje con audio construido (entrada) ==\n")
    print(f"  Bloques: {len(mensaje.content)}")
    bloque_audio = mensaje.content[1]
    print(f"  [1] type={bloque_audio['type']!r} · mime={bloque_audio['mime_type']!r} "
          f"· data={bloque_audio['data'][:24]}… ({len(bloque_audio['data'])} chars)")

    # --- Audio de SALIDA: síntesis de voz (TTS) ---
    pet = peticion_tts("Hola, soy tu asistente de voz.", voz="verse", formato="mp3")
    print("\n== Petición TTS construida (salida) ==\n")
    print(f"  payload: {pet}")
    print("  (la respuesta REAL de TTS son bytes de audio, no texto)")

    # La llamada REAL solo si hay llave: sin ella, no gastamos cuota.
    if util.requiere_llm_key() is not None:
        print("\n(⏸️  Sin API key: no llamo al modelo. Pon la llave en .env para verlo en acción.)")
        print("    Recuerda: el proveedor debe OÍR (Gemini acepta audio; Groq de solo texto no).")
        return

    print("\n== Enviando el audio a un modelo que oye ==\n")
    try:
        respuesta = util.crear_llm().invoke([mensaje])
        print(f"  Respuesta: {respuesta.content}")
    except Exception as error:  # noqa: BLE001 — cuota, red o proveedor sin audio
        if util.es_error_cuota(error):
            print(util.mensaje_cuota())
        else:
            print(f"❌ El modelo no pudo responder (¿oye el proveedor?): {error}")


if __name__ == "__main__":
    main()
