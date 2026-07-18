# Auditoría de producción — proyecto_final · proyecto_llmops · proyecto_retail

**Fecha:** 2026-07-18 · **Alcance:** los tres proyectos de `curso_ejemplos/` · **Pregunta:** ¿qué les falta para ser soluciones desplegables en producción real?
**Deploy target de referencia:** Docker + VPS/cloud genérico (compose, healthcheck HTTP, logs a stdout 12-factor, secretos por env vars, vector store como servicio).
**Método:** exploración exhaustiva de código, tests, ADRs, runbooks y CI; toda cita `path:línea` fue verificada contra el árbol actual. **No se modificó código.**

---

## 1 · Veredicto ejecutivo

| Proyecto | Rol real | Distancia a producción | Recomendación |
|---|---|---|---|
| `proyecto_final` | Prototipo didáctico (capstone m18): agente ReAct + RAG, CLI de 2 turnos | 🔴 Lejos — y **no debe recorrerla** | **No desplegarlo.** Su camino a producción ya está materializado: `proyecto_llmops` lo importa y lo endurece. Mantenerlo como material didáctico. |
| `proyecto_llmops` | Hardening de proyecto_final: FastAPI+SSE, pgvector, Redis, Langfuse, guardrails, RBAC, A/B, eval-gate | 🟡 Media — arquitectura correcta, ejecución incompleta | **Candidato principal.** Cerrar los 6 críticos (§4) lo deja desplegable en un VPS con Docker. |
| `proyecto_retail` | Espejo independiente de llmops para Sifrah (m29): catálogo como fuente de verdad, price grounding | 🟡 Media — mismo patrón, con 3 cables sueltos propios | Hereda el roadmap de llmops **más** sus críticos propios: tracing muerto, coste en 0 y eval-gate fuera de CI (§5). |

La conclusión estructural: **no tiene sentido "productionizar" los tres por igual**. El repo ya contiene la progresión prototipo → producción (final → llmops); el trabajo real está en cerrar la brecha entre "integrado en código" y "operativo de verdad" en llmops y retail.

Un dato a favor de los tres: los ADRs y runbooks **ya reconocen la mayoría de los límites** que esta auditoría señala. El gap no es de conciencia — es de ejecución.

---

## 2 · Marco de evaluación

Checklist contra el que se midió cada proyecto (target Docker + VPS):

1. **Imagen de la app** — Dockerfile propio, no solo infraestructura en compose.
2. **Orquestación** — compose con healthcheck apuntando a `/health`, restart policy.
3. **Config y secretos** — tipada (pydantic-settings), env vars, sin placeholders hardcodeados.
4. **Logging estructurado** — JSON a stdout con niveles y correlación; no `print()`.
5. **Auth y red** — autenticación en la API, CORS, `/metrics` no público.
6. **Resiliencia** — timeouts de cliente LLM, retry con backoff, rate limiting, manejo de 429.
7. **Persistencia de estado** — métricas, feedback y memoria conversacional sobreviven al reinicio y agregan entre workers.
8. **Observabilidad efectiva** — no basta integrarla: debe estar *cableada en el path real* y fallar ruidosamente.
9. **Evaluación en CI** — el eval-gate del proyecto corre y puede vetar.
10. **Integridad documental** — README/ADR dicen la verdad sobre conteos y defaults.

---

## 3 · proyecto_final — no lo despliegues; ya tiene sucesor

**Qué es sólido:** inyección de dependencias de punta a punta (`graph_builder.construir_agente` acepta tools/prompt/modelo — por eso llmops lo reutiliza vía `app/_proyecto_final.py`), 42 tests offline con dobles, validación fail-fast del entorno (`config.py:64-75`), ADR-0001 que documenta y acota la decisión del vector store en memoria.

**Evidencia de que es prototipo (no defectos a corregir):**

- CLI con 2 turnos hardcodeados y `thread_id` fijo (`main.py:39-46`); sin servidor HTTP.
- Estado 100 % RAM: `MemorySaver` (`persistence.py:39-47`, con la migración a Sqlite/Postgres **comentada**, no implementada) e `InMemoryVectorStore` reconstruido en cada arranque (`rag.py:56-59`).
- `print()` en lugar de logging; sin reintentos/timeouts; auditoría en archivo plano local sin rotación ni concurrencia segura (`audit.py:76-86`).
- Sin Dockerfile ni healthcheck.

**Recomendación:** mantenerlo tal cual. Dos retoques menores, ambos documentales:

