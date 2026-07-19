# Auditoría end-to-end del curso · ¿forma a un AI Engineer profesional?

**Fecha:** 2026-07-11 · **Rama:** `001-verificador-curso` · **Auditor:** revisión asistida (Claude Code)
**Alcance:** `curso_ejemplos/` completo — `curso-langchain.html` (5819 líneas), 26 ejemplos `NN_*.py`, `README.md`, 3 proyectos (`proyecto_final`, `proyecto_llmops`, `proyecto_retail`), suite de tests y `verificar_curso.py`.
**Método:** mapa exhaustivo del contenido → matriz de competencias contra un marco de rol AI Engineer 2026 → verificación técnica (tests reales, versiones instaladas, precios contra páginas oficiales) → **pasada adversarial** que intenta refutar cada hallazgo antes de darlo por bueno.

---

## 1. Resumen ejecutivo

**Veredicto: SÍ es un curso profesional de AI Engineer.** Cubre el núcleo del rol de forma poco común: no solo explica, sino que **implementa con código y lo protege con tests que corren sin gastar un token** (628 tests offline, todos en verde hoy). La progresión es sólida (Python mínimo → básico → producción → AI Engineer → 2 capstones), tiene instrumentos de evaluación reales (5 quizzes, examen de 24 preguntas, banco de 35 preguntas de entrevista + 4 casos de system design) y dos proyectos integradores de nivel producción (`proyecto_llmops`, `proyecto_retail`).

Las carencias **no están en el núcleo** sino en la frontera (multimodal generativo, voz, GraphRAG, computer use, memoria de largo plazo) y en **higiene de material**, no en la corrección de lo que enseña. La observación más importante para la marca "curso profesional" es de **integridad**: varios conteos de tests están desactualizados en el texto y hay un archivo de ejemplo borrado por accidente. Son defectos de mantenimiento, rápidos de corregir, que hoy contradicen la promesa de rigor que el propio curso hace.

**Nota global: 8.7 / 10** — contenido y pedagogía sobresalientes; penalizado por hallazgos de integridad que un curso que presume de "verificado por N tests" no debería tener.

### Nota por dimensión

| Dimensión | Nota | Comentario |
|---|---|---|
| Fundamentos LLM (m27) | 9 | Tokenización/softmax/muestreo/perplejidad/atención **en código** + RLHF/DPO, KV cache, cuantización, MoE/Mamba en prosa. |
| Prompting (m26b) | 9 | Few-shot, CoT, self-consistency, descomposición + ToT/GoT/CoVe/APE. Con harness antes/después. |
| RAG (m11, m12, m20, m24) | 9 | De in-memory a BM25+coseno+RRF+rerank, multi-query/RAG-Fusion, HyDE/sentence-window, vector DB. Muy completo. |
| Agentes / LangGraph (m8, m10, m13) | 9 | Ciclo ReAct a mano y prebuilt, StateGraph, HITL, persistencia. |
| Herramientas / MCP (m7, m14) | 9 | `@tool`, servidor+cliente MCP en un archivo, offline. |
| Multiagente (m15) | 8 | Patrón supervisor implementado. |
| Evaluación / observabilidad (m16, m16b) | 9 | Datasets, LLM-as-judge, tríada RAG, **eval por trayectoria**, model-vs-product evals, LangSmith, coste. |
| LLMOps (llmops, m24b, m25) | 9 | Proyecto real: FastAPI+SSE, prompts versionados, A/B con lazo cerrado, feedback, caché semántica, guardrails, CI gate, ADRs. |
| Seguridad / guardrails (m23) | 9 | OWASP LLM Top-10, inyección, saneo, red-teaming, privacidad (MIA, PII). |
| Fine-tuning vs RAG (m21) | 8 | Reglas de decisión, dataset→JSONL, espectro de adaptación (PEFT/LoRA/full FT). Conceptual (sin entrenar). |
| Multimodal (m22) | 6 | Solo **entrada** de imagen (visión). Sin generación de imagen, sin audio/voz. |
| Serving / API / streaming / frontend (m17, m25) | 9 | FastAPI, SSE, frontend chat vainilla, concurrencia por thread. |
| Despliegue / infra (m15b, m18b) | 8 | 4 caminos (API/hospedado/cloud gestionado/on-prem), Bedrock/Vertex, vLLM, costes reales. K8s solo conceptual. |
| Elección de modelo/proveedor (m18b) | 10 | Excepcional: tabla de precios verificada, decisión por restricción, cambio por `.env`. |
| Empleabilidad (examen, entrevista, system design) | 9 | Banco de entrevista + 4 casos de system design mapeados a módulos. |
| Ingeniería (specs m19, ADRs, tests m17b) | 9 | SDD con spec-kit, ADRs por decisión, `-m offline`, CI. |
| Memoria del agente | 5 | Solo **checkpointer por `thread_id`** (conversacional). Sin memoria de largo plazo / cross-sesión. |
| **Integridad del material** | **5** | Conteos de tests desactualizados y archivo de ejemplo borrado (§6). |

