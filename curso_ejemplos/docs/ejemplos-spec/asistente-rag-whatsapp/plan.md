# Implementation Plan: Asistente de consultas por WhatsApp

**Branch**: `001-asistente-whatsapp` | **Date**: 2026-07-20 | **Spec**: [`spec.md`](spec.md)

> Documento de **ejemplo** para la [guía de specs para apps de IA](../../guia-spec-para-apps-de-ia.md).
> Aquí —y **solo** aquí— aparecen las decisiones técnicas. El spec no nombra ni una librería.

---

## Summary

Sistema RAG sobre el corpus del negocio (catálogo, políticas, horarios), expuesto por la API de
WhatsApp Business. La restricción que gobierna todo el diseño es **FR-010: menos de USD 0.03 por
conversación**, que elimina de entrada las arquitecturas de varias llamadas al modelo por
mensaje. El segundo eje es la **abstención** (FR-006 a FR-009), que se resuelve con un umbral
de recuperación explícito antes de llamar al modelo, no pidiéndole al modelo que se porte bien.

## Technical Context

**Orquestación**: n8n — el negocio ya lo usa y Rosa necesita poder ver el flujo.

**Framework de IA**: LangChain (Python) para la cadena de recuperación y generación, expuesta
como servicio HTTP que n8n invoca.

**Almacenamiento**: Supabase (PostgreSQL + pgvector) para el corpus indexado y el registro de
conversaciones.

**Corpus**: 3 documentos (catálogo, políticas, horarios y zonas) sincronizados desde la hoja de
cálculo de Rosa.

**Modelo de generación**: un modelo pequeño de la gama económica, con el modelo intermedio como
alternativa si la calidad no alcanza el umbral.

> ⚠️ **El identificador exacto del modelo y su precio por millón de tokens se rellenan
> verificándolos contra la documentación oficial del proveedor el día de escribir este plan.**
> Nunca de memoria: ambos cambian cada pocos meses y un precio caducado invalida el cálculo de
> FR-010 entero.

**Canal**: API de WhatsApp Business (Cloud API).

**Evaluación**: script propio que corre el conjunto dorado y reporta exactitud, tasa de
citación, tasa de abstención y coste medio.

**Objetivos de desempeño**: < 4 s p95 (FR-011) · < USD 0.03 por conversación (FR-010).

**Escala**: ~40 conversaciones/día, picos de 15/hora los fines de semana. Es un volumen
pequeño: la arquitectura se optimiza para **coste y simplicidad operativa**, no para
throughput.

---

## Decisiones técnicas y alternativas descartadas

### D1. Una sola llamada al modelo por mensaje

**Decisión**: recuperar fragmentos → una única llamada de generación con las fuentes en el
contexto. Sin cadena de refinamiento, sin agente que itere, sin llamada previa de
reformulación.

**Por qué**: es aritmética de FR-010. Con tres centavos por conversación y una media de 3
mensajes por conversación, el presupuesto por mensaje es de un centavo. Dos llamadas al modelo
por mensaje lo agotan antes de contar la recuperación.

**Descartado**: agente con herramientas (más flexible, 3-5× el coste y latencia impredecible);
cadena *refine* sobre varios fragmentos (mejor calidad en respuestas largas, pero aquí las
respuestas son de dos frases).

### D2. Umbral de recuperación como puerta, antes del modelo

**Decisión**: si el mejor fragmento recuperado no supera un umbral de similitud, **no se llama
al modelo**: se devuelve directamente la respuesta de abstención.

**Por qué**: FR-006 exige abstención fiable, y pedirle al modelo "si no sabes, dilo" es una
instrucción que cumple *casi* siempre — y el escenario 3 de la Historia 2 exige **100%**. Una
puerta determinista antes de la llamada sí da el 100%, y además ahorra el coste de la llamada
en los casos que iban a fallar. El umbral concreto se calibra contra los 12 casos negativos del
conjunto dorado.

**Descartado**: confiar la abstención al prompt (no alcanza el 100%); un clasificador
adicional (otra llamada, rompe D1).

### D3. Chunking por sección semántica, no por tamaño fijo

**Decisión**: cada producto del catálogo es un fragmento; cada política, un fragmento.

