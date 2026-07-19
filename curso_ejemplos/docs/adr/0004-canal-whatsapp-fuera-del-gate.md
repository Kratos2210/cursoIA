# ADR-0004 — El canal de WhatsApp vive fuera del gate offline

- **Estado:** aceptado
- **Fecha:** 2026-07-17
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El curso enseña a construir el **agente** (m10–m15) y a servirlo por **HTTP**
(m17, m25). Un currículo comparable de mercado (perfil Datapath, 72 h) llega un
paso más allá: pone el agente en un **canal real de mensajería** —WhatsApp— para
que el alumno vea el sistema end-to-end, no solo el `POST /chat`. La auditoría de
tooling 2026-07 lo marcó como gap: "el concepto está, falta el hands-on de
integración".

Poner un agente en WhatsApp necesita tres cosas que **rompen la constitución
offline-first** del repo (todo ejemplo corre en la CI sin red, sin cuota y en
segundos):

- Un puente a WhatsApp (**EvolutionAPI**) que solo existe como **contenedor
  Docker** con estado (sesión del número, QR).
- Un **número de WhatsApp** real y una **API key de LLM** con cuota.
- Un webhook público que WhatsApp/EvolutionAPI puedan llamar.

Meter esto en `tests/` y en el gate offline lo volvería imposible de correr en la
CI y frágil para cualquiera que solo quiera la parte conceptual.

## Decisión

> El canal de WhatsApp vive en `canales/whatsapp/` (webhook FastAPI +
> `docker-compose.yml` + `.env.example`) y en un **módulo de lectura** (m31),
> **fuera** del gate offline. Sus únicas dependencias (`fastapi`, `uvicorn`,
> `httpx`) van en un **extra opcional** `whatsapp` de `pyproject.toml`; la CI
> corre `uv sync --extra dev`, así que **no lo instala**. No se testea y su fila
> en el #mapa lleva "—".

El **agente no cambia**: el webhook lo recibe **por parámetro** (`responder`),
igual que en todo el curso el modelo se inyecta. El canal es una capa exterior
enchufable, no una reescritura del núcleo.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Anexo fuera del gate (`canales/`, extra `whatsapp`)** | Enseña la integración real; cero impacto en deps/CI del resto | No corre en la CI; necesita Docker + número | ✅ **Elegida** |
| Añadir el canal al núcleo y testearlo | Coherente con el resto | Imposible sin Docker/red/número en la CI; frágil | Rompe la constitución para todos |
| Simular WhatsApp con un doble offline | Testeable | Un WhatsApp "de mentira" no enseña el hands-on de integración que se pide | No cumple el objetivo |
| No cubrirlo | Cero trabajo | El gap de canal real sigue abierto | No enseñar no es una opción |

## Consecuencias

**Positivas**
- El alumno pone su agente en un **canal real** sin tocar el núcleo ni el entorno
  del resto del curso: `uv run pytest -m offline` sigue verde sin Docker.
- El punto de extensión `responder(texto, thread_id)` deja claro cómo enchufar el
  agente RAG del `proyecto_llmops` o el `create_react_agent` del m10.

**Negativas** (hay que decirlas)
- El canal **no está cubierto por tests**: puede quedar desactualizado si cambia
  la API de EvolutionAPI. Se marca como material de lectura, con la imagen Docker
  *pineable* a una versión concreta en producción.
- Introduce una **segunda categoría** de material ("fuera del gate", como el
  [ADR-0003](0003-notebook-lora-fuera-del-gate.md)) que hay que señalizar (fila
  "—" en el #mapa).

**Cuándo revisar**

Cuando el repo tenga un entorno con Docker preprovisionado donde levantar
EvolutionAPI sea el flujo por defecto; ahí el webhook podría ganar un smoke test
con un doble de EvolutionAPI en vez de la API real.
