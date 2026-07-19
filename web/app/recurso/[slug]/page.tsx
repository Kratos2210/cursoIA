import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { EXTRA_ITEMS, extraBySlug } from "@/lib/roadmap";
import { ModuleFooter } from "@/components/app/ModuleFooter";
import { OnThisPage } from "@/components/app/OnThisPage";
import { ReadingProgress } from "@/components/app/ReadingProgress";
import { KindTag } from "@/components/content/ui";

export const dynamicParams = false;

export function generateStaticParams() {
  return EXTRA_ITEMS.map((i) => ({ slug: i.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const item = extraBySlug(slug);
  return { title: item ? `${item.title} · AI Engineer` : "AI Engineer" };
}

export default async function ExtraPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const item = extraBySlug(slug);
  if (!item) notFound();

  const { default: Content } = await import(`../../../content/extras/${slug}.mdx`);

  return (
    <>
      <ReadingProgress />
      <div className="view mod-view">
        <div className="mod-main">
          <article className="article">
            <KindTag colorVar="--accent">Referencia</KindTag>
            <h1>{item.title}</h1>
            <Content />
          </article>
          <ModuleFooter id={item.id} prev={null} next={null} />
        </div>
        <OnThisPage />
      </div>
    </>
  );
}
