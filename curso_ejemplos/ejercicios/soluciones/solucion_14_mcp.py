"""
SOLUCIÓN · Ejercicio 14 — Una tercera tool en el servidor MCP
==========================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Añadir la tool `sugerir_accion` al servidor FastMCP del TEMA 14 y consumirla
  desde el cliente ENCADENADA con `evaluar_severidad`. Como el ejemplo original,
  este archivo es a la vez SERVIDOR y CLIENTE, y corre 100% OFFLINE: el
  protocolo MCP viaja de verdad por stdio, pero no interviene ningún LLM.

LÓGICA:
  - Rol servidor (se activa con:  ... solucion_14_mcp.py servidor):
      registra TRES tools con @mcp.tool(); la nueva es `sugerir_accion`.
  - Rol cliente (lo corres tú, sin argumentos):
      descubre las tools por el protocolo (sin leer el código del servidor) y
      encadena evaluar_severidad(porcentaje) -> sugerir_accion(severidad).

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_14_mcp.py
"""

import sys        # el argumento ("servidor" o nada) y la ruta de este archivo
import asyncio     # el cliente MCP es asíncrono: necesita un bucle de eventos


# ============ 1) ROL SERVIDOR: ahora con TRES tools ============
def correr_servidor():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("gobierno_datos")

    @mcp.tool()
    def buscar_regla(nombre: str) -> str:
        """Devuelve la definición de una regla de calidad de datos."""
        reglas = {
            "completitud": "no deben faltar valores obligatorios",
            "unicidad": "no debe haber registros duplicados",
            "consistencia": "el mismo dato debe coincidir entre sistemas",
        }
        return reglas.get(nombre.lower(), "regla no encontrada")

    @mcp.tool()
    def evaluar_severidad(porcentaje_error: float) -> str:
        """Clasifica la severidad de un hallazgo según su % de registros afectados."""
        if porcentaje_error >= 10:
            return "alta"
        return "baja" if porcentaje_error < 5 else "media"

    # ⭐ LA TOOL NUEVA. La segunda línea del docstring es su contrato: le dice a
    #    quien la consuma (un agente, o tú) CUÁNDO usarla. Sin ella, el modelo no
    #    sabría que va después de evaluar_severidad.
    @mcp.tool()
    def sugerir_accion(severidad: str) -> str:
        """Devuelve la acción que exige la normativa para una severidad dada.
        Úsala DESPUÉS de evaluar_severidad, para saber qué hacer con el hallazgo."""
        acciones = {
            "alta": "escalar al comité de riesgos en 24 horas",
            "media": "abrir un plan de corrección a 15 días",
            "baja": "registrar y revisar en la próxima auditoría",
        }
        return acciones.get(severidad.lower(), "severidad no reconocida")

    mcp.run(transport="stdio")


# ============ 2) ROL CLIENTE: descubrir y ENCADENAR ============
def _texto(resultado) -> str:
    """MCP devuelve 'bloques de contenido'; sacamos el texto plano.

    Es el mismo helper que el ejemplo define dentro de correr_cliente().
    """
    if isinstance(resultado, list):
        return " ".join(b.get("text", "") for b in resultado if isinstance(b, dict))
    return str(resultado)


async def correr_cliente():
    from langchain_mcp_adapters.client import MultiServerMCPClient

    # Lanza ESTE MISMO archivo como servidor, en un subproceso aparte.
    client = MultiServerMCPClient({
        "gobierno_datos": {
            "command": sys.executable,
            "args": [__file__, "servidor"],   # -> activa el rol servidor
            "transport": "stdio",
        },
    })

    # ---- Descubrimiento: el cliente NO leyó el código del servidor ----
    herramientas = await client.get_tools()
    print("=== Tools descubiertas en el servidor MCP ===")
    for t in herramientas:
        print(f"  · {t.name}: {t.description}")

    mapa = {t.name: t for t in herramientas}

    # ---- Encadenar: la salida de una tool alimenta a la siguiente ----
    # Esto es EXACTAMENTE lo que haría un agente con estas tres tools; aquí lo
    # hacemos a mano para verlo sin gastar cuota.
    print("\n=== Encadenando evaluar_severidad -> sugerir_accion ===")
    for porcentaje in (12.0, 7.0, 1.0):
        severidad = _texto(await mapa["evaluar_severidad"].ainvoke(
            {"porcentaje_error": porcentaje}))
        accion = _texto(await mapa["sugerir_accion"].ainvoke({"severidad": severidad}))
        print(f"  evaluar_severidad({porcentaje}) -> {severidad}")
        print(f"  sugerir_accion('{severidad}')  -> {accion}\n")

    print("💡 Solo tocamos el SERVIDOR: el cliente descubrió la tool nueva sin")
    print("   cambiar una línea. Ese es todo el sentido de MCP: publicas una")
    print("   herramienta una vez y cualquier cliente del protocolo la consume.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "servidor":
        correr_servidor()                # rol servidor (lo lanza el cliente)
    else:
        asyncio.run(correr_cliente())    # rol cliente (lo corres tú)


if __name__ == "__main__":
    try:
        main()
    except ImportError as error:
        print(f"❌ Falta una librería: {error}")
        print("   Instala con: uv pip install -r curso_ejemplos/requirements.txt")
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
