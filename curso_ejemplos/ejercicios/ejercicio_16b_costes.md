# Ejercicio 16b — Predice la factura antes de calcularla

**Ejemplo base:** `16b_observabilidad_langsmith.py` · **Gasta cuota:** ❌ **no, es 100% offline**

> La aritmética del coste es código tuyo (`estimar_costo`, testeado en
> `TestTema16bObservabilidad`). Por eso puedes predecir el número exacto y luego
> comprobarlo, sin gastar un token.

## Contexto

El TEMA 16b deja caer una frase que casi todo el mundo memoriza mal:

> *"Los tokens de salida cuestan varias veces más que los de entrada. Por eso lo
> caro no es el contexto gigante del RAG: es una respuesta larga."*

Con `gemini-3.1-flash-lite`, la tabla `PRECIOS` dice: **entrada $0.25 / 1M**,
**salida $1.50 / 1M**. La salida cuesta 6× por token. Suena a que una respuesta
larga siempre domina la factura. Vamos a poner esa intuición a prueba.

## Los dos escenarios

Un mismo modelo, `gemini-3.1-flash-lite`, dos usos muy distintos de GobData:

| Escenario | Qué es | tokens entrada | tokens salida |
|-----------|--------|----------------|---------------|
| **A** | RAG sobre toda la normativa: contexto enorme, respuesta corta | 50 000 | 200 |
| **B** | Redactor de comunicados: prompt corto, respuesta larga | 500 | 3 000 |

## Predice, antes de ejecutar

**Escribe en un papel, ANTES de tocar `estimar_costo`:**

1. ¿Cuál de los dos escenarios cuesta más por llamada, **A** o **B**?
   (La intuición de "la salida es 6× más cara" apunta a **B**. ¿Es verdad aquí?)
2. Calcula **a mano** los dos costes con la fórmula
   `(entrada·0.25 + salida·1.50) / 1_000_000`. Anota los dos números en dólares.
3. **La pregunta buena:** manteniendo el escenario B con 500 tokens de entrada,
   ¿cuántos tokens de **salida** necesitaría para igualar el coste de A? Despeja
   la incógnita antes de programarla.

## Criterio de aceptación

```bash
uv run python ejercicios/soluciones/solucion_16b_costes.py
```

Debe imprimir, usando `estimar_costo` del ejemplo (no una fórmula que reescribas):

```text
Escenario A (RAG, 50000+200)  -> $0.012800
Escenario B (redactor, 500+3000) -> $0.004625
Gana (más caro): A, por ~2.8x
Punto de equilibrio: B igualaría a A con ~8450 tokens de salida
```

Y tienes que poder defender esta conclusión con los números delante:

> Sí, la salida cuesta 6× por token. Pero **A tiene 100× más tokens de entrada**,
> y 100× barato le gana a 6× caro. La regla no es "la salida siempre domina":
> es "multiplica el precio por la **cantidad**, no por el precio a secas".

## Reglas del juego

- **Usa la lógica de coste que ya existe.** Importa `estimar_costo` y `PRECIOS`
  del ejemplo `16b_observabilidad_langsmith.py`. Si reescribes la fórmula, el
  día que cambie un precio tendrás dos versiones que se contradicen.
- Cero llamadas a la API. Este ejercicio es pura aritmética observable.

---

## Pistas

<details>
<summary>Pista 1 — cómo importar la lógica sin instanciar nada</summary>

`estimar_costo(tokens, modelo)` recibe un dict `{"entrada": …, "salida": …}` y el
nombre del modelo, y devuelve dólares. No llama a ningún LLM: es aritmética pura.

```python
tokens_A = {"entrada": 50_000, "salida": 200}
costo_A = estimar_costo(tokens_A, "gemini-3.1-flash-lite")
```

El modelo tiene que estar en la tabla `PRECIOS`, o `estimar_costo` devuelve
`0.0` ("no sé cuánto costó", que no es lo mismo que "fue gratis").

</details>

<details>
<summary>Pista 2 — el cálculo a mano (para contrastar con el programa)</summary>

```text
A = (50000 · 0.25 + 200 · 1.50) / 1e6 = (12500 + 300) / 1e6 = $0.012800
B = (  500 · 0.25 + 3000 · 1.50) / 1e6 = (  125 + 4500) / 1e6 = $0.004625
```

A cuesta **2.77×** lo que B. Toda la ventaja de B en salida (4500 frente a 300)
no compensa que A traiga **49 500 tokens de entrada de más**.

</details>

<details>
<summary>Pista 3 — despejar el punto de equilibrio</summary>

Quieres el número de tokens de salida `s` que hace que B cueste lo mismo que A:

```text
500·0.25 + s·1.50 = 12800      (12800 = coste de A en "micro-dólares", ·1e6)
125 + 1.5·s = 12800
1.5·s = 12675
s = 8450 tokens de salida
```

O sea: el redactor tendría que escribir **~8450 tokens** (unas 6000 palabras)
para que su factura alcanzara a la de una sola consulta RAG sobre toda la
normativa. Por eso, en este sistema, **el coste vive en el contexto, no en la
respuesta** — justo al revés de lo que sugiere "la salida es 6× más cara".

</details>

<details>
<summary>Pista 4 — el test que fija la conclusión</summary>

```python
def test_el_rag_con_contexto_gigante_gana_al_redactor(m16b):
    a = m16b.estimar_costo({"entrada": 50_000, "salida": 200}, "gemini-3.1-flash-lite")
    b = m16b.estimar_costo({"entrada": 500, "salida": 3_000}, "gemini-3.1-flash-lite")
    assert a > b            # la intuición "la salida manda" falla aquí
    assert a == pytest.approx(0.0128)
```

Convierte una conclusión contraintuitiva en algo que no puede erosionarse sin
que un test se ponga rojo.

</details>

---

## Reflexión

Presupuestar un sistema de IA no es memorizar "la salida es cara". Es multiplicar
**precio × cantidad** en cada dirección y ver quién gana. Un RAG que mete medio
documento en cada prompt puede costar más que un chatbot verboso, aunque el
chatbot escriba diez veces más.

El número que le enseñas a tu jefe —"$X cada 1000 consultas"— sale de esta
aritmética, no de una intuición. Y ahora sabes cuál de los dos platillos de la
balanza vigilar en tu caso.

**Solución:** [`soluciones/solucion_16b_costes.py`](soluciones/solucion_16b_costes.py)
