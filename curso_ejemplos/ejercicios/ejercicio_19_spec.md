# Ejercicio 19 — Escribir un spec de verdad (y correr spec-kit)

**Base:** los Conceptos [19](/concepto/19-spec-driven-development) y [19b](/concepto/19b-spec-de-apps-de-ia)
**Gasta cuota:** no. Escribes texto y corres comandos de spec-kit; ninguno llama a un LLM de pago.
**Referencia / solución:** los artefactos del ejemplo trabajado en
[`../docs/ejemplos-spec/asistente-rag-whatsapp/`](../docs/ejemplos-spec/asistente-rag-whatsapp/)
y la guía [`../docs/guia-spec-para-apps-de-ia.md`](../docs/guia-spec-para-apps-de-ia.md).

> 💡 Este ejercicio no tiene una solución `.py` porque un spec no se ejecuta: se
> revisa. Tu "criterio de aceptación" es la **checklist** de más abajo, la misma
> que usarías antes de pasar un spec real a `/plan`. Leer el método no enseña a
> escribirlo; esto sí.

## Contexto

El asistente de WhatsApp del ejemplo trabajado (bodega Sifrah) lleva dos meses en
producción respondiendo horarios, catálogo y precios. El cliente pide una
**funcionalidad nueva**:

> "Los clientes preguntan mucho si un pedido ya está listo para recoger. ¿Se
> puede que el bot les diga el estado de su pedido?"

Tu trabajo es escribir el spec de esa feature. No es greenfield: la constitución
ya existe, los presupuestos se heredan, y hay un sistema que **no debe romperse**.

## Enunciado

### Parte 1 — El spec de la feature (a mano, siguiendo los seis pasos)

Crea `specs/00X-estado-de-pedido/spec.md` y escríbelo aplicando el método del
Concepto 19b, en este orden:

1. **Las cuatro preguntas.** Quién sufre, qué hace hoy en su lugar, cómo sabremos
   que mejoró, y qué explícitamente **no** vas a hacer (pista: consultar el estado
   ≠ modificarlo).
2. **Una user story P1** con su *Independent Test*. Aplícale el test de
   independencia: si implementas solo esto, ¿tienes algo demostrable?
3. **Requisitos funcionales** con `MUST` + verbo observable. Al menos uno de
   **abstención** (¿qué hace el bot si no encuentra el pedido, o si el número no
   corresponde a quien pregunta?) y uno de **autonomía** (¿consultar el estado es
   autónomo? ¿modificarlo? ¿confirmar la recogida?).
4. **Un criterio de éxito con umbral** sobre un conjunto dorado, y el **delta**
   del golden set: qué casos nuevos añade esta feature (incluidos negativos).
5. **La sección de no-regresión.** Lo que este cambio NO debe empeorar: umbrales
   vigentes, coste por conversación, abstención al 100%.
6. Marca con `[NEEDS CLARIFICATION]` lo que no puedes decidir tú, y en
   `Assumptions` lo que decidiste por defecto.

### Parte 2 — Corre spec-kit sobre tu spec

Con tu `spec.md` escrito, ejecuta los comandos reales y observa qué hace cada uno:

```bash
/speckit-clarify     # ¿qué ambigüedades te destapa que no habías visto?
/speckit-plan        # ¿el modelo y la base de datos aparecen AQUÍ y no en el spec?
/speckit-tasks       # ¿la tarea del golden set queda antes de la implementación?
/speckit-analyze     # ¿algún requisito quedó sin tarea, o alguna tarea sin requisito?
```

Anota, para cada uno, **una** cosa que el comando te obligó a mejorar.

## Predice, antes de correr `/speckit-clarify`

1. Tu spec seguro dejó **al menos una** ambigüedad sin marcar. ¿Cuál crees que es?
   (Pista honesta: casi siempre es "cómo identificamos que el pedido es de quien
   pregunta" — un requisito de privacidad disfrazado de detalle técnico.)
2. ¿`/speckit-clarify` te preguntará sobre eso, o sobre otra cosa que no viste?

## Criterio de aceptación

Tu spec pasa si supera esta checklist (extracto de la guía, sección 5.2):

- [ ] Ningún FR nombra una librería, un proveedor o un modelo (test de la tapadera).
- [ ] La P1 es demostrable por sí sola.
- [ ] Hay al menos un requisito de abstención y uno de autonomía.
- [ ] El criterio de éxito tiene un número y se mide sin abrir el código.
- [ ] El delta del golden set incluye casos negativos.
- [ ] Existe la sección de no-regresión con umbrales concretos.
- [ ] Lo que no sabías decidir está en `[NEEDS CLARIFICATION]`, no adivinado.
- [ ] El spec cabe en dos páginas.

Compara luego tu resultado con
[`spec-feature-citacion.md`](../docs/ejemplos-spec/asistente-rag-whatsapp/spec-feature-citacion.md):
es otra feature sobre el mismo sistema, y te sirve de patrón de **forma** (no de
contenido — tu caso es distinto).

---

## Pistas

<details>
<summary>Pista 1 — la trampa de este caso: no es una feature de "leer datos"</summary>

"Consultar el estado de un pedido" suena inofensivo, pero mete un requisito que
el asistente de horarios no tenía: **datos por cliente**. Horarios y precios son
públicos; el estado de *mi* pedido no. Eso dispara dos requisitos que un spec
descuidado se salta:

- Uno de **abstención por identidad**: el bot no revela el estado de un pedido a
  quien no puede probar que es suyo.
- Uno de **fuga de datos** en los casos de borde: nunca el pedido de otro cliente.

Si tu spec no los tiene, `/speckit-clarify` te los va a sacar a la fuerza.

</details>

<details>
<summary>Pista 2 — dónde está la frontera de autonomía</summary>

Tres acciones, tres peldaños distintos (Concepto 35):

- **Consultar** el estado → autónomo, es solo lectura.
- **Confirmar** que el cliente pasará a recoger → borrador para Rosa, no autónomo.
- **Marcar** el pedido como entregado → jamás el bot; efecto sobre el inventario.

Un solo FR que diga "el bot gestiona pedidos" mezcla los tres y es justo el error
que el spec debe evitar.

</details>

<details>
<summary>Pista 3 — el delta del golden set, no un golden set nuevo</summary>

No rehaces el conjunto dorado: le **añades** los casos de esta feature. Como
mínimo: 2 consultas válidas (pedido existe, es del cliente), 1 negativo de
identidad (pedido de otro), 1 de pedido inexistente, 1 de intención de recogida
(que debe escalar). Y la no-regresión exige correr también los 72 casos que ya
existían — porque tocar el prompt para esto puede romper las respuestas de
horarios.

</details>

---

## Reflexión

Fíjate en lo que acaba de pasar: la feature que el cliente pidió en una frase
—"que diga el estado del pedido"— escondía un requisito de **privacidad** que no
estaba en ninguna parte de esa frase. No lo encontró tu intuición: lo encontró el
**método**, cuando el paso de abstención te obligó a preguntarte "¿y si el número
no es de quien pregunta?".

Eso es para lo que sirve escribir el spec antes del código. No es papeleo: es el
sitio barato donde descubres, en una tarde de texto, el problema que en producción
te habría costado la confianza de un cliente y quizá una multa.
