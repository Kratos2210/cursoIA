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
     base64 dentro de un `data:` URL y se mete como un bloque de contenido junto
     al texto. La llamada REAL al modelo con visión va en `__main__`, protegida
     por la API key (sin llave, imprime la estructura y no gasta cuota).

  📐 FORMATO DE LOS BLOQUES (verificado contra el paquete instalado, no de memoria):
     usamos el bloque estilo "chat completions" que `langchain-google-genai`
     acepta y traduce a la parte `inline_data` que la API de Gemini espera:
         {"type": "text",      "text": "..."}
         {"type": "image_url", "image_url": {"url": "data:image/png;base64,...."}}
     Es el mismo formato que entienden los proveedores compatibles con OpenAI
     (los que usa `crear_llm()` por su rama `ChatOpenAI`), así que el mensaje
     viaja igual cambies o no de proveedor.

LÓGICA (paso a paso):
  1) imagen_a_data_url(): bytes de imagen → `data:{mime};base64,{...}` (stdlib base64).
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


# ============ 1) CODIFICAR LA IMAGEN COMO DATA URL ============
def imagen_a_data_url(datos: bytes, mime: str = "image/png") -> str:
    """Convierte los bytes de una imagen en un `data:` URL con su base64.

    POR QUÉ base64: el JSON de la petición es texto, no puede llevar bytes crudos.
    base64 reescribe los bytes como texto ASCII; el prefijo `data:{mime};base64,`
    le dice al receptor qué tipo de imagen es y cómo decodificarla.
    """
    b64 = base64.b64encode(datos).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ============ 2) ARMAR EL MENSAJE MULTIMODAL ============
def mensaje_multimodal(texto: str, data_url: str) -> HumanMessage:
    """Construye un HumanMessage con DOS bloques: el texto y la imagen.

    El contenido de un mensaje deja de ser un string y pasa a ser una LISTA de
    bloques. Cada bloque declara su `type`. El de imagen usa el `data:` URL que
    produjo `imagen_a_data_url`. El modelo con visión lee ambos como una sola
    entrada: "mira esta imagen Y responde a esta pregunta".
    """
    return HumanMessage(content=[
        {"type": "text", "text": texto},
        {"type": "image_url", "image_url": {"url": data_url}},
    ])


def main() -> None:
    import util

    imagen = base64.b64decode(PNG_DEMO_1x1)
    data_url = imagen_a_data_url(imagen, mime="image/png")
    pregunta = "¿Qué ves en esta imagen? Descríbela en una frase."
    mensaje = mensaje_multimodal(pregunta, data_url)

    print("== Mensaje multimodal construido ==\n")
    print(f"  Bloques: {len(mensaje.content)}")
    print(f"  [0] type={mensaje.content[0]['type']!r} · text={mensaje.content[0]['text']!r}")
    bloque_img = mensaje.content[1]
    url = bloque_img["image_url"]["url"]
    print(f"  [1] type={bloque_img['type']!r} · url={url[:40]}… ({len(url)} chars)")

    # La llamada REAL solo si hay llave: sin ella, no gastamos cuota.
    if util.requiere_llm_key() is not None:
        print("\n(⏸️  Sin API key: no llamo al modelo. Pon la llave en .env para verlo en acción.)")
        print("    Recuerda: el proveedor debe tener VISIÓN (Gemini sí; Groq de solo texto no).")
        return

    print("\n== Enviando la imagen a un modelo con visión ==\n")
    try:
        respuesta = util.crear_llm().invoke([mensaje])
        print(f"  Respuesta: {respuesta.content}")
    except Exception as error:  # noqa: BLE001 — cuota, red o proveedor sin visión
        if util.es_error_cuota(error):
            print(util.mensaje_cuota())
        else:
            print(f"❌ El modelo no pudo responder (¿tiene visión el proveedor?): {error}")


if __name__ == "__main__":
    main()
