<!--
SYNC IMPACT REPORT
==================
Version change: (plantilla sin versión) → 1.0.0
Motivo del bump: ratificación inicial (MAJOR: primera versión con principios
  concretos que sustituyen la plantilla genérica Library-First/TDD).

Principios definidos (reemplazan los placeholders de la plantilla):
  I.   Español didáctico y comentarios del PORQUÉ  (nuevo)
  II.  uv siempre, nunca pip directo               (nuevo)
  III. Tests offline obligatorios (marcador `offline`, sin red, sin llaves)  (nuevo)
  IV.  Cero dependencias nuevas salvo necesidad real (stdlib + import util)   (nuevo)
  V.   El material del curso es la fuente de verdad (HTML/README/util = solo lectura) (nuevo)

Secciones:
  + "Restricciones técnicas del repositorio" (SECTION_2)
  + "Flujo de desarrollo y puertas de calidad" (SECTION_3)

Plantillas revisadas para alinearlas con esta constitución:
  ✅ .specify/templates/plan-template.md   (Constitution Check apunta a estos principios)
  ✅ .specify/templates/spec-template.md   (sin requisitos que choquen; alineado)
  ✅ .specify/templates/tasks-template.md  (las tareas de test usan marcador offline)

Follow-ups / TODOs: ninguno. No quedan tokens sin resolver.
-->

# Constitución del curso LangChain (curso_ejemplos)

## Core Principles

### I. Español didáctico y comentarios del PORQUÉ
Este repositorio es **material de enseñanza**, no solo software que funciona. Por eso:
- El código y los comentarios se escriben en **español** (el chat con el instructor también).
- Cada pieza no obvia lleva un comentario que explica el **PORQUÉ**, no el QUÉ: el lector
  ya ve *qué* hace la línea; lo que aprende es *por qué se hace así* y qué alternativa se
  descartó. Un comentario que solo reformula el código sobra.
- Los nombres (funciones, tests, variables) son descriptivos y en español, aunque sean
  largos: `test_el_agente_recuerda_el_turno_anterior` vale más que `test_memory`.
**Rationale:** un estudiante aprende del razonamiento, no del resultado. Si el porqué no
está escrito, el material falla en su único trabajo.

### II. uv siempre, nunca pip directo
Toda ejecución, instalación de dependencias y arranque de tests pasa por **`uv`**
(`uv run …`, `uv add …`, `uv sync`). **Nunca** `pip install` ni `python` a secas.
**Rationale:** un entorno reproducible es parte del contenido: el estudiante copia los
comandos tal cual. Mezclar `pip` rompe el lockfile (`uv.lock`) y siembra "en mi máquina
sí funciona".

### III. Tests offline obligatorios (marcador `offline`, sin red, sin llaves)
Todo comportamiento verificable se cubre con un test **offline**:
- Marcado con `@pytest.mark.offline` (clase o función).
- **Sin red**: no llama a ninguna API ni descarga nada.
- **Sin llaves**: no requiere `GOOGLE_API_KEY` ni ninguna otra variable secreta.
- Corre entero con `uv run pytest -m offline` y termina en verde.
Los tests van en `curso_ejemplos/tests/`, con fixtures pequeñas e **inline** cuando el
dato de prueba es simple, imitando el estilo de `tests/test_util.py`.
**Rationale:** el estudiante debe poder correr la suite en un avión, sin cuota y sin gastar
un centavo. Un test que necesita red no es una red de seguridad: es una lotería.

### IV. Cero dependencias nuevas salvo necesidad real
Una feature de tooling/verificación se implementa con la **biblioteca estándar** de Python
más `import util` del propio curso. No se añaden paquetes al `pyproject.toml` salvo que sea
**estrictamente imprescindible**, y en ese caso se justifica por escrito en el plan.
**Rationale:** cada dependencia es superficie que el estudiante debe instalar, entender y
mantener. Para parsear HTML o comparar tablas, la stdlib (`html.parser`, `re`, `pathlib`)
alcanza; meter una librería externa sería enseñar a matar moscas a cañonazos.

### V. El material del curso es la fuente de verdad (solo lectura)
`curso-langchain.html`, `README.md` y `util.py` son la **versión canónica** del curso.
Una feature de verificación los **lee y contrasta**, pero **no los edita**. Si el verificador
detecta una discrepancia real, se **reporta** como hallazgo; no se "arregla" tocando el
material para que el test pase.
**Rationale:** el verificador existe justamente para proteger esos archivos. Si pudiera
editarlos para acallar un fallo, dejaría de ser un guardián y pasaría a ser cómplice.

## Restricciones técnicas del repositorio

- **Estructura**: los ejemplos y su tooling viven en `curso_ejemplos/`; los tests en
  `curso_ejemplos/tests/` (pytest, con `conftest.py` que sabe importar archivos `NN_*.py`).
- **Suite verde**: la línea base offline está en verde (372 tests). Toda feature la mantiene
  verde y **suma** sus propios tests; no se rompe ni se salta un test existente.
- **Portabilidad**: rutas construidas con `pathlib` y relativas al archivo, nunca absolutas
  a la máquina del autor.
- **Salida usable en CI**: una herramienta de verificación imprime un informe **legible por
  humanos** y termina con **exit code ≠ 0** si algo falla, para poder colgarla de la CI.

## Flujo de desarrollo y puertas de calidad

Este proyecto sigue **Spec-Driven Development** con spec-kit. Para cada feature:
1. **Specify → (Clarify) → Plan → Tasks → Implement**, en ese orden; los artefactos
   (`specs/NNN-*/spec.md`, `plan.md`, `tasks.md`) se **commitean** (son material didáctico).
2. **Puerta de tests**: antes de dar por hecha una feature, `uv run pytest -m offline`
   pasa en verde, incluidos los tests nuevos.
3. **Puerta de constitución**: el plan incluye un "Constitution Check" que confirma el
   cumplimiento de los cinco principios; cualquier desviación se justifica explícitamente.
4. **Commits convencionales** (`feat:`, `fix:`, `chore:`, `docs:`…), en español.

## Governance

Esta constitución **prevalece** sobre cualquier práctica ad-hoc. Enmendarla exige:
editar este archivo, actualizar el Sync Impact Report de la cabecera y revisar que las
plantillas de `.specify/templates/` sigan alineadas.

Versionado semántico de la constitución:
- **MAJOR**: se elimina o redefine un principio de forma incompatible.
- **MINOR**: se añade un principio o una sección nueva.
- **PATCH**: aclaraciones o correcciones de redacción sin cambio de fondo.

Cumplimiento: toda revisión de una feature verifica que respete estos principios; la
complejidad extra (una dependencia nueva, un test que toca red) debe justificarse o se
rechaza.

**Version**: 1.0.0 | **Ratified**: 2026-07-10 | **Last Amended**: 2026-07-10
