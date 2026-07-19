"""
SOLUCIÓN · Ejercicio 29 — Retail: el dato sucio, el filtro tonto y el eval
===========================================================================
⚠️ No leas esto hasta haberlo intentado.

FINALIDAD:
  Verificar con asserts las cuatro fronteras del caso Sifrah:
    · P1: en_promo exige compare_at > price ESTRICTO (igualdad no es promo).
    · P2: "cadena" sí (sinónimo), "dorada" no (substring): color = None.
    · P3: honesto 1.0 vs descuidado 0.75 — lo tumba respeta_precio.
    · P4: el caso imposible aprueba al honesto (no responder es válido)
          y hunde más al descuidado.

  100% offline: funciones puras sobre el catálogo demo. No gasta cuota.

Ejecuta:  uv run python curso_ejemplos/ejercicios/soluciones/solucion_29_retail.py
"""

import importlib.util
import os

# ---- Cargamos el ejemplo 29 (su nombre empieza por número: no se puede importar) ----
CARPETA_CURSO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cargar_tema29():
    ruta = os.path.join(CARPETA_CURSO, "29_caso_retail.py")
    spec = importlib.util.spec_from_file_location("tema29", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


t29 = cargar_tema29()

CASOS = [{"peticion": p} for p in [
    "quiero aretes dorados por menos de 25 soles",
    "una cartera para regalo, hasta S/80",
    "algo para el cabello, máximo 12 soles",
    "un collar de zircón por menos de 10 soles",
]]


# ==================================================================
# PARTE 1 · El ETL y la promo que no es promo
# ==================================================================
def parte_1():
    print("\n[P1] normalizar_producto con compare_at_price == price")
    crudo = {"title": "Aretes Luna", "tags": ["dorado"],
             "variants": [{"sku": "AR-9", "price": "59.90",
                           "compare_at_price": "59.90", "available": True}]}
    p = t29.normalizar_producto(crudo)
    print(f"     → {p}")

    assert p["precio"] == 59.9                # float("59.90"): el string se
    assert p["categoria"] == "aretes"         # convierte UNA vez, en el ETL
    # La regla es `float(antes) > precio` ESTRICTO: igualdad no es promo. Un
    # catálogo que rellena compare_at_price con el mismo precio no infla promos.
    assert p["en_promo"] is False
    print("     → en_promo=False: la igualdad no es rebaja (el `>` estricto salva).")


# ==================================================================
# PARTE 2 · "cadena" sí, "dorada" no
# ==================================================================
def parte_2():
    print("\n[P2] extraer_filtros('una cadena dorada, tope de S/ 40')")
    f = t29.extraer_filtros("una cadena dorada, tope de S/ 40")
    print(f"     → {f}")

    assert f["presupuesto"] == 40.0           # 'tope de' + 'S/' → regex ✓
    assert f["categoria"] == "collares"       # 'cadena' es sinónimo de petición
    # La sorpresa: _COLORES matchea por substring y 'dorado' NO está dentro de
    # 'dorada'. El femenino rompe el filtro — el regex no sabe gramática.
    assert f["color"] is None
    print("     → color=None: 'dorado' no es substring de 'dorada'. En producción")
    print("       esto lo reemplaza el m05: with_structured_output(FiltrosCompra).")


# ==================================================================
# PARTE 3 · Honesto vs descuidado, con la misma métrica
# ==================================================================
def parte_3():
    print("\n[P3] evaluar_asistente sobre los 4 casos")
    catalogo = t29.cargar_catalogo()
    honesto = t29.evaluar_asistente(CASOS, t29.asistente_honesto, catalogo)
    descuidado = t29.evaluar_asistente(CASOS, t29.asistente_descuidado, catalogo)
    print(f"     honesto = {honesto} · descuidado = {descuidado}")

    assert honesto == 1.0
    assert descuidado == 0.75                 # falla 1 de 4: respeta_precio
    # El descuidado anula el presupuesto → recomienda lo más caro; el eval
    # RE-EXTRAE el presupuesto de la petición y lo compara. Donde lo caro
    # casualmente cabe, se salva: por eso 0.75 y no 0.0.

    # Y la fidelidad: un precio inventado tumba la respuesta aunque los
    # productos recuperados sean los correctos.
    prods = t29.buscar_productos(
        t29.extraer_filtros("aretes dorados por menos de 25 soles"), catalogo)
    assert t29.respuesta_es_fiel("Te recomiendo estos a S/9999.00", prods) is False
    print("     → al descuidado lo tumba respeta_precio; S/9999 tumba la fidelidad.")


# ==================================================================
# PARTE 4 · El caso trampa: presupuesto imposible
# ==================================================================
def parte_4():
    print("\n[P4] quinto caso: 'un collar de zircón por menos de 5 soles'")
    catalogo = t29.cargar_catalogo()
    casos = CASOS + [{"peticion": "un collar de zircón por menos de 5 soles"}]
    honesto = t29.evaluar_asistente(casos, t29.asistente_honesto, catalogo)
    descuidado = t29.evaluar_asistente(casos, t29.asistente_descuidado, catalogo)
    print(f"     honesto = {honesto} · descuidado = {descuidado}")

    # El honesto devuelve [] y armar_respuesta([]) dice la verdad comercial
    # ("no tengo nada que cumpla eso"). Sin productos no hay precio que violar:
    # respuesta_es_fiel(texto, []) es True → el caso APRUEBA.
    assert honesto == 1.0
    # El descuidado ignora el presupuesto también aquí → baja aún más.
    assert descuidado < 0.75
    assert t29.respuesta_es_fiel(t29.armar_respuesta([]), []) is True
    print("     → no responder es una respuesta válida; un sustituto fuera de")
    print("       presupuesto no lo es. Grounding aplicado al negocio.")


def main() -> None:
    print("=" * 64)
    print("SOLUCIÓN 29 · las cuatro fronteras del caso Sifrah (100% OFFLINE)")
    print("=" * 64)
    parte_1()
    parte_2()
    parte_3()
    parte_4()
    print("\nTodo comprobado con asserts. ✅")


if __name__ == "__main__":
    main()
