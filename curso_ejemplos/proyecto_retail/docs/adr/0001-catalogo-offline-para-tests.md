# ADR-0001 — Catálogo offline versionado para los tests

- **Estado:** aceptado
- **Fecha:** 2026-07-11
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El asistente lee de un catálogo con la forma del `products.json` de Shopify. La
fuente real (`sifrah.com/products.json`) es pública, pero:

- cambia a diario (colecciones por temporada, promos que entran y salen), y
- depende de la red y de que un tercero mantenga el endpoint vivo.

Un test que baje el catálogo real es un test que falla el día que Sifrah cambia
un precio, saca un producto o tiene una caída — sin que nuestro código tenga
ningún bug. Eso es un test que el equipo aprende a ignorar.

## Decisión

> Los tests corren contra `data/catalogo_demo.json`: una docena de productos
> fijos que calcan la FORMA del endpoint real (mismos campos: `title`,
> `product_type`, `tags`, `variants` con `price`/`compare_at_price`/`available`).
> El catálogo real se baja aparte, a mano, con `data/fetch_catalogo.py`, para el
> ejercicio "con los datos de verdad".

El demo incluye a propósito las trampas del dato real: `product_type` dice
"Joyería" en todo (mochila y cepillo incluidos), un producto agotado, y promos
escondidas en `compare_at_price`. Sin esas trampas, el ETL no tendría nada que
demostrar.

## Alternativas consideradas

| Opción | En contra | ¿Por qué no? |
|--------|-----------|--------------|
| **Demo fijo con la forma real** | No prueba categorías nuevas del catálogo vivo | ✅ **Elegida**: determinista, sin red, byte a byte |
| Bajar el catálogo real en cada test | Falla por cambios de un tercero; lento; sin red no corre | Un test frágil se acaba desactivando |
| Grabar el catálogo real una vez (fixture VCR) | Se queda obsoleto y nadie lo actualiza; pesa | El demo curado enseña mejor las trampas |

## Consecuencias

- Los tests son deterministas y offline: la CI no gasta cuota ni depende de la red.
- El catálogo real vive fuera del ciclo de tests, en un ejercicio explícito: el
  estudiante ve fallar el ETL con datos sucios de verdad y lo arregla.
- **Riesgo aceptado:** el demo puede divergir de la forma real si Shopify cambia
  su esquema. Cuando eso pase, se actualiza el demo a mano — es un archivo, no
  una integración.
