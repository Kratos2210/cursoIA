# Fase 0 · Investigación y decisiones técnicas

No quedaban marcadores `NEEDS CLARIFICATION` en el spec (se resolvieron en Assumptions). Aun así,
estas son las decisiones de diseño que fija el plan, con su porqué.

## D1 · Cómo recolectar los `id` y los `href="#…"` del HTML

- **Decisión**: usar `html.parser.HTMLParser` de la stdlib para recorrer las etiquetas y quedarnos con
  el atributo `id` de cualquier elemento y con los `href` que empiezan por `#`.
- **Rationale**: una regex ingenua sobre `id="..."` también capturaría `id` que aparezcan dentro de
  cadenas de código o comentarios; el parser entiende la estructura y es stdlib (cero dependencias).
- **Alternativas descartadas**: `BeautifulSoup`/`lxml` (dependencia nueva, viola principio IV);
  regex sola (frágil ante el HTML real de 400 KB con ejemplos de código embebidos).

## D2 · Detección de DOCTYPE

- **Decisión**: buscar la subcadena `doctype` sin distinguir mayúsculas en el texto crudo del archivo.
- **Rationale**: `HTMLParser.handle_decl` captura `<!DOCTYPE …>`, pero un `DOCTYPE` pegado como texto
  plano o comentado también rompería la publicación; la búsqueda textual insensible a mayúsculas es la
  red más amplia y es lo que pide FR-002.
- **Alternativas descartadas**: depender solo de `handle_decl` (se saltaría un DOCTYPE mal formado).

## D3 · Extraer los modelos por defecto del cheat sheet

- **Decisión**: localizar la segunda tabla de la sección `#cheat` (encabezados `LLM_PROVIDER` /
  `Modelo por defecto` / `Llave`) y leer, por fila, el par (proveedor, modelo) que va dentro de los
  `<code>` de las dos primeras celdas.
- **Rationale**: es la tabla que declara los 7 defaults; se compara par a par contra
  `util.MODELOS_POR_DEFECTO` (import directo, sin duplicar el dato).
- **Alternativas descartadas**: parsear la primera tabla del cheat (atajos de código, no defaults).

## D4 · Comparar la tabla de módulos del HTML (#mapa) con la §5 del README

- **Decisión**: extraer, de cada tabla, el conjunto de filas normalizadas (texto de las celdas sin
  etiquetas HTML/Markdown ni espacios sobrantes) y compararlos como conjuntos; reportar filas que
  sobran/faltan en cada lado.
- **Rationale**: una es HTML y otra Markdown; comparar el texto normalizado evita falsos positivos por
  maquetación y cumple FR-004 ("se espejan").
- **Alternativas descartadas**: comparación byte a byte (imposible entre dos formatos); comparar solo la
  primera columna (no detectaría un cambio de ejemplo/test en una fila existente).

## D5 · Estructura del programa y su salida

- **Decisión**: cada chequeo es una función pura que devuelve un `ResultadoChequeo`
  (nombre, ok, detalles). `main()` los corre todos, imprime un informe y devuelve 0/1.
- **Rationale**: funciones puras = testeables offline con fixtures inline (principio III); separar
  "calcular" de "imprimir/salir" permite testear la lógica sin capturar stdout ni `SystemExit`.
- **Alternativas descartadas**: lanzar excepciones por fallo (haría difícil listar TODOS los fallos de
  una pasada; se prefiere acumular y reportar todo junto).
