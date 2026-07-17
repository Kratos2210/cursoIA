import Link from "next/link";
import { modulesByLevel, extras } from "@/lib/content";

// F1: minimal course index (temario). The styled hero, level cards and global
// progress bar land in F2/F4.
export default function Home() {
  const groups = modulesByLevel();
  return (
    <main className="prose">
      <h2>Curso: LangChain, RAG y LangGraph desde cero</h2>
      <p>
        De tu primer modelo a un AI Engineer: {groups.reduce((n, g) => n + g.items.length, 0)}{" "}
        módulos con ejemplos ejecutables y autoevaluaciones.
      </p>

      {groups.map((g) => (
        <section key={g.levelName}>
          <h3 style={{ color: `var(--l${g.level})` }}>{g.levelName}</h3>
          <ul>
            {g.items.map((m) => (
              <li key={m.slug}>
                <Link href={`/modulos/${m.slug}`}>
                  <strong>{m.badge}</strong> · {m.title}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}

      <h3>Extras</h3>
      <ul>
        {extras.map((e) => (
          <li key={e.slug}>
            <Link href={`/${e.slug}`}>{e.title}</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
