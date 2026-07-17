import Link from "next/link";
import { KindTag } from "@/components/content/ui";
import type { Item } from "@/lib/roadmap";

export function ComingSoon({ item }: { item: Item }) {
  const color = `var(${item.colorVar})`;
  const kindLabel = item.kind === "project" ? "Proyecto integrador" : `Módulo ${item.num}`;
  return (
    <article className="article">
      <KindTag colorVar={item.colorVar}>
        {item.levelName} · {kindLabel}
      </KindTag>
      <h1>{item.title}</h1>

      {item.brief ? (
        <div className="brief">
          <div className="brief-lab" style={{ color }}>
            ★ Qué vas a construir
          </div>
          <p>{item.brief}</p>
        </div>
      ) : null}

      <div className="coming">
        <div className="emoji">🚧</div>
        <h2>Contenido en preparación</h2>
        <p>
          Este es el prototipo del rediseño. Los módulos <b>00</b> y <b>04</b> están completos como
          muestra de la nueva experiencia.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 22, flexWrap: "wrap" }}>
          <Link href="/modulo/00" className="btn-primary" style={{ fontSize: 13, padding: "11px 18px" }}>
            Ver Módulo 00 →
          </Link>
          <Link href="/modulo/04" className="btn-ghost" style={{ fontSize: 13, padding: "11px 18px" }}>
            Ver Módulo 04 →
          </Link>
        </div>
      </div>
    </article>
  );
}
