# 📚 Ejemplos del curso — listos para copiar y ejecutar

Cada archivo es **autónomo**: lo abres en VS Code, lo corres y funciona solo.
Están comentados **sección por sección** para que entiendas cada línea.

Y todo está **verificado por 886 tests** que corren sin gastar un solo token
(ver [§6](#6-cómo-se-verifica-que-esto-funciona)).

## 1) Requisitos (una sola vez)

```bash
git clone https://github.com/Kratos2210/cursoIA.git
cd cursoIA/curso_ejemplos
cp .env.example .env       # edita y pon tu llave de https://aistudio.google.com
uv sync                    # instala todo desde pyproject.toml (el canon)
uv run python env_utils.py # ¿está todo listo? (añade --ping para llamar de verdad)
```

> 🧰 ¿Usas pip en vez de uv, necesitas un extra concreto o algo se rompió?
> **[SETUP.md](SETUP.md)** reúne las dos rutas de instalación, la tabla de extras
> y todo el troubleshooting en un solo sitio.

> `pyproject.toml` + `uv.lock` son la receta reproducible.
> `requirements.txt` se mantiene solo por compatibilidad con `pip install -r`.

> ⚡ **La cuota de Gemini es cortísima.** *Todos* los ejemplos llaman a
> `util.crear_llm()`, que lee el proveedor del `.env`. Con dos líneas
> (`LLM_PROVIDER=groq` + `GROQ_API_KEY`, [llave gratis](https://console.groq.com/keys))
> el curso entero pasa al modelo por defecto de Groq sin tocar una sola línea de código.
> También hay `LLM_PROVIDER=ollama` (en tu máquina, sin llave).

> 🧭 **El RAG es la excepción.** Groq no ofrece embeddings, así que los temas 11 y
> 12 y el proyecto final seguirían gastando `GOOGLE_API_KEY` solo para vectorizar.
> Salida sin cuota: `uv sync --extra emb` + `EMBEDDINGS_PROVIDER=fastembed`, que
> los calcula en tu máquina. Ver [§9](#9-cambiar-de-proveedor-groq-ollama-fastembed).

## 2) Cómo ejecutar cualquier ejemplo

Desde **dentro** de `curso_ejemplos/` (aquí vive el `pyproject.toml` que `uv` necesita):

```bash
uv run python 01_primer_modelo.py
```

> ¿Dudas de dónde estás parado? `uv run python -c "import sys; print(sys.prefix)"`
> debe terminar en `curso_ejemplos/.venv`. Si no, te falta un `cd`.

**¿Sin llave o sin cuota?** Empieza por los offline: `07`, `12`, `13b`, `14`,
`15`, `16` y `16b`. No gastan nada — y los temas 12 y 13b son, no por
casualidad, los que más enseñan sobre ingeniería de RAG y agentes.

## 3) Índice de ejemplos

La columna «Cuota» se refiere al proveedor que tengas activo: con
`LLM_PROVIDER=groq` gastas cupo de Groq, no de Gemini.

| Tema | Archivo | Qué aprendes | Cuota |
|------|---------|--------------|-------|
| 01 · Primer modelo | `01_primer_modelo.py` | invoke + tipos de mensaje | Sí |
| 02 · Prompts + LCEL | `02_prompts_lcel.py` | plantillas y el operador `\|` | Sí |
| 03 · Interfaz unificada | `03_interfaz_unificada.py` | invoke / batch / stream | Sí |
| 04 · Memoria | `04_memoria.py` | recordar la conversación | Sí |
| 05 · Salida estructurada | `05_salida_estructurada.py` | Pydantic + `with_structured_output` | Sí |
| 06 · Runnables | `06_runnables.py` | Parallel / Passthrough / Lambda | Sí |
| 07 · Herramientas | `07_herramientas.py` | `@tool` | **No** |
| 08 · Routing | `08_routing.py` | el ciclo completo A→D | Sí |
| 09 · Resiliencia + async | `09_resiliencia_async.py` | fallbacks, retry, async | Sí |
| 10 · Agente (prebuilt) | `10_agente.py` | `create_agent` + memoria | Sí |
| 10b · Middleware de agentes | `10b_middleware.py` | middleware: resumen · PII · aprobación humana | **No** |
| 11 · RAG | `11_rag.py` | responder desde un documento | Sí (chat **+ embeddings**) |
| 12 · RAG en profundidad | `12_rag_hibrido_rerank.py` | BM25 + vectorial, RRF y re-ranking | **No** |
| 13 · LangGraph a fondo | `13_langgraph_stategraph.py` | `StateGraph` desde cero | Sí |
| 13b · Human-in-the-loop | `13b_human_in_the_loop.py` | `interrupt()` + `Command(resume=…)` | **No** |
| 14 · MCP | `14_mcp_servidor_cliente.py` | servidor FastMCP + cliente en un archivo | **No** |
| 15 · Multiagente | `15_supervisor_multiagente.py` | el patrón **supervisor** con LangGraph | **No** |
| 16 · Evaluación | `16_evaluacion.py` | dataset + métrica + LLM-as-judge opcional | Opcional |
| 16b · Observabilidad | `16b_observabilidad_langsmith.py` | tracing, tokens y **coste real** | **No** |
| 17 · Servir el agente | `17_servidor_agente.py` | FastAPI: `POST /chat` con memoria por usuario | Sí |
| 20 · RAG avanzado | `20_rag_avanzado.py` | multi-query + RAG-Fusion (RRF sobre variantes) | **No** |
| 21 · Fine-tuning vs RAG | `21_fine_tuning.py` | decidir enfoque + dataset de chat a JSONL | **No** |
| 22 · Multimodal | `22_multimodal.py` | enviar texto + imagen a un modelo con visión | Sí |
| 22b · Voz (audio in/out) | `22b_voz.py` | audio de entrada (STT) · síntesis de voz (TTS) · generación multimodal | No |
| 23 · Seguridad | `23_seguridad.py` | red-teaming OWASP LLM: inyección, saneo, secretos | **No** |
| 24 · Vector DBs | `24_vector_db.py` | dedup por hash + índice IVFFlat (recall↔velocidad) | **No** |
| 26a · Anatomía del prompt | `26a_anatomia_prompt.py` | rol · tarea · contexto · formato · delimitadores · prompt de sistema | **No** |
| 26b · Prompt engineering | `26b_prompt_engineering.py` | few-shot · CoT · self-consistency · descomposición | **No** |
| 27 · Fundamentos del LLM | `27_fundamentos_llm.py` | tokenización BPE · softmax/temperatura · top_k/top_p · perplejidad | **No** |
| 28 · Desafíos y alucinaciones | `28_alucinaciones.py` | taxonomía causa→mitigación · detector de inconsistencia · fragilidad | **No** |
| 29 · Caso real 2: retail | `29_caso_retail.py` | ETL de catálogo Shopify · filtros duros · grounding de precios · eval | **No** |
| 30 · Memoria de largo plazo | `30_memoria_largo_plazo.py` | store vs checkpointer · hechos del usuario entre conversaciones · namespaces | **No** |

**Proyecto final:** [`proyecto_final/`](proyecto_final/) — el asistente de
Gobierno de Datos, repartido en 8 módulos y con 44 tests propios.

**Proyecto retail:** [`proyecto_retail/`](proyecto_retail/) — el caso del m29
(asistente de compras Sifrah) llevado a un proyecto LLMOps organizado: el LLM
cableado de verdad (m05), guardrail de precios, caché semántico, A/B de prompts,
evals con CI gate, serving FastAPI/SSE y ADRs. 127 tests, 100% offline.

## 4) Ejercicios

Leer código no enseña a escribirlo. En [`ejercicios/`](ejercicios/) hay 19
ejercicios con enunciado, **pistas progresivas**, criterio de aceptación
verificable y solución aparte —incluidos los de temas avanzados (MCP, patrón
supervisor, evaluación, coste, multimodal, alucinaciones y el caso retail).

Los que no puedes saltarte —y no gastan cuota— son
[`ejercicio_12_rerank.md`](ejercicios/ejercicio_12_rerank.md) (predice el ranking
antes de ejecutarlo) y [`ejercicio_13_hitl.md`](ejercicios/ejercicio_13_hitl.md);
y en la recta final, buena parte de los avanzados (14, 15, 16b y 17) también son
100% offline.

Ningún ejercicio cablea el proveedor: llaman a `util.crear_llm()`, que lee
`LLM_PROVIDER` del `.env`. Cuando Gemini te dé un 429, pásate a Groq sin tocar
código ([§9](#9-cambiar-de-proveedor-groq-ollama-fastembed)).

## 5) Mapa: concepto → archivo → ejercicio → test

La columna de tests es la que hace que esto sea material de estudio y no un
montón de scripts: **cada concepto tiene una prueba que lo defiende**.

| Concepto | Ejemplo | Ejercicio | Test que lo protege |
|----------|---------|-----------|---------------------|
| Mensajes e `invoke` | `01` · `02` · `03` | — | `test_imports.py` |
| Memoria de conversación | `04` | [04](ejercicios/ejercicio_04_memoria.md) | `test_agente.py::test_el_agente_recuerda_el_turno_anterior` |
| Salida estructurada | `05` | [05](ejercicios/ejercicio_05_estructurada.md) | `test_offline.py::TestTema05SalidaEstructurada` |
| Runnables / LCEL | `06` | — | `test_offline.py::TestTema06Runnables` |
| Herramientas (`@tool`) | `07` · `08` | [07](ejercicios/ejercicio_07_tools.md) | `test_offline.py::TestTema07Herramientas` |
| Resiliencia (429, retry) | `09` | — | `test_util.py::TestEsErrorCuota` |
| 🏗 Proyecto: contrato JSON + filtro + métricas + fallback | `09b` | — | `test_offline.py::TestTema09bProyectoTexto` (6 tests) |
| Agente ReAct | `10` | — | `test_agente.py::TestAgenteCompleto` |
| Middleware de agentes | `10b` | — | `test_10b_middleware.py` |
| RAG: trocear y unir | `11` | [11](ejercicios/ejercicio_11_rag.md) | `test_offline.py::TestTema11Rag` |
| BM25 · coseno · RRF · re-rank | `12` | [12](ejercicios/ejercicio_12_rerank.md) | `test_offline.py::TestTema12*` (25 tests) |
| Re-ranker REAL (cross-encoder ONNX, sin torch) | `rerank/rerank_real.py` | [12](ejercicios/ejercicio_12_rerank.md) | — (companion, fuera del gate, ADR-0008) |
| `StateGraph` (nodos y aristas) | `13` | — | `test_offline.py::TestTema13bHumanInTheLoop` |
| Human-in-the-loop | `13b` | [13](ejercicios/ejercicio_13_hitl.md) | `test_offline.py::TestTema13bHumanInTheLoop` |
| MCP (servidor + cliente) | `14` | [14](ejercicios/ejercicio_14_mcp.md) | `test_offline.py::TestTema14Mcp` |
| Patrón supervisor | `15` | [15](ejercicios/ejercicio_15_supervisor.md) | `test_offline.py::TestTema15Supervisor` |
| Evaluación con dataset | `16` | [16](ejercicios/ejercicio_16_evaluacion.md) | *el propio ejemplo es la métrica* |
| Tokens, coste y tracing | `16b` | [16b](ejercicios/ejercicio_16b_costes.md) | `test_offline.py::TestTema16bObservabilidad` |
| Servir por HTTP | `17` | [17](ejercicios/ejercicio_17_api.md) | `test_imports.py` |
| Elegir modelo y proveedor | `util.py` | — | `test_util.py::TestProveedoresNuevos` |
| Auditoría / trazabilidad | `proyecto_final/audit.py` | [🏆](ejercicios/ejercicio_proyecto.md) | `proyecto_final/tests/test_audit.py` |
| Inyección de dependencias | `proyecto_final/graph_builder.py` | [🏆](ejercicios/ejercicio_proyecto.md) | `proyecto_final/tests/test_agente.py` |
| Spec-Driven Development (verificador) | `verificar_curso.py` | — | `tests/test_verificar_curso.py` |
| Spec de una aplicación de IA | `docs/guia-spec-para-apps-de-ia.md` | — | — (documento de método, sin test) |
| Multi-query y RAG-Fusion | `20` | [20](ejercicios/ejercicio_20_rag_avanzado.md) | `test_offline.py::TestTema20*` |
| Fine-tuning vs RAG | `21` | — | `test_offline.py::TestTema21*` |
| Fine-tuning hands-on (LoRA/QLoRA en Colab) | `docs/notebooks/21b_lora_colab.ipynb` | — | — (fuera del gate, ADR-0003) |
| Multimodal (texto + imagen) | `22` | [22](ejercicios/ejercicio_22_multimodal.md) | `test_offline.py::TestTema22*` |
| Voz: audio de entrada y síntesis (TTS) | `22b` | [22](ejercicios/ejercicio_22_multimodal.md) | `test_offline.py::TestTema22bVoz*` |
| Agente de voz en tiempo real (Deepgram STT→LLM→TTS) | `voz/agente_voz_realtime.py` | — | — (anexo, fuera del gate, ADR-0007) |
| Seguridad y red-teaming (OWASP LLM) | `23` | [23](ejercicios/ejercicio_23_seguridad.md) | `test_redteam.py` |
| Vector DBs en producción (dedup · IVFFlat) | `24` | — | `test_offline.py::TestTema24*` |
| DB vectorial REAL (Qdrant · HNSW · upsert idempotente) | `vectordb/qdrant_companion.py` | — | — (companion, fuera del gate, ADR-0009) |
| Caché exacta vs semántica (TTL, llave por rol, hit rate) | `proyecto_llmops/cache/` | — | `proyecto_llmops/tests/test_cache.py` |
| Feedback 👍/👎 y A/B de prompts | `proyecto_llmops/observability/feedback.py` | — | `proyecto_llmops/tests` |
| Frontend de chat con SSE (streaming) | `proyecto_llmops/app/static/chat.html` | — | — |
| Canal WhatsApp (webhook + EvolutionAPI) | `canales/whatsapp/webhook.py` | — | — (anexo, fuera del gate, ADR-0004) |
| Orquestación low-code con n8n | `canales/n8n/agente_rag_whatsapp.json` | — | — (anexo, fuera del gate, ADR-0005) |
| Mapa del ecosistema (LangChain vs LlamaIndex · CrewAI · OpenAI Agents SDK) | — | — | — |
| Correr LlamaIndex y CrewAI (mismo RAG/supervisor, otra piel) | `frameworks/rag_llamaindex.py` · `frameworks/crew_crewai.py` | — | — (anexo, fuera del gate, ADR-0006) |
| Discovery de procesos (AS-IS/TO-BE · escalera de autonomía · matriz) | — | — | — |
| Anatomía del prompt (rol · tarea · contexto · formato · delimitadores) | `26a` | [26a](ejercicios/ejercicio_26a_prompting.md) | `test_offline.py::TestTema26a*` |
| Prompt engineering (few-shot · CoT · self-consistency) | `26b` | — | `test_offline.py::TestTema26b*` |
| Mecánica del LLM (tokenización · softmax · muestreo · perplejidad) | `27` | [27](ejercicios/ejercicio_27_fundamentos.md) | `test_offline.py::TestTema27*` |
| Arquitecturas e historia (transformer · encoder/decoder · RLHF · MoE) | — | — | — |
| Desafíos: alucinaciones y detección (SelfCheckGPT) | `28` | [28](ejercicios/ejercicio_28_alucinaciones.md) | `test_offline.py::TestTema28*` |
| Caso real 2: asistente de compras retail (ETL · grounding · eval) | `29` | [29](ejercicios/ejercicio_29_retail.md) | `test_offline.py::TestTema29*` |
| Caso retail en producción (proyecto LLMOps) | `proyecto_retail/` | — | `proyecto_retail/tests` |
| Memoria de largo plazo (recordar entre conversaciones) | `30` | — | `test_offline.py::TestTema30*` |
| Cultura DevOps y CALMS (los 5 pilares) | — | — | — |
| Git: ramas, flujo de trabajo y pull requests | — | — | — |
| Docker a fondo (VM vs contenedor · Dockerfile · multi-stage) | — | — | — |
| Infraestructura como Código con Terraform | — | — | — |
| DevSecOps (SAST · DAST · S-SDLC) | — | — | — |

## 6) Cómo se verifica que esto funciona

```bash
cd curso_ejemplos
uv run pytest -m offline        # 886 tests, ~30 s, CERO llamadas a la API
```

Qué cubren:

- **`tests/test_imports.py`** — importa **todos** los ejemplos. Detecta que una
  librería cambió de API (`langchain 1.3 → 1.4`) sin gastar un token. También
  verifica que ningún ejemplo llame a la API *al importarse*.
- **`tests/test_offline.py`** — la lógica no-LLM de cada tema: la aritmética de
  las tools, los moldes Pydantic, las fórmulas de BM25/RRF, el grafo HITL en sus
  dos ramas, el protocolo MCP contra un servidor real, el enrutado del supervisor
  y el cálculo de costes.
- **`tests/test_util.py`** — la lógica compartida (`es_error_cuota`, troceado) y la
  fábrica de modelos: que `LLM_PROVIDER=groq` construya de verdad un cliente
  apuntando a Groq, y que pida `GROQ_API_KEY` y no la llave de Google.
- **`proyecto_final/tests/`** — el proyecto final entero, con un **modelo falso**
  que recita un guion: pregunta → tool → auditoría → respuesta.
- **`proyecto_llmops/tests/`** — el servicio de producción: guardrails, caché
  semántico, tríada RAG, el gate del deploy y la API entera (con `TestClient`,
  un agente falso y sin levantar Postgres, Redis ni Langfuse).

Y en cada `push`, [la CI](../.github/workflows/ci.yml) corre exactamente eso en
Python 3.11 y 3.12. **Nunca llama a la API**: no gasta cuota y no falla por un
429 ajeno al código.

Aparte va [`eval-gate.yml`](../.github/workflows/eval-gate.yml), que **sí gasta
cuota** y **sí puede bloquear un deploy**: corre la tríada RAG sobre el dataset
versionado. Se lanza a mano o al crear una release, nunca en cada push.

## 7) Documentación de operación

| Documento | Para qué |
|-----------|----------|
| [`docs/README_runbook.md`](docs/README_runbook.md) | Qué teclas tocar cuando algo se rompe: 429, `.env`, depurar un grafo, rollback |
| [`docs/adr/0001-vector-store.md`](docs/adr/0001-vector-store.md) | Por qué `InMemoryVectorStore` y cuándo dejará de servir |
| [`docs/adr/0002-re-ranker.md`](docs/adr/0002-re-ranker.md) | Por qué el re-ranker está escrito a mano y no con un cross-encoder |
| [`docs/adr/0000-plantilla.md`](docs/adr/0000-plantilla.md) | La plantilla para tus propios ADR |

## 8) 🚀 El escalón siguiente: `proyecto_llmops/`

El `proyecto_final/` es **el prototipo que funciona en local**.
[`proyecto_llmops/`](proyecto_llmops/README.md) es ese mismo agente convertido en
un **producto**: el mismo dominio (GobData), envuelto en las cuatro capas que
exige producción.

```bash
uv sync --extra llmops
docker compose -f proyecto_llmops/docker-compose.yml up -d   # Postgres+pgvector, Redis, Langfuse
uv run uvicorn proyecto_llmops.app.main:app --port 8000
```

| Pilar LLMOps | Dónde vive | La idea que hay que llevarse |
|---|---|---|
| 🛡️ **Gobernanza** | `guardrails/` | Bloquear lo hostil, **sanear** lo torpe. El prompt no es un control de seguridad |
| 💸 **Coste y UX** | `cache/`, `app/llm.py`, `app/streaming.py` | Un HIT del caché cuesta $0. Y un caché sin rol **se salta el RBAC** |
| 🔭 **Observabilidad** | `observability/` | La media esconde al usuario que se va: mide **p95** y **TTFT** |
| 📊 **Evaluación** | `evals/` | La evaluación solo vale si tiene **poder de veto** (`ci_gate.py` → `exit 1`) |

Y tres decisiones documentadas, con sus consecuencias negativas escritas:
[pgvector](proyecto_llmops/docs/adr/0003-pgvector.md) ·
[Langfuse](proyecto_llmops/docs/adr/0004-langfuse.md) ·
[caché semántico](proyecto_llmops/docs/adr/0005-semantic-cache.md).
Cuando algo se rompa: [su runbook](proyecto_llmops/docs/README_runbook.md).

## 9) Cambiar de proveedor (Gemini, Groq, OpenAI, Claude, OpenRouter, DeepSeek, Ollama)

Ningún archivo del curso instancia un modelo a mano. Todos llaman a
`util.crear_llm()` y a `util.crear_embeddings()`, que leen el `.env`. Cambiar de
proveedor es cambiar una línea, nunca el código. **Cuál elegir** para una
solución real (pago vs. open weights, precios, dónde corre) se explica en el
Concepto 18b de la web (`web/content/modules/18b-elegir-modelo-y-proveedor.mdx`).

| Quiero… | En el `.env` | Instalar |
|---------|--------------|----------|
| Gemini (por defecto) | `LLM_PROVIDER=google` + `GOOGLE_API_KEY` | — |
| **Groq (el que aguanta)** | `LLM_PROVIDER=groq` + `GROQ_API_KEY` | — |
| Ollama en mi máquina | `LLM_PROVIDER=ollama` + `LLM_MODELO=qwen3:8b` | `ollama serve` |
| OpenAI · `gpt-5.4-mini` | `LLM_PROVIDER=openai` + `OPENAI_API_KEY` | — |
| Anthropic · `claude-haiku-4-5` | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` | — |
| OpenRouter (agregador, tiene `:free`) | `LLM_PROVIDER=openrouter` + `OPENROUTER_API_KEY` | — |
| DeepSeek · `deepseek-v4-flash` | `LLM_PROVIDER=deepseek` + `DEEPSEEK_API_KEY` | — |
| Otro modelo del mismo proveedor | `LLM_MODELO=llama-3.3-70b-versatile` | — |
| **Embeddings sin cuota** | `EMBEDDINGS_PROVIDER=fastembed` | `uv sync --extra emb` |

> ⚠️ **Qué modelo usa cada proveedor está en `util.MODELOS_POR_DEFECTO`, y esa tabla
> es una foto con fecha.** Los proveedores retiran modelos sin avisar (le pasó a
> `qwen/qwen3-32b`, el default de Groq hasta 2026-07). Si ves `model not found` o
> `model_decommissioned`, no es tu código: copia un ID vigente de la tabla de
> modelos del cheat sheet de la web —o de la página oficial del proveedor— y
> ponlo en `LLM_MODELO` del `.env`. Esa variable gana sobre cualquier default.

Una sola clase (`ChatOpenAI` con otra `base_url`) cubre Groq, Ollama, OpenAI,
OpenRouter y DeepSeek: el mercado convergió en el dialecto de la API de OpenAI.
Gemini y Claude (Anthropic) no lo hablan, y por eso conservan su propia rama en
`crear_llm()`.

### ⚠️ Los embeddings NO siguen a `LLM_PROVIDER`

Y no es un descuido. **Groq no ofrece embeddings**, y además **cambiar de modelo
de embeddings invalida el índice entero**: los vectores viejos y los nuevos viven
en espacios distintos, así que compararlos no da un resultado peor — da un
resultado *sin sentido*. Hay que reindexar.

En el curso eso no muerde (el índice se reconstruye en cada arranque), pero
conviene entenderlo antes de llegar a producción. Para hacer RAG sin gastar nada:

```bash
uv sync --extra emb                 # fastembed (ONNX, sin PyTorch)
echo "EMBEDDINGS_PROVIDER=fastembed" >> .env
uv run python 11_rag.py             # vectoriza en tu máquina; solo el chat sale a internet
```

La primera ejecución descarga el modelo (~220 MB, multilingüe porque el curso
está en español). Después funciona sin conexión.

## 10) Si ves un error 429 (RESOURCE_EXHAUSTED)

Es el límite del plan gratuito de Gemini. Espera unos minutos, cambia el modelo
a `gemini-2.5-flash`, **pásate a Groq** ([§9](#9-cambiar-de-proveedor-groq-ollama-fastembed))
o activa facturación. **No es un error de tu código.**

Mientras tanto, corre los ejemplos offline: son 7 de los 19.
Receta completa en el [runbook](docs/README_runbook.md#31-429-resource_exhausted--el-más-común).

---

> El curso HTML completo —con los cuatro niveles, los quizzes, las soluciones
> plegables, el FAQ de errores y el cheat sheet— explica la teoría de cada tema
> y las variantes con librerías reales (`rank_bm25`, cross-encoders, LangSmith).
