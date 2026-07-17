import manifest from "@/content/modules.manifest.json";

// The full course (all 37 modules + 7 extras from the original curso-langchain.html,
// converted to MDX in F1) presented in the v2 "AI Engineer roadmap" design.
// Levels come straight from the manifest's nav grouping; here we just relabel
// each group with a v2 display name + color ramp.

type ManifestItem = {
  id: string;
  slug: string;
  title: string;
  kind: "module" | "extra";
  level: number;
  levelName: string;
  order: number;
  badge: string;
  pyFile: string | null;
  fileref: string | null;
  tested: boolean;
  goals: string | null;
  prereqs: string | null;
  minutes: string | null;
};

const MODULES = manifest.modules as ManifestItem[];
const EXTRAS = manifest.extras as ManifestItem[];

// Original nav group -> v2 level display name + color.
const LEVEL_STYLE: Record<string, { name: string; short: string; colorVar: string }> = {
  "Básico": { name: "Nivel 1 · Fundamentos", short: "1 · Fundamentos", colorVar: "--l1" },
  "Intermedio": { name: "Nivel 2 · Construye con LangChain", short: "2 · LangChain", colorVar: "--l2" },
  "Avanzado": { name: "Nivel 3 · RAG y Agentes", short: "3 · RAG y Agentes", colorVar: "--l3" },
  "Producción": { name: "Nivel 4 · Producción", short: "4 · Producción", colorVar: "--l4" },
  "Proyecto": { name: "Nivel 5 · Proyecto", short: "5 · Proyecto", colorVar: "--l5" },
  "AI Engineer": { name: "Nivel 6 · AI Engineer", short: "6 · AI Engineer", colorVar: "--l6" },
};
const FALLBACK = { name: "Curso", short: "Curso", colorVar: "--accent" };

export type Item = {
  id: string;
  slug: string;
  num: string;
  title: string;
  href: string;
  kind: "module" | "extra";
  levelKey: string;
  levelName: string;
  levelShort: string;
  colorVar: string;
  pyFile: string | null;
  tested: boolean;
  goals: string | null;
  prereqs: string | null;
  minutes: string | null;
};

function toItem(m: ManifestItem): Item {
  const style = LEVEL_STYLE[m.levelName] ?? FALLBACK;
  const isExtra = m.kind === "extra";
  return {
    id: m.id,
    slug: m.slug,
    num: m.badge || (isExtra ? "✦" : m.slug.split("-")[0]),
    title: m.title,
    href: isExtra ? `/recurso/${m.slug}` : `/modulo/${m.slug}`,
    kind: m.kind,
    levelKey: m.levelName,
    levelName: style.name,
    levelShort: style.short,
    colorVar: style.colorVar,
    pyFile: m.pyFile,
    tested: m.tested,
    goals: m.goals,
    prereqs: m.prereqs,
    minutes: m.minutes,
  };
}

export type Level = {
  key: string;
  name: string;
  short: string;
  colorVar: string;
  items: Item[];
};

export const LEVELS: Level[] = (() => {
  const groups: Level[] = [];
  for (const m of MODULES) {
    const style = LEVEL_STYLE[m.levelName] ?? FALLBACK;
    let g = groups.find((x) => x.key === m.levelName);
    if (!g) {
      g = { key: m.levelName, name: style.name, short: style.short, colorVar: style.colorVar, items: [] };
      groups.push(g);
    }
    g.items.push(toItem(m));
  }
  return groups;
})();

/** Ordered list of every module (for prev/next). Extras are navigated separately. */
export const MODULE_ITEMS: Item[] = LEVELS.flatMap((l) => l.items);
export const EXTRA_ITEMS: Item[] = EXTRAS.map(toItem);
export const ALL_ITEMS: Item[] = [...MODULE_ITEMS, ...EXTRA_ITEMS];
export const ALL_IDS: string[] = ALL_ITEMS.map((i) => i.id);

export const TOTAL_MODULES = MODULE_ITEMS.length;
export const TOTAL_LEVELS = LEVELS.length;
export const TOTAL_EXTRAS = EXTRA_ITEMS.length;

export function moduleBySlug(slug: string): Item | undefined {
  return MODULE_ITEMS.find((i) => i.slug === slug);
}
export function extraBySlug(slug: string): Item | undefined {
  return EXTRA_ITEMS.find((i) => i.slug === slug);
}
export function neighbors(id: string): { prev: Item | null; next: Item | null } {
  const idx = MODULE_ITEMS.findIndex((i) => i.id === id);
  return {
    prev: idx > 0 ? MODULE_ITEMS[idx - 1] : null,
    next: idx >= 0 && idx < MODULE_ITEMS.length - 1 ? MODULE_ITEMS[idx + 1] : null,
  };
}
