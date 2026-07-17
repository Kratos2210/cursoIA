#!/usr/bin/env node
// One-shot converter: curso_ejemplos/curso-langchain.html -> web/content/*.mdx
//
// Walks each <section id> of the hand-authored single-page course and emits one
// MDX file per section (modules + extras) plus a manifest. The HTML markup is
// highly regular (see the class vocabulary in the source), so each construct
// maps to a component in web/components or to plain Markdown.
//
// Run:   npm run convert            (writes MDX + manifest)
//        npm run convert -- --check (also runs the fidelity gate, exits non-zero on failure)
//
// This script is committed as an auditable record of the migration even though
// it only runs once; after F1 the MDX files are the source of truth.

import { load } from "cheerio";
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..");
const HTML_PATH = join(REPO, "curso_ejemplos", "curso-langchain.html");
const OUT_MODULES = join(__dirname, "..", "content", "modules");
const OUT_EXTRAS = join(__dirname, "..", "content", "extras");
const MANIFEST_PATH = join(__dirname, "..", "content", "modules.manifest.json");
const REPORT_PATH = join(__dirname, "..", "content", "conversion-report.json");

const CHECK = process.argv.includes("--check");

// Sections that are not numbered modules. Everything else is a module.
const EXTRA_SLUGS = {
  examen: "examen",
  entrevista: "entrevista",
  ejercicios: "ejercicios",
  faq: "faq",
  cheat: "cheat-sheet",
  mapa: "mapa",
  llmops: "llmops",
};
// Extra routes (for internal-link rewriting). All extras live under /recurso/<slug>
// (the v2 route); the slug is the same value used for the output filename.
const EXTRA_ROUTE = Object.fromEntries(
  Object.entries(EXTRA_SLUGS).map(([id, slug]) => [id, `/recurso/${slug}`])
);

const html = readFileSync(HTML_PATH, "utf8");
const $ = load(html);

// ---------------------------------------------------------------------------
// Pass 1 — nav: level grouping, order, badge and short title per module id.
// ---------------------------------------------------------------------------
const nav = new Map(); // oldId -> { badge, navTitle, level, levelName, order }
{
  let level = 1;
  let levelName = "";
  let order = 0;
  $("#nav")
    .children()
    .each((_, el) => {
      const $el = $(el);
      if ($el.hasClass("navsec")) {
        const m = ($el.attr("style") || "").match(/--l(\d)/);
        level = m ? Number(m[1]) : level;
        levelName = $el.text().trim();
      } else if (el.tagName === "a") {
        const href = $el.attr("href") || "";
        if (!href.startsWith("#")) return;
        const oldId = href.slice(1);
        const badge = $el.find(".n").text().trim();
        const navTitle = $el.clone().children(".n").remove().end().text().trim();
        nav.set(oldId, { badge, navTitle, level, levelName, order: order++ });
      }
    });
}

