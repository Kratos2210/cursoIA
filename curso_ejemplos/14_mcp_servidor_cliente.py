"""
TEMA 14 · MCP: tu primer servidor + cliente (en un solo archivo)
==========================================================
FINALIDAD:
  Ver el Model Context Protocol funcionando de verdad: este archivo es
  a la vez un SERVIDOR MCP (expone herramientas de forma estándar) y un
  CLIENTE que se conecta a él, descubre sus tools y las invoca.

  ⭐ Este ejemplo es 100% OFFLINE: no usa ningún LLM ni gasta cuota.
     El protocolo MCP corre completo (dos procesos hablando por stdio);
     solo omitimos al modelo — aquí TÚ haces de agente e invocas las tools.

LÓGICA (paso a paso):
  1) ROL SERVIDOR (se ejecuta con:  ... 14_mcp_servidor_cliente.py servidor)
     - FastMCP registra dos tools con @mcp.tool() (igual que @tool del TEMA 07).
     - mcp.run(transport="stdio"): atiende por entrada/salida estándar.
  2) ROL CLIENTE (se ejecuta SIN argumentos — es lo que corres tú)
     - MultiServerMCPClient lanza este mismo archivo como servidor (subproceso).
     - get_tools(): descubre qué herramientas expone (¡sin leer su código!).
     - Invocamos cada tool y mostramos el resultado.
  3) En el TEMA 14 del curso ves el paso final: darle estas mismas tools
     a un agente con create_agent para que las use solo.

Requisitos: pip install -r curso_ejemplos/requirements.txt   (añade mcp + adapters)
Ejecuta:    uv run python curso_ejemplos/14_mcp_servidor_cliente.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import sys        # leer el argumento ("servidor" o nada) y la ruta del propio archivo
import asyncio    # el cliente MCP es asíncrono: necesitamos un bucle de eventos


# ============ 1) ROL SERVIDOR: un adaptador MCP de Gobierno de Datos ============
def correr_servidor():
    # El import va aquí dentro para que el rol cliente no lo necesite cargar.
    from mcp.server.fastmcp import FastMCP   # FastMCP: crear servidores MCP con decoradores

    mcp = FastMCP("gobierno_datos")          # el nombre con el que se presenta

    # ⭐ Igual que en el TEMA 07: el docstring y los tipos son el contrato
    #    que leerá quien consuma la tool (un agente o, hoy, tú).
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

    # Atiende por stdio: el cliente le escribe a su entrada y lee su salida.
    mcp.run(transport="stdio")


# ============ 2) ROL CLIENTE: descubrir e invocar las tools ============
async def correr_cliente():
    from langchain_mcp_adapters.client import MultiServerMCPClient  # cliente MCP -> tools de LangChain

    # Lanza ESTE MISMO archivo como servidor, en un subproceso aparte.
    # sys.executable = el mismo Python con el que corres esto (el de tu venv).
    client = MultiServerMCPClient({
        "gobierno_datos": {
            "command": sys.executable,
            "args": [__file__, "servidor"],   # -> activa el rol servidor
            "transport": "stdio",
        },
    })

    # ---- Descubrimiento: ¿qué ofrece el servidor? --------
    # El cliente NO leyó el código del servidor: le preguntó por el protocolo.
    herramientas = await client.get_tools()
    print("=== Tools descubiertas en el servidor MCP ===")
    for t in herramientas:
        print(f"  · {t.name}: {t.description}")

    # ---- Invocación: usamos las tools como si fueran locales ----
    # (Con un LLM, este paso lo haría el agente solo: TEMA 14 del curso.)
    mapa = {t.name: t for t in herramientas}

    def texto(resultado):
        """MCP devuelve 'bloques de contenido'; sacamos el texto plano."""
        if isinstance(resultado, list):
            return " ".join(b.get("text", "") for b in resultado if isinstance(b, dict))
        return str(resultado)

    print("\n=== Invocando las tools (tú haces de agente) ===")
    regla = await mapa["buscar_regla"].ainvoke({"nombre": "completitud"})
    print("  buscar_regla('completitud')  ->", texto(regla))

    severidad = await mapa["evaluar_severidad"].ainvoke({"porcentaje_error": 12.0})
    print("  evaluar_severidad(12.0)      ->", texto(severidad))

    print("\n💡 Paso final (con tu llave y cuota): dale estas tools a un agente:")
    print("   agente = create_agent(llm, tools=herramientas)")
    print("   El agente decidirá solo cuándo llamar al servidor MCP.")


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