---

## 2. Metodología y fuentes del benchmark

Se auditó contra el conjunto de competencias que hoy definen el rol *AI Engineer* (quien construye productos sobre modelos de terceros, no quien preentrena): fundamentos operativos del LLM, prompting, salida estructurada, RAG (básico→avanzado), agentes y orquestación, herramientas/MCP, multiagente, memoria, evaluación/observabilidad, LLMOps (CI/CD, versionado de prompts, A/B, feedback, coste, caching), seguridad/guardrails, vector DBs, fine-tuning vs RAG, multimodal, serving/streaming/frontend, despliegue e infraestructura, elección de modelo, system design y prácticas de ingeniería (specs, ADRs, tests).

**Verificación técnica realizada (no de memoria):**
- Suite offline ejecutada: `uv run pytest -m offline` → **628 passed** (22.7 s, cero llamadas a API).
- Versiones instaladas confirmadas contra los pins: `langgraph 1.2.8`, `langchain-core 1.4.8`, `langchain-google-genai 4.2.7`, `langchain-openai 1.3.3`, `langchain-anthropic 1.4.8`, `mcp 1.28.1`.
- Precios de modelos contrastados contra páginas oficiales: la tabla de Google **calza al centavo** (`gemini-3.1-flash-lite` $0.25/$1.50; `gemini-2.5-pro` con tramos $1.25→$2.50 / $10→$15; `gemini-2.5-flash` $0.30/$2.50). La página de Anthropic redirige a planes de consumo (no API), así que las filas de Claude no se re-verificaron numéricamente, pero el match exacto de Google valida la frescura de la tabla ("consultada 2026-07-09").
- `verificar_curso.py` hoy: **verde** (45 anclas, sin DOCTYPE, tabla de modelos == `util.MODELOS_POR_DEFECTO`, `#mapa == §5` con 30 filas).

---

## 3. Matriz de cobertura (competencia → módulo → profundidad)

Leyenda: 🟢 implementado con código+tests · 🟡 prosa/conceptual sólido · 🟠 solo mención de pasada · 🔴 ausente.

