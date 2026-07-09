# CLAUDE.md — Proyecto de estudio LangChain / RAG / LangGraph

Guía de contexto para trabajar en este repo. Chat en español, código en inglés
(salvo los ejemplos didácticos del curso, que van comentados en español a propósito).

## 🎯 Qué es este proyecto
Repositorio de **aprendizaje** de LangChain, RAG y LangGraph (nivel intermedio→avanzado).
Contiene experimentos sueltos (notebooks y scripts) y un **curso estructurado** con
ejemplos ejecutables y un proyecto final.

## 🧰 Stack y entorno
- **Python** con **`uv`** (nunca `pip` directo). Ejecutar: `uv run python <archivo>`.
- Entorno virtual: `.venv/` (en la raíz de este proyecto).
- **Modelos**: Google Gemini vía `langchain-google-genai` (`gemini-2.0-flash`;
  embeddings `gemini-embedding-001`). Algunos experimentos antiguos usan Qwen (`ChatTongyi`).
- Versiones instaladas: `langchain 1.3`, `langchain-core 1.4`, `langgraph 1.2`,
  `langchain-google-genai 4.2`, `pydantic 2`, `python-dotenv`.
- **Llave**: `GOOGLE_API_KEY` en un `.env` (NO commitear). Plantilla en `curso_ejemplos/.env.example`.
- ⚠️ El plan gratuito de Gemini tiene cuota; es común ver **429 RESOURCE_EXHAUSTED**.
  No es un bug del código: esperar unos minutos o usar `gemini-2.5-flash`.

## 📚 El curso (lo principal y más actualizado)

### Curso HTML (Artifact)
- URL: https://claude.ai/code/artifact/4c3cc6d1-cb2d-45c8-9dfd-a04214bd722e
  (la URL anterior `574784a7-…` fue borrada; esta la reemplaza desde 2026-07-08).
- **Fuente canónica en el repo**: `curso_ejemplos/curso-langchain.html` (commiteable).
  Se edita ese archivo y se **republica al MISMO `url`** con la herramienta Artifact
  (favicon 🔗). Título estable: "Curso: LangChain, RAG y LangGraph desde cero".
- Estructura: 4 niveles (Básico / Intermedio / Avanzado / Producción) + Proyecto final + Referencia.
  Diseño "cuaderno de ingeniería", doble tema claro/oscuro, resaltado de código por JS,
  navegación lateral por niveles. Cada tema tiene un aviso "📋 Copia y ejecuta".
- Los módulos 12–17 están expandidos a profundidad de producción (2026-07-08): pipeline RAG
  por etapas + chunking + RRF + precision@k, LangGraph con persistencia/auditoría/escalada
  a humano, MCP con servidor mínimo y tabla de seguridad, microservicios con manifiesto
  K8s explicado línea a línea, observabilidad con LLM-as-judge y regresiones, repo
  productivo con plantilla ADR y runbook. Incorpora patrones del repo de EricBz.
- Cierre del nivel Producción (2026-07-09): el HTML ya engancha **todos** los archivos
  ejecutables que existían pero no se mencionaban. Módulo 16: sección "¿cuánto me está
  costando?" con `16b_observabilidad_langsmith.py` (tokens → dólares, degradación en
  cascada, aviso de que la tabla de precios caduca). Módulo 17: fileref a `docs/` y
  sección "Servir el agente" con `17_servidor_agente.py` (concurrencia por `thread_id`,
  arranque caro en el `lifespan`, 429 → HTTP 503); el snippet es fiel al archivo real.
  Módulo 18: el fileref apunta a `main.py` (no a `app.py`) y explica que el capstone
  modular **es** el Módulo 17 hecho realidad (inyección por parámetro → 43 tests sin API).