- ✏️ README: añadir una línea explícita "la versión de producción de este proyecto es `proyecto_llmops`" (hoy la relación solo se descubre leyendo código). **[Hecho en Fase 0.]**
- ✅ README línea 69 dice **44 tests** y pytest colecta **44** — es correcto. (Una medición por `grep "def test"` da 42 porque no cuenta la parametrización; el conteo válido es `pytest --collect-only`. Corregido respecto a la primera versión de este informe.)

---

## 4 · proyecto_llmops — hallazgos priorizados

### ✗ Críticos (bloquean cualquier despliegue)

| # | Hallazgo | Evidencia |
|---|---|---|
| L1 | ~~**Sin Dockerfile de la app.**~~ **[Cerrado en Fase 1]** — `docker-compose.yml` levanta solo infra (Postgres+pgvector, Redis, Langfuse); la app corre con `uvicorn --reload` a mano. No hay imagen que desplegar. | `docker-compose.yml` |
| L2 | ~~**Sin auth ni CORS; el `rol` viaja en el body → RBAC decorativo.**~~ **[Cerrado en Fase 1]** (`app/auth.py`: el rol sale de la credencial; sin `API_KEYS` el modo abierto se avisa y se publica en `/health`) — Cualquier cliente elige su propio rol. `/chat`, `/metrics` y `/feedback` abiertos. El propio código lo confiesa. | `app/main.py:84-88`, ADR-0007 |
| L3 | **Métricas y feedback en memoria, por proceso.** Se pierden al reiniciar; con N workers hay N colectores que no agregan. El A/B (ADR-0006) decide sobre datos que se evaporan. | `observability/metrics.py`, ADR-0006 |
| L4 | ~~**Tokens y coste en 0 sin Langfuse.** `_flujo` registraba `Uso()` vacío ("el conteo real lo aporta el callback de Langfuse") — si Langfuse no está, `/metrics` miente en silencio.~~ **[Cerrado en Fase 0]:** `ContadorDeUso` acumula el `usage_metadata` de todas las llamadas del ciclo ReAct desde el propio stream. Un 0 hoy significa "el proveedor no informó", no "fue gratis". | `app/main.py:366`, `observability/cost_model.py`, `app/streaming.py:180` |
| L5 | ~~**Sin logging estructurado.**~~ **[Cerrado en Fase 1]** (`observability/logs.py`: JSON a stdout + `request_id` por ContextVar) — Cero `import logging`; scripts con `print()`. En un VPS no hay forma de correlacionar un error con un request. | todo el árbol |
| L6 | **Sin rate limiting, sin timeouts de cliente LLM, sin backoff.** Solo `with_fallbacks` (cascada cheap→strong). Un 429 sostenido o un proveedor colgado se propagan tal cual. | `app/llm.py:80-93`, runbook §2 |

### ▲ Importantes

- **`add_documents()` no idempotente** — reindexar duplica fragmentos; reconocido en ADR-0003 y runbook §3.
- **Filtro RBAC en Python, no en el `WHERE` SQL** — los documentos restringidos viajan hasta la app antes de descartarse (ADR-0003).
- **Tracing con `except Exception` silencioso** en todo `observability/tracing.py` — si la observabilidad se cae, nadie se entera (ADR-0004, runbook §7).
- **Guardrails = listas negras de subcadenas**, evadibles con leetspeak ("1gnora tus 1nstrucciones") — `guardrails/policy.py:58`, `output_guard.py:42`. Falta un modelo guardián.
- **Clasificación de confidencialidad por subcadenas** (`app/rag.py:56`) — el propio código dice "en producción esto sería un clasificador entrenado o un LLM".
- **Dataset de evals: 12 ejemplos** y el eval-gate en CI corre **sin Postgres** — evalúa el fallback in-memory, no el índice pgvector real (`.github/workflows/eval-gate.yml`).
- **Checkpointer `MemorySaver`** — memoria conversacional efímera (`app/agent.py:60`).
- **Secretos placeholder hardcodeados en compose** — `NEXTAUTH_SECRET: "cambia-esto-en-produccion..."`, `pk-lf-xxxxxxxx` (`docker-compose.yml:93-104`). Aceptable en demo; letal si alguien hace `docker compose up` en un servidor real sin cambiarlos.
- **Umbral de caché 0.92 sin calibrar** con tráfico real + **búsqueda lineal en el cliente** (mala a >50k entradas) — ADR-0005.

### ○ Deseables

