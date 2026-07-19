# Guion · Ruta 7 — Proyectos y casos reales (6–7 min)

**Se publica en:** c35 · **Demo:** el eval del caso retail cazando al asistente descuidado

## Gancho (0:00–0:30)

> Antes de construir un agente hay una pregunta más cara que todo el código:
> ¿esto SE DEBE automatizar? Esta ruta empieza donde empieza el trabajo real —
> con el proceso, no con el prompt — y termina con dos proyectos completos en
> tu portafolio: un capstone de gobierno de datos y un asistente de retail con
> su eval, su guardrail y su honestidad medida con números.

## Qué vas a poder hacer (0:30–1:15)

- Hacer discovery: ficha AS-IS, TO-BE, la escalera de autonomía y decidir el peldaño correcto (c35).
- Especificar ANTES de codear con Spec-Driven Development (c19) — el verificador de este curso nació así.
- Construir el capstone: casi todo el curso en un solo sistema auditable (c18).
- Defender un caso real de retail: ETL sucio, filtros duros, grounding de precios y un eval que no perdona (c29).

## Demo (1:15–4:30) — offline

```bash
cd curso_ejemplos
uv run python 29_caso_retail.py
```

Puntos de guion:
- «Mira la petición: "un collar de zircón por menos de 10 soles". No hay nada
  que cumpla eso. ¿Qué hace un asistente honesto?» → mostrar la respuesta «no
  tengo» pasando el guardrail. «No responder ES una respuesta válida.»
- Enseñar el marcador final: honesto 1.0 vs descuidado 0.75. «El descuidado no
  es un hombre de paja: es EXACTAMENTE el asistente que sale si no pones el
  presupuesto como filtro duro. El eval lo caza con la misma métrica.»
- «Todo el flujo — catálogo sucio de Shopify incluido — está en el repo, con
  127 tests. Y la versión LLMOps completa en proyecto_retail/.»

## Recorrido de la ruta (4:30–5:45)

- **c35** discovery de procesos: qué automatizar y hasta qué peldaño.
- **c19** SDD: spec → plan → tareas → implementación (con artefactos reales del repo).
- **c18** capstone de gobierno de datos. **c29** el caso retail que acabas de ver.

## Cierre (5:45–6:15)

> Los proyectos de esta ruta son los que pones en el CV — y las preguntas de
> esta ruta son las que te hacen en la entrevista. Empieza por el c35.

**CTA:** `/concepto/35-discovery-de-procesos`
