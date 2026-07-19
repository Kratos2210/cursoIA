"""
logs.py · Logging estructurado: lo que se lee cuando una clienta reclama
========================================================================
FINALIDAD:
  Que un fallo del asistente se pueda INVESTIGAR. Un `print()` en un VPS con
  varios workers de uvicorn produce esto:

      Error al responder
      Error al responder
      buscando en el catálogo...

  Tres líneas sin dueño. ¿De la misma clienta? ¿Del mismo worker? ¿Antes o
  después del timeout de Groq? No hay forma de saberlo. El log estructurado
  produce esto otro:

      {"ts":"2026-07-18T20:14:02Z","nivel":"ERROR","mensaje":"request falló",
       "request_id":"a3f9c1","ruta":"/chat","logger":"proyecto_retail.app.main"}

  Ahora se puede filtrar por `request_id` y reconstruir UNA petición entera.
  Esto importa especialmente aquí: cuando alguien reporta "me dijo un precio
  que no era", lo primero que necesitas es SU petición, no todas.

LÓGICA — las tres decisiones que importan:

  1) JSON A STDOUT, no a un archivo. Es la regla 11 de los 12 factores: la app
     no gestiona sus logs, los ESCUPE. Quien los recoge (docker, journald, Loki)
     ya sabe rotarlos y agregarlos. Un archivo dentro del contenedor se pierde
     cuando el contenedor muere, que es todo el rato.

  2) ⭐ EL `request_id` VIAJA EN UN ContextVar, no en un parámetro. Pasarlo a
     mano obligaría a ensuciar la firma de TODAS las funciones (`responder(...,
     request_id)`) hasta la última capa. Un ContextVar es una variable global
     que respeta la concurrencia: cada tarea asíncrona ve SU valor, aunque haya
     cien peticiones a la vez. El middleware lo fija al entrar y lo suelta al
     salir; cualquier log emitido en medio lo hereda solo.

  3) EL NIVEL SE ELIGE POR ENTORNO (`LOG_LEVEL`). En desarrollo quieres DEBUG;
     en producción, INFO. Recompilar para cambiar la verbosidad no es una opción.

⚠️ LO QUE NO SE LOGUEA, y es deliberado: la pregunta de la clienta y la respuesta
   del modelo. En retail eso es dato de cliente ("¿tienen algo para el
   cumpleaños de mi hija?" es PII de contexto, aunque no traiga un DNI) y los
   logs suelen acabar en un tercero que no está en el acuerdo de tratamiento de
   datos. Se loguea la FORMA de la petición (ruta, estado, si hubo cache hit),
   nunca su contenido. Si necesitas el contenido para depurar, ahí está Langfuse,
   que sí es infraestructura tuya.

⚠️ ESTE MÓDULO ES UN GEMELO del de proyecto_llmops, no una importación de él.
   Los dos proyectos son deliberadamente independientes (ver el aviso de
   pythonpath en pyproject.toml): compartir el módulo acoplaría el despliegue de
   Sifrah al de GobData, y la duplicación de 150 líneas cuesta menos que ese
   acoplamiento.
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# El identificador de la petición en curso. Vacío fuera de una request (por
# ejemplo, en los logs del arranque, que no pertenecen a nadie).
_request_id: ContextVar[str] = ContextVar("request_id", default="")

# Los atributos que `logging` mete en CADA registro. Todo lo que no esté aquí es
# un campo que puso quien llamó (vía `extra=`), y por eso se emite al JSON.
_ATRIBUTOS_ESTANDAR = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"asctime", "message", "taskName"}


def fijar_request_id(valor: str):
    """Fija el id de la petición en curso. Devuelve el token para restaurarlo."""
    return _request_id.set(valor)


def reiniciar_request_id(token) -> None:
    """Deshace un `fijar_request_id`. Va SIEMPRE en un `finally`.

    Sin esto, un worker que atiende la petición B podría seguir viendo el id de
    la A: los ContextVar no se limpian solos al acabar una tarea.
    """
    _request_id.reset(token)


def request_id_actual() -> str:
    """El id de la petición en curso ('' si estamos fuera de una)."""
    return _request_id.get()


class FormateadorJSON(logging.Formatter):
    """Convierte un LogRecord en UNA línea de JSON.

    Una línea por evento es lo que esperan los recolectores de logs. Un traceback
    multilínea rompería esa promesa, así que se serializa DENTRO del campo
    `excepcion` en vez de escupirse en crudo.
    """

    def format(self, record: logging.LogRecord) -> str:
        datos = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc)
                          .isoformat(timespec="milliseconds")
                          .replace("+00:00", "Z"),
            "nivel": record.levelname,
            "mensaje": record.getMessage(),
            "logger": record.name,
        }

        # El hilo de Ariadna. Solo si estamos dentro de una petición.
        if rid := _request_id.get():
            datos["request_id"] = rid

        # Los campos que pasó quien llamó: logger.info("...", extra={"ruta": ...}).
        for clave, valor in record.__dict__.items():
            if clave not in _ATRIBUTOS_ESTANDAR:
                datos[clave] = valor

        if record.exc_info:
            datos["excepcion"] = self.formatException(record.exc_info)

        # default=str: un objeto no serializable degrada a su repr en vez de
        # tumbar el logging. Un log que revienta al reportar un fallo te deja
        # ciego justo en el momento en el que más ves falta.
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO", stream=None, forzar: bool = False) -> None:
    """Deja el logging raíz escupiendo JSON a stdout. Idempotente.

    Se llama UNA vez, al construir la app. Es idempotente porque uvicorn con
    `--reload` reimporta el módulo, y sin esta guarda cada recarga añadiría otro
    handler: la misma línea repetida dos, tres, cuatro veces.

    `stream` existe para poder dirigir la salida a otro sitio (stderr, o un
    buffer en los tests). Por defecto, stdout: es lo que espera el recolector
    de logs del contenedor.

    `forzar` sustituye el handler aunque ya hubiera uno. Lo necesitan los tests:
    pytest reordena los handlers del logger raíz entre sus fases, así que un
    handler instalado "antes" puede haber desaparecido cuando corre el test.
    """
    raiz = logging.getLogger()
    raiz.setLevel(nivel.upper())

    for handler in list(raiz.handlers):
        if isinstance(handler, logging.StreamHandler) and \
                isinstance(handler.formatter, FormateadorJSON):
            if not forzar:
                handler.setLevel(nivel.upper())
                return                  # ya estaba configurado
            raiz.removeHandler(handler)  # lo reemplazamos por el nuevo

    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(FormateadorJSON())
    handler.setLevel(nivel.upper())
    raiz.addHandler(handler)
    _callar_a_los_ruidosos()


# Librerías que en INFO narran cada llamada HTTP que hacen. Bajarse el catálogo
# live (data/fetch_catalogo.py) o hablar con Groq dispara peticiones que
# acabarían todas en el log del servicio: la señal se ahoga en el ruido y el
# operador deja de leerlo. Se las sube a WARNING, así siguen avisando de lo malo.
_RUIDOSOS = ("httpx", "httpcore", "urllib3", "openai", "filelock")


def _callar_a_los_ruidosos() -> None:
    for nombre in _RUIDOSOS:
        logging.getLogger(nombre).setLevel(logging.WARNING)


def obtener_logger(nombre: str) -> logging.Logger:
    """El logger de un módulo. Se usa `__name__` para que el campo `logger` del
    JSON diga de dónde salió la línea sin que nadie lo escriba a mano."""
    return logging.getLogger(nombre)
