# ADR-0011 — Arquitectura de software y hosting (VPS) son contenido web, fuera del gate

- **Estado:** aceptado
- **Fecha:** 2026-07-19
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

Una revisión del temario contra el ciclo de vida real de un producto de software
dejó dos huecos, confirmados por una auditoría de cobertura del contenido web:

- **Dónde se aloja el proyecto:** el c15b enseña la *topología* (microservicios,
  K8s, serverless) y el c17c (ADR-0010) asume un VPS *ya existente* — su
  `deploy.yml` hace SSH a `secrets.VPS_HOST` y ejecuta `cd /srv/gobdata` — pero
  ningún módulo explica de dónde sale ese servidor. Cero menciones en todo el
  curso de reverse proxy, dominio/DNS, TLS/Let's Encrypt, firewall o
  aprovisionamiento, y ninguna comparación VPS vs PaaS vs contenedor gestionado.
- **Arquitectura de software:** el alumno ejecuta `proyecto_llmops`, que es un
  **monolito modular** FastAPI (un proceso; paquetes `app/`, `guardrails/`,
  `observability/`, `cache/`, `evals/`, `prompts/` con dependencias en una
  dirección), pero ningún módulo lo describe como arquitectura; el c15b dibuja
  microservicios idealizados que no coinciden con el código real. Tampoco
  existía frontend/backend como capas con contrato de API, monolito vs
  microservicios como decisión, ni el SDLC como marco (el c19 cubre solo SDD).

Ambos son contenido conceptual y operativo, no código nuevo. Aprovisionar un
VPS real exigiría una cuenta con billing y secrets en el repo (`gh secret list`
sigue vacío), lo que rompe la constitución offline-first — el mismo veto que ya
motivó el ADR-0010.

## Decisión

> Dos **módulos core** de la Ruta 6, solo en `web/content/`, sin artefactos
> Python nuevos y sin dependencias:
>
> - `modules/15a-arquitectura-de-software.mdx` — antes del 15b. Su ejemplo
>   trabajado es el propio `proyecto_llmops`: no añade código, enseña a **leer
>   el que ya existe** (capas, contrato de API, dirección de imports —
>   verificada contra el código real: `guardrails/` no importa nada de `app/`;
>   el resto solo comparte `app.config`).
> - `modules/15c-donde-vive-tu-agente.mdx` — entre 15b y 17c. El mapa de
>   decisión VPS/PaaS/contenedor gestionado/serverless y la ruta VPS completa
>   (SSH, firewall, Docker, DNS, TLS con Caddy, `/srv/gobdata`). Los comandos,
>   el Caddyfile y el compose van como **listados comentados dentro del MDX**
>   (patrón ADR-0010): archivos reales serían código muerto sin servidor
>   destino. Sus nombres (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`,
>   `/srv/gobdata`, `gobdata.example.com`) casan literalmente con el
>   `deploy.yml` del 17c, que con esto gana su "mundo al otro lado del SSH".

El gate offline **no cambia**. Los precios de proveedores (Hetzner, DO, EC2,
Railway, Render, Fly.io, Cloud Run, dominio) fueron **verificados contra las
páginas oficiales el 2026-07** y se marcan como caducables, igual que la tabla
del c18b.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Contenido web con listados comentados** | Cierra ambos huecos sin deuda de infra ni deps | El alumno sin ~4 €/mes aprende el diseño, no la ejecución | ✅ **Elegida** |
| Scripts reales de aprovisionamiento (cloud-init/Terraform en el repo) | Ejecutable de verdad | Código muerto sin cuenta destino; nadie lo mantiene en verde | Mantener IaC que nunca corre confunde más que enseña |
| VPS de demostración del curso | El 15c y el deploy.yml del 17c serían reales | Coste recurrente + secrets en la CI; rompe offline-first | Mismo veto que en ADR-0010 |
| Anexos opcionales en vez de módulos core | Menor compromiso | El hosting y la arquitectura son el hueco central del eslogan "de cero a producción" | Un anexo dice "esto es periferia", y no lo es |

## Consecuencias

**Positivas**
- Se cierra la pregunta "¿y de dónde sale el servidor?" que el 17c dejaba
  abierta, y sus tres secrets ganan sentido anticipado.
- El código que el alumno ya corre queda por fin descrito como arquitectura, y
  la aparente contradicción "el 15b enseña microservicios pero corres un
  monolito" se convierte en lección explícita (la secuencia correcta, no un
  descuido).
- La ruta 6 queda con una narrativa completa: diseño (15a) → topología (15b) →
  sustrato (15c) → cinta de CD (17c).

**Negativas**
- Los precios y las UIs de los proveedores caducan. Mitigado: fecha de consulta
  visible y orden de magnitud en vez de céntimos.
- El paso a paso del VPS no se ejecuta ni se testea en CI. Mitigado: es la misma
  clase de listado comentado que el `deploy.yml` del 17c, y el módulo lo declara.

**Cuándo revisar**

El mismo disparador que ADR-0010: si el curso adopta un VPS de demostración, el
paso a paso del 15c se convierte en script ejecutable (o cloud-init), el
`deploy.yml` del 17c en workflow real, y ambos ganan un smoke test contra un
despliegue de verdad.
