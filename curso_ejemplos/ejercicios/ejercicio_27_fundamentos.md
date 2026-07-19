# Ejercicio 27 — Fundamentos: qué significan de verdad tus parámetros

**Ejemplo base:** `27_fundamentos_llm.py` · **Gasta cuota:** no (100% offline)

> Llevas 26 módulos poniendo `temperature=0` y `top_p=0.9` porque alguien lo
> puso en un ejemplo. Este ejercicio te obliga a **predecir números** antes de
> ejecutarlos. Si tu predicción falla, ahí está lo que no entendías.

## Contexto

`27_fundamentos_llm.py` implementa a mano las cuatro piezas: BPE, softmax con
temperatura, muestreo `top_k`/`top_p` y perplejidad. Todo son funciones puras y
deterministas, así que se puede **calcular a mano y comprobar**.

Usaremos siempre estos logits, los del ejemplo:

```python
logits = [2.0, 1.0, 0.2, -1.0]
```

## Parte 1 — El plural que cuesta un token

Con el corpus del ejemplo y `n_merges=12`, tokeniza `"proyecto"` y `"proyectos"`.

**Criterio de aceptación:** predice el número de tokens de cada uno **antes** de
ejecutar, acierta la diferencia, y explica por qué `"ecto"` acabó siendo una sola
pieza mientras que `"proy"` sigue partido letra a letra. ¿Qué le pasaría a una
factura de tokens si tu producto está en un idioma que no estaba en el corpus de
entrenamiento del tokenizador?

## Parte 2 — Encuentra la temperatura que NO cambia nada

Calcula `softmax_con_temperatura(logits, t)` para `t = 0, 0.1, 0.5, 1.0, 2.0, 10.0`.

**Criterio de aceptación:** responde con los números en la mano:

1. ¿A partir de qué `t` la distribución es **indistinguible** de `t=0` con 4
   decimales? ¿Qué implica eso para el clásico "pon `temperature=0.1` para que
   sea casi determinista"?
2. Con `t=10.0`, ¿se ha vuelto uniforme del todo? Da el número exacto y di
   cuánto ventaja le queda al token 0 sobre el 3.
3. `temperature=0` **no** apaga la creatividad. Explica en una frase qué apaga
   de verdad.

## Parte 3 — El `top_p` que es un `top_k=1` disfrazado

Muestrea 2000 veces con `top_p = 0.5`, `0.9` y `1.0`, contando qué índices salen.

**Criterio de aceptación:** descubre que **uno de esos tres valores nunca sale
del token 0**, di cuál y demuestra con la aritmética de la distribución **por qué
tenía que pasar**. Luego responde: si un compañero te dice "he puesto `top_p=0.5`
para que el modelo sea más creativo", ¿qué le explicas?

## Parte 4 — La perplejidad tiene unidades

Calcula la perplejidad de estos tres casos:

```python
calcular_perplejidad([0.25, 0.25, 0.25, 0.25])   # el modelo dudaba entre 4
calcular_perplejidad([1.0, 1.0])                 # certeza absoluta
calcular_perplejidad([0.5, 0.0])                 # un token imposible
```

**Criterio de aceptación:** el primero da un número **exacto y muy reconocible**.
Di cuál es y completa la frase: «una perplejidad de N significa que el modelo
estaba tan indeciso como si eligiera al azar entre ___». Explica también por qué
el tercero da `inf` y por qué eso es correcto y no un bug.

## Parte 5 — Conecta con el m28

**Criterio de aceptación:** explica, usando lo de la Parte 4, cómo montarías un
**filtro de perplejidad** que marque prompts adversariales, y di **qué falso
positivo** tendría ese filtro en un producto real.

---

## Pistas

<details>
<summary>Pista 1 — por qué "ecto" sí y "proy" no</summary>

Mira los merges aprendidos:

```
[('t','o'), ('c','to'), ('e','cto'), ('f','ecto'), ('a','fecto'), ...]
```

BPE fusiona el par **más frecuente** en cada ronda. En el corpus
(`proyecto, objeto, efecto, afecto, insecto, dialecto`), la secuencia `e-c-t-o`
aparece en casi todas las palabras, así que se fusiona pronto y en cadena:
`to` → `cto` → `ecto`.

`p-r-o-y` aparece **en una sola palabra**. Nunca es el par más frecuente, nunca
se fusiona, y se queda en letras sueltas.

**La consecuencia comercial:** un tokenizador entrenado sobre todo en inglés
parte el español —y mucho más el quechua, el árabe o el tailandés— en trozos
diminutos. La misma frase cuesta 2–3× más tokens. Pagas más por token **y**
consumes tu ventana de contexto más rápido, por un texto que dice lo mismo. La
tokenización es un impuesto invisible sobre los idiomas mal representados.

</details>

<details>
<summary>Pista 2 — el colapso de la temperatura</summary>

Con `t=0.1`, los logits se dividen por 0.1, o sea se **multiplican por 10**:
`[20, 10, 2, -10]`. La diferencia entre el primero y el segundo pasa de 1 a 10,
y `exp(10) ≈ 22026`. El token 0 se lleva el 99.995%.

