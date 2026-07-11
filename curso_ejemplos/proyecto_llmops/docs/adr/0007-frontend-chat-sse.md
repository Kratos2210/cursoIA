# ADR-0007 — Frontend de chat: SPA vainilla servida por FastAPI, SSE por fetch

- **Estado:** aceptado
- **Fecha:** 2026-07-10
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El servicio GobData ya hace mucho por dentro —guardrails, caché semántico,
tracing, métricas, A/B de prompts con feedback 👍/👎 (ver ADR-0006)— pero todo
eso solo se toca por `curl`. Le falta una cara: una página donde escribir una
pregunta, ver la respuesta aparecer **token a token** y votar si sirvió.

Esa página tiene una restricción dura de este curso: **cero dependencias
nuevas**. Nada de build, nada de framework, nada de CDN. Y una técnica: el
endpoint `POST /chat` responde en **streaming SSE** (ver `app/streaming.py`), y
la API cómoda del navegador para SSE, `EventSource`, **solo hace GET** y no deja
mandar cuerpo. Nuestro `/chat` es POST con un JSON (`mensaje`, `rol`,
`thread_id`), así que la vía fácil no aplica.

## Decisión

> **Una SPA vainilla (HTML+CSS+JS en un solo archivo) servida por el propio
> FastAPI.** El HTML vive en `app/static/chat.html`; `app/frontend.py` lo lee
> **una vez** al importar y lo expone como `PAGINA_CHAT`; la ruta `GET /` lo
> devuelve envuelto en un `HTMLResponse`. Sin build, sin framework, sin CDN: la
> página abre en un navegador sin conexión a internet.
>
> **El stream SSE se consume con `fetch` + `ReadableStream`**, no con
> `EventSource`. Se lee `response.body.getReader()`, se decodifica con
> `TextDecoder`, se acumula en un buffer y se parte por la línea en blanco
> (`\n\n`) que separa eventos; el trozo sin cerrar se retiene para la siguiente
> lectura. El parser reconoce los tres eventos de `app/streaming.py`: token por
> defecto (append a la burbuja), `fin` (captura la `variante` y muestra 👍/👎) y
> `bloqueado`/`error` (pinta el error).

**Por qué leer el HTML una vez y no en cada request.** El archivo no cambia
mientras el proceso vive: releerlo del disco por cada `GET /` sería E/S por nada.
Se carga al importar y queda en memoria. El precio —editar el HTML no se refleja
sin reiniciar— no existe en desarrollo: el `--reload` de uvicorn re-importa el
módulo al detectar el cambio, y la relectura vuelve a ocurrir. Como bonus,
`PAGINA_CHAT` es un simple string importable **sin levantar la app**, así un test
puede afirmar su contenido sin un TestClient.

**Por qué no un framework ni un paso de build.** Un React/Vue traería
`node_modules`, un bundler y un artefacto que servir: rompe el "cero
dependencias" y multiplica por diez la superficie para una página que es un
formulario y un parser. El coste no compra nada aquí.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **SPA vainilla + fetch/ReadableStream** | Cero deps; abre offline; consume un POST-SSE; `PAGINA_CHAT` testeable como string | El parser SSE se escribe a mano (buffer + `\n\n`) | ✅ **Elegida** |
| `EventSource` + GET | API nativa, reconexión automática | Solo GET, sin cuerpo ni cabeceras: obligaría a volver `/chat` un GET con la pregunta en la query | No encaja con un POST con JSON |
| WebSocket | Bidireccional, framing por mensajes | El flujo es de una sola dirección (servidor→cliente); una conexión de ida y vuelta para no usar la vuelta; más infra | Sobredimensionado para SSE |
| Framework SPA con build (React/Vue) | Ergonomía, componentes | `node_modules`, bundler, artefacto; rompe "cero deps" | Coste enorme para un formulario |
| `StaticFiles` / `FileResponse` | Estándar de Starlette para servir estáticos | Monta E/S por request o un subárbol entero; el HTML deja de ser un string importable sin app | Innecesario para un único archivo cacheable en memoria |

## Consecuencias

**Positivas**
- **Cero dependencias nuevas**: solo FastAPI/Starlette, que ya estaban. La
  página es HTML+CSS+JS en un archivo y abre sin internet.
- La página se sirve **desde el mismo origen** que la API, así que `fetch("/chat")`
  y `fetch("/feedback")` no necesitan CORS en la demo.
- `frontend.PAGINA_CHAT` es un **string importable sin levantar nada**: los tests
  (`tests/test_frontend.py`) afirman su contenido y la autocontención sin red.
- **Aditivo**: solo aparece una ruta `GET /`; `/health`, `/metrics`, `/chat` y
  `/feedback` no se tocan y sus tests siguen en verde.
- Cierra visualmente el lazo del A/B (ADR-0006): el front captura la `variante`
  del evento `fin` y la devuelve en el voto.

**Negativas / limitaciones** (las decimos en voz alta)
- **La demo se sirve abierta**: sin auth y sin CORS explícito. Funciona porque es
  el mismo origen y un entorno de curso. En producción va **detrás de auth**, del
  **mismo origen** (o CORS bien acotado), y `/metrics` **no** se expone público.
- **El `rol` sigue viajando en el body** (el mismo aviso que `main.py`): un rol
  que elige el cliente vuelve el RBAC decorativo. En producción se deriva del
  token de auth, no del selector de la página.
- **El feedback sigue en memoria y por proceso** (heredado del ADR-0006): los
  votos que manda el front se pierden al reiniciar y no se agregan entre workers.
- El **parser SSE es propio**: no maneja `id:`/`retry:` ni reconexión (no los
  usamos). Si el formato de `app/streaming.py` creciera, el parser habría que
  ampliarlo a mano.
- Editar `chat.html` **no se refleja sin reiniciar** el proceso (se lee una vez);
  en desarrollo el `--reload` de uvicorn lo resuelve re-importando el módulo.

**Cuándo revisar esta decisión**
1. Cuando el front deba salir a **producción** → poner auth, fijar CORS/mismo
   origen y dejar de exponer `/metrics` público.
2. Cuando la UI crezca más allá de un formulario (historial, adjuntos, múltiples
   vistas) → replantear si compensa un framework con build.
3. Cuando `app/streaming.py` añada campos SSE nuevos (`id:`, `retry:`) o un
   segundo endpoint en streaming → factorizar el parser a un módulo reutilizable.