**Por qué**: partir por tamaño fijo corta filas del catálogo por la mitad y produce fragmentos
con medio precio. Los documentos ya tienen estructura natural; usarla es gratis y elimina toda
una clase de fallos.

**Descartado**: chunks de 512 tokens con solape (el estándar por defecto, malo para datos
tabulares).

### D4. Sin re-ranker

**Decisión**: recuperación vectorial directa, los 4 mejores fragmentos al contexto.

**Por qué**: un re-ranker mejoraría la precisión, pero es una segunda llamada a modelo por
mensaje y no cabe en FR-010. Con un corpus de tres documentos pequeños, la recuperación simple
debería bastar. **Se revisa si la eval no alcanza el 90% de FR/Historia 1** — y si hiciera
falta, la conversación es con el cliente sobre el techo de coste (principio II), no una
decisión que tomemos por nuestra cuenta.

### D5. La cita se construye en código, no la escribe el modelo

**Decisión**: el modelo genera la respuesta; el sistema **añade** la línea de fuente a partir de
los metadatos del fragmento que efectivamente se recuperó.

**Por qué**: FR-004 exige que la cita sea correcta, y un modelo al que le pides que cite a veces
cita el documento equivocado o inventa la fecha. Si la cita la pone el código con el metadato
real, es correcta por construcción. Es la diferencia entre esperar un comportamiento y
garantizarlo.

### D6. Frescura por sincronización programada

**Decisión**: un flujo de n8n reindexa el corpus cada 6 horas y marca la fecha de vigencia; si
el catálogo tiene más de 7 días, la respuesta lo advierte.

**Por qué**: FR-012 pide menos de 24 h; cada 6 horas da margen de sobra y evita construir
webhooks sobre una hoja de cálculo.

---

## Constitution Check

*GATE: debe pasar antes de implementar y volver a revisarse al terminar.*

| Principio | Cumplimiento | Cómo |
|---|---|---|
| **I. Ninguna afirmación sin fuente** | ✅ | D5 construye la cita desde el metadato real, no desde el modelo |
| **II. Techo de coste** | ✅ | D1 (una llamada) y D4 (sin re-ranker) se derivan directamente del techo |
| **III. Nada terminado sin medición** | ✅ | El conjunto dorado es la tarea T004, **anterior** a la implementación (ver `tasks.md`) |
| **IV. Datos del cliente** | ✅ | Retención cero contratada con el proveedor; teléfono seudonimizado antes de registrar (FR-014) |
| **V. Degradación explícita** | ✅ | D2 da abstención determinista; el fallo del proveedor cae al escenario 4 de la Historia 2 |

**Desviaciones**: ninguna.

**Riesgo abierto**: si la eval no alcanza el 90% sin re-ranker (D4), hay conflicto entre el
principio I (calidad de la fuente) y el II (coste). Se resuelve **con el cliente**, renegociando
el techo o recortando el alcance — no relajando el umbral en silencio, que sería exactamente el
antipatrón que el Concepto 19 describe con el verificador.

---

## Estructura del proyecto

```text
asistente-whatsapp/
├── servicio/              # Servicio Python (LangChain)
│   ├── recuperacion.py    # Indexado, búsqueda y umbral (D2, D3)
│   ├── generacion.py      # La única llamada al modelo (D1) + citación (D5)
│   ├── clasificacion.py   # Reclamo / intención de compra → escalado (FR-007, FR-009)
│   └── registro.py        # Trazas y coste (FR-014)
├── evals/
│   ├── conjunto_dorado.jsonl   # Los 60 casos etiquetados por Rosa
│   └── correr_evals.py         # Exactitud, citación, abstención, coste
├── flujos-n8n/            # Webhook de WhatsApp, sincronización del corpus, escalado
└── corpus/                # Documentos versionados con su responsable
```

**Decisión de estructura**: el servicio de IA se separa de n8n a propósito. n8n orquesta
(recibe, enruta, escala, notifica); el servicio hace la parte que necesita ser **testeable con
el conjunto dorado sin pasar por WhatsApp**. Meter la cadena dentro de un nodo de n8n haría
imposible correr las evals de forma automática, y sin evals no hay principio III.
