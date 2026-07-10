# Plan: Módulo "Elegir modelo y proveedor" + conmutador ampliado

## Contexto

El curso ya conmuta de proveedor desde el `.env` (google/groq/ollama vía `util.crear_llm()`), pero no enseña **cómo elegir** modelo y proveedor para una solución real: no hay nada sobre pago vs open source, cloud gestionado (AWS Bedrock) vs on-premise (Ollama/vLLM), ni un cuadro comparativo de precios y ventanas de contexto. Además el conmutador se queda corto: faltan los proveedores de pago más usados (OpenAI, Anthropic) y un agregador de modelos open (OpenRouter, DeepSeek).

**Decisiones del usuario (ya tomadas):** añadir `openai`, `anthropic`, `openrouter`, `deepseek` al conmutador; Bedrock **solo documentado** en el HTML (sin dependencia AWS); el contenido nuevo va como **Módulo 18b** entre `#m18` (capstone) y `#llmops`. La implementación se ejecuta con **subagentes Opus 4.8** (petición explícita del usuario); el análisis/orquestación queda en la sesión principal (Fable).

## Decisiones de diseño fijadas

**Defaults por proveedor** (`MODELOS_POR_DEFECTO`):
- `openai: "gpt-5-mini"` (verificar id exacto en platform.openai.com al implementar)
- `anthropic: "claude-haiku-4-5"` ($1/$5 por 1M, 200K contexto — verificado)
- `openrouter: "meta-llama/llama-3.3-70b-instruct:free"` (gratis, no razonador, tool calling OK — verificar disponibilidad)
- `deepseek: "deepseek-chat"` (NO `deepseek-reasoner`: function calling limitado rompería temas 05/07)

**Estructura en `util.py`** — dos diccionarios:
```python
_PROVEEDORES_NATIVOS = {           # clase propia, no dialecto OpenAI
    "google": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}
_COMPATIBLES_OPENAI = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "ollama": ("http://localhost:11434/v1", "OLLAMA_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
}
```
- Rama anthropic en `crear_llm()` (import perezoso, como la de Gemini):
  `from langchain_anthropic import ChatAnthropic; return ChatAnthropic(model=modelo, temperature=temperature)`
- `reasoning_format:"hidden"` sigue siendo **exclusivo de Groq**. Para OpenRouter con modelo razonador: `extra["reasoning"] = {"exclude": True}` (su parámetro unificado). DeepSeek/OpenAI: sin parche.
- `langchain-anthropic` va en **deps base** del pyproject (precedente: langchain-openai está en base; los tests offline instancian ChatAnthropic y la CI corre `-m offline`). Añadir con `uv add`. También añadir `langchain-anthropic` y el faltante `langchain-openai` a `requirements.txt`.

## WP1 — Código y config (subagente Opus 4.8, `model: "opus"`)

Archivos: `curso_ejemplos/util.py`, `curso_ejemplos/tests/test_util.py`, `curso_ejemplos/.env.example`, `curso_ejemplos/pyproject.toml` + `uv.lock`, `curso_ejemplos/requirements.txt`, `curso_ejemplos/README.md` §9, `CLAUDE.md` (raíz — tabla de proveedores).

- `.env.example`: opciones D OpenAI (platform.openai.com/api-keys), E Anthropic (console.anthropic.com/settings/keys), F OpenRouter (openrouter.ai/keys, tiene modelos `:free`), G DeepSeek (platform.deepseek.com/api_keys, de pago).
- Tests (~9 nuevos, 3 modificados):
  - ⚠️ `test_un_proveedor_inventado_falla_claro` usa `"openrouter"` como inventado (test_util.py:135) → cambiar a `"cohere"` **en el mismo commit**.
  - Extender `test_cada_proveedor_tiene_su_modelo` y `test_cada_proveedor_lee_SU_variable_de_llave`.
  - Clase `TestProveedoresNuevos`: base_url correcta por proveedor + modelo default, `extra_body is None` para openai/deepseek, anthropic construye `ChatAnthropic` (monkeypatch de ANTHROPIC_API_KEY antes), anthropic sin llave → SystemExit con "ANTHROPIC_API_KEY", `reasoning_format` NO se envía fuera de Groq, openrouter+razonador → `extra_body == {"reasoning": {"exclude": True}}`.
  - `TestRequiereLlmKey`: anthropic pide ANTHROPIC_API_KEY, no otra.

## WP2 — HTML módulo 18b + espejos (subagente Opus 4.8, independiente de WP1)

Archivos: `curso_ejemplos/curso-langchain.html`, `curso_ejemplos/README.md` §5.

**Pre-tarea obligatoria**: WebFetch a páginas oficiales de precios (OpenAI, Anthropic, Gemini, DeepSeek, Groq, OpenRouter) y anotar la fecha de consulta. Ya verificados: Claude Opus 4.8 $5/$25 · 1M; Sonnet 5 $3/$15 (intro $2/$10 hasta 2026-08-31) · 1M; Haiku 4.5 $1/$5 · 200K. **Nada de precios de memoria.**

