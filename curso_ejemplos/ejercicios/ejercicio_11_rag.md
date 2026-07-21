# Ejercicio 11 — RAG: k, documentos nuevos y anti-alucinación

**Ejemplo base:** `11_rag.py` · **Gasta cuota:** sí (embeddings + 1 llamada por pregunta)

> ⚠️ **Este es el único ejercicio que Groq no salva del todo.** Puedes mover el
> *chat* a Groq (`LLM_PROVIDER=groq`), pero **Groq no ofrece
> embeddings** y el RAG los necesita: seguirías gastando `GOOGLE_API_KEY` solo
> para vectorizar.
>
> Salida sin cuota — calcúlalos en tu máquina:
> `uv sync --extra emb` y `EMBEDDINGS_PROVIDER=fastembed` en el `.env`.
>
> Y ojo, porque esto muerde en producción: cambiar de modelo de embeddings **no**
> es cambiar de proveedor de chat. **Invalida el índice entero**, porque los
> vectores viejos y los nuevos viven en espacios distintos. Compararlos no da un
> resultado peor: da un resultado sin sentido. Hay que reindexar.

## Contexto

`11_rag.py` indexa `datos_rag.txt` (7 fragmentos), recupera los `k=2` más
parecidos y responde **solo** con ellos. La regla anti-alucinación vive en el
prompt: *"Responde SOLO con el contexto. Si la respuesta no está, dilo."*

Ese prompt es una promesa. Vas a comprobar si se cumple.

## Parte 1 — Juega con k

Cambia `k` a `1` y luego a `6`. Lanza siempre las mismas tres preguntas del ejemplo.

**Criterio de aceptación:** encuentra **una pregunta que se responde bien con
`k=2` pero mal con `k=1`**, y explica por qué. Después responde: si subir `k`
solo puede ayudar, ¿por qué no ponemos `k=100` y nos olvidamos?

## Parte 2 — Añade un documento

Añade a `datos_rag.txt` un párrafo nuevo:

```text
Política de vacaciones:
Cada consultor tiene 30 días calendario de vacaciones al año. Deben solicitarse
con 15 días de anticipación y no pueden acumularse más de 2 periodos.
```

**Criterio de aceptación:**
1. `¿Cuántos días de vacaciones hay?` se responde correctamente.
2. El test `test_datos_rag_reales` de `tests/test_util.py` ahora **falla**
   (esperaba 7 fragmentos). Arréglalo. Piensa antes de cambiar el número:
   ¿es el test el que está mal, o acabas de romper algo?

## Parte 3 — Ataca la anti-alucinación

Consigue que el modelo **se invente una respuesta** pese al prompt. Ideas:

- Pregunta algo *plausible pero ausente*: «¿Cuánto cuesta el plan Enterprise?»
- Pregunta algo *parcialmente presente*: «¿Aceptan pago con tarjeta Visa en cuotas?»
  (el documento habla de cuotas, y de Yape/Plin, pero **no** de Visa).
- Pregunta con una **premisa falsa**: «¿Por qué la política de reembolsos es de
  14 días?» (son 7).

**Criterio de aceptación:** documenta **al menos un caso** donde el modelo no
admita que no sabe. Después, mejora el prompt para que sí lo haga, y comprueba
que las tres preguntas originales siguen respondiéndose bien.

---

## Pistas

<details>
<summary>Pista 1 — por qué no k=100</summary>

Tres razones, y la tercera es la que sorprende:

1. **Coste**: cada fragmento son tokens de entrada que pagas en cada pregunta.
2. **Contexto**: hay un límite de tokens; con muchos documentos, no cabe.
3. **Ruido** (la importante): un modelo con 100 fragmentos, de los que 98 son
   irrelevantes, responde **peor** que con 2 buenos. Es el fenómeno *"lost in
   the middle"*: los modelos atienden bien al principio y al final del contexto,
   y se pierden lo del medio.

Más contexto no es más información. Es más ruido, y hay que pagarlo.

</details>

<details>
<summary>Pista 2 — la premisa falsa</summary>

«¿Por qué la política de reembolsos es de 14 días?» es el ataque más eficaz.
El fragmento de reembolsos **sí** se recupera (habla de reembolsos), así que el
modelo tiene contexto relevante… y muchos modelos aceptan la premisa del usuario
y racionalizan el 14 en vez de corregirlo.

Un RAG que "no alucina" porque tiene el contexto correcto puede seguir mintiendo
si tú le regalas la mentira dentro de la pregunta.

</details>

<details>
<summary>Pista 3 — endurecer el prompt</summary>

```python
prompt = ChatPromptTemplate.from_template(
    "Eres un asistente que responde EXCLUSIVAMENTE con el contexto dado.\n"
    "Reglas estrictas:\n"
    "1. Si la respuesta no está en el contexto, responde exactamente: "
    "   'No tengo esa información en la documentación.'\n"
    "2. Si la pregunta da por hecho algo que CONTRADICE el contexto, "
    "   corrige la premisa antes de responder.\n"
    "3. No uses conocimiento previo. No supongas. No completes.\n\n"
    "Contexto:\n{context}\n\nPregunta: {question}"
)
```

La regla 2 es la que ataca la premisa falsa, y casi nadie la escribe.

Aun así: **esto reduce las alucinaciones, no las elimina.** Por eso el TEMA 16
existe — necesitas un dataset y una métrica para saber cuánto mejoró de verdad,
en vez de fiarte de tres pruebas a mano.

</details>

---

## Reflexión

Cuando un RAG responde mal, el reflejo es tocar el prompt. Casi siempre el
problema está **antes**: el retriever no trajo el fragmento correcto, y ningún
prompt del mundo arregla eso. Depura en este orden:

1. ¿Está la información en el documento?
2. ¿La recupera el retriever? (imprime el contexto, no lo supongas)
3. ¿La usa bien el modelo?

Solo el paso 3 es un problema de prompt. Y es el menos frecuente.

**Solución:** [`soluciones/solucion_11_rag.md`](soluciones/solucion_11_rag.md)
