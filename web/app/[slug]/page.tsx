import { notFound } from "next/navigation";
import { extras, extraBySlug } from "@/lib/content";

// F1: minimal page for the "extra" sections (examen, entrevista, faq,
// cheat-sheet, mapa, llmops, ejercicios). Dedicated routes for some of these
// (ejercicios, proyectos) arrive in F3.
export const dynamicParams = false;

export function generateStaticParams() {
  return extras.map((m) => ({ slug: m.slug }));
}

export default async function ExtraPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const meta = extraBySlug(slug);
  if (!meta) notFound();

  const { default: Content } = await import(`../../content/extras/${slug}.mdx`);

  return (
    <main className="prose">
      <h2>{meta.title}</h2>
      <Content />
    </main>
  );
}
