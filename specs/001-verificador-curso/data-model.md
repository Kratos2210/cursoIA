# Fase 1 · Modelo de datos

El verificador no persiste nada; estas son las entidades en memoria durante una ejecución.

## `ResultadoChequeo` (dataclass)

Representa el veredicto de uno de los cuatro chequeos.

| Campo      | Tipo        | Significado                                                        |
|------------|-------------|-------------------------------------------------------------------|
| `nombre`   | `str`       | Nombre legible del chequeo (p. ej. "Anclas internas").            |
| `ok`       | `bool`      | `True` si el chequeo pasó.                                        |
| `detalles` | `list[str]` | Líneas de detalle de los fallos; vacío si `ok` es `True`.        |

**Reglas**: si `detalles` no está vacío, `ok` debe ser `False`. `main()` agrega todos los
resultados; el exit code global es 0 solo si todos los `ok` son `True`.

## Entidades del dominio (derivadas del material, no clases)

- **Ancla interna**: par `(origen "#X", destino id="X")`. El chequeo A verifica que el conjunto de
  destinos (`id`) cubre el conjunto de orígenes (`href="#…"`).
- **Fila de modelo por defecto**: par `(proveedor, modelo)`. Se compara el dict extraído del cheat
  sheet contra `util.MODELOS_POR_DEFECTO` (mismo conjunto de claves y mismo valor por clave).
- **Fila de módulo**: tupla del texto normalizado de las celdas de una fila. El chequeo D compara el
  conjunto de filas del `#mapa` (HTML) con el de la §5 del README.

## Estados / transiciones

No hay máquina de estados: el programa es una pasada única sin estado persistente.
