# Ejercicio 13 — Escalar cuando el humano rechaza

**Ejemplo base:** `13b_human_in_the_loop.py` · **Gasta cuota:** ❌ **no, es 100% offline**

## Contexto

El grafo actual es:

```text
START -> detectar -> aprobar -> registrar -> END
```

Cuando la severidad es `alta`, el nodo `aprobar` llama a `interrupt()`, el grafo
se congela y espera a un humano. Si el humano dice `si`, se registra. Si dice
`no`, se **descarta y ahí muere el asunto**.

Eso está mal. En una financiera, que un analista rechace un hallazgo de severidad
alta no lo hace desaparecer: lo **escala** a su supervisor.

## Enunciado

Añade un nodo `escalar` y enruta así:

```text
                              ┌── aprobado ──> registrar ──> END
START -> detectar -> aprobar ─┤
                              └── rechazado ─> escalar ───> END
```

`escalar` debe:
1. Escribir en el estado un `registro` que indique que el caso subió de nivel.
2. Guardar **quién** lo rechazó y **el motivo** que dio.

Para eso tendrás que cambiar el `interrupt()`: además de `si`/`no`, el humano
debe poder dar un motivo cuando rechaza.

## Criterios de aceptación

1. Con severidad `alta` + respuesta `si` → el grafo pasa por `registrar` y el
   estado final dice `REGISTRADO`.
2. Con severidad `alta` + respuesta `no` → pasa por `escalar` (**no** por
   `registrar`) y el estado final dice `ESCALADO`, incluyendo el motivo.
3. Con severidad `baja` → no hay `interrupt()`, pasa por `registrar`, y el
   grafo **nunca** entra en `escalar`.
4. Escribe **tres tests offline**, uno por cada camino. Guíate por
   `TestTema13bHumanInTheLoop` en `tests/test_offline.py`.

## Parte 2 (opcional) — Reanudar tras un reinicio

Con `MemorySaver`, si el proceso muere mientras el grafo está pausado, el estado
se pierde. Cambia el checkpointer a `SqliteSaver` y demuestra que puedes:

1. Lanzar el grafo hasta el `interrupt()`.
2. **Matar el proceso** (Ctrl-C).
3. Volver a arrancar, y reanudarlo con `Command(resume="no")` usando el mismo
   `thread_id`.

Necesitarás `uv pip install langgraph-checkpoint-sqlite`. La receta está comentada
en `proyecto_final/persistence.py`.

Ese es, literalmente, el mecanismo por el que una aprobación puede tardar tres días.

---

## Pistas

<details>
<summary>Pista 1 — el estado necesita campos nuevos</summary>

```python
class EstadoAuditoria(TypedDict):
    hallazgo: str
    severidad: str
    aprobado: bool
    motivo_rechazo: str    # nuevo
    registro: str
```

Un `TypedDict` no valida en tiempo de ejecución, pero documenta el contrato del
grafo. Si un nodo devuelve una clave que no está aquí, LangGraph la ignora en
silencio — y te vuelves loco buscando por qué "no se guarda". Declárala.

</details>

<details>
<summary>Pista 2 — la arista condicional</summary>

Es el mismo patrón que el supervisor del TEMA 15:

```python
def tras_aprobar(state) -> str:
    """Devuelve la ETIQUETA de la siguiente arista."""
    return "registrar" if state["aprobado"] else "escalar"

grafo.add_conditional_edges(
    "aprobar",
    tras_aprobar,
    {"registrar": "registrar", "escalar": "escalar"},
)
grafo.add_edge("registrar", END)
grafo.add_edge("escalar", END)
```

⚠️ Borra el `grafo.add_edge("aprobar", "registrar")` que había antes. Si lo dejas,
el grafo irá **siempre** a `registrar`, además de a donde diga la condicional.

</details>

<details>
<summary>Pista 3 — pedirle el motivo al humano</summary>

`interrupt()` devuelve **lo que sea** que le pases a `Command(resume=...)`.
No tiene que ser un string: puede ser un diccionario.

```python
decision = interrupt({...})           # el humano responde con un dict
aprobado = decision.get("respuesta") == "si"
return {"aprobado": aprobado, "motivo_rechazo": decision.get("motivo", "")}
```

Y al reanudar:

```python
app.invoke(Command(resume={"respuesta": "no", "motivo": "falta evidencia"}), config)
```

En un test, esto es todo lo que necesitas: nada de `input()`.

</details>

<details>
<summary>Pista 4 — el test del camino de escalado</summary>

```python
def test_el_rechazo_escala_el_hallazgo(importar_ejemplo):
    from langgraph.types import Command
    app = importar_ejemplo("13b_human_in_the_loop").construir_grafo()
    config = {"configurable": {"thread_id": "t_escala"}}
    app.invoke(ESTADO_ALTA, config)                       # se pausa
    final = app.invoke(
        Command(resume={"respuesta": "no", "motivo": "falta evidencia"}), config)
    assert final["registro"].startswith("ESCALADO")
    assert "falta evidencia" in final["registro"]
```

</details>

---

## Reflexión

Un `interrupt()` convierte un programa en un **proceso de negocio**. El grafo
puede estar pausado tres días esperando a que alguien lea un correo, y reanudarse
exactamente donde estaba. Es la diferencia entre un script y un sistema.

Y fíjate en lo que **no** cambió al añadir el escalado: ni el modelo, ni el
prompt, ni las tools. Solo el grafo. Esa separación entre *"qué sabe el sistema"*
y *"qué hace el sistema"* es la razón de existir de LangGraph.

**Solución:** [`soluciones/solucion_13_hitl.py`](soluciones/solucion_13_hitl.py)
