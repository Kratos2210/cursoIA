# Plan: Proyecto end-to-end LLMOps — GobData en producción

## Contexto y posicionamiento

El curso ya tiene un `proyecto_final/` modular y testeado (el "prototipo que funciona en local"). Este plan añade el **siguiente escalón real**: un proyecto hermano, `proyecto_llmops/`, que lleva ESE MISMO dominio (GobData, financiera, normativa + evaluación de reglas + auditoría) a un producto empresarial escalable, seguro y rentable aplicando el ciclo de vida LLMOps en sus 3 fases.

**No duplica** `proyecto_final/`: lo **reutiliza como núcleo** y le añade las capas de producción alrededor. El ADR-0001 existente ya dice literalmente *"cuándo revisar InMemory → pgvector"*, *"cuándo desplegar con más de un proceso"* — este plan materializa esos "cuándo".

**Decisión del usuario**: servicios reales con `docker-compose` (Langfuse + Redis + Postgres/pgvector), y los 4 pilares LLMOps en profundidad.

---

## Arquitectura del proyecto

```
proyecto_llmops/
├── docker-compose.yml          # Postgres+pgvector, Redis, Langfuse (self-hosted)
├── .env.example                # TODAS las vars (GOOGLE_API_KEY, PG, Redis, Langfuse)
├── README.md                   # Cómo levantarlo, diagrama de arquitectura
│
├── app/                        # El servicio (FastAPI)
│   ├── main.py                 # API: POST /chat (con streaming SSE), GET /health
│   ├── config.py               # Settings centralizados (pydantic-settings)
│   ├── llm.py                  # Cascade: barato→caro, con with_fallbacks
│   ├── agent.py                # Reutiliza proyecto_final/graph_builder con pgvector
│   ├── rag.py                  # pgvector retriever (reemplaza InMemory)
│   └── streaming.py            # token-a-token vía SSE
│
├── guardrails/                 # PILAR: Gobernanza (filtros entrada/salida, PII, RBAC)
│   ├── __init__.py
│   ├── input_guard.py          # anti prompt-injection, tópicos prohibidos
│   ├── output_guard.py         # filtro de contenido sensible, PII leak
│   ├── pii.py                  # detección DNI/tarjeta/email (regex + opc. Presidio)
│   ├── rbac.py                 # control de acceso por rol sobre documentos
│   └── policy.py               # reglas declarativas (qué bloquear, qué anonimizar)
│
├── cache/                      # PILAR: Optimización costo
│   ├── semantic_cache.py       # cache semántico (coseno); backend Redis si hay, in-mem si no
│   └── cache_backends.py       # interfaz: InMemoryCache vs RedisCache
│
├── observability/              # PILAR: Observabilidad
│   ├── tracing.py              # wrapper Langfuse (decorador @observe)
│   ├── metrics.py              # TTFT, tokens in/out, costo por request, latencia p50/p95
│   └── cost_model.py           # precios por modelo (gemini-2.0-flash, etc.)
│
├── evals/                      # PILAR: Evaluación + CI/CD
│   ├── dataset.jsonl           # dataset versionado (pregunta + respuesta esperada + contexto)
│   ├── rag_triad.py            # faithfulness, answer_relevance, context_precision (LLM-judge)
│   ├── judge.py                # LLM-as-judge con structured output
│   ├── run_evals.py            # corre el dataset entero y produce un reporte
│   └── ci_gate.py              # umbral: si score < X, exit 1 (bloquea el deploy)
│
├── prompts/                    # Prompt management (prompts como código)
│   ├── *.yaml                  # versionados, con variables, few-shot, metadata
│   └── loader.py               # carga + render Jinja2
│
├── tests/                      # Tests (offline donde sea posible)
│   ├── test_guardrails.py      # prompt injection bloqueado, PII detectado
│   ├── test_cache.py           # hit/miss del semántico
│   ├── test_rbac.py            # rol sin permiso no ve documento restringido
│   ├── test_evals.py           # tríada RAG con LLM mockeado
│   └── test_smoke_api.py       # FastAPI con TestClient (sin llamar Gemini)
│
└── docs/
    ├── README_runbook.md       # operación del servicio en producción
    ├── adr/0003-pgvector.md    # por qué pgvector sobre Chroma en producción
    ├── adr/0004-langfuse.md    # por qué Langfuse self-hosted sobre LangSmith
    └── adr/0005-semantic-cache.md
```

---

## Fases del ciclo de vida LLMOps (mapeadas a entregables)

### Fase 1 — Ideación: Estrategia y Datos
- **Data Sourcing + document parsing**: `rag.py` lee la normativa con troceado limpio + clasificación de **confidencialidad** por fragmento (metadato `confidentiality: public|internal|restricted`). Esto alimenta el RBAC.
- **Selección del modelo base**: `llm.py` implementa una **arquitectura en cascada** — modelo barato (`gemini-2.0-flash`) primero, salta al de mayor razonamiento solo si el guardrail de "complejidad" lo indica o si hay fallback. Tabla costo/latencia/razonamiento documentada en un ADR.

