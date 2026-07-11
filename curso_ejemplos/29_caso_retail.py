"""
TEMA 29 · Caso real 2: asistente de compras para una cadena de retail
=====================================================================
FINALIDAD:
  Aplicar el arco completo del curso a un negocio REAL y verificable: Sifrah,
  cadena peruana de bisutería y accesorios de moda para mujer (90+ tiendas a
  nivel nacional y e-commerce en Shopify). Su catálogo es PÚBLICO: el endpoint
  estándar de Shopify `https://sifrah.com/products.json` devuelve productos con
  título, tags, precio, precio de oferta y disponibilidad. Este módulo construye
  sobre esa forma de dato un ASISTENTE DE COMPRAS: "quiero aretes dorados por
  menos de 25 soles" → recomendación con precios REALES, sin inventar nada.

  ⭐ La lección central del caso: en retail, PRECIO y STOCK jamás salen del
     modelo. El LLM entiende la intención y redacta; el CATÁLOGO responde.
     Un chatbot que inventa un precio no es un bug simpático: es un reclamo
     (y en Perú, un problema con Indecopi).

  ⭐ 100% OFFLINE. El catálogo de ejemplo calca la FORMA del endpoint real
     (mismos campos que products.json) con una docena de productos fijos, para
     que el pipeline entero se pueda testear byte a byte sin red. El HTML del
     curso te enseña a correr lo mismo contra los 250 productos reales.

LÓGICA (el end-to-end, paso a paso):
  1) normalizar_producto()  — ETL: el dato real llega sucio. En el catálogo real
     TODO tiene product_type="Joyería" (hasta las mochilas y los cepillos): la
     categoría de verdad hay que DERIVARLA del título y los tags.
  2) extraer_filtros()      — entender la petición: presupuesto, categoría,
     color. Aquí con reglas deterministas (testeable); en producción es
     `llm.with_structured_output(FiltrosCompra)` — el m05, tal cual.
  3) buscar_productos()     — filtros DUROS primero (precio, stock, categoría:
     eso es un WHERE, no una semántica), ranking por afinidad después. El eco
     del m24: el filtro de metadatos va en la búsqueda, no encima.
  4) armar_respuesta() + respuesta_es_fiel() — grounding: la respuesta se arma
     SOLO con productos recuperados, y un guardrail verifica que cada precio
     citado exista en el catálogo (m23 + m28: anti-alucinación de precios).
  5) evaluar_asistente()    — el eval del m16 en versión retail: sobre un mini
     dataset de peticiones, ¿el 100% de lo recomendado respeta presupuesto,
     stock y fidelidad de precios? Si un cambio lo baja: regresión.

Requisitos: ninguno extra (solo Python).  No usa red.
Ejecuta:    uv run python 29_caso_retail.py
"""

# ============ LIBRERÍAS QUE USAMOS ============
from __future__ import annotations

import re
import unicodedata

# ============ 1) EL CATÁLOGO, CON LA FORMA DEL DATO REAL ============
# Calca los campos del products.json de Shopify (título, tags, variants con
# price/compare_at_price/available, product_type). Nota el detalle REAL más
# importante: product_type dice "Joyería" en TODO — la mochila incluida. Así
# llega el dato de verdad; el paso 1 existe por esto.
CATALOGO_CRUDO = [
    {"title": "Aretes Argolla Mediana Dorado", "product_type": "Joyería",
     "tags": ["Aretes", "Bañado en oro", "Colección Julio"],
     "variants": [{"sku": "AR-001", "price": "19.90", "compare_at_price": None, "available": True}]},
    {"title": "Aretes Colgantes Perla Plateado", "product_type": "Joyería",
     "tags": ["Aretes", "Bañado en plata"],
     "variants": [{"sku": "AR-002", "price": "24.90", "compare_at_price": "34.90", "available": True}]},
    {"title": "Aretes Piedra Zircón Dorado", "product_type": "Joyería",
     "tags": ["Aretes", "Zircón"],
     "variants": [{"sku": "AR-003", "price": "29.90", "compare_at_price": None, "available": False}]},
    {"title": "Collar Cadena Fina Dorado", "product_type": "Joyería",
     "tags": ["Collares", "Bañado en oro"],
     "variants": [{"sku": "CO-001", "price": "39.90", "compare_at_price": None, "available": True}]},
    {"title": "Collar Dije Corazón Plateado", "product_type": "Joyería",
     "tags": ["Collares", "Bañado en plata"],
     "variants": [{"sku": "CO-002", "price": "34.90", "compare_at_price": "49.90", "available": True}]},
    {"title": "Anillo Ajustable Zircón Plateado", "product_type": "Joyería",
     "tags": ["Anillos", "Zircón"],
     "variants": [{"sku": "AN-001", "price": "16.90", "compare_at_price": None, "available": True}]},
    {"title": "Pulsera Acero Eslabones Dorado", "product_type": "Joyería",
     "tags": ["Pulseras", "Acero"],
     "variants": [{"sku": "PU-001", "price": "22.90", "compare_at_price": None, "available": True}]},
    {"title": "Cartera Crossbody Clásica Negro", "product_type": "Joyería",
     "tags": ["Carteras Y Mochilas", "Bolsos y Carteras para mujer"],
     "variants": [{"sku": "CA-001", "price": "69.90", "compare_at_price": None, "available": True}]},
    {"title": "Mochila 2 en 1 Travel Fucsia", "product_type": "Joyería",
     "tags": ["Mochila", "Promocional"],
     "variants": [{"sku": "MO-001", "price": "12.90", "compare_at_price": "39.90", "available": True}]},
    {"title": "Set Ganchos Pico de Pato Flor Dorado", "product_type": "Joyería",
     "tags": ["Accesorio De Cabello", "Clip"],
     "variants": [{"sku": "GA-001", "price": "10.90", "compare_at_price": None, "available": True}]},
    {"title": "Set Colets Básicos 15 Unidades", "product_type": "Joyería",
     "tags": ["Accesorio De Cabello", "Basico"],
     "variants": [{"sku": "GA-002", "price": "6.90", "compare_at_price": None, "available": True}]},
    {"title": "Cepillo de Cabello con Espejo Negro", "product_type": "Joyería",
     "tags": ["Belleza", "Basico"],
     "variants": [{"sku": "BE-001", "price": "14.90", "compare_at_price": None, "available": True}]},
]

