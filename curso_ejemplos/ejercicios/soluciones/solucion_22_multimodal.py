"""
SOLUCIÓN · Ejercicio 22 — Multimodal: el mensaje deja de ser un string
=======================================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Armar a mano las cuatro formas del módulo y AFIRMAR sobre ellas:
    · P1: texto + N imágenes = 1 + N bloques, texto primero.
    · P2: entre wav y mp3 cambia SOLO el mime_type del bloque `media`.
    · P3: el TTS es una petición aparte (su respuesta son bytes, no chat).
    · P4: el pipeline emite parcial×3 → final_stt → token×3 → audio×3.

  100% offline: no se llama a ningún modelo. No gasta cuota.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_22_multimodal.py
"""

import base64
import importlib.util
import os
from collections import Counter

from langchain_core.messages import HumanMessage

# ---- Cargamos los ejemplos 22 y 22b (empiezan por número: no se pueden importar) ----
CARPETA_CURSO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cargar(nombre_archivo, alias):
    ruta = os.path.join(CARPETA_CURSO, nombre_archivo)
    spec = importlib.util.spec_from_file_location(alias, ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


t22 = cargar("22_multimodal.py", "tema22")
t22b = cargar("22b_voz.py", "tema22b")


# ==================================================================
# PARTE 1 · Dos imágenes en un solo mensaje
# ==================================================================
def mensaje_multimodal_varias(texto: str, imagenes_b64: list[str],
                              mime: str = "image/png") -> HumanMessage:
    """Texto primero, luego un bloque `image` (tipado v1) por cada imagen."""
    return HumanMessage(content_blocks=[
        {"type": "text", "text": texto},
        *[{"type": "image", "base64": b64, "mime_type": mime} for b64 in imagenes_b64],
    ])


def parte_1():
    print("\n[P1] texto + 2 imágenes")
    png_b64 = t22.imagen_a_base64(base64.b64decode(t22.PNG_DEMO_1x1))

    msg = mensaje_multimodal_varias("Compara estas dos fotos.", [png_b64, png_b64])
    tipos = [b["type"] for b in msg.content_blocks]
    print(f"     bloques: {len(msg.content_blocks)} · tipos: {tipos}")
    assert len(msg.content_blocks) == 3          # 1 texto + 2 imágenes
    assert tipos == ["text", "image", "image"]   # el texto va primero

    # Con lista vacía degrada al mensaje de texto normal (1 bloque).
    solo_texto = mensaje_multimodal_varias("¿Hola?", [])
    assert [b["type"] for b in solo_texto.content_blocks] == ["text"]
    print("     → 1 + N bloques; con N=0, un chat de texto de toda la vida.")


# ==================================================================
# PARTE 2 · wav vs mp3: solo cambia el mime_type
# ==================================================================
def parte_2():
    print("\n[P2] audio_a_bloque con los mismos bytes")
    datos = b"RIFF....WAVE"                            # bytes de juguete
    wav = t22b.audio_a_bloque(datos, mime="audio/wav")
    mp3 = t22b.audio_a_bloque(datos, mime="audio/mp3")
    print(f"     wav: {{type: {wav['type']!r}, mime_type: {wav['mime_type']!r}}}")
    print(f"     mp3: {{type: {mp3['type']!r}, mime_type: {mp3['mime_type']!r}}}")

    assert wav["type"] == mp3["type"] == "media"
    assert wav["data"] == mp3["data"]                  # mismos bytes → mismo base64
    assert wav["mime_type"] != mp3["mime_type"]        # lo ÚNICO que cambia

    # En v1 la imagen y el audio se parecen: los dos llevan los datos en base64
    # y el `mime_type` como campo aparte del bloque. (El de imagen es `image` con
    # `base64`; el de audio, `media` con `data` — misma idea, distinto nombre.)
    print("     → imagen y audio declaran el mime aparte; cambia el nombre del campo, no la idea.")


# ==================================================================
# PARTE 3 · El TTS es una petición aparte
# ==================================================================
def parte_3():
    print("\n[P3] peticion_tts")
    p = t22b.peticion_tts("El pedido llega mañana.", voz="verse", formato="wav")
    print(f"     claves: {sorted(p.keys())} · payload: {p}")
    # La respuesta de un TTS son BYTES de audio, no texto: no puede encadenarse
    # como un mensaje más del historial. Por eso es una petición aparte.
    print("     → no es chat: el servidor devuelve bytes, no un mensaje.")


# ==================================================================
# PARTE 4 · Contar los eventos del pipeline
# ==================================================================
def parte_4():
    print("\n[P4] pipeline_voz_streaming, contado")

    def responder(transcripcion):
        yield from ["Claro. ", "Tenemos dos modelos. ", "¿Cuál prefieres?"]

    eventos = list(t22b.pipeline_voz_streaming(["hola ", "quiero ", "audífonos"],
                                               responder))
    conteo = Counter(tipo for tipo, _ in eventos)
    print(f"     conteo: {dict(conteo)}")
    print(f"     orden : {[tipo for tipo, _ in eventos]}")

    assert conteo["parcial"] == 3      # uno por fragmento de audio
    assert conteo["final_stt"] == 1
    assert conteo["token"] == 3        # uno por token del responder
    assert conteo["audio"] == 3        # uno por FRASE (. ! ?) de la respuesta

    # El orden es por fases: STT parcial → final → LLM → TTS por frase.
    tipos = [tipo for tipo, _ in eventos]
    assert tipos == ["parcial"] * 3 + ["final_stt"] + ["token"] * 3 + ["audio"] * 3

    # Bonus: sin puntuación final, la última frase pendiente se emite igual —
    # pero ya no se puede ADELANTAR: sale solo cuando el LLM terminó.
    sin_punto = list(t22b._dividir_en_frases("Claro. Un momento"))
    assert sin_punto == ["Claro.", "Un momento"]
    print("     → 3 frases = 3 síntesis; la puntuación es lo que permite adelantar audio.")


def main() -> None:
    print("=" * 64)
    print("SOLUCIÓN 22 · bloques tipados y pipeline de voz (100% OFFLINE)")
    print("=" * 64)
    parte_1()
    parte_2()
    parte_3()
    parte_4()
    print("\nTodo comprobado con asserts. ✅")


if __name__ == "__main__":
    main()
