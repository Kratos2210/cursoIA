# Auditoría de la web del curso · ¿la entrega está a la altura del contenido?

**Fecha:** 2026-07-18 · **Rama:** `002-migracion-nextjs` · **Auditor:** revisión asistida (Claude Code)
**Alcance:** `web/` completo — 45 módulos MDX (`content/modules/`), 7 extras (`content/extras/`), `modules.manifest.json`, `conversion-report.json`, home y páginas de la app.
**Método:** fan-out de 8 agentes de solo lectura (7 de contenido por bloque + 1 de estructura) con rúbrica de 8 criterios por módulo; dimensión de cobertura verificada en sesión principal contra `curso_ejemplos/`; **todo hallazgo P0/P1 re-verificado leyendo el archivo:línea citado** antes de entrar al informe.

---

## 1. Resumen ejecutivo

**Veredicto: la web es una entrega sólida y fiel al curso.** La cobertura es completa (los 31 ejemplos `.py`, los 3 anexos y los 3 proyectos están representados sin huecos; la conversión HTML→MDX no perdió tokens), las matemáticas y APIs citadas se verificaron correctas (RRF, softmax, z-test, LoRA, precios contra `util.py`/`cost_model.py`), y las 10 cajas nuevas de las currículas externas (agent engineering, lidr, ética) son técnicamente correctas salvo un matiz.

Los defectos están en dos frentes: **un puñado de errores factuales puntuales** (el más serio: atribuir IVFFlat a Qdrant en m24) y una **deuda estructural de doble fuente de verdad**: la app renderiza SOLO desde `modules.manifest.json`, pero los `export const meta` de los 52 MDX quedaron congelados en la organización vieja (~110 campos desincronizados). En sí es metadato muerto — no rompe nada — pero en **6 campos la corrección se hizo solo en el MDX muerto y el usuario ve la versión stale del manifest**, incluyendo chips de prereqs que mandan al módulo equivocado (m16 en vez de m16c). A eso se suman huecos de consistencia didáctica (prácticas sin `<Solution>` en ~8 módulos, ejemplos sin "▸ deberías ver").

Lo que NO se encontró también importa: **0 enlaces rotos de 204 validados, 0 componentes MDX sin definir, build limpio (56 páginas estáticas en 49 s)** y contadores de la home derivados del manifest, no hardcodeados.

### Nota global

| Dimensión | Nota | Comentario |
|---|---|---|
| **Contenido** | **9.0 / 10** | Exacto y completo; penalizado por 1 error factual (m24) y huecos de `<Solution>`/salidas esperadas. |
| **Estructura** | **7.5 / 10** | Funciona sin roturas (0 links rotos, build OK); penalizada por el desync manifest↔MDX con 6 campos stale visibles y 4 prereqs hacia adelante. |
| **Cobertura** | **10 / 10** | Sin huecos; conversión limpia (44 secciones, 0 tokens perdidos). |

### Nota por bloque de contenido

| Bloque | Módulos | Nota | Resumen |
|---|---|---|---|
| L1 | m00–m04 (+0b) | 9.0 | Sin P0/P1. Detalles de pulido (checkpoints ausentes en m00/m0b, conteo "8 vs 7 ideas"). |
| L2 | m05–m09b | 8.5 | m09b práctica sin solución ni salida esperada; m07 ejemplo sin salida. |
| L3 | m10–m13 | 9.0 | Caja CAG (m11) correcta; APIs LangGraph verificadas (StateGraph, interrupt/Command). |
| L4 | m14–m17b | 9.0 | Caja prompt caching precisa salvo matiz Anthropic opt-in; m16 práctica sin solución. |
| L5a | m18–m24b | 8.7 | **Error factual m24 (Qdrant/IVFFlat)**; prácticas sin solución en 6 módulos; cajas 🌐 de m19/m20/m23 correctas. |
| L5b | m25–m33 | 9.0 | m28 enlaza evals a m16 en vez de m16c; metadatos de order desincronizados. |
| Extras | 7 archivos | 9.5 | Sin P0/P1. Cheat-sheet, mapa, examen y precios verificados exactos contra fuente. |

