# 🏆 Proyecto final — Asistente de Gobierno de Datos

Un asistente que **integra casi todo el curso** en una sola app ejecutable.
Y, además, es el ejemplo vivo del último tema: **cómo pasar de un archivo
gigante a un agente modular y testeable**.

> **¿Y la versión de producción?** Esto es el **prototipo didáctico** (CLI, estado
> en RAM). El salto a producción —FastAPI + SSE, pgvector, Redis, guardrails,
> tracing con Langfuse y un eval-gate que puede vetar un deploy— ya está
> materializado en **`proyecto_llmops`**, que reutiliza el `construir_agente()` de
> aquí. Si buscas el patrón "esto en serio", míralo allí.

## ¿Qué hace?
1. Lee la normativa (`normativa.txt`) y la indexa para **RAG**.
2. Expone 2 **herramientas** que el agente usa solo:
   - `buscar_normativa(pregunta)` → responde dudas citando la normativa.
   - `evaluar_regla_calidad(regla)` → evalúa una regla con **salida estructurada**
     (Pydantic) y guarda el resultado en un **log de auditoría**.
3. Un **agente con memoria** decide qué herramienta usar en cada turno.

## Conceptos que integra
| Concepto | Tema del curso |
|----------|----------------|
| RAG (vector store + retriever) | 11 |
| Herramientas `@tool` + routing | 07 · 08 |
| Salida estructurada (Pydantic) | 05 |
| Agente con memoria (LangGraph) | 10 |
| Auditoría / trazabilidad | Producción |

## 🧩 El mapa de módulos

Antes esto era **un solo `app.py` de 158 líneas**. Al importarlo, ya llamaba a
la API: era imposible testearlo. Ahora cada archivo tiene un trabajo:

| Archivo | Responsabilidad | ¿Llama a la API? |
|---------|-----------------|------------------|
| `config.py` | Rutas, modelos, constantes, validación del entorno | No |
| `rag.py` | Trocear la normativa, vectorizarla, recuperar contexto | Solo `construir_retriever()` |
| `audit.py` | El molde `HallazgoCalidad` y el log de auditoría | No |
| `tools.py` | Las 2 tools del agente (fábrica con inyección) | A través del modelo |
| `state.py` | El estado que viaja por el grafo | No |
| `persistence.py` | Dónde vive la memoria (RAM hoy, Postgres mañana) | No |
| `graph_builder.py` | Ensambla modelo + tools + memoria | Solo `construir_agente_real()` |
| `main.py` | Punto de entrada: la demo de 2 turnos | Sí |
| `app.py` | Atajo de compatibilidad (llama a `main.py`) | Sí |

**La regla que lo hace posible:** `construir_agente()` recibe el modelo, el
evaluador y el retriever **por parámetro** (inyección de dependencias). Por eso
un test puede pasarle un modelo falso y verificar el grafo entero sin gastar cuota.

## Cómo ejecutarlo
Desde la carpeta del proyecto (`studylangchainnivelinter`):

```bash
# 1) (una vez) instala dependencias y crea tu .env
uv sync
cp curso_ejemplos/.env.example curso_ejemplos/.env   # edita y pon tu llave

# 2) corre el proyecto
uv run python curso_ejemplos/proyecto_final/main.py
# (app.py hace exactamente lo mismo, se mantiene por compatibilidad)
```

## Qué verás
- Turno 1: responde cuántos años se conservan los registros (usa `buscar_normativa`).
- Turno 2: evalúa una regla de cifrado (usa `evaluar_regla_calidad`).
- Al final imprime el archivo `hallazgos_auditoria.log` que se acaba de generar.

## ✅ Cómo se verifica que funciona

```bash
uv run pytest curso_ejemplos/proyecto_final/tests -v
```

44 tests que corren **sin llave y sin cuota**, gracias a los dobles de prueba
de `tests/conftest.py`:

- `tests/test_rag.py` — el troceado de la normativa y el armado del contexto.
- `tests/test_audit.py` — el molde Pydantic y el log (que **nunca** se sobrescribe).
- `tests/test_agente.py` — el grafo completo con un **modelo falso** que recita
  un guion: pregunta → tool → auditoría → respuesta, más la memoria por `thread_id`.

## Ideas para ampliarlo
- Re-ranking del contexto (tema 12) — ver `ejercicios/ejercicio_12_rerank.md`.
- Aprobación humana antes de registrar (human-in-the-loop, tema 13b).
- Observabilidad con LangSmith (tema 16) — ver `16b_observabilidad_langsmith.py`.
- Cambiar `MemorySaver` por `SqliteSaver`: la receta está comentada en `persistence.py`.
- El ejercicio guiado completo: `ejercicios/ejercicio_proyecto.md`.
