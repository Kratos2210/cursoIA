# Contrato del CLI · `verificar_curso.py`

## Invocación

```bash
cd curso_ejemplos
uv run python verificar_curso.py
```

Sin argumentos: usa las rutas por defecto (el HTML, el README y `util` de la propia carpeta).
Las rutas se resuelven con `pathlib` relativas al archivo del script, para que funcione desde
cualquier CWD y en CI.

## Salida (stdout)

Informe legible por humanos. Para cada uno de los cuatro chequeos, una línea de veredicto y, si
falla, sus detalles indentados. Ejemplo con todo en verde:

```text
Verificador del curso
=====================
[OK]    Anclas internas: 15 enlaces, todos con destino.
[OK]    Sin DOCTYPE en el HTML.
[OK]    Modelos por defecto del cheat sheet == util.MODELOS_POR_DEFECTO (7).
[OK]    Tabla de módulos #mapa == tabla §5 del README (18 filas).

Todo coherente. ✅
```

Ejemplo con un fallo:

```text
[FALLO] Anclas internas: 1 enlace sin destino.
        - href="#no-existe" no tiene un elemento con id="no-existe".
...
Se encontraron incoherencias. ❌
```

## Código de salida

- `0`: los cuatro chequeos pasan.
- `1`: al menos un chequeo falla (usable como gate de CI).

## Contrato de funciones (para tests)

Cada chequeo se expone como función pura, testeable sin I/O de disco:

- `verificar_anclas(html: str) -> ResultadoChequeo`
- `verificar_sin_doctype(html: str) -> ResultadoChequeo`
- `verificar_modelos(html: str, modelos: dict[str, str]) -> ResultadoChequeo`
- `verificar_tablas_modulos(html: str, readme_md: str) -> ResultadoChequeo`

Reciben el contenido como string (fixtures inline en los tests), no rutas. Una capa fina
(`main()` / helpers de lectura) las conecta a los archivos reales.
