# Quickstart · validar el verificador del curso

## Requisitos

- `uv` instalado y el entorno del curso sincronizado (`cd curso_ejemplos && uv sync`).
- No hace falta red ni llaves de API.

## Correr el verificador contra el material real

```bash
cd curso_ejemplos
uv run python verificar_curso.py
echo "exit code: $?"
```

**Esperado hoy**: los cuatro chequeos en verde y `exit code: 0`. Si algún chequeo falla, el informe
nombra el elemento causante (enlace, proveedor o fila) y el exit code es `1` — eso sería un hallazgo
real en el material, que se reporta (no se corrige el HTML/README/util para tapar el fallo).

## Correr los tests de la feature

```bash
cd curso_ejemplos
uv run pytest tests/test_verificar_curso.py -m offline -q
```

**Esperado**: todos verdes. Los tests usan fixtures HTML/Markdown pequeñas inline: un caso sano (pasa)
y un caso roto por cada chequeo (falla y reporta el detalle correcto).

## Correr toda la suite offline (no regresión)

```bash
cd curso_ejemplos
uv run pytest -m offline -q
```

**Esperado**: la línea base (372 tests) más los nuevos, todos en verde.
