// Build-time full-text index for the ⌘K palette. Reads the manifest + every
// MDX and emits public/search-index.json (gitignored): the client fetches it
// lazily the first time the palette opens, so pages stay light.
//
// Headings are slugged with github-slugger — the SAME library rehype-slug uses
// at render time — so deep links `/concepto/x#heading` always match.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import GithubSlugger from "github-slugger";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const CONTENT = join(ROOT, "content");
const OUT = join(ROOT, "public", "search-index.json");

/** Strip an MDX body down to searchable plain text + its headings. */
function parseMdx(raw) {
  const slugger = new GithubSlugger();
  const headings = [];
  const body = [];
  let inFence = false;
  for (const line of raw.split("\n")) {
    if (line.trimStart().startsWith("```")) {
      inFence = !inFence;
      continue;
    }
    if (inFence) {
      body.push(line); // code is worth searching (InMemoryStore, uv run…)
      continue;
    }
    const h = /^(#{2,3})\s+(.*)$/.exec(line);
    if (h) {
      const text = plain(h[2]);
      headings.push({ id: slugger.slug(text), text });
      body.push(text);
      continue;
    }
    body.push(plain(line));
  }
  return { headings, text: body.join(" ").replace(/\s+/g, " ").trim() };
}

/** Markdown/JSX decorations out, human text in. */
function plain(line) {
  return line
    .replace(/<[^>]+>/g, " ") // JSX/HTML tags
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1") // [text](url) -> text
    .replace(/[`*_]/g, "")
    .trim();
}

const manifest = JSON.parse(readFileSync(join(CONTENT, "modules.manifest.json"), "utf8"));
const docs = [];

for (const m of manifest.modules) {
  const raw = readFileSync(join(CONTENT, "modules", `${m.slug}.mdx`), "utf8");
  docs.push({
    slug: m.slug,
    href: `/concepto/${m.slug}`,
    num: m.badge || m.slug.split("-")[0],
    title: m.title,
    group: m.levelName,
    ...parseMdx(raw),
  });
}
for (const e of manifest.extras) {
  const raw = readFileSync(join(CONTENT, "extras", `${e.slug}.mdx`), "utf8");
  docs.push({
    slug: e.slug,
    href: `/recurso/${e.slug}`,
    num: "✦",
    title: e.title,
    group: "Referencia",
    ...parseMdx(raw),
  });
}

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({ docs }));
console.log(`search-index: ${docs.length} documentos → public/search-index.json`);
