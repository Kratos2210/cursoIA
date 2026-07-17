import { KindTag, MetaChips, MetaChip, FileRef, Box, Solution, Recap, C } from "@/components/content/ui";
import { CodeFigure } from "@/components/content/CodeFigure";
import { Quiz } from "@/components/content/Quiz";

export function M04() {
  return (
    <article className="article">
      <KindTag colorVar="--l1">Nivel 1 · Fundamentos · Módulo 04</KindTag>
      <h1>Prompts + LCEL: la línea de ensamblaje</h1>

      <FileRef file="02_prompts_lcel.py" tested />

      <MetaChips>
        <MetaChip icon="🎯" label="Sabrás:">
          armar cadenas con plantillas y el operador <C>|</C> (LCEL)
        </MetaChip>
        <MetaChip icon="✅" label="Necesitas:">
          Módulo 03
        </MetaChip>
        <MetaChip icon="⏱️">~25 min</MetaChip>
      </MetaChips>

      <p>
        Un <b>prompt template</b> es un molde con huecos <C>{"{variables}"}</C>. Y aquí aparece la
        idea central de LangChain moderno: <b>LCEL</b>, que conecta pasos con el operador tubería{" "}
        <C>|</C>.
      </p>

      <Box kind="def" label="◈ Definición · LCEL">
        <p>
          <b>LCEL</b> (LangChain Expression Language) es una forma <b>declarativa</b> de construir
          cadenas: en lugar de escribir paso a paso <em>cómo</em> se llama a cada pieza, <b>declaras
          el orden</b> en que se conectan y LangChain se encarga del resto.
        </p>
        <p>
          La sintaxis imita las tuberías de Unix: <C>|</C> encadena componentes de modo que <b>la
          salida de uno es la entrada del siguiente</b>.
        </p>
        <p className="formula">Prompt&nbsp; |&nbsp; Modelo (LLM)&nbsp; |&nbsp; Parser</p>
      </Box>

      <Box kind="analogy" label="◆ Analogía">
        <p>
          El <C>|</C> es una <b>línea de ensamblaje</b>: el dato entra por la izquierda y avanza de
          estación en estación. <em>prompt</em> arma el mensaje → <em>modelo</em> lo responde →{" "}
          <em>parser</em> limpia la salida.
        </p>
      </Box>

      <CodeFigure
        caption="chain.py · tu primera cadena LCEL"
        code={`from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template(
    "Eres analista de atención al cliente. Clasifica el sentimiento "
    "(Positivo/Negativo/Neutro) de esta reseña y responde en una frase.\\n"
    "Reseña: {review}"
)

cadena = prompt | llm | StrOutputParser()   # prompt -> modelo -> texto

print(cadena.invoke({"review": "El producto llegó tarde y roto."}))`}
      />

      <CodeFigure
        caption="▸ deberías ver (algo así)"
        output
        code={`Negativo. El cliente expresa molestia porque el producto llegó tarde y dañado.`}
      />

      <Box kind="practice" label="▸ Para practicar">
        <p>
          Modifica el prompt para que además <b>traduzca la reseña al inglés</b>. Solo cambias el
          molde: la cadena <C>prompt | llm | parser</C> sigue igual. Eso es el poder de LCEL.
        </p>
        <Solution>
          <CodeFigure
            caption="solución · solo cambia el molde"
            copyable={false}
            code={`prompt = ChatPromptTemplate.from_template(
    "Eres analista de atención al cliente. Para esta reseña:\\n"
    "1) Clasifica el sentimiento (Positivo/Negativo/Neutro).\\n"
    "2) Tradúcela al inglés.\\n"
    "Reseña: {review}"
)
# la cadena NO se toca:
print((prompt | llm | StrOutputParser()).invoke(...))`}
          />
        </Solution>
      </Box>

      <Quiz
        title="✅ Autoevaluación · Nivel 1"
        items={[
          {
            prompt: (
              <>
                ¿Qué hace <C>StrOutputParser()</C> al final de una cadena?
              </>
            ),
            options: [
              { node: "Llama al modelo una segunda vez para verificar" },
              { node: "Convierte la respuesta del modelo en texto plano", ok: true },
              { node: "Corrige la ortografía de la respuesta" },
            ],
            feedback: (
              <>
                Evita escribir <C>.content</C> a cada rato: la cadena ya devuelve el texto listo.
              </>
            ),
          },
          {
            prompt: (
              <>
                En LCEL, <C>prompt | llm | parser</C> significa que…
              </>
            ),
            options: [
              { node: "El dato pasa de estación en estación, como línea de ensamblaje", ok: true },
              { node: "Los tres se ejecutan al mismo tiempo" },
              { node: "Es una comparación lógica tipo “o”" },
            ],
            feedback: (
              <>
                El <C>|</C> conecta pasos en orden: el prompt arma el mensaje, el modelo responde, el
                parser limpia.
              </>
            ),
          },
          {
            prompt: (
              <>
                ¿Para qué pones <C>temperature=0</C>?
              </>
            ),
            options: [
              { node: "Para que responda más rápido" },
              { node: "Para gastar menos cuota" },
              { node: "Para respuestas precisas y repetibles", ok: true },
            ],
            feedback: <>Temperatura baja = menos creatividad. Ideal para clasificar, calcular o usar tools.</>,
          },
        ]}
      />

      <Recap colorVar="--l1">
        Un prompt es una <b>plantilla reutilizable</b>, no un texto fijo. Y el operador <C>|</C>{" "}
        encadena prompt → modelo → parser en un solo objeto invocable.
      </Recap>
    </article>
  );
}
