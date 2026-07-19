# ADR-0010 — CD, nube gestionada y la guía "0→producción" son contenido web, fuera del gate

- **Estado:** aceptado
- **Fecha:** 2026-07-19
- **Decide:** Alberto Ruiz (autor del curso)

## Contexto

El benchmark de mercado dejó tres huecos en el temario, confirmados por una
auditoría del contenido:

- **Continuous Delivery/Deployment (CD):** el curso enseña CI a fondo (m17b +
  `ci.yml`/`eval-gate.yml` reales) pero el despliegue es manual. El propio
  informe `docs/auditoria-produccion-2026-07.md` §7 lista el CD como Fase 3 no
  hecha. No hay pipeline de deploy, ni canary/blue-green, ni rollback automático.
- **Desplegar productivo en la nube gestionada:** el m18b cubre *elegir* Bedrock
  o Vertex a nivel de proveedor, pero no *operarlo* (identidad IAM, red privada,
  model access, cuotas, guardrails nativos, dónde corre el contenedor).
- **Guía "de cero a producción":** es el eslogan del curso, pero el roadmap solo
  existía como auditoría interna, no como una guía orientada al alumno.

Los tres son **contenido conceptual y operativo**, no código nuevo. Un pipeline
de CD real necesitaría un VPS destino y secretos (`gh secret list` está vacío);
desplegar en Bedrock/Vertex necesitaría una cuenta cloud con billing. Ninguna de
las dos cosas encaja en la constitución offline-first del repo ni en su CI.

## Decisión

> Los tres añadidos viven **solo en la web** (`web/content/`), sin artefactos
> Python nuevos y sin dependencias nuevas en `pyproject.toml`:
>
> - `modules/17c-continuous-delivery.mdx` — **módulo core** de la Ruta 6, tras
>   `15b`. El workflow `deploy.yml` es un **listado comentado dentro del MDX**;
>   no se crea `.github/workflows/deploy.yml` real (sería código muerto: no hay
>   VPS ni secrets). Reutiliza narrativamente el `eval-gate.yml` y el
>   `proyecto_llmops/tests/test_smoke_despliegue.py` que **sí** existen.
> - `modules/34-desplegar-en-bedrock-y-vertex.mdx` — **anexo opcional**
>   `tested:false`, con los snippets de `langchain-aws` y `langchain-google-vertexai`
>   como **código de referencia** (no se añaden esos paquetes a las deps).
> - `extras/de-cero-a-produccion.mdx` — **recurso de cierre** transversal que
>   enlaza los módulos en 6 fases; reusa el esqueleto del roadmap de la auditoría.

El gate offline **no cambia**: no hay tests nuevos, ni imports nuevos, ni un
workflow que la CI deba correr. Los ids de modelo de Bedrock/Vertex son
**placeholders verificables** (consultados contra la doc oficial de LangChain el
2026-07-19) y se marcan como caducables, igual que la tabla de precios del m18b.

## Alternativas consideradas

| Opción | A favor | En contra | ¿Por qué no? |
|--------|---------|-----------|--------------|
| **Contenido web, YAML y snippets dentro del MDX** | Cierra los tres gaps sin deuda de mantenimiento ni infra | El alumno no ejecuta el pipeline ni la nube sin cuenta | ✅ **Elegida** |
| `deploy.yml` real (workflow_dispatch) | Se ve en el repo de verdad | Código muerto: sin VPS ni secrets, nunca corre; hay que explicar por qué | Mantener un workflow que no se dispara confunde más que enseña |
| Añadir `langchain-aws`/`vertexai` a un extra y testearlo | Coherente con otros extras | Exige cuenta cloud con billing en la CI; rompe offline-first | No hay forma de correrlo sin credenciales de pago |
| Dejar el roadmap solo en la auditoría | Cero trabajo | El alumno nunca lo ve; el eslogan "0→prod" queda sin mapa | El valor era justo llevarlo al alumno |

## Consecuencias

**Positivas**
- Se cierran los tres huecos del benchmark con **cero código nuevo** y cero
  dependencias: nada que mantener en verde, nada que la CI deba instalar.
- El módulo 17c le da sentido retroactivo al `eval-gate.yml` ("puede vetar un
  deploy") y al smoke test de despliegue, que hasta ahora no tenían un deploy
  que proteger.
- La guía de cierre convierte el eslogan del curso en un artefacto accionable.

**Negativas**
- El pipeline de CD y los snippets de nube **no se ejecutan ni se testean**:
  pueden desfasarse si GitHub Actions o los SDKs de `langchain-aws`/`vertexai`
  cambian su API. Mitigado marcándolos como referencia con ids/versiones
  verificables.
- El alumno sin VPS ni cuenta cloud aprende el **diseño**, no la ejecución. Es
  explícito en ambos módulos.

**Cuándo revisar**

Si el curso adoptara un VPS de demostración (o un entorno cloud de laboratorio
con billing acotado), el 17c podría ganar un `deploy.yml` real con
`workflow_dispatch` y el anexo 34 un smoke test contra un despliegue de prueba.
