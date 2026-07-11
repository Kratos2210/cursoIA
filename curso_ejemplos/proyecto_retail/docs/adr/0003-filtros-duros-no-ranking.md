# ADR-0003 — El presupuesto es un filtro DURO, no una señal de ranking

- **Estado:** aceptado
- **Fecha:** 2026-07-11
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

La clienta dice "aretes dorados por menos de 25 soles". Hay dos formas de tratar
ese "menos de 25":

1. Como una **preferencia** que baja la puntuación de los productos caros (parte
   del ranking de relevancia).
2. Como una **restricción dura** que excluye del todo a los que se pasan (un
   `WHERE precio <= 25`).

La opción 1 es la que sale "gratis" si metes todo en un ranking semántico: los
caros aparecen más abajo, pero aparecen. Y ahí está la trampa: un producto de
S/39.90 ante un tope de S/25 no es "menos relevante" — es **inválido**.
Recomendarlo es faltar a lo que la clienta pidió.

## Decisión

> Presupuesto, stock y categoría son **filtros duros** que se aplican ANTES del
> ranking (`app/search.py`): primero se descarta lo que no cumple, y solo entre
> los válidos se ordena por afinidad. Si nada cumple, la respuesta es lista vacía
> — "no tengo eso" es válido; un sustituto fuera de presupuesto, no.

Es el `WHERE` del m24 (metadatos de la búsqueda), no el ranking del m11/m12.

## Consecuencias

- La búsqueda nunca recomienda algo fuera de presupuesto o agotado, por muy
  "relevante" que sea semánticamente. La métrica del eval lo verifica.
- El ranking (hoy: color pedido + más barato) queda **aislado** en la función
  `afinidad`, para poder cambiarlo por embeddings + re-ranking (m12) sin tocar
  los filtros duros. Ver [ADR-0005](0005-escalabilidad-embeddings-vector-db.md).
- **Consecuencia asumida:** una petición con presupuesto muy ajustado puede dar
  cero resultados. Es correcto: el asistente lo dice y ofrece ajustar. Rellenar
  con un producto caro "para no dejar vacío" sería exactamente el error.
