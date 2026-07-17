import { notFound } from "next/navigation";
import { modules, moduleBySlug } from "@/lib/content";

// F1: minimal module page proving every MDX compiles as a static route.
// The full shell (sidebar, prev/next, styled header) lands in F2.
export const dynamicParams = false;

export function generateStaticParams() {
  return modules.map((m) => ({ slug: m.slug }));
}

export default async function ModulePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const meta = moduleBySlug(slug);
  if (!meta) notFound();

  const { default: Content } = await import(`../../../content/modules/${slug}.mdx`);

  return (
    <main className="prose">
      <p className="modtag">
        {meta.levelName} · Módulo {meta.badge}
      </p>
      <h2>{meta.title}</h2>
      <Content />
    </main>
  );
}
