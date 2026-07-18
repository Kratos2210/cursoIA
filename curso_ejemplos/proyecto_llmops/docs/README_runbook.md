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

# ¿Qué está pasando? (con METRICAS_BACKEND=memoria es POR PROCESO)
curl -s -H "X-API-Key: $API_KEY" localhost:8000/metrics | jq

# ¿Están los servicios en pie?
docker compose -f proyecto_llmops/docker-compose.yml ps
```

`/health` responde sin llamar al modelo y **sin credencial**, a propósito: el
orquestador no tiene llaves, y un `/health` con auth convertiría un error de
configuración en un reinicio en bucle. Si `/health` va y `/chat` no, el problema
está **aguas abajo**: el proveedor del LLM, Postgres o Redis.

Dos campos de `/health` que ahorran media investigación:

| Campo | Si vale… | Significa |
|---|---|---|
| `auth_activa` | `false` | **El servicio está abierto**: no hay `API_KEYS` y cualquiera puede consultar eligiendo su propio rol. Correcto en la demo del curso; en producción es el incidente |
| `agente_listo` | `false` | El lifespan no terminó de construir el agente. Suele ser la descarga de embeddings del primer arranque |

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

> ⚠️ **Primero: ¿de quién es el 429?** Desde la Fase 1 hay DOS fuentes de 429 y
> se diagnostican al revés. Mira el cuerpo de la respuesta:
>
> | Cuerpo | Origen | Sección |
> |---|---|---|
> | `{"error": "Demasiadas peticiones. Espera un momento."}` | **Nuestro** limitador (`app/rate_limit.py`) | §2b |
> | Un error del proveedor, o un `event: error` por el stream SSE | El proveedor del LLM | esta sección |
>
> El nuestro trae `Retry-After` y aparece en el log como
> `"límite de peticiones excedido"` con el campo `cliente`. El del proveedor no
> llega a producir esa línea porque ni siquiera salimos de casa.

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

## 2b) Nuestro propio 429 · el limitador de peticiones

| Síntoma | Causa probable | Acción |
|---|---|---|
| Un cliente legítimo recibe 429 en uso normal | `RATE_LIMIT_PETICIONES` demasiado bajo para su patrón de uso | Subirlo, o darle su propia API key: el límite se cuenta **por credencial**, no por servicio |
| **Todos** los usuarios se limitan entre sí | Hay un proxy delante y todos comparten IP | Dales credenciales (`API_KEYS`): con `X-API-Key` cada uno tiene su cubo. Ver el aviso sobre `X-Forwarded-For` en `app/rate_limit.py` |
| El límite "no funciona" con varios workers | Es **por proceso**: con N workers el efectivo es N × límite | Es una limitación conocida y documentada. El límite de verdad va en el reverse proxy (`nginx limit_req`) o en Redis |
| Memoria del proceso creciendo despacio | Clientes acumulados en el limitador | `olvidar_inactivos()` los descarta; si nadie lo llama periódicamente, crece. Revisar |

```bash
# Quién está siendo limitado (los clientes van anonimizados: key:…abc123)
docker compose -f proyecto_llmops/docker-compose.yml logs app \
  | grep '"mensaje": "límite de peticiones excedido"' | jq -r .cliente | sort | uniq -c
