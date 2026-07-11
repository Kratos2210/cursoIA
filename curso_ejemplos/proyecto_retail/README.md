# 🛍️ Proyecto Retail — asistente de compras Sifrah en producción

> ¿Cómo llevamos el caso del módulo 29 (un pipeline en un archivo) a un
> **producto LLMOps organizado, con guardrails, evaluación y serving**, sin
> perder la regla de oro: precio y stock jamás salen del modelo?

El [`29_caso_retail.py`](../29_caso_retail.py) es el caso enseñado en un archivo:
ETL, búsqueda con filtros duros, grounding de precios y eval, con la pieza LLM en
maqueta (regex + plantilla). **Este proyecto es el escalón siguiente**: el mismo
caso, ahora con el LLM cableado de verdad (m05) y envuelto en las capas que exige
producción. La misma relación que [`proyecto_llmops`](../proyecto_llmops) tiene
con los módulos sueltos.

---

## El camino de una petición (y dónde vive cada capa)

```
        ┌─────────────────────────────────────────────────────────────┐
        │                   REQUEST  (POST /chat)                      │
        │        { "mensaje": "aretes dorados por < S/25" }            │
        └──────────────────────────────┬──────────────────────────────┘
                                       ▼
   1️⃣ GUARDRAIL DE ENTRADA  (guardrails/input_guard.py)
      · anti-inyección · anti "invéntate un precio"   (si bloquea → 0 tokens)
                                       ▼
   2️⃣ SEMANTIC CACHE  (cache/semantic_cache.py)
      · ¿ya respondimos esto (semánticamente)? → HIT: costo ~0
                                       ▼
   3️⃣ AGENTE  (app/agent.py)
      · intención → filtros tipados        (app/intent.py, m05)
      · búsqueda: filtros DUROS + ranking   (app/search.py)
      · redacción con tono de vendedora     (prompts/vendedora.yaml)
      · GROUNDING de precios ✔/✖ → reintento → fallback determinista
        (guardrails/price_guard.py)  ← la respuesta que sale ya es FIEL
                                       ▼
   4️⃣ STREAMING SSE  (app/streaming.py)   · verificar-y-luego-emitir
                                       ▼
   5️⃣ MÉTRICAS  (observability/)          · latencia · TTFT · costo · guardrails
```

| Fase LLMOps | Dónde vive | Qué aprendes |
|-------------|-----------|--------------|
| **Ideación** | `app/etl.py`, `data/` | data sourcing de un catálogo real + ETL del dato sucio |
| **Desarrollo** | `app/intent.py`, `app/agent.py`, `prompts/`, `evals/` | salida estructurada (m05), prompts como código, eval con métrica propia |
| **Operación** | `guardrails/`, `cache/`, `observability/`, `app/main.py` | grounding de precios, caché semántico, tracing, serving SSE, A/B |

---

## 1) Requisitos

```bash
cd curso_ejemplos
uv sync --extra dev            # FastAPI + TestClient + pytest ya vienen aquí

# Tu llave + la config (sin llave, los tests corren igual; la app no):
cp proyecto_retail/.env.example proyecto_retail/.env
$EDITOR proyecto_retail/.env   # pega tu LLM_API_KEY (Groq gratis) o usa Ollama
```

> **¿Sin Docker o sin llave?** El caché degrada a memoria y el tracing se apaga
> solo. Los tests corren sin nada levantado; solo la app (que llama al LLM) pide
> llave. Redis es opcional y solo aporta a escala (caché compartido entre workers).

---

## 2) Levantar el servicio

```bash
# API + chat en http://localhost:8000
uv run uvicorn proyecto_retail.app.main:app --reload --port 8000

# Probarlo por curl (streaming SSE):
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"quiero aretes dorados por menos de 25 soles"}'
```

Abre `http://localhost:8000/` para el chat con cara (SPA vainilla, sin build).

---

## 3) Evaluación y CI gate (lo que bloquea un deploy malo)

```bash
uv run python proyecto_retail/evals/run_evals.py   # % de casos fieles
uv run python proyecto_retail/evals/ci_gate.py ; echo $?   # 0 = ok, 1 = bloqueado
```

El gate tiene **dos puertas**: la media (`EVAL_UMBRAL_APROBACION`) y el **mínimo**
— CERO tolerancia a un precio inventado. Nueve casos perfectos y uno que alucina
un precio dan un 0.90, y aun así el deploy se bloquea: en retail, un precio
inventado no es "un caso flojo", es un reclamo. Ver
[`docs/adr/0002`](docs/adr/0002-grounding-determinista-no-llm-judge.md).

---

## 4) Mapa rápido "quiero X → miro en Y"

| Quiero entender… | Mira en |
|------------------|---------|
| Cómo se deriva la categoría del dato sucio | `app/etl.py` |
| Cómo la frase se vuelve filtros tipados (m05) | `app/intent.py` |
| Por qué el presupuesto es un WHERE y no ranking | `app/search.py` · [`adr/0003`](docs/adr/0003-filtros-duros-no-ranking.md) |
| Cómo se impide un precio inventado | `guardrails/price_guard.py` · [`adr/0002`](docs/adr/0002-grounding-determinista-no-llm-judge.md) |
| El lazo redacción → verificación → reintento → fallback | `app/agent.py` |
| Por qué se verifica-y-luego-se-emite (streaming) | `app/streaming.py` |
| Cómo se cachea una petición repetida | `cache/semantic_cache.py` |
| Cómo se hace el A/B del tono de la vendedora | `prompts/experimentos.py` · `observability/feedback.py` |
| La métrica que decide un deploy | `evals/retail_metric.py` · `evals/ci_gate.py` |
| Por qué RAG y no fine-tuning | [`adr/0004`](docs/adr/0004-rag-no-fine-tuning.md) |
| Cómo escala (embeddings, vector DB) | [`adr/0005`](docs/adr/0005-escalabilidad-embeddings-vector-db.md) |
| Qué tocar cuando algo falla | [`docs/README_runbook.md`](docs/README_runbook.md) |

---

## 5) Cómo se prueba (61 tests, cero cuota, cero Docker)

```bash
uv run pytest proyecto_retail/tests -m offline    # ~1 s
```

Todo lo caro entra **por parámetro**: `crear_app()` recibe el responder, el caché
y el colector; `responder_con_guardrail()` recibe el LLM; la métrica recibe el
`responder`. Por eso la API entera se levanta con un `TestClient` y un responder
falso, sin modelo y sin Redis.

Lo que de verdad se afirma no es "el modelo responde bien" (eso lo mide `evals/`),
sino **las invariantes**: que una inyección nunca llegue al agente, que un HIT de
caché nunca lo llame, y que **una respuesta con un precio inventado nunca salga**.