| Competencia | Módulo(s) | Nivel |
|---|---|---|
| Invoke/mensajes, temperatura | m1 | 🟢 |
| LCEL, prompts, parsers | m2 | 🟢 |
| invoke/batch/stream + async | m3, m9 | 🟢 |
| Memoria conversacional (checkpointer) | m4, m10, m13 | 🟢 |
| Salida estructurada (Pydantic) | m5 | 🟢 |
| Runnables de composición | m6 | 🟢 *(pero ver §6: archivo borrado)* |
| Herramientas `@tool` | m7 | 🟢 |
| Ciclo agente / routing | m8 | 🟢 |
| Resiliencia (fallbacks, retry, 429) | m9 | 🟢 |
| Agente prebuilt (create_react_agent) | m10 | 🟢 |
| RAG básico (embeddings, retriever, MMR) | m11 | 🟢 |
| RAG avanzado (BM25, RRF, rerank, híbrido) | m12 | 🟢 |
| RAG: transformar la consulta (multi-query, RAG-Fusion, HyDE) | m20 | 🟢 |
| LangGraph a fondo (StateGraph, HITL, persistencia) | m13, m13b | 🟢 |
| MCP servidor+cliente | m14 | 🟢 |
| Multiagente supervisor | m15 | 🟢 |
| Evaluación (datasets, LLM-as-judge, tríada RAG, trayectoria) | m16 | 🟢 |
| Observabilidad (LangSmith, coste) | m16b | 🟢 |
| Repo productivo, runbook, servir | m17 | 🟢 |
| Tests + CI (fake model, `-m offline`) | m17b | 🟢 |
| Fine-tuning vs RAG, espectro de adaptación, JSONL | m21 | 🟡 |
| Seguridad, red-teaming, OWASP LLM Top-10, privacidad | m23 | 🟢 |
| Vector DB producción (HNSW vs IVFFlat, dedup, nprobe) | m24 | 🟢 (HNSW 🟡: descrito, se implementa IVFFlat) |
| A/B de prompts + feedback (lazo cerrado) | m24b | 🟢 |
| Frontend chat SSE | m25 | 🟢 |
| Mapa de ecosistema (LlamaIndex/CrewAI/…) | m26 | 🟡 |
| Prompt engineering como disciplina | m26b | 🟢 |
| Fundamentos LLM (tokenización, muestreo, perplejidad, atención) | m27 | 🟢 |
| RLHF/DPO, KV cache, cuantización, MoE/Mamba | m27, m18b | 🟡 |
| Alucinaciones (taxonomía, detección estilo SelfCheckGPT) | m28 | 🟢 |
| LLMOps end-to-end (proyecto) | llmops | 🟢 |
| Caché semántica como palanca de coste | llmops (ADR-0005) | 🟢 |
| Elección de modelo, despliegue, costes | m18b | 🟢 |
| Cloud gestionado (Bedrock/Vertex/Foundry) | m18b | 🟡 |
| Kubernetes / serverless | m15b | 🟡 (YAML conceptual, sin deploy real) |
| Caso real end-to-end (dato sucio → producción) | m18, m29 | 🟢 |
| SDD / specs / ADRs | m19, docs/adr | 🟢 |
| System design (entrevista) | #entrevista | 🟡 |
| **Prompt caching de proveedor + Batch API (descuentos)** | m18b (de pasada) | 🟠 |
| **Memoria de largo plazo / cross-sesión (store semántico)** | — | 🔴 |
| **Multimodal generativo (imágenes, TTS/STT, voz)** | — | 🔴 |
| **GraphRAG / RAG sobre grafo de conocimiento** | — | 🔴 |
| **Computer use / automatización de navegador** | — | 🔴 |

> **Nota metodológica (pasada adversarial):** la exploración inicial reportó que RLHF/DPO/MoE/cuantización estaban "solo en la entrevista, no en m27". **Es falso** — están en el cuerpo de m27 (líneas 4421–4460) y en m18b. La verificación cruzada lo corrigió antes de convertirlo en un hallazgo. Igualmente se descartó "sin caché" como brecha: la caché semántica está 🟢 en `proyecto_llmops` (ADR-0005).

---

## 4. Fortalezas diferenciales

1. **Todo corre y todo se prueba sin gastar cuota.** 628 tests offline con un modelo *fake* que "recita un guion"; la CI puede correr sin llave. Muy pocos cursos logran esto.
2. **Dos capstones de dominios opuestos.** `proyecto_final` (gobierno de datos, financiera) y `proyecto_retail` (retail Sifrah, catálogo Shopify público real). El m29 enseña la lección que los tutoriales con datos limpios omiten: *el dato real llega sucio y el ETL es donde se gana o se pierde*.
3. **LLMOps de verdad, no diapositivas.** `proyecto_llmops` tiene prompts versionados en YAML, A/B con el lazo cerrado (un grafo por variante), feedback por variante, caché semántica, guardrails/RBAC, evals con CI gate y ADRs 0003–0007.
4. **m18b (elegir modelo) es ejemplar.** Cuatro caminos de despliegue, tabla de precios verificada, ejercicio de estimación de coste mensual resuelto, y la tesis operativa "cambiar de modelo = cambiar el `.env`" respaldada por `util.crear_llm()`.
5. **Honestidad técnica.** El curso avisa de la deprecación de `create_react_agent` (`LangGraphDeprecatedSinceV10`) en m10 y explica la migración a `langchain.agents.create_agent`, en vez de esconderla.
6. **Empleabilidad explícita.** Examen + banco de 35 preguntas de entrevista con respuestas modelo + 4 casos de system design, cada respuesta mapeada al módulo donde se construyó.
7. **Pedagogía consistente.** Plantilla uniforme (◈ definición, ◆ analogía, código con PORQUÉ, ▲ warning, ⛔ cuándo-NO, ▸ practicar, ↺ recap, ✔ checkpoint) y guardián de coherencia automatizado (`verificar_curso.py`).

---

## 5. Brechas priorizadas

### Crítica — ninguna de contenido
El núcleo del rol está cubierto. Lo "crítico" aquí es de integridad y se trata en §6.

