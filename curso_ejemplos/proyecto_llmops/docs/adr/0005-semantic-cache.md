# ADR-0005 — Caché semántico con aislamiento por rol y umbral alto

- **Estado:** aceptado
- **Fecha:** 2026-07-09
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

En un asistente de normativa, las preguntas se repiten muchísimo. Diez analistas
distintos preguntan, con diez redacciones distintas, cuántos años se conservan
los registros. Cada una de esas preguntas cuesta:

- una llamada al modelo (dinero), y
- entre 1 y 4 segundos de espera (UX).

Un caché exacto (`dict[pregunta] -> respuesta`) apenas acierta: `"¿hay que
cifrar los datos?"` y `"¿los datos se cifran?"` son claves distintas. Un **caché
semántico** compara los *vectores* de las preguntas y acierta en ambas.

La tentación es presentarlo como una optimización inocente. No lo es. Tiene dos
formas de hacer daño, y las dos son peores que el problema que resuelve:

1. **Un falso positivo no es lentitud: es una respuesta incorrecta.** Con un
   umbral bajo, `"¿debo cifrar los datos?"` y `"¿debo cifrar los backups?"` se
   parecen mucho, y el usuario recibe con total aplomo la respuesta a una
   pregunta que no hizo.

2. **El caché es un canal lateral que se salta el RBAC.** Si un `compliance`
   pregunta por las claves maestras y su respuesta se cachea sin más, el
   siguiente `analyst` que pregunte algo parecido recibe material restringido:
   sin pasar por el retriever, sin pasar por `filtrar_por_rol`. Toda la
   gobernanza del proyecto, esquivada por una optimización de coste.

## Decisión

> Usaremos un caché semántico con **backend Redis**, **umbral de coseno 0.92** y
> **una clave por rol** (`gobdata:cache:<rol>`), con TTL de 24 h y degradación a
> memoria si Redis no responde.

Vive en `cache/semantic_cache.py` (la lógica) y `cache/cache_backends.py`
(dónde se guarda). El filtro por rol se aplica **en el backend**, no en una capa
de arriba, para que ninguna ruta de código pueda saltárselo.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Semántico, Redis, por rol, umbral 0.92** | Acierta con reformulaciones; compartido entre workers; el aislamiento de roles es estructural | Búsqueda lineal en el cliente; un embedding por pregunta | ✅ **Elegida** |
| Caché **exacto** (hash de la pregunta) | Trivial; cero falsos positivos; cero riesgo | Tasa de aciertos ridícula: cualquier reformulación es un MISS | Resuelve el caso que casi nunca ocurre |
| Semántico **sin rol** | Más aciertos (todos los roles comparten) | **Fuga de datos restringidos.** Ver el punto 2 del contexto | Descartada por seguridad. Más aciertos a costa de saltarse el RBAC no es un intercambio: es un incidente |
| Semántico con **umbral 0.80** | Muchos más aciertos | Confunde preguntas vecinas y responde a la que no se hizo | Un MISS caro es infinitamente mejor que un HIT equivocado |
| Índice vectorial en Redis (**RediSearch/HNSW**) | Búsqueda O(log n); escala a millones | Otro módulo de Redis que operar; complejidad que nuestro volumen no justifica | Con miles de entradas, la búsqueda lineal es ruido frente a la latencia del LLM |
| **Sin caché** | Cero riesgo, cero complejidad | Se paga cada pregunta repetida, y son la mayoría | El ahorro es real y medible (`/metrics` → `cache_tasa_aciertos`) |

## Consecuencias

**Positivas**
- Un HIT cuesta **$0** y responde en milisegundos: es la única optimización que
  mejora coste y latencia a la vez.
- El aislamiento por rol está en la clave de Redis: es infraestructura, no un
  `if` que alguien puede borrar en un refactor.
- El TTL de 24 h acota el daño de una respuesta obsoleta cuando la normativa cambia.
- `tasa_aciertos` se expone en `/metrics`: si el caché no sirve, se ve.

**Negativas** (las aceptamos a sabiendas)
- **El umbral 0.92 es un número elegido a ojo.** Lo honesto es calibrarlo con
  tráfico real: registrar la `similitud` de cada HIT y comprobar a mano si las
  parejas eran de verdad la misma pregunta. Hasta que eso se haga, es una
  conjetura razonable, no un dato.
- La búsqueda es **lineal en el cliente**: trae todas las entradas del rol y
  compara vector a vector. Con 500 entradas es gratis; con 500.000 es un desastre.
- Un caché por rol **fragmenta los aciertos**: tres roles, tres cachés, tres
  veces menos reutilización. Es el precio del aislamiento, y se paga con gusto.
- La respuesta cacheada **congela el estado de la normativa** en el momento en
  que se generó. El TTL lo acota; no lo elimina. Un cambio urgente de normativa
  exige `FLUSHDB` (está en el runbook).
- Cachear **la respuesta saneada, no la cruda**, es obligatorio: si se cachea el
  texto crudo, el guardrail de salida se ejecuta una vez y se esquiva para
  siempre en los HITs siguientes. Hay un test que lo fija
  (`test_smoke_api.py::test_se_cachea_la_respuesta_saneada`).

**Cuándo revisar esta decisión**

1. Cuando el caché supere **~50.000 entradas** por rol → pasar a RediSearch/HNSW.
2. Cuando haya tráfico real suficiente para **calibrar el umbral con datos**
   (medir la precisión de los HITs) en vez de con intuición.
3. Si aparece un cuarto rol y la fragmentación deja la tasa de aciertos por
   debajo del 10% → replantear si el caché compensa su complejidad.
