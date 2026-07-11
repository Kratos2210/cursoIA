# ADR-0006 — A/B de prompts (pegajoso por hash) y feedback 👍/👎 en memoria

- **Estado:** aceptado
- **Fecha:** 2026-07-10
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

Tenemos dos redacciones del prompt del sistema: `agente_gobdata` (larga, la
actual) y `agente_gobdata_conciso` (breve). ¿Cuál responde mejor? "Mejor" no lo
decide el gusto de quien escribió el prompt: lo decide el usuario. Para medirlo
hacen falta dos piezas que encajan:

1. **Repartir** a los usuarios entre las dos variantes (A/B).
2. **Recoger** su satisfacción (👍/👎) y agregarla **por variante**.

Sin las dos, no hay experimento. Con solo la primera, repartes a ciegas; con
solo la segunda, no sabes a qué variante atribuir el voto.

El reparto tiene una trampa sutil. Si a cada request se le sortea una variante,
el mismo usuario ve A, luego B, luego A en la misma conversación: percibe un
asistente que cambia de personalidad, y —peor— su voto ya no se puede atribuir a
una variante concreta. **El reparto tiene que ser pegajoso**: la variante debe
ser una función del `thread_id`, no un sorteo por request.

## Decisión

> **Bucketing determinista y pegajoso por hash.** La variante se calcula como
> `sha256(thread_id) % nº_variantes`. El mismo `thread_id` cae siempre en la
> misma variante. Vive en `prompts/experimentos.py` (`asignar_variante` y la
> dataclass `Experimento`).
>
> **Feedback en un colector en memoria**, `observability/feedback.py`
> (`ColectorFeedback`), inyectado en `crear_app(..., feedback=None)` igual que
> las métricas. Se expone por **`POST /feedback`** (registra un voto) y
> **`GET /feedback`** (`tasa_aprobacion` por variante). El evento SSE `fin` de
> `POST /chat` anuncia la `variante`, para que el cliente la devuelva en su voto.

**Por qué hash y no un contador ni `random`.** El hash da, a la vez:

- **Reproducible entre procesos** sin coordinar nada. Un contador `0,1,0,1…`
  exigiría un estado compartido (Redis, un lock) entre los workers de uvicorn; el
  hash lo recalcula cada worker por su cuenta y todos coinciden.
- **Sin estado**: no hay que guardar "a quién le tocó qué".
- **Uniforme**: sha256 esparce las claves parejo, así el reparto queda equilibrado.

Se usa `hashlib.sha256`, no el `hash()` de Python: este último está aleatorizado
por proceso (`PYTHONHASHSEED`), así que dos workers asignarían al mismo usuario
variantes distintas —rompiendo la pegajosidad justo entre procesos, que es donde
más duele.

## Alcance de esta entrega (y lo que queda para después)

Aquí el `thread_id` **fija la variante** y el feedback **se agrega por variante**:
el lazo A/B de medición está cerrado. Lo que aún **no** se hace es re-cablear el
agente para que use el YAML de la variante asignada (hoy ambas ramas usan el
prompt por defecto). Ese es el paso siguiente, mecánico: cargar el prompt cuyo
nombre es la variante. Se deja fuera para no acoplar esta feature al constructor
del agente real, que necesita Postgres y embeddings.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Hash del thread_id, pegajoso** | Reproducible sin coordinar workers; sin estado; uniforme | Cambiar el reparto (p. ej. 90/10) pide algo más que un módulo | ✅ **Elegida** |
| Sorteo por request (`random`) | Trivial | No es pegajoso: el usuario ve A y B alternándose y el voto no se atribuye | Rompe el experimento |
| Contador global `0,1,0,1…` | Reparto exacto | Exige estado compartido entre workers (Redis/lock) | Coordinación que el hash evita |
| `hash()` de Python | Es stdlib y rápido | Aleatorizado por proceso (`PYTHONHASHSEED`): workers discrepan | Rompe la pegajosidad entre procesos |
| Feedback directo a una tabla/Langfuse | Persiste; permite significancia estadística | Infra (DB/servicio) que el curso no monta | Es el destino de producción, no el mínimo ejecutable |

## Consecuencias

**Positivas**
- El reparto es pegajoso y reproducible **sin coordinar nada** entre workers.
- `asignar_variante` es una función **pura**: se testea sin levantar la API.
- El feedback vive en **su propio endpoint**: no ensucia el `resumen()` de
  `/metrics` (que tiene tests fijando sus claves). Coste/latencia y satisfacción
  son ejes distintos y se miden por separado.
- Todo es **aditivo**: el evento `fin` gana una clave `variante` sin quitar
  `cache_hit` ni `similitud`; los smoke tests existentes siguen en verde.

**Negativas / limitaciones** (las decimos en voz alta)
- **El feedback vive en memoria, por proceso.** Con varios workers, cada uno
  cuenta los suyos y ninguno ve el total —el mismo aviso que `ColectorMetricas`.
  Al reiniciar el proceso, los votos se pierden. En producción el voto va a una
  **tabla** (o a **Langfuse**), donde persiste entre despliegues y se agrega
  entre procesos.
- **Tres votos no deciden nada.** La `tasa_aprobacion` con pocos votos es ruido:
  una variante puede ir "ganando" 3-0 por azar. El ganador de un A/B se decide
  con **significancia estadística** (tamaño de muestra suficiente, un test de
  proporciones), no comparando dos fracciones pequeñas. Este colector da la señal
  cruda; la decisión estadística es de la capa de análisis, no de este proceso.
- **El agente aún no usa el prompt de la variante** (ver "Alcance"): hoy medimos
  la infraestructura del A/B, no todavía el efecto real de cambiar el prompt.
- El reparto es fijo al 50/50 por diseño del hash; un *canary* 95/5 pediría
  particionar el espacio del hash, no solo un módulo.

**Cuándo revisar esta decisión**
1. Cuando haya que **persistir** los votos entre reinicios o agregarlos entre
   workers → mover `ColectorFeedback` a una tabla o a Langfuse.
2. Cuando se quiera **decidir un ganador** → añadir el test de significancia y no
   fiarse de la tasa cruda.
3. Cuando se re-cablee el agente al prompt de la variante → cerrar el lazo A/B
   completo (medir el efecto del prompt, no solo repartir).