### Alta
- **Memoria de largo plazo del agente (🔴).** El curso solo enseña memoria conversacional por `thread_id` (checkpointer). No cubre memoria persistente cross-sesión / semántica (p. ej. `langgraph` `BaseStore`/`InMemoryStore`, "recuerda que el usuario prefiere X entre conversaciones"), que hoy es una competencia esperada. **Recomendación:** un módulo `m30` o una caja en m13 con un ejemplo offline de store de memoria (guardar/recuperar hechos del usuario entre `thread_id` distintos) + tests. Esfuerzo: medio (1 ejemplo + sección + ~10 tests).

### Media
- **Multimodal generativo y voz (🔴).** m22 cubre solo *entrada* de imagen (visión). No hay generación de imágenes ni audio/TTS/STT (voz), cada vez más presentes en productos. **Recomendación:** caja de profundización en m22 (o `m22b`) conceptual + un ejemplo mínimo de STT/TTS con proveedor conmutable. Esfuerzo: medio.
- **Prompt caching de proveedor + Batch API (🟠).** Solo se mencionan de pasada en m18b como palancas de coste. Para un AI Engineer que optimiza factura, merecen tratamiento propio (caché de prompt de Anthropic/OpenAI/Gemini, descuentos por batch async). **Recomendación:** caja en m16b o m18b con el mecanismo y cuándo aplica. Esfuerzo: bajo (solo prosa/tabla).
- **GraphRAG (🔴).** RAG está muy completo salvo la variante sobre grafo de conocimiento, útil cuando las relaciones importan. **Recomendación:** caja conceptual en m20 comparando RAG vectorial vs GraphRAG. Esfuerzo: bajo.

### Baja
- **Kubernetes/serverless (🟡):** m15b es conceptual (YAML de ejemplo, sin deploy real). Aceptable para el alcance del curso; se podría enlazar a un tutorial externo.
- **Computer use / automatización de navegador (🔴):** emergente y específico; opcional. Mención en m26 (ecosistema) bastaría.
- **HNSW (🟡):** descrito y comparado en m24, pero el pipeline implementa IVFFlat. Está bien como está; una nota de "en producción normalmente usarás HNSW (pgvector/Qdrant)" lo redondearía.

---

## 6. Hallazgos de integridad (reproducibles)

Estos son los que más pesan contra la etiqueta "profesional" y son los más baratos de corregir.

### H1 · `06_runnables.py` borrado por accidente y **no protegido por ningún test** — **Alta**
El archivo del ejemplo del m06 está borrado del working tree pero sigue referenciado en 6 lugares. Ningún commit lo elimina (último toque en `8b80f58`), así que es un borrado accidental local.
```bash
git status --short curso_ejemplos/06_runnables.py     # ' D ...'  (borrado, no commiteado)
git log --oneline -- curso_ejemplos/06_runnables.py   # 8b80f58, fa64588  (nunca se borró en git)
grep -rn "06_runnables" curso_ejemplos/README.md curso_ejemplos/curso-langchain.html
#   README.md:58  (tabla §3),  README.md:117 (tabla §5),
#   HTML:1236 (fileref con badge "✓ cubierto por tests"),  HTML:1289,  HTML:5328 (#mapa)
```
Agravante: `test_imports.py` hace *glob* de archivos en disco, así que al no estar el archivo **simplemente no lo prueba** (pasa "en vacío"); y `TestTema06Runnables` prueba la API de LangChain, no el archivo. Por eso la suite sigue verde y el badge **"✓ cubierto por tests"** de la línea 1236 es hoy **falso**. Un alumno que siga el README para correr `06_runnables.py` obtiene *file not found*.
**Fix:** `git checkout HEAD -- curso_ejemplos/06_runnables.py` (recuperable al instante).
> **✔ RESUELTO** (2026-07-11): archivo recuperado; `test_imports.py` ya lo importa (smoke test verde) y el badge "✓ cubierto por tests" vuelve a ser cierto.

### H2 · Conteos de tests desactualizados en todo el material — **Alta**
El texto cita cifras de tests que ya no coinciden con la suite real. La cifra **"383 tests"** es el *baseline viejo* (antes de los módulos AI Engineer) y aparece ~7 veces; la suite hoy pasa **628**.
```bash
uv run pytest -m offline -q         # 628 passed
grep -rn "383 tests\|44 tests\|197 tests" curso_ejemplos/README.md curso_ejemplos/curso-langchain.html
```
Los conteos reales se obtienen con `pytest --collect-only` (NO con `grep -c "def test"`, que ignora los tests parametrizados — por eso una revisión con grep subcuenta):

