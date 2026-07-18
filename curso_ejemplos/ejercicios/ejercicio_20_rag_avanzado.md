# Ejercicio 20 — RAG avanzado: cuándo el multi-query NO ayuda

**Ejemplo base:** `20_rag_avanzado.py` · **Gasta cuota:** no (100% offline)

> Este ejercicio no llama a ningún modelo. Toda la mecánica —expansión, RRF,
> compresión— es aritmética determinista sobre `datos_rag.txt`, así que puedes
> **predecir** el resultado antes de ejecutarlo. Eso es justo lo que se te pide.

## Contexto

`20_rag_avanzado.py` ataca el RAG por el lado de la **pregunta**: en vez de una
búsqueda, genera 3–4 reformulaciones (`expandir_consulta`), recupera con cada una
(`recuperar`) y fusiona los rankings con RRF (`fusion_rrf`).

El ejemplo está montado para que el multi-query **gane**: la pregunta dice
«devolución» y el documento dice «reembolso», y el mapa `SINONIMOS` tapa
justo ese hueco.

Ahora vas a buscar dónde **no** gana. Una técnica que solo has visto triunfar es
una técnica que todavía no entiendes.

## Parte 1 — Predice antes de ejecutar

Para la pregunta `"¿Cómo pido la devolución de mi dinero?"`:

1. Escribe en un papel **cuántas variantes** devuelve `expandir_consulta` y
   cuáles son, sin ejecutar nada.
2. Predice qué chunk queda **1º** con `recuperar(pregunta, chunks, k=3)` (una
   sola búsqueda) y cuál queda 1º con `rag_fusion(...)`.

**Criterio de aceptación:** tu predicción del número de variantes coincide con
`len(expandir_consulta(pregunta))` (son **4**), y aciertas el hecho incómodo: con
la pregunta cruda, `recuperar` devuelve **lista vacía** —no encuentra nada— y sin
embargo `rag_fusion` sí recupera el chunk correcto. Explica por qué.

Después compara con `expandir_consulta("reembolso")`. Ahí solo sale **1**
variante. Explica qué línea de la función hace que las otras tres desaparezcan.

## Parte 2 — Encuentra el caso donde RAG-Fusion EMPATA o PIERDE

Busca una pregunta en la que `rag_fusion` **no mejore** a `recuperar` a secas —
o incluso devuelva peor orden.

Pistas de dónde mirar: preguntas cuyo vocabulario ya coincide con el documento,
preguntas de una sola palabra, o preguntas cuyos sinónimos **no** están en el
mapa `SINONIMOS`.

**Criterio de aceptación:** documenta **una pregunta concreta** donde los dos
rankings coincidan (o el de fusión sea peor), y explica el mecanismo: ¿qué
hicieron las variantes en ese caso? Responde además: si el multi-query a veces no
aporta y siempre cuesta N búsquedas en vez de 1, ¿cómo decidirías en producción
cuándo activarlo?

## Parte 3 — Rompe el RRF subiendo k

`fusion_rrf` tiene un parámetro `k=60` (el del paper original). Ejecútalo con
`k=1` y con `k=10000` sobre los mismos rankings.

**Criterio de aceptación:** explica con los números en la mano qué le pasa al
ranking en cada extremo, y por qué `k` alto hace que **el puesto deje de
importar**. Di cuál de los dos extremos se parece más a "votar por mayoría".

## Parte 4 — La compresión que borra la respuesta

`comprimir_contexto` conserva solo las frases que comparten términos con la
pregunta. Es un ahorro de tokens… y un riesgo.

**Criterio de aceptación:** encuentra una pregunta donde `comprimir_contexto`
**elimine la frase que contiene la respuesta**, y explica por qué el filtro la
descartó. Propón un arreglo y di qué te cuesta.

---

## Pistas

<details>
<summary>Pista 1 — por qué las variantes no son 4</summary>

`expandir_consulta` construye hasta cuatro candidatas, pero termina con:

```python
return list(dict.fromkeys(variantes))
```

