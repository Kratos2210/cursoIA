# ADR-0003 — Usar pgvector (Postgres) como vector store del servicio

- **Estado:** aceptado
- **Fecha:** 2026-07-09
- **Decide:** Alberto Ruiz (autor del curso)
- **Reemplaza a:** [ADR-0001](../../../docs/adr/0001-vector-store.md) *para el proyecto LLMOps*
  (el `proyecto_final/` sigue con `InMemoryVectorStore`, y sigue estando bien)

## Contexto

El ADR-0001 eligió `InMemoryVectorStore` y escribió, con letra clara, **cuándo
habría que revisarlo**:

> 1. El corpus pasa de ~1.000 fragmentos, o
> 2. el tiempo de arranque supera los 5 segundos, o
> 3. **el proyecto se despliega con más de un proceso**.

El `proyecto_llmops/` cumple el tercer disparador desde su primera línea: es un
servicio FastAPI que se sirve con varios workers de uvicorn. Con
`InMemoryVectorStore`, **cada worker vectoriza la normativa entera al arrancar y
mantiene su propia copia en RAM**. Cuatro workers = cuatro índices idénticos,
cuatro veces la memoria, y cuatro tandas de embeddings en cada despliegue.

Restricciones nuevas que el prototipo no tenía:

- El índice debe **sobrevivir a un reinicio**. Un pod que se reinicia a las 3am
  no puede tardar minutos en re-vectorizar antes de aceptar tráfico.
- Los fragmentos llevan **metadatos** (`confidentiality`) y el RBAC filtra por
  ellos. El vector store debe poder almacenar y devolver metadatos estructurados.
- El equipo **ya opera Postgres**. Introducir un motor de datos nuevo significa
  otro backup, otra rotación de credenciales, otro runbook, otra página de
  guardia.

## Decisión

> Usaremos **pgvector sobre el Postgres que ya operamos**, vía
> `langchain-postgres`, como vector store del servicio.

Sigue aislado en un único sitio: `app/rag.py::construir_retriever_pgvector()`.
El resto del proyecto no sabe qué hay debajo — y `construir_retriever_memoria()`
mantiene el camino sin Docker para los tests y para quien solo quiera leer.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **pgvector** | Un motor que el equipo ya opera (backup, HA, permisos); transaccional; los metadatos son columnas JSONB indexables; el filtro del RBAC se puede empujar al `WHERE` | Más lento que un índice vectorial dedicado a partir de ~1M de vectores; el tuning de HNSW en Postgres es más artesanal | ✅ **Elegida** |
| **Chroma** | Sencillísimo; persiste en disco | Un proceso más que operar, o un directorio compartido entre workers (que es exactamente el problema que veníamos a resolver); su historia de versiones ha roto formatos de índice | Resuelve la persistencia, no la concurrencia |
| **Qdrant / Weaviate** | Rendimiento excelente; filtros por metadatos de primera clase; pensados para esto | **Un sistema de datos entero, nuevo**: backup, monitorización, actualizaciones, credenciales, un runbook más | Nuestro corpus es una normativa: miles de fragmentos, no millones. Pagaríamos toda la operación sin usar el rendimiento |
| **Pinecone** (gestionado) | Cero operación | Los datos salen de la infraestructura de la financiera | **Inaceptable**: es normativa interna con anexos confidenciales |
| Seguir con **InMemory** | Cero cambios | N workers = N índices; se pierde en cada reinicio | Es justo el disparador que el ADR-0001 anticipó |

## Consecuencias

**Positivas**
- El índice se construye **una vez** y todos los workers lo comparten.
- Un reinicio no cuesta ni un embedding: el arranque pasa de segundos a milisegundos.
- Los metadatos de confidencialidad viven en JSONB. Hoy filtramos en Python
  (`guardrails/rbac.py`); mañana ese filtro puede bajar al `WHERE` de la query
  y dejar de traer a la aplicación documentos que el rol no puede ver.
- El backup del vector store es el backup de Postgres, que ya existe.

**Negativas** (las aceptamos a sabiendas)
- **Ya no se puede correr el servicio sin Docker.** Es la libertad que perdemos.
  La mitigamos con la degradación graceful de `construir_agente_real()`: si
  Postgres no responde, cae a memoria. Arranca, pero no es producción.
- Postgres pasa a ser una **dependencia de arranque**: si está caído, el RAG no
  funciona. Antes el fallo era imposible porque no había nada que estuviera caído.
- pgvector no es el motor vectorial más rápido del mercado. A partir de ~1M de
  vectores, la latencia de búsqueda se notará frente a Qdrant.
- `add_documents()` **no es idempotente**: correr la indexación dos veces duplica
  los fragmentos. Hoy no muerde porque indexamos al arrancar y el corpus es
  pequeño; en cuanto haya reindexado incremental, hará falta un hash por documento.

**Cuándo revisar esta decisión**

En cuanto se cumpla **cualquiera** de estas:
1. El corpus supera **1 millón de vectores**, o
2. la latencia p95 de la búsqueda vectorial pasa de **100 ms**, o
3. hace falta búsqueda híbrida (BM25 + vectorial) de primera clase — pgvector la
   hace, pero a mano; Qdrant y Weaviate la traen puesta, y el módulo 12 del curso
   ya enseña por qué la híbrida gana a la puramente vectorial.

El camino de salida es Qdrant, y lo que cambia es **una función**.
