"""
agent.py · El lazo completo: redactar → verificar → reintentar → fallback
==========================================================================
FINALIDAD:
  Orquestar el pipeline con el LLM cableado y el guardrail cerrando el lazo:

      petición
        → intención  (intent.py: with_structured_output → filtros tipados, m05)
        → búsqueda    (search.py: filtros DUROS + ranking)
        → redacción   (el LLM pone la prosa de vendedora SOLO sobre lo recuperado)
        → grounding   (price_guard.py: ¿algún precio inventado?)
        → [si falla]  reintento correctivo → [si vuelve a fallar] FALLBACK determinista

  ⭐ El grounding NO es opcional. Una respuesta con un precio inventado no llega
     jamás al cliente. El fallback `armar_respuesta()` es determinista: si el
     modelo insiste en inventar, gana la plantilla, que es fiel por construcción.

  ⭐ Todo entra por parámetro (llm, variante, extraer) → el pipeline entero se
     testea con un ModeloFalso, sin cuota. La MISMA métrica del eval (m16) que
     juzga a este agente juzga también a la maqueta del `29_caso_retail.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from proyecto_retail.app import intent
from proyecto_retail.app.search import buscar_productos
from proyecto_retail.guardrails.output_guard import revisar_salida
from proyecto_retail.prompts.loader import cargar_cacheado


@dataclass(frozen=True)
class RespuestaAgente:
    """Lo que produce el agente para una petición. Inmutable."""
    productos: list[dict]
    texto: str
    variante: str = "vendedora"
    acciones: tuple[str, ...] = field(default_factory=tuple)


# ------------------------------------------------------------------
# El fallback determinista (fiel por construcción)
# ------------------------------------------------------------------
def formatear_productos(productos: list[dict]) -> str:
    """La lista de productos recuperados, para inyectar en el prompt de la vendedora."""
    if not productos:
        return "(no hay productos que cumplan la petición)"
    return "\n".join(
        f"- {p['titulo']} · S/{p['precio']:.2f}"
        f"{' · EN PROMO' if p['en_promo'] else ''} · SKU {p['sku']}"
        for p in productos)


def armar_respuesta(productos: list[dict]) -> str:
    """El borrador determinista, armado SOLO con productos recuperados.

    Es el FALLBACK: fiel por construcción (cita exactamente los precios del
    catálogo). Cuando hay productos, el LLM lo mejora con tono de marca; cuando el
    LLM falla el grounding dos veces, esta plantilla es la red de seguridad.
    """
    if not productos:
        return ("No encontré productos que cumplan lo que pides. "
                "¿Ajustamos el presupuesto o miramos otra categoría?")
    lineas = ["Esto es lo que tengo para ti:"]
    for p in productos:
        promo = " ¡en promo!" if p["en_promo"] else ""
        lineas.append(f"- {p['titulo']} a S/{p['precio']:.2f}{promo} (SKU {p['sku']})")
    return "\n".join(lineas)


# ------------------------------------------------------------------
# La redacción con el LLM (tono de marca, sobre lo recuperado)
# ------------------------------------------------------------------
def redactar_respuesta_llm(llm, productos: list[dict],
                           variante: str = "vendedora", correccion: str = "") -> str:
    """El LLM redacta la recomendación SOLO sobre los productos recuperados.

    `variante` elige el prompt (A/B). `correccion` se usa en el reintento: se le
    dice al modelo qué precios puede citar y se le pide rehacer la respuesta.
    """
    prompt = cargar_cacheado(variante)
    sistema = prompt.render(productos=formatear_productos(productos))
    humano = "Recomiéndale a la clienta entre esos productos (y solo esos)."
    if correccion:
        humano += f"\n\n{correccion}"

    respuesta = llm.invoke([("system", sistema), ("human", humano)])
    return respuesta.content.strip()


# ------------------------------------------------------------------
# El lazo completo
# ------------------------------------------------------------------
def responder_con_guardrail(llm, peticion: str, catalogo: list[dict],
                            *, variante: str = "vendedora",
                            extraer=None, k: int = 3) -> RespuestaAgente:
    """El pipeline con el LLM cableado y el guardrail cerrando el lazo.

    extraer: callable(llm, peticion) -> dict de filtros. Por defecto, el m05
             (intent.extraer_filtros_llm). Se inyecta para testear con reglas.
    """
    extraer = extraer if extraer is not None else intent.extraer_filtros_llm
    filtros = extraer(llm, peticion)
    productos = buscar_productos(filtros, catalogo, k=k)

    # Sin candidatos no hay nada que inventar: la honestidad determinista basta.
    if not productos:
        return RespuestaAgente(productos, armar_respuesta([]), variante,
                               acciones=("sin_resultados",))

    # 1) El LLM redacta con tono de marca.
    texto = redactar_respuesta_llm(llm, productos, variante)
    veredicto = revisar_salida(texto, productos)
    if veredicto.permitido:
        return RespuestaAgente(productos, texto, variante)

    # 2) Reintento correctivo: le recordamos qué precios son legítimos.
    precios_ok = ", ".join(f"S/{p['precio']:.2f}" for p in productos)
    correccion = (f"Tu respuesta anterior citó un precio que NO está en el "
                  f"catálogo. Los ÚNICOS precios permitidos son: {precios_ok}. "
                  f"Reescríbela usando solo esos.")
    texto = redactar_respuesta_llm(llm, productos, variante, correccion)
    veredicto = revisar_salida(texto, productos)
    if veredicto.permitido:
        return RespuestaAgente(productos, texto, variante, acciones=("reintento_grounding",))

    # 3) El modelo insiste en inventar: gana el determinista. Fiel siempre.
    return RespuestaAgente(productos, armar_respuesta(productos), variante,
                           acciones=("reintento_grounding", "fallback_determinista"))


def agente_compras(llm, *, variante: str = "vendedora", extraer=None):
    """Un `responder(peticion, catalogo) -> (productos, texto)` con el LLM dentro.

    Compatible con `evals/retail_metric.py`: la MISMA métrica que juzga a la
    maqueta juzga al agente real. Se inyecta `llm` para pasar un ModeloFalso en
    los tests y evaluar sin cuota.
    """
    def responder(peticion: str, catalogo: list[dict]):
        r = responder_con_guardrail(llm, peticion, catalogo, variante=variante, extraer=extraer)
        return r.productos, r.texto
    return responder


def construir_responder_real(variante: str = "vendedora"):  # pragma: no cover - requiere API
    """El responder de producción: construye el LLM del .env y lo cablea."""
    from proyecto_retail.app.llm import crear_llm
    return agente_compras(crear_llm(), variante=variante)