Eso **deduplica conservando el orden**. Si la pregunta no contiene ninguna
palabra del mapa `SINONIMOS`, la variante "sustituida" es idéntica a la original
y desaparece; y si no tiene stopwords, la de "solo palabras clave" también
colapsa.

Una pregunta ya limpia y sin sinónimos conocidos genera **una sola variante**. Y
ahí el multi-query es, literalmente, la búsqueda de siempre pagada N veces.

</details>

<details>
<summary>Pista 2 — dónde empata la fusión</summary>

Prueba `"¿Quién controla las llaves de API?"`. El documento usa ese mismo
vocabulario, así que:

- la variante "solo clave" recupera casi lo mismo que la original,
- `SINONIMOS` sí tiene `credenciales`/`contraseña` → `llaves`, pero la pregunta
  ya dice "llaves", así que no hay nada que sustituir.

Con todas las variantes devolviendo el **mismo ranking**, RRF suma lo mismo a
cada chunk y el orden final es idéntico. La fusión de N copias de una lista es
esa lista.

**La regla:** el multi-query paga cuando hay **desajuste de vocabulario** entre
la pregunta y el corpus. Sin ese desajuste, solo multiplica el coste.

</details>

<details>
<summary>Pista 3 — la aritmética de k en RRF</summary>

El aporte de un chunk que queda en el puesto *p* (0-indexado) es `1/(k+p+1)`.

- Con **k=1**: 1º aporta 1/2 = 0.500, 2º aporta 1/3 = 0.333. El primer puesto
  vale **un 50% más** que el segundo. El puesto lo decide casi todo.
- Con **k=10000**: 1º aporta 1/10001 ≈ 0.0000999, 2º aporta 1/10002 ≈ 0.0000999.
  Prácticamente idénticos. Lo único que distingue a un chunk es **en cuántas
  listas aparece**.

Por eso `k` alto ≈ **votar por mayoría** (importa la presencia, no la posición) y
`k` bajo ≈ dictadura del primer puesto. El 60 del paper es el compromiso: el
puesto pesa, pero aparecer en varias listas pesa más.

</details>

<details>
<summary>Pista 4 — por qué la compresión borra la respuesta</summary>

Mira el filtro:

```python
terminos = {t for t in tokenizar(pregunta) if t not in STOPWORDS and len(t) > 3}
```

Ese `len(t) > 3` descarta términos cortos. Y los términos cortos suelen ser los
más discriminantes de un dominio: `IVA`, `DNI`, `SLA`, `RUC`… o, en este corpus,
**`API`**.

Prueba con **«¿Dan API?»** y mira las dos cosas por separado: qué recupera
`rag_fusion` y qué devuelve `comprimir_contexto`. La sorpresa es que el
retriever acierta de pleno.

Peor aún: la frase con la respuesta puede usar un sinónimo del documento que no
esté en el mapa. El filtro no la reconoce y la tira.

**El arreglo** y su coste: bajar el umbral de longitud o añadir un *fallback*
("si la compresión deja menos de N caracteres, devuelve el chunk entero"). Lo que
cuesta es lo obvio: más tokens. La compresión es siempre un canje entre coste y
riesgo de amputar la respuesta — y amputarla es mucho más caro que unos tokens.

</details>

---

## Reflexión

Las técnicas de RAG avanzado se presentan casi siempre con el caso donde
brillan. Multi-query brilla con desajuste de vocabulario; re-ranking brilla con
mucho ruido recuperado; la compresión brilla con contextos largos y redundantes.

La pregunta profesional no es *"¿es buena esta técnica?"* sino **"¿qué problema
concreto tiene mi pipeline, y esta técnica ataca ese problema?"**. Añadir
multi-query a un RAG cuyo fallo real es que el documento no contiene la respuesta
es multiplicar por cuatro el coste de fallar.

Mide primero. Luego elige la técnica.

**Solución:** [`soluciones/solucion_20_rag_avanzado.py`](soluciones/solucion_20_rag_avanzado.py)
