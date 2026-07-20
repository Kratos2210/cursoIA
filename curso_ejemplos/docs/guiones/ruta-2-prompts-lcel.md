# Guion · Ruta 2 — Prompts y composición LCEL (6–7 min)

**Se publica en:** c02 · **Demo:** el pipeline del c09b devolviendo JSON validado

## Gancho (0:00–0:30)

> Un prompt no es una pregunta bonita: es una PLANTILLA con huecos, versionada
> como código. Y la diferencia entre un juguete y un sistema es que el sistema
> devuelve un DATO validado, no un párrafo que alguien tiene que leer. En esta
> ruta pasas de «chatear con la IA» a construir tu primera utilidad seria.

## Qué vas a poder hacer (0:30–1:15)

- Componer prompt → modelo → parser con el operador `|` (LCEL) y leerlo como una tubería.
- Forzar al modelo a devolver JSON que Pydantic valida — o revienta, que es lo correcto.
- Armar un pipeline con filtro de entrada, reintentos y fallback: tu primer sistema completo (c09b).

## Demo (1:15–4:30)

```bash
cd curso_ejemplos
uv run python 05_salida_estructurada.py   # el modelo devuelve un MOLDE, no prosa
uv run python 09b_proyecto_texto.py       # el pipeline completo del proyecto
```

Puntos de guion:
- En el 05: enseñar el `BaseModel` en el editor ANTES de correr. «Esto es un
  contrato. El modelo firma o no pasa.»
- En el 09b: señalar el diagrama animado de la web (pantalla partida): consulta
  → filtro → prompt → modelo → JSON, y los DOS lazos de vuelta (reintento y
  coste). «Los lazos son la diferencia entre demo y producto.»
- Forzar un fallo: petición vacía → el filtro la rechaza ANTES de gastar
  tokens. «El código más barato es el que no llama al modelo.»

## Recorrido de la ruta (4:30–5:45)

- **c02** plantillas y el operador `|`. **c26b** few-shot, CoT, self-consistency — el prompting con método.
- **c06** Runnables: Parallel, Passthrough, Lambda. **c05** salida estructurada.
- **c04** memoria de conversación. **c09** resiliencia: 429, retry, fallback, async.
- **c09b** el proyecto que lo cose todo (lo que acabas de ver).

## Cierre (5:45–6:15)

> Cuando termines esta ruta vas a tener algo que el 90% no tiene: un pipeline
> que devuelve datos validados y aguanta errores. Eso ya es vendible. Empieza
> por el c02.

**CTA:** `/concepto/02-prompts-lcel`
