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

| # | Ejercicio | Tema | Ejemplo base | ¿Gasta cuota? |
|---|-----------|------|--------------|---------------|
| 04 | [Memoria con ventana](ejercicio_04_memoria.md) | Memoria | `04_memoria.py` | Sí |
| 05 | [Un cuarto molde Pydantic](ejercicio_05_estructurada.md) | Salida estructurada | `05_salida_estructurada.py` | Sí |
| 07 | [Dos tools nuevas](ejercicio_07_tools.md) | Herramientas + routing | `07_herramientas.py` · `08_routing.py` | Parcial |
| 11 | [Anti-alucinación del RAG](ejercicio_11_rag.md) | RAG | `11_rag.py` | Sí |
| 12 | [Predice el ranking](ejercicio_12_rerank.md) | Híbrido + re-ranking | `12_rag_hibrido_rerank.py` | **No** |
| 13 | [Escalar cuando el humano rechaza](ejercicio_13_hitl.md) | LangGraph + HITL | `13b_human_in_the_loop.py` | **No** |
| 🏆 | [Extender el proyecto final](ejercicio_proyecto.md) | Todo junto | `proyecto_final/` | Parcial |

**Si te quedaste sin cuota** (429), haz los ejercicios 12 y 13: son 100% offline
y, no por casualidad, son los dos que más enseñan sobre *ingeniería* de RAG y agentes.

## Cómo saber que lo hiciste bien

Cada ejercicio trae un **criterio de aceptación**: una condición verificable, no
una opinión. Varios se comprueban con un test que tú mismo escribes.

Y el proyecto entero sigue teniendo su red:

```bash
cd curso_ejemplos
uv run pytest -m offline      # nada de lo que toques debe romper esto
```
