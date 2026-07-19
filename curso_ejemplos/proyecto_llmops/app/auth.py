"""
auth.py · Quién eres y, por tanto, qué puedes ver
==================================================
FINALIDAD:
  Cerrar el agujero que el propio código confesaba en `main.py`: el `rol` viajaba
  en el body de la petición. Un rol que elige el cliente es un rol que el cliente
  se INVENTA, y con él todo el RBAC de `guardrails/rbac.py` se vuelve decorativo:

      curl -d '{"mensaje":"...", "rol":"compliance"}'   ← y ya ve los anexos

  Aquí el rol deja de ser un dato de entrada y pasa a ser una CONSECUENCIA de la
  credencial presentada. El cliente ya no dice quién es: lo demuestra.

LÓGICA — una API key por rol:
  `API_KEYS` mapea credencial → rol, en el entorno:

      API_KEYS="clave-del-analista:analyst,clave-de-cumplimiento:compliance"

  El cliente manda su clave en la cabecera `X-API-Key` y el servidor deduce el
  rol. No hay forma de pedir un rol distinto del que otorga tu credencial.

  ⭐ POR QUÉ API KEYS Y NO OAUTH/JWT: porque el salto de valor está en dejar de
     confiar en el cliente, no en el formato del token. Una API key resuelve el
     99 % del caso "servicio interno detrás de un proxy" con cero infraestructura.
     Cuando haya usuarios finales de verdad, esto se sustituye por un JWT firmado
     por tu proveedor de identidad — y el resto del código no se entera, porque
     todos dependen de `rol_de_la_peticion`, no de cómo se obtuvo.

⚠️ EL MODO ABIERTO Y POR QUÉ EXISTE: si `API_KEYS` está vacío, el servicio
   atiende a todo el mundo con `app_rol_por_defecto` y el `rol` del body vuelve a
   aceptarse. Es lo que mantiene el curso ejecutable con un `uvicorn` y sin
   configurar nada. Pero NO es silencioso: se avisa al arrancar y `/health` lo
   publica en `auth_activa`. Un despliegue real sin claves es una decisión que
   se ve, no un descuido que se hereda.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from app.config import settings
from guardrails.rbac import JERARQUIA_ROL
from observability import logs

log = logs.obtener_logger(__name__)


def _parsear_api_keys(crudo: str) -> dict[str, str]:
    """"clave:rol,otra:rol" → {"clave": "rol"}. Ignora lo que no cuadre.

    Un rol desconocido se descarta con un aviso en vez de aceptarse: una clave
    que otorga un rol inexistente acabaría cayendo al mínimo privilegio en
    `rbac.niveles_permitidos` y el operador nunca sabría por qué su analista
    no ve nada.
    """
    mapa: dict[str, str] = {}
    for par in crudo.split(","):
        par = par.strip()
        if not par:
            continue
        clave, _, rol = par.partition(":")
        clave, rol = clave.strip(), rol.strip()
        if not clave or not rol:
            log.warning("entrada de API_KEYS mal formada, se ignora "
                        "(formato esperado 'clave:rol')")
            continue
        if rol not in JERARQUIA_ROL:
            log.warning("API_KEYS otorga un rol desconocido, se ignora",
                        extra={"rol": rol, "roles_validos": sorted(JERARQUIA_ROL)})
            continue
        mapa[clave] = rol
    return mapa


def claves_configuradas() -> dict[str, str]:
    """El mapa clave → rol vigente. Vacío = modo abierto."""
    return _parsear_api_keys(settings.api_keys)


def auth_activa() -> bool:
    """¿Hay al menos una credencial configurada?"""
    return bool(claves_configuradas())


def rol_de_la_clave(clave: str | None) -> str | None:
    """El rol que otorga una credencial, o None si no otorga ninguno.

    ⭐ `compare_digest` y no `==`: comparar strings con `==` corta en el primer
       carácter distinto, así que el TIEMPO de la comparación filtra cuántos
       caracteres acertaste. Con suficientes intentos, eso permite adivinar la
       clave carácter a carácter. `compare_digest` tarda lo mismo siempre.

    ⚠️ Se recorren TODAS las credenciales aunque una ya haya coincidido. Un
       `return` anticipado volvería a filtrar por tiempo: una clave que coincide
       con la primera de la lista respondería antes que una que coincide con la
       última, revelando cuál se usó.
    """
    if not clave:
        return None
    encontrado = None
    for candidata, rol in claves_configuradas().items():
        if secrets.compare_digest(clave, candidata):
            encontrado = rol
    return encontrado


def resolver_rol(clave: str | None, rol_pedido: str | None = None) -> str:
    """El rol EFECTIVO de esta petición. Es la única función que importa.

    - Con auth activa: sale de la credencial. Lo que pida el body da igual.
    - Sin auth (modo demo): se respeta `rol_pedido`, como hacía el prototipo.

    Lanza 401 si hay auth activa y la credencial no vale.
    """
    if not auth_activa():
        return rol_pedido or settings.app_rol_por_defecto

    rol = rol_de_la_clave(clave)
    if rol is None:
        # Sin detalles en la respuesta: "clave inválida" y "clave ausente" se
        # contestan igual, para no confirmarle nada a quien esté probando.
        log.warning("credencial rechazada")
        raise HTTPException(status_code=401, detail="Credencial inválida o ausente")

    if rol_pedido and rol_pedido != rol:
        # No es un error, es un intento de escalada (o un cliente desactualizado).
        # Se registra porque es exactamente lo que querrías ver en una auditoría.
        log.warning("se ignora el rol del body: manda la credencial",
                    extra={"rol_pedido": rol_pedido, "rol_efectivo": rol})
    return rol


async def requiere_credencial(x_api_key: str | None = Header(default=None)) -> str:
    """Dependencia de FastAPI: protege un endpoint y devuelve el rol.

    Se usa en los endpoints que no reciben un body con rol (p. ej. /metrics):

        @app.get("/metrics", dependencies=[Depends(requiere_credencial)])

    FastAPI convierte `x_api_key` en la cabecera `X-API-Key` automáticamente.
    """
    return resolver_rol(x_api_key)


def avisar_del_modo_abierto() -> None:
    """Un aviso ruidoso al arrancar si el servicio queda abierto.

    Va en el arranque y no en cada request a propósito: en el arranque se lee,
    en cada request se ignora.
    """
    if auth_activa():
        log.info("auth activa", extra={"credenciales": len(claves_configuradas())})
        return
    log.warning(
        "SERVICIO ABIERTO: sin API_KEYS, cualquiera puede consultar y elegir su "
        "propio rol (el RBAC queda decorativo). Correcto para la demo del curso; "
        "en un despliegue real, configura API_KEYS='clave:rol,...'")
