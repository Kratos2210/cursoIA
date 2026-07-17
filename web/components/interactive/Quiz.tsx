"use client";

// F1 stub: renders quiz content statically (options as disabled-looking buttons,
// feedback always visible). The interactive scoring/persistence logic lands in F2.
import type { ReactNode } from "react";

type WithChildren = { children?: ReactNode };

export function Quiz({ title, children }: WithChildren & { title?: string }) {
  return (
    <div className="quiz">
      {title ? <div className="quiz-head">{title}</div> : null}
      {children}
    </div>
  );
}

export function Question({ children }: WithChildren) {
  return <div className="q">{children}</div>;
}

export function Prompt({ children }: WithChildren) {
  return <p className="enun">{children}</p>;
}

export function Option({ ok, children }: WithChildren & { ok?: boolean }) {
  return (
    <button type="button" className="opt" data-ok={ok ? "" : undefined}>
      {children}
    </button>
  );
}

export function Feedback({ children }: WithChildren) {
  return <p className="fb">{children}</p>;
}