// ---------------------------------------------------------------------------
// Slugs, routes, anchor map (element id -> containing section id).
// ---------------------------------------------------------------------------
function slugify(s) {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

const sections = $("section[id]").toArray();
const isExtra = (id) => Object.prototype.hasOwnProperty.call(EXTRA_SLUGS, id);

function sectionSlug(id) {
  if (isExtra(id)) return EXTRA_SLUGS[id];
  const info = nav.get(id);
  const badge = info?.badge && /^[0-9]/.test(info.badge) ? info.badge : id.replace(/^m/, "");
  const title = info?.navTitle || $(`#${id} h2`).first().text().trim() || id;
  return `${badge}-${slugify(title)}`;
}
function sectionRoute(id) {
  if (isExtra(id)) return EXTRA_ROUTE[id];
  return `/modulo/${sectionSlug(id)}`;
}

// Map every element id in the document to the id of its enclosing <section>,
// so intra-page anchors (#m12, #m29-proyecto) rewrite to the right route + hash.
const anchorToSection = new Map();
for (const sec of sections) {
  const secId = sec.attribs.id;
  anchorToSection.set(secId, secId);
  $(sec)
    .find("[id]")
    .each((_, el) => anchorToSection.set(el.attribs.id, secId));
}
function rewriteHash(hash) {
  const secId = anchorToSection.get(hash);
  if (!secId) return `#${hash}`; // unknown anchor: leave as-is
  const route = sectionRoute(secId);
  return hash === secId ? route : `${route}#${hash}`;
}

// ---------------------------------------------------------------------------
// Serialization helpers.
// ---------------------------------------------------------------------------
const INLINE_TAGS = new Set([
  "a", "b", "strong", "i", "em", "code", "span", "sup", "sub", "br", "small", "u", "mark",
]);

function escInline(text, table = false) {
  let s = text.replace(/\\/g, "\\\\").replace(/`/g, "\\`");
  s = s.replace(/</g, "\\<").replace(/[{}]/g, (c) => "\\" + c);
  if (table) s = s.replace(/\|/g, "\\|");
  return s;
}

function attr(s) {
  // Safe double-quoted JSX attribute value.
  return String(s).replace(/"/g, "”").replace(/\s+/g, " ").trim();
}

function inlineCode(node, table) {
  let raw = $(node).text();
  const ticks = raw.includes("`") ? "``" : "`";
  const pad = raw.startsWith("`") || raw.endsWith("`") ? " " : "";
  if (table) raw = raw.replace(/\|/g, "\\|");
  return `${ticks}${pad}${raw}${pad}${ticks}`;
}

// Render a node's children as an inline Markdown string.
function renderInline(node, table = false) {
  let out = "";
  for (const child of node.children || []) {
    if (child.type === "text") {
      out += escInline(child.data, table);
      continue;
    }
    if (child.type !== "tag") continue;
    const $c = $(child);
    const tag = child.tagName;
    if (tag === "code") {
      out += inlineCode(child, table);
    } else if (tag === "strong" || tag === "b") {
      out += `**${renderInline(child, table)}**`;
    } else if (tag === "em" || tag === "i") {
      out += `*${renderInline(child, table)}*`;
    } else if (tag === "a") {
      const href = $c.attr("href") || "";
      const text = renderInline(child, table) || escInline($c.text(), table);
      const target = href.startsWith("#") ? rewriteHash(href.slice(1)) : href;
      out += `[${text}](${target})`;
    } else if (tag === "br") {
      out += " ";
    } else if (tag === "span" && $c.hasClass("chip")) {
      out += `<Chip>${renderInline(child, table)}</Chip>`;
    } else if (tag === "span" && $c.hasClass("arch")) {
      out += `<Arch>${renderInline(child, table)}</Arch>`;
    } else if (tag === "span" && $c.hasClass("mod")) {
      // handled by QA summary; skip inline
    } else if (tag === "sup" || tag === "sub") {
      out += `<${tag}>${renderInline(child, table)}</${tag}>`;
    } else {
      out += renderInline(child, table);
    }
  }
  return out.replace(/[ \t]+/g, " ");
}

function labelOf($el) {
  return attr($el.children(".lab").first().text().trim());
}

function codeLang($fig, code) {
  if ($fig.hasClass("output")) return "text";
  const first = code.split("\n").find((l) => l.trim()) || "";
  if (/^\s*\$|^\s*(uv|pip|pipx|npm|npx|cd|git|docker|docker-compose|curl|export|source|python)\b/.test(first))
    return "bash";
  if (/^\s*[[{]/.test(first) && /["\d]/.test(first)) return "json";
  return "python";
}

// Render a node's children as a list of block-level MDX strings.
function renderBlocks(node) {
  const blocks = [];
  let inlineBuf = "";
  const flushInline = () => {
    const t = inlineBuf.trim();
    if (t) blocks.push(t);
    inlineBuf = "";
  };

  for (const child of node.children || []) {
    if (child.type === "text") {
      if (child.data.trim()) inlineBuf += escInline(child.data);
      continue;
    }
    if (child.type === "comment") continue;
    if (child.type !== "tag") continue;
    const $c = $(child);
    const tag = child.tagName;
    const cls = $c.attr("class") || "";

    if (INLINE_TAGS.has(tag)) {
      inlineBuf += renderInline({ children: [child] });
      continue;
    }
    flushInline();

    if (tag === "p") {
      const t = renderInline(child).trim();
      if (t) blocks.push(t);
    } else if (/^h[1-6]$/.test(tag)) {
      const depth = Number(tag[1]);
      const hashes = "#".repeat(Math.min(Math.max(depth, 2), 4));
      const id = $c.attr("id");
      const line = `${hashes} ${renderInline(child).trim()}`;
      blocks.push(id ? `<span id="${attr(id)}" />\n\n${line}` : line);
    } else if (tag === "ul" || tag === "ol") {
      const marker = (i) => (tag === "ol" ? `${i + 1}. ` : "- ");
      const items = $c
        .children("li")
        .toArray()
        .map((li, i) => marker(i) + renderInline(li).trim());
      blocks.push(items.join("\n"));
    } else if (tag === "dl") {
      const parts = ["<DefList>"];
      $c.children().each((_, d) => {
        if (d.tagName === "dt") parts.push(`  <Term>${renderInline(d).trim()}</Term>`);
        else if (d.tagName === "dd") parts.push(`  <Def>${renderInline(d).trim()}</Def>`);
      });
      parts.push("</DefList>");
      blocks.push(parts.join("\n"));
    } else if (tag === "figure" && $c.hasClass("code")) {
      const cap = $c.find("figcaption").clone();
      cap.children(".d").remove();
      const title = attr(cap.text().trim());
      const code = $c.find("pre code").text().replace(/\n+$/, "");
      const lang = codeLang($c, code);
      const meta = title ? ` title="${title}"` : "";
      blocks.push("```" + lang + meta + "\n" + code + "\n```");
    } else if (tag === "figure") {
      blocks.push(...renderBlocks(child));
    } else if (tag === "table") {
      blocks.push(renderTable($c));
    } else if (tag === "div" && $c.hasClass("tbl-wrap")) {
      $c.children("table").each((_, t) => blocks.push(renderTable($(t))));
    } else if (tag === "div" && $c.hasClass("box")) {
      const kind = ["def", "analogy", "practice", "warn"].find((k) => $c.hasClass(k)) || "def";
      blocks.push(wrap(`<Box kind="${kind}" label="${labelOf($c)}">`, bodyWithoutLab($c), "</Box>"));
    } else if (tag === "div" && $c.hasClass("checkpoint")) {
      blocks.push(wrap(`<Checkpoint label="${labelOf($c)}">`, bodyWithoutLab($c), "</Checkpoint>"));
    } else if (tag === "div" && $c.hasClass("recap")) {
      const lvl = (cls.match(/\bl(\d)\b/) || [, "1"])[1];
      blocks.push(wrap(`<Recap level={${lvl}} label="${labelOf($c)}">`, bodyWithoutLab($c), "</Recap>"));
    } else if (tag === "div" && $c.hasClass("avoid")) {
      blocks.push(wrap(`<Avoid label="${labelOf($c)}">`, bodyWithoutLab($c), "</Avoid>"));
    } else if (tag === "div" && $c.hasClass("flow")) {
      blocks.push(renderFlow($c));
    } else if (tag === "div" && $c.hasClass("flowcap")) {
      blocks.push(`<FlowCap>${renderInline(child).trim()}</FlowCap>`);
    } else if (tag === "div" && $c.hasClass("quiz")) {
      blocks.push(renderQuiz($c));
    } else if (tag === "details" && $c.hasClass("qa")) {
      blocks.push(renderQA($c));
    } else if (tag === "details" && $c.hasClass("sol")) {
      const summary = attr($c.children("summary").first().text().trim() || "Ver una solución");
      const body = $c.find(".sbody").first();
      blocks.push(wrap(`<Solution summary="${summary}">`, body.length ? body[0] : child, "</Solution>"));
    } else if (tag === "div" && $c.hasClass("grid3")) {
      blocks.push(renderGrid($c));
    } else if (tag === "div" && $c.hasClass("ivblock")) {
      blocks.push(wrap("<IvBlock>", child, "</IvBlock>"));
    } else if (tag === "div" && $c.hasClass("lvbanner")) {
      const lvl = (($c.attr("style") || "").match(/--l(\d)/) || [, "1"])[1];
      const title = attr($c.children(".k").first().text().trim());
      const rest = $c.clone();
      rest.children(".k").remove();
      blocks.push(wrap(`<LevelBanner level={${lvl}} title="${title}">`, rest[0], "</LevelBanner>"));
    } else if (tag === "div" && $c.hasClass("formula")) {
      blocks.push(wrap("<Formula>", child, "</Formula>"));
    } else if (tag === "div" && ($c.hasClass("note-src") || $c.hasClass("ruta"))) {
      blocks.push(wrap("<Note>", child, "</Note>"));
    } else if (tag === "div" || tag === "section" || tag === "article") {
      blocks.push(...renderBlocks(child)); // transparent container
    }
    // silently ignore purely-decorative leftovers (e.g. empty status divs)
  }
  flushInline();
  return blocks;
}

// A cheerio element clone with the .lab child removed (its text became a prop).
function bodyWithoutLab($el) {
  const c = $el.clone();
  c.children(".lab").remove();
  return c[0];
}

// Wrap children blocks inside a JSX component with blank lines so MDX parses
// the children as block content.
function wrap(open, childNode, close) {
  const inner = renderBlocks(childNode).join("\n\n");
  return `${open}\n\n${inner}\n\n${close}`;
}

function renderTable($t) {
  const head = $t
    .find("thead th")
    .toArray()
    .map((th) => renderInline(th, true).trim());
  const rows = $t
    .find("tbody tr")
    .toArray()
    .map((tr) =>
      $(tr)
        .children("td,th")
        .toArray()
        .map((td) => renderInline(td, true).trim())
    );
  const cols = head.length || (rows[0] ? rows[0].length : 0);
  const header = head.length ? head : new Array(cols).fill(" ");
  const sep = new Array(cols).fill("---");
  const line = (cells) => `| ${cells.join(" | ")} |`;
  return [line(header), line(sep), ...rows.map((r) => line(r))].join("\n");
}

function renderFlow($f) {
  const parts = ["<Flow>"];
  $f.children().each((_, el) => {
    const $el = $(el);
    if ($el.hasClass("step")) {
      const n = attr($el.children(".num").text().trim());
      const title = attr($el.children(".ti").text().trim());
      const de = renderInline($el.children(".de")[0] || el).trim();
      parts.push(`  <Step n="${n}" title="${title}">${de}</Step>`);
    } else if ($el.hasClass("flowcap")) {
      parts.push(`  <FlowCap>${renderInline(el).trim()}</FlowCap>`);
    }
  });
  parts.push("</Flow>");
  return parts.join("\n");
}

function renderQuiz($q) {
  const title = attr($q.children(".qhead").first().text().trim());
  const parts = [`<Quiz title="${title}">`, ""];
  $q.children(".q").each((_, q) => {
    const $qq = $(q);
    parts.push("<Question>");
    parts.push(`  <Prompt>${renderInline($qq.children(".enun")[0] || q).trim()}</Prompt>`);
    $qq.find(".opts button").each((_, b) => {
      const ok = $(b).is("[data-ok]") ? " ok" : "";
      parts.push(`  <Option${ok}>${renderInline(b).trim()}</Option>`);
    });
    const fb = $qq.children(".fb").first();
    if (fb.length) parts.push(`  <Feedback>${renderInline(fb[0]).trim()}</Feedback>`);
    parts.push("</Question>", "");
  });
  parts.push("</Quiz>");
  return parts.join("\n");
}

function renderQA($d) {
  const summaryEl = $d.children("summary").first();
  const mod = attr(summaryEl.find(".mod").text().trim());
  const sClone = summaryEl.clone();
  sClone.children(".mod").remove();
  const summary = renderInline(sClone[0]).trim();
  const ans = $d.find(".ans").first();
  const inner = renderBlocks(ans.length ? ans[0] : $d[0]).join("\n\n");
  return [
    `<QA mod="${mod}">`,
    `  <QSummary>${summary}</QSummary>`,
    "  <QAnswer>",
    "",
    inner,
    "",
    "  </QAnswer>",
    "</QA>",
  ].join("\n");
}

function renderGrid($g) {
  const parts = ["<Grid3>", ""];
  $g.children(".ccard").each((_, c) => {
    const $c = $(c);
    const num = attr($c.children(".cardnum").text().trim());
    const title = attr($c.children("h4").text().trim());
    const rest = $c.clone();
    rest.children(".cardnum,h4").remove();
    const body = renderBlocks(rest[0]).join("\n\n");
    parts.push(`<Card num="${num}" title="${title}">`, "", body, "", "</Card>", "");
  });
  parts.push("</Grid3>");
  return parts.join("\n");
}

// ---------------------------------------------------------------------------
// Per-section conversion.
// ---------------------------------------------------------------------------
function convertSection(sec) {
  const id = sec.attribs.id;
  const $sec = $(sec);
  const col = $sec.children(".col").first();
  const root = col.length ? col : $sec;
  const work = $(root).clone();

  // Extract header metadata, then remove those nodes from the body.
  const modtag = work.children(".modtag").first();
  const levelFromTag = (modtag.attr("class") || "").match(/\bl(\d)\b/);
  const h2 = work.children("h2").first();
  const title = h2.text().trim();
  const fileref = work.find(".fileref").first();
  const filerefText = fileref.text().trim();
  const tested = fileref.find(".tested").length > 0;
  const modmeta = work.children(".modmeta").first();
  const metaSpans = modmeta.children("span").toArray().map((s) => $(s).text().trim());

  const pyMatch = filerefText.match(/([\w./-]*\/)?(\d[\w-]*\.py)\b/);
  const pyFile = pyMatch ? pyMatch[2] : null;

  const navInfo = nav.get(id);
  const extra = isExtra(id);
  const level = navInfo?.level ?? (levelFromTag ? Number(levelFromTag[1]) : 5);

  const meta = {
    id,
    slug: sectionSlug(id),
    title: title || navInfo?.navTitle || id,
    kind: extra ? "extra" : "module",
    level,
    levelName: navInfo?.levelName ?? "",
    order: navInfo?.order ?? 999,
    badge: navInfo?.badge ?? "",
    pyFile,
    fileref: filerefText || null,
    tested,
    goals: metaSpans[0] || null,
    prereqs: metaSpans[1] || null,
    minutes: metaSpans[2] || null,
  };

  // Strip header nodes (kept in meta) but preserve lvbanner (it is content).
  modtag.remove();
  h2.remove();
  fileref.closest(".fileref").remove();
  modmeta.remove();

  // Compute the expected plain text from the SAME body we serialize (headers
  // already relocated to meta), inserting whitespace at every tag boundary so
  // inline siblings don't fuse into chimera tokens.
  const originalText = htmlToText(work.html() || "");

  const body = renderBlocks(work[0]).join("\n\n");
  const mdx = `export const meta = ${JSON.stringify(meta, null, 2)};\n\n${body}\n`;

  return { id, meta, mdx, originalText };
}

// ---------------------------------------------------------------------------
// Fidelity gate.
// ---------------------------------------------------------------------------
function normalizeText(s) {
  return s.replace(/\s+/g, " ").trim();
}
// Strip tags to spaces, then decode entities via a throwaway parse, so the
// result is comparable to the space-separated text reconstructed from MDX.
function htmlToText(htmlStr) {
  const spaced = htmlStr.replace(/<[^>]+>/g, " ");
  return normalizeText(load(`<div>${spaced}</div>`).text());
}
const STOP = new Set(["para", "como", "esto", "esta", "este", "pero", "porque", "cuando", "donde"]);
function tokens(s) {
  const set = new Set();
  for (const w of s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").split(/[^a-z0-9]+/)) {
    if (w.length >= 5 && !/^\d+$/.test(w) && !STOP.has(w)) set.add(w);
  }
  return set;
}
function gotText(mdx, meta) {
  // Reconstruct plain text from generated MDX to detect dropped content.
  const props = [];
  mdx.replace(/(?:label|title|summary|num|n)="([^"]*)"/g, (_, v) => (props.push(v), ""));
  // Set code aside FIRST: both fenced blocks and inline spans legitimately
  // contain "<" (e.g. `if t <= 0:` or `onnxruntime<1.24`), which the tag
  // stripper below would otherwise treat as an opening tag and eat.
  const codes = [];
  let t = mdx
    .replace(/^export const meta[\s\S]*?;\n/, "")
    .replace(/```[^\n]*\n([\s\S]*?)```/g, (_, code) => (codes.push(code), " "))
    .replace(/``([^\n]+?)``/g, (_, code) => (codes.push(code), " "))
    .replace(/`([^`\n]+)`/g, (_, code) => (codes.push(code), " "));
  t = t
    .replace(/<[^>]+>/g, " ")
    .replace(/\\([\\`<{}|])/g, "$1")
    .replace(/[*_#>|]/g, " ")
    .replace(/`+/g, " ");
  const metaText = [meta.title, meta.fileref, meta.goals, meta.prereqs, meta.minutes]
    .filter(Boolean)
    .join(" ");
  return [t, codes.join(" "), props.join(" "), metaText].join(" ");
}

function runCheck(results) {
  const report = { counts: {}, sections: results.length, missingBySections: {}, ok: true };

  const expect = {
    Box: $(".box").length,
    Quiz: $(".quiz").length,
    Question: $(".q").length,
    Checkpoint: $(".checkpoint").length,
    Recap: $(".recap").length,
    Avoid: $(".avoid").length,
    Flow: $(".flow").length,
    Step: $(".step").length,
    Grid3: $(".grid3").length,
    Card: $(".ccard").length,
    QA: $("details.qa").length,
    Solution: $("details.sol").length,
    codeFence: $("figure.code").length,
    table: $("table").length,
  };
  const allMdx = results.map((r) => r.mdx).join("\n");
  const countTag = (t) => (allMdx.match(new RegExp(`<${t}[\\s>]`, "g")) || []).length;
  const got = {
    Box: countTag("Box"),
    Quiz: countTag("Quiz"),
    Question: countTag("Question"),
    Checkpoint: countTag("Checkpoint"),
    Recap: countTag("Recap"),
    Avoid: countTag("Avoid"),
    Flow: countTag("Flow"),
    Step: countTag("Step"),
    Grid3: countTag("Grid3"),
    Card: countTag("Card"),
    QA: countTag("QA"),
    Solution: countTag("Solution"),
    codeFence: (allMdx.match(/^```[a-z]/gm) || []).length,
    table: (allMdx.match(/^\| --- /gm) || []).length,
  };

  for (const k of Object.keys(expect)) {
    const pass = expect[k] === got[k];
    report.counts[k] = { expect: expect[k], got: got[k], pass };
    if (!pass) report.ok = false;
  }

  let totalMissing = 0;
  for (const r of results) {
    const exp = tokens(r.originalText);
    const gt = tokens(gotText(r.mdx, r.meta));
    const missing = [...exp].filter((w) => !gt.has(w));
    if (missing.length) {
      report.missingBySections[r.meta.slug] = missing.slice(0, 40);
      totalMissing += missing.length;
      if (missing.length > 3) report.ok = false; // small tolerance for tokenizer noise
    }
  }
  report.totalMissingTokens = totalMissing;
  return report;
}

// ---------------------------------------------------------------------------
// Main.
// ---------------------------------------------------------------------------
for (const dir of [OUT_MODULES, OUT_EXTRAS]) {
  if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
}

const results = sections.map(convertSection);
const manifest = { generatedAt: new Date().toISOString(), total: results.length, modules: [], extras: [] };

for (const r of results) {
  const out = r.meta.kind === "extra" ? OUT_EXTRAS : OUT_MODULES;
  writeFileSync(join(out, `${r.meta.slug}.mdx`), r.mdx, "utf8");
  const entry = { ...r.meta };
  (r.meta.kind === "extra" ? manifest.extras : manifest.modules).push(entry);
}
manifest.modules.sort((a, b) => a.order - b.order);
writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2) + "\n", "utf8");

console.log(`✓ Wrote ${manifest.modules.length} modules + ${manifest.extras.length} extras (${results.length} sections).`);

if (CHECK) {
  const report = runCheck(results);
  writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2) + "\n", "utf8");
  console.log("\nFidelity gate:");
  for (const [k, v] of Object.entries(report.counts)) {
    console.log(`  ${v.pass ? "✓" : "✗"} ${k.padEnd(10)} expect ${v.expect}  got ${v.got}`);
  }
  console.log(`  total missing tokens: ${report.totalMissingTokens}`);
  const bad = Object.entries(report.missingBySections).filter(([, m]) => m.length > 3);
  if (bad.length) {
    console.log("\n  sections with dropped content:");
    for (const [slug, m] of bad) console.log(`    ${slug}: ${m.slice(0, 12).join(", ")}${m.length > 12 ? " …" : ""}`);
  }
  console.log(`\n${report.ok ? "✓ GATE PASSED" : "✗ GATE FAILED"}`);
  if (!report.ok) process.exit(1);
}
