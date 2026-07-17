import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { MODULE_ITEMS, moduleBySlug, neighbors } from "@/lib/roadmap";
import { ModuleFooter } from "@/components/app/ModuleFooter";
import { OnThisPage } from "@/components/app/OnThisPage";
import { ReadingProgress } from "@/components/app/ReadingProgress";
import { KindTag, FileRef } from "@/components/content/ui";

export const dynamicParams = false;

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
  const chips = [item.goals, item.prereqs, item.minutes].filter(Boolean) as string[];

  return (
    <>
      <ReadingProgress />
      <div className="view mod-view">
      <div className="mod-main">
        <article className="article">
          <KindTag colorVar={item.colorVar}>
            {item.levelName} · Módulo {item.num}
          </KindTag>
          <h1>{item.title}</h1>
          {item.pyFile ? <FileRef file={item.pyFile} tested={item.tested} /> : null}
          {chips.length ? (
            <div className="meta-chips">
              {chips.map((c, i) => (
                <span className="meta-chip" key={i}>
                  {c}
                </span>
              ))}
            </div>
          ) : null}
          <Content />
        </article>
        <ModuleFooter id={item.id} prev={prev} next={next} />
      </div>
      <OnThisPage />
      </div>
    </>
  );
}