| Afirmación en el material | Dónde | Real (pytest) | Estado |
|---|---|---|---|
| "383 tests" (global) | README §6/§2, HTML m17b×3, #mapa | 628 | ❌ stale → corregido a 628 |
| "197 tests" (`proyecto_llmops`) | HTML llmops fileref | 232 | ❌ → corregido a 232 |
| "44 tests" (`proyecto_final`) | HTML m17b/m18 ×4, README §8 | 44 | ✅ correcto (el grep decía 42) |
| "61 tests" (`proyecto_retail`) | HTML m29, README | 61 | ✅ |
| "25 tests" (`TestTema12`) | HTML/README #mapa | 25 | ✅ |
Suma por carpeta (pytest `--collect-only`): `tests/` 291 + `proyecto_final` 44 + `proyecto_llmops` 232 + `proyecto_retail` 61 = **628**.
Causa raíz: `verificar_curso.py` valida anclas, DOCTYPE, tabla de modelos y `#mapa==§5`, pero **no** los conteos de tests, así que derivaron sin control.
**Fix:** actualizar las cifras (hecho). Un chequeo automático en `verificar_curso.py` se descartó a propósito: hoy es puro/stdlib y no corre pytest; meterle `--collect-only` rompería su diseño rápido y sin dependencias. Mejor mantener la disciplina de actualizar la cifra al añadir tests.
> **✔ RESUELTO** (2026-07-11): 383→628 (5 sitios en HTML + 2 en README) y 197→232 (fileref de llmops); `proyecto_retail/tests/` añadido a la lista de carpetas de m17b. Verificador verde tras el cambio.

### H3 · `proyecto_retail/` sin versionar — **Media**
El proyecto entero del m29 está *untracked*; no está en git.
```bash
git status --short curso_ejemplos/proyecto_retail   # '?? curso_ejemplos/proyecto_retail/'
git ls-files curso_ejemplos/proyecto_retail          # (vacío)
```
El HTML y el README ya lo referencian como material del curso. Si el repo se clona limpio, el m29 apunta a una carpeta que no existe.
**Fix:** commitear `proyecto_retail/`.
> **⏳ PENDIENTE DE ALBERTO** (2026-07-11): al revisar el working tree apareció que **no es solo `proyecto_retail/` lo que falta commitear**. El commit `30bba72` (m29) quedó incompleto: hay ~142 líneas sin commitear en `curso-langchain.html`, los `testpaths` de `pyproject.toml` y cambios de `README.md`, todos del mismo conjunto m29/retail. Commitear a ciegas mezclaría ese trabajo previo con las correcciones de esta auditoría. Decisión: **no commitear automáticamente**; Alberto define el corte de commits (ver §7, nota de commits).

### H4 · `pyproject.toml` no incluye `langchain` pese a recomendar `create_agent` — **Baja**
m10 recomienda migrar a `from langchain.agents import create_agent`, pero el paquete `langchain` no está en dependencias (`ModuleNotFoundError: No module named 'langchain'`), así que un alumno que siga la recomendación no puede ejecutarla sin `uv add langchain`. El curso lo dice ("y añadir el paquete `langchain`"), pero conviene o bien incluirlo, o bien dejar la nota más explícita.
> **✔ RESUELTO** (2026-07-11): se eligió la opción de menor riesgo — no inflar dependencias base ni regenerar `uv.lock`, sino hacer la nota de m10 accionable con el comando exacto (`uv add langchain`).

---

## 7. Backlog recomendado (si se aprueba una fase 3)

Ordenado por relación impacto/esfuerzo. **Nada de esto bloquea que el curso ya sea profesional hoy** — el bloque A lo hace *impecable*.

**A. Higiene — ✔ APLICADO el 2026-07-11 (salvo el commit, ver nota)**
1. ✔ `06_runnables.py` recuperado (`git checkout HEAD -- …`). Suite verde (628).
2. ✔ Conteos actualizados: 383→628 y 197→232; `proyecto_final` (44) y `proyecto_retail` (61) ya eran correctos. *(El "44→42" del borrador era un error de contar con grep; pytest colecta 44.)*
3. ⏳ Commit **pendiente de Alberto**: el corte de commits lo decide él porque el working tree mezcla el m29/retail sin terminar con estas correcciones.
4. ✔ Nota de m10 hecha accionable (`uv add langchain`), sin tocar `pyproject.toml`/`uv.lock`.

