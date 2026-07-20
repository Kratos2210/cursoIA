# Guion · Ruta 3 — Herramientas y Agentes (7–8 min)

**Se publica en:** c07 · **Demo:** `interrupt()` congelando un agente hasta que un humano aprueba

## Gancho (0:00–0:30)

> Un agente no es magia: es un modelo al que le diste HERRAMIENTAS y un ciclo
> para usarlas. Y la parte que nadie te enseña es la más importante: cómo hacer
> que se DETENGA — porque un agente que puede archivar, borrar o pagar sin
> pedir permiso no es un empleado digital, es un riesgo con API key.

## Qué vas a poder hacer (0:30–1:15)

- Darle herramientas (`@tool`) a un modelo y ver el ciclo ReAct completo: pensar → actuar → observar.
- Construir el grafo a mano con LangGraph: estado, nodos, aristas condicionales, memoria.
- Pausar el agente con `interrupt()` para que un humano apruebe la acción — y reanudarlo días después.
- Conectar herramientas por MCP y coordinar varios agentes con un supervisor.

## Demo (1:15–4:45) — 100% offline, sin gastar cuota

```bash
cd curso_ejemplos
uv run python 13b_human_in_the_loop.py
```

Puntos de guion:
- «Fíjate: el agente PROPONE archivar, y el programa… se congela. No es un bug.
  Es `interrupt()`: el estado quedó guardado en el checkpointer.»
- Aprobar → el grafo despierta EXACTAMENTE donde estaba. «Podrían haber pasado
  tres días. El estado vive fuera del proceso.»
- Correrlo otra vez y RECHAZAR: el agente re-planifica. «Las dos salidas del
  humano son parte del grafo, no un if pegado con cinta.»
- Pantalla partida con el playground del c13 en la web: el mismo ciclo, clicable.

## Recorrido de la ruta (4:45–6:15)

- **c07/c08** herramientas y routing — el vocabulario del agente.
- **c10** el agente prebuilt en 5 líneas; **c13** el mismo agente construido a mano, pieza por pieza.
- **c14** MCP: el USB-C de las herramientas. **c15** patrón supervisor multiagente.
- **c30** memoria de largo plazo: que recuerde ENTRE conversaciones, no solo dentro de una.

## Cierre (6:15–6:45)

> La demo que viste corre sin API key y sin gastar un centavo — y es el
> concepto más importante de agentes en producción. Empieza por el c07.

**CTA:** `/concepto/07-herramientas`
