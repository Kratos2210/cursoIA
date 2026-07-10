# 🔒 Soluciones

**Alto.** Si has llegado aquí sin haber intentado el ejercicio, date la vuelta.

El valor de un ejercicio no está en tener el código correcto. Está en el rato que
pasaste equivocándote: ahí es donde tu cabeza construye el modelo mental que
luego usarás para depurar a las 11 de la noche.

Leer una solución es como ver a alguien levantar pesas.

---

## Cuándo sí abrir un archivo de aquí

- Ya lo intentaste y **funciona**: compara tu enfoque con este. Las diferencias
  son lo interesante.
- Ya lo intentaste y **no funciona**, y las pistas del enunciado se agotaron.
- Quieres ver **qué pasa de verdad** al ejecutarlo (los de 12 y 13 imprimen
  el análisis completo).

## Los archivos

| Solución | Formato | ¿Se puede ejecutar? |
|----------|---------|---------------------|
| [`solucion_04_memoria.py`](solucion_04_memoria.py) | script | Sí (necesita llave) |
| [`solucion_05_estructurada.py`](solucion_05_estructurada.py) | script | Sí (la parte offline corre sin llave) |
| [`solucion_07_tools.py`](solucion_07_tools.py) | script | Sí (la parte offline corre sin llave) |
| [`solucion_11_rag.md`](solucion_11_rag.md) | análisis | No: las respuestas son razonamiento, no código |
| [`solucion_12_rerank.py`](solucion_12_rerank.py) | script | **Sí, 100% offline** |
| [`solucion_13_hitl.py`](solucion_13_hitl.py) | script | **Sí, 100% offline** |
| [`solucion_14_mcp.py`](solucion_14_mcp.py) | script | **Sí, 100% offline** |
| [`solucion_15_supervisor.py`](solucion_15_supervisor.py) | script | **Sí, 100% offline** |
| [`solucion_16_evaluacion.py`](solucion_16_evaluacion.py) | script | Sí (la métrica offline corre sin llave; el juez LLM es opcional) |
| [`solucion_16b_costes.py`](solucion_16b_costes.py) | script | **Sí, 100% offline** |
| [`solucion_17_api.py`](solucion_17_api.py) | script | **Sí, 100% offline** (con `uv sync --extra ui`) |

El ejercicio del proyecto final no trae solución: sus seis niveles son trabajo
real, y sus pistas ya te dicen dónde está la trampa de cada uno.

## Los dos que hay que ejecutar sí o sí

```bash
cd curso_ejemplos
uv run python ejercicios/soluciones/solucion_12_rerank.py
uv run python ejercicios/soluciones/solucion_13_hitl.py
```

No gastan cuota, y el de re-ranking imprime tres fallos reales del pipeline
(morfología, stopwords y empates silenciosos) que no verías de ninguna otra forma.

Y en la misma línea, los de temas avanzados también corren sin llave:

```bash
uv run python ejercicios/soluciones/solucion_14_mcp.py         # MCP: 3 tools por el protocolo
uv run python ejercicios/soluciones/solucion_15_supervisor.py  # enrutado de 3 especialistas
uv run python ejercicios/soluciones/solucion_16b_costes.py     # predice la factura
uv run python ejercicios/soluciones/solucion_17_api.py         # endpoint nuevo con TestClient
```