- Tabla de precios estática "foto de 2026-07" (`observability/cost_model.py:33`); modelo desconocido → coste 0.0, indistinguible de gratis.
- Rangos abiertos sin techo en el extra `llmops` del pyproject (`fastapi>=0.115`, `redis>=5.0`…) — `uv.lock` protege hoy, pero un `uv sync` futuro puede traer majors.
- Gestor de secretos (Vault/SSM) en lugar de `.env`.
- Dataset de evals más grande y balanceado por categoría (hoy: 5 de 12 son `recuperacion_directa`).

### Integridad documental

- El README dice **232 tests** y pytest colecta **232** — correcto. El error estaba en **ADR-0004, que decía 652** (`docs/adr/0004-langfuse.md:55`) y no cuadra con nada. **[Corregido en Fase 0; tras cerrar L4 el conteo es 240 en README y ADR.]** (El conteo válido es `pytest --collect-only`; `grep "def test"` da 229 por no contar la parametrización.)
- `app/embeddings.py:20` marcaba default `huggingface`; `config.py:79` y `.env.example` fijan `fastembed`. **[Corregido el docstring en Fase 0.]**

---

## 5 · proyecto_retail — hallazgos priorizados

### ✗ Críticos

| # | Hallazgo | Evidencia |
|---|---|---|
| R1 | **Tracing muerto en el path real.** `observability/tracing.py` existe con degradación graceful, pero `tracing.callbacks()` **nunca se cablea**: `agent.py:87` hace `llm.invoke([...])` sin `config={"callbacks": ...}`. Langfuse no recibe una sola traza del serving path. | `app/agent.py:87` |
| R2 | **Coste y tokens siempre en 0.** `extraer_uso()` existe (`observability/cost_model.py:45-53`) pero nunca se llama; todos los `MetricasRequest` se registran con `Uso()` vacío. `/metrics` reporta coste 0 siempre. | `app/main.py:192,209,234` |
| R3 | **El eval-gate de retail NO está en CI.** `evals/ci_gate.py` propio existe (doble puerta: media + cero tolerancia a precio inventado) pero el workflow ejecuta solo el de llmops. El invariante central del proyecto —"el precio nunca viene del modelo"— no tiene veto automatizado. | `.github/workflows/eval-gate.yml:81` |
| R4 | **Sin Dockerfile (compose solo Redis), sin auth, sin manejo de 429/backoff.** El runbook §2 dice literalmente "cambia el `.env` a mano" ante un 429. | `docker-compose.yml`, runbook |
| R5 | **Embeddings bag-of-words de demo** (hashing blake2b, 128 dims, auto-documentado como "stand-in didáctico" que no capta sinónimos). El caché semántico de producción necesita embeddings reales — con estos, "aretes dorados" y "aros dorados" no se parecen. | `app/embeddings.py` |

### ▲ Importantes

- **`catalogo_fuente="live"` no cableado**: el lifespan siempre llama `cargar_catalogo_demo()` (`app/main.py:103-105`); `CATALOGO_URL` solo la usa el script manual `data/fetch_catalogo.py`. La app no puede consumir el catálogo real sin tocar código.
- **Dataset: 8 casos reales vs README que exige "al menos los 13 casos"** (`README.md:180`). El archivo tiene 13 líneas, pero 5 son comentarios `//` — quien escribió el criterio contó líneas.
- **`price_guard` solo detecta formato `S/xx.xx`** — "cuesta veinte soles" se escapa (runbook §1).
- **Guardrails por subcadenas**, evadibles ("1nvéntate un precio pasa") — auto-reconocido en `guardrails/input_guard.py:18-20`.
- **Métricas/feedback en memoria por proceso** — mismo patrón que llmops (L3).
- **Sin logging estructurado** — mismo patrón que llmops (L5).

### ○ Deseables

- `catalogo_url` con default hardcodeado a `https://sifrah.com/products.json` (`app/config.py:59`) — un dominio real en un default es una llamada de red sorpresa esperando a ocurrir.
- Tabla de precios estática (mismo patrón que llmops).
- Índice vectorial real para el caché (RediSearch o pgvector) en vez de coseno lineal en Python.

**Nota de arquitectura:** retail **no importa nada** de llmops (cero `from proyecto_llmops`); duplica estructura deliberadamente como espejo didáctico. Para el curso es correcto. Si ambos fueran a producción de verdad, los módulos calcados (`cost_model`, `metrics`, `tracing`, `feedback`, `cache_backends`) pedirían extraerse a una librería compartida — hoy cada bugfix hay que aplicarlo dos veces (esta auditoría es la prueba: L3≈métricas retail, L5≈logging retail).

---

## 6 · Gaps transversales

Los mismos seis agujeros aparecen en llmops y retail — son **el patrón del salto curso→producción**, no defectos aislados:

