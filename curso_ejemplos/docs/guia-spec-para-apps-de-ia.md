# Guía: escribir el spec de una aplicación de IA

> Documento de trabajo. El [Concepto 19](../../web/content/modules/19-spec-driven-development.mdx)
> explica **qué es** Spec-Driven Development y por qué el spec gana sobre el código. Esta guía
> resuelve la pregunta siguiente: **cómo se redacta uno**, y qué cambia cuando el sistema que
> especificas tiene un modelo de lenguaje dentro.
>
> Ejemplo trabajado completo en [`ejemplos-spec/asistente-rag-whatsapp/`](ejemplos-spec/asistente-rag-whatsapp/).

---

## Índice

1. [El método de redacción](#1-el-método-de-redacción)
2. [Qué cambia cuando el sistema es de IA](#2-qué-cambia-cuando-el-sistema-es-de-ia)
3. [Desde cero vs. feature acotado](#3-desde-cero-vs-feature-acotado)
4. [Ejemplo trabajado](#4-ejemplo-trabajado)
5. [Antipatrones, checklist y cómo conducirlo con un asistente](#5-antipatrones-checklist-y-cómo-conducirlo-con-un-asistente)

---

## 1. El método de redacción

Esta sección vale para cualquier software, con IA o sin ella. Es el andamiaje sobre el que la
sección 2 monta lo específico de los modelos.

La plantilla de referencia es [`.specify/templates/spec-template.md`](../../.specify/templates/spec-template.md),
y el ejemplo determinista contra el que conviene contrastar todo es
[`specs/001-verificador-curso/spec.md`](../../specs/001-verificador-curso/spec.md).

### 1.1. De idea difusa a spec: las cuatro preguntas

Un cliente nunca llega con un spec. Llega con una frase: *"quiero un bot que responda a mis
clientes por WhatsApp"*. Entre esa frase y un documento verificable hay cuatro preguntas, y
conviene hacerlas en este orden porque cada una acota a la siguiente.

**¿Quién sufre hoy, y cuánto?**
No "los clientes" en abstracto. Una persona concreta con un problema medible: *"Rosa, la
encargada, contesta 40 mensajes al día repitiendo horarios y precios; los fines de semana
tarda hasta 6 horas en responder y pierde ventas"*. Si no puedes nombrar a quien sufre, no
tienes un problema — tienes una idea.

**¿Qué hace hoy en su lugar?**
Siempre existe un proceso actual, aunque sea manual y malo. Describirlo te da tres cosas
gratis: la línea base contra la que medirás, los casos reales que alimentarán tus pruebas, y
la lista de excepciones que el proceso manual absorbe sin que nadie las haya escrito nunca.
Este paso es el *discovery*, y en el curso vive en el
[Concepto 35](../../web/content/modules/35-discovery-de-procesos.mdx): la spec empieza donde
el discovery termina.

**¿Cómo sabremos que mejoró?**
La respuesta tiene que ser un número que alguien pueda medir sin abrir el código. *"Rosa
responde menos de 10 mensajes al día a mano"* sirve. *"El bot funciona bien"* no sirve, y la
diferencia entre ambas frases es la diferencia entre un spec y un deseo.

**¿Qué explícitamente NO vamos a hacer?**
La sección más barata de escribir y la que más discusiones evita tres semanas después. Si no
escribes que no vas a cerrar ventas, alguien asumirá que sí.

> **Regla:** si no puedes contestar las cuatro, no te falta tiempo de redacción — te falta
> una conversación con el cliente. Escribir el spec sin ellas es inventar el problema.

### 1.2. User stories: el test de independencia

La plantilla pide historias priorizadas (P1, P2, P3…), y la prioridad no es un adorno de
gestión. La regla real es más dura de lo que parece:

> Si implemento **solo la P1** y nada más, ¿tengo algo demostrable a un cliente?

Si la respuesta es "no, porque falta la P2", la P1 está mal cortada. El error clásico es
cortar por **capas técnicas** en lugar de por **valor**:

| Corte malo (por capa) | Corte bueno (por valor) |
|---|---|
| P1: montar la base de datos vectorial | P1: responde preguntas de horarios citando la fuente |
| P2: conectar el modelo | P2: responde también sobre precios del catálogo |
| P3: conectar WhatsApp | P3: escala a Rosa cuando no sabe |

Con el corte malo, después de la P1 no tienes nada que enseñar y no has aprendido nada. Con
el bueno, después de la P1 ya sabes si la idea entera funciona, porque atravesaste el sistema
de punta a punta por la rebanada más fina posible.

Cada historia lleva su **Independent Test** escrito en la propia historia: cómo se comprueba
esa historia sola. Si no sabes escribirlo, la historia no es independiente.

### 1.3. Requisitos funcionales: `MUST` + verbo observable

Un FR bien escrito tiene tres propiedades: usa `MUST`, describe algo **observable desde
fuera**, y no nombra ninguna tecnología.

```
✅ FR-003: El sistema MUST citar, en cada respuesta sobre precios, el documento
           y la fecha de la que salió el dato.

❌ FR-003: El sistema MUST usar pgvector con embeddings de 1536 dimensiones
           para recuperar los precios.
```

El segundo no es un requisito: es una decisión de implementación que se coló hacia arriba. Y
cuando una decisión técnica vive en el spec pasan dos cosas malas. Primero, la cierras antes
de haber investigado — el `/plan` ya no puede evaluar alternativas porque el spec se las
prohibió. Segundo, el día que cambies de vector store tendrás que editar el spec, y un spec
que cambia por razones técnicas deja de ser la fuente de verdad del negocio.

> **El test rápido:** tapa la palabra que nombra la tecnología. Si el requisito pierde
> sentido, estaba mal escrito. "MUST citar el documento y la fecha" sobrevive a cualquier
> stack; "MUST usar pgvector" no dice qué gana el usuario.

### 1.4. Criterios de éxito: medibles y agnósticos

Los FR describen **comportamiento**; los criterios de éxito describen **resultado**. Se
confunden constantemente. Un FR dice qué hace el sistema; un SC dice cómo sabrás, dentro de
un mes, si valió la pena construirlo.

```
FR-005: El sistema MUST responder en menos de 5 segundos.        ← comportamiento
SC-002: El 80% de las consultas de fin de semana se resuelven
        sin intervención de Rosa, medido sobre 4 semanas.        ← resultado
```

Un SC que no se puede medir sin leer el código está mal escrito. Un SC que menciona una
librería está peor.

### 1.5. `[NEEDS CLARIFICATION]` y `Assumptions`: dónde va lo que no sabes

Estas dos secciones son la válvula de escape del método, y usarlas bien es la diferencia
entre un spec honesto y uno que finge saberlo todo.

- **`[NEEDS CLARIFICATION]`** marca lo que **no puedes decidir tú**: reglas de negocio, límites
  legales, quién aprueba qué. Va inline, dentro del requisito afectado, para que sea imposible
  implementarlo sin verlo. Se resuelve preguntando, no adivinando.

- **`Assumptions`** registra lo que **decidiste por defecto** porque nadie lo especificó y el
  trabajo no podía esperar. No es lo mismo que no saberlo: es saber que elegiste, y dejar
  constancia para que quien discrepe pueda discrepar con algo concreto.

El spec del verificador lo hace bien: su sección
[`Assumptions`](../../specs/001-verificador-curso/spec.md) documenta cuatro decisiones que la
descripción original dejaba abiertas ("los 7 defaults" se refiere a *esta* tabla concreta,
"DOCTYPE" se compara sin distinguir mayúsculas…). Ninguna era obvia; todas están escritas.

---

## 2. Qué cambia cuando el sistema es de IA

Aquí está el contenido real de esta guía. Todo lo anterior sigue aplicando, pero un sistema
con un LLM dentro rompe un supuesto que la plantilla de spec-kit da por sentado: **que el
mismo input produce el mismo output, y que "correcto" es una propiedad binaria**.

El verificador del curso es determinista: un `href="#x"` sin su `id="x"` está roto, siempre,
en todas las ejecuciones. Un asistente que responde sobre un catálogo no tiene esa propiedad.
La misma pregunta puede dar dos redacciones distintas, ambas correctas; o una correcta y una
sutilmente inventada. Ocho desplazamientos se siguen de ahí.

### 2.1. El criterio de aceptación deja de ser booleano

Un `Given/When/Then` con resultado exacto no se puede escribir para "responde bien". Esto es
inútil:

```
❌ Given un cliente pregunta "¿a qué hora abren?",
   When el asistente responde,
   Then responde "Abrimos de 9am a 6pm".
```

El modelo dirá "Estamos abiertos de 9 de la mañana a 6 de la tarde" y el escenario fallará
siendo la respuesta perfecta. La forma correcta mueve el escenario de **un caso** a **un
conjunto con umbral**:

```
✅ Given el conjunto dorado de 60 preguntas reales de clientes,
   When se ejecuta la evaluación completa,
   Then ≥90% de las respuestas contienen el dato correcto,
        ≥95% citan el documento del que salió,
        y 0% afirman un precio que no está en el catálogo.
```

Fíjate en tres cosas. El umbral es **distinto por criterio**, porque no todos los fallos
cuestan igual: una respuesta incompleta molesta, un precio inventado cuesta dinero y
credibilidad. Los criterios que valen dinero llevan umbral **cero** y se escriben aparte. Y
el escenario ya no habla de una interacción sino de una **medición**, que es lo único
verificable cuando el sistema no es determinista.

### 2.2. El golden set es parte del spec, no del plan

Este es el punto que más gente se salta, y el que más caro sale.

El conjunto dorado —las preguntas reales con su respuesta esperada— **es la definición
ejecutable del QUÉ**. Es al spec de IA lo que los escenarios de aceptación son al spec
determinista. Si lo dejas para el plan o, peor, para "cuando lleguemos a testear", lo que
ocurre invariablemente es que se construye **después** del sistema, mirando lo que el sistema
ya hace. Y un examen escrito después de ver las respuestas del alumno no evalúa nada.

Lo que el spec debe fijar sobre el golden set:

| Qué se fija | Ejemplo | Por qué en el spec |
|---|---|---|
| **Origen** | 60 preguntas del historial real de WhatsApp de los últimos 3 meses | Preguntas inventadas por el equipo miden lo que el equipo imagina, no lo que los clientes preguntan |
| **Tamaño y cobertura** | ≥50 casos: 40% horarios/ubicación, 40% catálogo y precios, 20% fuera de alcance | Sin cuota por categoría, el conjunto se sesga hacia lo fácil |
| **Quién etiqueta la respuesta correcta** | Rosa, la encargada — no el equipo técnico | La verdad de negocio la tiene el negocio |
| **Casos negativos obligatorios** | ≥10 preguntas que el sistema **debe** rechazar | Sin ellos solo mides si responde, no si sabe callarse |

> **Regla:** si el spec de una app de IA no viene con su golden set definido, no es
> verificable, y un spec no verificable no es un spec — es una carta de intenciones.

### 2.3. Requisitos de abstención: cuándo el sistema debe callarse

En software determinista especificas qué hace el sistema. En IA, la parte difícil —y la que
distingue un prototipo de algo que puedes poner frente a clientes— es especificar **cuándo no
debe hacer nada**.

Un LLM siempre responde. Esa es su naturaleza y es también el riesgo: ante una pregunta cuya
respuesta no está en el corpus, producirá algo plausible en lugar de admitir que no sabe. Si
el spec no exige la abstención, no la vas a obtener.

Los requisitos de abstención que casi todo sistema de IA necesita:

```
FR-00x: El sistema MUST responder "no tengo ese dato, te paso con una persona"
        cuando ningún fragmento recuperado supere el umbral de relevancia.

FR-00x: El sistema MUST escalar a un humano, sin intentar responder, cuando el
        mensaje contenga un reclamo, una queja formal o una solicitud de devolución.

FR-00x: El sistema MUST negarse a confirmar precios, stock o plazos que no
        aparezcan literalmente en el catálogo vigente.

FR-00x: El sistema MUST identificarse como asistente automático en el primer
        mensaje de cada conversación.
```

Los dos primeros son los que salvan proyectos. El tercero es el que evita la demanda.

### 2.4. Los presupuestos son requisitos de primera clase

En software normal, coste y latencia son requisitos no funcionales de segunda fila: se
optimizan al final si molestan. En IA condicionan el **diseño entero**, y por eso van en el
spec y no en el plan.

```
FR-00x: El coste medio por conversación resuelta MUST mantenerse por debajo
        de USD 0.03, medido sobre el tráfico de una semana.

FR-00x: El sistema MUST enviar la primera respuesta en menos de 4 segundos (p95).
```

La razón de que esto sea spec y no plan: **el presupuesto elimina arquitecturas**. Con tres
centavos por conversación no cabe un re-ranker sobre veinte fragmentos, ni una cadena de tres
llamadas al modelo, ni un agente que itere hasta convencerse. Si el presupuesto aparece
después de elegir la arquitectura, descubres la incompatibilidad cuando ya está construido.
Escrito en el spec, el `/plan` nace sabiendo contra qué techo trabaja.

Un detalle que se olvida: el presupuesto se expresa **por unidad de negocio** (por
conversación resuelta, por documento procesado), no por llamada al modelo. Al cliente le
importa lo que cuesta atender a un cliente, no lo que cuesta un token.

### 2.5. Los modos de fallo propios de la IA hay que nombrarlos

La sección `Edge Cases` de un spec determinista lista condiciones de borde: archivo ausente,
tabla vacía, mayúsculas distintas. Un sistema de IA tiene además una familia de fallos que no
existen en software normal, y que **no aparecerán solos** si el spec no los nombra:

| Modo de fallo | Qué es | Qué debe exigir el spec |
|---|---|---|
| **Alucinación** | Afirmar con confianza algo que no está en las fuentes | Trazabilidad: toda afirmación factual citada, y umbral cero para datos que cuestan dinero |
| **Inyección de prompt indirecta** | Un documento del corpus contiene instrucciones que el modelo obedece | Que el contenido recuperado se trate como **datos**, nunca como instrucciones, y un caso de prueba explícito |
| **Fuga de datos** | El sistema revela información de otro cliente o del prompt interno | Aislamiento por cliente y prohibición de revelar instrucciones internas |
| **Deriva de versión** | El proveedor actualiza el modelo y el comportamiento cambia sin que tú toques nada | Que el golden set se corra **antes de aceptar** cualquier cambio de modelo o de prompt |

El último es el más subestimado. Es la razón real de que el golden set exista: no es para el
día del lanzamiento, es para el día —dentro de seis meses— en que algo cambie por debajo y
necesites saber en veinte minutos si sigues cumpliendo el contrato.

### 2.6. El modelo NO va en el spec

*"Usa Claude"*, *"usa GPT-4"*, *"usa un modelo open source"* son decisiones de **plan**, con
su justificación y sus alternativas descartadas. En el spec no pintan nada.

El argumento es puramente práctico: el panorama de modelos cambia cada pocos meses. Si
"MUST usar el modelo X" está escrito en el spec, cada cambio de proveedor te obliga a editar
el documento que se supone que es la fuente de verdad **del negocio** — y el negocio no
cambió. Lo que el negocio pidió sigue siendo "que cite la fuente y no invente precios".

```
Spec:  FR-004: El sistema MUST citar la fuente de todo dato factual.
              El coste por conversación MUST ser < USD 0.03.

Plan:  Modelo elegido: [modelo concreto y versión].
       Por qué: cumple el presupuesto de FR-004 con margen y sigue
       instrucciones de citación de forma fiable en las pruebas.
       Descartado: [alternativa] — mejor calidad, 4× el coste, no cabe.
```

El spec pone el techo, el plan elige qué cabe debajo. Cambiar de modelo pasa a ser una
edición del plan y una corrida del golden set, no una renegociación del contrato.

> Corolario práctico: **nunca escribas de memoria el identificador ni el precio de un
> modelo**. Ambos cambian y ambos caducan; verifícalos contra la documentación oficial del
> proveedor el día que llenes el plan.

### 2.7. El peldaño de autonomía es un requisito, no un detalle

Cuánta libertad tiene el sistema para actuar sin supervisión es una decisión de **negocio**,
con consecuencias legales y económicas. No es una elección de arquitectura y no se delega al
plan.

El [Concepto 35](../../web/content/modules/35-discovery-de-procesos.mdx) tiene la escalera:
regla determinista → copiloto → agente → sistema agéntico. El spec debe decir en qué peldaño
está cada acción, y no todas tienen que estar en el mismo:

```
FR-00x: El sistema MUST responder consultas informativas de forma autónoma.
FR-00x: El sistema MUST NO confirmar pedidos ni comprometer stock; para esas
        intenciones MUST redactar un borrador y esperar aprobación de Rosa.
FR-00x: Toda acción con efecto externo MUST quedar registrada con el mensaje
        que la originó, para poder auditarla después.
```

Ese "responder sí, comprometer no" es la frontera que hace que un cliente acepte poner el
sistema en producción. Es contenido de spec.

### 2.8. El corpus es parte del contrato

En un sistema RAG, la calidad de las respuestas depende más del corpus que del modelo, así
que el corpus no puede ser un detalle de implementación. El spec fija **qué fuentes entran,
con qué frescura y quién las aprueba**:

```
FR-00x: El sistema MUST responder únicamente a partir del catálogo vigente,
        las políticas de la tienda y el documento de horarios.
FR-00x: Un cambio en el catálogo MUST reflejarse en las respuestas en menos
        de 24 horas.
FR-00x: Los documentos del corpus MUST tener un responsable identificado que
        aprueba su ingreso.
```

Sin la regla de frescura, el sistema recita el precio del mes pasado con total seguridad —y
técnicamente no está alucinando, está citando bien una fuente obsoleta, que para el cliente
es exactamente igual de malo.

### Resumen de la sección

| Dimensión | Spec determinista | Spec de aplicación de IA |
|---|---|---|
| Criterio de aceptación | Given/When/Then exacto | Umbral sobre conjunto dorado |
| Definición de "listo" | Los tests pasan | Las evals superan el umbral |
| Artefacto que acompaña al spec | Escenarios | Golden set etiquetado por negocio |
| Lo difícil de especificar | Qué hace | Cuándo se abstiene |
| Coste y latencia | NFR de segunda fila | Requisito que elimina arquitecturas |
| Casos de borde | Entradas límite | + alucinación, inyección, fuga, deriva |
| Elección de tecnología | Fuera del spec | Fuera del spec (modelo incluido) |
| Estabilidad en el tiempo | El código no cambia solo | El modelo cambia bajo tus pies |

---

## 3. Desde cero vs. feature acotado

El método es el mismo; lo que cambia es por dónde empiezas y cuánto escribes.

### 3.1. Desde cero (greenfield)

**Primero la constitución, no el spec.** La constitución recoge los principios que sobreviven
a *todas* las features: lo que nunca se negocia por conveniencia. Se escribe una vez, se
enmienda con cuidado, y su valor aparece meses después, cuando alguien proponga el atajo que
ella prohíbe.

La [constitución de este curso](../../.specify/memory/constitution.md) es un buen modelo de
forma: cinco principios, cada uno con su **Rationale** explícito. Para un proyecto de IA de
cliente, los cinco principios suelen salir de estas familias:

1. **Trazabilidad** — ninguna afirmación factual sin fuente citada.
2. **Presupuesto** — un techo de coste por unidad de negocio que ninguna feature puede romper.
3. **Evals antes que features** — ninguna funcionalidad se da por terminada sin su medición.
4. **Datos del cliente** — qué sale del perímetro, qué se retiene, qué se registra.
5. **Degradación explícita** — el sistema falla diciendo que falla, nunca inventando.

**Después, el spec del slice más fino que ya entrega valor.** El error más común del greenfield
es escribir el spec de la aplicación completa: sale un documento de quince páginas que nadie
lee entero, que mezcla lo seguro con lo especulativo, y que estará obsoleto antes de terminar
la primera historia. Escribe el spec de la P1 atravesando el sistema entero, constrúyela,
aprende, y **después** especifica la siguiente con lo que aprendiste.

### 3.2. Feature sobre algo que ya existe

Aquí la constitución ya está y los presupuestos se heredan, así que el spec es mucho más
corto —media página es normal— pero gana una sección que el greenfield no tiene:

**No-regresión: qué no debe romperse.** Es la pregunta que un spec de feature debe contestar
siempre, y en IA tiene una respuesta concreta y ejecutable:

```
## No-regresión

- El golden set actual (60 casos) MUST seguir superando sus umbrales vigentes
  después de este cambio.
- El coste por conversación MUST NO subir más de USD 0.005.
- Los casos negativos (abstención) MUST seguir en 100%.
```

Esto importa especialmente en IA por una razón que no tiene equivalente en software normal:
**tocar el prompt para mejorar una cosa empeora otra**, y no hay compilador que te avise. Un
cambio de dos líneas en las instrucciones para que cite mejor las fuentes puede hacer que
deje de abstenerse. Sin la corrida del golden set antes y después, ese intercambio ocurre y
nadie lo nota hasta que un cliente lo reporta.

### 3.3. La regla de tamaño

> Si el spec no cabe en dos páginas, no es un spec: son tres specs mal cortados.

Un spec largo casi nunca es un problema de redacción — es la señal de que metiste varias
features en una. Córtalo por historias independientes y escribe el de la primera.

---

## 4. Ejemplo trabajado

En [`ejemplos-spec/asistente-rag-whatsapp/`](ejemplos-spec/asistente-rag-whatsapp/) está el
recorrido completo para un caso realista: **una PyME peruana que quiere responder consultas de
clientes por WhatsApp sobre su catálogo, precios y políticas**, citando siempre la fuente.

| Archivo | Qué contiene |
|---|---|
| [`constitution.md`](ejemplos-spec/asistente-rag-whatsapp/constitution.md) | Los cinco principios del proyecto, con su rationale |
| [`spec.md`](ejemplos-spec/asistente-rag-whatsapp/spec.md) | El spec completo: 3 historias priorizadas, FR con abstención y presupuesto, golden set, criterios con umbral |
| [`plan.md`](ejemplos-spec/asistente-rag-whatsapp/plan.md) | Las decisiones técnicas que el spec dejó abiertas, con alternativas descartadas y Constitution Check |
| [`tasks.md`](ejemplos-spec/asistente-rag-whatsapp/tasks.md) | La descomposición, con el golden set como tarea **anterior** a la implementación |
| [`spec-feature-citacion.md`](ejemplos-spec/asistente-rag-whatsapp/spec-feature-citacion.md) | El mismo sistema, ya en producción, recibiendo un feature acotado — para contrastar el tamaño |

Léelos en ese orden. La cadena que conviene trazar es la misma que el Concepto 19 propone para
el verificador: coge el requisito de abstención del `spec.md`, síguelo hasta la decisión que
lo resuelve en el `plan.md`, y de ahí a la tarea que lo construye y a la que lo mide.

---

## 5. Antipatrones, checklist y cómo conducirlo con un asistente

### 5.1. Antipatrones

**El spec que es un plan disfrazado.** Nombra librerías, modelos y esquemas de base de datos.
Síntoma: no se entiende sin saber de tecnología. Cura: tapa cada nombre propio técnico y
comprueba que el requisito sigue teniendo sentido para el cliente.

**El spec sin números.** "Rápido", "preciso", "confiable", "escalable". No son requisitos, son
adjetivos: no se pueden verificar y por tanto no se pueden incumplir, que es justamente lo que
los hace inútiles.

**El golden set para después.** El más caro de todos, porque el coste no se ve en el momento.
Se paga cuando el conjunto acaba construido a imagen de lo que el sistema ya hacía.

**Solo casos felices.** Cincuenta preguntas que el sistema debe contestar y ninguna que deba
rechazar. Mides si responde, no si sabe callarse — y lo segundo es lo que decide si puedes
ponerlo frente a clientes.

**El spec congelado.** Se escribe, se aprueba, y el código se aleja de él sin que nadie lo
actualice. El Concepto 19 ya lo advierte: el spec **vive**. Cuando cambia el requisito, se
cambia el spec y se regeneran plan y tasks.

**Todo en P1.** Si las tres historias son P1, no priorizaste: pospusiste la decisión hasta que
te la imponga la falta de tiempo.

### 5.2. Checklist antes de pasar a `/plan`

- [ ] Puedo nombrar a la persona que sufre el problema y cuánto le cuesta hoy.
- [ ] Implementando solo la P1 tengo algo demostrable a un cliente.
- [ ] Ningún FR nombra una librería, un proveedor o un modelo.
- [ ] Cada criterio de éxito tiene un número y se puede medir sin abrir el código.
- [ ] El golden set está definido: origen, tamaño, cobertura y quién etiqueta.
- [ ] Hay casos negativos: al menos uno de cada tipo de cosa que el sistema debe rechazar.
- [ ] Está escrito cuándo el sistema se abstiene y a quién escala.
- [ ] Hay un techo de coste por unidad de negocio y un objetivo de latencia.
- [ ] Los cuatro modos de fallo de IA están considerados en `Edge Cases`.
- [ ] Está escrito qué acciones son autónomas y cuáles requieren aprobación humana.
- [ ] Lo que no sé decidir está marcado `[NEEDS CLARIFICATION]`; lo que decidí por defecto está en `Assumptions`.
- [ ] Está escrito qué NO vamos a hacer.

### 5.3. Cómo conducirlo con un asistente

El Concepto 19 lo resume: **la IA teclea, tú diriges**. Aplicado a la redacción del spec:

**Dale el material, no la idea.** Un asistente al que le dices "escribe el spec de un bot de
WhatsApp" inventará un producto genérico plausible. Uno al que le das la transcripción de la
reunión, veinte mensajes reales de clientes y la constitución del proyecto escribirá un primer
borrador sobre hechos. El contexto que le das es el techo de lo que puede producir.

**`/speckit-clarify` pesa más en IA que en software normal.** En un sistema determinista, las
ambigüedades típicas se descubren al implementar: el compilador o el test te avisan. En un
sistema de IA, una ambigüedad sobre "qué significa responder bien" no la detecta nada —
produce un sistema que funciona *de alguna manera*, y solo descubres cuál cuando el cliente se
queja. Las preguntas de clarificación que más rinden son siempre las mismas tres: **cuál es el
umbral aceptable**, **qué pasa cuando no sabe**, y **quién decide si una respuesta fue buena**.

**Vigila la filtración de decisiones técnicas.** Es el fallo más frecuente del asistente
redactando specs: le sale natural escribir "usaremos embeddings de OpenAI y pgvector" dentro
de un requisito, porque está entrenado con código. Revisa el borrador con el test de la
sección 1.3 y devuelve al plan todo lo que sea CÓMO.

**Revisa el spec como revisarías un PR.** No "se ve bien" sino contra la checklist de 5.2. Un
spec plausible-pero-vago produce exactamente el mismo problema que el Concepto 19 describe
para el código: cuesta más descubrir en qué se desvió que haberlo escrito tú.

---

## Ver también

- [Concepto 19 — Spec-Driven Development con spec-kit](../../web/content/modules/19-spec-driven-development.mdx) — qué es SDD y los cinco pasos
- [Concepto 19b — Escribir el spec de una aplicación de IA](../../web/content/modules/19b-spec-de-apps-de-ia.mdx) — la versión docente de esta guía
- [Concepto 35 — Discovery de procesos](../../web/content/modules/35-discovery-de-procesos.mdx) — qué automatizar, antes del spec
- [`specs/001-verificador-curso/`](../../specs/001-verificador-curso/) — el ejemplo determinista real del repo
- [`.specify/templates/`](../../.specify/templates/) — las plantillas de spec-kit
- [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — la constitución de este proyecto