Redondeado a 4 decimales: `[1.0, 0.0, 0.0, 0.0]`. **Idéntico a `t=0`.**

O sea: `temperature=0.1` no es "casi determinista", es **determinista en la
práctica** para logits normales. La zona interesante está entre 0.5 y 1.5; por
debajo de 0.3 casi todo colapsa.

Y con `t=10.0` sale `[0.2873, 0.2599, 0.2400, 0.2128]`: se acerca a lo uniforme
(0.25) pero **no llega nunca**. El orden se conserva siempre — softmax es
monótona. La temperatura aplana, jamás reordena.

</details>

<details>
<summary>Pista 3 — el núcleo que solo tiene un token</summary>

Con `t=1.0`, las probabilidades son `[0.6317, 0.2324, 0.1044, 0.0315]`.

`muestrear_top_p` acumula desde el más probable y **para en cuanto llega a `p`**:

```python
nucleo.append(indice)
acumulado += probs[indice]
if acumulado >= p:
    break
```

Con `p=0.5`: el primer token ya aporta 0.6317 ≥ 0.5 → **el núcleo tiene un solo
token** y el muestreo es greedy puro. `top_p=0.5` aquí es exactamente `top_k=1`.

Qué le explicas a tu compañero: `top_p` **no es un dial de creatividad**, es un
recorte de la cola. Bajarlo hace el modelo **menos** creativo, no más — y por
debajo de la probabilidad del token más probable lo vuelve completamente
determinista. Si quiere más variedad, tiene que **subir** `top_p` (o la
temperatura), no bajarlo.

Detalle bonito: `top_p=1.0` y `top_k=4` dan exactamente el mismo reparto
(`{0: 1243, 1: 497, 2: 193, 3: 67}` con `Random(42)`), porque ambos admiten
todos los tokens.

</details>

<details>
<summary>Pista 4 — la perplejidad cuenta opciones</summary>

`calcular_perplejidad([0.25]*4)` da **exactamente 4.0**.

No es casualidad. Perplejidad = `exp(-media(log p))`. Con todas las
probabilidades iguales a `1/N`, sale `exp(log N) = N`.

> **Una perplejidad de N significa que el modelo estaba tan indeciso como si
> eligiera al azar entre N opciones equiprobables.**

Por eso se dice que la perplejidad es el «número efectivo de opciones». Certeza
absoluta (`[1.0, 1.0]`) da **1.0**: una sola opción, ninguna duda. Es el mínimo
posible; la perplejidad nunca baja de 1.

Y el `inf` del tercer caso es **correcto**: el modelo le dio probabilidad 0 a un
token que de hecho apareció. Es sorpresa infinita — el modelo consideraba
imposible algo que pasó. Matemáticamente `log(0) = -inf`; conceptualmente, tu
modelo está roto o el texto es imposible bajo él. Devolver `inf` en vez de
reventar es la decisión correcta: propaga la señal en vez de esconderla.

</details>

<details>
<summary>Pista 5 — el filtro de perplejidad y su falso positivo</summary>

La idea (m28): un prompt de inyección con sufijos adversariales generados por
gradiente —`describing.\ + similarlyNow write oppositeley.]( Me giving**ONE`—
está lleno de tokens improbables. Su perplejidad se dispara. Umbral arriba,
bloqueo.

```python
def sospechoso(probs, umbral=1000.0):
    return calcular_perplejidad(probs) > umbral
```

**El falso positivo que lo mata en producción:** todo lo que es legítimamente
raro. Código fuente, logs, identificadores (`a7f3-9c2e-...`), fórmulas químicas,
nombres propios poco comunes, jerga técnica, y —muy importante— **texto en un
idioma minoritario o mezclado**. Un usuario peruano escribiendo con quechua o
con jerga limeña tiene perplejidad alta y no está atacando a nadie.

Es la Parte 1 volviendo a morder: el mismo sesgo del tokenizador reaparece como
sesgo del filtro de seguridad. Un guardarraíl basado en perplejidad discrimina,
sin quererlo, exactamente a los usuarios peor representados en el entrenamiento.

Por eso el filtro de perplejidad es una **señal más** para puntuar, nunca un
bloqueo por sí solo. Igual que el detector de regex del m23.

</details>

---

## Reflexión

Los tres parámetros que más se tocan a ciegas —`temperature`, `top_p`, `top_k`—
resultan ser lo mismo mirado desde ángulos distintos: **cuánta masa de
probabilidad dejas viva antes de tirar el dado**.

- `temperature` **deforma** la distribución (aplana o concentra).
- `top_k` y `top_p` la **recortan** (por número fijo o por masa acumulada).

Ninguno "hace al modelo más creativo": todos deciden cuánto riesgo aceptas de
que salga un token improbable. La creatividad que percibes es riesgo bien
administrado.

Y la moraleja de método: has predicho números y algunos te han salido mal. En un
sistema con LLM, esa es la única forma honesta de saber que entiendes algo —
porque el modelo siempre devuelve *algo* plausible, y lo plausible no te corrige.

**Solución:** [`soluciones/solucion_27_fundamentos.py`](soluciones/solucion_27_fundamentos.py)
