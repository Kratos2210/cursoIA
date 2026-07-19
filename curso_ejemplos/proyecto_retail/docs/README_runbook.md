# Runbook — asistente de compras Sifrah (qué tocar cuando algo falla)

La documentación de arquitectura y el *por qué* de cada decisión están en
[`adr/`](adr/). Esto es lo otro: qué hacer a las 11pm cuando algo se rompe.

---

## 1. El asistente inventa un precio (no debería pasar nunca)

**Síntoma:** una respuesta cita un `S/xx.xx` que no está en el catálogo.

Por diseño, esto **no puede llegar al cliente**: `guardrails/price_guard.py`
verifica cada precio, y si falla dos veces (redacción + reintento), gana el
fallback determinista `armar_respuesta`, fiel por construcción (ver
[ADR-0002](adr/0002-grounding-determinista-no-llm-judge.md)).

**Si aun así ves un precio inventado en producción:**
1. Comprueba que la respuesta salió por el pipeline (`app/agent.py`) y no por un
   atajo que se saltó el guardrail. El guardrail solo protege lo que pasa por él.
2. Revisa el formato: `price_guard` reconoce `S/xx.xx`. Si el modelo escribió el
   precio en letras ("diecinueve noventa"), se le escapa — endurece el prompt
   (`prompts/vendedora.yaml`) para exigir el formato con SKU y precio numérico.
3. Añade el caso a `evals/dataset.jsonl` y corre el gate: debe quedar como
   regresión.

---

## 2. Un 429 / RESOURCE_EXHAUSTED del proveedor

**Síntoma:** el `/chat` devuelve un evento `error` con "429" o "RESOURCE_EXHAUSTED".

La cuota del proveedor se agotó. Cambiar de proveedor es cambiar el `.env`, no el
código:
```
# de Groq a Ollama (local, sin cuota):
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODELO=qwen3:8b
```
Reinicia el servicio. Ver `app/llm.py` y `app/config.py`.

---

## 3. El catálogo cambió y el asistente recomienda algo agotado / con precio viejo

**Causa probable:** el caché sirvió una respuesta vieja. El caché tiene TTL de
24h, pero un cambio urgente (una promo que se acabó hoy) no espera.

**Cura:** vaciar el caché.
- Sin Redis (memoria): reinicia el proceso.
- Con Redis: `docker compose -f proyecto_retail/docker-compose.yml exec redis redis-cli DEL retail:cache`

Y actualiza el catálogo: en producción `CATALOGO_FUENTE=live` (baja el real); en
demo, edita `data/catalogo_demo.json`.

---

## 4. La categoría de un producto sale mal ("otros", o clasificada donde no es)

**Causa:** el ETL (`app/etl.py`) deriva la categoría del título+tags con una
lista de reglas (`CATEGORIAS`). Un producto nuevo con vocabulario que las reglas
no conocen cae en "otros".

**Cura:** añade la palabra clave a `CATEGORIAS` (respeta el ORDEN: las reglas más
específicas van antes; por eso "gancho"/"colet" van antes que "cabello", para que
el cepillo no se cuele). Añade un test en `tests/test_retail_etl.py`.

Correr `uv run python proyecto_retail/data/fetch_catalogo.py` lista los productos
reales que cayeron en "otros": es el punto de partida.

---

## 5. El CI gate bloquea un deploy

**Síntoma:** `ci_gate.py` sale con código 1.

Lee los motivos que imprime:
- **"Score X% < umbral"** → el asistente respeta menos casos de los exigidos.
  Mira el reporte: ¿qué casos fallan y por qué (presupuesto, stock, precio)?
- **"PRECIO INVENTADO en '…'"** → cero tolerancia. Un solo caso infiel bloquea,
  aunque la media pase. Es lo que la media esconde (ver
  [ADR-0002](adr/0002-grounding-determinista-no-llm-judge.md) y el gate).

No "aflojes" el umbral para que pase: arregla el caso o, si el caso está mal
planteado, corrígelo en `evals/dataset.jsonl` a conciencia.

---

## 6. El servicio no arranca

- **`Falta LLM_API_KEY…`** → copia `.env.example` a `.env` y pon tu llave.
- **`No existe el prompt 'vendedora'`** → revisa `prompts/` (deben estar
  `vendedora.yaml` y `vendedora_directa.yaml`).
- **El caché no conecta a Redis** → no es un error: degrada a memoria solo. Si
  quieres Redis, `docker compose -f proyecto_retail/docker-compose.yml up -d`.

---

## Comprobación rápida de salud

```bash
# Tests (offline, sin cuota):
uv run pytest proyecto_retail/tests -m offline -q

# El servicio arranca:
uv run uvicorn proyecto_retail.app.main:app --port 8000
curl -s localhost:8000/health
```