# La categoría REAL se deriva del título+tags, no del product_type (que miente).
# Orden: la primera palabra clave que aparezca gana. "gancho"/"colet" van antes
# que "cabello" para que el cepillo (belleza) no se cuele como accesorio de cabello.
_CATEGORIAS = [
    ("aretes",   ("arete", "argolla")),
    ("collares", ("collar", "dije")),
    ("anillos",  ("anillo",)),
    ("pulseras", ("pulsera",)),
    ("carteras", ("cartera", "bolso", "crossbody")),
    ("mochilas", ("mochila",)),
    ("cabello",  ("gancho", "colet", "accesorio de cabello", "clip")),
    ("belleza",  ("cepillo", "espejo", "belleza")),
]

_STOPWORDS = {"de", "la", "el", "los", "las", "un", "una", "con", "para", "por",
              "y", "en", "que", "menos", "hasta", "algo", "quiero", "busco",
              "soles", "maximo", "máximo"}


def _sin_tildes(texto: str) -> str:
    """'zircón' → 'zircon': compara sin tildes para que la búsqueda no dependa
    de si quien escribe acentúa (nadie acentúa en un chat)."""
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def normalizar_producto(crudo: dict) -> dict:
    """ETL de UN producto: de la forma del endpoint a la forma que usa el asistente.

    PORQUÉ existe este paso: el dato real nunca llega listo. En el catálogo real
    de Shopify, `price` es un STRING ("12.90"), la promoción hay que deducirla
    (compare_at_price > price) y product_type es inútil ("Joyería" en todo).
    Quien se salta el ETL termina con un asistente que compara strings y
    clasifica mochilas como joyas.
    """
    variante = crudo["variants"][0]
    precio = float(variante["price"])                      # "12.90" → 12.9
    antes = variante.get("compare_at_price")
    texto = _sin_tildes(f"{crudo['title']} {' '.join(crudo['tags'])}".lower())

    categoria = "otros"
    for nombre, claves in _CATEGORIAS:
        if any(clave in texto for clave in claves):
            categoria = nombre
            break

    return {
        "sku": variante["sku"],
        "titulo": crudo["title"],
        "categoria": categoria,                            # derivada, no confiada
        "precio": precio,
        "en_promo": antes is not None and float(antes) > precio,
        "disponible": bool(variante["available"]),
        "texto": texto,                                    # lo indexable
    }


def cargar_catalogo(crudos: list[dict] | None = None) -> list[dict]:
    """El catálogo normalizado. Inyectable para testear con otros datos."""
    return [normalizar_producto(p) for p in (crudos or CATALOGO_CRUDO)]


# ============ 2) ENTENDER LA PETICIÓN: extraer filtros ============
_RE_PRESUPUESTO = re.compile(
    r"(?:menos de|hasta|maximo|no mas de|tope de)\s*s?/?\.?\s*(\d+(?:\.\d+)?)")

_COLORES = ("dorado", "plateado", "negro", "fucsia", "rosa")

