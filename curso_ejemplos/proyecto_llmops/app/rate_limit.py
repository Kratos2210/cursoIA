"""
rate_limit.py · El freno: cuántas peticiones por minuto y por quién
====================================================================
FINALIDAD:
  Que un solo cliente no pueda vaciarte la cuenta del proveedor. Cada request a
  /chat cuesta dinero real; sin freno, un bucle mal escrito (o un abuso
  deliberado) convierte tu factura en el incidente. El guardrail de entrada
  filtra QUÉ se pregunta; esto limita CUÁNTO.

LÓGICA — ventana deslizante:
  Se guardan las marcas de tiempo de las últimas peticiones de cada cliente y se
  descartan las que ya salieron de la ventana. Si quedan `limite` o más, se
  rechaza con un 429.

      límite 3/min, ventana ────────────────────────────►
      peticiones:   x   x        x                    x
                    └── 3 en la ventana ──┘ la 4ª: 429

  ⭐ POR QUÉ VENTANA DESLIZANTE Y NO CONTADOR POR MINUTO: un contador que se
     reinicia "en punto" permite el doble del límite a caballo entre dos
     ventanas — 3 peticiones a las 10:00:59 y otras 3 a las 10:01:01 son 6 en
     dos segundos, respetando "3 por minuto". La ventana deslizante no tiene
     ese borde.

  ⭐ EL RELOJ SE INYECTA (`ahora`). Así el test comprueba el paso del tiempo sin
     dormir de verdad: una suite que hace `sleep(60)` para probar un límite por
     minuto es una suite que nadie corre.

⚠️ ESTÁ EN MEMORIA Y POR PROCESO. Con N workers de uvicorn, el límite efectivo
   es N × límite, porque cada proceso cuenta lo suyo. Es la misma limitación que
   tienen las métricas (ver observability/metrics.py) y la razón es la misma: el
   estado compartido pide Redis. Para un límite de verdad hay dos caminos, y los
   dos están FUERA de este archivo:
     1) el reverse proxy (nginx `limit_req`, Traefik, Cloudflare) — lo normal, y
        además frena ANTES de gastar un worker de Python;
     2) un contador en Redis, que ya está en la infraestructura del proyecto.
   Esto de aquí es la red de seguridad de último recurso, no la puerta principal.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import settings
from observability import logs

log = logs.obtener_logger(__name__)


class LimitadorVentana:
    """Ventana deslizante por clave. Máquina de estados PURA: sin red, sin reloj
    propio (se le pasa `ahora`), así que se testea entera en milisegundos."""

    def __init__(self, limite: int, ventana_s: float):
        self.limite = limite
        self.ventana_s = ventana_s
        # deque y no lista: se descarta por la izquierda (lo viejo) en O(1).
        self._marcas: dict[str, deque[float]] = defaultdict(deque)

    def permitir(self, clave: str, ahora: float | None = None) -> bool:
        """¿Puede pasar esta petición? Registra la marca si la deja pasar."""
        if self.limite <= 0:            # 0 o menos = sin límite
            return True

        ahora = time.monotonic() if ahora is None else ahora
        marcas = self._marcas[clave]

        # Fuera las que ya salieron de la ventana.
        corte = ahora - self.ventana_s
        while marcas and marcas[0] <= corte:
            marcas.popleft()

        if len(marcas) >= self.limite:
            return False

        marcas.append(ahora)
        return True

    def olvidar_inactivos(self, ahora: float | None = None) -> int:
        """Tira las claves sin marcas vivas y devuelve cuántas quitó.

        ⚠️ Sin esto, el diccionario crece con cada cliente que pasa por aquí y
           no se vacía nunca: una fuga de memoria lenta que solo se manifiesta
           tras semanas de uptime, que es cuando peor viene.
        """
        ahora = time.monotonic() if ahora is None else ahora
        corte = ahora - self.ventana_s
        muertas = [c for c, m in self._marcas.items() if not m or m[-1] <= corte]
        for clave in muertas:
            del self._marcas[clave]
        return len(muertas)


def identificar(request) -> str:
    """A quién se le cuentan las peticiones.

    La credencial primero: es la identidad de verdad y no cambia si el cliente
    salta de red. Sin auth, la IP es lo único que hay.

    ⚠️ Detrás de un proxy, `request.client.host` es la IP del PROXY: todos los
       usuarios comparten cubo y se limitan entre sí. Ahí hay que leer
       `X-Forwarded-For` — pero solo si confías en quien la pone, porque es una
       cabecera que el cliente puede falsificar para saltarse el límite. Por eso
       no se lee aquí: hacerlo bien depende de tu despliegue, y hacerlo mal es
       peor que no hacerlo.
    """
    clave = request.headers.get("X-API-Key")
    if clave:
        # No se guarda la clave en claro como identificador: aparecería en
        # cualquier volcado de estado. Los últimos caracteres bastan para
        # distinguir clientes.
        return f"key:…{clave[-6:]}"
    return f"ip:{request.client.host if request.client else 'desconocida'}"


def crear_limitador() -> LimitadorVentana:
    """El limitador configurado desde el .env."""
    return LimitadorVentana(limite=settings.rate_limit_peticiones,
                            ventana_s=settings.rate_limit_ventana_s)


def revisar(limitador: LimitadorVentana, request) -> None:
    """Aplica el límite o lanza un 429. Lo llama el middleware."""
    quien = identificar(request)
    if limitador.permitir(quien):
        return

    log.warning("límite de peticiones excedido", extra={"cliente": quien})
    raise HTTPException(
        status_code=429,
        detail="Demasiadas peticiones. Espera un momento.",
        # Retry-After es parte del contrato del 429: un cliente educado lo lee
        # y espera. Sin ella, reintentará de inmediato y empeorará el problema.
        headers={"Retry-After": str(int(settings.rate_limit_ventana_s))},
    )
