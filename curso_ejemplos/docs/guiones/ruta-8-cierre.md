# Guion · Ruta 8 — Cierre: AI Engineer (5–6 min)

**Se publica en:** c26 · **Demo:** el mismo RAG del curso corriendo en LlamaIndex

## Gancho (0:00–0:30)

> Ya sabes construir, evaluar y desplegar. Falta lo último que separa a un
> técnico de un ingeniero: el MAPA. Saber qué framework elegir mañana, leer un
> repo ajeno escrito con otra librería, y contestar «¿por qué LangChain y no
> X?» sin ponerte nervioso. Este cierre te da el mapa — y la prueba de que las
> ideas viajan entre frameworks.

## Qué vas a poder hacer (0:30–1:10)

- Situar LangChain frente a LlamaIndex, CrewAI y OpenAI Agents SDK: qué optimiza cada uno y a qué costo.
- Leer y correr el MISMO RAG y el MISMO patrón supervisor del curso en otros dos frameworks.
- Cerrar el curso con el examen final y tu constancia — y con la entrevista de trabajo ensayada.

## Demo (1:10–3:30)

```bash
cd curso_ejemplos
uv run --extra llamaindex python frameworks/rag_llamaindex.py
```

Puntos de guion:
- «Mismo `datos_rag.txt`, misma pregunta, otra librería. Fíjate en lo que NO
  cambió: cargar → indexar → consultar. Cambió la ergonomía, no el concepto.»
- Abrir `frameworks/crew_crewai.py` en el editor (sin correrlo): «y aquí el
  supervisor del c15 descrito como ROLES. Más alto nivel, menos control — esa
  es siempre la moneda de cambio.»
- «La lección del c26 no es cuál es mejor: es que tú ya piensas en los
  CONCEPTOS, y por eso ningún framework nuevo te va a asustar.»

## Recorrido del cierre (3:30–4:30)

- **c26** el mapa del ecosistema, comparativa honesta con criterios.
- **c32** LlamaIndex y CrewAI ejecutables (lo que viste).
- Y los recursos finales: **examen** (80 preguntas), **entrevista** (las preguntas reales con sus respuestas), **constancia** al 100%.

## Cierre (4:30–5:00)

> Si llegaste hasta aquí, ya no eres alguien que «sabe LangChain»: eres alguien
> que sabe construir sistemas de IA y explicar por qué los construyó así. Rinde
> el examen, imprime tu constancia — y sal a cobrar por esto.

**CTA:** `/concepto/26-mapa-del-ecosistema`
