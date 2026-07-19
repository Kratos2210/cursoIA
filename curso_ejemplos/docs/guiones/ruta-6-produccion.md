# Guion · Ruta 6 — Producción y LLMOps (8–10 min)

**Se publica en:** c17 · **Demo:** el stack LLMOps completo levantando en Docker + smoke test

## Gancho (0:00–0:30)

> Tu agente funciona en tu laptop. Felicitaciones: eso es el 30% del trabajo.
> El otro 70% se llama producción: que aguante usuarios, que no queme la
> tarjeta, que avise cuando miente y que otro humano pueda operarlo sin
> llamarte un domingo. Esta es la ruta que convierte «sé LangChain» en «soy
> AI Engineer» — y es la más larga del curso porque es la que te contratan.

## Qué vas a poder hacer (0:30–1:30)

- Estructurar un repo que otro pueda operar: runbook, ADRs, inyección de dependencias.
- Testear IA sin gastar cuota (los cientos de tests offline de este repo como ejemplo vivo) y colgarlos de CI.
- Servir el agente por HTTP con streaming SSE, observarlo (tokens, coste, trazas) y evaluarlo con gate.
- Desplegar con Continuous Delivery: tag → build → deploy → smoke test → rollback — y saber DÓNDE vivirá (VPS, PaaS, nube).

## Demo (1:30–5:30)

```bash
cd curso_ejemplos
docker compose -f proyecto_llmops/docker-compose.yml --profile app up -d --build
SMOKE_URL=http://localhost:8000 uv run pytest \
    proyecto_llmops/tests/test_smoke_despliegue.py -v
```

Puntos de guion:
- Mientras levanta: enseñar el stack en el compose (FastAPI + Postgres/pgvector + Redis + Langfuse). «Esto no es un hello world: es el mismo stack que una empresa chica de verdad.»
- Smoke en verde: «estos tests le pegan al contenedor DE VERDAD, por fuera. Los unitarios no ven config rota; el smoke sí.»
- Romperlo: llave de Langfuse falsa → smoke en ROJO. «Este rojo es el pipeline
  impidiendo que un contenedor mentiroso llegue a producción. Esto es CD.»

## Recorrido de la ruta (5:30–7:30)

- **c17** repo productivo · **c15a/b/c** arquitectura y dónde vive tu agente (VPS→PaaS→nubes grandes).
- **c17b/c17c** tests+CI y Continuous Delivery (lo del smoke). **c16/c16c** observabilidad, coste y evaluación con gate.
- **c23** seguridad y red-teaming OWASP. **c24b** feedback 👍/👎 y A/B. **c25** frontend SSE.
- **c31/c31b** canal WhatsApp y n8n. **c34** Bedrock/Vertex: la nube gestionada.

## Cierre (7:30–8:00)

> Todo lo que viste corre en este repo, con sus tests y sus ADRs — no es un
> diagrama de conferencia. Empieza por el c17 y termina desplegando de verdad.

**CTA:** `/concepto/17-repo-productivo`
