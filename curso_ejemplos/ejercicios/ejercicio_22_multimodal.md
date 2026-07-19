# Ejercicio 22 — Multimodal: el mensaje deja de ser un string

**Ejemplo base:** `22_multimodal.py` · `22b_voz.py` · **Gasta cuota:** no
(armar los mensajes es 100% offline; enviarlos al modelo es opcional)

> En texto, un mensaje es un string. En multimodal, es una **lista de bloques
> tipados** — y casi todos los errores de multimodal son errores de armar mal
> esa lista. Este ejercicio te hace construirla a mano, predecir su forma y
> recorrer el pipeline de voz sin gastar un token.

## Contexto

`22_multimodal.py` arma un `HumanMessage` con dos bloques (`text` +
`image_url`) y `22b_voz.py` hace lo mismo para audio (`media` + `mime_type`),
el payload de TTS y el pipeline de voz en streaming
(`pipeline_voz_streaming`), todo determinista.

## Parte 1 — Dos imágenes en un solo mensaje

`mensaje_multimodal(texto, data_url)` acepta UNA imagen. Escribe
`mensaje_multimodal_varias(texto, data_urls)` que acepte una lista (piensa en
"compara estas dos fotos del mismo producto").

**Criterio de aceptación:** predice, antes de ejecutar, cuántos bloques tendrá
`content` con 2 imágenes y en qué posición queda el texto. Tu función debe
producir exactamente esa estructura (compruébalo con `len` y con los `type` de
cada bloque), y con una lista vacía debe degradar al mensaje de texto normal.

## Parte 2 — Audio de entrada: el bloque que NO es `image_url`

Usa `audio_a_bloque` (del 22b) para armar el bloque de un audio `.wav` y de un
`.mp3` con los mismos bytes.

**Criterio de aceptación:** predice qué campos cambian entre ambos bloques y
cuáles no. Después responde: ¿por qué el audio necesita declarar `mime_type` si
la imagen del m22 no lo declara en su bloque? (pista: mira dónde quedó el mime
en `imagen_a_data_url`).

## Parte 3 — TTS: la petición que no es un mensaje

Construye `peticion_tts("El pedido llega mañana.", voz="verse", formato="wav")`.

**Criterio de aceptación:** predice las claves del dict resultante y explica en
una frase por qué el TTS **no** puede modelarse como un mensaje más del chat
(qué devuelve el servidor que lo hace distinto).

## Parte 4 — Cuenta las síntesis antes de correr el pipeline

El pipeline real sintetiza **por frases**, no al final. Dado este `responder`
inyectado:

```python
def responder(transcripcion):
    yield from ["Claro. ", "Tenemos dos modelos. ", "¿Cuál prefieres?"]
```

y `fragmentos_audio = ["hola ", "quiero ", "audífonos"]`, recorre
`pipeline_voz_streaming(fragmentos_audio, responder)` guardando los eventos.

**Criterio de aceptación:** predice, ANTES de ejecutar: (1) cuántos eventos
`("audio", …)` salen y por qué; (2) cuántos `("parcial", …)`; (3) el orden
exacto de los TIPOS de evento. Luego verifica los tres números con un
`Counter`. Bonus: ¿qué pasaría con el conteo de audios si la respuesta
terminara sin puntuación final?

---

## Pistas

<details>
<summary>Pista 1 — la lista de bloques</summary>

El contenido multimodal siempre es `[bloque, bloque, …]` y cada bloque declara
su `type`. Con texto + 2 imágenes son **3 bloques**, texto primero:

```python
def mensaje_multimodal_varias(texto, data_urls):
    return HumanMessage(content=[
        {"type": "text", "text": texto},
        *[{"type": "image_url", "image_url": {"url": u}} for u in data_urls],
    ])
```

Con la lista vacía, el desempaquetado `*[]` no añade nada: queda un mensaje de
un solo bloque de texto — exactamente el degradado que pide el criterio.

</details>

<details>
<summary>Pista 2 — dónde vive el mime</summary>

En la imagen, el mime viaja **dentro del data URL** (`data:image/png;base64,…`):
el bloque no lo repite porque la URL ya lo lleva. En el audio, el bloque `media`
lleva los bytes en `data` pelado (sin prefijo), así que el `mime_type` tiene que
ir como campo aparte — si no, el proveedor no sabría si decodifica un wav o un
mp3. Entre `.wav` y `.mp3` cambia SOLO `mime_type`; `type` y `data` son
idénticos (mismos bytes → mismo base64).

</details>

<details>
<summary>Pista 3 — por qué el TTS va aparte</summary>

Un mensaje de chat produce **texto** (más bloques de texto). El TTS produce
**bytes de audio**: la respuesta no es un mensaje que puedas encadenar en la
conversación, es un archivo. Por eso `peticion_tts` arma una petición aparte
(`input`, `voice`, `format`) contra un endpoint distinto, y por eso en el m22b
el TTS se dispara por frase desde el pipeline, no desde el historial del chat.

</details>

<details>
<summary>Pista 4 — el conteo de eventos</summary>

- `("parcial", …)`: uno por fragmento de audio → **3**.
- `("final_stt", …)`: **1**.
- `("token", …)`: uno por token del responder → **3**.
- `("audio", …)`: uno por FRASE de la respuesta completa. La respuesta
  concatenada es `"Claro. Tenemos dos modelos. ¿Cuál prefieres?"` y
  `_dividir_en_frases` corta en `.`, `!`, `?` → **3 audios**.

El orden de tipos: todos los `parcial`, luego `final_stt`, luego todos los
`token`, luego todos los `audio`.

Bonus: si la respuesta termina sin puntuación, el resto pendiente se emite
igual (el `if frase.strip()` final del generador) — el conteo no baja, pero esa
última síntesis solo puede salir cuando el LLM terminó del todo: la puntuación
es lo que permite adelantar audio.

</details>

---

## Reflexión

Todo el módulo cabe en una idea: **multimodal = el mismo chat, con bloques
tipados**. La imagen entra como bloque, el audio entra como bloque, y lo único
que de verdad es distinto —la voz de salida— se va a una petición aparte porque
su respuesta no es texto. Si tienes clara la forma de la lista, el resto es
elegir proveedor con visión y pagar la cuota.

**Solución:** [`soluciones/solucion_22_multimodal.py`](soluciones/solucion_22_multimodal.py)
