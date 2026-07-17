import { KindTag, MetaChips, MetaChip, Box, Grid3, Card, Recap, TableWrap, Solution, C } from "@/components/content/ui";
import { CodeFigure } from "@/components/content/CodeFigure";

export function M00() {
  return (
    <article className="article">
      <KindTag colorVar="--l1">Nivel 1 · Fundamentos · Módulo 00</KindTag>
      <h1>Preparar el terreno</h1>

      <MetaChips>
        <MetaChip icon="🎯" label="Sabrás:">
          preparar tu PC y correr tu primer script con <C>uv</C>
        </MetaChip>
        <MetaChip icon="✅" label="Necesitas:">
          una computadora
        </MetaChip>
        <MetaChip icon="⏱️">~30 min</MetaChip>
      </MetaChips>

      <p>
        Un modelo de lenguaje (LLM) como Gemini o Qwen sabe conversar, pero por sí solo <em>no</em>{" "}
        calcula con exactitud, no recuerda charlas anteriores y no conoce tus documentos privados.
        Estas librerías resuelven justo eso.
      </p>

      <Box kind="analogy" label="◆ Analogía">
        <p>
          Piensa en un <b>LLM</b> como un empleado brillante recién contratado: habla muchos idiomas
          y sabe de casi todo… pero llegó sin computadora, sin acceso a tu base de datos y con
          amnesia cada mañana. <b>LangChain, RAG y LangGraph</b> son las herramientas de oficina que
          lo vuelven realmente útil.
        </p>
      </Box>

      <h3>Los tres protagonistas</h3>
      <Grid3>
        <Card num="pieza 1" title="LangChain">
          <p>La caja de piezas estándar: modelos, prompts, parsers, herramientas. Bloques que encajan entre sí.</p>
        </Card>
        <Card num="técnica" title="RAG">
          <p>
            No es una librería, es una <em>técnica</em>: darle al modelo tus documentos como “chuleta”
            para responder con datos reales.
          </p>
        </Card>
        <Card num="pieza 2" title="LangGraph">
          <p>El orquestador: agentes que piensan en ciclo (pensar → actuar → observar), recuerdan y sobreviven a fallos.</p>
        </Card>
      </Grid3>

      <h3>
        Instala <C>uv</C> y crea tu proyecto
      </h3>
      <p>
        <C>uv</C> gestiona tu Python y tus librerías. Pega en tu terminal el comando de tu sistema:
      </p>

      <CodeFigure
        caption="terminal · instalar uv"
        code={`# macOS o Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (en PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`}
      />

      <CodeFigure
        caption="terminal · crear el proyecto"
        code={`uv init mi-curso-ia && cd mi-curso-ia
uv add langchain langgraph python-dotenv pypdf
uv add langchain-google-genai langchain-openai`}
      />

      <Box kind="warn" label="▲ El primer tropiezo de todo el mundo">
        <p>
          Al verificar la instalación puede aparecer{" "}
          <C>ModuleNotFoundError: No module named 'dotenv'</C>. No falló <C>uv</C>: hizo exactamente
          lo que le pediste. Si la lista de dependencias está vacía, crea el entorno y no pone nada
          dentro.
        </p>
        <p>
          <b>La cura:</b> corre los <C>uv add</C> dentro de tu carpeta <C>mi-curso-ia/</C>.
        </p>
      </Box>

      <h3>Consigue tu llave API</h3>
      <p>
        El modelo vive en los servidores de otra empresa; tu programa se identifica con una{" "}
        <b>llave API</b>. Es gratis y toma un minuto. Tienes dos proveedores y el curso funciona
        igual con cualquiera:
      </p>
      <TableWrap>
        <table>
          <thead>
            <tr>
              <th>Proveedor</th>
              <th>Dónde</th>
              <th>La llave empieza con</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><b>Gemini</b></td>
              <td>aistudio.google.com</td>
              <td><code>AIza…</code></td>
            </tr>
            <tr>
              <td><b>Groq</b> (recomendado)</td>
              <td>console.groq.com/keys</td>
              <td><code>gsk_…</code></td>
            </tr>
          </tbody>
        </table>
      </TableWrap>

      <CodeFigure
        caption=".env · con tu llave real (sin comillas ni espacios)"
        code={`LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMBEDDINGS_PROVIDER=fastembed`}
      />

      <Box kind="def" label="◈ Definición · API key">
        <p>
          Una <b>API key</b> es una contraseña que identifica a tu programa ante el servicio. En el
          plan gratuito no cuesta nada, pero se trata como cualquier contraseña: <b>no se comparte y
          nunca se sube a internet</b> (por eso vive en el <C>.env</C>).
        </p>
      </Box>

      <Box kind="practice" label="▸ Para practicar">
        <p>
          Instala lo del bloque básico y consigue tu llave. Verifica que <C>.env</C> exista y esté
          en tu <C>.gitignore</C>.
        </p>
        <Solution>
          <CodeFigure
            caption="solución · verificación en 4 comandos"
            copyable={false}
            code={`pwd                      # ¿estás DENTRO de mi-curso-ia?
cat .env                 # debe mostrar LLM_PROVIDER y tu llave
cat .gitignore | grep .env
uv run python -c "from dotenv import load_dotenv; print('listo')"`}
          />
        </Solution>
      </Box>

      <Recap colorVar="--l1">
        Un LLM por sí solo no calcula, no recuerda y no conoce tus documentos. <b>LangChain</b> lo
        conecta a herramientas, <b>RAG</b> le da tus papeles y <b>LangGraph</b> le da un ciclo de
        trabajo.
      </Recap>
    </article>
  );
}
