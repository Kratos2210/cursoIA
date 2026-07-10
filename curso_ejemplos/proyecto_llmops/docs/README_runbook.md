# Runbook — GobData en producción

> Qué hacer cuando algo falla a las 11 de la noche. Sin narrativa, sin teoría:
> síntoma → diagnóstico → acción.

El runbook del prototipo ([`curso_ejemplos/docs/README_runbook.md`](../../docs/README_runbook.md))
cubre los fallos del código. Este cubre los del **servicio**: los que aparecen
cuando hay usuarios, servicios levantados y una factura.

---

## 0) Los tres comandos que se ejecutan primero, siempre

```bash
# ¿Está vivo el servicio y qué cree él de sí mismo?
curl -s localhost:8000/health | jq

# ¿Qué está pasando? (por proceso: con varios workers, mira Langfuse)
curl -s localhost:8000/metrics | jq

# ¿Están los servicios en pie?
docker compose -f proyecto_llmops/docker-compose.yml ps
```

`/health` responde sin llamar al modelo, a propósito. Si `/health` va y `/chat`
no, el problema está **aguas abajo** del servicio: el proveedor del LLM,
Postgres o Redis.

---

## 1) El servicio no arranca

| Síntoma | Causa probable | Acción |
|---|---|---|
| `ValueError: Falta LLM_API_KEY` | No hay `.env`, o está en la carpeta equivocada | `cp proyecto_llmops/.env.example proyecto_llmops/.env` y rellenar |
| `ModuleNotFoundError: fastapi` | Falta el extra | `uv sync --extra llmops` |
| Cuelga ~30 s y arranca | Está descargando el modelo de embeddings (~220 MB), solo la primera vez | Esperar. La segunda vez es instantáneo |
| `ImportError: EMBEDDINGS_PROVIDER=huggingface necesita el extra 'hf'` | macOS Intel, o falta el extra | `EMBEDDINGS_PROVIDER=fastembed` en el `.env`. Es el **mismo modelo** |

---

## 2) `429 RESOURCE_EXHAUSTED` / rate limit del proveedor

**Es lo más frecuente, y casi nunca es un bug.**

1. Confirma que la cascada hizo su trabajo: `app/llm.py::crear_cascada()` salta
   solo al modelo `strong` cuando el `cheap` devuelve 429. Si el `strong` también
   está agotado, no hay nada que saltar.
2. Comprueba que `LLM_MODELO_CHEAP` y `LLM_MODELO_STRONG` son **distintos**. Si
   son el mismo, `with_fallbacks` reintenta con el modelo que acaba de fallar.
3. Mitigación inmediata: bajar el tráfico o esperar. La cuota es por minuto.
4. Mitigación real: **subir la tasa de aciertos del caché**.
   `curl -s localhost:8000/metrics | jq .cache_tasa_aciertos`.
   Si está por debajo de 0.1, el caché no está trabajando (ver §5).

---

## 3) Postgres / pgvector

| Síntoma | Qué pasó | Acción |
|---|---|---|
| El servicio arranca pero las respuestas ignoran la normativa | `construir_agente_real()` **degradó a memoria** porque Postgres no respondía. Arranca, pero no es producción | `docker compose up -d postgres`, y reiniciar el servicio |
| `connection refused` en el puerto 5433 | El compose mapea 5433 (host) → 5432 (contenedor) | Comprobar `PG_PORT=5433` en el `.env` |
| El RAG devuelve fragmentos duplicados | `add_documents()` **no es idempotente**: se indexó dos veces (ver ADR-0003, consecuencias negativas) | Vaciar la colección y reindexar: `DELETE FROM langchain_pg_embedding;` y reiniciar |

**Depurar qué recuperó el retriever** (sin levantar la app entera):

```bash
uv run python -c "
from app import rag
r = rag.construir_retriever_pgvector()
print(rag.recuperar(r, '¿cuántos años se conservan?', rol='analyst'))
"
```

Si eso devuelve vacío para un `analyst`: la heurística de
`clasificar_confidencialidad()` está marcando la normativa como `restricted`.
Ya pasó una vez y hay tests que lo fijan (`test_rag_rbac.py`).

---

## 4) Un usuario dice que el asistente respondió algo que no debía

**Este es el incidente que importa.** Orden de investigación:

1. **Busca la traza en Langfuse** (`http://localhost:3000`), filtra por
   `thread_id`. Ahí ves el prompt exacto, los fragmentos recuperados y la
   respuesta.
2. **¿Qué fragmentos recuperó?** Si entre ellos hay uno `restricted` y el rol era
   `analyst`, el fallo está en `guardrails/rbac.py` o en la clasificación de
   `app/rag.py`. **Ese es el bug**, no el modelo.
3. **¿Saltó el `output_guard`?** Si el usuario recibió `"No tengo autorización
   para responder eso"`, el sistema funcionó: la última red atrapó una fuga que
   el RBAC dejó pasar. Igualmente hay un bug aguas arriba — la red no debería
   haber tenido que actuar.