---

## 2. Cobertura (dimensión C) — completa, sin huecos

Verificado en sesión principal contra el inventario de `curso_ejemplos/`:

- `conversion-report.json` limpio: **44 secciones convertidas, 0 tokens perdidos**.
- Los **31 `.py` numerados** están representados: 28 con módulo propio + 3 fusionados (13b→m13, 17_servidor→m17, 22b→m22/m33).
- Anexos A/B/C → m31/31b/32/33. Proyectos → m18 (capstone), `/recurso/llmops` (proyecto_llmops) y m29 (proyecto_retail, ancla `#m29-proyecto` verificada). LoRA → m21b.
- Cierres verificados durante la auditoría:
  - `gemini-3.1-flash-lite` **es un ID real** (verificado 2026-07-18 en ai.google.dev) — los agentes lo marcaban dudoso; **no es hallazgo**.
  - Las referencias a `proyectorag/`, `funcionaconver_v3_streaming.py` y `agent.py` **no son errores**: son artefactos que el alumno construyó en el curso básico previo. Queda como P2 añadir una nota de contexto para el alumno que entra directo (m10, m12, m16c, extras/mapa).

---

## 3. Hallazgos P1 (verificados archivo:línea) — errores factuales y huecos didácticos

Ningún P0 de contenido. P1 confirmados:

| # | Archivo:línea | Hallazgo |
|---|---|---|
| 1 | `24-vector-dbs-en-produccion.mdx:98` | Afirma que **Qdrant ofrece IVFFlat** — falso: Qdrant solo indexa con HNSW. Se contradice con la propia tabla comparativa del módulo. (pgvector y Milvus sí ofrecen ambos.) |
| 2 | `28-desafios-y-alucinaciones.mdx:54,59` | Atribuye "evals" a **m16** y enlaza a `/modulo/16-observabilidad-y-costo` — la evaluación con datasets/métricas es **m16c** (el propio prereq de la línea 14 dice m16c). |
| 3 | `09b-proyecto-utilidad-texto.mdx:73` | Práctica sin `<Solution>` **y** el módulo no tiene ningún bloque "▸ deberías ver" (es el proyecto integrador temprano; el alumno no puede autocorregirse). |
| 4 | `07-herramientas.mdx` | El ejemplo ejecutable no muestra salida esperada (no hay bloque "▸ deberías ver" en todo el módulo). |
| 5 | `16-observabilidad-y-costo.mdx:189` | Práctica sin `<Solution>` (sí tiene salida esperada en l.122). |
| 6 | `modules.manifest.json` (26b, 28, 29) | Chips de prereq **visibles** dicen "m16 (evaluación/evals)" — la evaluación es **m16c**; el chip manda al módulo de observabilidad. El fix ya existe pero solo en el `meta` MDX, que la app no lee (ver §5). |
| 7 | `modules.manifest.json` (0b, 27) | Más campos stale visibles con el fix atrapado en el MDX muerto: goals de m0b dicen "las 7 ideas" (el MDX corregido dice 8); minutes de m27 "~30 min" (MDX: ~35). |
| 8 | Prereqs hacia adelante (manifest) | `26b` (pos 10) requiere m11 (pos 18) y m16 (pos 34); `28` (pos 25) requiere m16 (pos 34); `32` (pos 22) requiere m26 (pos 44); `33` requiere "m22b", **id que no existe** (es el archivo `22b_voz.py`, cubierto en m22). |

## 4. Hallazgos P2 (pulido; verificación puntual, no exhaustiva)

