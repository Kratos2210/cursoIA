# 🚀 Proyecto LLMOps — GobData en producción

> ¿Cómo llevamos un prototipo de IA que funciona bien en local a un **producto
> empresarial escalable, seguro y rentable**?

El [`proyecto_final/`](../proyecto_final) es ese prototipo: un agente que
responde dudas de normativa y evalúa reglas de calidad, modular y testeado.
**Este proyecto es el siguiente escalón**: el mismo dominio (GobData,
financiera), ahora envuelto en las capas que exige producción —gobernanza,
observabilidad, optimización de costo y evaluación continua—.

La respuesta no está en cambiar de modelo cada semana. Está en dominar **LLMOps**.

---

## Las 3 fases del ciclo de vida (y dónde vive cada una aquí)

```
        ┌─────────────────────────────────────────────────────────────┐
        │                   REQUEST  (POST /chat)                      │
        │  { "mensaje": "...", "rol": "analyst", "thread_id": "..." }  │
        └──────────────────────────────┬──────────────────────────────┘
                                       ▼
   1️⃣ GUARDRAILS DE ENTRADA  (guardrails/input_guard.py)
      · anti prompt-injection · tópicos prohibidos · PII de entrada
                                       │ (si bloquea → 400, ni toca el LLM)
                                       ▼
   2️⃣ SEMANTIC CACHE  (cache/semantic_cache.py) ── Redis
      · ¿esta pregunta ya se hizo (semánticamente)? → HIT: responde a costo ~0
                                       │ (miss → sigue)
                                       ▼
   3️⃣ AGENTE  (app/agent.py) ── reutiliza proyecto_final/graph_builder
      · RAG sobre pgvector (Postgres) · tools · memoria (checkpointer)
      · tracing Langfuse @observe en cada paso
                                       ▼
   4️⃣ GUARDRAILS DE SALIDA  (guardrails/output_guard.py)
      · filtro de contenido sensible · PII leak · coherencia
                                       ▼
   5️⃣ RESPUESTA  (streaming SSE token-a-token)
                                       │
                                       ▼
   6️⃣ MÉTRICAS  (observability/metrics.py)
      · TTFT · tokens in/out · costo · latencia → Langfuse
```

| Fase del ciclo LLMOps | Módulo | Qué aprendes |
|------------------------|--------|--------------|
| **1 · Ideación** | `app/rag.py`, `guardrails/policy.py` | data sourcing + parsing limpio + clasificación de confidencialidad |
| **2 · Desarrollo** | `prompts/`, `app/agent.py`, `evals/` | prompts como código, chains vs agents, tríada RAG |
| **3 · Operación** | `guardrails/`, `cache/`, `observability/` | guardrails, caching, tracing, CI gate |

---

## 1) Requisitos

```bash
# A) Dependencias de Python (el extra llmops trae TODO lo de producción)
cd curso_ejemplos
uv sync --extra llmops --extra dev

# B) Los servicios (Postgres+pgvector, Redis, Langfuse)
docker compose -f proyecto_llmops/docker-compose.yml up -d
docker compose -f proyecto_llmops/docker-compose.yml ps   # los 3 "healthy"

# C) Tu llave + la config
cp proyecto_llmops/.env.example proyecto_llmops/.env
$EDITOR proyecto_llmops/.env      # pega tu GOOGLE_API_KEY
```

> **¿Sin Docker o sin llave de pago?** La mayoría de los módulos tienen
> **fallback in-memory/no-op** y los tests corren sin servicios levantados.
> El modo "servicios reales" se activa solo al correr la app.

---

## 2) Levantar el servicio

```bash
# API en http://localhost:8000  (streaming SSE en /chat)
uv run uvicorn proyecto_llmops.app.main:app --reload --port 8000

# Probarlo:
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"¿Cuántos años se conservan los registros?","rol":"analyst"}'
```

- **Langfuse UI**: http://localhost:3000 (`langfuse@local` / `langfuse`) — ahí
  ves la traza de cada request, con tokens, costo y latencia.

---

## 3) Evaluación y CI/CD (lo que bloquea deploys malos)

```bash
# Correr la tríada RAG sobre el dataset (faithfulness, relevance, precision)
uv run python proyecto_llmops/evals/run_evals.py

# El "gate": si el score baja del umbral (EVAL_UMBRAL_APROBACION), exit 1
uv run python proyecto_llmops/evals/ci_gate.py
echo $?    # 0 = aprobado, 1 = bloqueado (regresión)
```

Dos workflows, y son dos a propósito:

| Workflow | Cuándo | Cuesta | ¿Puede vetar? |
|---|---|---|---|
| [`ci.yml`](../../.github/workflows/ci.yml) | cada push | gratis, nunca llama a la API | no |
| [`eval-gate.yml`](../../.github/workflows/eval-gate.yml) | a mano / al crear una release | **gasta cuota** | **sí**: `exit 1` bloquea el deploy |

Confundirlos es el error clásico: o pagas una evaluación completa por cada commit
de un README, o no evalúas nunca porque «la CI ya pasa».

