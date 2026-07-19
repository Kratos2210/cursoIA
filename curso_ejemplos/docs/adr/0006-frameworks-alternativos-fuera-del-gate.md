# ADR-0006 — LlamaIndex y CrewAI: de "sabor ilustrativo" a ejecutable, fuera del gate

- **Estado:** aceptado
- **Fecha:** 2026-07-17
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El m26 (mapa del ecosistema) muestra el **"sabor"** de otros frameworks (CrewAI,
Pydantic-AI, LlamaIndex) con snippets **ilustrativos que no se ejecutan**. El
benchmark de mercado (perfil multi-framework) pedía que el alumno **corra** al
menos uno alternativo, no solo lo lea: reconocer "la misma idea con otra piel" se
fija mucho mejor ejecutando.

La tensión con la constitución offline-first es real: LlamaIndex y CrewAI son
**ecosistemas propios** (no LangChain), arrastran **muchas dependencias**
transitivas y necesitan **una API de LLM con cuota** para dar un resultado. No
encajan en `tests/` ni en `-m offline`.

## Decisión

> Los snippets ilustrativos del m26 pasan a **ejecutables** en `frameworks/`:
> `rag_llamaindex.py` (el mismo RAG del m11 sobre `datos_rag.txt`) y
> `crew_crewai.py` (roles investigador→redactor, el m15 a alto nivel). Viven en
> **extras opcionales** (`uv sync --extra llamaindex` / `--extra crewai`),
> **fuera** del gate offline: la CI corre `uv sync --extra dev`, no los instala
> ni los testea. Un **módulo de lectura** (m32) los enmarca. Fila "—" en el #mapa.

Ambos se apuntan al **mismo endpoint OpenAI-compatible del `.env`** que ya usa el
curso, para no introducir otro proveedor; LlamaIndex usa embeddings **fastembed
locales** (los del curso). Los ids de modelo son **placeholders verificables**,
no canónicos.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Ejecutable en extras, fuera del gate** | El alumno corre otro framework de verdad; cero impacto en deps/CI del resto | No se testea; necesita cuota | ✅ **Elegida** |
| Dejarlo solo ilustrativo (como estaba) | Cero trabajo | No se ejecuta; el gap "correr un alternativo" sigue | Ya era el estado; no cierra el gap |
| Meter LlamaIndex/CrewAI en el núcleo y testearlo | Coherente con el resto | +decenas de deps y una API con cuota en la CI | Rompe la constitución para todos |

## Consecuencias

**Positivas**
- El alumno **ejecuta** LlamaIndex y CrewAI y comprueba en vivo el tradeoff del
  m26 ("más alto nivel = menos control"), sin contaminar el entorno base.
- Refuerza la tesis del curso: DI, tests y observabilidad son **tuyos**, no del
  framework — el núcleo sigue en LangChain/LangGraph, testeado y offline.

**Negativas**
- Los dos scripts **no están cubiertos por tests** y dependen de APIs externas:
  pueden desfasarse si LlamaIndex/CrewAI cambian su API o el id de modelo. Se
  marcan como lectura + ejecución-si-tienes-cuota, con ids verificables.
- Suma dos extras más a `pyproject.toml`; se documenta aquí para que la lista de
  "material fuera del gate" ([ADR-0003](0003-notebook-lora-fuera-del-gate.md),
  [ADR-0004](0004-canal-whatsapp-fuera-del-gate.md)) quede trazable.

**Cuándo revisar**

Si el curso adoptara un proveedor de LLM local sin cuota (Ollama por defecto en la
CI), estos scripts podrían ganar un smoke test que corra una query mínima.
