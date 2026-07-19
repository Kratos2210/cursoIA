# Ejercicio 29 — Retail: el dato sucio, el filtro tonto y el eval que no perdona

**Ejemplo base:** `29_caso_retail.py` · **Gasta cuota:** no (100% offline)

> El caso Sifrah entero es determinista: ETL, filtros, búsqueda, grounding y
> eval son funciones puras. Este ejercicio te hace predecir dónde se rompe cada
> pieza — que es exactamente lo que te va a preguntar un cliente real: "¿y si
> el catálogo viene mal?", "¿y si la clienta escribe distinto?", "¿cómo sabes
> que no inventa precios?".

## Contexto

`29_caso_retail.py`: `normalizar_producto` (ETL de un producto estilo Shopify),
`extraer_filtros` (petición → `{presupuesto, categoria, color}` con regex y
sinónimos), `buscar_productos` (presupuesto = filtro DURO), `respuesta_es_fiel`
(ningún precio citado fuera del contexto) y `evaluar_asistente` (% de casos que
respetan precio, stock y fidelidad) con `asistente_honesto` vs
`asistente_descuidado`.

## Parte 1 — El ETL y la promo que no es promo

Normaliza este producto crudo:

```python
crudo = {"title": "Aretes Luna", "tags": ["dorado"],
         "variants": [{"sku": "AR-9", "price": "59.90",
                       "compare_at_price": "59.90", "available": True}]}
```

**Criterio de aceptación:** predice `precio`, `categoria` y —sobre todo—
`en_promo` ANTES de ejecutar. Explica por qué `price` llega como string y qué
regla exacta decide `en_promo` (¿qué pasaría si un catálogo pusiera
`compare_at_price` igual al precio en TODOS los productos, como hacen algunas
tiendas para "rellenar" el campo?).

## Parte 2 — El filtro que entiende "cadena" pero no "dorada"

Extrae los filtros de esta petición:

```python
extraer_filtros("una cadena dorada, tope de S/ 40")
```

**Criterio de aceptación:** predice los tres campos antes de ejecutar. Uno de
los tres te va a sorprender. Explica la causa exacta mirando el código (cómo
matchea `_COLORES`) y di qué pieza del curso reemplaza esta extracción por
reglas cuando el producto sube de nivel (está en el docstring de la función —
pero predícelo primero).

## Parte 3 — La fidelidad y el eval comparativo

Con el catálogo por defecto y estos cuatro casos:

```python
casos = [{"peticion": p} for p in [
    "quiero aretes dorados por menos de 25 soles",
    "una cartera para regalo, hasta S/80",
    "algo para el cabello, máximo 12 soles",
    "un collar de zircón por menos de 10 soles",
]]
```

**Criterio de aceptación:** predice el score de `evaluar_asistente` para
`asistente_honesto` y para `asistente_descuidado`, y QUÉ criterio exacto (de
los tres: presupuesto, stock, fidelidad de precios) tumba los casos que el
descuidado falla. Verifica también que una respuesta con un precio inventado
(`"…a S/9999.00"`) falla `respuesta_es_fiel` aunque los productos sean los
correctos.

## Parte 4 — Escribe tu propio caso trampa

Añade un quinto caso cuyo presupuesto sea imposible de cumplir en su categoría
(mira los precios del catálogo con `cargar_catalogo()`).

**Criterio de aceptación:** con tu caso añadido, el honesto sigue en 1.0 y el
descuidado baja. Explica por qué una respuesta SIN productos pasa el eval
(¿qué devuelve `armar_respuesta([])` y por qué eso es lo correcto para el
negocio, aunque "no vendió nada"?).

---

## Pistas

<details>
<summary>Pista 1 — la regla exacta de en_promo</summary>

```python
antes = variante.get("compare_at_price")
en_promo = antes is not None and float(antes) > precio
```

Es `>` **estricto**: `compare_at_price == price` NO es promo. Con `"59.90"` en
ambos campos, `en_promo` da `False` — correcto: no hay rebaja. Un catálogo que
rellena `compare_at_price` con el mismo precio no infla las promos, gracias a
ese `>`. Y `price` llega como string porque así lo entrega el endpoint real de
Shopify: el ETL existe precisamente para que `float("59.90")` ocurra en UN
sitio y no en cada comparación.

</details>

<details>
<summary>Pista 2 — el género que rompe el color</summary>

Resultado real: `{'presupuesto': 40.0, 'categoria': 'collares', 'color': None}`.

- `presupuesto`: la regex acepta "tope de" y el `S/` opcional → 40.0. ✓
- `categoria`: "cadena" es sinónimo de petición para "collares". ✓
- `color`: el matching es `color in texto` con `_COLORES = ("dorado", …)` — y
  `"dorado"` **no es substring de `"dorada"`**. El femenino rompe el filtro.

La pieza que reemplaza esto en producción es el **m05**: 
`llm.with_structured_output(FiltrosCompra)` — un LLM entiende "dorada", "algo
lindo pa mi flaca, unos 30 lucas" y todo lo que el regex jamás verá. La
interfaz (petición → filtros tipados) no cambia; por eso el resto del pipeline
sobrevive al upgrade.

</details>

<details>
<summary>Pista 3 — quién tumba al descuidado</summary>

Scores reales: honesto **1.0**, descuidado **0.75** (falla 1 de 4).

El descuidado anula el presupuesto y recomienda lo más caro. El criterio que lo
tumba es `respeta_precio`: `evaluar_asistente` re-extrae el presupuesto de la
petición y comprueba `p["precio"] <= presupuesto` sobre lo recomendado. En los
casos donde lo más caro casualmente cabe en el presupuesto, el descuidado se
salva — por eso no baja a 0.0. (Stock no lo tumba: el catálogo demo casi todo
está disponible; y sus precios son reales, así que la fidelidad tampoco.)

Y sí: `respuesta_es_fiel("…a S/9999.00", productos)` da `False` — 9999.00 no
está entre los precios del contexto recuperado.

</details>

<details>
<summary>Pista 4 — el caso imposible</summary>

```python
casos.append({"peticion": "un collar de zircón por menos de 5 soles"})
```

Con presupuesto 5.0 ningún collar sobrevive al filtro duro → el honesto
devuelve `[]` y `armar_respuesta([])` responde la verdad comercial: "no tengo
nada que cumpla eso, ¿ajustamos presupuesto o miramos otra categoría?". Ese
caso aprueba el eval: sin productos no hay precio que violar ni stock que
mentir, y `respuesta_es_fiel(texto, [])` es `True` porque no cita precios.

El descuidado, en cambio, ignora el presupuesto y recomienda collares carísimos
→ `respeta_precio` falso → su score baja. **No responder es una respuesta
válida; un sustituto fuera de presupuesto no lo es.** Eso es grounding aplicado
al negocio, no solo a los datos.

</details>

---

## Reflexión

El caso entero es la misma lección cuatro veces: **cada frontera del sistema
necesita su regla explícita**. El ETL decide qué es promo (no el string del
endpoint), el filtro decide qué es "dorado" (y falla en lo que no previó), el
presupuesto es un filtro duro (no una sugerencia), y el eval re-deriva las
reglas desde la petición (no confía en el asistente). Cuando el LLM reemplace
al regex del m05, todas esas reglas siguen ahí — porque el modelo pone la
prosa, pero las fronteras las pones tú.

**Solución:** [`soluciones/solucion_29_retail.py`](soluciones/solucion_29_retail.py)