> **Nota de commits.** Cambios en el working tree hoy: (i) *previos de Alberto* — el m29/retail sin commitear (HTML ~142 líneas, `pyproject.toml` testpaths, `README.md`, `proyecto_retail/` untracked); (ii) *de esta auditoría* — conteos en HTML/README, nota de m10, y este informe (`docs/auditoria-ai-engineer-2026-07.md`). Los de tipo (ii) sobre HTML/README están intercalados con los de tipo (i) en los mismos archivos, así que no se pueden separar en commits limpios sin `git add -p`. Recomendación: Alberto commitea primero el conjunto m29/retail (cierra `30bba72`), luego un commit `docs/fix(curso): auditoría AI Engineer + sincronizar conteos de tests`.

**B. Cierre de brechas de contenido (por prioridad)**
5. Módulo/caja de **memoria de largo plazo del agente** con ejemplo offline + tests. *(medio)*
6. Cajas conceptuales de bajo esfuerzo: **prompt caching + Batch API** (m16b/m18b), **GraphRAG** (m20), **HNSW en producción** (m24). *(bajo cada una)*
7. **Multimodal generativo / voz**: caja en m22 + ejemplo mínimo TTS/STT conmutable. *(medio)*

---

## 8. Conclusión

El curso **cumple** el objetivo: guía a un estudiante desde Python mínimo hasta poder diseñar, construir, evaluar, asegurar y operar soluciones de IA en producción, con dos casos reales end-to-end y preparación explícita para entrevistas. Está por encima de la media del mercado en rigor (todo testeado offline), en honestidad técnica (avisa de deprecaciones y de que los precios caducan) y en ingeniería (specs, ADRs, CI gate).

Lo que hoy separa "muy bueno" de "impecable" **no es contenido faltante del núcleo**, sino cuatro asuntos de mantenimiento (§6) — un archivo borrado, conteos de tests viejos, un proyecto sin commitear y una dependencia ausente — todos corregibles en una tarde. Cerrados esos, y con la memoria de largo plazo como principal adición de contenido, el curso queda como referencia profesional completa de AI Engineer.

---

## 9. Actualización 2026-07-11 · Bloque B aplicado (cierre de brechas de contenido)

Tras el bloque A (§6), se ejecutó el **bloque B** del backlog (§7). Cambios:

- **✔ Memoria de largo plazo — nuevo módulo `m30` (brecha 🔴→🟢).** Sección HTML con plantilla completa + `30_memoria_largo_plazo.py` offline (`InMemoryStore` de LangGraph, `put`/`search`, namespaces por `user_id`, contraste checkpointer-vs-store) + 10 tests `TestTema30*` + fila en #mapa/§5/§3 + nav + cheat. API verificada por introspección contra `langgraph 1.2.8` (no de memoria).
- **✔ Voz / multimodal generativo (brecha 🔴→🟢).** Caja ◈ en `m22` (oír / hablar / generar imágenes) + `22b_voz.py` offline (bloque `media`/`mime_type` para audio de entrada —formato verificado contra `langchain-google-genai`— y payload TTS) + 4 tests `TestTema22bVoz` + fila en #mapa/§5/§3.
- **✔ Tres cajas conceptuales (🟠→🟡):** prompt caching + Batch API en `m18b`, GraphRAG en `m20`, HNSW-en-producción en `m24` (solo HTML, antes del checkpoint de cada módulo).

**Nuevo baseline:** **642 tests** offline en verde (antes 628; +14). Verificador coherente: 46 anclas, `#mapa == §5` con **32 filas**. Cero deps nuevas.

**Cierre de los dos pendientes de baja prioridad (mismo día):**
- **✔ Computer use (🔴→🟡):** caja ◈ en `m14` (cuando no hay API, el agente opera la GUI; riesgos y por qué es el último recurso, con sandbox + HITL).
- **✔ Deploy real K8s (🟡→🟡+):** caja ◈ en `m15b` (qué falta más allá del manifiesto de ejemplo: probes, HPA, secrets, ingress, requests/limits).

Ambas solo-HTML, sin deps ni ejemplos ejecutables (no son testeables offline). Baseline sin cambios: 642 tests, verificador verde (46 anclas, 32 filas). Con esto **el backlog de la auditoría queda cerrado**.