# La clienta no habla como el catálogo: dice "aros" (peruanísimo), "pelo",
# "cadena". Estos sinónimos SOLO aplican a la petición — al producto no, porque
# "cabello" clasificaría el cepillo (belleza) como accesorio de cabello.
_SINONIMOS_PETICION = {
    "aretes":   ("aros", "pendiente"),
    "collares": ("cadena",),
    "cabello":  ("cabello", "pelo"),
}


def extraer_filtros(peticion: str) -> dict:
    """De 'aretes dorados por menos de 25 soles' → {categoria, color, presupuesto}.

    Aquí es determinista (reglas + regex) para que el test sea byte a byte. En
    producción este paso ES el m05: `llm.with_structured_output(FiltrosCompra)`
    con un molde Pydantic — el LLM entiende 'algo lindo pa mi flaca, unos 30
    lucas' mucho mejor que un regex. La INTERFAZ (petición → filtros tipados)
    es la misma; por eso el resto del pipeline no cambia al subir de nivel.
    """
    texto = _sin_tildes(peticion.lower())
    filtros: dict = {"presupuesto": None, "categoria": None, "color": None}

    if (m := _RE_PRESUPUESTO.search(texto)):
        filtros["presupuesto"] = float(m.group(1))

    for nombre, claves in _CATEGORIAS:
        claves_peticion = claves + _SINONIMOS_PETICION.get(nombre, ())
        if any(clave in texto for clave in claves_peticion):
            filtros["categoria"] = nombre
            break

    for color in _COLORES:
        if color in texto:
            filtros["color"] = color
            break

    return filtros


# ============ 3) BUSCAR: filtros DUROS primero, ranking después ============
def buscar_productos(filtros: dict, catalogo: list[dict], k: int = 3) -> list[dict]:
    """Los k mejores productos que CUMPLEN los filtros. Puede devolver menos, o nada.

    PORQUÉ en dos fases:
      - Presupuesto, stock y categoría son restricciones DURAS: un producto de
        S/39.90 ante un tope de S/25 no es "menos relevante", es INVÁLIDO. Eso
        se resuelve con un filtro (el WHERE del m24), jamás con el ranking.
      - Solo ENTRE los válidos se ordena por afinidad con la petición (solape
        de términos — el espíritu del m11 en miniatura; en producción,
        embeddings + re-ranking del m12).
    Y la regla del m20: si nada cumple, la respuesta es LISTA VACÍA. "No tengo"
    es una respuesta válida; un sustituto fuera de presupuesto no lo es.
    """
    candidatos = [p for p in catalogo if p["disponible"]]
    if filtros.get("presupuesto") is not None:
        candidatos = [p for p in candidatos if p["precio"] <= filtros["presupuesto"]]
    if filtros.get("categoria"):
        candidatos = [p for p in candidatos if p["categoria"] == filtros["categoria"]]

    def afinidad(producto: dict) -> tuple:
        # El color pedido pesa más que cualquier otro término; a igualdad,
        # gana el más barato (regla de la casa: primero lo accesible).
        con_color = filtros.get("color") and filtros["color"] in producto["texto"]
        return (1 if con_color else 0, -producto["precio"])

    return sorted(candidatos, key=afinidad, reverse=True)[:k]


# ============ 4) RESPONDER CON GROUNDING (y verificarlo) ============
def armar_respuesta(productos: list[dict]) -> str:
    """El BORRADOR de respuesta, armado SOLO con productos recuperados.

    En producción, este texto se lo pasas al LLM para que lo redacte con tono
    de marca (m02: el prompt manda el contexto, el modelo pone la prosa). La
    regla que no se negocia: el modelo REDACTA sobre estos datos; no añade
    productos, precios ni stock de su cosecha.

    ⚠️ Y un detalle que nos mordió al escribir este módulo: la primera versión
       ECOABA la petición ("Para «...hasta S/80» te recomiendo") — y el guardrail
       de abajo saltaba, porque ese S/80 del usuario no es un precio del
       catálogo. La cura es no re-inyectar el texto del usuario en la salida:
       la misma higiene que el m23 pide contra la inyección de prompts.
    """
    if not productos:
        return ("No encontré productos que cumplan lo que pides. "
                "¿Ajustamos el presupuesto o miramos otra categoría?")
    lineas = ["Esto es lo que tengo para ti:"]
    for p in productos:
        promo = " ¡en promo!" if p["en_promo"] else ""
        lineas.append(f"- {p['titulo']} a S/{p['precio']:.2f}{promo} (SKU {p['sku']})")
    return "\n".join(lineas)


def precios_citados(texto: str) -> set[float]:
    """Todos los S/xx.xx que un texto menciona. Es la mitad del guardrail."""
    return {float(m) for m in re.findall(r"S/\s?(\d+(?:\.\d+)?)", texto)}