```

---

## 2c) `401` · credenciales

| Síntoma | Causa probable | Acción |
|---|---|---|
| Todo devuelve 401 de golpe tras un deploy | Se definió `API_KEYS` y los clientes aún no mandan `X-API-Key` | Repartir las claves, o vaciar `API_KEYS` para volver al modo abierto **a sabiendas** |
| Un rol no ve lo que debería | El rol sale de la CREDENCIAL, no del body: la clave otorga menos nivel del que se pide | Revisar el mapeo `clave:rol`. El intento queda en el log como `"se ignora el rol del body"` con `rol_pedido` y `rol_efectivo` |
| `/metrics` da 401 desde un script | `/metrics` está detrás de auth desde la Fase 1 | Añadir la cabecera `X-API-Key` |
| Una clave del `.env` no funciona | Rol inexistente en el mapeo: la entrada se descarta al arrancar | Buscar `"API_KEYS otorga un rol desconocido"` en el log del arranque. Roles válidos: `public`, `analyst`, `compliance` |

---

## 2d) Investigar UNA petición concreta

Desde la Fase 1 cada línea de log es un JSON con `request_id`, y ese id se
devuelve en la cabecera `X-Request-ID`. Cuando alguien reporta un fallo, pídeselo:

```bash
# Todo lo que ocurrió en esa petición, en orden
docker compose -f proyecto_llmops/docker-compose.yml logs app \
  | grep '"request_id": "a3f9c1b2"' | jq -c '{ts, nivel, mensaje, ruta, estado}'

# Los errores de la última hora, con su traceback
docker compose -f proyecto_llmops/docker-compose.yml logs --since 1h app \
  | jq -c 'select(.nivel == "ERROR") | {ts, mensaje, request_id, excepcion}'
```

> Si el cliente entra por un proxy que ya pone `X-Request-ID`, se **respeta** ese
> id: la traza cose de punta a punta y no empieza de cero en cada salto.
>
> ⚠️ Lo que **no** vas a encontrar en el log es la pregunta del usuario ni la
> respuesta del modelo. Es deliberado: pueden traer PII y los logs suelen acabar
> en un tercero. Para el contenido está Langfuse (§7), que es infraestructura
> tuya.

---

## 3) Postgres / pgvector

| Síntoma | Qué pasó | Acción |
|---|---|---|
| El servicio arranca pero las respuestas ignoran la normativa | `construir_agente_real()` **degradó a memoria** porque Postgres no respondía. Arranca, pero no es producción | `docker compose up -d postgres`, y reiniciar el servicio |
| `connection refused` en el puerto 5433 | El compose mapea 5433 (host) → 5432 (contenedor) | Comprobar `PG_PORT=5433` en el `.env` |
| El RAG devuelve fragmentos duplicados | Desde la Fase 2 el indexado **es idempotente** (id derivado del contenido, `app/rag.py::id_de_fragmento`). Si aún duplica, lo indexado ANTES del cambio tiene ids viejos que ya no coinciden | Vaciar y reindexar UNA vez: `DELETE FROM langchain_pg_embedding;` y reiniciar. A partir de ahí, reindexar actualiza en vez de insertar |
| Corregiste la confidencialidad de un fragmento y sigue saliendo con la vieja | El nivel entra en el hash del id, así que la corrección crea una fila NUEVA; la antigua sigue ahí | Borrar la fila antigua. El id cambia a propósito: si no, la corrección se perdería |

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

## 4b) `/metrics` no cuadra

| Síntoma | Causa probable | Acción |
|---|---|---|
| Los números **bajan** entre dos llamadas seguidas | `METRICAS_BACKEND=memoria` y hay varios workers: cada llamada la atiende uno distinto y cada uno cuenta lo suyo | `METRICAS_BACKEND=postgres`. Es exactamente lo que cierra esta trampa |
| El historial se borró | Backend en memoria + reinicio (deploy, OOM) | Igual: persistir en Postgres |
| `costo_total: 0` con tráfico real | El proveedor no informó del consumo, o el modelo no está en la tabla de precios | Un 0 significa **"no sé"**, nunca "fue gratis". Ver `cost_model.PRECIOS` y el aviso `modelo_desconocido` |
| Todo en cero y la base está caída | El backend de Postgres **degrada a propósito**: prefiere perder la métrica a tumbar la petición | Buscar `"no se pudieron leer las métricas"` en el log. El servicio está sano; el que no está es el almacén |

```bash
# ¿De verdad se están escribiendo?
docker compose -f proyecto_llmops/docker-compose.yml exec postgres \
  psql -U gobdata -c "SELECT count(*), max(creado_en) FROM metricas_request;"
```

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
