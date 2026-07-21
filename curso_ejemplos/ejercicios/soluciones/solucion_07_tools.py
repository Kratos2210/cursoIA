"""
SOLUCIÓN · Ejercicio 07 — Dos tools nuevas
==========================================================
⚠️ No leas esto hasta haberlo intentado.

Partes 1 y 3 son OFFLINE (no gastan cuota). La Parte 2 necesita la llave del
proveedor que elijas (GOOGLE_API_KEY, o GROQ_API_KEY con LLM_PROVIDER=groq).

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_07_tools.py
"""

import os
import sys

# `util.py` vive en curso_ejemplos/, dos carpetas más arriba. Estos scripts se
# ejecutan desde soluciones/, así que Python no lo encontraría solo.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# `crear_llm()` construye el modelo del proveedor que diga el .env. Con
# LLM_PROVIDER=groq usas el modelo por defecto de Groq y dejas de gastar la
# (cortísima) cuota gratuita de Gemini.
from util import crear_llm, requiere_llm_key

from dotenv import load_dotenv
from langchain_core.tools import tool


# ============ PARTE 1 · Las dos tools nuevas (offline) ============
# Un RUC peruano válido: 11 dígitos, empezando por 10, 15, 17 o 20.
PREFIJOS_VALIDOS = ("10", "15", "17", "20")
TASA_IGV = 0.18   # 18% en Perú


@tool
def validar_ruc(ruc: str) -> str:
    """Valida si un RUC peruano tiene el formato correcto (11 dígitos).
    Úsala cuando el usuario mencione un RUC o pida verificar un contribuyente."""
    # ⭐ Devolvemos TEXTO explicativo, no un bool: el modelo va a LEER esta
    #    respuesta para redactar la suya. Un 'False' no le dice nada.
    if not ruc.isdigit():
        return "inválido: el RUC solo puede contener dígitos"
    if len(ruc) != 11:
        return f"inválido: tiene {len(ruc)} dígitos y debe tener 11 dígitos"
    if not ruc.startswith(PREFIJOS_VALIDOS):
        return f"inválido: debe empezar por {', '.join(PREFIJOS_VALIDOS)}"
    return "válido"


@tool
def calcular_igv(monto: float) -> float:
    """Calcula el monto final con IGV incluido (18% en Perú).
    Úsala cuando el usuario pida el precio con impuestos o con IGV."""
    return monto * (1 + TASA_IGV)


@tool
def calculadora_descuentos(precio: float, porcentaje: float) -> float:
    """Calcula el precio final tras aplicar un descuento.
    Úsala cuando el usuario pida calcular precios con descuento."""
    return precio - (precio * porcentaje / 100)


# ============ Los asserts del criterio de aceptación ============
def verificar_offline():
    """Los criterios del ejercicio, comprobados sin gastar un token."""
    assert validar_ruc.invoke({"ruc": "20123456789"}).startswith("válido")
    assert "11 dígitos" in validar_ruc.invoke({"ruc": "201234"})
    assert "dígitos" in validar_ruc.invoke({"ruc": "2012345678X"})
    assert "empezar por" in validar_ruc.invoke({"ruc": "99123456789"})
    assert calcular_igv.invoke({"monto": 100.0}) == 118.0
    assert set(validar_ruc.args) == {"ruc"}

    # Lo que el modelo LEE de cada tool (su verdadera interfaz):
    print("=== Lo que ve el modelo ===")
    for herramienta in (validar_ruc, calcular_igv, calculadora_descuentos):
        print(f"  · {herramienta.name}{tuple(herramienta.args)}")
        print(f"    {herramienta.description.splitlines()[0]}")

    # El cálculo encadenado del ejercicio:
    con_descuento = calculadora_descuentos.invoke({"precio": 3500, "porcentaje": 18})
    con_igv = calcular_igv.invoke({"monto": con_descuento})
    print(f"\n  3500 - 18% = {con_descuento}   ->  con IGV = {con_igv}")
    assert con_descuento == 2870.0
    assert round(con_igv, 2) == 3386.60
    print("\n✅ Parte 1 y 3: todos los criterios se cumplen (sin gastar cuota).")


# ============ PARTE 2 · Que el modelo las combine (gasta cuota) ============
def parte_2():
    """El ciclo completo de 08_routing.py, pero con TRES tools."""
    from langchain_core.messages import HumanMessage, ToolMessage

    # El proveedor sale del .env. `bind_tools` funciona igual con Gemini que con
    # cualquier modelo de Groq: el tool calling es parte del protocolo, no del modelo.
    llm = crear_llm(temperature=0)
    herramientas = [calculadora_descuentos, validar_ruc, calcular_igv]
    llm_tools = llm.bind_tools(herramientas)
    mapa = {t.name: t for t in herramientas}

    pregunta = ("El RUC 20123456789 nos compró por 3500 soles con 18% de descuento. "
                "¿Es válido el RUC y cuánto pagará con IGV?")
    mensajes = [HumanMessage(content=pregunta)]

    print(f"\n🙋 {pregunta}\n")

    # ⭐ Un solo turno puede no bastar: el modelo necesita el precio con
    #    descuento ANTES de poder pedir el IGV de ese número. Por eso el
    #    bucle: se repite mientras siga pidiendo herramientas.
    for vuelta in range(1, 6):
        ai = llm_tools.invoke(mensajes)
        mensajes.append(ai)

        if not ai.tool_calls:
            print(f"\n🤖 {ai.content}")
            return

        print(f"  --- vuelta {vuelta}: el modelo pide {len(ai.tool_calls)} tool(s) ---")
        for llamada in ai.tool_calls:
            resultado = mapa[llamada["name"]].invoke(llamada["args"])
            print(f"    {llamada['name']}({llamada['args']}) -> {resultado}")
            mensajes.append(ToolMessage(content=str(resultado), tool_call_id=llamada["id"]))

    print("⚠️ El modelo no terminó en 5 vueltas. En producción, esto es un límite "
          "de recursión y hay que cortarlo (create_react_agent lo hace solo).")


def main():
    verificar_offline()

    load_dotenv()
    # requiere_llm_key() mira la llave del proveedor ACTIVO, no siempre la de
    # Google: con LLM_PROVIDER=groq comprueba GROQ_API_KEY, y con ollama, nada.
    if requiere_llm_key():
        print(f"\nℹ️  {requiere_llm_key()}")
        print("   Me salto la Parte 2 (la que llama al modelo).")
        return

    print("\n" + "=" * 60)
    print("PARTE 2 · El modelo elige y encadena las tres tools")
    print("=" * 60)
    parte_2()

    print("""
💡 PARTE 3 · ¿Qué pasa si borras el docstring de validar_ruc?

   LangChain usa entonces solo el NOMBRE de la función como descripción.
   'validar_ruc' es tan claro que el modelo probablemente acierte igual.

   Prueba de verdad: renómbrala a `def procesar(x: str)` y bórrale el docstring.
   Ahí verás el fallo real — no la llama nunca, o la llama con basura.

   LECCIÓN: el par (nombre, docstring) ES la interfaz de tu tool. El cuerpo de
   la función es un detalle de implementación que el modelo jamás llega a ver.
""")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"❌ Un criterio de aceptación no se cumple: {error}")
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). La Parte 1 ya se verificó offline.")
        else:
            print(f"❌ Error inesperado: {error}")
