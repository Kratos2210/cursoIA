# canales/ — ponerle un canal real al agente (WhatsApp y n8n)

El curso construye el agente (m10–m15) y lo sirve por HTTP (m17/m25). Este anexo
le pone delante un **canal de mensajería**: el agente no cambia, solo cambia por
dónde entra y sale el texto.

```
WhatsApp ──▶ EvolutionAPI ──▶ webhook FastAPI ──▶ responder(texto) ──▶ agente
                                    │                                     │
                                    └──── enviar_whatsapp(reply) ◀────────┘
```

| Carpeta | Qué es | Espejo en el curso |
|---|---|---|
| `whatsapp/` | webhook FastAPI para EvolutionAPI (`webhook.py`) + `Dockerfile` + `docker-compose.yml` + `.env.example`. El "cerebro" entra por parámetro (`responder`), igual que el modelo se inyecta en todo el curso. | m31 (web), m17/m25 |
| `n8n/` | `agente_rag_whatsapp.json`: el MISMO flujo, orquestado en n8n en vez de código — se importa desde la UI de n8n (Workflows → Import from File). | m31b (web) |

## Cómo se corre

```bash
# vía local
uv run --extra whatsapp uvicorn canales.whatsapp.webhook:app --port 8080

# o todo junto (EvolutionAPI + webhook)
docker compose -f canales/whatsapp/docker-compose.yml up
```

Necesita Docker (EvolutionAPI), un número de WhatsApp y una API key de LLM.
Copia `whatsapp/.env.example` y rellénalo antes de levantar nada.

## Por qué está fuera del gate offline

Decidido en [ADR-0004](../docs/adr/0004-canal-whatsapp-fuera-del-gate.md) (canal
WhatsApp) y [ADR-0005](../docs/adr/0005-n8n-orquestacion-anexo.md) (n8n como
anexo de orquestación): dependen de servicios externos con estado (WhatsApp,
Docker, n8n) y no corren en la CI. La mecánica testeable (servir el agente por
HTTP) vive en m17/m25.
