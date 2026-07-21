# 📕 Runbook — operar el curso y el proyecto final

Un **runbook** no explica qué es un agente. Explica qué teclas tocar cuando
algo se rompe a las 11 de la noche. Está escrito para que lo siga alguien que
no escribió este código.

> El README.md del curso es la *documentación*. Esto es la *operación*.

---

## 1. Puesta en marcha (desde cero)

```bash
cd /Users/lbeto/proyectos/spec-sdd/studylangchainnivelinter

# 1) Dependencias. El canon es curso_ejemplos/pyproject.toml.
cd curso_ejemplos && uv sync --extra dev

# 2) La llave. NUNCA se commitea.
cp .env.example .env
$EDITOR .env          # pega tu GOOGLE_API_KEY de https://aistudio.google.com

# 3) Verificación que NO gasta cuota (debe pasar todo):
uv run pytest -m offline

# 4) Verificación que SÍ gasta cuota (una llamada):
uv run python 01_primer_modelo.py
```

**Criterio de "está sano":** el paso 3 termina en verde y el paso 4 imprime una
respuesta del modelo.

---

## 2. Variables de entorno

| Variable | ¿Obligatoria? | Para qué | Si falta |
|----------|---------------|----------|----------|
| `GOOGLE_API_KEY` | Sí, salvo los offline | Llamar a Gemini (chat + embeddings) | El ejemplo aborta con un mensaje claro |
| `LANGSMITH_API_KEY` | No | Enviar trazas a LangSmith (tema 16b) | `16b` corre igual, sin tracing |
| `LANGSMITH_PROJECT` | No | Agrupar las trazas | Se usa `curso-langchain` |
| `LANGSMITH_TRACING` | No | La enciende `16b` sola si hay llave | — |

Los ejemplos leen el `.env` con `python-dotenv`. **`load_dotenv()` busca hacia
arriba desde el directorio actual**, así que un `.env` en la raíz del proyecto
también funciona — y también puede sorprenderte si creías estar sin llave.

### Ejemplos que NO necesitan ninguna llave
`07`, `12`, `13b`, `14`, `16` (métrica offline) y `16b` (modo offline).
Son los que corre la CI. Úsalos para verificar que el entorno está bien sin
gastar un solo token.

---

## 3. Incidentes frecuentes

### 3.1 `429 RESOURCE_EXHAUSTED` — el más común

**Síntoma:** `⏳ Cuota de Gemini agotada (429)`.

**No es un bug.** Es el límite del plan gratuito (por minuto o por día).

**Qué hacer, en orden:**
1. Espera 60 segundos y reintenta. Si era el límite *por minuto*, se arregla solo.
2. Si persiste, cambia de modelo sin tocar código: `LLM_MODELO=gemini-2.5-flash`
   en el `.env`. (Ya no hay ninguna constante `MODELO_CHAT` que editar: todo el
   curso construye el modelo con `util.crear_llm()`, que lee el `.env`.)
3. **La salida buena: cámbiate de proveedor.** `LLM_PROVIDER=groq` +
   `GROQ_API_KEY` y el curso entero pasa al modelo por defecto de Groq, con un
   cupo mucho más generoso. Llave gratis en <https://console.groq.com/keys>.
   ⚠️ Si Groq te contesta `model not found` / `model_decommissioned`, es que
   retiró ese modelo (le pasó a `qwen/qwen3-32b` en 2026-07). No es tu código:
   copia un ID vigente de <https://console.groq.com/docs/models> —o de la tabla
   de modelos del cheat sheet de la web— y ponlo en `LLM_MODELO` del `.env`.
   ⚠️ El RAG (temas 11, 12 y proyecto final) necesita **embeddings**, y Groq no
   los ofrece: seguiría gastando `GOOGLE_API_KEY` solo para vectorizar. Para no
   gastar nada: `uv sync --extra emb` y `EMBEDDINGS_PROVIDER=fastembed`, que los
   calcula en tu máquina.
4. Si sigue, es el límite *diario* de Gemini: espera al reinicio (medianoche,
   hora del Pacífico) o activa facturación en Google AI Studio.
5. Mientras tanto, sigue estudiando con los ejemplos offline (§2).

**Cómo se distingue de un problema real:** `util.es_error_cuota(exc)` busca
`429` o `RESOURCE_EXHAUSTED` en el texto del error. Cualquier otra cosa
(`401`, `PERMISSION_DENIED`, timeout) **no** es cuota: es tu llave o tu red.

### 3.2 `❌ Falta GOOGLE_API_KEY`

El `.env` no existe, está en otra carpeta, o la variable está mal escrita.

```bash
ls -la curso_ejemplos/.env                      # ¿existe?
grep GOOGLE_API_KEY curso_ejemplos/.env         # ¿la línea está bien?
uv run python -c "import os,dotenv;dotenv.load_dotenv();print(bool(os.getenv('GOOGLE_API_KEY')))"
```

