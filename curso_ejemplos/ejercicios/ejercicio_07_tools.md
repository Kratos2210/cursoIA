# Ejercicio 07 — Dos tools nuevas, y que el modelo elija

**Ejemplos base:** `07_herramientas.py` (definir) y `08_routing.py` (usar)
**Gasta cuota:** la Parte 1 no; la Parte 2 sí (2 llamadas por pregunta)

## Parte 1 — Escribe dos tools (offline)

Añade a `07_herramientas.py` dos herramientas nuevas del dominio del curso:

1. **`validar_ruc(ruc: str) -> str`** — un RUC peruano válido tiene **11 dígitos**
   y empieza por `10`, `15`, `17` o `20`. Devuelve un texto que explique si es
   válido y, si no, por qué no.

2. **`calcular_igv(monto: float) -> float`** — el IGV en Perú es del **18%**.
   Devuelve el monto **con** IGV incluido.

**Criterio de aceptación (verificable sin cuota):**

```python
assert validar_ruc.invoke({"ruc": "20123456789"}).startswith("válido")
assert "11 dígitos" in validar_ruc.invoke({"ruc": "201234"})
assert calcular_igv.invoke({"monto": 100.0} ) == 118.0
assert set(validar_ruc.args) == {"ruc"}
```

Escribe estos asserts como un test de verdad en `tests/`, con el estilo de
`tests/test_offline.py`.

## Parte 2 — Que el modelo las combine

Coge `08_routing.py` y dale las **tres** tools (las dos nuevas + la calculadora
de descuentos). Luego hazle esta pregunta:

> «El RUC 20123456789 nos compró por 3500 soles con 18% de descuento.
> ¿Es válido el RUC y cuánto pagará con IGV?»

**Criterio de aceptación:** el modelo llama a **las tres** tools (mira
`ai.tool_calls`) y su respuesta final contiene `2870` (el precio con descuento)
y `3386.6` (ese precio con IGV).

## Parte 3 — Rompe el docstring

Borra el docstring de `validar_ruc` y vuelve a lanzar la Parte 2.

**Criterio de aceptación:** describe qué pasó. ¿La eligió igual? ¿La ignoró?
¿La llamó cuando no tocaba?

---

## Pistas

<details>
<summary>Pista 1 — la forma de una tool</summary>

```python
@tool
def validar_ruc(ruc: str) -> str:
    """Valida si un RUC peruano tiene el formato correcto (11 dígitos).
    Úsala cuando el usuario mencione un RUC o pida verificar un contribuyente."""
    ...
```

La segunda línea del docstring — *"Úsala cuando…"* — es la más importante del
archivo. Es lo único que el modelo tiene para decidir si esta tool le sirve.

</details>

<details>
<summary>Pista 2 — la validación del RUC</summary>

```python
PREFIJOS_VALIDOS = ("10", "15", "17", "20")

if not ruc.isdigit():
    return "inválido: el RUC solo puede contener dígitos"
if len(ruc) != 11:
    return f"inválido: tiene {len(ruc)} dígitos y debe tener 11 dígitos"
if not ruc.startswith(PREFIJOS_VALIDOS):
    return f"inválido: debe empezar por {', '.join(PREFIJOS_VALIDOS)}"
return "válido"
```

Fíjate en que devolvemos **texto explicativo**, no un `bool`. El modelo va a
*leer* esa respuesta para redactar la suya: dale material.

</details>

<details>
<summary>Pista 3 — el bucle de tools (Parte 2)</summary>

`08_routing.py` ya trae el bucle completo. Solo tienes que ampliar la lista:

```python
herramientas = [calculadora_descuentos, validar_ruc, calcular_igv]
llm_tools = llm.bind_tools(herramientas)
mapa = {t.name: t for t in herramientas}
```

Y el bucle `for llamada in ai.tool_calls:` ya itera sobre **todas** las llamadas
que pidió el modelo, no solo la primera. Por eso funciona sin tocar nada más.

</details>

<details>
<summary>Pista 4 — qué esperar en la Parte 3</summary>

Sin docstring, LangChain usa el **nombre** de la función como única descripción.
`validar_ruc` es un nombre bastante bueno, así que el modelo quizá acierte igual.

Pruébalo entonces con un nombre malo (`def procesar(x: str)`) y **sin** docstring.
Ahí verás el fallo de verdad: el modelo no la llama nunca, o la llama con basura.

Lección: el par (nombre, docstring) **es** la interfaz. El código es un detalle
de implementación que el modelo jamás ve.

</details>

---

## Reflexión

Una tool tiene dos consumidores: el intérprete de Python (que ejecuta el cuerpo)
y el modelo (que lee la firma y el docstring). Casi todo el mundo escribe el
primero con cuidado y el segundo de cualquier manera. Después se queja de que
"el agente elige mal".

**Solución:** [`soluciones/solucion_07_tools.py`](soluciones/solucion_07_tools.py)
