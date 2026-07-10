# Feature Specification: Verificador de coherencia del curso

**Feature Branch**: `001-verificador-curso`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "Verificador del curso: chequea coherencia entre curso-langchain.html, README.md y util.py"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detectar enlaces internos rotos en el material (Priority: P1)

Quien mantiene el curso edita constantemente `curso-langchain.html` (401 KB, decenas de
secciones). Al mover o renombrar una sección es fácil dejar un enlace de navegación
`href="#loquesea"` apuntando a un ancla que ya no existe: el lector hace clic y no pasa nada.
Esta historia permite, con un solo comando, saber si TODOS los enlaces internos tienen destino.

**Why this priority**: es el fallo más frecuente y más invisible al ojo humano (un HTML enorme),
y el que peor experiencia da al estudiante. Es el mínimo producto viable: por sí solo ya justifica
la herramienta.

**Independent Test**: se ejecuta el verificador sobre un HTML con un `href="#x"` sin su `id="x"`;
debe reportar ese enlace concreto y terminar con código de salida ≠ 0.

**Acceptance Scenarios**:

1. **Given** un HTML donde cada `href="#X"` tiene un elemento con `id="X"`, **When** se ejecuta el
   verificador, **Then** ese chequeo se reporta como correcto.
2. **Given** un HTML con un `href="#no-existe"` sin ancla destino, **When** se ejecuta el verificador,
   **Then** el informe nombra `#no-existe` como enlace roto y el proceso falla (código ≠ 0).

---

### User Story 2 - Garantizar que el HTML se publica sin carcasa duplicada (Priority: P2)

El HTML del curso se publica con una herramienta que inyecta ella misma la carcasa
(`DOCTYPE`, `<head>`, etc.). Si alguien pega un `DOCTYPE` dentro del archivo, la publicación
genera una página con doble carcasa y se rompe. Esta historia detecta esa contaminación.

**Why this priority**: es un fallo binario y de bajo tráfico (rara vez ocurre), pero cuando ocurre
rompe la publicación entera; barato de comprobar.

**Independent Test**: se pasa un HTML que contiene la palabra `DOCTYPE`; el verificador lo reporta y falla.

**Acceptance Scenarios**:

1. **Given** un HTML sin `DOCTYPE`, **When** se ejecuta el verificador, **Then** el chequeo pasa.
2. **Given** un HTML que contiene `<!DOCTYPE html>`, **When** se ejecuta el verificador, **Then** se
   reporta la presencia de `DOCTYPE` y el proceso falla.

---

### User Story 3 - Mantener las tablas de referencia sincronizadas con el código (Priority: P3)

El curso documenta información que también vive en el código y debe coincidir letra por letra:
(a) los modelos por defecto de cada proveedor aparecen en la tabla del cheat sheet del HTML y en
`util.MODELOS_POR_DEFECTO`; (b) la tabla de módulos del mapa del HTML y la tabla §5 del `README.md`
listan las mismas filas. Cuando se cambia un modelo o se añade un módulo en un sitio y se olvida el
otro, el material miente. Esta historia detecta esas divergencias.

**Why this priority**: es la comprobación más valiosa a medio plazo (la que un humano nunca revisa a
mano) pero también la que más contexto necesita; por eso va después de las dos anteriores.

**Independent Test**: se altera un modelo por defecto solo en la tabla del HTML (no en `util.py`);
el verificador reporta exactamente esa fila discrepante y falla.

**Acceptance Scenarios**:

1. **Given** que los 7 modelos por defecto del cheat sheet coinciden con `util.MODELOS_POR_DEFECTO`,
   **When** se ejecuta el verificador, **Then** el chequeo pasa.
2. **Given** que un proveedor muestra en el HTML un modelo distinto al de `util.MODELOS_POR_DEFECTO`,
   **When** se ejecuta el verificador, **Then** se reporta el proveedor y ambos valores en conflicto.
3. **Given** que la tabla de módulos del mapa y la tabla §5 del README listan las mismas filas,
   **When** se ejecuta el verificador, **Then** el chequeo pasa.
4. **Given** que una fila existe en una tabla pero no en la otra, **When** se ejecuta el verificador,
   **Then** se reporta qué fila sobra o falta y en qué tabla.

---

### Edge Cases

- **HTML con anclas repetidas o mayúsculas distintas**: los `id` de HTML distinguen mayúsculas; la
  comparación de anclas es sensible a mayúsculas/minúsculas y exacta.
- **Modelo por defecto que en el HTML aparece dentro de más texto**: la tabla del cheat sheet lista un
  par `proveedor → modelo` por fila; se compara ese par, no la prosa que lo rodea.
- **Diferencias de formato entre las dos tablas de módulos** (una es Markdown, otra HTML): la
  comparación normaliza el contenido de cada celda (espacios, etiquetas) antes de comparar filas, para
  no reportar falsos positivos por maquetación.