Errores típicos: comillas de más (`GOOGLE_API_KEY="abc"` está bien, `= "abc"` no),
o haber copiado `.env.example` sin editarlo.

### 3.3 Un ejemplo dejó de importar tras `uv sync`

Casi siempre una librería cambió su API entre versiones.

```bash
uv run pytest tests/test_imports.py -v     # te dice EXACTAMENTE cuál y por qué
```

Ese test existe justo para esto: convierte una rotura silenciosa en un fallo
con nombre y apellido. Arregla el import y vuelve a correrlo.

### 3.4 El agente responde, pero se inventa la normativa

El RAG no está trayendo el fragmento correcto. **Depura el retrieval antes que
el prompt** — el 90% de las veces el problema está ahí:

```python
# En un REPL, dentro de curso_ejemplos/proyecto_final:
import rag
retriever = rag.construir_retriever()
print(rag.contexto(retriever, "¿cuántos años se conservan los registros?"))
```

Si el contexto no contiene la respuesta, el modelo no puede acertar: no es
alucinación, es hambre. Sube `FRAGMENTOS_POR_CONSULTA` en `config.py`, o mejora
el troceado (tema 12: híbrido + re-ranking).

### 3.5 Depurar un grafo de LangGraph

Un grafo que "no hace nada" casi siempre está esperando algo.

```python
# 1) ¿En qué nodo está parado?
estado = app.get_state(config)
print(estado.next)           # () = terminó. ('aprobar',) = está pausado ahí.

# 2) ¿Qué pidió el interrupt()?
print(estado.tasks[0].interrupts[0].value if estado.tasks else "sin interrupts")

# 3) Ver el recorrido paso a paso, nodo a nodo:
for evento in app.stream(entrada, config, stream_mode="updates"):
    print(evento)
```

**Errores clásicos:**
- `interrupt()` sin `checkpointer` → no puede reanudar. Falla siempre.
- Reanudar con un `thread_id` distinto → el grafo no encuentra su estado y
  empieza de cero.
- Un nodo que devuelve `{"messages": mensaje}` en vez de `{"messages": [mensaje]}`.

### 3.6 El log de auditoría no crece

`proyecto_final/hallazgos_auditoria.log` solo se escribe cuando el agente decide
usar `evaluar_regla_calidad`. Si preguntaste algo que resolvió con
`buscar_normativa`, **no hay hallazgo que auditar** y el log no cambia. Es correcto.

Para confirmar que la escritura funciona sin gastar cuota:
```bash
uv run pytest proyecto_final/tests/test_audit.py -v
```

---

## 4. Rollback

El repositorio no despliega nada, así que "rollback" significa **volver a un
estado que corría**.

```bash
# 1) ¿Qué cambió?
git status && git diff

# 2) Descartar cambios locales de un archivo:
git restore curso_ejemplos/11_rag.py

# 3) Volver al último commit sano (⚠️ pierde lo no commiteado):
git stash            # red de seguridad, por si acaso
git reset --hard HEAD

# 4) Verificar que volviste a un estado sano:
cd curso_ejemplos && uv run pytest -m offline
```

**Rollback de dependencias.** `uv.lock` es la receta exacta del entorno. Si un
`uv sync` rompió algo, restaura el lock anterior y re-sincroniza:

```bash
git restore curso_ejemplos/uv.lock
uv sync --extra dev
```

Por eso `uv.lock` **sí se commitea** (y el `.env`, nunca).

---

## 5. Checklist antes de dar por bueno un cambio

1. `uv run pytest -m offline` → verde.
2. `uv run python -m compileall -q .` → sin errores.
3. Si tocaste un ejemplo, córrelo: `uv run python curso_ejemplos/NN_*.py`.
4. Si tocaste el proyecto final: `uv run pytest proyecto_final/tests -v`.
5. Si tocaste el HTML del curso: republicar al **mismo `url`** del Artifact
   (si no, el enlace que tienen los alumnos se rompe).

La CI (`.github/workflows/ci.yml`) corre los pasos 1 y 2 en Python 3.11 y 3.12
en cada push. Nunca llama a la API: no gasta cuota y no falla por un 429 ajeno.

---

## 6. Mapa de "quién es responsable de qué"

| Si falla… | Mira en… |
|-----------|----------|
| La llave, las rutas, el modelo | `proyecto_final/config.py` |
| El contexto recuperado | `proyecto_final/rag.py` |
| El log de auditoría | `proyecto_final/audit.py` |
| Qué tool eligió el agente | `proyecto_final/tools.py` (los docstrings) |
| El ciclo del agente | `proyecto_final/graph_builder.py` |
| La memoria entre turnos | `proyecto_final/persistence.py` |
| El manejo del 429 | `util.py` (`es_error_cuota`) |

Las decisiones de arquitectura y **por qué** se tomaron: `docs/adr/`.
