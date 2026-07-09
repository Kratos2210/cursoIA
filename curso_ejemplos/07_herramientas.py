"""
TEMA 07 · Herramientas (darle manos al modelo)
==========================================================
FINALIDAD:
  Convertir una función normal de Python en una "herramienta" que la
  IA puede usar por sí misma (calcular, consultar, etc.).

LÓGICA (paso a paso):
  1) Decoramos una función con @tool.
  2) Su docstring y sus parámetros le dicen al modelo qué hace y cómo usarla.
  3) La probamos como función normal y vemos lo que "lee" el modelo.

Requisitos: pip install -r curso_ejemplos/requirements.txt   (este NO llama a la API)
Ejecuta:    uv run python curso_ejemplos/07_herramientas.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from dotenv import load_dotenv          # cargar .env (por consistencia; aquí no llamamos a la API)
from langchain_core.tools import tool   # 'tool': decorador que convierte una función en herramienta


# ---- La herramienta se define fuera de main() -----------
# ⭐ El docstring NO es adorno: el modelo lo LEE para decidir cuándo usarla,
#    y usa los nombres/tipos de los parámetros para pasar los datos.
@tool
def calculadora_descuentos(precio: float, porcentaje: float) -> float:
    """Calcula el precio final tras aplicar un descuento.
    Úsala cuando el usuario pida calcular precios con descuento."""
    return precio - (precio * porcentaje / 100)


def main():
    load_dotenv()

    # ---- 1) Probar la tool como función normal ----------
    # (útil para verificar tu lógica antes de dársela a la IA)
    print("=== Probar la tool directamente ===")
    print("Precio final:", calculadora_descuentos.invoke({"precio": 3500, "porcentaje": 18}))

    # ---- 2) Ver lo que la IA "lee" de tu tool -----------
    print("\n=== Lo que ve el modelo ===")
    print("nombre      :", calculadora_descuentos.name)
    print("descripción :", calculadora_descuentos.description)
    print("parámetros  :", calculadora_descuentos.args)

    # En el TEMA 08 le entregamos esta tool al modelo para que la use SOLO.


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"❌ Error inesperado: {error}")
