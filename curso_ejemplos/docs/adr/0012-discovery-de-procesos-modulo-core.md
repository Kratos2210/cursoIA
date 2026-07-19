# ADR-0012 — Discovery de procesos: módulo core web abriendo el Nivel 7

- **Estado:** aceptado
- **Fecha:** 2026-07-19
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El curso enseña a **construir** — cadenas, RAG, agentes, deploy — pero no enseña
a **decidir qué construir**. En una empresa real hay procesos que solo piden
automatización determinista, otros un copiloto, otros un agente o un sistema
agéntico, y esa decisión (más la de *cuál va primero*) es la fase consultiva
previa que el temario saltaba:

- El c13 y el c10 dan el criterio workflow-vs-agente **técnico**, el c31b el de
  código-vs-low-code y el c23 el "no todo se automatiza" (HITL) — pero ninguno
  los reúne como método de negocio.
- El único embrión de discovery era la apertura del c29: el "menú del
  consultor" con 5 casos (cada uno con su dato y su retorno) y los 3 criterios
  por los que ganó el asistente de compras. El menú aparecía **sin el método
  que lo produce**.
- AS-IS/TO-BE, matriz de priorización y ROI: cero cobertura en todo el curso.
- La fila "Requisitos" del SDLC del c15a colapsaba directamente en la spec del
  c19 — como si el "qué construir" naciera en la spec, cuando su mitad de
  negocio se decide antes.
- La guía de-cero-a-produccion arrancaba en F0 con el agente ya respondiendo:
  construye bien, sin preguntarse si construye lo correcto.

## Decisión

> Un **módulo core web-only**, `modules/35-discovery-de-procesos.mdx` (badge
> 35, kind concept, sin script Python ni dependencias), **abriendo el Nivel 7**
> antes del c19: el arco del nivel queda discovery → spec (c19) → capstone
> (c18) → caso real (c29). En el manifest: order 45, renumerando 19→46, 18→47,
> 29→48, 26→49 (total 57→58).
>
> - **Caso trabajado: Sifrah**, la retail del c29. La matriz
>   impacto × viabilidad debe hacer **ganar** al asistente de compras con los 3
>   criterios que el c29 ya cita (dato accesible · integra lo conocido · riesgo
>   medible) — el módulo es la precuela que produce el menú del consultor, no
>   un caso nuevo.
> - **Método:** ficha AS-IS (entrevistando al dueño del proceso), TO-BE con
>   checkpoints HITL, escalera de autonomía (reglas/RPA → copiloto → agente →
>   sistema agéntico, con la regla del peldaño más bajo que resuelva) y
>   priorización con payback simple.
> - **ROI cuantificado simple en soles** (h/mes × S//h vs construir+operar,
>   payback en meses) con **cifras inventadas plausibles para retail peruano,
>   declaradas como ejemplo** en el propio MDX — a diferencia de los precios
>   del ADR-0011, no requieren verificación externa.
> - Fase previa breve en `extras/de-cero-a-produccion.mdx` («Antes de F0 · ¿Es
>   este el proceso correcto?») + enlaces entrantes en c29, c19, c15a (fila
>   Requisitos), mapa y entrevista.

El gate offline **no cambia** (pyFile null, tested false, patrón ADR-0010/0011).

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Módulo core badge 35 abriendo el Nivel 7** | El discovery es el corazón del arco consultoría→código; queda en la ruta con prev/next | Renumera 4 módulos del manifest | ✅ **Elegida** |
| Anexo fuera del gate (patrón ADR-0004..0007) | Sin renumerar nada | Un anexo dice "esto es periferia" — y decidir qué construir no lo es | El eslogan consultivo del curso pasa por aquí |
| Sección dentro del c29 | El caso ya vive ahí | Infla un módulo ya largo y mezcla método (decidir) con implementación (construir) | El método vale para cualquier caso, no solo Sifrah |
| Extra fuera de ruta (como mapa/entrevista) | Cero impacto en navegación | Pierde prev/next y el lugar narrativo antes del c19 | El orden discovery→spec ES la lección |

## Consecuencias

**Positivas**
- El "ganó la 1" del c29 deja de ser magia: el alumno ve el método que produjo
  el menú y los criterios formalizados en una matriz reutilizable.
- La fila Requisitos del SDLC queda completa (discovery + spec), y el lazo del
  curso se cierra: Discovery → Spec → Build → Operación → nuevo discovery.
- El curso gana la conversación con gerencia: escalera de autonomía, ficha de
  proceso y payback de servilleta — el vocabulario del consultor, no solo del
  ingeniero.

**Negativas**
- Las cifras de ROI son inventadas (aunque plausibles y declaradas): un alumno
  podría citarlas como dato. Mitigado: el MDX las marca como ilustrativas en
  cada tabla.
- Renumerar 4 módulos toca el manifest completo. Mitigado: script python +
  asserts de orden/unicidad, patrón ya usado dos veces.

**Cuándo revisar**

- Si el curso añade un "caso real 3", debe **salir de este método** (su
  apertura debería ser la ficha y la matriz que lo eligieron, como el c29 ya
  hace en retrospectiva).
- Si la ficha de proceso se vuelve plantilla descargable o interactiva, gana
  artefacto propio (y este módulo deja de ser web-only).
