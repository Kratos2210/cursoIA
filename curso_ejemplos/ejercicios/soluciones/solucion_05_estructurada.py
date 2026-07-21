"""
SOLUCIÓN · Ejercicio 05 — Un cuarto molde Pydantic
==========================================================
⚠️ No leas esto hasta haberlo intentado.

El molde TicketSoporte, sus tests offline, y la extracción real con el modelo.
La parte de tests corre SIN llave; la extracción necesita la llave del
proveedor que elijas (GOOGLE_API_KEY, o GROQ_API_KEY con LLM_PROVIDER=groq).

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_05_estructurada.py
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
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


# ============ EL MOLDE ============
class TicketSoporte(BaseModel):
    """Un ticket de soporte extraído de un correo de cliente."""

    asunto: str = Field(description="Resumen del problema, menos de 10 palabras")

    # ⭐ Literal, no str. with_structured_output traduce este molde a un JSON
    #    Schema, y un Literal se convierte en un 'enum' que RESTRINGE al modelo
    #    a esos tres valores exactos. Con un str a secas, el modelo escribiría
    #    "Alta", "urgente" o "ALTA!!" y tu `if urgencia == "alta"` tomaría la
    #    rama equivocada SIN lanzar ninguna excepción. Ese es el bug más caro
    #    que existe: el que no se nota.
    urgencia: Literal["alta", "media", "baja"] = Field(
        description="alta si el cliente pide solución inmediata o menciona una fecha límite")

    categoria: Literal["facturación", "técnico", "comercial"] = Field(
        description="facturación si hay cobros; técnico si algo no funciona")

    # ⭐ Esto no es un campo cualquiera: es un CONTROL DE GOBIERNO DE DATOS.
    #    Si es True, este texto no puede ir a un log, a un dataset ni a una
    #    traza sin anonimizar antes.
    cliente_menciona_datos_personales: bool = Field(
        description="True si el correo contiene DNI, RUC, teléfono, dirección o similar")

    productos: List[str] = Field(
        default_factory=list,
        description="Nombres de productos o planes mencionados; lista vacía si ninguno")


CORREO = """
Buenas, soy Ana Torres (DNI 45678912). Llevo dos días sin poder entrar al panel
de Analytics y encima me cobraron el plan Pro dos veces este mes. Necesito que
lo arreglen HOY, tengo una auditoría el viernes.
"""


# ============ LOS TESTS OFFLINE (criterio de aceptación nº 4) ============
def verificar_offline():
    """Valida el molde sin llamar al modelo. Cópialos a tests/ si quieres."""

    # Un ticket válido se construye sin problema.
    ticket = TicketSoporte(
        asunto="Sin acceso al panel y doble cobro",
        urgencia="alta",
        categoria="técnico",
        cliente_menciona_datos_personales=True,
        productos=["Analytics", "Pro"],
    )
    assert ticket.urgencia == "alta"

    # Una urgencia inventada se rechaza. ESTE es el test que justifica el Literal.
    try:
        TicketSoporte(asunto="a", urgencia="urgentísima", categoria="técnico",
                      cliente_menciona_datos_personales=False, productos=[])
        raise AssertionError("debería haber rechazado 'urgentísima'")
    except ValidationError:
        pass   # ✅ lo esperado

    # Una categoría inventada, igual.
    try:
        TicketSoporte(asunto="a", urgencia="alta", categoria="legal",
                      cliente_menciona_datos_personales=False, productos=[])
        raise AssertionError("debería haber rechazado la categoría 'legal'")
    except ValidationError:
        pass

    # 'productos' es opcional: por defecto, lista vacía (no None).
    minimo = TicketSoporte(asunto="a", urgencia="baja", categoria="comercial",
                           cliente_menciona_datos_personales=False)
    assert minimo.productos == []

    # Todos los campos llevan description: son las instrucciones que lee el modelo.
    assert all(c.description for c in TicketSoporte.model_fields.values())

    print("✅ Los 5 criterios offline se cumplen (sin gastar cuota).")


# ============ LA EXTRACCIÓN REAL ============
def extraer():
    # Respeta LLM_PROVIDER del .env (google | groq | ollama). Temperatura 0:
    # extraer datos no es una tarea creativa.
    llm = crear_llm(temperature=0)
    extractor = llm.with_structured_output(TicketSoporte)
    ticket = extractor.invoke(f"Extrae un ticket de soporte de este correo:\n{CORREO}")

    print("\n=== Ticket extraído ===")
    print(f"  asunto      : {ticket.asunto}")
    print(f"  urgencia    : {ticket.urgencia}")
    print(f"  categoría   : {ticket.categoria}")
    print(f"  productos   : {ticket.productos}")
    print(f"  datos personales: {ticket.cliente_menciona_datos_personales}")

    # Los criterios de aceptación 1 y 2 del ejercicio:
    assert ticket.urgencia == "alta", "el correo dice 'HOY' y menciona una fecha límite"
    assert ticket.cliente_menciona_datos_personales is True, "el correo trae un DNI"

    if ticket.cliente_menciona_datos_personales:
        print("\n  🔒 ALERTA DE GOBIERNO DE DATOS: este ticket contiene datos personales.")
        print("     Anonimízalo ANTES de que llegue a un log, a un dataset de")
        print("     entrenamiento o a la traza de LangSmith.")


def main():
    verificar_offline()

    load_dotenv()
    # La llave que hace falta depende del proveedor activo (google | groq | ollama).
    if requiere_llm_key():
        print(f"\nℹ️  {requiere_llm_key()}")
        print("   Me salto la extracción real.")
        return
    extraer()

    print("""
💡 CRITERIO 3 · ¿Qué se pierde al cambiar Literal por str?

   El molde sigue funcionando. El ejemplo sigue corriendo. Y ahí está el peligro.

   Con Literal, el JSON Schema que recibe el modelo lleva un 'enum': el modelo
   queda restringido a alta|media|baja. Con str, el esquema solo dice "texto".

   El modelo escribirá "Alta" un día y "urgente" otro. Tu código hace
   `if urgencia == "alta"` y toma la rama equivocada — sin excepción, sin log,
   sin nada. El sistema no falla: MIENTE. Y lo descubres semanas después.

   La misma idea, aplicada en el proyecto final: audit.HallazgoCalidad valida
   la severidad con un field_validator y rechaza lo que no sea alta|media|baja,
   para que nunca se escriba basura en el log de auditoría.
""")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"❌ Un criterio de aceptación no se cumple: {error}")
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). La parte offline ya se verificó.")
        else:
            print(f"❌ Error inesperado: {error}")
