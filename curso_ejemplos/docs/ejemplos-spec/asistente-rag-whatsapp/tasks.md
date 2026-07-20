# Tasks: Asistente de consultas por WhatsApp

**Input**: [`spec.md`](spec.md) y [`plan.md`](plan.md)

> Documento de **ejemplo** para la [guía de specs para apps de IA](../../guia-spec-para-apps-de-ia.md).
>
> **Lo que hay que mirar en este archivo**: el conjunto dorado (T004–T005) está **antes** de
> escribir una línea del sistema. Ese orden no es cosmético — es lo que impide construir el
> examen mirando las respuestas del alumno.

**Formato**: `[ID] [P?] [Historia] Descripción` · `[P]` = paralelizable (archivos distintos, sin
dependencias entre sí).

---

## Fase 1: Setup

- [ ] T001 Crear la estructura de `plan.md` y el proyecto Python con `uv`
- [ ] T002 [P] Provisionar Supabase con la extensión pgvector y el esquema de conversaciones
- [ ] T003 [P] Registrar el número de WhatsApp Business y validar el webhook contra n8n

---

## Fase 2: Criterio de aceptación (BLOQUEANTE)

**Propósito**: existir antes que el sistema. Ninguna historia puede darse por terminada sin esto.

**⚠️ Ninguna tarea de la Fase 4 en adelante empieza hasta que la Fase 2 esté cerrada.**

- [ ] T004 Extraer y anonimizar 60 mensajes reales de los últimos 3 meses, con la cobertura que
      fija el spec: 24 informativas, 24 de catálogo/precios, 12 negativos
- [ ] T005 **Sesión de etiquetado con Rosa** (4 h): respuesta esperada y documento fuente correcto
      para cada caso → `evals/conjunto_dorado.jsonl`
- [ ] T006 Implementar `evals/correr_evals.py`: reporta exactitud, tasa de citación, tasa de
      abstención y coste medio por conversación
- [ ] T007 Correr las evals contra un sistema vacío y **verificar que falla**. Si no falla, el
      conjunto o el medidor están mal — un examen que aprueba sin alumno no evalúa nada

**Checkpoint**: existe una definición ejecutable de "listo". Ahora se puede construir.

---

## Fase 3: Fundamentos (bloquea todas las historias)

- [ ] T008 Sincronización del corpus desde la hoja de cálculo → `corpus/` versionado, con
      responsable y fecha de vigencia (FR-012, D6)
- [ ] T009 Indexado con chunking por sección semántica en `servicio/recuperacion.py` (D3)
- [ ] T010 [P] Registro de trazas y coste por conversación en `servicio/registro.py`, con el
      teléfono seudonimizado (FR-014)
- [ ] T011 [P] Flujo n8n base: recibir mensaje de WhatsApp → llamar al servicio → responder

**Checkpoint**: hay corpus indexado y un mensaje puede dar la vuelta completa.

---

## Fase 4: Historia 1 — Responder citando la fuente (P1) 🎯 MVP

**Objetivo**: responder consultas informativas y de catálogo con el dato correcto y su fuente.

**Test independiente**: las 48 preguntas no negativas del conjunto dorado se responden sin
intervención humana, ≥90% correctas y ≥95% citadas.

- [ ] T012 [US1] Búsqueda vectorial sobre el corpus, 4 mejores fragmentos (D4)
- [ ] T013 [US1] Única llamada de generación con las fuentes en contexto en
      `servicio/generacion.py` (D1)
- [ ] T014 [US1] Construcción de la cita **en código** desde los metadatos del fragmento
      recuperado (D5, FR-004)
- [ ] T015 [US1] Aviso de catálogo con más de 7 días de antigüedad (edge case de frescura)
- [ ] T016 [US1] Mensaje de identificación como asistente automático al abrir conversación (FR-005)
- [ ] T017 [US1] **Correr las evals**: exactitud ≥90%, citación ≥95%, precios con tolerancia cero
- [ ] T018 [US1] Verificar el coste medido contra FR-010 (< USD 0.03). Si no cabe, revisar D1/D4
      antes de seguir — no al final

