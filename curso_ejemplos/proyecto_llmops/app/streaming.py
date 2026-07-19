"""
streaming.py · Token a token, sin renunciar al guardrail de salida
===================================================================
FINALIDAD:
  Que el usuario vea la respuesta aparecer desde el primer token. No es cosmética:
  con streaming, una respuesta de 4 segundos se percibe como instantánea, porque
  lo que el ojo mide es el **TTFT** (time to first token), no el tiempo total.

  Pero el streaming choca de frente con `guardrails/output_guard.py`:

      Para filtrar la respuesta hay que tener la respuesta.
      Para hacer streaming hay que emitirla antes de tenerla.

  Esa contradicción es real y la mayoría de los tutoriales la resuelven
  ignorándola: hacen streaming y quitan el guardrail. Aquí no.

LÓGICA — el buffer de retención:
  Emitimos todo MENOS los últimos `VENTANA` caracteres. Esa cola retenida es la
  garantía: si un término sensible ("api_key", "clave maestra") tiene como mucho
  `VENTANA` caracteres, entonces **nunca puede quedar a caballo** entre lo ya
  emitido y lo retenido. Cuando el término se completa, sigue íntegro dentro de
  la ventana, y lo tapamos antes de que salga.

      texto acumulado:  "...la clave maes|tra está en el HSM"
                         └── ya emitido ──┘└─ retenido (VENTANA) ─┘
      El canario "clave maestra" se completa DENTRO de la zona retenida.
      → se bloquea antes de emitir un solo carácter de él.

  El precio: el usuario ve la respuesta con `VENTANA` caracteres de retraso.
  A 64 caracteres, es imperceptible. El TTFT sube unos milisegundos; la fuga
  baja a cero. Es el intercambio correcto.

  ⚠️ LA INVARIANTE QUE SOSTIENE TODO: `VENTANA` debe ser >= la longitud del
     patrón más largo que sabemos detectar. Si añades a `policy.py` un término
     de 80 caracteres y no subes VENTANA, este módulo deja de ser correcto en
     silencio. Por eso hay un test que lo comprueba.

  ⚠️ Y EL LÍMITE HONESTO: esto protege contra los patrones que CONOCEMOS. Si el
     modelo parafrasea un anexo restringido sin usar ninguna palabra canario, el
     buffer no lo ve. La defensa de verdad sigue siendo el RBAC del retriever:
     no entregarle al modelo lo que no debe leer. Esto es la última red, no la
     primera.
"""
from __future__ import annotations

import json

from guardrails import policy
from guardrails.output_guard import revisar_salida

# Cuántos caracteres se retienen. Debe superar el patrón más largo detectable:
# términos sensibles, canarios de nivel y la PII más larga (una tarjeta de 19
# dígitos con separadores ocupa ~24 caracteres). 64 da margen de sobra.
VENTANA = 64


class GuardiaDeStream:
    """Deja pasar los tokens que ya es seguro emitir. Uno por uno.

    Uso:
        guardia = GuardiaDeStream(rol="analyst")
        for token in stream:
            trozo = guardia.empujar(token)
            if guardia.bloqueado:
                yield evento_sse({"error": guardia.motivo}, evento="bloqueado"); return
            if trozo:
                yield evento_sse({"token": trozo})
        yield evento_sse({"token": guardia.cerrar()})

    Es una máquina de estados PURA: no toca la red, no llama al modelo. Se le
    empujan strings y devuelve strings. Por eso se testea entera sin un LLM.
    """

    def __init__(self, rol: str = "analyst", ventana: int = VENTANA):
        self.rol = rol
        self.ventana = ventana
        self._acumulado = ""    # todo lo que el modelo ha dicho
        self._emitido = ""      # lo que ya salió hacia el usuario (saneado)
        self.bloqueado = False
        self.motivo: str | None = None

    def empujar(self, token: str) -> str:
        """Añade un token y devuelve el texto que YA es seguro emitir ('' si nada).

        Si detecta una fuga de nivel, marca `bloqueado` y devuelve ''. El
        llamador debe cortar el stream: lo que salió hasta ahora era inofensivo
        (el canario nunca llegó a emitirse), pero lo que viene, no.
        """
        if self.bloqueado:
            return ""

        # ⚠️ Coste: revisamos el acumulado ENTERO en cada token, así que el
        #    trabajo total crece con el cuadrado de la longitud. Con respuestas
        #    de unos miles de caracteres es ruido frente a la latencia del
        #    modelo. Para respuestas muy largas habría que revisar solo la cola.
        self._acumulado += token

        # 1) ¿Fuga de nivel? Se decide sobre TODO lo acumulado, no sobre el token.
        #    Un canario se completa dentro de la ventana retenida, así que aquí
        #    lo cazamos antes de haber emitido ni un carácter de él.
        veredicto = revisar_salida(self._acumulado, self.rol)
        if not veredicto.permitido:
            self.bloqueado = True
            self.motivo = veredicto.motivo
            return ""

        # 2) Saneamos TODO lo acumulado (redacción + PII) y retenemos la cola.
        #    Sanear el acumulado entero, y no solo el token, es lo que permite
        #    tapar un término que se formó a lo largo de varios tokens.
        saneado = veredicto.texto
        seguro = saneado[:max(0, len(saneado) - self.ventana)]

        # 3) El delta: lo seguro menos lo ya emitido.
        #    La invariante (ventana >= patrón más largo) garantiza que `seguro`
        #    siempre empieza por `self._emitido`: un término dentro de la zona ya
        #    emitida estaba completo cuando se emitió, luego ya iba saneado.
        if not seguro.startswith(self._emitido) or len(seguro) <= len(self._emitido):
            return ""

        nuevo = seguro[len(self._emitido):]
        self._emitido = seguro
        return nuevo

    def cerrar(self) -> str:
        """El último trozo: la cola retenida, ya saneada. Llamar al terminar el stream."""
        if self.bloqueado:
            return ""
        veredicto = revisar_salida(self._acumulado, self.rol)
        if not veredicto.permitido:      # el canario estaba en la mismísima cola
            self.bloqueado = True
            self.motivo = veredicto.motivo
            return ""
        return veredicto.texto[len(self._emitido):]

    @property
    def texto_completo(self) -> str:
        """La respuesta entera y saneada. Es ESTA la que se cachea, no la cruda."""
        veredicto = revisar_salida(self._acumulado, self.rol)
        return veredicto.texto


