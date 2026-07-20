# 🏋️ Ejercicios del curso

Leer código no enseña a escribirlo. Estos ejercicios te obligan a **modificar**
los ejemplos y a **predecir** qué va a pasar antes de ejecutar.

## Cómo trabajarlos

1. Abre el ejercicio y lee **solo el enunciado**.
2. Inténtalo. Si te atascas, abre **la Pista 1**. Solo la 1.
3. Si sigues atascado, la Pista 2. Y así.
4. Cuando funcione, compara con la solución en `soluciones/`.

> Las pistas están plegadas (`<details>`). Ábrelas de una en una: **cada pista
> que no necesitas es aprendizaje que te regalas**.

**Nunca copies la solución antes de intentarlo.** El valor no está en tener el
código correcto: está en el rato que pasaste equivocándote.

## Índice

La columna «¿Gasta cuota?» se refiere al proveedor que tengas activo — con
`LLM_PROVIDER=groq` gastas cupo de Groq, no de Gemini (ver abajo).

| # | Ejercicio | Tema | Ejemplo base | ¿Gasta cuota? | ¿Sirve Groq? |
|---|-----------|------|--------------|---------------|--------------|
| 04 | [Memoria con ventana](ejercicio_04_memoria.md) | Memoria | `04_memoria.py` | Sí | ✅ |
| 05 | [Un cuarto molde Pydantic](ejercicio_05_estructurada.md) | Salida estructurada | `05_salida_estructurada.py` | Sí | ✅ |
| 07 | [Dos tools nuevas](ejercicio_07_tools.md) | Herramientas + routing | `07_herramientas.py` · `08_routing.py` | Parcial | ✅ |
| 11 | [Anti-alucinación del RAG](ejercicio_11_rag.md) | RAG | `11_rag.py` | Sí | ⚠️ chat sí, embeddings no |
| 12 | [Predice el ranking](ejercicio_12_rerank.md) | Híbrido + re-ranking | `12_rag_hibrido_rerank.py` | **No** | — |
| 13 | [Escalar cuando el humano rechaza](ejercicio_13_hitl.md) | LangGraph + HITL | `13b_human_in_the_loop.py` | **No** | — |
| 14 | [Una tercera tool MCP](ejercicio_14_mcp.md) | MCP servidor + cliente | `14_mcp_servidor_cliente.py` | **No** | — |
| 15 | [Un tercer especialista](ejercicio_15_supervisor.md) | Patrón supervisor | `15_supervisor_multiagente.py` | **No** | — |
| 16 | [Casos trampa en el dataset](ejercicio_16_evaluacion.md) | Evaluación | `16_evaluacion.py` | Parcial | ✅ chat (juez) |
| 16b | [Predice la factura](ejercicio_16b_costes.md) | Observabilidad + coste | `16b_observabilidad_langsmith.py` | **No** | — |
| 17 | [Un endpoint nuevo, sin API](ejercicio_17_api.md) | Servir el agente | `17_servidor_agente.py` | **No** | — |
| 20 | [Cuándo el multi-query NO ayuda](ejercicio_20_rag_avanzado.md) | RAG avanzado | `20_rag_avanzado.py` | **No** | — |
| 22 | [El mensaje deja de ser un string](ejercicio_22_multimodal.md) | Multimodal + voz | `22_multimodal.py` · `22b_voz.py` | **No** | — |
| 23 | [Rodea tu propio detector](ejercicio_23_seguridad.md) | Seguridad | `23_seguridad.py` | **No** | — |
| 27 | [Qué significan de verdad tus parámetros](ejercicio_27_fundamentos.md) | Fundamentos del LLM | `27_fundamentos_llm.py` | **No** | — |
| 28 | [Mide la sospecha, no la confíes](ejercicio_28_alucinaciones.md) | Alucinaciones | `28_alucinaciones.py` | **No** | — |
| 29 | [El dato sucio y el eval que no perdona](ejercicio_29_retail.md) | Caso real retail | `29_caso_retail.py` | **No** | — |
| 🏆 | [Extender el proyecto final](ejercicio_proyecto.md) | Todo junto | `proyecto_final/` | Parcial | ⚠️ chat sí, embeddings no |

## ⚡ Si la cuota de Gemini se te agota (429)

Te va a pasar: el plan gratuito de Gemini da para muy poco, y estos ejercicios
llaman al modelo varias veces cada uno. Tienes dos salidas.

**Salida 1 — Cambia a Groq.** Nada en el curso instancia el modelo a mano:
todo llama a `util.crear_llm()`, que lee el proveedor del `.env`. Consigue una
llave gratis en [console.groq.com/keys](https://console.groq.com/keys) y añade dos líneas:

```bash
# curso_ejemplos/.env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_tu_llave_aqui
```

Ya está. Los ejercicios —y todos los ejemplos del curso— pasan a usar
**`qwen/qwen3-32b`**, con un cupo mucho más generoso. No hay que tocar ni una
línea de código.

> ⭐ **Por qué basta con eso.** Groq, Ollama, Together y OpenAI hablan todos el
> *mismo* dialecto: la API de OpenAI. Por eso una sola clase (`ChatOpenAI` con
> otra `base_url`) los cubre a los cuatro. Gemini no lo habla, y por eso tiene su
> propia rama en `crear_llm()`. No es que LangChain tenga un adaptador por
> proveedor: es que el mercado convergió en un protocolo.

**El único límite: Groq no ofrece embeddings.** El ejercicio 11 (RAG) los
necesita, así que el chat irá por Groq pero vectorizar seguiría gastando
`GOOGLE_API_KEY`. La salida sin cuota es calcularlos en tu máquina:

```bash
uv sync --extra emb                 # fastembed (ONNX, sin PyTorch)
# y en el .env:
EMBEDDINGS_PROVIDER=fastembed
```

Y de paso aprendes algo que muerde en producción: cambiar de modelo de embeddings
**no** es cambiar de proveedor de chat. **Invalida el índice entero**, porque los
vectores viejos y los nuevos viven en espacios distintos. Hay que reindexar.

**Salida 2 — Haz los ejercicios offline.** Los ejercicios 12, 13, 14, 15, 16b,
17, 20, 22, 23, 27, 28 y 29 no llaman a ningún modelo y, no por casualidad, son
los que más enseñan sobre *ingeniería* de RAG, agentes, MCP, multimodal,
alucinaciones, coste y despliegue. Un 429 no es excusa: es una invitación a
practicar justo lo que importa.

## Cómo saber que lo hiciste bien

Cada ejercicio trae un **criterio de aceptación**: una condición verificable, no
una opinión. Varios se comprueban con un test que tú mismo escribes.

Y el proyecto entero sigue teniendo su red:

```bash
cd curso_ejemplos
uv run pytest -m offline      # nada de lo que toques debe romper esto
```