### Fase 2 — Desarrollo: Arquitectura y Orquestación
- **Prompt Engineering avanzado**: `prompts/*.yaml` con prompts tratados como código — estructura XML, salida JSON estricto, few-shot. `loader.py` los renderiza. Los prompts viven versionados, no hardcoded.
- **Chains vs Agents**: documentado + implementado. GobData sigue siendo agente ReAct (necesita autonomía: decide entre consultar normativa o evaluar regla), pero las piezas internas (el RAG, el guardrail) son **cadenas deterministas**.
- **RAG vs Fine-Tuning**: ADR justificando RAG (datos dinámicos: la normativa cambia) vs fine-tuning. Se usa **pgvector** (datos dinámicos persistentes) — materializa la decisión "cuándo revisar InMemory" del ADR-0001.
- **LLM-as-a-Judge + tríada RAG**: `evals/rag_triad.py` implementa faithfulness (¿la respuesta se sostiene solo en el contexto?), answer relevance (¿responde la pregunta?) y context precision (¿el contexto recuperado es relevante?). `judge.py` usa `with_structured_output`.

### Fase 3 — Operación: Producción y Gobernanza
- **CI/CD automatizado**: `evals/ci_gate.py` corre el dataset; si el score de la tríada baja de umbral, `exit 1` y **bloquea el deploy**. Workflow de GitHub Actions que lo ejecuta.
- **Observabilidad E2E**: `observability/tracing.py` envuelve cada request con Langfuse `@observe`; `metrics.py` captura TTFT, tokens, costo. **Langfuse self-hosted** vía docker-compose (tú elegiste servicios reales).
- **Optimización costo/UX**: `cache/semantic_cache.py` (coseno sobre embeddings; Redis como backend persistente, in-memory como fallback didáctico). Streaming SSE nativo en `/chat`. Arquitectura en cascada en `llm.py`.
- **Gobernanza y guardrails**: `guardrails/` completo:
  - **input_guard**: detecta prompt injection (patrones + heurística) y tópicos prohibidos antes de tocar el modelo.
  - **output_guard**: filtra contenido sensible antes de devolver al usuario.
  - **pii**: detección de DNI/tarjeta/email (regex first; Presidio opcional como extra).
  - **rbac**: acceso por rol a nivel de **documento** (el retriever filtra por `metadata.confidentiality` vs el rol del usuario).

---

## docker-compose.yml (servicios reales)
- **postgres** + extensión `pgvector` → vector store persistente del RAG.
- **redis** → backend del semantic cache.
- **langfuse** (+ su propio postgres) → observabilidad/tracing self-hosted.
- Todo arrancable con `docker compose up -d`. El `README.md` guía el `uv sync --extra llmops` y la configuración de `.env`.

---

## Integración con el curso existente
- `pyproject.toml` gana un extra `[llmops]` con: `langfuse`, `redis`, `psycopg`, `fastapi`, `uvicorn`, `pydantic-settings`, `jinja2` (Presidio en extra aparte por su peso).
- El `README.md` principal del curso añade una sección "🚀 Proyecto LLMOps de producción" que enlaza `proyecto_llmops/`.
- Se añaden **2 ADRs nuevos** (`docs/adr/0003-pgvector`, `0004-langfuse`, `0005-semantic-cache`) siguiendo la plantilla y tono existentes.
- El HTML del curso (`curso-langchain.html`) gana una sección nueva `#llmops` que enseña el ciclo de vida de 3 fases y referencia este proyecto (esto alinea con el plan del HTML ya aprobado, Fase D).

---

## Estilo y restricciones
- Respeta el estilo del curso: cabecera `FINALIDAD`/`LÓGICA`, comentarios línea por línea, español, dominio GobData/Datawith.AI.
- **Degradación graceful donde aplique**: aunque elegiste servicios reales, los **tests** no deben requerir Docker corriendo — el semantic cache y el tracing tienen un fallback in-memory/no-op para que `pytest` corra en CI sin servicios levantados. Los servicios reales se usan al correr la app, no al testear unidades.
- Inyección de dependencias en todo (como ya hace `proyecto_final`): `SemanticCache`, `Tracer`, `Retriever`, `Guard` se reciben por parámetro → testeables sin red.

---

## Orden de ejecución
1. **Cimientos**: `docker-compose.yml`, `config.py`, `.env.example`, `README.md` + extras en `pyproject.toml`.
2. **Núcleo reutilizado**: `app/agent.py` + `rag.py` con pgvector (adapta `proyecto_final`).
3. **Guardrails** (pilar más diferenciador): input/output/pii/rbac/policy + tests.
4. **Observabilidad**: tracing Langfuse + metrics + cost_model.
5. **Optimización**: semantic cache + cascade + streaming SSE.
6. **Evals + CI gate**: tríada RAG, dataset, judge, ci_gate, workflow de GH Actions.
7. **Prompts como código**: YAML + loader.
8. **Docs**: runbook + 3 ADRs + sección HTML.

