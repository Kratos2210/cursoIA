---
description: "Lista de tareas para el verificador de coherencia del curso"
---

# Tasks: Verificador de coherencia del curso

**Input**: Design documents from `specs/001-verificador-curso/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: SÍ incluidos. El spec los pide explícitamente (FR-008): cada chequeo debe estar cubierto
por tests offline con fixtures HTML inline.

**Organization**: agrupadas por historia de usuario (US1, US2, US3) para poder implementarlas y
probarlas de forma independiente. Todas las rutas son dentro de `curso_ejemplos/`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (infraestructura compartida)

**Purpose**: crear el esqueleto del módulo y su archivo de tests.

- [ ] T001 Crear `curso_ejemplos/verificar_curso.py` con docstring didáctico en español (qué verifica y
  por qué existe), los imports de stdlib (`re`, `sys`, `pathlib`, `html.parser`, `dataclasses`) e
  `import util`, y las rutas por defecto al HTML y al README resueltas con `pathlib` relativas al script.
- [ ] T002 Crear `curso_ejemplos/tests/test_verificar_curso.py` con docstring de cabecera al estilo de
  `tests/test_util.py` e `import verificar_curso`.

---

## Phase 2: Foundational (prerequisitos que bloquean las historias)

**Purpose**: la dataclass de resultado y el parser HTML base que todos los chequeos reutilizan.

**⚠️ CRITICAL**: ningún chequeo puede escribirse hasta terminar esta fase.

- [ ] T003 Definir la dataclass `ResultadoChequeo(nombre: str, ok: bool, detalles: list[str])` en
  `curso_ejemplos/verificar_curso.py`, con comentario del porqué (separar cálculo de impresión/salida).
- [ ] T004 Implementar en `curso_ejemplos/verificar_curso.py` un `HTMLParser` reutilizable (o helpers)
  que recolecte, en una sola pasada, el conjunto de `id` presentes y la lista de `href="#…"`, y helpers
  para extraer el texto y las filas de una tabla dada su sección.

**Checkpoint**: base lista; las tres historias pueden implementarse en paralelo.

---

## Phase 3: User Story 1 - Detectar enlaces internos rotos (Priority: P1) 🎯 MVP

**Goal**: cada `href="#X"` del HTML tiene su `id="X"`; si no, se reporta y el proceso falla.

**Independent Test**: fixture con un `href="#x"` sin `id="x"` → el resultado es `ok=False` y nombra `#x`.

### Tests for User Story 1 ⚠️ (escribir primero, deben fallar antes de implementar)

- [ ] T005 [P] [US1] En `curso_ejemplos/tests/test_verificar_curso.py`, test de caso sano (todo `href`
  tiene destino → `ok=True`) y de caso roto (un ancla sin destino → `ok=False` y el detalle nombra el `#X`).

### Implementation for User Story 1

- [ ] T006 [US1] Implementar `verificar_anclas(html: str) -> ResultadoChequeo` en
  `curso_ejemplos/verificar_curso.py`, comparando el conjunto de `href="#…"` contra el de `id`.

**Checkpoint**: US1 funcional y testeable por sí sola (MVP).

---

## Phase 4: User Story 2 - Publicar sin DOCTYPE duplicado (Priority: P2)

**Goal**: el HTML no contiene `DOCTYPE`; si aparece, se reporta y falla.

**Independent Test**: fixture con `<!DOCTYPE html>` → `ok=False`.

### Tests for User Story 2 ⚠️

- [ ] T007 [P] [US2] En `curso_ejemplos/tests/test_verificar_curso.py`, test de HTML sin DOCTYPE
  (`ok=True`) y con DOCTYPE en varias capitalizaciones (`ok=False`).

### Implementation for User Story 2

- [ ] T008 [US2] Implementar `verificar_sin_doctype(html: str) -> ResultadoChequeo` en
  `curso_ejemplos/verificar_curso.py` (búsqueda de `doctype` insensible a mayúsculas).

**Checkpoint**: US1 y US2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Tablas de referencia sincronizadas (Priority: P3)

**Goal**: (c) modelos del cheat sheet == `util.MODELOS_POR_DEFECTO`; (d) tabla `#mapa` espeja §5 del README.

**Independent Test**: fixture con un modelo cambiado solo en el HTML → reporta ese proveedor; fixture con
una fila de módulo desalineada → reporta la fila.

### Tests for User Story 3 ⚠️

- [ ] T009 [P] [US3] En `curso_ejemplos/tests/test_verificar_curso.py`, tests de `verificar_modelos`:
  caso coincidente (`ok=True`) y caso con un modelo divergente (`ok=False`, reporta proveedor y ambos valores).
- [ ] T010 [P] [US3] En `curso_ejemplos/tests/test_verificar_curso.py`, tests de
  `verificar_tablas_modulos`: caso espejado (`ok=True`) y caso con una fila que falta en un lado (`ok=False`).

### Implementation for User Story 3

- [ ] T011 [US3] Implementar `verificar_modelos(html, modelos)` en `curso_ejemplos/verificar_curso.py`:
  extraer los pares (proveedor, modelo) de la 2ª tabla de `#cheat` y compararlos con `util.MODELOS_POR_DEFECTO`.
- [ ] T012 [US3] Implementar `verificar_tablas_modulos(html, readme_md)` en
  `curso_ejemplos/verificar_curso.py`: extraer y normalizar las filas de la tabla `#mapa` (HTML) y de la
  §5 del README (Markdown) y compararlas como conjuntos.

**Checkpoint**: los cuatro chequeos funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T013 Implementar `main()` en `curso_ejemplos/verificar_curso.py`: leer los archivos reales, correr
  los cuatro chequeos, imprimir el informe legible (formato del contrato `contracts/cli.md`) y `sys.exit`
  con 0/1 según haya fallos. Guardarlo bajo `if __name__ == "__main__":`.
- [ ] T014 Ejecutar `cd curso_ejemplos && uv run pytest -m offline -q` y confirmar 372 + nuevos en verde.
- [ ] T015 Ejecutar `cd curso_ejemplos && uv run python verificar_curso.py` contra el material real y
  confirmar exit 0 (o reportar como hallazgo cualquier incoherencia real, sin tocar el material).

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; BLOQUEA todas las historias (dataclass + parser base).
- **US1/US2/US3 (Phases 3-5)**: dependen de Foundational; entre ellas son independientes (funciones puras
  distintas). Pueden hacerse en cualquier orden; el orden de prioridad es P1 → P2 → P3.
- **Polish (Phase 6)**: `main()` depende de que existan los cuatro chequeos; la verificación final depende
  de todo lo anterior.

### Within Each User Story

- El test se escribe primero y debe fallar antes de implementar la función del chequeo.

### Parallel Opportunities

- T005, T007, T009, T010 (tests de distintas historias, mismo archivo pero secciones independientes) se
  pueden redactar en paralelo conceptualmente; las implementaciones T006/T008/T011/T012 tocan funciones
  distintas del mismo módulo y son independientes entre sí.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup → Foundational → US1 (anclas) → validar → ya hay valor entregable.

### Incremental Delivery

2. US2 (DOCTYPE) → US3 (tablas) → `main()` + validación final. Cada historia suma sin romper las anteriores.

---

## Notes

- [P] = archivos/funciones distintas, sin dependencia.
- Todos los tests llevan `@pytest.mark.offline` y usan fixtures inline (sin tocar el material real).
- Commit tras cada grupo lógico.
- El material del curso (HTML/README/util) es solo lectura: un fallo real se reporta, no se "arregla".
