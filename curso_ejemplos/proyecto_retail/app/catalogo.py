"""
catalogo.py · De dónde salen los productos, y qué pasa cuando no salen
=======================================================================
FINALIDAD:
  Cablear de una vez `CATALOGO_FUENTE=live`. Hasta ahora el ajuste existía en el
  .env pero el lifespan llamaba SIEMPRE a `cargar_catalogo_demo()`: la app no
  podía consumir el catálogo real sin tocar código, y el script
  `data/fetch_catalogo.py` era manual y de un solo uso.

  Y, ya que el catálogo pasa a venir de fuera, refrescarlo: un precio cambia y
  el asistente tiene que enterarse sin reiniciar el servicio.

LÓGICA — dos fuentes y un refresco:
    CATALOGO_FUENTE=demo   data/catalogo_demo.json. Cero red, cero sorpresas.
                           Es lo que hace ejecutable el curso.
    CATALOGO_FUENTE=live   El products.json real, normalizado por el MISMO ETL.

⭐ LA ASIMETRÍA QUE HAY QUE ENTENDER — y es la decisión importante de este módulo:

    Al ARRANCAR con `live`, si la descarga falla → el servicio NO arranca.
    Al REFRESCAR, si la descarga falla         → se conserva el catálogo bueno.

  Parece incoherente y no lo es. Caer al catálogo DEMO cuando el real no está
  disponible sería servir los precios de doce productos de mentira como si
  fueran los de la tienda. El proyecto entero existe para que el precio nunca
  se lo invente el modelo (ver guardrails/output_guard.py y evals/ci_gate.py);
  servirlo desde un fichero de demostración sería inventarlo por otra vía, y
  además en silencio. Mejor no arrancar: un servicio caído se ve, un precio
  equivocado no.

  En el refresco es al revés: ya hay un catálogo bueno en memoria, ligeramente
  viejo. Servir datos de hace diez minutos es un problema mucho menor que
  quedarse sin servicio porque la tienda tuvo un hipo de red.
"""
from __future__ import annotations

import asyncio

from proyecto_retail.app.config import settings
from proyecto_retail.observability import logs

log = logs.obtener_logger(__name__)


def bajar_catalogo(url: str | None = None) -> list[dict]:
    """Baja el catálogo real y lo normaliza con el ETL del proyecto.

    Aislado en su propia función para poder sustituirlo en los tests: nada de
    red en la suite. El ETL es el MISMO que usa el modo demo, así que un cambio
    de normalización afecta a los dos por igual y no se pueden desincronizar.
    """
    from proyecto_retail.app.etl import cargar_catalogo
    from proyecto_retail.data.fetch_catalogo import bajar_crudo

    return cargar_catalogo(bajar_crudo(url or settings.catalogo_url))


def cargar_inicial(bajar=bajar_catalogo) -> list[dict]:
    """El catálogo con el que arranca el servicio.

    Con `live`, un fallo aquí es FATAL a propósito (ver la asimetría del
    encabezado): preferimos no arrancar a arrancar sirviendo precios de demo.
    """
    if settings.catalogo_fuente != "live":
        from proyecto_retail.app.etl import cargar_catalogo_demo
        catalogo = cargar_catalogo_demo()
        log.info("catálogo demo cargado", extra={"productos": len(catalogo)})
        return catalogo

    catalogo = bajar(settings.catalogo_url)
    if not catalogo:
        # Una lista vacía es tan peligrosa como un error: el asistente
        # respondería "no tengo nada" a todo, y eso parece un problema de
        # producto y no de infraestructura.
        raise RuntimeError(
            f"El catálogo real ({settings.catalogo_url}) vino vacío. El servicio "
            f"no arranca: servir el catálogo demo como si fuera el real daría "
            f"precios falsos a clientes de verdad.")

    log.info("catálogo real cargado", extra={"productos": len(catalogo),
                                             "url": settings.catalogo_url})
    return catalogo


async def refrescar_periodicamente(estado: dict, intervalo_s: float,
                                   bajar=bajar_catalogo,
                                   dormir=asyncio.sleep) -> None:
    """Vuelve a bajar el catálogo cada `intervalo_s`. Corre como tarea de fondo.

    ⚠️ Un fallo aquí NO tumba nada ni vacía el catálogo: se registra y se
       reintenta en el siguiente ciclo, sirviendo mientras tanto el último
       bueno. `dormir` e `bajar` se inyectan para que el test recorra varios
       ciclos en microsegundos en vez de esperar horas.
    """
    while True:
        await dormir(intervalo_s)
        try:
            nuevo = bajar(settings.catalogo_url)
        except Exception:
            log.exception("no se pudo refrescar el catálogo; sigue el anterior",
                          extra={"productos_vigentes": len(estado["catalogo"])})
            continue

        if not nuevo:
            # Mismo criterio que arriba, sin ser fatal: un catálogo vacío
            # sustituyendo a uno bueno dejaría al asistente sin nada que decir.
            log.warning("el catálogo refrescado vino vacío; se conserva el anterior",
                        extra={"productos_vigentes": len(estado["catalogo"])})
            continue

        anteriores = len(estado["catalogo"])
        estado["catalogo"] = nuevo
        log.info("catálogo refrescado", extra={"antes": anteriores,
                                               "ahora": len(nuevo)})