**Exactitud / matices:**
- m16 (caja prompt caching 🌐): dice que Anthropic y OpenAI cachean automático por igual — en **Anthropic es opt-in** (`cache_control`); corregir el matiz.
- m11: cifras "~220 MB" de KV cache sin sustento citado.
- m13:92: referencia personal "comisión de EricBz" (residuo del curso fuente).
- m27:51: el trozo BPE "ecto" no cuadra con el merge real del ejemplo.
- m18b: fechas inconsistentes (2026-07-10 vs 07-09 en l.103/105/124); comillas tipográficas mal en l.41.
- m17b: "44 tests" (contados 42 `def test_` en `proyecto_final/tests`) y "642 tests" junto a un snippet de CI que solo corre `-m offline` (141).
- extras/llmops: meta "232 tests" vs 229 contados. extras/examen: bloque 5 dice "m20–m30" vs contenido real "20–28·30". extras/entrevista:117: QA de m21 bajo encabezado "módulos 11,12,20,16".

**Metadatos muertos (`export const meta` de los MDX; la app no los lee — §5):**
- Orders duplicados: 10 (m09/m09b), 19 (m16c/m17), 26 (m21/m21b — nuevo), 35 (m27b/m28), 40 triplicado (m31/m32/m33).
- levelName desincronizado en m21/m21b/m22/m27/m27b/m28. *(El desync de m33 reportado en la primera pasada NO se reprodujo: manifest y MDX dicen ambos "Modelos".)*
- Ids inconsistentes en el manifest: `m09b` con cero a la izquierda vs `m9`/`m0b`/`m18b` (solo estético; el id se usa para localStorage/neighbors).
- `lib/content.ts` es código muerto (nadie lo importa) — candidato a borrar para eliminar la apariencia de segunda fuente.

**Didáctica / formato:**
- Prácticas sin `<Solution>` también en m18, m20, m22, m23, m24, m24b (además de los P1 de arriba).
- m21 sin "▸ deberías ver"; m05 (Tagging) ejemplo sin salida.
- m00 y m0b sin `<Checkpoint>`; m0b "8 ideas" (l.18) vs "7 ideas" (l.143).
- m03: título de código dice `.ipynb` pero el `pyFile` real es otro.
- m24b:99: título `significancia.py` de archivo inexistente.
- m11:177: caja CAG con `kind="analogy"` siendo una tabla comparativa (renderiza bien; kind semánticamente incorrecto).
- Labels engañosos con destino válido: `18b:213` "[m16b](/modulo/16-observabilidad-y-costo)" (no existe slug 16b); `33:18` "[m22b](/modulo/22-multimodal)" — m33 usa "m22b" ~15 veces refiriéndose al archivo `22b_voz.py`, no a un módulo web.
- Falta nota de contexto sobre artefactos del curso básico previo (`proyectorag/` etc.) en m10/m12/m16c y extras/mapa.

---

## 5. Estructura (dimensión A) — 7.5/10

### Fuente de verdad de la app: SOLO `modules.manifest.json`

Verificado en código:
- `lib/roadmap.ts:1,27-28` importa el manifest; `LEVELS` se construye iterando el **orden del array** (`lib/roadmap.ts:91-103`); `MODULE_ITEMS` (`:106`) alimenta prev/next (`:121-127`) y `generateStaticParams` (`app/modulo/[slug]/page.tsx:25-27`). Los chips de meta visibles salen del manifest (`app/modulo/[slug]/page.tsx:50-54`).
- Los `export const meta` de los 52 MDX **no se importan en ninguna parte** (la página solo importa el `default` del MDX). Son **metadato muerto**.
- El campo `order` ni siquiera se lee en runtime: solo lo usa el generador (`scripts/convert-html-to-mdx.mjs:597`) para ordenar el array. En el manifest no hay orders duplicados y el array es monótono → los duplicados en MDX son cosméticos, no bug de render.