def longitud_maxima_de_patron() -> int:
    """El patrón más largo que los guardrails saben reconocer.

    Existe para que un test pueda afirmar `VENTANA >= longitud_maxima_de_patron()`
    y que añadir un término largo a policy.py no rompa el streaming en silencio.
    """
    from guardrails.output_guard import _CANARIOS_RESTRINGIDOS
    patrones = (*policy.TERMINOS_SENSIBLES_SALIDA, *_CANARIOS_RESTRINGIDOS)
    return max(len(p) for p in patrones)


# ------------------------------------------------------------------
# El formato SSE (Server-Sent Events)
# ------------------------------------------------------------------
def evento_sse(datos: dict, evento: str | None = None) -> str:
    """Formatea un evento SSE. FUNCIÓN PURA.

    SSE es un protocolo de texto ridículamente simple sobre HTTP: líneas
    `campo: valor` y una línea EN BLANCO que cierra el evento. Esa línea en
    blanco no es estilo — es el delimitador. Sin ella, el navegador espera
    para siempre.

        event: token
        data: {"token": "hola"}
        <línea en blanco>

    Se elige SSE y no WebSocket porque el flujo es de una sola dirección
    (servidor → cliente): un WebSocket sería una conexión bidireccional para no
    usar la vuelta. SSE reconecta solo y viaja por HTTP normal.
    """
    lineas = []
    if evento:
        lineas.append(f"event: {evento}")
    # ensure_ascii=False: la normativa está en español y 'ó' no se lee.
    lineas.append(f"data: {json.dumps(datos, ensure_ascii=False)}")
    return "\n".join(lineas) + "\n\n"


async def tokens_del_agente(agente, mensaje: str, thread_id: str, callbacks=None,
                            contador=None):
    """Los tokens del agente, uno a uno, según los va produciendo el modelo.

    `stream_mode="messages"` es el que emite **chunks de token**. Los otros modos
    de LangGraph (`values`, `updates`) emiten el estado completo tras cada nodo:
    útiles para depurar el grafo, inútiles para escribir en pantalla.

    Filtramos los mensajes de las tools: al usuario le interesa la respuesta del
    agente, no el volcado del retriever.

    `contador` (un `ContadorDeUso`) es opcional y recoge el consumo de paso. Se
    le empuja el fragmento ANTES de filtrar por nodo, a propósito: la llamada que
    decide usar una tool gasta tokens igual que la que redacta la respuesta, y si
    solo contáramos lo que se imprime, el coste saldría corto.
    """
    configuracion = {"configurable": {"thread_id": thread_id}}
    if callbacks:
        configuracion["callbacks"] = callbacks

    async for fragmento, metadatos in agente.astream(
        {"messages": [("user", mensaje)]},
        config=configuracion,
        stream_mode="messages",
    ):
        if contador is not None:
            contador.sumar(fragmento)
        # El nodo 'tools' también emite mensajes; solo queremos los del modelo.
        if metadatos.get("langgraph_node") == "tools":
            continue
        contenido = getattr(fragmento, "content", "")
        if contenido:
            yield contenido
