# Ejercicio 28 — Alucinaciones: mide la sospecha, no la confíes

**Ejemplo base:** `28_alucinaciones.py` · **Gasta cuota:** no (100% offline)

> El detector de inconsistencia del m28 es aritmética pura sobre strings. Eso lo
> hace testeable — y también le da puntos ciegos MUY concretos. Este ejercicio
> te hace predecir sus números y encontrarle los límites, que es la única forma
> honesta de usar un detector en producción.

## Contexto

`28_alucinaciones.py` trae `detectar_inconsistencia` (dispersión entre varias
respuestas a la MISMA pregunta: `1 - más_común/total`), `es_sospechosa`
(umbral 0.5), `medir_fragilidad`/`es_fragil` (¿variantes triviales del prompt
cambian la respuesta?) y la taxonomía consultable `causas_por_modulo`.

## Parte 1 — Predice el score (y cae en la trampa)

Cuatro muestras de la misma pregunta ("¿capital de Francia?"):

```python
respuestas = ["París.", " parís ", "Paris", "Lyon"]
```

**Criterio de aceptación:** predice `detectar_inconsistencia(respuestas)` y
`es_sospechosa(respuestas)` ANTES de ejecutar. Si tu predicción fue 0.25 /
False, ejecuta y explica exactamente qué hace `_normalizar` con cada una de las
cuatro — y qué NO hace.

## Parte 2 — Engaña al detector con la verdad… mentirosa

Construye una lista de respuestas donde el detector dé **0.0** (consistencia
perfecta) siendo todas **falsas**.

**Criterio de aceptación:** tu lista da score 0.0, y explicas en dos frases por
qué el self-check por consistencia no puede atrapar un error *sistemático* (el
modelo que se aprendió mal un dato lo repite igual de convencido en cada
muestra). ¿Qué módulo del curso ataca ESE tipo de error? Compruébalo con
`causas_por_modulo`.

## Parte 3 — Fragilidad: ¿cuántas respuestas "distintas" hay aquí?

Tres variantes triviales del mismo prompt devolvieron:

```python
respuestas = ["1969", "En 1969", "1969."]
```

**Criterio de aceptación:** predice `medir_fragilidad(respuestas)` y
`es_fragil(respuestas)` antes de ejecutar. Explica cuál de las tres se unifica
con cuál, cuál no, y por qué esta métrica sobre-reporta fragilidad cuando las
respuestas son texto libre (¿qué usaría un SelfCheckGPT real en su lugar?).

## Parte 4 — La taxonomía es consultable, no prosa

Elige dos módulos que ya cursaste (por ejemplo `m11` y `m23`).

**Criterio de aceptación:** ANTES de ejecutar, escribe qué causas de
alucinación crees que mitiga cada uno. Después compara con
`causas_por_modulo("m11")` y `causas_por_modulo("m23")`, y revisa con
`modulos_de_mitigacion()` cuántos módulos del curso aparecen en el mapa. ¿Te
sorprendió alguna asignación? Esa sorpresa es el ejercicio.

---

## Pistas

<details>
<summary>Pista 1 — lo que _normalizar no hace</summary>

`_normalizar` pasa a minúsculas, recorta espacios y quita puntuación de borde.
Así `"París."` y `" parís "` cuentan como la misma respuesta… pero **no quita
tildes**: `"Paris"` (sin tilde) queda como una respuesta DISTINTA de `"parís"`.

Conteo real: `parís`×2, `paris`×1, `lyon`×1 → más común 2 de 4 →
`score = 1 - 2/4 = 0.5` → `es_sospechosa` (≥ 0.5) da **True**.

La moraleja: comparar strings no es comparar significados. El 29 resuelve esto
mismo con `_sin_tildes` para su buscador; un SelfCheckGPT real compara por
similitud semántica. Conocer el punto ciego de tu detector es parte de usarlo.

</details>

<details>
<summary>Pista 2 — consistencia ≠ verdad</summary>

```python
detectar_inconsistencia(["Lima fue fundada en 1540"] * 5)   # → 0.0
```

(La fecha real es 1535.) El detector mide **dispersión entre muestras**: si el
error es sistemático —el modelo se aprendió mal el dato— todas las muestras
coinciden y el score es 0.0, indistinguible de saberlo bien.

Contra el error sistemático la herramienta es el **grounding**: RAG con la
fuente delante (m11) y su citación/fidelidad (m20/m28). Míralo en la taxonomía:
las causas de `causas_por_modulo("m11")` son exactamente de ese tipo.

</details>

<details>
<summary>Pista 3 — la fragilidad sobre-reportada</summary>

`_normalizar` unifica `"1969"` con `"1969."` (puntuación de borde), pero
`"En 1969"` queda como `"en 1969"` — otra cadena. Resultado:
`medir_fragilidad → 2` y `es_fragil → True`, aunque las tres respuestas *dicen
lo mismo*.

Para texto libre, la versión real compara por similitud semántica (embeddings,
m11/m12) o extrae primero el dato con salida estructurada (m05) y compara el
campo, no la frase. La métrica didáctica funciona porque el ejercicio controla
el formato — en producción ese control no existe.

</details>

<details>
<summary>Pista 4 — cómo leer la taxonomía</summary>

```python
for modulo in sorted(t28.modulos_de_mitigacion()):
    print(modulo, "→", t28.causas_por_modulo(modulo))
```

No hay respuesta "correcta" que copiar aquí: el criterio es que tu predicción y
el mapa difieran en algo y puedas decir POR QUÉ el mapa asigna esa causa a ese
módulo. Si tu predicción coincide al 100%, elige dos módulos más.

</details>

---

## Reflexión

Las tres ideas del módulo, ya con números encima:

1. **La dispersión detecta la inventiva, no la mentira.** Un modelo que duda
   fabrica algo distinto en cada muestra (score alto); uno que se equivocó
   sistemáticamente miente igual todas las veces (score 0.0).
2. **Todo detector barato tiene puntos ciegos de string.** Tildes, prefijos,
   formato — conocerlos decide si el detector te protege o te da falsa
   seguridad.
3. Por eso ningún detector es un bloqueo por sí solo: son **señales que se
   apilan** (con el grounding del m11, los guardrails del m23, el filtro de
   perplejidad del 27). Igual que en el m23: alarma ≠ frontera.

**Solución:** [`soluciones/solucion_28_alucinaciones.py`](soluciones/solucion_28_alucinaciones.py)
