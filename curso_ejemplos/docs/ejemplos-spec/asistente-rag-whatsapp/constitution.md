# Constitución del proyecto: Asistente de atención por WhatsApp

**Cliente**: Bodega Sifrah (PyME, Lima) · **Version**: 1.0.0 · **Ratified**: 2026-07-20

> Documento de **ejemplo** para la [guía de specs para apps de IA](../../guia-spec-para-apps-de-ia.md).
> Es realista y completo, pero el cliente es ficticio.

Los principios que siguen están **por encima de cualquier feature**. Una historia de usuario
que los contradiga se rechaza o exige enmendar esta constitución primero.

---

## Core Principles

### I. Ninguna afirmación factual sin fuente

Toda respuesta que contenga un dato del negocio —precio, stock, horario, plazo, política— debe
poder rastrearse hasta un documento concreto del corpus, y la respuesta debe nombrarlo. Si el
dato no está en el corpus, el sistema no lo dice: se abstiene.

**Rationale:** el valor entero de este sistema frente a "preguntarle a un chatbot cualquiera"
es que lo que afirma se puede verificar. Una respuesta sin fuente es indistinguible de una
alucinación, y basta que el cliente descubra **una** para que deje de confiar en todas las
demás. La trazabilidad no es una feature de calidad: es la razón de existir del producto.

### II. Techo de coste por conversación

El coste medio por conversación resuelta no supera **USD 0.03**. Ninguna feature puede romper
ese techo; si una lo necesita, se renegocia el techo con el cliente **antes** de construirla,
no después.

**Rationale:** el margen de una bodega por venta es de unos pocos soles. Un asistente que
cueste más que el margen que ayuda a capturar es un pasivo con buena demo. Fijar el techo
antes de diseñar elimina arquitecturas caras temprano, cuando descartarlas es gratis; fijarlo
después obliga a desmontar lo ya construido.

### III. Ninguna feature está terminada sin su medición

Una funcionalidad se considera hecha cuando existe su caso en el conjunto dorado, la
evaluación corre automáticamente y supera el umbral acordado. "Funciona, lo probé a mano" no
cuenta como terminado.

**Rationale:** en un sistema no determinista, probar tres veces a mano no dice nada — puede
fallar la cuarta y nadie se entera. La eval es a este proyecto lo que la suite de tests a un
proyecto normal: la única definición de "listo" que sobrevive al día siguiente.

### IV. Los datos del cliente no salen más de lo imprescindible

Los mensajes de los clientes se envían al proveedor del modelo solo para producir la respuesta,
con retención cero contratada. No se usan datos personales para entrenar nada. Los números de
teléfono se almacenan seudonimizados y no se incluyen nunca en prompts ni en registros de
depuración.

**Rationale:** la bodega no tiene equipo legal, y confía en nosotros para no meterla en un
problema. Un incidente de privacidad no lo paga el proveedor del modelo: lo paga la relación
del cliente con su barrio.

### V. Degradación explícita: el sistema falla diciendo que falla

Ante duda, error, caída del proveedor o pregunta fuera de alcance, el sistema responde que no
puede ayudar y ofrece contacto humano. Nunca improvisa, nunca responde a medias, nunca calla.

**Rationale:** el peor resultado posible no es que el asistente no sepa — es que el cliente
crea que sí sabía. Una respuesta inventada destruye más confianza que diez "déjame pasarte con
Rosa", y además nadie la detecta hasta que ya hizo daño.

---

## Restricciones del proyecto

- **Sin escritura en sistemas del negocio**: el asistente lee catálogo y políticas; no crea
  pedidos, no modifica stock, no cobra. Cualquier acción con efecto externo pasa por aprobación
  humana.
- **Corpus versionado**: los documentos que alimentan el sistema viven en un repositorio con
  historial. Un cambio de corpus es un cambio auditable, con responsable.
- **Español peruano**: el sistema responde en el registro que usan los clientes de la bodega,
  no en español neutro de manual.
- **Observabilidad mínima**: toda conversación queda registrada con la pregunta, la respuesta,
  las fuentes recuperadas y el coste. Sin eso no se puede diagnosticar nada.

## Flujo de trabajo y puertas de calidad

1. **Constitution → /specify → /clarify → /plan → /tasks → /implement**, en ese orden.
2. **Puerta de evals**: ninguna entrega llega a producción sin que el conjunto dorado supere
   sus umbrales, incluidos los casos negativos al 100%.
3. **Puerta de presupuesto**: cada entrega reporta el coste medido por conversación.
4. **Puerta de constitución**: el plan incluye un Constitution Check con los cinco principios;
   toda desviación se justifica por escrito o se rechaza.
5. **Cambio de modelo o de prompt = corrida completa del conjunto dorado** antes de aceptar.

## Governance

Enmendar esta constitución exige editar este archivo, registrar el motivo y revisar que los
specs vigentes sigan cumpliéndola.

- **MAJOR**: se elimina o redefine un principio de forma incompatible.
- **MINOR**: se añade un principio o una sección.
- **PATCH**: aclaraciones de redacción sin cambio de fondo.