- Secciones faltantes escritas (2026-07-09): el menú lateral enlazaba a `#m17b` y
  `#ejercicios` **pero esas secciones no existían** (enlaces muertos). Ya están:
  **17b "Tests y CI"** (por qué testear IA es distinto, el `ModeloFalso` que recita un
  guion, el marcador `offline` + `--strict-markers`, y por qué la CI no tiene la llave)
  y **"Ejercicios"** (tabla de los 7, método de pistas progresivas, criterio de aceptación).
  ⚠️ Al añadir enlaces al `nav`, crear la `<section id="…">` en el mismo cambio.
  `m17b` cuenta como módulo (regex `/^m\d+b?$/` en el JS de progreso); `ejercicios` no.
- Auditoría plan↔repo↔HTML (2026-07-09): el plan (`curso_ejemplos/.zcode/plans/`) está
  implementado al 100%. Se corrigieron 3 desfases del HTML: la tabla de `#mapa` apuntaba a
  experimentos viejos (`studylangchain/*.py`, **inexistentes**), el cheat sheet no llegaba
  más allá del módulo 16, y el glosario no definía *Supervisor* ni *Modelo falso*.
  ⚠️ **`#mapa` es un espejo de la tabla §5 del `curso_ejemplos/README.md`**: si cambia una,
  actualizar la otra. Los `.py` de `curso_ejemplos/` son la versión canónica; los notebooks
  de la raíz son el borrador histórico.
- Estructura y aprendizaje (2026-07-09, plan `plan-sess_65d88ad7-…`): accesibilidad
  (`role="progressbar"` + `aria-valuenow`, `aria-current` en el scrollspy, `aria-label` en
  nav/tema/botones copiar, `.sr-only`), **buscador del índice** (input `#navq` que filtra el
  nav por el texto real de cada `<section>`; usa el atributo `hidden`, por eso hacen falta
  las reglas `nav a[hidden]` y `.navsec[hidden]` — `nav a` es `display:flex` y ganaría),
  **botón volver arriba** (`#toTop`), **21 recaps** "En una frase" (`.recap.lN` al final de
  cada `.col`), **badge `✓ cubierto por tests`** en los 19 filerefs de ejemplos numerados, y
  **6 diagramas nuevos** en `.flow` puro (ciclo del agente m10, pipeline RAG en dos caminos
  m11, grafo `StateGraph` m13, human-in-the-loop m13b, microservicios con balanceador +
  estado compartido m15, `POST /chat` m17, módulos del capstone m18). También `.flowcap`
  (rótulo sobre un `.flow`).
  ⚠️ **NO envolver el HTML en `<!DOCTYPE>`/`<html>`/`<head>`** (lo pedía la Fase A.1 del
  plan): la herramienta Artifact ya inyecta esa carcasa al publicar, y añadirla duplicaría
  las etiquetas. El archivo empieza en `<title>` a propósito. Consecuencia: abrir el `.html`
  suelto con `file://` muestra los acentos rotos (sin `charset`); la vista buena es el Artifact.
- Trampa de `uv` documentada en el curso (2026-07-09): el Módulo 00 mandaba `uv init` + `uv add`
  pero no explicaba que **`uv run` solo instala lo declarado en `dependencies`**. Quien salta los
  `uv add` obtiene `Creating virtual environment` + `ModuleNotFoundError: dotenv` y cree que falló
  la instalación. Añadidos: aviso `.box warn` con el síntoma exacto, `.box analogy` con la regla
  "uv usa el `pyproject.toml` más cercano hacia arriba" + `uv run python -c "import sys; print(sys.prefix)"`
  para diagnosticar, `pwd` como paso 1 de la verificación, y 2 filas nuevas en `#faq`.
  Los dos caminos válidos: construir en `mi-curso-ia/` con `uv add`, o correr los ejemplos en
  `curso_ejemplos/` con `uv sync --extra dev`. No mezclarlos.
- ℹ️ El `.env` real vive en la **raíz** del proyecto, no en `curso_ejemplos/`. Da igual:
  `load_dotenv()` sube directorios (`find_dotenv`) y lo encuentra desde ambos sitios.
