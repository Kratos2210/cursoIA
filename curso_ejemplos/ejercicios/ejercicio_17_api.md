# Ejercicio 17 — Un endpoint nuevo, probado sin API

**Ejemplo base:** `17_servidor_agente.py`
**Gasta cuota:** ❌ **no** para el criterio de aceptación (se prueba con `TestClient` y un agente falso)

> El servidor real construye el agente al arrancar, y eso **sí** gasta cuota. La
> gracia de este ejercicio es probar tu endpoint **sin** arrancar el agente real:
> le inyectas un doble de prueba y hablas con la app en memoria, con `TestClient`.

## Contexto

`17_servidor_agente.py` expone hoy dos rutas:

```text
POST /chat            -> responde una pregunta (cada 'usuario' es un thread_id)
GET  /salud           -> ¿está vivo el servidor? {estado, agente_listo}
```

El `POST /chat` ya guarda la conversación de cada usuario en el checkpointer,
aislada por `thread_id`. Pero no hay forma de **leer** ese historial: un cliente
que quiera pintar el chat de un usuario no tiene endpoint al que pedirlo.

## Enunciado

### Parte 1 — `GET /historial/{thread_id}`

Añade una ruta que devuelva la conversación guardada de un `thread_id`:

```json
{
  "thread_id": "ana",
  "turnos": 2,
  "historial": [
    {"rol": "human", "texto": "¿Cuántos años se conservan los registros?"},
    {"rol": "ai",    "texto": "Diez años, según la Regla 2."}
  ]
}
```

El historial vive en el checkpointer del agente. Se lee con
`agente.get_state(config).values["messages"]`, donde `config` es el mismo
`{"configurable": {"thread_id": ...}}` que usa `/chat`.

Trata los bordes como los trata el ejemplo: si el agente aún no está listo,
`503`; si el `thread_id` no tiene historial, `turnos: 0` y lista vacía (no un
error).

### Parte 2 — Un `/salud` más rico

Amplía `/salud` para que además informe qué modelo sirve y cuántas peticiones ha
atendido:

```json
{"estado": "ok", "agente_listo": true, "modelo": "gemini-3.1-flash-lite", "atendidas": 4}
```

El modelo sale de `util.modelo_por_defecto()`. El contador lo llevas en el
diccionario `ESTADO`.

## Criterio de aceptación (sin API)

El truco para probarlo offline: **no arranques el agente real**. Inyecta un
agente falso en `ESTADO` y crea el `TestClient` **sin** el `with`, para que el
`lifespan` (que construiría el agente de verdad) no llegue a ejecutarse.

```bash
uv run python ejercicios/soluciones/solucion_17_api.py
```

Debe imprimir las respuestas de los tres endpoints y terminar en verde. Lo
esencial que tienen que verificar tus aserciones:

```python
r = cliente.get("/historial/ana")
assert r.status_code == 200
assert r.json()["turnos"] == 2
assert r.json()["historial"][0]["rol"] == "human"

r = cliente.get("/historial/desconocido")
assert r.json()["turnos"] == 0          # sin historial no es un error

r = cliente.get("/salud")
assert r.json()["agente_listo"] is True
assert "modelo" in r.json()
```

---

## Pistas

<details>
<summary>Pista 1 — por qué el lifespan no se dispara (y por qué te conviene)</summary>

`TestClient(app)` a secas **no** ejecuta los eventos de arranque/apagado de
Starlette. Solo los ejecuta si lo usas como gestor de contexto:
`with TestClient(app) as cliente:`.

Como el `lifespan` del ejemplo es justo quien llama a `construir_agente()` (y eso
gasta cuota e indexa la normativa), **no** uses el `with`. Así el arranque caro
nunca corre, y tú controlas el estado a mano:

```python
ESTADO["agente"] = AgenteFalso()      # inyectas tu doble
cliente = TestClient(app)             # sin 'with' -> sin lifespan -> sin API
```

</details>

<details>
<summary>Pista 2 — el doble de prueba: qué interfaz imitar</summary>

Tu endpoint solo le pide al agente **una** cosa: `get_state(config)`, y de ahí
`.values["messages"]`. Así que el falso solo necesita implementar eso:

```python
from langchain_core.messages import HumanMessage, AIMessage

class EstadoFalso:
    def __init__(self, mensajes): self.values = {"messages": mensajes}

class AgenteFalso:
    HISTORIALES = {
        "ana": [HumanMessage("¿Cuántos años se conservan los registros?"),
                AIMessage("Diez años, según la Regla 2.")],
    }
    def get_state(self, config):
        hilo = config["configurable"]["thread_id"]
        return EstadoFalso(self.HISTORIALES.get(hilo, []))
```

Usamos mensajes de LangChain de verdad para que `m.type` dé `"human"`/`"ai"`
igual que en producción. El endpoint no distingue el doble del agente real:
esa es toda la idea de un test doble.

</details>

<details>
<summary>Pista 3 — el endpoint del historial</summary>

```python
@app.get("/historial/{thread_id}")
def historial(thread_id: str):
    agente = ESTADO["agente"]
    if agente is None:
        raise HTTPException(status_code=503, detail="El agente todavía está arrancando.")
    config = {"configurable": {"thread_id": thread_id}}
    mensajes = agente.get_state(config).values.get("messages", [])
    return {
        "thread_id": thread_id,
        "turnos": len(mensajes),
        "historial": [{"rol": m.type, "texto": m.content} for m in mensajes],
    }
```

Fíjate en `.get("messages", [])`: un hilo sin conversación devuelve lista vacía,
no un `KeyError`. "No hay historial" es una respuesta válida, no un fallo.

</details>

<details>
<summary>Pista 4 — el contador de /salud</summary>

Lleva el contador en `ESTADO` e increméntalo en `/chat`. Para /salud:

```python
@app.get("/salud")
def salud():
    listo = ESTADO["agente"] is not None
    return {
        "estado": "ok" if listo else "arrancando",
        "agente_listo": listo,
        "modelo": modelo_por_defecto(),      # de util.py, sin llamar al modelo
        "atendidas": ESTADO.get("atendidas", 0),
    }
```

`modelo_por_defecto()` solo lee el `.env`; no habla con ningún proveedor, así que
el health check sigue siendo barato y offline.

</details>

---

## Reflexión

Un endpoint no necesita el sistema entero para probarse. El agente real cuesta
cuota y segundos de indexado; tu ruta `/historial`, en cambio, es cinco líneas
que transforman un `get_state` en JSON — y eso se prueba en milisegundos con un
doble. Separar *"la lógica del endpoint"* de *"el agente que hay detrás"* es lo
que te deja tener tests de la API que corren en cada commit, sin llave.

Es la misma idea del resto del curso: la parte cara (el LLM) casi nunca es la
que se rompe. Se rompe tu código alrededor —y ese sí puedes blindarlo gratis.

**Solución:** [`soluciones/solucion_17_api.py`](soluciones/solucion_17_api.py)
