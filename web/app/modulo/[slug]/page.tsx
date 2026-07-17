import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ITEMS, moduleBySlug, neighbors } from "@/lib/roadmap";
import { ModuleFooter } from "@/components/app/ModuleFooter";
import { ComingSoon } from "@/components/app/ComingSoon";
import { M00 } from "@/components/modules/M00";
import { M04 } from "@/components/modules/M04";

export const dynamicParams = false;

export function generateStaticParams() {
  return ITEMS.filter((i) => i.kind === "module").map((i) => ({ slug: i.slug }));
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
  const content = slug === "00" ? <M00 /> : slug === "04" ? <M04 /> : <ComingSoon item={item} />;

  return (
    <div className="view">
      {content}
      <ModuleFooter id={item.id} prev={prev} next={next} />
    </div>
  );
}
