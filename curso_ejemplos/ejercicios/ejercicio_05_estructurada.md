# Ejercicio 05 — Un cuarto molde Pydantic

**Ejemplo base:** `05_salida_estructurada.py` · **Gasta cuota:** sí (1–2 llamadas)

> 💡 **¿Sin cuota de Gemini?** Este ejercicio usa `util.crear_llm()`, que lee el proveedor del `.env`. Pon `LLM_PROVIDER=groq` + `GROQ_API_KEY` y pasas al modelo por defecto de Groq sin tocar código. Ver [README](README.md#-si-la-cuota-de-gemini-se-te-agota-429).


## Contexto

`05_salida_estructurada.py` tiene tres moldes: `Persona`, `Extraccion` y
`Etiqueta`. Vas a construir un cuarto para un caso real de gobierno de datos.

## Enunciado

Crea un molde `TicketSoporte` que extraiga, de un correo de cliente escrito en
lenguaje natural, estos campos:

| Campo | Tipo | Notas |
|-------|------|-------|
| `asunto` | `str` | Resumen en menos de 10 palabras |
| `urgencia` | `Literal["alta","media","baja"]` | No un `str` cualquiera |
| `categoria` | `Literal["facturación","técnico","comercial"]` | |
| `cliente_menciona_datos_personales` | `bool` | ⚠️ Si es `True`, hay que anonimizar |
| `productos` | `list[str]` | Vacía si no menciona ninguno |

Pruébalo con este correo:

```text
Buenas, soy Ana Torres (DNI 45678912). Llevo dos días sin poder entrar al panel
de Analytics y encima me cobraron el plan Pro dos veces este mes. Necesito que
lo arreglen HOY, tengo una auditoría el viernes.
```

## Criterios de aceptación

1. `urgencia == "alta"` y `cliente_menciona_datos_personales is True`.
2. `productos` contiene al menos `"Analytics"` (o similar) y el plan `"Pro"`.
3. **Si cambias `Literal` por `str`, el ejemplo sigue corriendo.** Explica por
   escrito qué se pierde. (Pista: piensa en qué pasa cuando el modelo devuelve
   `"Alta"`, `"urgente"` o `"ALTA!!"` y tu código hace `if urgencia == "alta"`.)
4. Escribe **un test offline** que valide el molde sin llamar al modelo:
   construye un `TicketSoporte` a mano y comprueba que rechaza
   `urgencia="urgentísima"`.

---

## Pistas

<details>
<summary>Pista 1 — el esqueleto</summary>

```python
from typing import Literal, List
from pydantic import BaseModel, Field

class TicketSoporte(BaseModel):
    """Un ticket de soporte extraído de un correo de cliente."""
    asunto: str = Field(description="Resumen del problema, menos de 10 palabras")
    urgencia: Literal["alta", "media", "baja"] = Field(description="...")
    # ...
```

Recuerda: el `description` de cada `Field` **no es un comentario**. Es la
instrucción que el modelo lee para saber qué poner ahí.

</details>

<details>
<summary>Pista 2 — por qué Literal y no str</summary>

`with_structured_output` traduce tu molde a un **JSON Schema** que se le envía
al modelo. Un `Literal["alta","media","baja"]` se convierte en un `enum` dentro
de ese esquema, y el modelo queda **restringido** a esos tres valores.

Con un `str` a secas, el esquema solo dice "aquí va texto". El modelo escribirá
lo que le parezca —`"Alta"`, `"urgente"`, `"muy alta"`— y tu `if urgencia == "alta"`
fallará silenciosamente en producción. No lanza una excepción: simplemente toma
la rama equivocada. Ese es el bug más caro que existe.

</details>

<details>
<summary>Pista 3 — el test offline</summary>

```python
import pytest
from pydantic import ValidationError

def test_rechaza_una_urgencia_inventada():
    with pytest.raises(ValidationError):
        TicketSoporte(asunto="a", urgencia="urgentísima", categoria="técnico",
                      cliente_menciona_datos_personales=False, productos=[])
```

Es exactamente el patrón de `proyecto_final/tests/test_audit.py`, donde
`HallazgoCalidad` rechaza una severidad inventada. Ve a mirarlo.

</details>

---

## Reflexión

El campo `cliente_menciona_datos_personales` no es un ejercicio de estilo: es
un **control de gobierno de datos ejecutable**. El correo de Ana contiene un DNI.
Un pipeline que lo detecte automáticamente puede anonimizarlo antes de que ese
texto acabe en un log, en un dataset de entrenamiento o en la traza de LangSmith.

Ese es el salto de "el modelo devuelve texto" a "el modelo devuelve datos sobre
los que puedo *decidir*".

**Solución:** [`soluciones/solucion_05_estructurada.py`](soluciones/solucion_05_estructurada.py)