**Consecuencia (la causa raíz del hallazgo P1 #6-7):** el manifest se regenera desde el HTML original (`scripts/convert-html-to-mdx.mjs:589-598`), pero varios fixes posteriores se hicieron a mano solo en los MDX. Resultado: 41/45 módulos y 7/7 extras con al menos un campo desincronizado (~110 campos), y en 6 de ellos **la versión corregida está en el archivo que nadie lee**.

### Lo que está sano

- **Enlaces internos: 204/204 válidos** (MDX + app + components; anchors validados con el mismo `github-slugger` que usa `rehype-slug`, `next.config.ts:30`). Los 4 candidatos a roto resultaron falsos positivos (3× `#m29-proyecto` resuelve contra un `<span id>` en m29:194; 1 href en código de ejemplo de m19:111).
- **Componentes: 25 usados (Box×263, Step×123, Quiz×11…), todos definidos** en `components/content/mdx.tsx` + `mdx-components.tsx`. Box kinds usados (def/analogy/practice/warn) todos válidos; cero props raras en Checkpoint/Recap/Solution/LevelBanner.
- **Build completo OK**: `npx next build` en 49 s, 56 páginas estáticas (45 módulos + 7 recursos + home + not-found). Contadores de la home derivados del manifest (`components/app/Dashboard.tsx:39-41`).
- Manifest íntegro: 52 entradas = 52 archivos, sin huérfanos en ninguna dirección, `total: 52` consistente.

### Lo que no

Ver P1 #6–8 (§3): campos stale visibles con el fix atrapado en MDX muerto, y 4 prereqs que apuntan hacia adelante en el orden de navegación (26b→m11/m16, 28→m16, 32→m26, 33→"m22b" inexistente). Los prereqs hacia adelante son en parte consecuencia de la reorganización temática: módulos de la ruta de prompting/calidad quedaron antes que sus dependencias de la ruta RAG/evals.

---

## 6. Correcciones propuestas (para aprobar antes de implementar)

**Grupo 1 — errores factuales (P1):**
1. m24:98 — quitar IVFFlat de Qdrant (dejar "que ofrecen índices como IVFFlat y HNSW" solo para pgvector/Milvus, o reformular).
2. m28:54,59 — cambiar la atribución de evals a m16c y el enlace a `/modulo/16c-evaluacion`.
3. m16 caja prompt caching — matiz Anthropic opt-in (`cache_control`).

**Grupo 2 — consistencia didáctica (P1):**
4. Añadir `<Solution>` a las prácticas de m09b y m16 (mínimo), idealmente también m18/20/22/23/24/24b.
5. Añadir "▸ deberías ver" a m07 y m09b (y m21, m05 si se quiere uniformidad).

**Grupo 3 — manifest stale visible (P1):**
6. Corregir en `modules.manifest.json` los 6 campos donde el usuario ve la versión vieja: prereqs de 26b/28/29 (m16→m16c), goals de 0b (7→8 ideas), minutes de 27 (~30→~35).
7. Prereqs hacia adelante: decidir si son deliberados por la organización temática (y entonces marcarlos como "de otra ruta") o corregirlos; el "m22b" de m33 sí hay que cambiarlo (id inexistente → m22 o quitar).

**Grupo 4 — doble fuente de verdad (P1 estructural, decisión de diseño):**
8. Elegir una: (a) borrar los `export const meta` de los MDX (y `lib/content.ts`) dejando el manifest como única fuente, o (b) hacer que el generador preserve los fixes manuales. La opción (a) es la barata y elimina la clase entera de bugs.

**Grupo 5 — pulido (P2):** el resto de §4, a discreción.

---

*Cross-check de conteos: 45 módulos + 7 extras = 52 archivos auditados por 7 agentes de contenido + 1 de estructura; 52 entradas del manifest contra 52 archivos; 204 enlaces internos validados; hallazgos P0/P1 verificados individualmente en sesión principal; P2 listados tal como los reportaron los agentes (verificación puntual).*