El gate tiene **dos puertas**: la media (degradación general) y el mínimo (el
caso roto que la media esconde). Sin la segunda, 20 ejemplos perfectos y uno
catastrófico dan un 0.95 y el deploy pasa tan tranquilo.

---

## 4) Los 4 pilares LLMOps, en detalle

### 🛡️ Gobernanza y guardrails (`guardrails/`)
Lo más diferenciador frente al MLOps tradicional.
- **`input_guard.py`**: bloquea prompt injection y tópicos prohibidos **antes**
  de tocar el modelo. Si bloquea, la request sale 400 sin gastar un token.
- **`output_guard.py`**: filtra contenido sensible y fugas de PII en la respuesta.
- **`pii.py`**: detecta DNI, tarjeta de crédito y email (regex first; Presidio opcional).
- **`rbac.py`**: acceso por **rol** a nivel de documento. Un `analyst` no ve la
  normativa `restricted`; el retriever filtra por `metadata.confidentiality`.
- **`policy.py`**: las reglas declarativas (qué bloquear, qué anonimizar) en un sitio.

### 💸 Optimización de costo y UX (`cache/`, `app/llm.py`, `app/streaming.py`)
- **`cache/semantic_cache.py`**: una pregunta repetida (o semánticamente igual,
  sobre el umbral de coseno) se responde **sin llamar al LLM**. Backend Redis.
- **`app/llm.py`**: arquitectura en **cascada** — modelo barato primero, salta
  al de mayor razonamiento solo si hace falta (guardrail de complejidad o fallback).
- **`app/streaming.py`**: streaming **token a token** vía SSE (UX: el usuario ve
  llegar la respuesta desde el primer token, no al final).

### 🔭 Observabilidad (`observability/`)
- **`tracing.py`**: cada request se envuelve con Langfuse `@observe`. Trazas
  forenses: prompt, respuesta, tools usadas, grafo de llamadas.
- **`metrics.py`**: TTFT (time to first token), tokens in/out, costo por request,
  latencia p50/p95.
- **`cost_model.py`**: precios por modelo (la tabla que convierte tokens → $).

### 📝 Prompts como código (`prompts/`)
- **`agente_gobdata.yaml`**: el prompt del sistema, con `version:` y un
  **changelog** que dice *por qué* cambió cada versión. Un `version: 3` sin
  changelog no sirve para investigar un incidente.
- **`loader.py`**: lo carga y lo renderiza con Jinja2 y `StrictUndefined`. Sin
  eso, un typo en `{{ rol }}` no da error: produce un prompt mutilado, el modelo
  responde algo plausible y nadie se entera.

### 📊 Evaluación (`evals/`)
- **`rag_triad.py`**: la tríada clásica — **faithfulness** (¿sin alucinar?),
  **answer relevance** (¿responde la pregunta?), **context precision** (¿el
  contexto recuperado era el bueno?).
- **`judge.py`**: LLM-as-judge con `with_structured_output` (un juez consistente).
- **`dataset.jsonl`**: dataset **versionado** (pregunta + respuesta esperada + contexto).
- **`ci_gate.py`**: el umbral que aprueba o bloquea el deploy.

---

## 5) Mapa rápido "quiero X → miro en Y"

| Quiero entender… | Mira en |
|------------------|---------|
| Cómo se bloquea un prompt malicioso | `guardrails/input_guard.py` |
| Cómo se filtra un documento por rol | `guardrails/rbac.py` |
| Cómo se cachea una pregunta repetida | `cache/semantic_cache.py` |
| Cómo se filtra la salida **sin renunciar al streaming** | `app/streaming.py` |
| Cómo se mide el costo de una request | `observability/cost_model.py` |
| Por qué p95 y no la media | `observability/metrics.py` |
| Qué métrica de la tríada señala al retriever | `evals/rag_triad.py` |
| Cómo se decide si un deploy pasa | `evals/ci_gate.py` |
| Dónde vive el prompt (y su changelog) | `prompts/agente_gobdata.yaml` |
| Por qué pgvector y no Chroma | `docs/adr/0003-pgvector.md` |
| Por qué Langfuse y no LangSmith | `docs/adr/0004-langfuse.md` |
| Por qué el caché va por rol | `docs/adr/0005-semantic-cache.md` |

## 6) Cómo se prueba (197 tests, cero cuota, cero Docker)

```bash
uv run pytest proyecto_llmops/tests -m offline    # ~2 s
```

Todo lo caro entra **por parámetro**: `crear_app()` recibe agente, caché y
colector; `SemanticCache` recibe embeddings y backend; `evaluar_triada` recibe
el juez. Por eso la API entera se levanta con un `TestClient`, un agente falso
que recita tokens y ningún servicio en pie.

Lo que de verdad se afirma no es «el modelo responde bien» (eso lo mide
`evals/`), sino **el orden de las capas**: que una inyección nunca llegue al
agente, que un acierto de caché nunca llegue al agente, y que lo que se cachea
sea la respuesta saneada y no la cruda.

Las decisiones de arquitectura y el **por qué**: `docs/adr/`.
La operación (qué hacer cuando algo falla a las 11pm): `docs/README_runbook.md`.