**Checkpoint**: MVP demostrable a Rosa. Si el coste o la exactitud no dan, **se para aquí** y se
revisa el plan; seguir construyendo sobre un MVP que no cumple solo hace más caro el arreglo.

---

## Fase 5: Historia 2 — Abstenerse y escalar (P2)

**Objetivo**: no improvisar nunca. Los 12 casos negativos al 100%.

**Test independiente**: los 12 negativos del conjunto dorado se abstienen o escalan
correctamente, sin una sola respuesta inventada.

- [ ] T019 [US2] Puerta de umbral de relevancia **antes** de llamar al modelo (D2, FR-006)
- [ ] T020 [US2] Calibrar el umbral contra los 12 casos negativos hasta el 100% de abstención,
      verificando que no rompe la exactitud de la Historia 1
- [ ] T021 [P] [US2] Clasificación de reclamo / devolución → escalado sin responder en
      `servicio/clasificacion.py` (FR-007)
- [ ] T022 [P] [US2] Detección de intención de compra → escalado (FR-009)
- [ ] T023 [US2] Tratar corpus y mensaje del cliente como datos, nunca como instrucciones
      (FR-015); verificar contra los 2 casos de inyección del conjunto dorado
- [ ] T024 [US2] Negativa a revelar instrucciones internas
- [ ] T025 [US2] Degradación ante caída del proveedor: avisar y encolar para Rosa (principio V)
- [ ] T026 [US2] Flujo n8n de escalado: marcar pendiente y notificar a Rosa
- [ ] T027 [US2] **Correr las evals completas**: abstención 100% y **sin regresión** en la
      Historia 1

**Checkpoint**: el sistema se puede dejar encendido sin vigilancia. Aquí es donde deja de ser
una demo.

---

## Fase 6: Historia 3 — Panel de pendientes (P3)

**Objetivo**: que Rosa responda los escalados y pueda marcar respuestas incorrectas.

- [ ] T028 [US3] Vista de conversaciones escaladas, con la pregunta y las fuentes recuperadas
- [ ] T029 [US3] Responder desde el panel → el mensaje llega a la conversación de WhatsApp
- [ ] T030 [US3] Botón de "respuesta incorrecta" → cola de revisión del conjunto dorado
- [ ] T031 [US3] Incorporar los casos revisados al `conjunto_dorado.jsonl`

---

## Fase 7: Puesta en producción

- [ ] T032 Automatizar la corrida de evals ante cualquier cambio de prompt, modelo o corpus
      (FR-013). Sin esto, el principio III se cumple solo mientras alguien se acuerde
- [ ] T033 Confirmar por escrito la retención cero con el proveedor del modelo (principio IV)
- [ ] T034 Panel de coste semanal por conversación (FR-010, principio II)
- [ ] T035 Resolver con el cliente FR-016 y FR-017, que siguen marcados `[NEEDS CLARIFICATION]`
- [ ] T036 Constitution Check final sobre lo construido
- [ ] T037 Piloto de 2 semanas con Rosa antes de abrirlo a todo el tráfico

---

## Dependencias

- **Fase 2 bloquea todo lo demás.** Es la inversión del orden habitual y el punto entero de este
  ejemplo.
- Fase 3 bloquea las historias.
- Historia 1 antes que la 2 solo porque hace falta responder para poder abstenerse; en riesgo la
  2 es más importante.
- Historia 3 es independiente: puede ir en paralelo a la 2 si hay más de una persona.

## Estrategia

**MVP**: Fases 1-4 y parar a validar con Rosa contra las evals, no contra la impresión de que
"responde bien". Si la Fase 4 no cumple coste o exactitud, el problema es del plan y se arregla
en el plan.

**Nunca**: bajar un umbral del spec para que las evals pasen. Si el umbral era el correcto, el
que está mal es el sistema; si estaba mal, se cambia el spec **explícitamente y con el cliente**,
y se regeneran plan y tasks. Ese es el principio del Concepto 19: el spec dice quién tiene
razón.
