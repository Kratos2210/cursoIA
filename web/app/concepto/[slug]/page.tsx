import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { MODULE_ITEMS, moduleBySlug, neighbors } from "@/lib/roadmap";
import { ModuleFooter } from "@/components/app/ModuleFooter";
import { OnThisPage } from "@/components/app/OnThisPage";
import { ReadingProgress } from "@/components/app/ReadingProgress";
import { KindTag, FileRef, MetaChip } from "@/components/content/ui";
import { VideoEmbed } from "@/components/app/VideoEmbed";
import { ListenButton } from "@/components/app/ListenButton";

export const dynamicParams = false;

// Split a meta string like "🎯 Al terminar sabrás: X" into its emoji, its label
// ("Al terminar sabrás") and the rest, so the header renders structured chips
// instead of one long raw string.
function parseChip(raw: string): { icon: string; label?: string; text: string } {
  const sp = raw.indexOf(" ");
  const icon = sp === -1 ? "" : raw.slice(0, sp);
  const body = (sp === -1 ? raw : raw.slice(sp + 1)).trim();
  const c = body.indexOf(": ");
  if (c !== -1 && c <= 28) {
    return { icon, label: body.slice(0, c), text: body.slice(c + 2).trim() };
  }
  return { icon, text: body };
}

export function generateStaticParams() {
  return MODULE_ITEMS.map((i) => ({ slug: i.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const item = moduleBySlug(slug);
  return { title: item ? `${item.num} · ${item.title} · AI Engineer` : "AI Engineer" };
}

export default async function ModulePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const item = moduleBySlug(slug);
  if (!item) notFound();

  const { prev, next } = neighbors(item.id);
  const { default: Content } = await import(`../../../content/modules/${slug}.mdx`);
  const chips = [
    item.goals ? { ...parseChip(item.goals), wide: true, key: "goals" } : null,
    item.prereqs ? { ...parseChip(item.prereqs), key: "prereqs" } : null,
    item.minutes ? { ...parseChip(item.minutes), key: "minutes" } : null,
  ].filter(Boolean) as { icon: string; label?: string; text: string; wide?: boolean; key: string }[];

  return (
    <>
      <ReadingProgress />
      <div className="view mod-view">
      <div className="mod-main">
        <article className="article">
          <nav className="crumbs" aria-label="Ruta de navegación">
            <Link href="/">Inicio</Link>
            <span aria-hidden="true">›</span>
            <Link href="/#roadmap">{item.levelShort}</Link>
            <span aria-hidden="true">›</span>
            <span aria-current="page">Concepto {item.num}</span>
          </nav>
          <KindTag colorVar={item.colorVar}>
            {item.levelName} · Concepto {item.num}
          </KindTag>
          <h1>{item.title}</h1>
          {item.pyFile ? (
            <FileRef file={item.pyFile} tested={item.tested} />
          ) : (
            <div className="fileref">
              {item.fileref ?? "📖 Concepto de lectura — sin script asociado"}
            </div>
          )}
          {chips.length ? (
            <div className="meta-chips">
              {chips.map((c) => (
                <MetaChip key={c.key} icon={c.icon} label={c.label} wide={c.wide}>
                  {c.text}
                </MetaChip>
              ))}
            </div>
          ) : null}
          {item.videoUrl ? <VideoEmbed url={item.videoUrl} title={item.title} /> : null}
          <ListenButton title={item.title} goals={item.goals} />
          <Content />
        </article>
        <ModuleFooter id={item.id} prev={prev} next={next} />
      </div>
      <OnThisPage />
      </div>
    </>
  );
}
