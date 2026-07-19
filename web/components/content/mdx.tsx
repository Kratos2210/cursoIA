// Server components for the converted MDX content, styled in the v2 look.
// These names match what the HTML→MDX converter emits (see scripts/convert-html-to-mdx.mjs)
// and are wired globally in mdx-components.tsx.
import type { ReactNode } from "react";

type Kids = { children?: ReactNode };
type BoxKind = "def" | "analogy" | "practice" | "warn";

export function Box({ kind = "def", label, children }: Kids & { kind?: BoxKind; label?: string }) {
  return (
    <div className={`box ${kind}`}>
      {label ? <div className="box-lab">{label}</div> : null}
      {children}
    </div>
  );
}

export function Checkpoint({ label, children }: Kids & { label?: string }) {
  return (
    <div className="checkpoint">
      {label ? <div className="box-lab">{label}</div> : null}
      {children}
    </div>
  );
}

export function Recap({ level = 1, label, children }: Kids & { level?: number; label?: string }) {
  const color = `var(--l${level})`;
  return (
    <div className="recap" style={{ borderLeftColor: color }}>
      {label ? (
        <div className="box-lab" style={{ color }}>
          {label}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function Avoid({ label, children }: Kids & { label?: string }) {
  return (
    <div className="avoid">
      {label ? <div className="box-lab">{label}</div> : null}
      {children}
    </div>
  );
}

export { Diagrama } from "./Diagrama";

export function Flow({ children }: Kids) {
  return <div className="flow">{children}</div>;
}
export function Step({ n, title, children }: Kids & { n?: string; title?: string }) {
  return (
    <div className="step">
      {n ? <div className="step-num">{n}</div> : null}
      {title ? <div className="step-title">{title}</div> : null}
      <div className="step-desc">{children}</div>
    </div>
  );
}
export function FlowCap({ children }: Kids) {
  return <div className="flowcap">{children}</div>;
}

export function LevelBanner({ level = 1, title, children }: Kids & { level?: number; title?: string }) {
  const color = `var(--l${level})`;
  return (
    <div className="lvbanner" style={{ borderColor: color }}>
      {title ? (
        <div className="lvbanner-title" style={{ color }}>
          {title}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function Grid3({ children }: Kids) {
  return <div className="grid3">{children}</div>;
}
export function Card({ num, title, children }: Kids & { num?: string; title?: string }) {
  return (
    <div className="ccard">
      {num ? <div className="ccard-num">{num}</div> : null}
      {title ? <h4>{title}</h4> : null}
      {children}
    </div>
  );
}

export function IvBlock({ children }: Kids) {
  return <div className="ivblock">{children}</div>;
}

export function DefList({ children }: Kids) {
  return <dl className="deflist">{children}</dl>;
}
export function Term({ children }: Kids) {
  return <dt>{children}</dt>;
}
export function Def({ children }: Kids) {
  return <dd>{children}</dd>;
}

export function Chip({ children }: Kids) {
  return <span className="ichip">{children}</span>;
}
export function Arch({ children }: Kids) {
  return <span className="arch">{children}</span>;
}
export function Note({ children }: Kids) {
  return <div className="note-src">{children}</div>;
}
export function Formula({ children }: Kids) {
  return <div className="formula-block">{children}</div>;
}

export function QA({ mod, children }: Kids & { mod?: string }) {
  return (
    <details className="qa" data-mod={mod}>
      {children}
    </details>
  );
}
export function QSummary({ children }: Kids) {
  return (
    <summary>
      {children}
    </summary>
  );
}
export function QAnswer({ children }: Kids) {
  return <div className="qa-answer">{children}</div>;
}

export function Solution({ summary = "Ver una solución", children }: Kids & { summary?: string }) {
  return (
    <details className="solution">
      <summary>{summary}</summary>
      <div className="sol-body">{children}</div>
    </details>
  );
}