def respuesta_es_fiel(texto: str, productos: list[dict]) -> bool:
    """¿Cada precio citado en la respuesta existe en los productos recuperados?

    Es el guardrail de salida del caso (m23) apuntando al riesgo #1 del retail:
    el PRECIO INVENTADO. Mismo espíritu que el detector del m28 —desconfiar de
    lo no sostenido—, pero determinista: aquí la fuente de verdad existe (el
    catálogo), así que se verifica contra ella, no contra la dispersión.
    """
    permitidos = {round(p["precio"], 2) for p in productos}
    return all(round(precio, 2) in permitidos for precio in precios_citados(texto))


# ============ 5) EVALUAR: el ritual del m16, versión retail ============
def evaluar_asistente(casos: list[dict], responder, catalogo: list[dict]) -> float:
    """% de casos donde TODO lo recomendado respeta presupuesto, stock y precios.

    `responder(peticion, catalogo) -> (productos, texto)` es el asistente bajo
    prueba: se inyecta para poder comparar dos versiones (¿mejoró el cambio?)
    igual que en el m16. Un caso aprueba solo si:
      - cada producto recomendado está disponible y dentro del presupuesto, y
      - la respuesta no cita precios fuera del catálogo recuperado.
    """
    aprobados = 0
    for caso in casos:
        productos, texto = responder(caso["peticion"], catalogo)
        presupuesto = extraer_filtros(caso["peticion"])["presupuesto"]
        respeta_precio = all(
            p["precio"] <= presupuesto for p in productos
        ) if presupuesto is not None else True
        respeta_stock = all(p["disponible"] for p in productos)
        if respeta_precio and respeta_stock and respuesta_es_fiel(texto, productos):
            aprobados += 1
    return aprobados / len(casos) if casos else 0.0


def asistente_honesto(peticion: str, catalogo: list[dict]):
    """El pipeline completo: filtros → búsqueda → respuesta con grounding."""
    productos = buscar_productos(extraer_filtros(peticion), catalogo)
    return productos, armar_respuesta(productos)


def asistente_descuidado(peticion: str, catalogo: list[dict]):
    """El anti-ejemplo: ignora el presupuesto (recomienda lo más caro que haya).

    Existe para que el eval lo ATRAPE: así se ve, con un número, por qué los
    filtros duros no son opcionales. Es el mismo truco del m26b: comparar el
    pipeline bueno contra uno malo con la MISMA métrica.
    """
    filtros = extraer_filtros(peticion)
    filtros["presupuesto"] = None                          # ← el "descuido"
    productos = sorted(buscar_productos(filtros, catalogo, k=2),
                       key=lambda p: p["precio"], reverse=True)
    return productos, armar_respuesta(productos)


# ============ DEMO ============
def main() -> None:
    catalogo = cargar_catalogo()
    print(f"Catálogo normalizado: {len(catalogo)} productos "
          f"({sum(p['en_promo'] for p in catalogo)} en promo)\n")

    peticiones = [
        "quiero aretes dorados por menos de 25 soles",
        "una cartera para regalo, hasta S/80",
        "algo para el cabello, máximo 12 soles",
        "un collar de zircón por menos de 10 soles",   # nada cumple → honestidad
    ]
    for peticion in peticiones:
        filtros = extraer_filtros(peticion)
        productos = buscar_productos(filtros, catalogo)
        respuesta = armar_respuesta(productos)
        print(f"» {peticion}")
        print(f"  filtros: {filtros}")
        print("  " + respuesta.replace("\n", "\n  "))
        print(f"  guardrail de precios: "
              f"{'OK' if respuesta_es_fiel(respuesta, productos) else 'VIOLADO'}\n")

    print("=== EVAL · asistente honesto vs descuidado (misma métrica) ===")
    # Casos con presupuestos AJUSTADOS a propósito: donde ignorar el tope duele.
    casos = [
        {"peticion": "aretes dorados por menos de 25 soles"},
        {"peticion": "un collar hasta S/35"},          # el de 39.90 NO debe salir
        {"peticion": "algo para el pelo, máximo 8 soles"},  # solo los colets caben
        {"peticion": "una cartera hasta S/80"},
    ]
    bueno = evaluar_asistente(casos, asistente_honesto, catalogo)
    malo = evaluar_asistente(casos, asistente_descuidado, catalogo)
    print(f"  honesto    (filtros duros + grounding): {bueno:.0%}")
    print(f"  descuidado (ignora el presupuesto)    : {malo:.0%}")
    print("  → la métrica atrapa al descuidado. Sin eval, lo atrapa un cliente.")


if __name__ == "__main__":
    main()
