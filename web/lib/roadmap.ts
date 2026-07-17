// The v2 course model: 6 levels, each with modules + one integrator project.
// Ported verbatim from the "Curso IA Engineering v2" design prototype.
// Only modules flagged `built` have written content; the rest render "coming soon".

export type RoadmapModule = {
  id: string;
  num: string;
  title: string;
  built?: boolean;
};

export type RoadmapProject = {
  id: string;
  title: string;
  brief: string;
};

export type RoadmapLevel = {
  id: string;
  n: string;
  name: string;
  shortName: string;
  colorVar: string; // e.g. "--l1"
  desc: string;
  mods: RoadmapModule[];
  proj: RoadmapProject;
};

export const LEVELS: RoadmapLevel[] = [
  {
    id: "l1", n: "1", name: "Nivel 1 · Fundamentos", shortName: "1 · Fundamentos", colorVar: "--l1",
    desc: "Desde cero absoluto: preparar tu máquina, el Python justo y necesario, entender qué es un LLM y hablar con uno desde código.",
    mods: [
      { id: "m0", num: "00", title: "Preparar el terreno", built: true },
      { id: "m1", num: "01", title: "Python mínimo para IA" },
      { id: "m2x", num: "02", title: "¿Qué es un LLM realmente?" },
      { id: "m3", num: "03", title: "Tu primer modelo" },
      { id: "m2", num: "04", title: "Prompts + LCEL", built: true },
    ],
    proj: {
      id: "p1", title: "Chatbot de terminal con personalidad",
      brief: "Un asistente que corre en tu terminal: recibe texto, arma el prompt con una plantilla, llama al modelo vía LCEL y responde con una personalidad que tú defines. Une todo el nivel: entorno, .env, prompts y cadenas.",
    },
  },
  {
    id: "l2", n: "2", name: "Nivel 2 · Construye con LangChain", shortName: "2 · LangChain", colorVar: "--l2",
    desc: "De cadenas simples a aplicaciones útiles: datos estructurados, memoria de conversación, herramientas y flujos con ramas.",
    mods: [
      { id: "m5", num: "05", title: "Salida estructurada" },
      { id: "m4", num: "06", title: "Memoria conversacional" },
      { id: "m6", num: "07", title: "Runnables de composición" },
      { id: "m7", num: "08", title: "Herramientas (tools)" },
      { id: "m8", num: "09", title: "Routing y ramas" },
    ],
    proj: {
      id: "p2", title: "Analizador de reseñas con herramientas",
      brief: "Un pipeline que lee reseñas de clientes, clasifica el sentimiento con salida estructurada (JSON validado), decide con routing si escalar la queja, y usa una herramienta para registrar el resultado. Tu primer sistema con decisiones.",
    },
  },
  {
    id: "l3", n: "3", name: "Nivel 3 · RAG", shortName: "3 · RAG", colorVar: "--l3",
    desc: "Que el modelo responda con TUS documentos: embeddings, bases vectoriales, chunking y recuperación de calidad profesional.",
    mods: [
      { id: "m10x", num: "10", title: "Embeddings y vectores" },
      { id: "m11x", num: "11", title: "Vector stores y chunking" },
      { id: "m11", num: "12", title: "RAG profesional" },
      { id: "m12", num: "13", title: "Recuperar + re-rankear" },
    ],
    proj: {
      id: "p3", title: "“Chatea con tus PDFs”",
      brief: "Una app que ingiere tus PDFs, los trocea, los indexa en una base vectorial y responde preguntas citando la página de donde salió cada dato. El proyecto que todo AI Engineer tiene en su portafolio — el tuyo citará fuentes de verdad.",
    },
  },
  {
    id: "l4", n: "4", name: "Nivel 4 · Agentes con LangGraph", shortName: "4 · Agentes", colorVar: "--l4",
    desc: "Sistemas que piensan en ciclo: agentes con herramientas, grafos de estado, equipos multiagente y el protocolo MCP.",
    mods: [
      { id: "m10", num: "14", title: "Agentes (prebuilt)" },
      { id: "m13", num: "15", title: "LangGraph a fondo" },
      { id: "m9", num: "16", title: "Resiliencia + async" },
      { id: "m15", num: "17", title: "Multiagente (supervisor)" },
      { id: "m14", num: "18", title: "MCP" },
    ],
    proj: {
      id: "p4", title: "Agente investigador autónomo",
      brief: "Un agente que recibe una pregunta amplia, planifica sub-tareas, busca en tus documentos y en la web, se auto-corrige cuando una ruta falla y entrega un informe con fuentes. Construido como grafo en LangGraph, con memoria persistente.",
    },
  },
  {
    id: "l5", n: "5", name: "Nivel 5 · Producción", shortName: "5 · Producción", colorVar: "--l5",
    desc: "Del script al sistema: observabilidad, evaluación, seguridad, estructura de repo profesional, tests y CI.",
    mods: [
      { id: "m16", num: "19", title: "Observabilidad y evaluación" },
      { id: "m23", num: "20", title: "Seguridad" },
      { id: "m17", num: "21", title: "Repo productivo" },
      { id: "m17b", num: "22", title: "Tests y CI" },
    ],
    proj: {
      id: "p5", title: "API de agentes en producción",
      brief: "Empaqueta tu agente investigador como una API con FastAPI: trazas en LangSmith, evaluaciones automáticas, guardrails de seguridad, tests en CI y despliegue. La diferencia entre “me funciona en mi laptop” e ingeniería.",
    },
  },
  {
    id: "l6", n: "6", name: "Nivel 6 · AI Engineer", shortName: "6 · AI Engineer", colorVar: "--l6",
    desc: "Las técnicas que separan al ingeniero: RAG avanzado, cuándo hacer fine-tuning, cómo funciona un LLM por dentro — y tu capstone.",
    mods: [
      { id: "m20", num: "23", title: "RAG avanzado" },
      { id: "m21", num: "24", title: "Fine-tuning vs RAG" },
      { id: "m27", num: "25", title: "El LLM por dentro" },
      { id: "examen", num: "✦", title: "Examen final" },
    ],
    proj: {
      id: "p6", title: "Capstone: tu producto de IA end-to-end",
      brief: "Tu propio producto, de la idea al despliegue: eliges el problema, justificas la arquitectura (RAG vs fine-tuning, agente vs cadena), lo construyes, lo evalúas y lo defiendes. Es la pieza central de tu portafolio de AI Engineer.",
    },
  },
];

