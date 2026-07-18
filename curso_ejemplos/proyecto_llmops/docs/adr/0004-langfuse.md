# ADR-0004 — Langfuse self-hosted (v2) para la observabilidad

- **Estado:** aceptado
- **Fecha:** 2026-07-09
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El curso ya usa **LangSmith** en el módulo 16b (`16b_observabilidad_langsmith.py`),
y funciona muy bien: un `LANGSMITH_API_KEY` y todas las llamadas de LangChain
quedan trazadas sin instrumentar nada.

El `proyecto_llmops/` tiene una restricción que el curso no tenía: es el
asistente de gobierno de datos de una **financiera peruana**. Las trazas de un
sistema RAG contienen, por construcción:

- la pregunta literal del usuario (que puede llevar un DNI, un RUC, un nombre),
- los **fragmentos de normativa interna** recuperados, incluidos los anexos
  confidenciales cuando pregunta un rol `compliance`,
- la respuesta completa del modelo.

Es decir: **la traza es una copia de los datos sensibles del sistema**. Mandarla
a un SaaS es exportar el corpus, pieza a pieza, a la infraestructura de un
tercero — y la Regla 4 de la propia normativa exige mínimo privilegio y log de
auditoría sobre esos datos.

A esto se añade una restricción didáctica: el alumno debe poder ver trazas
**sin crear una cuenta en ningún sitio**.

## Decisión

> Usaremos **Langfuse v2, self-hosted** vía `docker-compose`, con degradación a
> **no-op** cuando no haya llaves configuradas.

Toda la integración vive en `observability/tracing.py`. El resto del código
llama a `tracing.callbacks()` y a `@tracing.observar(...)` sin saber si hay
alguien escuchando al otro lado.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Langfuse v2 self-hosted** | Los datos no salen de la red de la financiera; open source; un solo Postgres; el alumno lo levanta con un `docker compose up` | Hay que operarlo (backup, actualizaciones); su UI va por detrás de LangSmith | ✅ **Elegida** |
| **Langfuse v3 self-hosted** | La versión actual; más escalable | Exige **ClickHouse + MinIO + Redis + un worker**: 6 contenedores y ~8 GB de RAM. Un alumno con un portátil de 8 GB no puede levantarlo | Desproporcionado para el corpus y para un curso. Por eso el `pyproject.toml` pinea `langfuse>=2,<3` |
| **LangSmith** (SaaS) | Lo mejor integrado con LangChain; cero operación; es lo que ya usa el módulo 16b | Las trazas —normativa confidencial incluida— viajan a un tercero. Requiere cuenta | **El motivo de este ADR.** Sigue siendo la opción correcta para el curso, no para este servicio |
| **OpenTelemetry + Grafana/Tempo** | El estándar de la industria; ya lo tendría un equipo de plataforma | No entiende de LLMs: hay que construir a mano el concepto de "prompt", "tokens", "coste", y la evaluación | Reconstruiríamos Langfuse encima de OTel |
| **Solo logs estructurados** | Cero dependencias | Una llamada a un agente es un **árbol** (agente → tool → RAG → modelo → agente). Un log plano no se abre por ramas | No sirve para depurar un agente |

## Consecuencias

**Positivas**
- Ninguna normativa confidencial sale de la infraestructura.
- El alumno ve trazas reales en `http://localhost:3000` sin registrarse en nada.
- La instrumentación es **opcional**: sin llaves, `observar()` devuelve la
  función intacta y `callbacks()` devuelve `[]`. Los 322 tests offline corren
  sin Langfuse levantado.

**Negativas** (las aceptamos a sabiendas)
- **Operamos un servicio más.** Langfuse v2 se queda sin soporte upstream:
  actualizar a la v3 será un proyecto, no un `docker compose pull`.
- La UI de Langfuse v2 tiene menos funciones que LangSmith (menos comparación de
  datasets, peor filtrado).
- El `except Exception` de `tracing.py` esconde los fallos del propio tracing. Es
  deliberado —un observador que tumba lo observado no es observabilidad— pero
  significa que **si Langfuse deja de recibir trazas, nadie se entera**. La única
  defensa es mirar la UI de vez en cuando: hay que ponerlo en el runbook.
- Perdemos la integración de un clic entre LangSmith y los datasets de evaluación.

**Cuándo revisar esta decisión**

1. Si la financiera aprueba un procesador de datos externo con contrato de
   confidencialidad → LangSmith vuelve a la mesa y ahorra la operación.
2. Si el volumen de trazas hace sudar al Postgres de Langfuse v2 (el disparador
   real de la v3 es del orden de millones de spans al mes).
3. Si el equipo de plataforma estandariza OpenTelemetry: entonces la pregunta
   pasa a ser cómo exportar los spans de LLM a la infraestructura común, no qué
   herramienta usar.
