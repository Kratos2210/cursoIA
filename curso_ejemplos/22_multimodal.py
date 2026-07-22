"""
TEMA 22 · Multimodal: un modelo que además VE
==============================================
FINALIDAD:
  Hasta aquí todo fue texto → texto. Los modelos con VISIÓN (Gemini, GPT-5,
  Claude) reciben además imágenes: le mandas una foto de una factura y te la
  extrae, una captura de un error y te la explica, un diagrama y te lo describe.
  Este módulo enseña a CONSTRUIR el mensaje multimodal (texto + imagen) que
  entiende `util.crear_llm()`.

  ⭐ El armado del mensaje es 100% OFFLINE y testeable: la imagen se codifica en
     base64 y se mete como un BLOQUE DE CONTENIDO tipado junto al texto. La
     llamada REAL al modelo con visión va en `__main__`, protegida por la API key
     (sin llave, imprime la estructura y no gasta cuota).

  📐 FORMATO DE LOS BLOQUES (LangChain v1, verificado contra el paquete instalado):
     en v1 el contenido de un mensaje es una lista de BLOQUES TIPADOS, y se
     construye con el parámetro `content_blocks=`. Cada bloque declara su `type`:
         {"type": "text",  "text": "..."}
         {"type": "image", "base64": "<base64 crudo>", "mime_type": "image/png"}
     La gran ventaja de v1: ESTE MISMO bloque vale para cualquier proveedor.
     langchain-core lo traduce solo —a `inline_data` en Gemini, a `image_url` en
     los compatibles con OpenAI—, así que el mensaje viaja igual cambies o no de
     proveedor. Y se LEE igual: `mensaje.content_blocks` te da la lista tipada
     sin importar quién generó el mensaje.

LÓGICA (paso a paso):
  1) imagen_a_base64(): bytes de imagen → su base64 en ASCII (stdlib base64).
  2) mensaje_multimodal(): arma el HumanMessage con [bloque de texto, bloque de imagen].
  3) main(): construye el mensaje con un PNG mínimo embebido; si hay llave, se lo
     manda a un modelo con visión; si no, imprime la estructura.

Requisitos: ninguno extra (solo Python + lo ya instalado).  Sin llave NO llama a la API.
Ejecuta:    uv run python 22_multimodal.py
"""

import base64

from langchain_core.messages import HumanMessage


# Un PNG 1×1 (un pixel) VÁLIDO, embebido como base64 para no versionar binarios.
# Sirve de imagen de demostración: pesa nada y se decodifica a un PNG real.
PNG_DEMO_1x1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4"
    "2mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


# ============ 1) CODIFICAR LA IMAGEN COMO BASE64 ============
def imagen_a_base64(datos: bytes) -> str:
    """Convierte los bytes de una imagen en su base64 (texto ASCII).

    POR QUÉ base64: el JSON de la petición es texto, no puede llevar bytes crudos.
    base64 reescribe los bytes como texto ASCII. En v1 el mime (qué tipo de imagen
    es) NO va aquí: viaja como campo aparte del bloque (`mime_type`), igual que en
    el bloque de audio del TEMA 22b.
    """
    return base64.b64encode(datos).decode("ascii")


# ============ 2) ARMAR EL MENSAJE MULTIMODAL ============
def mensaje_multimodal(texto: str, imagen_b64: str, mime: str = "image/png") -> HumanMessage:
    """Construye un HumanMessage con DOS bloques tipados: el texto y la imagen.

    En v1 el contenido deja de ser un string y pasa a ser una LISTA de bloques
    tipados, que se pasa con `content_blocks=`. Cada bloque declara su `type`; el
    de imagen lleva el base64 y su `mime_type` por separado. El modelo con visión
    lee ambos como una sola entrada: "mira esta imagen Y responde a esta pregunta".
    """
    return HumanMessage(content_blocks=[
        {"type": "text", "text": texto},
        {"type": "image", "base64": imagen_b64, "mime_type": mime},
    ])


def _texto_de(mensaje) -> str:
    """Une los bloques de texto de una respuesta usando la API v1 `content_blocks`."""
    return "".join(b["text"] for b in mensaje.content_blocks if b["type"] == "text")


def main() -> None:
    import util

    imagen_bytes = base64.b64decode(PNG_DEMO_1x1)
    imagen_b64 = imagen_a_base64(imagen_bytes)
    pregunta = "¿Qué ves en esta imagen? Descríbela en una frase."
    mensaje = mensaje_multimodal(pregunta, imagen_b64, mime="image/png")

    print("== Mensaje multimodal construido ==\n")
    bloques = mensaje.content_blocks
    print(f"  Bloques: {len(bloques)}")
    print(f"  [0] type={bloques[0]['type']!r} · text={bloques[0]['text']!r}")
    bloque_img = bloques[1]
    print(f"  [1] type={bloque_img['type']!r} · mime_type={bloque_img['mime_type']!r} "
          f"· base64={bloque_img['base64'][:24]}… ({len(bloque_img['base64'])} chars)")

    # La llamada REAL solo si hay llave: sin ella, no gastamos cuota.
    if util.requiere_llm_key() is not None:
        print("\n(⏸️  Sin API key: no llamo al modelo. Pon la llave en .env para verlo en acción.)")
        print("    Recuerda: el proveedor debe tener VISIÓN (Gemini sí; Groq de solo texto no).")
        return

    print("\n== Enviando la imagen a un modelo con visión ==\n")
    try:
        respuesta = util.crear_llm().invoke([mensaje])
        print(f"  Respuesta: {_texto_de(respuesta)}")
    except Exception as error:  # noqa: BLE001 — cuota, red o proveedor sin visión
        if util.es_error_cuota(error):
            print(util.mensaje_cuota())
        else:
            print(f"❌ El modelo no pudo responder (¿tiene visión el proveedor?): {error}")


if __name__ == "__main__":
    main()