- Capa didáctica (2026-07-08): módulo **0b "Python mínimo"** para no-programadores,
  **4 quizzes** de autoevaluación por nivel (JS offline), **soluciones plegables**
  (`details.sol`) en cada "Para practicar", **salidas esperadas** (`figure.code.output`)
  bajo los bloques clave, botón **copiar** por bloque, **progreso persistente** por
  módulo (localStorage `curso-lc-progress`, contadores en sidebar), plan de estudio
  en 8 sesiones (módulo 00), secciones **FAQ de errores** (`#faq`) y **cheat sheet +
  cambio de proveedor** (`#cheat`).

### Ejemplos ejecutables — `curso_ejemplos/`
Cada archivo es **autónomo**, comentado sección por sección (Finalidad + Lógica paso a paso),
con **cada import explicado**, validación de `GOOGLE_API_KEY`, estructura `main()` y manejo de 429.

| Archivo | Tema |
|---------|------|
| `01_primer_modelo.py` | invoke + tipos de mensaje |
| `02_prompts_lcel.py` | prompts + LCEL (`\|`) |
| `03_interfaz_unificada.py` | invoke / batch / stream (+ async) |
| `04_memoria.py` | memoria con MessagesPlaceholder |
| `05_salida_estructurada.py` | Pydantic + `with_structured_output` |
| `06_runnables.py` | Parallel / Passthrough / Lambda |
| `07_herramientas.py` | `@tool` (offline, no gasta cuota) |
| `08_routing.py` | ciclo completo A→D + ToolMessage |
| `09_resiliencia_async.py` | `with_fallbacks`, `with_retry`, async |
| `10_agente.py` | `create_react_agent` + memoria + streaming |
| `11_rag.py` | RAG con `InMemoryVectorStore` (usa `datos_rag.txt`) |
| `12_rag_hibrido_rerank.py` | búsqueda híbrida BM25+vectorial, fusión RRF, re-ranking (**100% offline**) |
| `13_langgraph_stategraph.py` | `StateGraph` desde cero |
| `13b_human_in_the_loop.py` | `interrupt()` + `Command(resume=…)` — pausa/aprobación humana (**offline**) |
| `14_mcp_servidor_cliente.py` | servidor FastMCP + cliente MCP en un archivo (**offline**) |
| `15_supervisor_multiagente.py` | patrón supervisor con LangGraph, aristas condicionales (**offline**) |
| `16_evaluacion.py` | evaluación con dataset + LLM-as-judge opcional (corre sin llave) |
| `16b_observabilidad_langsmith.py` | tracing LangSmith + tokens + coste; degradación graceful (**offline**) |
| `17_servidor_agente.py` | FastAPI `POST /chat` sobre el proyecto final (`uv sync --extra ui`) |

Apoyo: `pyproject.toml` (canon de deps), `uv.lock`, `requirements.txt` (compat),
`.env.example`, `datos_rag.txt`, `util.py`, `README.md`.

### Calidad: tests y CI
- **141 tests, 100% offline** (no gastan cuota). Correr: `uv run pytest -m offline`.
  - `tests/test_imports.py` — importa todos los ejemplos (detecta roturas de versión).
  - `tests/test_offline.py` — lógica no-LLM por tema (BM25/RRF, HITL, MCP, supervisor, costes).
  - `tests/test_util.py` — lógica compartida.
  - `proyecto_final/tests/` — 43 tests; usan un **modelo falso** (`ModeloFalso` en
    su `conftest.py`) que recita un guion, para ejercitar el grafo completo sin API.
- CI en `.github/workflows/ci.yml`: pytest `-m offline` en Python 3.11 y 3.12. Nunca llama a la API.
- ⚠️ `uv run` requiere `[tool.uv] package = false` en el pyproject (el curso son
  scripts sueltos, no un paquete instalable).

### Ejercicios — `curso_ejemplos/ejercicios/`
7 ejercicios con enunciado, pistas progresivas, criterio de aceptación y
`soluciones/` aparte. Los de los temas 12 y 13 son 100% offline y sus soluciones
(`solucion_12_rerank.py`, `solucion_13_hitl.py`) son **ejecutables**.

