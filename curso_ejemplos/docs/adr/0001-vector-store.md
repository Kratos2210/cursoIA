# ADR-0001 — Usar `InMemoryVectorStore` para el RAG del curso

- **Estado:** aceptado
- **Fecha:** 2026-07-09
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El proyecto final indexa `normativa.txt`: **5 reglas, ~6 fragmentos, menos de
2 KB de texto**. Sobre eso hace RAG para responder dudas de gobierno de datos.

Restricciones reales de este proyecto:

- Es un **curso**. El estudiante debe poder correr el ejemplo con un solo
  comando, sin levantar un Docker ni crear una cuenta en ningún sitio.
- La normativa **no cambia** durante una ejecución. Se indexa al arrancar y
  se consulta unas pocas veces.
- Los tests de la CI **no deben llamar a la API** ni depender de un servicio externo.
- El corpus es tan pequeño que cualquier estructura de índice (HNSW, IVF) sería
  más lenta de construir que una búsqueda por fuerza bruta de 6 vectores.

## Decisión

> Usaremos `InMemoryVectorStore` de `langchain-core`, reconstruyendo el índice
> en cada arranque del proceso.

Está aislado en un único sitio: `proyecto_final/rag.py::construir_retriever()`.
Ningún otro módulo sabe qué vector store hay debajo.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **InMemoryVectorStore** | Cero instalación; ya viene en `langchain-core`; el índice se reconstruye en <1 s | Se pierde al reiniciar; no escala más allá de unos miles de fragmentos | ✅ **Elegida** |
| **Chroma** | Persiste en disco; sigue siendo un solo proceso; API casi idéntica | Una dependencia más (~40 MB con sus binarios); un directorio de estado que se corrompe y confunde al alumno | El corpus es de 6 fragmentos: persistir cuesta más de lo que ahorra |
| **pgvector (Postgres)** | Lo de producción: transaccional, concurrente, con backup | Exige levantar Postgres; el alumno pelea con Docker antes de aprender RAG | Fuera del alcance de un curso |
| **FAISS** | Muy rápido en corpus grandes | Compilación nativa; en Mac Intel da problemas de instalación | Optimiza un cuello de botella que no tenemos |

## Consecuencias

**Positivas**
- `uv run python proyecto_final/main.py` funciona sin más pasos.
- `rag.trocear()` y `rag.contexto()` quedan puros y se testean sin API
  (`proyecto_final/tests/test_rag.py`).
- Cambiar de vector store toca **una función**, no el proyecto entero.

**Negativas** (las aceptamos a sabiendas)
- Cada arranque **re-vectoriza la normativa**: son 6 llamadas al modelo de
  embeddings. Con `normativa.txt` es gratis; con un PDF de 200 páginas serían
  minutos de espera y cuota quemada en cada reinicio.
- La memoria del proceso crece con el corpus. A partir de ~10.000 fragmentos,
  cargar todo en RAM deja de ser razonable.
- No hay búsqueda concurrente entre procesos: cada worker tendría su propia copia.

**Cuándo revisar esta decisión**

En cuanto se cumpla **cualquiera** de estas tres:
1. El corpus pasa de ~1.000 fragmentos, o
2. el tiempo de arranque supera los 5 segundos, o
3. el proyecto se despliega con más de un proceso (un servidor web, el tema 17).

En ese momento, el primer paso es Chroma con persistencia en disco —
`rag.construir_retriever()` es lo único que cambia.
