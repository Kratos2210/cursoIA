# Feature Specification: Enlace al documento en la cita

**Feature Branch**: `004-cita-con-enlace`

**Created**: 2026-09-15

**Status**: Draft

**Input**: Rosa: "los clientes preguntan de dónde saqué el precio; ¿se puede mandar el link?"

> Documento de **ejemplo** para la [guía de specs para apps de IA](../../guia-spec-para-apps-de-ia.md).
>
> **Contraste deliberado**: el sistema lleva dos meses en producción. Compara el tamaño de este
> spec con el de [`spec.md`](spec.md). Es media página, y no porque esté peor escrito: la
> constitución ya existe, los presupuestos se heredan y el corpus está definido. Lo único que
> este spec añade y el greenfield no tiene es la sección de **no-regresión**.

---

## Contexto

El asistente ya cita la fuente en texto ("según la lista de precios del 12 de septiembre"), pero
el cliente no puede comprobarlo. Rosa reporta que unas 5 veces por semana alguien pregunta si
puede ver el documento. Hoy ella lo manda a mano.

---

## User Story 1 - Ver el documento citado (Priority: P1)

Cuando el asistente responde con un dato del catálogo o de las políticas, el cliente recibe
además un enlace público al documento del que salió, y puede abrirlo.

**Why this priority**: es la única historia de esta feature.

**Independent Test**: se pregunta por un precio; la respuesta incluye un enlace que abre el
catálogo vigente.

**Acceptance Scenarios**:

1. **Given** una respuesta con un dato del corpus, **When** el asistente la envía, **Then**
   incluye un enlace al documento citado.
2. **Given** los 48 casos no negativos del conjunto dorado, **When** se ejecuta la evaluación,
   **Then** el 100% de los enlaces resuelven al documento **correcto** (no a otro del corpus).
3. **Given** una respuesta de abstención, **When** el asistente la envía, **Then** no incluye
   ningún enlace.

---

## Requirements

- **FR-101**: El sistema MUST incluir, en toda respuesta que cite una fuente, un enlace público
  y estable al documento citado.
- **FR-102**: El enlace MUST apuntar a la **versión vigente** del documento, la misma de la que
  salió el dato.
- **FR-103**: El sistema MUST NO incluir enlaces en respuestas de abstención ni en escalados.
- **FR-104**: Los documentos publicados MUST NO contener información interna (márgenes, costos
  de proveedor, datos de otros clientes).

---

## No-regresión *(la sección que un spec de feature siempre necesita)*

Qué **no** debe romperse. Se verifica con la misma corrida de evals, antes y después.

- El conjunto dorado (72 casos a hoy) MUST seguir superando sus umbrales vigentes: exactitud
  ≥90%, citación ≥95%, precios con tolerancia cero.
- La tasa de abstención de los casos negativos MUST seguir en **100%**.
- El coste por conversación MUST NO subir más de **USD 0.002** (el techo de USD 0.03 del
  principio II no se toca).
- La latencia p95 MUST seguir por debajo de 4 s.

> **Por qué esto no es burocracia.** El enlace se añade tocando la plantilla de la respuesta, que
> es también donde vive la instrucción de abstenerse. Un cambio de dos líneas ahí puede hacer que
> el sistema deje de decir "no sé" — y no hay compilador que avise. La corrida antes/después es
> lo único que lo detecta.

---

## Success Criteria

- **SC-101**: Rosa deja de enviar documentos a mano (hoy: ~5/semana), medido en un mes.
- **SC-102**: Cero reportes de enlaces que apunten al documento equivocado.

---

## Assumptions

- Los documentos del corpus se pueden publicar tal cual: son catálogo, políticas y horarios,
  información que el negocio ya da a cualquiera que pregunte. FR-104 lo verifica antes de
  publicar.
- Se hereda la constitución del proyecto sin enmiendas.
- **Fuera de alcance**: enlaces a fragmentos concretos dentro del documento (anclas). Se enlaza
  el documento completo.
