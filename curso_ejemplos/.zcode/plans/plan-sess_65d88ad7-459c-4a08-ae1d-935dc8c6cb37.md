# Plan: mejorar la estructura y el aprendizaje del HTML del curso

## Diagnóstico
El HTML (`curso-langchain.html`, ~196KB monolítico) ya es **maduro**: tiene dark mode, scrollspy, barra de progreso, progreso persistente en localStorage, 4 quizzes, 21 callouts "Para practicar", 21 `<details>` de soluciones, botón copiar código, diagramas de pasos `.flow`, y resaltador de sintaxis propio. El sistema de diseño (tokens CSS, `.box/.flow/.ccard/.lvbanner/.fileref`) es coherente y reutilizable.

Pero tiene problemas reales en 4 frentes (los que pediste):

| Frente | Problemas concretos |
|--------|---------------------|
| **Técnico** | HTML *inválido*: sin `<!DOCTYPE>`, `<html>`, `<head>`, `charset`, `viewport`, `lang="es"`. Cero `aria-*`/`role`. El nav `m15` dice "Multiagente y arquitectura" pero el contenido es microservicios/K8s (engañoso). |
| **Visual** | 0 imágenes/SVG/diagramas conceptuales. Conceptos clave (ciclo del agente, pipeline RAG end-to-end, grafo LangGraph con su ciclo, arquitectura supervisor/multiagente) son solo texto. |
| **Pedagógico** | Sin recaps por módulo. Sin botón volver arriba. Sin buscador. El HTML no referencia los archivos `.py`/tests nuevos del plan de infraestructura. |
| **Contenido** | Los temas nuevos que estoy creando (supervisor multiagente, servidor del agente, proyecto modular, LangSmith real) son brechas que el HTML no refleja. |

**Decisión clave de diseño**: mantener el archivo monolítico (tu elección). Todas las mejoras reutilizan el sistema de componentes existente (no invento clases nuevas salvo lo imprescindible), y el JS nuevo se suma a la IIFE actual.

---

## Fase A — Corrección técnica (fundación, sin cambio visual)

1. **Carcasa HTML5 válida**: envolver todo en `<!DOCTYPE html>` / `<html lang="es">` / `<head>` con `<meta charset>`, `<meta viewport>`, `<meta name="description">`, `<meta name="author">`. El `<title>` y `<style>` actuales pasan al `<head>`. Esto no cambia ni un pixel.
2. **Accesibilidad**: `aria-label` en `<nav>`, `role="progressbar"` + `aria-valuenow` en la barra de progreso, `aria-label` en botones copiar y en el toggle de tema, `aria-current="page"` en el enlace activo del scrollspy. Añadir `:focus-visible` estilado (hoy no existe).
3. **Arreglar nav `m15`**: renombrar el enlace de "Multiagente y arquitectura" a "Arquitectura y despliegue" (refleja el contenido real de microservicios/K8s/serverless) — o bien, si la Fase D añade multiagente, dividir en `m15` (arquitectura) + `m15b` (multiagente).
4. **Footer ampliado**: añadir referencia al repo/tests y a cómo verificar el curso (enlaza el plan de infraestructura: `pytest tests/`), manteniendo la firma "Datawith.AI · Alberto Ruiz".

## Fase B — Refuerzo visual (diagramas para los conceptos clave)

Reutilizar el componente `.flow` existente (y su variante `.step.hl`) — **no añadir SVG/mermaid**, para respetar tu decisión de archivo monolítico sin dependencias. Diagramas a añadir:

1. **El ciclo del agente (m8/m10)**: `Pregunta → Modelo decide → ¿tool? → ejecutar → Modelo responde → (ciclado)`. Un `.flow` con la flecha de retorno dibujada en CSS. Hoy solo se narra.
2. **Pipeline RAG end-to-end (m11/m12)**: `Documento → chunking → embeddings → vector store → (consulta) → retrieval → re-rank → LLM → respuesta`. Unifica lo que hoy está fragmentado en varios `.flow` sueltos en un único diagrama maestro al inicio de la sección RAG.
3. **Grafo LangGraph con su ciclo (m13)**: `START → modelo → [arista condicional] → tools → (vuelve a modelo) → END`. Refleja literalmente el `StateGraph` del archivo `13_langgraph_stategraph.py`.
4. **Human-in-the-loop como pausa (m13b)**: `detectar → aprobar ⏸️(interrupt) → humano responde → Command(resume) → registrar`. Visualiza la mecánica de pausa/reanudar.
5. **Arquitectura de microservicios (m15)**: ya hay un diagrama `.flow` con `svc1/svc2/svc3`; lo completo con el balanceador delante y el estado compartido (vector store, base de datos) detrás, para mostrar el patrón stateless.
6. **Patrón supervisor/multiagente (nuevo, m15b)**: `Usuario → Supervisor → {Agente A | Agente B} → Supervisor → Respuesta`.

