# ADR-0005 — n8n entra como anexo de integración (revierte el "no n8n")

- **Estado:** aceptado (revierte la decisión informal previa "no n8n en el núcleo")
- **Fecha:** 2026-07-17
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

Al planificar la mejora didáctica (2026-07) se evaluó añadir un módulo de **n8n**
y **se descartó**: el curso enseña a construir el agente **en código** (LangChain
/ LangGraph), y meter una herramienta *low-code* en el núcleo diluía ese objetivo
y arrastraba otra pieza que mantener.

El benchmark contra un competidor de mercado (perfil Datapath) reabrió el tema
desde otro ángulo: allí n8n no es "otra forma de programar el agente", sino el
**pegamento de integración** que conecta el agente (ya construido en código) con
canales y sistemas del negocio (WhatsApp, CRM, hojas, colas) **sin escribir el
plumbing a mano**. Ese encuadre —n8n como orquestador *alrededor* del agente, no
*en lugar* del agente— sí encaja con el curso y es una habilidad de mercado real.

## Decisión

> n8n entra como **anexo opcional de integración** (m31b), **no** como núcleo. El
> agente se sigue construyendo en código (LangChain/LangGraph); n8n solo orquesta
> **alrededor**: recibe el webhook de WhatsApp, llama al `POST /chat` del agente
> (el del `proyecto_llmops`) y devuelve la respuesta al canal. El artefacto es un
> workflow **importable** (`canales/n8n/agente_rag_whatsapp.json`) descrito en el
> módulo; **fuera del gate offline** (n8n es un servicio Docker, no una dependencia
> de Python). Fila "—" en el #mapa.

Esto **revierte** la decisión previa "no n8n", que aplicaba a n8n *como forma de
construir el agente*. Como **capa de integración** el veredicto cambia: sí, pero
periférico y opcional.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **n8n como anexo de integración (orquesta el agente en código)** | Habilidad de mercado; no toca el núcleo; el agente sigue en código | Otra pieza (servicio Docker) a explicar | ✅ **Elegida** |
| n8n como forma de construir el agente | Low-code, rápido de demostrar | Diluye el objetivo del curso (agentes en código); menos control/testeo | Contradice la tesis del curso |
| Seguir sin n8n | Menos superficie | Deja fuera una integración que el mercado pide | El gap de tooling sigue abierto |

## Consecuencias

**Positivas**
- El alumno ve las **dos formas** de conectar el canal: el webhook en código
  (m31, [ADR-0004](0004-canal-whatsapp-fuera-del-gate.md)) y la versión low-code
  con n8n (m31b), y **cuándo conviene cada una**.
- El núcleo del curso **no cambia**: el agente sigue en LangGraph, testeado y
  offline; n8n queda como capa exterior importable.

**Negativas**
- El workflow n8n **no está cubierto por tests** y puede quedar desfasado si n8n
  cambia sus nodos HTTP/Webhook. Se marca como material de lectura.
- Reabre una decisión ya cerrada; por eso queda **documentada como reversión
  explícita** y acotada al rol de integración.

**Cuándo revisar**

Si n8n pasara a usarse para lógica central del agente (no solo pegamento), habría
que reevaluar: eso sí chocaría con la tesis "agentes en código" del curso.
