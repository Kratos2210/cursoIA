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

## 5) Cómo se prueba (127 tests, cero cuota, cero Docker)

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

---

## Criterios de aceptación · cómo se ve un proyecto bien hecho

El gate de `evals/ci_gate.py` dice *pasa / no pasa*, pero un gate verde no
significa proyecto terminado: mide la fidelidad de las respuestas, no la calidad
del sistema que las produce. Esto es lo otro.

Cada ítem es **verificable**: un comando que corre, un umbral concreto o un
archivo que existe. Si no puedes demostrarlo con una de esas tres cosas, no
está hecho.

> La regla que ordena toda esta rúbrica: **precio y stock jamás salen del
> modelo**. Todo lo de abajo existe para defender esa frontera.

### 1 · Funcionalidad — el asistente vende lo que hay, al precio que es

- [ ] **Criterio:** `uv run uvicorn proyecto_retail.app.main:app --port 8000`
  levanta sin excepciones, `http://localhost:8000/` sirve el chat y
  `curl -N -X POST localhost:8000/chat -H "Content-Type: application/json" -d
  '{"mensaje":"quiero aretes dorados por menos de 25 soles"}'` responde en
  **streaming SSE**.
- [ ] **Criterio:** ese mismo caso **no recomienda nada por encima de S/25** ni
  nada con `available: false`. El presupuesto es un **WHERE**, no una señal de
  ranking (`app/search.py`, [`adr/0003`](docs/adr/0003-filtros-duros-no-ranking.md)).
- [ ] **Criterio:** «un collar de zircón por menos de 10 soles» (nada cumple)
  responde **lista vacía y lo dice**, en vez de ofrecer un sustituto fuera de
  presupuesto. "No tengo" es una respuesta válida; mentir no.
- [ ] **Criterio:** el ETL de `app/etl.py` **deriva la categoría del título y
  los tags**, no de `product_type` — que en el catálogo real dice "Joyería"
  hasta en las mochilas y los cepillos. Verifícalo: la mochila sale como
  `mochilas` y el cepillo como `belleza`, no como joyas.
- [ ] **Criterio:** `app/intent.py` convierte la frase en **filtros tipados**
  (m05, `with_structured_output`), y entiende el vocabulario de la clienta
  ("aros", "pelo", "cadena"), no solo el del catálogo.

### 2 · Evaluación y calidad — la métrica que decide un deploy

- [ ] **Criterio:** `uv run python proyecto_retail/evals/run_evals.py` imprime
  el **% de casos fieles** y detalla cuáles fallaron, no solo el agregado.
- [ ] **Criterio:** `uv run python proyecto_retail/evals/ci_gate.py ; echo $?`
  devuelve **0**, con un score ≥ `EVAL_UMBRAL_APROBACION` (**0.9** por defecto,
  en `app/config.py`).
- [ ] **Criterio:** las **dos puertas** funcionan por separado. `evaluar_puertas`
  es una función pura: constrúyele un `Reporte` a mano y comprueba que
  - un score de **0.85** bloquea (puerta de la media), y
  - **un solo** caso con `fiel=False` bloquea aunque el score sea 0.90 o más
    (cero tolerancia al precio inventado).
- [ ] **Criterio:** `evals/dataset.jsonl` tiene **al menos los 8 casos**
  actuales e incluye los tres tipos que importan: presupuesto ajustado, stock
  agotado y **petición imposible** (donde la respuesta correcta es "no tengo").
- [ ] **Criterio:** el eval atrapa a un asistente deliberadamente malo. Pásale
  un responder que ignore el presupuesto y comprueba que la métrica **baja** —
  como hace `asistente_descuidado` en `29_caso_retail.py`. Una métrica que no
  distingue al bueno del malo no mide nada.
- [ ] **Criterio:** `EVAL_MUESTRA` está en **1.0** (el dataset entero): con 13
  casos, muestrear no ahorra nada y sí esconde regresiones.

### 3 · Grounding y guardrails — el precio inventado no sale

- [ ] **Criterio:** `guardrails/price_guard.py` verifica que **cada precio
  citado** en la respuesta exista en los productos recuperados. Un `S/` que el
  modelo se inventó dispara el fallo.
- [ ] **Criterio:** el lazo completo funciona y se puede observar:
  **redacción → verificación → reintento → fallback determinista**
  (`app/agent.py`). Fuerza un fallo con un LLM falso que invente un precio y
  comprueba que lo que sale es el **fallback**, no el invento.
- [ ] **Criterio:** el streaming es **verificar-y-luego-emitir**
  (`app/streaming.py`): ni un token con un precio sin verificar llega al
  navegador. Un guardrail que corrige *después* de emitir no corrige nada.
- [ ] **Criterio:** la respuesta **no re-inyecta el texto del usuario**. Un
  "hasta S/80" ecoado en la salida dispara el guardrail, porque ese S/80 no es
  un precio del catálogo (la trampa documentada en `29_caso_retail.py`).
- [ ] **Criterio:** un mensaje del tipo "invéntate un precio más barato" es
  bloqueado en `guardrails/input_guard.py` **sin gastar tokens**.

### 4 · Observabilidad, resiliencia y coste

- [ ] **Criterio:** cada petición registra **latencia, TTFT, coste y disparos de
  guardrail** en `observability/`. Los guardrails que saltan son una métrica de
  producto, no solo un log.
- [ ] **Criterio:** el A/B del tono de la vendedora funciona: dos variantes de
  `prompts/experimentos.py` se sirven y `observability/feedback.py` atribuye el
  feedback **a la variante correcta**.
- [ ] **Criterio:** sin Redis y sin llaves de Langfuse, la app **sigue en pie**:
  el caché degrada a memoria y el tracing se apaga solo.
- [ ] **Criterio:** el caché semántico acierta con una petición reformulada por
  encima de `CACHE_UMBRAL_SIMILITUD` (**0.92**) y un HIT **nunca invoca al
  LLM** — demostrable con un doble que cuente llamadas.
- [ ] **Criterio:** `BUSQUEDA_TOP_K` (**3** por defecto) acota lo que se
  recomienda; subirlo no debe romper el grounding.

### 5 · Documentación e ingeniería — otro puede recogerlo

- [ ] **Criterio:** `uv run pytest proyecto_retail -m offline` colecta **127
  tests** y pasa en verde, **sin Docker, sin llave y sin cuota**, en ~1 s.
- [ ] **Criterio:** existe un ADR por cada decisión no obvia. Hoy son **5**
  (`docs/adr/0001`–`0005`), incluida la más discutible: **por qué el grounding
  es determinista y no un LLM-as-judge**
  ([`adr/0002`](docs/adr/0002-grounding-determinista-no-llm-judge.md)).
- [ ] **Criterio:** `prompts/vendedora.yaml` está versionado y su tono se cambia
  **sin tocar código**.
- [ ] **Criterio:** `docs/README_runbook.md` responde, para cada fallo probable
  (catálogo desactualizado, LLM caído, gate en rojo, precios que no cuadran),
  **qué mirar y qué hacer**.
- [ ] **Criterio:** los tests afirman **invariantes**, no respuestas concretas
  del modelo: que una inyección nunca llegue al agente, que un HIT de caché
  nunca lo llame, y que una respuesta con precio inventado nunca salga.