| Gap | llmops | retail |
|---|---|---|
| Sin imagen Docker de la app | L1 | R4 |
| Sin logging estructurado | L5 | ▲ |
| Métricas/feedback en memoria por proceso | L3 | ▲ |
| Sin auth en la API | L2 | R4 |
| Sin rate limiting / timeouts / backoff | L6 | R4 |
| Guardrails heurísticos evadibles | ▲ | ▲ |
| Tabla de precios estática | ○ | ○ |
| Sin gestor de secretos | ○ | ○ |

---

## 7 · Roadmap priorizado

Esfuerzo: **S** = horas · **M** = 1–3 días · **L** = 1 semana+. Orden = valor/esfuerzo.

### Fase 0 — Quick wins ✅ COMPLETADA (cierra R1, R2, R3, **L4** y las mentiras documentales)

| Ítem | Proyecto | Esfuerzo |
|---|---|---|
| Cablear `tracing.callbacks()` en `agent.py` (una línea en el `invoke`) ✅ | retail | S |
| Llamar `extraer_uso()` y propagar `usage_metadata` para que `/metrics` deje de reportar 0 ✅ | retail **y llmops (L4)** | S |
| Añadir `proyecto_retail/evals/ci_gate.py` al workflow `eval-gate.yml` ✅ | retail | S |
| Corregir las 5 discrepancias documentales (tests 232/652/229, tests 44/42, dataset 13/8, default embeddings, README de final → apuntar a llmops) ✅ | los tres | S |

### Fase 1 — Deployable ✅ COMPLETADA (cierra L1, L2, L5 y R4 salvo el 429/backoff)

| Ítem | Proyecto | Esfuerzo |
|---|---|---|
| Dockerfile multi-stage (uv + imagen slim) + servicio `app` en compose con healthcheck a `/health` y restart policy ✅ | llmops, retail | M |
| `logging` JSON a stdout con nivel por env y un `request_id` correlacionado ✅ | llmops, retail | M |
| Auth mínima (API key por header) + CORS + derivar `rol` del token, no del body + `/metrics` detrás de auth ✅ | llmops (retail hereda, sin roles) | M |
| Quitar placeholders de secretos del compose (exigirlos por env, fail-fast si faltan) ✅ | llmops | S |

### Fase 2 — Robusto (M/L; cierra L3, L4, L6 y ▲ estructurales)

| Ítem | Proyecto | Esfuerzo |
|---|---|---|
| Timeouts de cliente LLM + retry con backoff exponencial (tenacity o `max_retries` del cliente) | llmops, retail | M |
| Rate limiting (slowapi en la app o límites en el reverse proxy) | llmops, retail | M |
| Persistir métricas y feedback en Postgres (ya está en la infra de llmops) — el A/B por fin decide sobre datos reales | llmops, retail | M |
| Checkpointer Postgres (`PostgresSaver`) para memoria conversacional | llmops | M |
| RBAC en el `WHERE` SQL (filtro en pgvector, no en Python) | llmops | M |
| Indexado idempotente (upsert por hash de fragmento) | llmops | M |
| Cablear `catalogo_fuente="live"` en el lifespan + refresco periódico | retail | M |

### Fase 3 — Escala y madurez (L)

| Ítem | Proyecto | Esfuerzo |
|---|---|---|
| Modelo guardián en guardrails (clasificador de inyección/PII) en lugar de listas negras | llmops, retail | L |
| Embeddings reales (fastembed ya está en deps) + índice vectorial para el caché | retail | M/L |
| Calibrar umbral de caché con tráfico real; migrar búsqueda lineal a índice | llmops, retail | M |
| Dataset de evals ≥50 casos balanceados por categoría; eval-gate contra Postgres real | llmops, retail | L |
| Gestor de secretos (Vault/SSM/1Password) + rotación | los tres | L |
| CD (build de imagen + deploy automatizado al VPS en tag) | llmops, retail | M |

---

## 8 · Cierre

La arquitectura de llmops y retail está bien pensada — capas correctas, degradación graceful, evaluación con veto, ADRs honestos. Lo que falta es la **última milla operativa**: una imagen que desplegar, un log que leer, una puerta que cerrar y métricas que no se evaporen. La Fase 0 es una tarde de trabajo y elimina las tres mentiras silenciosas (trazas que no existen, costes en 0, gate que no veta); la Fase 1 convierte "corre en mi máquina" en "corre en un VPS". A partir de ahí, cada fase es opcional según el destino real: demo interna, piloto con Sifrah, o servicio multi-cliente.