## Fase C — Refuerzo pedagógico

1. **Recap por módulo**: un nuevo componente `.recap` (caja compacta, estilo `.box` con un token de color propio, ej. borde izquierdo del nivel) al final de cada `<section>` de módulo con "En una frase: qué aprendiste" + "archivo: `NN_xxx.py`". Refuerza el cierre de cada unidad. Son ~14 recaps.
2. **Botón "volver arriba"**: flotante (bottom-right), aparece tras hacer scroll. CSS mínimo + 5 líneas de JS en la IIFE existente.
3. **Buscador de texto en la página**: un input en el nav que filtra/enmarca términos (`window.find` o resaltado de coincidencias en los `<section>`). Ligero, sin librerías, degrada con elegancia si no hay JS.
4. **Conexión con el plan de infraestructura**: cada `.fileref` existente se enriquece con un badge "✓ testeado" que apunta a `tests/test_offline.py`, y donde aplique, con el ejercicio propuesto correspondiente. Cierra el lazo HTML ↔ código ↔ tests.

## Fase D — Nuevos módulos en el HTML (materializar las brechas)

Contenido nuevo que va DENTRO del HTML (siguiendo el patrón de módulo existente: `<section id>` + `.lvbanner` + texto + `figure.code` + `.box` + quiz):

1. **m15b · Multiagente (supervisor)**: explica el patrón supervisor con LangGraph, con el diagrama de la Fase B.6 y un bloque de código que referencia el nuevo `15_supervisor_multiagente.py` del plan de infraestructura.
2. **m17c · Servir el agente (interfaz)**: cómo exponer un agente por HTTP con FastAPI. Diagrama `Cliente → FastAPI → Agente LangGraph → tools/RAG`. Referencia el nuevo `17_servidor_agente.py`.
3. **Refuerzo del m16 · Observabilidad**: ampliar con la sección de **conteo de tokens/coste real** y **LangSmith tracing** (hoy el m16 es teórico en parte), referenciando el nuevo `16b_observabilidad_langsmith.py`.
4. **Sección m18 (capstone) actualizada**: reflejar el **proyecto modular** (`config.py/rag.py/audit.py/tools.py/graph_builder.py/...`) como "el siguiente paso" del `app.py` actual, con un diagrama de los módulos y sus dependencias.

## Fase E — Integración y verificación

1. **Actualización del índice del nav** para reflejar nuevos módulos (`m15b`, `m17c`).
2. **Nuevo glosario**: añadir términos nuevos (supervisor, multiagente, FastAPI, endpoint, stateless ya existe, ASGI).
3. **Verificación**: abrir el HTML y confirmar que (a) valida como HTML5 razonable, (b) dark mode sigue funcionando, (c) scrollspy sigue marcando bien, (d) los diagramas `.flow` nuevos se ven bien en móvil (scroll horizontal), (e) el buscador y volver arriba funcionan.

---

## Orden de ejecución
A → B → C → D → E. La Fase A es la base y no toca contenido; B y C son aditivas sobre el existente; D depende de que existan los archivos `.py` nuevos (del plan de infraestructura, que retomamos mañana).

## Notas de alcance
- **No** se convierte a generador/markdown (tu decisión: monolítico).
- **No** se añaden dependencias externas (sin mermaid, sin highlight.js): el resaltador propio se respeta.
- **No** se reescribe el contenido existente: se corrige, se amplía y se conecta, manteniendo el tono y los ejemplos de dominio (Gobierno de Datos / Datawith.AI).
- Los diagramas son CSS puro reutilizando `.flow` — coherentes con el sistema de diseño actual.

## Lo que NO incluye
- No genero imágenes reales (PNG/JPG): todo sigue siendo tipográfico/CSS.
- No cambio el proveedor ni los ejemplos de código existentes del HTML.