// ---- Flattened, navigable item model ---------------------------------------

export type Item = {
  id: string;
  kind: "module" | "project";
  num: string;
  title: string;
  built: boolean;
  brief?: string;
  slug: string;
  href: string;
  levelName: string;
  levelShort: string;
  colorVar: string;
};

function moduleSlug(m: RoadmapModule): string {
  return /^\d+$/.test(m.num) ? m.num : m.id;
}

function toItems(): Item[] {
  const items: Item[] = [];
  for (const lvl of LEVELS) {
    for (const m of lvl.mods) {
      const slug = moduleSlug(m);
      items.push({
        id: m.id, kind: "module", num: m.num, title: m.title, built: !!m.built,
        slug, href: `/modulo/${slug}`,
        levelName: lvl.name, levelShort: lvl.shortName, colorVar: lvl.colorVar,
      });
    }
    items.push({
      id: lvl.proj.id, kind: "project", num: "★", title: lvl.proj.title, built: false,
      brief: lvl.proj.brief, slug: lvl.n, href: `/proyecto/${lvl.n}`,
      levelName: lvl.name, levelShort: lvl.shortName, colorVar: lvl.colorVar,
    });
  }
  return items;
}

/** Flat list in course order: level mods then the level project, level by level. */
export const ITEMS: Item[] = toItems();

export const ALL_IDS: string[] = ITEMS.map((i) => i.id);

export function moduleBySlug(slug: string): Item | undefined {
  return ITEMS.find((i) => i.kind === "module" && i.slug === slug);
}
export function projectBySlug(slug: string): Item | undefined {
  return ITEMS.find((i) => i.kind === "project" && i.slug === slug);
}
export function itemById(id: string): Item | undefined {
  return ITEMS.find((i) => i.id === id);
}

/** Previous / next across the flat item list (modules and projects interleaved). */
export function neighbors(id: string): { prev: Item | null; next: Item | null } {
  const idx = ITEMS.findIndex((i) => i.id === id);
  return {
    prev: idx > 0 ? ITEMS[idx - 1] : null,
    next: idx >= 0 && idx < ITEMS.length - 1 ? ITEMS[idx + 1] : null,
  };
}

export const TOTAL_MODULES = ITEMS.filter((i) => i.kind === "module").length;
export const TOTAL_PROJECTS = ITEMS.filter((i) => i.kind === "project").length;
export const TOTAL_ITEMS = ITEMS.length;
