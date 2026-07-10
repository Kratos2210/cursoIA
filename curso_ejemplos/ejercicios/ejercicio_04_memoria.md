# Ejercicio 04 — Memoria: el tercer turno y la ventana

**Ejemplo base:** `04_memoria.py` · **Gasta cuota:** sí (3–4 llamadas)

> 💡 **¿Sin cuota de Gemini?** Este ejercicio usa `util.crear_llm()`, que lee el proveedor del `.env`. Pon `LLM_PROVIDER=groq` + `GROQ_API_KEY` y pasas a `qwen/qwen3-32b` sin tocar código. Ver [README](README.md#-si-la-cuota-de-gemini-se-te-agota-429).


## Contexto

`04_memoria.py` guarda el historial en una lista de Python y lo reenvía entero
en cada turno. Funciona… hasta que deja de funcionar: el historial crece sin
límite, el prompt se vuelve enorme, y un día el modelo te dice que superaste
su ventana de contexto. Además, **pagas por cada token del historial, en cada turno**.

## Parte 1 — Un tercer turno

Añade un tercer turno a la conversación en el que preguntes algo que **solo se
pueda responder combinando los dos turnos anteriores**. Por ejemplo, si dijiste
tu nombre en el turno 1 y tu ciudad en el turno 2, pregunta algo que necesite
ambos.

**Criterio de aceptación:** la respuesta del tercer turno menciona información
que apareció en el primero *y* en el segundo.

## Parte 2 — La ventana deslizante

Modifica `chatear()` para que el historial **nunca supere los N mensajes más
recientes** (empieza con `N = 4`, es decir, 2 intercambios).

Después, vuelve a lanzar el tercer turno de la Parte 1.

**Criterio de aceptación:** con `N = 2` (un solo intercambio), el modelo ya
**no** puede responder al tercer turno. Ese olvido no es un bug: es el precio
exacto de la ventana. Tienes que poder explicarlo.

## Parte 3 — Resumir en vez de olvidar

Una ventana tira lo viejo. Un **resumen** lo comprime. Implementa esto:

> Cuando el historial supere los 6 mensajes, sustituye los más antiguos por un
> único `AIMessage` que contenga un resumen de lo que dijeron, generado por el
> propio modelo.

**Criterio de aceptación:** tras 5 turnos, `len(historial) <= 6`, y el modelo
sigue recordando tu nombre del turno 1.

---

## Pistas

<details>
<summary>Pista 1 — dónde tocar (Parte 2)</summary>

Todo ocurre dentro de `chatear()`, justo después de los dos `historial.append(...)`.
El historial es una lista normal de Python. Piensa en *slicing*.

</details>

<details>
<summary>Pista 2 — la ventana (Parte 2)</summary>

```python
VENTANA = 4   # nº máximo de mensajes conservados

def chatear(texto):
    r = cadena.invoke({"input": texto, "history": historial})
    historial.append(HumanMessage(content=texto))
    historial.append(AIMessage(content=r.content))
    # Conservamos solo los últimos VENTANA mensajes:
    del historial[:-VENTANA]      # ⚠️ trampa: con VENTANA=0 esto NO borra nada
    return r.content
```

⚠️ **La trampa de `[:-0]`.** Si `VENTANA` vale 0, `historial[:-0]` es
`historial[:0]`, que es la lista **vacía**: no borra nada, justo lo contrario de
lo que esperabas. Compruébalo: `l=[1,2,3]; del l[:-0]; print(l)`. Para una
ventana de 0 hay que escribir `historial.clear()`. Python está lleno de estas.

`del historial[:-4]` borra todo menos los 4 últimos. Es la forma idiomática de
recortar *in place* — importante, porque `chatear` cierra sobre esa lista y
reasignarla (`historial = historial[-4:]`) crearía una lista nueva que la función
externa no vería.

</details>

<details>
<summary>Pista 3 — el resumen (Parte 3)</summary>

Necesitas una segunda llamada al modelo, con su propio prompt:

```python
def resumir(mensajes):
    conversacion = "\n".join(f"{m.type}: {m.content}" for m in mensajes)
    resumen = llm.invoke(
        "Resume esta conversación en 2 frases, conservando NOMBRES y DATOS "
        f"concretos (fechas, ciudades, preferencias):\n{conversacion}"
    )
    return AIMessage(content=f"[Resumen de lo anterior] {resumen.content}")
```

Y en `chatear()`, cuando `len(historial) > 6`:

```python
if len(historial) > 6:
    viejos, recientes = historial[:-4], historial[-4:]
    historial[:] = [resumir(viejos), *recientes]    # ojo al [:] otra vez
```

Fíjate en el prompt: le pides **explícitamente** que conserve nombres y datos.
Un resumen genérico ("hablaron de comida") destruiría justo lo que la memoria
tenía que recordar.

</details>

---

## Reflexión

Las tres estrategias que acabas de tocar son las tres que existen:

| Estrategia | Coste por turno | Qué pierde |
|-----------|------------------|------------|
| Historial completo | Crece sin límite | Nada… hasta que revienta |
| Ventana | Constante | Todo lo anterior a la ventana |
| Resumen | Constante + 1 llamada | Los detalles que el resumen no salvó |

En producción se combinan: ventana de mensajes recientes **+** resumen de lo
viejo **+** un RAG sobre el histórico completo para lo que haga falta recuperar.

**Solución:** [`soluciones/solucion_04_memoria.py`](soluciones/solucion_04_memoria.py)
