# Implementation Plan: Verificador de coherencia del curso

**Branch**: `001-verificador-curso` | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-verificador-curso/spec.md`

## Summary

Un script CLI, `curso_ejemplos/verificar_curso.py`, que ejecuta cuatro chequeos de coherencia
del material del curso (anclas internas, ausencia de DOCTYPE, modelos por defecto del cheat sheet
vs. `util.MODELOS_POR_DEFECTO`, y espejo de las tablas de módulos HTML/README), imprime un informe
legible y devuelve exit code ≠ 0 si algo falla. Solo biblioteca estándar (`html.parser`, `re`,
`pathlib`, `sys`) más `import util`. Tests offline en `tests/test_verificar_curso.py` con fixtures
HTML inline.

## Technical Context

**Language/Version**: Python 3.12 (el del curso, gestionado con `uv`).

**Primary Dependencies**: Ninguna nueva. Solo stdlib (`html.parser`, `re`, `pathlib`, `sys`,
`dataclasses`) e `import util` del propio curso.

**Storage**: N/A (lee archivos de texto; no persiste nada).

**Testing**: pytest con marcador `offline`; fixtures HTML pequeñas inline. Estilo de `tests/test_util.py`.

**Target Platform**: cualquier máquina de desarrollo o CI con Python; sin red ni llaves.

**Project Type**: single project — herramienta CLI dentro de `curso_ejemplos/`.

**Performance Goals**: < 5 s sobre el HTML real de 401 KB (holgadísimo; una sola pasada de parseo).

**Constraints**: sin red, sin llaves de API, cero dependencias nuevas, no editar el material del curso.

**Scale/Scope**: un HTML (~400 KB), un README, un dict de 7 entradas; ~15 anclas distintas, 18 filas
de módulos, 7 filas de modelos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Contrastado contra `.specify/memory/constitution.md` v1.0.0:

- **I. Español didáctico y comentarios del PORQUÉ**: ✅ el script y los tests se comentan en español
  explicando por qué (p. ej. por qué se usa `HTMLParser` y no una regex ingenua para los `id`).
- **II. uv siempre**: ✅ se ejecuta con `uv run python verificar_curso.py` y `uv run pytest`.
- **III. Tests offline obligatorios**: ✅ `tests/test_verificar_curso.py` con `@pytest.mark.offline`,
  fixtures inline, sin red ni llaves.
- **IV. Cero dependencias nuevas**: ✅ solo stdlib + `import util`. No se toca `pyproject.toml`.
- **V. Material del curso = solo lectura**: ✅ el verificador lee HTML/README/util; si detecta un
  fallo real, se reporta, no se corrige el material.

**Resultado**: PASS, sin violaciones. La tabla de Complexity Tracking queda vacía.

## Project Structure

### Documentation (this feature)

```text
specs/001-verificador-curso/
├── plan.md              # Este archivo
├── spec.md              # Especificación (WHAT/WHY)
├── research.md          # Fase 0: decisiones técnicas
├── data-model.md        # Fase 1: entidades del dominio
├── quickstart.md        # Fase 1: cómo validar la feature
├── contracts/
│   └── cli.md           # Contrato del CLI (salida y exit codes)
├── checklists/
│   └── requirements.md  # Checklist de calidad del spec
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
curso_ejemplos/
├── util.py                     # (solo lectura) fuente de MODELOS_POR_DEFECTO
├── curso-langchain.html        # (solo lectura) material verificado
├── README.md                   # (solo lectura) material verificado
├── verificar_curso.py          # NUEVO · la herramienta
└── tests/
    ├── conftest.py             # (existente) fixtures compartidas
    ├── test_util.py            # (existente) estilo a imitar
    └── test_verificar_curso.py # NUEVO · tests offline de la herramienta
```

**Structure Decision**: single project. La herramienta vive junto a los ejemplos en `curso_ejemplos/`
para que `import util` funcione igual que en los ejemplos y en los tests (mismo `sys.path`). No se crea
carpeta `src/`: rompería la convención del curso, donde todo cuelga de `curso_ejemplos/`.

## Complexity Tracking

> Sin violaciones de constitución. Nada que justificar.
