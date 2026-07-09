# 📚 Ejemplos del curso — listos para copiar y ejecutar

Cada archivo es **autónomo**: lo abres en VS Code, lo corres y funciona solo.
Están comentados **sección por sección** para que entiendas cada línea.

Y todo está **verificado por 141 tests** que corren sin gastar un solo token
(ver [§6](#6-cómo-se-verifica-que-esto-funciona)).

## 1) Requisitos (una sola vez)

```bash
cd curso_ejemplos
uv sync                  # instala todo desde pyproject.toml (el canon)
cp .env.example .env     # edita y pon tu llave de https://aistudio.google.com
```

> `pyproject.toml` + `uv.lock` son la receta reproducible.
> `requirements.txt` se mantiene solo por compatibilidad con `pip install -r`.

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
| 10 · Agente (prebuilt) | `10_agente.py` | `create_react_agent` + memoria | Sí |
| 11 · RAG | `11_rag.py` | responder desde un documento | Sí |
| 12 · RAG en profundidad | `12_rag_hibrido_rerank.py` | BM25 + vectorial, RRF y re-ranking | **No** |
| 13 · LangGraph a fondo | `13_langgraph_stategraph.py` | `StateGraph` desde cero | Sí |
| 13b · Human-in-the-loop | `13b_human_in_the_loop.py` | `interrupt()` + `Command(resume=…)` | **No** |
| 14 · MCP | `14_mcp_servidor_cliente.py` | servidor FastMCP + cliente en un archivo | **No** |
| 15 · Multiagente | `15_supervisor_multiagente.py` | el patrón **supervisor** con LangGraph | **No** |
| 16 · Evaluación | `16_evaluacion.py` | dataset + métrica + LLM-as-judge opcional | Opcional |
| 16b · Observabilidad | `16b_observabilidad_langsmith.py` | tracing, tokens y **coste real** | **No** |
| 17 · Servir el agente | `17_servidor_agente.py` | FastAPI: `POST /chat` con memoria por usuario | Sí |

**Proyecto final:** [`proyecto_final/`](proyecto_final/) — el asistente de
Gobierno de Datos, repartido en 8 módulos y con 43 tests propios.

## 4) Ejercicios

Leer código no enseña a escribirlo. En [`ejercicios/`](ejercicios/) hay 7
ejercicios con enunciado, **pistas progresivas**, criterio de aceptación
verificable y solución aparte.

Los dos que no puedes saltarte —y no gastan cuota— son
[`ejercicio_12_rerank.md`](ejercicios/ejercicio_12_rerank.md) (predice el ranking
antes de ejecutarlo) y [`ejercicio_13_hitl.md`](ejercicios/ejercicio_13_hitl.md).

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
| Agente ReAct | `10` | — | `test_agente.py::TestAgenteCompleto` |
| RAG: trocear y unir | `11` | [11](ejercicios/ejercicio_11_rag.md) | `test_offline.py::TestTema11Rag` |
| BM25 · coseno · RRF · re-rank | `12` | [12](ejercicios/ejercicio_12_rerank.md) | `test_offline.py::TestTema12*` (25 tests) |
| `StateGraph` (nodos y aristas) | `13` | — | `test_offline.py::TestTema13bHumanInTheLoop` |
| Human-in-the-loop | `13b` | [13](ejercicios/ejercicio_13_hitl.md) | `test_offline.py::TestTema13bHumanInTheLoop` |
| MCP (servidor + cliente) | `14` | — | `test_offline.py::TestTema14Mcp` |
| Patrón supervisor | `15` | — | `test_offline.py::TestTema15Supervisor` |
| Evaluación con dataset | `16` | — | *(el propio ejemplo es la métrica)* |
| Tokens, coste y tracing | `16b` | — | `test_offline.py::TestTema16bObservabilidad` |
| Servir por HTTP | `17` | [🏆 nivel 5](ejercicios/ejercicio_proyecto.md) | `test_imports.py` |
| Auditoría / trazabilidad | `proyecto_final/audit.py` | [🏆](ejercicios/ejercicio_proyecto.md) | `proyecto_final/tests/test_audit.py` |
| Inyección de dependencias | `proyecto_final/graph_builder.py` | [🏆](ejercicios/ejercicio_proyecto.md) | `proyecto_final/tests/test_agente.py` |

## 6) Cómo se verifica que esto funciona

```bash
cd curso_ejemplos
uv run pytest -m offline        # 141 tests, ~20 s, CERO llamadas a la API
```

Qué cubren:

- **`tests/test_imports.py`** — importa **todos** los ejemplos. Detecta que una
  librería cambió de API (`langchain 1.3 → 1.4`) sin gastar un token. También
  verifica que ningún ejemplo llame a la API *al importarse*.
- **`tests/test_offline.py`** — la lógica no-LLM de cada tema: la aritmética de
  las tools, los moldes Pydantic, las fórmulas de BM25/RRF, el grafo HITL en sus
  dos ramas, el protocolo MCP contra un servidor real, el enrutado del supervisor
  y el cálculo de costes.
- **`tests/test_util.py`** — la lógica compartida (`es_error_cuota`, troceado).
- **`proyecto_final/tests/`** — el proyecto final entero, con un **modelo falso**
  que recita un guion: pregunta → tool → auditoría → respuesta.

Y en cada `push`, [la CI](../.github/workflows/ci.yml) corre exactamente eso en
Python 3.11 y 3.12. **Nunca llama a la API**: no gasta cuota y no falla por un
429 ajeno al código.

## 7) Documentación de operación

| Documento | Para qué |
|-----------|----------|
| [`docs/README_runbook.md`](docs/README_runbook.md) | Qué teclas tocar cuando algo se rompe: 429, `.env`, depurar un grafo, rollback |
| [`docs/adr/0001-vector-store.md`](docs/adr/0001-vector-store.md) | Por qué `InMemoryVectorStore` y cuándo dejará de servir |
| [`docs/adr/0002-re-ranker.md`](docs/adr/0002-re-ranker.md) | Por qué el re-ranker está escrito a mano y no con un cross-encoder |
| [`docs/adr/0000-plantilla.md`](docs/adr/0000-plantilla.md) | La plantilla para tus propios ADR |

## 8) Si ves un error 429 (RESOURCE_EXHAUSTED)

Es el límite del plan gratuito de Gemini. Espera unos minutos, cambia el modelo
a `gemini-2.5-flash`, o activa facturación. **No es un error de tu código.**

Mientras tanto, corre los ejemplos offline: son 7 de los 19.
Receta completa en el [runbook](docs/README_runbook.md#31-429-resource_exhausted--el-más-común).

---

> El curso HTML completo —con los cuatro niveles, los quizzes, las soluciones
> plegables, el FAQ de errores y el cheat sheet— explica la teoría de cada tema
> y las variantes con librerías reales (`rank_bm25`, cross-encoders, LangSmith).
