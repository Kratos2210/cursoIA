# Setup y solución de problemas

Todo lo necesario para dejar el curso corriendo, y qué hacer cuando algo se rompe.
Si solo quieres arrancar, la [ruta rápida](#ruta-rápida-uv) son cuatro comandos.

---

## Ruta rápida (uv)

`uv` es el camino recomendado: resuelve el entorno y las dependencias en un paso y
respeta `uv.lock`, así que instalas exactamente las versiones con las que se
escribió el curso.

```bash
cd curso_ejemplos
uv sync                    # entorno + dependencias desde pyproject.toml
cp .env.example .env       # pon tu llave dentro
uv run python 01_primer_modelo.py
```

¿No tienes `uv`? `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) o
`pip install uv`.

---

## Ruta alternativa (pip)

Funciona igual de bien; solo pierdes el lockfile, así que puedes acabar con
versiones más nuevas que las probadas. Si algo falla de forma rara, ese suele ser
el motivo.

```bash
cd curso_ejemplos
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .                   # dependencias base desde pyproject.toml
cp .env.example .env
python 01_primer_modelo.py
```

Instalar con `-e .` (y no `pip install -r requirements.txt`) es lo que mantiene
`pyproject.toml` como única fuente de verdad. `requirements.txt` se conserva solo
por compatibilidad con entornos que lo exijan.

### Extras: lo que no viene en la instalación base

Cada extra cubre un tramo del curso. Instala solo el que necesites.

| Extra | Para qué | uv | pip |
|---|---|---|---|
| `dev` | tests (`pytest`, `httpx`) | `uv sync --extra dev` | `pip install -e ".[dev]"` |
| `emb` | embeddings locales sin gastar cuota (m11, m12, proyecto final) | `uv sync --extra emb` | `pip install -e ".[emb]"` |
| `llmops` | API y stack de producción (`proyecto_llmops`) | `uv sync --extra llmops` | `pip install -e ".[llmops]"` |
| `ui` | interfaz de chat (m25) | `uv sync --extra ui` | `pip install -e ".[ui]"` |
| `hf` | fine-tuning local (m21b) | `uv sync --extra hf` | `pip install -e ".[hf]"` |
| `qdrant` | vector DB de producción (m24) | `uv sync --extra qdrant` | `pip install -e ".[qdrant]"` |
| `whatsapp` | canal de WhatsApp (m31) | `uv sync --extra whatsapp` | `pip install -e ".[whatsapp]"` |
| `llamaindex`, `crewai` | frameworks alternativos (m32) | `uv sync --extra llamaindex` | `pip install -e ".[llamaindex]"` |
| `voice` | agente de voz realtime (m33) | `uv sync --extra voice` | `pip install -e ".[voice]"` |

Con pip puedes combinarlos: `pip install -e ".[dev,emb]"`.

Cada carpeta de anexo trae su propio README con el detalle (qué es, cómo se
corre y el ADR que lo respalda): [frameworks/](frameworks/README.md) ·
[canales/](canales/README.md) · [voz/](voz/README.md) ·
[rerank/](rerank/README.md) · [vectordb/](vectordb/README.md).

---

## Proveedores de modelo

Todos los ejemplos llaman a `util.crear_llm()`, que lee el proveedor del `.env`.
Cambiar de proveedor es cambiar dos líneas, nunca código.

| Proveedor | `.env` | Nota |
|---|---|---|
| Gemini (por defecto) | `GOOGLE_API_KEY=…` | [llave gratis](https://aistudio.google.com); cuota muy corta |
| Groq | `LLM_PROVIDER=groq` + `GROQ_API_KEY=…` | [llave gratis](https://console.groq.com/keys); cuota mucho más holgada |
| Ollama | `LLM_PROVIDER=ollama` | en tu máquina, sin llave ni internet |
| OpenAI / Claude / OpenRouter / DeepSeek | ver [README §9](README.md#9-cambiar-de-proveedor-gemini-groq-openai-claude-openrouter-deepseek-ollama) | de pago |

**Los embeddings no siguen a `LLM_PROVIDER`.** Groq no ofrece embeddings, así que
los módulos de RAG seguirían gastando `GOOGLE_API_KEY` solo para vectorizar. Para
cortar ese gasto: `uv sync --extra emb` y `EMBEDDINGS_PROVIDER=fastembed`, que los
calcula localmente.

---

## Solución de problemas

### `429 RESOURCE_EXHAUSTED`

El más común, y **no es un error de tu código**: es el límite del plan gratuito de
Gemini. Por orden de preferencia: pásate a Groq (dos líneas en el `.env`), espera
unos minutos, o activa facturación.

Mientras tanto corre los ejemplos que no gastan nada: `07`, `12`, `13b`, `14`,
`15`, `16` y `16b`. Receta completa en el
[runbook](docs/README_runbook.md#31-429-resource_exhausted--el-más-común).

### `ModuleNotFoundError` o el import no encuentra `util`

Casi siempre es que estás fuera del directorio. Los comandos se corren **desde
dentro de** `curso_ejemplos/`, que es donde vive el `pyproject.toml`. Para
confirmar dónde estás parado:

```bash
uv run python -c "import sys; print(sys.prefix)"   # debe terminar en curso_ejemplos/.venv
```

Con pip, el equivalente es comprobar que el `venv` está activado (el prompt
muestra `(.venv)`).

### La llave está en el `.env` y aun así dice que falta

Comprueba que copiaste `.env.example` a `.env` (no al revés), que el archivo está
en `curso_ejemplos/` y que la línea no tiene comillas ni espacios alrededor del
`=`.

### Un ejemplo de RAG devuelve resultados sin sentido

Si cambiaste `EMBEDDINGS_PROVIDER` con un índice ya construido, los vectores
viejos y los nuevos viven en espacios distintos: el resultado no es *peor*, es
*sin sentido*, y no lanza ningún error. Borra el índice y reindexa.

### Los tests fallan

```bash
uv run pytest -m offline     # no gasta tokens ni necesita llave
```

Si fallan los `offline`, el problema es del entorno, no de tu cuota. Revisa que
instalaste el extra `dev`.

### Runbooks de operación

Para lo que ocurre en ejecución (servicios caídos, latencia, costes disparados),
cada proyecto trae el suyo:

- [Runbook del curso](docs/README_runbook.md)
- [Runbook de `proyecto_llmops`](proyecto_llmops/docs/README_runbook.md)
- [Runbook de `proyecto_retail`](proyecto_retail/docs/README_runbook.md)

---

## Verificar que todo está bien

```bash
uv run pytest -m offline          # suite completa sin gastar un token
uv run python verificar_curso.py  # coherencia del material del curso
```
