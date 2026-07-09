"""
TEMA 05 · Salida estructurada (del texto al dato)
==========================================================
FINALIDAD:
  Forzar al modelo a devolver DATOS ordenados (no un párrafo),
  usando moldes Pydantic. Ideal para extraer y clasificar.

LÓGICA (paso a paso):
  1) Definimos un molde (clase Pydantic) con los campos que queremos.
  2) llm.with_structured_output(molde) obliga al modelo a rellenarlo.
  3) El resultado es un objeto Python con atributos (no texto suelto).

Requisitos: pip install -r curso_ejemplos/requirements.txt  +  .env con GOOGLE_API_KEY
Ejecuta:    uv run python curso_ejemplos/05_salida_estructurada.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
import os                                   # variables de entorno
from dotenv import load_dotenv              # cargar .env
from typing import Optional, List           # 'typing': tipos (opcional, lista) para los moldes
from pydantic import BaseModel, Field       # 'pydantic': fábrica de moldes de datos con validación
from langchain_google_genai import ChatGoogleGenerativeAI   # modelo Gemini


# ---- Los moldes se definen fuera de main() (son "plantillas") ----
class Persona(BaseModel):
    """Una persona mencionada en el texto."""
    nombre: str = Field(description="Nombre de la persona")
    # Optional[int] = puede ser un número o None (si no se menciona).
    edad: Optional[int] = Field(default=None, description="Edad si se menciona")

class Extraccion(BaseModel):
    personas: List[Persona]  # una LISTA: busca a TODAS, no solo una

class Etiqueta(BaseModel):
    sentimiento: str = Field(description="positivo | negativo | neutro")
    idioma: str = Field(description="idioma detectado del texto")


def main():
    # ---- 1) Preparar llave y modelo ---------------------
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("❌ Falta GOOGLE_API_KEY. Copia .env.example a .env y pon tu llave.")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    # ---- 2) EXTRAER: el modelo llena el molde Extraccion -
    # with_structured_output = "ponle anteojeras": deja de conversar y llena el formulario.
    extractor = llm.with_structured_output(Extraccion)
    print("=== Extracción de personas ===")
    r = extractor.invoke("Ana tiene 30 años y su hijo Luis, 5. También vino Marta.")
    for p in r.personas:                     # r es un objeto Python; iteramos sus atributos
        print(f"- {p.nombre} (edad: {p.edad})")

    # ---- 3) CLASIFICAR (tagging): mismo patrón ----------
    clasificador = llm.with_structured_output(Etiqueta)
    print("\n=== Clasificación (tagging) ===")
    etiqueta = clasificador.invoke("I love this new system, it's super fast!")
    print("sentimiento:", etiqueta.sentimiento, "| idioma:", etiqueta.idioma)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
            print("⏳ Cuota de Gemini agotada (429). Espera unos minutos o usa 'gemini-2.5-flash'.")
        else:
            print(f"❌ Error inesperado: {error}")
