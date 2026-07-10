# Ejercicio 15 — Un tercer especialista, y predice a quién enruta

**Ejemplo base:** `15_supervisor_multiagente.py` · **Gasta cuota:** ❌ **no, es 100% offline**

> Como el ejercicio 12: **escribe tu predicción antes de ejecutar**. El grafo es
> real; lo único simulado es el cerebro del supervisor, que aquí decide con
> reglas. Justo por eso puedes predecir su salida exactamente.

## Contexto

El equipo tiene hoy dos especialistas y un supervisor que reparte:

```text
· consultor  — responde dudas sobre la normativa.
· evaluador  — evalúa/puntúa si una regla de calidad se cumple.
· supervisor — no sabe de nada, pero sabe A QUIÉN preguntarle.
```

La política de enrutado vive en la función pura `decidir(pregunta, ya_respondido)`:
si piden **evaluar/verificar**, va al `evaluador`; en cualquier otro caso, al
`consultor`. Falta una capacidad que en una financiera se pide a diario:
**redactar el comunicado** de un hallazgo para el regulador.

## Enunciado

Añade un tercer especialista, `redactor`, y enséñale al supervisor a enrutarle
las peticiones de redacción.

```text
                 ┌── consultor ──┐
START -> supervisor ┼── evaluador ──┼──> supervisor ──> END
                 └── redactor ───┘
```

1. Amplía el `Literal Destino` para incluir `"redactor"`.
2. Añade una lista `PALABRAS_DE_REDACCION` (p. ej. `redacta`, `redactar`,
   `informe`, `comunicado`, `documenta`, `notifica`) y una rama en `decidir`.
3. Escribe el nodo `redactor`: devuelve un `respuesta` con el borrador del
   comunicado y `quien_respondio = "redactor"`.
4. Regístralo en el grafo y añádelo al mapa de la arista condicional.

## Predice, antes de ejecutar

Rellena esta tabla **en un papel** antes de correr nada. Es el ejercicio:

| # | Pregunta | ¿consultor, evaluador o redactor? |
|---|----------|-----------------------------------|
| 1 | ¿Cuántos años se conservan los registros? | ? |
| 2 | Evalúa esta regla: cifrado AES-256. | ? |
| 3 | Redacta el comunicado del incumplimiento de junio. | ? |
| 4 | Documenta qué dice la norma sobre el consentimiento. | ? |
| 5 | **Redacta un informe que evalúe la regla 3.** | ? |

La fila 5 es la trampa: menciona **redacción** y **evaluación** a la vez. A
quién termina yendo **no** depende de cuál "pesa más" — depende de **en qué
orden pusiste los `if`** en `decidir`. Predice el destino *y* explica por qué.

## Criterios de aceptación

1. Las filas 1–4 enrutan a lo que predijiste.
2. La fila 5 enruta a **el especialista cuyo `if` va primero** en tu `decidir`.
   Cambia el orden de los dos `if` y comprueba que el destino de la fila 5 se
   invierte, mientras las otras cuatro no se mueven.
3. Un especialista responde y el grafo **termina** (no entra en bucle): la regla
   `if ya_respondido: return "FIN"` sigue siendo la que corta el ciclo.
4. Escribe tests offline al estilo de `TestTema15Supervisor`: uno que mande la
   fila 3 al `redactor`, y uno que fije el desempate de la fila 5.

```bash
uv run python ejercicios/soluciones/solucion_15_supervisor.py
```

---

## Pistas

<details>
<summary>Pista 1 — el orden de los `if` ES la política de desempate</summary>

`decidir` mira la pregunta con una cadena de `if`. El **primero** que casa gana;
los demás ni se evalúan. Por eso la fila 5 ("redacta un informe que evalúe…")
no tiene una respuesta "correcta" universal: tiene la respuesta que tu código
decidió al ordenar los `if`.

```python
def decidir(pregunta, ya_respondido):
    if ya_respondido:
        return "FIN"
    texto = pregunta.lower()
    if any(p in texto for p in PALABRAS_DE_REDACCION):   # ¿este primero…
        return "redactor"
    if any(p in texto for p in PALABRAS_DE_EVALUACION):   # …o este?
        return "evaluador"
    return "consultor"
```

Un supervisor de verdad (con LLM) tiene el mismo problema, solo que el desempate
lo decide el modelo en vez de tu orden de `if`. La lección es la misma: **las
intenciones se solapan, y el enrutado necesita una regla de desempate explícita.**

</details>

<details>
<summary>Pista 2 — el Literal te protege de un typo</summary>

```python
Destino = Literal["consultor", "evaluador", "redactor", "FIN"]
```

Si olvidas añadir `"redactor"` aquí pero el nodo existe, el grafo enruta igual…
hasta que el LLM del modo `decidir_con_llm` devuelva "redactor" y la salida
estructurada lo rechace por no estar en el Literal. Declararlo es documentar el
contrato **y** blindar el modo LLM de una vez.

</details>

<details>
<summary>Pista 3 — registrar el nodo y cerrar el bucle</summary>

Tres cambios en `construir_grafo`, calcados de los otros dos especialistas:

```python
grafo.add_node("redactor", redactor)
grafo.add_conditional_edges(
    "supervisor", hacia_donde,
    {"consultor": "consultor", "evaluador": "evaluador",
     "redactor": "redactor", "FIN": END},   # <- añade la entrada
)
grafo.add_edge("redactor", "supervisor")    # <- devuelve el control (cierra el bucle)
```

⚠️ Si olvidas la última línea, el `redactor` va directo a… ningún sitio: el
grafo no sabe volver al supervisor y no puede terminar limpio.

</details>

<details>
<summary>Pista 4 — el test que fija el desempate</summary>

```python
def test_redaccion_va_al_redactor(m15sol):
    assert m15sol.decidir("Redacta el comunicado del incumplimiento", False) == "redactor"

def test_el_desempate_lo_gana_quien_va_primero(m15sol):
    # Con redacción antes que evaluación en decidir(), gana el redactor.
    assert m15sol.decidir("Redacta un informe que evalúe la regla 3", False) == "redactor"
```

Ese segundo test es el valioso: convierte una decisión de diseño (el orden de
los `if`) en algo que un cambio accidental pondría en rojo.

</details>

---

## Reflexión

Añadir un tercer especialista **no alargó el prompt de los otros dos** ni tocó
su lógica: cada uno sigue con su trabajo. Eso es lo que compra el patrón
supervisor frente a un único agente con diez tools —donde cada tool nueva
confunde un poco más a las demás.

Y te llevas la lección incómoda de todo enrutado: cuando dos intenciones se
solapan, *algo* tiene que desempatar. Aquí fue el orden de tus `if`; en
producción será el prompt del supervisor. Hazlo explícito, o el sistema
desempatará por ti de una forma que no controlas.

**Solución:** [`soluciones/solucion_15_supervisor.py`](soluciones/solucion_15_supervisor.py)
