// Local rehype plugin — runs BEFORE @shikijs/rehype in the MDX pipeline.
//
// The HTML→MDX converter emits fenced blocks with a meta title, e.g.
//   ```python title="04_memoria.py · construir_cadena"
// Shiki reads that meta for its own purposes and then discards it, so the
// caption never reaches the page. This plugin lifts the title out first and
// wraps the <pre> in <figure class="codefig"><figcaption><span class="cap">…
// Shiki later replaces only the inner <pre><code> (parent.children[index] =
// fragment), so the figure and its figcaption — siblings it never matches —
// survive untouched.
//
// Registered as a string path in next.config.ts so it stays serializable under
// Turbopack. No external deps (manual tree walk) to keep resolution trivial.

const TITLE_RE = /title="([^"]*)"/;

function metaOf(codeEl) {
  // Same source Shiki reads from (see @shikijs/rehype PreHandler).
  return codeEl?.data?.meta ?? codeEl?.properties?.metastring?.toString() ?? "";
}

function codeChild(pre) {
  return (pre.children || []).find(
    (c) => c.type === "element" && c.tagName === "code"
  );
}

function isLangText(codeEl) {
  const cls = codeEl?.properties?.className;
  const arr = Array.isArray(cls) ? cls : cls ? [cls] : [];
  return arr.includes("language-text");
}

function figureFor(pre) {
  const code = codeChild(pre);
  if (!code) return null;
  const m = TITLE_RE.exec(metaOf(code));
  if (!m) return null;
  const title = m[1];
  // "Expected output" blocks: plain text whose caption starts with the ▸ marker.
  const isOutput = isLangText(code) && title.startsWith("▸");
  return {
    type: "element",
    tagName: "figure",
    properties: { className: isOutput ? ["codefig", "is-output"] : ["codefig"] },
    children: [
      {
        type: "element",
        tagName: "figcaption",
        properties: {},
        children: [
          {
            type: "element",
            tagName: "span",
            properties: { className: ["cap"] },
            children: [{ type: "text", value: title }],
          },
        ],
      },
      pre,
    ],
  };
}

function walk(node) {
  if (!node || !Array.isArray(node.children)) return;
  for (let i = 0; i < node.children.length; i++) {
    const child = node.children[i];
    if (child?.type === "element" && child.tagName === "pre") {
      const fig = figureFor(child);
      if (fig) {
        node.children[i] = fig; // pre now lives inside the figure; don't recurse in
        continue;
      }
    }
    walk(child);
  }
}

export default function rehypeCodeTitle() {
  return (tree) => {
    walk(tree);
  };
}