- Nav: insertar tras la línea de `#m18` (~L414): `<a href="#m18b"><span class="n">18b</span>Elegir modelo y proveedor</a>`. Sección `<section id="m18b">` tras el cierre de `#m18` (~L2964), antes de `#llmops`. El JS de progreso la cuenta solo (regex `/^m\d+b?$/`) — no tocar JS. **Sin DOCTYPE/head** (la Artifact tool inyecta la carcasa). Nav y sección en el mismo cambio.
- Esqueleto del módulo (estilo del curso: intro → `.box.def` → contenido → práctica → recap):
  1. h3 «Modelos de pago y open weights» — `.box.def` (dl: modelo de pago / open weights / licencia Llama vs Apache 2.0), `.box.warn` "open source ≠ gratis de servir", `.box.analogy` (partitura vs orquesta).
  2. h3 «Los cuatro caminos» — diagrama `.flow` de 4 steps: API de pago · open weights vía API hospedada (Groq/Together/OpenRouter/DeepSeek) · cloud gestionado (**Bedrock**: IAM, facturación AWS, VPC, datos no salen; snippet `ChatBedrockConverse` de langchain-aws marcado "solo lectura, requiere cuenta AWS"; mencionar Vertex/Azure Foundry) · on-premise (Ollama dev / vLLM producción, `.box.warn` de VRAM/hardware).
  3. h3 «Cuánto cuesta cada modelo (consultado: FECHA)» — `.tbl-wrap` con columnas: modelo | proveedor | tipo | $/1M entrada | $/1M salida | ventana | nota. Filas: GPT-5.x + gpt-5-mini, Claude Opus 4.8 / Sonnet 5 / Haiku 4.5, Gemini 2.5 Flash/Pro, deepseek-chat, Llama 3.3 70B en Groq, Qwen3 32B en Groq, y «tu máquina (Ollama)» con $0 + coste de hardware. `.box.warn`: los precios caducan, enlaces oficiales.
  4. h3 «Cómo decidir» — tabla criterio→camino (privacidad/regulación → on-prem o Bedrock; latencia → Groq; coste mínimo → DeepSeek/Gemini Flash; capacidad máxima → Opus/GPT-5; ventana 1M → Claude/Gemini), `figure.code` del `.env` ampliado, conexión con `crear_llm()` y `with_fallbacks` (Módulo 09): empezar de pago, abaratar después sin tocar código.
  5. `.box.practice` + `details.sol` + `.checkpoint` + `.recap.l5` (arch: `util.py`).
- Cheat sheet `#cheat` (~L3434): valores nuevos de `LLM_PROVIDER`, defaults alineados (gpt-5-mini, claude-haiku-4-5), enlace a #m18b.
- Glosario `#mapa`: open weights, licencia de modelo, AWS Bedrock, vLLM, on-premise, OpenRouter. Tabla #mapa + **README §5 (espejo obligatorio)**: fila «Elegir modelo y proveedor | util.py | 18b | test_util.py::TestProveedoresNuevos».
- Módulo 00 (~L560): mención de que hay más proveedores → Módulo 18b. FAQ: generalizar la fila «❌ Falta …_API_KEY»; fila nueva para 401/402 «insufficient credits» de proveedores de pago.

## WP3 — Verificación y publicación (sesión principal)

```bash
cd /Users/lbeto/proyectos/spec-sdd/studylangchainnivelinter/curso_ejemplos
uv run pytest -m offline -q                    # medir baseline ANTES de WP1
uv run python -m py_compile util.py
uv run pytest tests/test_util.py -m offline -q # baseline+~9, 0 fallos
uv run pytest -m offline -q                    # actualizar el conteo citado en README y CLAUDE.md
grep -c 'id="m18b"' curso-langchain.html       # == 1
grep -c 'DOCTYPE' curso-langchain.html         # == 0
# todo href="#X" del nav tiene su <section id="X">
```
- Comprobar espejos: #mapa ↔ README §5, cheat ↔ `MODELOS_POR_DEFECTO`, `.env.example` ↔ `_COMPATIBLES_OPENAI`.
- **Republicar el HTML al MISMO url del Artifact** (574784a7-…, favicon 🔗, título estable).
- Actualizar CLAUDE.md (tabla LLM_PROVIDER, conteo de tests, nota del módulo 18b).
- Commits convencionales separados: `feat(providers): …` y `docs(html): módulo 18b …`.

## Riesgos
1. Test del "proveedor inventado" usa `openrouter` → renombrar en el mismo commit.
2. `reasoning_format` fuera de Groq = 400 → test que lo blinda.
3. No tocar las 3 entradas viejas de `MODELOS_POR_DEFECTO` ni el special-case de google (33 tests existentes).
4. HTML sin DOCTYPE; nav+sección juntos; republicar al mismo url.
5. Precios solo de páginas oficiales, con fecha visible en la tabla.
