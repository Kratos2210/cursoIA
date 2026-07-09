# 🏆 Ejercicio final — Extender el asistente de Gobierno de Datos

**Base:** `proyecto_final/` · **Gasta cuota:** algunas partes sí, otras no

Este no es un ejercicio: es una **lista de trabajo real**. Cada parte es
independiente. Haz las que te interesen, en el orden que quieras.

> Antes de empezar: `uv run pytest proyecto_final/tests -v` debe estar en verde.
> Es tu red. Después de **cada** cambio, vuelve a lanzarlo.

---

## Nivel 1 — Una tercera tool (offline testeable)

Añade a `tools.py` una tool `listar_reglas()` que devuelva los títulos de todas
las reglas de la normativa, sin llamar al modelo.

**Criterio:** un test en `tests/test_agente.py` verifica que devuelve las 5
reglas. El agente la elige cuando le preguntas «¿qué reglas hay?».

<details>
<summary>Pista</summary>

`rag.trocear(rag.leer_normativa())` te da los fragmentos. El título de cada
regla es la primera línea de cada fragmento (`fragmento.page_content.split("\n")[0]`),
saltándote el fragmento 0, que es el título del documento.

No necesitas el retriever: quieres **todas** las reglas, no las relevantes.

</details>

---

## Nivel 2 — Persistencia real

Cambia `MemorySaver` por `SqliteSaver` en `persistence.py`.

**Criterio:** corres `main.py`, lo matas, lo vuelves a correr con el mismo
`thread_id`, y el agente **recuerda** la conversación anterior.

<details>
<summary>Pista</summary>

La receta está comentada en `persistence.py`. El detalle que muerde:
`SqliteSaver.from_conn_string()` es un **gestor de contexto**. No puedes hacer
`return SqliteSaver.from_conn_string(...)` y usarlo fuera del `with`: la conexión
se cierra al salir.

Tienes dos salidas: mover el `with` a `main()` y pasar el checkpointer hacia
abajo, o quedarte con la conexión abierta a mano (`.__enter__()`) y cerrarla al
terminar. La primera es la correcta; la segunda enseña por qué.

</details>

---

## Nivel 3 — Aprobación humana antes de auditar (offline)

Un hallazgo de severidad `alta` no debería escribirse en el log de auditoría sin
que un humano lo apruebe. Integra el patrón del TEMA 13b en el proyecto final.

**Criterio:**
1. Si `hallazgo.severidad == "alta"`, el grafo se **pausa** antes de escribir.
2. Con `Command(resume="si")` se escribe; con `"no"`, no se escribe nada.
3. Un test lo demuestra sin llamar a la API (usa `ModeloFalso` de `conftest.py`).

<details>
<summary>Pista — el sitio donde esto se complica</summary>

`create_react_agent` no te deja meter un nodo entre la tool y el resto. Tienes
dos caminos:

**(a) El fácil:** llama a `interrupt()` **dentro** de la tool
`evaluar_regla_calidad`, justo antes de `audit.registrar_auditoria(...)`. Funciona:
las tools corren dentro de un nodo del grafo, así que `interrupt()` es legal ahí.

**(b) El honesto:** abandona `create_react_agent` y arma el `StateGraph` a mano
(agente → tools → aprobar → registrar). Más trabajo, y control total.

Empieza por (a). Cuando funcione, entenderás por qué (b) existe: en (a), el
grafo se pausa *a mitad de una tool*, y al reanudar la tool se re-ejecuta desde
su principio. Si la tool tuviera efectos secundarios antes del `interrupt()`,
ocurrirían **dos veces**.

Ese es un bug de producción de verdad, y lo acabas de encontrar tú.

</details>

---

## Nivel 4 — Observabilidad (necesita LANGSMITH_API_KEY, gratis)

Instrumenta el proyecto final con LangSmith y responde, **con números**:

1. ¿Cuántos tokens cuesta un turno que usa `buscar_normativa`?
2. ¿Y uno que usa `evaluar_regla_calidad`? ¿Por qué la diferencia?
3. ¿Qué paso tarda más: los embeddings, el retrieval o la generación?

**Criterio:** una tabla con los tres tiempos y los dos costes. Y una frase sobre
qué optimizarías primero.

<details>
<summary>Pista</summary>

No hace falta tocar el código del agente: LangSmith se activa por variables de
entorno (ver `16b_observabilidad_langsmith.py::activar_tracing`).

```bash
export LANGSMITH_API_KEY="ls__..."
export LANGSMITH_TRACING=true
uv run python proyecto_final/main.py
```

Abre la traza en smith.langchain.com y despliega el árbol. La respuesta a la
pregunta 3 sorprende a casi todo el mundo.

</details>

---

## Nivel 5 — Servirlo por HTTP

Coge `17_servidor_agente.py` y añade:

1. `GET /auditoria` — devuelve el log de hallazgos como JSON.
2. Rate limiting: máximo 5 peticiones por minuto y por `usuario`.
3. Un test con `TestClient` de FastAPI que verifique que `/chat` responde 503
   cuando el agente aún no ha arrancado.

**Criterio:** `uv sync --extra ui && uv run pytest` sigue en verde, y
`curl localhost:8000/auditoria` devuelve las líneas del log.

<details>
<summary>Pista</summary>

`audit.leer_auditoria()` ya te da la lista de líneas. El endpoint es de tres líneas.

Para el test, `fastapi.testclient.TestClient` **no dispara el `lifespan`** salvo
que lo uses como gestor de contexto (`with TestClient(app) as c:`). Justo por eso
es fácil testear el 503: crea el `TestClient` **sin** el `with`, y `ESTADO["agente"]`
seguirá siendo `None`.

</details>

---

## Nivel 6 — El multiagente

Reemplaza el agente único por el patrón supervisor del TEMA 15: un `consultor`
(solo RAG) y un `auditor` (solo evaluación + escritura del log), con un supervisor
que enruta.

**Criterio:** los tests existentes de `test_agente.py` siguen pasando (adaptando
el armado), y ahora puedes escribir un test que verifique que **una consulta nunca
toca el log de auditoría** — porque el consultor, literalmente, no tiene esa tool.

Esa garantía es imposible con un agente único. Es la razón de ser del patrón.

---

## Reflexión final

Fíjate en lo que hizo posible **todo** lo anterior: que `construir_agente()`
reciba el modelo, el evaluador y el retriever **por parámetro**.

Ese único detalle —inyección de dependencias— es lo que separa un proyecto que
puedes extender y testear de uno que solo puedes admirar. El `app.py` original
de 158 líneas hacía exactamente lo mismo que el modular… y no permitía ninguno
de estos seis ejercicios.

Las decisiones de arquitectura y su porqué: [`docs/adr/`](../docs/adr/).
Cuando algo se rompa: [`docs/README_runbook.md`](../docs/README_runbook.md).
