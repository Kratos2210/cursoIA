"""
auth.py · Quién puede hablar con el asistente
==============================================
FINALIDAD:
  Cerrar la puerta que estaba abierta: hasta aquí, cualquiera que descubriera la
  URL del servicio podía gastar tu cuota de Groq a voluntad. En un asistente de
  compras el riesgo no es que se filtre un secreto (el catálogo es PÚBLICO: está
  en sifrah.com/products.json), es económico y reputacional:

      while true; do curl -X POST .../chat -d '{"mensaje":"hola"}'; done

  Eso son tokens que pagas tú. Y `/metrics` publicaría de paso cuánto tráfico
  manejas y cuánto te cuesta, que es información de negocio.

LÓGICA — una lista de claves válidas, y nada más:
  `API_KEYS` es una lista separada por comas, en el entorno:

      API_KEYS="clave-de-la-web,clave-del-bot-de-whatsapp"

  El cliente manda la suya en la cabecera `X-API-Key`. O vale, o no vale.

  ⭐ POR QUÉ AQUÍ NO HAY ROLES, y en proyecto_llmops sí. No es un descuido ni una
     versión "a medio hacer": es que el dominio no los pide. GobData tiene
     normativa restringida y anexos que un analista no debe ver, así que su
     `auth.py` mapea credencial → rol y alimenta un RBAC (guardrails/rbac.py).
     Aquí TODO el catálogo es público y todo el mundo ve lo mismo; un modelo de
     roles sería maquinaria sin nada que proteger. La autenticación responde
     "¿te dejo entrar?"; la autorización, "¿qué puedes ver?". Sifrah solo
     necesita la primera pregunta. Inventar la segunda sería complejidad
     decorativa — y la complejidad decorativa es la que luego se rompe.

  ⭐ POR QUÉ API KEYS Y NO OAUTH/JWT: porque el salto de valor está en dejar de
     atender a cualquiera, no en el formato del token. Una API key resuelve el
     99 % del caso "la web y el bot llaman a mi backend" con cero
     infraestructura. Cuando haya usuarios finales de verdad con su propia
     sesión, esto se sustituye por un JWT firmado por tu proveedor de identidad
     — y el resto del código no se entera, porque todos dependen de
     `requiere_credencial`, no de cómo se obtuvo.

⚠️ EL MODO ABIERTO Y POR QUÉ EXISTE: si `API_KEYS` está vacío, el servicio
   atiende a todo el mundo. Es lo que mantiene el curso ejecutable con un
   `uvicorn` y sin configurar nada. Pero NO es silencioso: se avisa al arrancar
   y `/health` lo publica en `auth_activa`. Un despliegue real sin claves es una
   decisión que se ve, no un descuido que se hereda.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from proyecto_retail.app.config import settings
from proyecto_retail.observability import logs

log = logs.obtener_logger(__name__)


def _parsear_api_keys(crudo: str) -> list[str]:
    """"clave1,clave2" → ["clave1", "clave2"]. Descarta vacíos y espacios.

    Un `API_KEYS="clave1, ,clave2"` (por una coma de más al editar el .env) no
    debe registrar una credencial vacía: con ella, mandar la cabecera en blanco
    valdría por una clave buena.
    """
    return [c.strip() for c in crudo.split(",") if c.strip()]


def claves_configuradas() -> list[str]:
    """Las credenciales vigentes. Lista vacía = modo abierto.

    Se lee de `settings` en cada llamada y no se cachea a propósito: así los
    tests pueden cambiar `API_KEYS` con `monkeypatch` sin reconstruir la app.
    El coste es partir un string corto, no una lectura de disco.
    """
    return _parsear_api_keys(settings.api_keys)


def auth_activa() -> bool:
    """¿Hay al menos una credencial configurada?"""
    return bool(claves_configuradas())


def credencial_valida(clave: str | None) -> bool:
    """¿Esta clave está en la lista? La función central del módulo.

    ⭐ `compare_digest` y no `==`: comparar strings con `==` corta en el primer
       carácter distinto, así que el TIEMPO de la comparación filtra cuántos
       caracteres acertaste. Con suficientes intentos, eso permite adivinar la
       clave carácter a carácter. `compare_digest` tarda lo mismo siempre.

    ⚠️ Se recorren TODAS las claves aunque una ya haya coincidido. Salir con un
       `return True` anticipado volvería a filtrar por tiempo: una clave que
       coincide con la primera de la lista respondería antes que una que
       coincide con la última.
    """
    if not clave:
        return False
    acierto = False
    for candidata in claves_configuradas():
        if secrets.compare_digest(clave, candidata):
            acierto = True
    return acierto


async def requiere_credencial(x_api_key: str | None = Header(default=None)) -> None:
    """Dependencia de FastAPI: protege un endpoint. 401 si la clave no vale.

    Se usa así:

        @app.get("/metrics", dependencies=[Depends(requiere_credencial)])

    FastAPI convierte `x_api_key` en la cabecera `X-API-Key` automáticamente.

    No devuelve nada (a diferencia del de llmops, que devuelve el rol): sin
    autorización que resolver, la credencial no aporta ningún dato al endpoint.
    Su único efecto es dejar pasar o cortar.
    """
    if not auth_activa():
        return                      # modo abierto: el del curso
    if not credencial_valida(x_api_key):
        # Sin detalles en la respuesta: "clave inválida" y "clave ausente" se
        # contestan igual, para no confirmarle nada a quien esté probando.
        log.warning("credencial rechazada")
        raise HTTPException(status_code=401, detail="Credencial inválida o ausente")


def avisar_del_modo_abierto() -> None:
    """Un aviso ruidoso al arrancar si el servicio queda abierto.

    Va en el arranque y no en cada request a propósito: en el arranque se lee,
    en cada request se ignora.
    """
    if auth_activa():
        log.info("auth activa", extra={"credenciales": len(claves_configuradas())})
        return
    log.warning(
        "SERVICIO ABIERTO: sin API_KEYS, cualquiera puede consultar el asistente "
        "y gastar tu cuota del proveedor. Correcto para la demo del curso; en un "
        "despliegue real, configura API_KEYS='clave1,clave2'")
