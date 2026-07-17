import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ITEMS, projectBySlug, neighbors } from "@/lib/roadmap";
import { ModuleFooter } from "@/components/app/ModuleFooter";
import { ComingSoon } from "@/components/app/ComingSoon";

export const dynamicParams = false;

export function generateStaticParams() {
  return ITEMS.filter((i) => i.kind === "project").map((i) => ({ slug: i.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const item = projectBySlug(slug);
  return { title: item ? `Proyecto · ${item.title} · AI Engineer` : "AI Engineer" };
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const item = projectBySlug(slug);
  if (!item) notFound();

  const { prev, next } = neighbors(item.id);

  return (
    <div className="view">
      <ComingSoon item={item} />
      <ModuleFooter id={item.id} prev={prev} next={next} />
    </div>
  );
}
