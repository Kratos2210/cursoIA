# Solución · Ejercicio 11 — RAG: k, documentos nuevos y anti-alucinación

> ⚠️ No leas esto hasta haberlo intentado.

Este ejercicio no tiene un `.py` de solución: sus respuestas son **análisis**,
no código. Los cambios que pide son de tres líneas cada uno.

---

## Parte 1 — Juega con k

### El cambio

```python
retriever = vs.as_retriever(search_kwargs={"k": 1})   # y luego 6
```

### Qué pasa

Con `k=1`, la pregunta **«¿Quién controla las llaves de API?»** se responde bien
(el chunk de Seguridad gana claramente). Pero prueba con una pregunta cuya
respuesta esté repartida, o cuyo mejor chunk sea el título:

Con `k=1`, cualquier pregunta cuyo chunk correcto quede **segundo** se responde
mal — y el modelo no tiene forma de saberlo: recibió un contexto, y respondió
con él. El modo de fallo no es "no sé": es una respuesta segura y equivocada.

### ¿Por qué no `k=100`?

Tres razones. La tercera es la que sorprende:

1. **Coste.** Cada fragmento son tokens de entrada, en cada pregunta, para siempre.
2. **Contexto.** Hay un límite de tokens. Con muchos documentos, no cabe.
3. **Ruido.** Un modelo con 100 fragmentos, de los que 98 son irrelevantes,
   responde **peor** que con 2 buenos. Es el fenómeno *"lost in the middle"*:
   los modelos atienden bien al principio y al final del contexto, y se pierden
   lo del medio.

> **Más contexto no es más información. Es más ruido, y encima lo pagas.**

Y aquí está la conexión con el TEMA 12: si el ruido es el problema, la solución
no es traer menos fragmentos — es **traer los correctos primero**. Eso es el
re-ranking. `k` alto + re-ranker que recorta a 3 le gana a `k=3` a secas.

---

## Parte 2 — Añade un documento

Tras añadir el párrafo de vacaciones, `datos_rag.txt` pasa de **7 a 8 fragmentos**.

### El test que se rompe

```
FAILED tests/test_util.py::TestTrocearParrafos::test_datos_rag_reales
    assert 8 == 7
```

### ¿El test está mal, o rompiste algo?

**El test está bien.** Hizo exactamente su trabajo: te avisó de que el corpus
cambió. Un test que se rompe cuando cambias los datos que describe no es un test
frágil: es un test que funciona.

Lo correcto es actualizarlo a 8 **conscientemente**, no a ciegas:

```python
def test_datos_rag_reales(self, chunks_datos_rag):
    assert len(chunks_datos_rag) == 8   # 7 originales + política de vacaciones
```

El reflejo de "cambio el número para que pase" es peligroso. La pregunta correcta
siempre es: *¿esperaba yo este cambio?* Aquí sí. Si un día ese test salta de 8 a
5 sin que tocaras el archivo, tendrás un problema de verdad — y lo sabrás.

---

## Parte 3 — Ataca la anti-alucinación

### Los tres ataques, de menos a más eficaz

**1. Plausible pero ausente** — *«¿Cuánto cuesta el plan Enterprise?»*
Suele funcionar bien: no se recupera nada parecido y el modelo admite que no sabe.
La anti-alucinación **aguanta**.

**2. Parcialmente presente** — *«¿Aceptan pago con tarjeta Visa en cuotas?»*
Aquí empieza a temblar. El chunk de Formas de pago **sí** se recupera (habla de
cuotas y de medios de pago). El modelo tiene contexto relevante y a menudo
responde algo ambiguo — «sí, ofrecemos pago en dos cuotas» — sin señalar que
**Visa no aparece por ningún lado**. No inventa un hecho, pero deja que asumas uno.

**3. Premisa falsa** — *«¿Por qué la política de reembolsos es de 14 días?»*
El ataque más eficaz. El chunk de reembolsos se recupera perfectamente (dice
**7 días**). Y muchos modelos, en vez de corregirte, **aceptan tu premisa y la
racionalizan**.

> Un RAG que "no alucina" porque tiene el contexto correcto puede seguir
> mintiendo si tú le regalas la mentira dentro de la pregunta.

### El prompt endurecido

```python
prompt = ChatPromptTemplate.from_template(
    "Eres un asistente que responde EXCLUSIVAMENTE con el contexto dado.\n"
    "Reglas estrictas:\n"
    "1. Si la respuesta no está en el contexto, responde exactamente:\n"
    "   'No tengo esa información en la documentación.'\n"
    "2. Si la pregunta da por hecho algo que CONTRADICE el contexto,\n"
    "   corrige la premisa ANTES de responder.\n"
    "3. Si el contexto responde solo en parte, di explícitamente qué parte\n"
    "   NO está cubierta.\n"
    "4. No uses conocimiento previo. No supongas. No completes.\n\n"
    "Contexto:\n{context}\n\nPregunta: {question}"
)
```

- La **regla 2** ataca la premisa falsa. Casi nadie la escribe.
- La **regla 3** ataca el caso "parcialmente presente".

### La advertencia honesta

Esto **reduce** las alucinaciones. No las elimina. Ninguna instrucción lo hace.

Y fíjate en la trampa de haberlo "verificado" con tres preguntas a mano: no
sabes si el prompt nuevo mejoró el sistema o si simplemente acertó esas tres.
Quizá empeoró las otras veinte que no probaste.

Para saberlo hace falta un dataset y una métrica que puedas volver a correr tras
cada cambio. Eso es exactamente el **TEMA 16** (`16_evaluacion.py`), y es la
razón de que exista.

---

## La lección que se lleva a producción

Cuando un RAG responde mal, el reflejo es tocar el prompt. Casi siempre el
problema está **antes**. Depura en este orden:

1. **¿Está la información en el documento?** (Sorprende cuántas veces no.)
2. **¿La recupera el retriever?** — imprime el contexto, no lo supongas:
   ```python
   print(unir(retriever.invoke(pregunta)))
   ```
3. **¿La usa bien el modelo?**

Solo el paso 3 es un problema de prompt. Y es, con diferencia, el menos frecuente.
