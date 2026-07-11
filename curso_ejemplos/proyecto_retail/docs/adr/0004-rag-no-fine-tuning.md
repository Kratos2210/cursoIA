# ADR-0004 — El catálogo va por recuperación (RAG), no por fine-tuning

- **Estado:** aceptado
- **Fecha:** 2026-07-11
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El asistente necesita conocer el catálogo: qué productos hay, a qué precio, en
promo o no, disponibles o no. ¿Dónde vive ese conocimiento? Dos caminos:

1. **Fine-tuning:** afinar un modelo con los productos y precios de este mes.
2. **Recuperación (RAG):** el catálogo es un dato externo que se consulta al
   responder; el modelo solo entiende la petición y redacta.

El catálogo real cambia **a diario**: colecciones por temporada, promos 2x1 que
entran y salen, stock que se agota. Afinar un modelo con los precios de julio es
fabricar un mentiroso para agosto.

## Decisión

> El catálogo se **recupera** en cada consulta (RAG); nunca se hornea en los
> pesos del modelo. El LLM solo pone la comprensión y la prosa; el catálogo pone
> los hechos (precio, stock, promo). La regla de oro: **precio y stock jamás
> salen del modelo**.

Es la biblioteca, no la escuela (m21): el conocimiento que cambia va al índice,
no al entrenamiento.

## Consecuencias

- Un cambio de precio se refleja al instante actualizando el catálogo, sin
  reentrenar nada.
- El modelo se puede cambiar (Groq → Gemini → local) sin perder el catálogo: son
  piezas independientes.
- El fine-tuning queda para lo que SÍ es comportamiento estable: el tono de la
  vendedora. Y eso se resuelve antes con un prompt (ver `prompts/vendedora.yaml`)
  que con fine-tuning — el espectro de adaptación del m21 dice bajar de escalón
  solo cuando el anterior se queda corto.
- En Perú, un precio inventado no es una anécdota: es un reclamo, y un problema
  con Indecopi. Esta decisión es también de cumplimiento, no solo técnica.
