"use client";

import Link from "next/link";
import { useApp } from "./AppProvider";
import type { Item } from "@/lib/roadmap";

export function ModuleFooter({
  id,
  prev,
  next,
}: {
  id: string;
  prev: Item | null;
  next: Item | null;
}) {
  const { ready, isDone, toggleComplete } = useApp();
  const done = ready && isDone(id);

  return (
    <div className="mod-foot">
      <button className={`complete-btn${done ? " done" : ""}`} onClick={() => toggleComplete(id)}>
        {done ? "✓ Concepto completado — desmarcar" : "Marcar concepto como completado"}
      </button>

      {!next ? (
        <Link href="/recurso/examen" className="mod-finish">
          🎓 Terminaste el temario — sigue con el <b>examen final</b> →
        </Link>
      ) : null}

      <div className="pager">
        {prev ? (
          <Link href={prev.href} className="prev">
            <span className="kick">← Anterior</span>
            <span className="lbl">
              {prev.num} · {prev.title}
            </span>
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link href={next.href} className={`next${done ? " primary" : ""}`}>
            <span className="kick">Siguiente →</span>
            <span className="lbl">
              {next.num} · {next.title}
            </span>
          </Link>
        ) : null}
      </div>
    </div>
  );
}
