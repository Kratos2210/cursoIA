# Ejercicio 14 — Una tercera tool en el servidor MCP

**Ejemplo base:** `14_mcp_servidor_cliente.py` · **Gasta cuota:** ❌ **no, es 100% offline**

> El protocolo corre de verdad —dos procesos hablando por stdio— pero sin LLM.
> Aquí TÚ haces de agente: descubres las tools y las invocas a mano.

## Contexto

El servidor `gobierno_datos` expone hoy dos tools:

```text
buscar_regla(nombre)          -> la definición de una regla de calidad
evaluar_severidad(porcentaje) -> "alta" | "media" | "baja"
```

`evaluar_severidad` te dice **cómo de grave** es un hallazgo, pero no qué hacer
con él. En GobData, cada nivel de severidad dispara una acción distinta de la
normativa: un hallazgo `alto` se escala al comité de riesgos; uno `bajo` se
anota y se revisa en la siguiente auditoría. Vamos a enseñárselo al servidor.

## Enunciado

Añade al **rol servidor** una tercera tool:

```python
sugerir_accion(severidad: str) -> str
```

que traduzca cada severidad a la acción que exige la normativa:

| severidad | acción esperada (una frase) |
|-----------|-----------------------------|
| `alta`    | escalar al **comité** de riesgos en 24 horas |
| `media`   | abrir un plan de corrección a 15 días |
| `baja`    | registrar y revisar en la próxima auditoría |

Que sea del mismo estilo que las otras dos: docstring que explique **cuándo**
usarla (es el contrato que leería un agente) y tipos en la firma.

Luego, en el **rol cliente**, descúbrela por el protocolo (sin leer el código
del servidor) e invócala **encadenada** con `evaluar_severidad`: primero
clasificas un porcentaje de error, y con esa severidad pides la acción.

## Predice, antes de ejecutar

1. ¿Cuántas tools listará ahora `get_tools()` en el cliente?
2. Un hallazgo con `porcentaje_error = 12.0`, ¿en qué acción termina tras pasar
   por las **dos** tools (`evaluar_severidad` → `sugerir_accion`)?
3. ¿Tuviste que tocar algo del cliente para que *descubriera* la tool nueva, o
   apareció sola? ¿Por qué?

## Criterio de aceptación

```bash
uv run python ejercicios/soluciones/solucion_14_mcp.py
```

Debe imprimir **tres** tools descubiertas y la cadena resuelta:

```text
=== Tools descubiertas en el servidor MCP ===
  · buscar_regla: ...
  · evaluar_severidad: ...
  · sugerir_accion: ...
...
  evaluar_severidad(12.0) -> alta
  sugerir_accion('alta')  -> escalar al comité de riesgos en 24 horas
```

Y escribe un test offline al estilo de `TestTema14Mcp` (en
`tests/test_offline.py`) que, sin leer el código del servidor, verifique:

```python
assert "sugerir_accion" in nombres            # la descubrió por el protocolo
assert "comité" in sugerir_accion("alta")     # y devuelve la acción correcta
```

---

## Pistas

<details>
<summary>Pista 1 — dónde va la tool nueva</summary>

Dentro de `correr_servidor()`, junto a las otras dos, con el mismo decorador:

```python
@mcp.tool()
def sugerir_accion(severidad: str) -> str:
    """Devuelve la acción que exige la normativa para una severidad dada.
    Úsala DESPUÉS de evaluar_severidad, para saber qué hacer con el hallazgo."""
    acciones = {
        "alta":  "escalar al comité de riesgos en 24 horas",
        "media": "abrir un plan de corrección a 15 días",
        "baja":  "registrar y revisar en la próxima auditoría",
    }
    return acciones.get(severidad.lower(), "severidad no reconocida")
```

Fíjate en la segunda línea del docstring: es lo único que un agente tendría
para decidir cuándo llamarla. Igual que en el TEMA 07, el par (nombre, docstring)
**es** la interfaz.

</details>

<details>
<summary>Pista 2 — por qué el cliente no cambia para descubrirla</summary>

El cliente nunca leyó el código del servidor. Hace `await client.get_tools()`,
y el servidor le **responde por el protocolo** qué tools tiene. Añadir una tool
al servidor cambia esa respuesta automáticamente: el cliente la ve sin que
toques su código.

Eso es todo el sentido de MCP: el consumidor y el proveedor solo comparten un
protocolo, no imports. Cambiar el servidor no obliga a recompilar el cliente.

</details>

<details>
<summary>Pista 3 — encadenar las dos tools</summary>

MCP devuelve "bloques de contenido", no un string pelado. Reutiliza el helper
`texto(...)` que el ejemplo ya define dentro de `correr_cliente()`:

```python
severidad = texto(await mapa["evaluar_severidad"].ainvoke({"porcentaje_error": 12.0}))
accion    = texto(await mapa["sugerir_accion"].ainvoke({"severidad": severidad}))
print(f"  evaluar_severidad(12.0) -> {severidad}")
print(f"  sugerir_accion('{severidad}') -> {accion}")
```

La salida de una tool alimenta la entrada de la siguiente: eso es,
literalmente, lo que hará un agente cuando le des estas tres tools.

</details>

<details>
<summary>Pista 4 — el test, sin instalar pytest-asyncio</summary>

El fixture `resultado_mcp` de `test_offline.py` ya levanta el servidor una vez
con `asyncio.run(...)`. Copia su patrón y añade `sugerir_accion` al diccionario
de invocaciones. No necesitas nada nuevo: el subproceso ya habla el protocolo.

```python
accion = _texto_mcp(await mapa["sugerir_accion"].ainvoke({"severidad": "alta"}))
assert "comité" in accion
```

</details>

---

## Reflexión

Añadir una capacidad a un sistema de agentes no siempre es tocar el agente. Aquí
tocaste **solo el servidor**, y cualquier cliente MCP —el tuyo, uno de otro
equipo, Claude Desktop— gana la tool nueva sin enterarse de nada. Esa es la
promesa del protocolo: las herramientas se publican una vez y se consumen desde
cualquier parte.

Y fíjate en lo barato que salió comprobarlo: sin cuota, sin llave, sin red hacia
fuera. El protocolo entero cabe en dos procesos de tu propia máquina.

**Solución:** [`soluciones/solucion_14_mcp.py`](soluciones/solucion_14_mcp.py)
