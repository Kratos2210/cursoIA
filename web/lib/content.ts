import manifest from "@/content/modules.manifest.json";

export type ContentMeta = {
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

export const modules = manifest.modules as ContentMeta[];
export const extras = manifest.extras as ContentMeta[];

export function moduleBySlug(slug: string): ContentMeta | undefined {
  return modules.find((m) => m.slug === slug);
}
export function extraBySlug(slug: string): ContentMeta | undefined {
  return extras.find((m) => m.slug === slug);
}

/** Modules grouped by their nav level section, preserving order. */
export function modulesByLevel(): { level: number; levelName: string; items: ContentMeta[] }[] {
  const groups: { level: number; levelName: string; items: ContentMeta[] }[] = [];
  for (const m of modules) {
    let g = groups.find((x) => x.levelName === m.levelName);
    if (!g) {
      g = { level: m.level, levelName: m.levelName, items: [] };
      groups.push(g);
    }
    g.items.push(m);
  }
  return groups;
}