4. **¿Vino de la caché?** Mira `cache_hit` en la traza. Un HIT que devuelve
   material restringido a un rol bajo significa que el aislamiento por rol se
   rompió: es un **incidente de seguridad**, no un bug de rendimiento.
   Acción inmediata: vaciar la caché (§5) y revisar `cache_backends.py`.

> ⚠️ Recuerda el límite que el propio código documenta: los guardrails detectan
> **patrones conocidos**. Si el modelo parafrasea un anexo restringido sin usar
> ninguna palabra canario, ninguna capa lo ve. La defensa de verdad es que el
> retriever no le entregue al modelo lo que no debe leer.

---

## 5) La caché

```bash
# ¿Está sirviendo de algo?
curl -s localhost:8000/metrics | jq '{cache_tasa_aciertos, tasa_cache}'

# Vaciarla entera (tras un cambio urgente de normativa, o ante un incidente)
docker compose -f proyecto_llmops/docker-compose.yml exec redis redis-cli FLUSHDB

# Vaciar solo un rol
docker compose ... exec redis redis-cli DEL gobdata:cache:analyst
```

| Síntoma | Causa | Acción |
|---|---|---|
| `cache_tasa_aciertos` ≈ 0 | Redis no responde y se degradó a memoria, **o** cada worker tiene su propia caché in-memory | `docker compose up -d redis`. Comprobar `REDIS_PORT=6380` |
| El asistente responde con normativa antigua | Respuesta cacheada de antes del cambio. El TTL es de 24 h | `FLUSHDB` |
| Dos preguntas distintas dan la misma respuesta | Falso positivo: el umbral es demasiado bajo | Subir `CACHE_UMBRAL_SIMILITUD` (0.92 → 0.95) y `FLUSHDB` |

**Cambiaste la normativa** → hay que hacer dos cosas, y olvidar una es el error
clásico: reindexar pgvector **y** vaciar la caché. Si solo reindexas, los HITs
siguen sirviendo la respuesta vieja durante 24 h.

---

## 6) El eval gate bloqueó un deploy

```bash
uv run python proyecto_llmops/evals/ci_gate.py    # exit 1 = bloqueado
```

El motivo del bloqueo **nombra la métrica que falla**. Léelo, porque cada una
manda a un sitio distinto:

| Métrica hundida | Dónde está el problema | Qué NO arregla nada |
|---|---|---|
| `faithfulness` | El modelo alucina → el **prompt** (`prompts/agente_gobdata.yaml`) | Cambiar el retriever |
| `answer_relevance` | El modelo divaga → el **prompt** | Cambiar el vector store |
| `context_precision` | El **retriever** trae los fragmentos equivocados → chunking, `k`, o búsqueda híbrida | Cambiar de LLM. Le estás dando los párrafos equivocados |

Si el motivo es `Ejemplo crítico`, hay **un caso roto** que la media escondía.
Mira cuál: suele ser `trampa_alucinacion` o `rbac_denegado`, y los dos son graves.

> No subas el umbral para que pase. `EVAL_UMBRAL_APROBACION` es un contrato, no
> un obstáculo. Si lo bajas para desplegar hoy, mañana no protege de nada.

---

## 7) Langfuse dejó de mostrar trazas

Es el fallo más silencioso del sistema, porque `observability/tracing.py` captura
toda excepción a propósito (un observador que tumba lo observado no es
observabilidad). Consecuencia: **si el tracing se rompe, nadie recibe una alerta**.

1. `curl -s localhost:8000/health | jq .tracing` → ¿`true`? Si es `false`, faltan
   `LANGFUSE_PUBLIC_KEY` o `LANGFUSE_SECRET_KEY` (hacen falta **las dos**).
2. `docker compose ps langfuse` → ¿en pie?
3. ¿Es un script corto (`run_evals.py`, `ci_gate.py`)? El SDK encola y envía en
   lotes desde un hilo de fondo. Un proceso que muere con el buffer lleno pierde
   las trazas en silencio. Por eso esos scripts llaman a `tracing.vaciar()` al
   final; si escribes uno nuevo, hazlo tú también.

**Ponlo en el calendario**: mirar la UI de Langfuse una vez por semana. Es la
única forma de detectar que el tracing lleva días caído.

---

## 8) Rollback

```bash
git revert <sha>            # el prompt, el código
docker compose restart      # los servicios
```

Un cambio de prompt es un cambio de comportamiento. `prompts/agente_gobdata.yaml`
lleva `version:` y un changelog precisamente para esto: en un incidente, la
pregunta "¿qué versión del prompt servíamos el martes?" tiene respuesta.

Tras cualquier rollback que toque el prompt o el retriever: **`FLUSHDB`**. Si no,
la caché sigue sirviendo las respuestas de la versión que acabas de revertir.
