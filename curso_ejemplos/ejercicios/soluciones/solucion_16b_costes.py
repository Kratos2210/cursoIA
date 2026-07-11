"""
SOLUCIÓN · Ejercicio 16b — Predice la factura antes de calcularla
==========================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Predecir el coste de dos escenarios con tokens asimétricos y comprobarlo con
  la MISMA lógica del ejemplo (estimar_costo), sin reescribir la fórmula. La
  lección: "la salida es 6× más cara" no basta para presupuestar; hay que
  multiplicar precio × CANTIDAD en cada dirección.

  100% offline: la aritmética del coste no llama a ningún LLM.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_16b_costes.py
"""

import importlib.util
from pathlib import Path

# La carpeta del curso está dos niveles arriba de esta solución.
CARPETA_CURSO = Path(__file__).resolve().parents[2]


def _cargar_ejemplo_16b():
    """Importa 16b_observabilidad_langsmith.py (empieza por dígito -> importlib).

    Reutilizamos su estimar_costo y su tabla PRECIOS: si mañana cambia un precio,
    este ejercicio se actualiza solo. Reescribir la fórmula aquí sería crear una
    segunda verdad que acabaría contradiciendo a la del ejemplo.
    """
    import sys
    if str(CARPETA_CURSO) not in sys.path:
        sys.path.insert(0, str(CARPETA_CURSO))   # para que su `from util import …` funcione
    ruta = CARPETA_CURSO / "16b_observabilidad_langsmith.py"
    spec = importlib.util.spec_from_file_location("ej_16b", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


MODELO = "gemini-3.1-flash-lite"   # entrada $0.25/1M · salida $1.50/1M (6× la entrada)

# Los dos escenarios del enunciado: mismo modelo, uso muy distinto.
ESCENARIOS = {
    "A (RAG, contexto enorme)": {"entrada": 50_000, "salida": 200},
    "B (redactor, respuesta larga)": {"entrada": 500, "salida": 3_000},
}


def tokens_salida_para_igualar(m16b, coste_objetivo: float, entrada: int) -> int:
    """Cuántos tokens de salida necesita un escenario (con 'entrada' fija) para
    costar 'coste_objetivo'. Despejamos usando la propia estimar_costo del ejemplo.

    coste = (entrada·p_in + salida·p_out) / 1e6   ->   salida = (coste·1e6 - entrada·p_in) / p_out
    """
    precio = m16b.PRECIOS[MODELO]
    micro = coste_objetivo * 1_000_000
    salida = (micro - entrada * precio["entrada"]) / precio["salida"]
    return round(salida)


def main():
    m16b = _cargar_ejemplo_16b()

    costes = {
        nombre: m16b.estimar_costo(tokens, MODELO)
        for nombre, tokens in ESCENARIOS.items()
    }

    print(f"=== Coste por llamada con {MODELO} ===")
    for nombre, tokens in ESCENARIOS.items():
        print(f"  {nombre:32s} ({tokens['entrada']}+{tokens['salida']}) "
              f"-> {m16b.formatear_costo(costes[nombre])}")

    caro = max(costes, key=costes.get)
    barato = min(costes, key=costes.get)
    veces = costes[caro] / costes[barato]
    print(f"\n  Gana (más caro): {caro[0]}, por ~{veces:.1f}x")

    # El punto de equilibrio: cuánto tendría que escribir B para alcanzar a A.
    entrada_b = ESCENARIOS["B (redactor, respuesta larga)"]["entrada"]
    salida_equilibrio = tokens_salida_para_igualar(m16b, costes["A (RAG, contexto enorme)"], entrada_b)
    print(f"  Punto de equilibrio: B igualaría a A con ~{salida_equilibrio} tokens de salida")

    print("\n💡 La intuición 'la salida es 6× más cara' apunta a B. Pero A tiene 100×")
    print("   más tokens de ENTRADA, y 100× barato le gana a 6× caro. La regla real:")
    print("   presupuesta multiplicando precio × CANTIDAD, no por el precio a secas.")


# ============ TEST QUE PEDÍA EL EJERCICIO ============
# Offline, usando la lógica del ejemplo (estilo TestTema16bObservabilidad):
#
#   def test_el_rag_con_contexto_gigante_gana_al_redactor(m16b):
#       a = m16b.estimar_costo({"entrada": 50_000, "salida": 200}, "gemini-3.1-flash-lite")
#       b = m16b.estimar_costo({"entrada": 500, "salida": 3_000}, "gemini-3.1-flash-lite")
#       assert a > b                       # la intuición "la salida manda" falla aquí
#       assert a == pytest.approx(0.0128)


if __name__ == "__main__":
    main()