### Documentación de operación — `curso_ejemplos/docs/`
- `README_runbook.md` — 429, `.env`, depurar un grafo (`app.get_state`), rollback.
- `adr/0001-vector-store.md`, `adr/0002-re-ranker.md`, `adr/0000-plantilla.md`.

### Proyecto final — `curso_ejemplos/proyecto_final/`
Asistente de **Gobierno de Datos (financiera)**: RAG + herramientas + salida
estructurada (Pydantic `HallazgoCalidad`) + agente con memoria + **auditoría**
(escribe `hallazgos_auditoria.log`). Doc en su `README.md`.

**Modularizado** (antes era un `app.py` de 158 líneas que llamaba a la API al importarse):

| Módulo | Responsabilidad |
|--------|-----------------|
| `config.py` | rutas, modelos, constantes, `validar_entorno()`. **Nada se ejecuta al importar** |
| `rag.py` | `trocear`, `leer_normativa`, `construir_retriever` (única que llama a la API), `contexto` |
| `audit.py` | `HallazgoCalidad` (con `field_validator` de severidad), `formatear_linea` (pura), `registrar_auditoria` (append), `leer_auditoria` |
| `tools.py` | `crear_tools(llm, evaluador, retriever, ruta_auditoria)` — fábrica con inyección |
| `state.py` | `EstadoAgente(MessagesState)` |
| `persistence.py` | `crear_checkpointer()` (MemorySaver; receta de Sqlite/Postgres comentada) |
| `graph_builder.py` | `construir_agente(...)` (todo por parámetro) y `construir_agente_real()` |
| `main.py` | punto de entrada (demo de 2 turnos) |
| `app.py` | shim de compatibilidad → `main.py` |

⭐ La regla que lo hace testeable: `construir_agente()` recibe modelo, evaluador y
retriever **por parámetro**. Por eso `tests/` puede pasarle un `ModeloFalso`.

Decisiones de diseño del capstone: `create_react_agent` (robusto) en la app ejecutable;
el nivel avanzado del curso explica además la variante con `StateGraph` y human-in-the-loop.
⚠️ `create_react_agent` emite un `LangGraphDeprecatedSinceV10` (se movió a
`langchain.agents.create_agent`); migrar requiere añadir el paquete `langchain`.

## ▶️ Cómo correr (puesta en marcha)
```bash
cd /Users/lbeto/proyectos/spec-sdd/studylangchainnivelinter/curso_ejemplos
uv sync --extra dev                                  # canon: pyproject.toml
cp .env.example .env                                 # editar y poner GOOGLE_API_KEY
uv run pytest -m offline                             # 141 tests, sin cuota
uv run python 07_herramientas.py                     # verificación offline
uv run python proyecto_final/main.py                 # proyecto final (app.py hace lo mismo)
```

## 🗂️ Experimentos previos (referencia, base del curso)
- `routing*.py`, `funcionaconver*.py` — tool calling y agente conversacional (con versiones `_mejorado` y `_v3_streaming`).
- Notebooks: `extraction.ipynb`, `Tagging.ipynb` (salida estructurada), `fallbacks.ipynb`,
  `chaincompleja.ipynb` (runnables/RAG), `interfazunificada.ipynb` (async/batch/stream), `functioncall.ipynb`.
- `proyectorag/app_rag.py` — RAG con PDFs (tiene su propio venv `mi_rag`).

## 🤝 Convenciones al trabajar aquí
- Ejecutar siempre con `uv run`.
- Los ejemplos del curso priorizan **claridad didáctica**: comentarios en español,
  imports explicados, robustez (validar llave, capturar 429). Mantener ese estilo.
- Al tocar el curso HTML: **republicar al mismo `url`** para conservar el enlace.
- Verificar cambios con `uv run python -m py_compile <archivos>` y, cuando haya cuota,
  ejecutando el script afectado.

## 📌 Repo de referencia externo
- https://github.com/EricBz/AiEngineering_Comision102110 — aportó ideas de auditoría,
  evaluación con LangSmith/tests y LangGraph Platform (`langgraph.json`).
