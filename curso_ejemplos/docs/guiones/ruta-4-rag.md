# Guion · Ruta 4 — RAG (6–7 min)

**Se publica en:** c11 · **Demo:** el re-ranker prediciendo el ranking antes de correrlo

## Gancho (0:00–0:30)

> El modelo no conoce tus documentos, tus políticas ni tu catálogo — y cuando
> no sabe, inventa con total confianza. RAG es la respuesta seria: buscar
> PRIMERO en tus datos y obligar al modelo a responder desde ahí. Esta ruta te
> lleva del RAG de tutorial al RAG que aguanta preguntas mal escritas.

## Qué vas a poder hacer (0:30–1:15)

- Montar el pipeline completo: trocear → indexar → recuperar → responder con fuente.
- Combinar BM25 + búsqueda vectorial con RRF, y re-rankear los candidatos.
- Saber CUÁNDO el multi-query ayuda y cuándo solo te cobra más (c20).
- Elegir chunk_size y overlap con criterio, no por copy-paste.

## Demo (1:15–4:30) — offline, sin cuota

```bash
cd curso_ejemplos
uv run python 12_rag_hibrido_rerank.py
```

Puntos de guion:
- ANTES de correr: «¿cuál de estos chunks debería ganar para esta pregunta?»
  (dejar 3 segundos). Correr. «¿Acertaste? Este juego de predecir es el
  ejercicio 12, y es la mejor forma de entender un ranking.»
- Enseñar el caso trampa: pregunta con sinónimo → el re-ranker didáctico da
  0.0 a todo. Pantalla partida con el playground del c12 en la web: «el
  cross-encoder sí entiende "reembolso"; el de palabras, no. Saber DÓNDE se
  rompe tu ranking es la habilidad.»
- Mover los sliders del playground de chunking del c11: «este dial lo vas a
  girar en todos tus RAG. Míralo antes de tocarlo en producción.»

## Recorrido de la ruta (4:30–5:45)

- **c11** el RAG profesional completo, con su anti-alucinación («no está en el documento» es una respuesta correcta) y cuándo NO usar RAG (CAG).
- **c12** híbrido: BM25 · coseno · RRF · re-ranking — la sala de máquinas.
- **c20** multi-query y RAG-Fusion, con su costo real. **c24** vector DBs en producción: dedup, IVFFlat, recall↔velocidad.

## Cierre (5:45–6:15)

> Cuando termines esta ruta vas a poder mirar el RAG de cualquier empresa y
> decir exactamente dónde se le escapan las respuestas. Empieza por el c11.

**CTA:** `/concepto/11-rag-profesional`