- **Archivo de entrada ausente**: si falta el HTML, el README o `util.py`, el verificador falla con un
  mensaje claro en vez de una traza cruda.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El verificador MUST comprobar que cada `href="#X"` de `curso_ejemplos/curso-langchain.html`
  tiene en el mismo documento un elemento con `id="X"`; reporta cada enlace sin destino.
- **FR-002**: El verificador MUST comprobar que el HTML NO contiene `DOCTYPE` (la carcasa la inyecta la
  herramienta de publicación); reporta si lo encuentra.
- **FR-003**: El verificador MUST comprobar que los 7 modelos por defecto de la tabla del cheat sheet
  (sección `#cheat`) coinciden, proveedor por proveedor, con `util.MODELOS_POR_DEFECTO`; reporta cada
  divergencia con proveedor y ambos valores.
- **FR-004**: El verificador MUST comprobar que la tabla de módulos de la sección `#mapa` del HTML y la
  tabla §5 de `curso_ejemplos/README.md` contienen las mismas filas (se espejan); reporta las filas que
  sobran o faltan.
- **FR-005**: El verificador MUST producir una salida legible por humanos que, para cada uno de los
  cuatro chequeos, indique claramente si pasó o falló y, si falló, el detalle concreto.
- **FR-006**: El verificador MUST terminar con código de salida distinto de cero si al menos un chequeo
  falla, y cero si todos pasan, para poder colgarse de una CI.
- **FR-007**: El verificador MUST funcionar sin acceso a red, sin llaves de API y sin añadir dependencias
  nuevas al proyecto (solo biblioteca estándar de Python más `import util`).
- **FR-008**: El comportamiento del verificador MUST estar cubierto por tests offline (marcador
  `offline`) con fixtures HTML pequeñas e inline, sin tocar los archivos reales del curso.

### Key Entities *(include if feature involves data)*

- **Ancla interna**: un par (origen `href="#X"`, destino `id="X"`) dentro del HTML. El chequeo verifica
  que todo origen tiene destino.
- **Fila de modelo por defecto**: un par (proveedor, modelo) presente tanto en el cheat sheet del HTML
  como en `util.MODELOS_POR_DEFECTO`.
- **Fila de módulo**: una fila de la tabla de módulos, presente en el mapa del HTML y en la §5 del README.
- **Resultado de chequeo**: nombre del chequeo, veredicto (pasó/falló) y lista de detalles de fallo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con el material del curso en su estado correcto, el verificador termina con éxito (código 0)
  y muestra los cuatro chequeos en verde.
- **SC-002**: Ante cualquiera de los cuatro tipos de incoherencia (enlace roto, DOCTYPE presente, modelo
  divergente, fila de módulo desalineada), el verificador falla (código ≠ 0) y nombra el elemento exacto
  causante, sin que el operador tenga que abrir el archivo para adivinarlo.
- **SC-003**: La suite offline del curso sigue en verde tras añadir la feature, incluidos los tests nuevos
  del verificador.
- **SC-004**: El verificador corre en menos de 5 segundos en una máquina de desarrollo típica, sin red ni
  llaves.

## Assumptions

- **Resolución de ambigüedad (Clarify)**: donde el "cómo decidir" quedaba abierto, se fijaron estos
  criterios sensatos, documentados aquí:
  - "Los 7 defaults del cheat sheet" se refiere a la **segunda tabla** de la sección `#cheat` (la de
    `LLM_PROVIDER → Modelo por defecto → Llave`), que hoy tiene exactamente 7 filas, una por proveedor de
    `util.MODELOS_POR_DEFECTO`. No a los atajos de código de la primera tabla.
  - "DOCTYPE" se compara **sin distinguir mayúsculas** (`doctype`, `DOCTYPE`, `Doctype` cuentan igual),
    porque cualquier variante rompe la publicación.
  - El "espejo" de las tablas de módulos compara el **conjunto de filas** (qué conceptos hay y su
    correspondencia ejemplo/test), normalizando maquetación; no exige idéntico orden de columnas entre
    Markdown y HTML.
  - Los enlaces externos (`href="http…"`, `mailto:`) quedan **fuera de alcance**: solo se validan anclas
    internas `href="#…"`.
- El verificador se ejecuta desde `curso_ejemplos/` (donde vive `util.py`), igual que los tests.
- `curso-langchain.html`, `README.md` y `util.py` son de **solo lectura** para esta feature: si el
  verificador halla una incoherencia real, se reporta como hallazgo; no se edita el material para
  silenciar el fallo.
- Se asume que el material está hoy en estado coherente, de modo que el verificador debe pasar contra los
  archivos reales el día de su entrega.
