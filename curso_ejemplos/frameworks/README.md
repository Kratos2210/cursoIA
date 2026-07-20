# frameworks/ — el mismo curso con otras pieles (LlamaIndex y CrewAI)

El m26 muestra el mapa del ecosistema con snippets ilustrativos; este anexo los
vuelve **ejecutables**. La lección no es "framework X es mejor": es reconocer la
MISMA idea del curso con otra API.

| Script | Qué demuestra | Espejo en el curso |
|---|---|---|
| `rag_llamaindex.py` | el RAG de m11/m12 (cargar → indexar → consultar) con LlamaIndex, sobre el mismo `datos_rag.txt` | m11, m12, m26 |
| `crew_crewai.py` | el patrón supervisor de m15, descrito como ROLES y TAREAS en vez de grafo explícito | m15, m26 |

## Cómo se corre

```bash
uv run --extra llamaindex python frameworks/rag_llamaindex.py
uv run --extra crewai    python frameworks/crew_crewai.py
```

Ambos necesitan una API de LLM con cuota (el endpoint OpenAI-compatible del
`.env`: Groq/OpenRouter/Ollama). Los ids de modelo se verifican en la web del
proveedor, nunca de memoria.

## Por qué está fuera del gate offline

Decidido en [ADR-0006](../docs/adr/0006-frameworks-alternativos-fuera-del-gate.md):
son extras opcionales (`uv sync --extra llamaindex` / `--extra crewai`), no se
testean en la CI y requieren cuota. La versión testeada y offline de estos
conceptos vive en los módulos del curso (m11/m12/m15).
