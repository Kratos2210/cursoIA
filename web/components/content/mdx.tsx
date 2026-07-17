// Server components for MDX content blocks. These are F1 stubs: they render the
// content faithfully with class hooks, but the polished styling lands in F2.
import type { ReactNode } from "react";

type WithChildren = { children?: ReactNode };
type BoxKind = "def" | "analogy" | "practice" | "warn";

export function Box({
  kind = "def",
  label,
  children,
}: WithChildren & { kind?: BoxKind; label?: string }) {
  return (
    <div className={`box box-${kind}`}>
      {label ? <div className="box-lab">{label}</div> : null}
      {children}
    </div>
  );
}

export function Checkpoint({ label, children }: WithChildren & { label?: string }) {
  return (
    <div className="checkpoint">
      {label ? <div className="box-lab">{label}</div> : null}
      {children}
    </div>
  );
}

export function Recap({
  level = 1,
  label,
  children,
}: WithChildren & { level?: number; label?: string }) {
  return (
    <div className={`recap recap-l${level}`}>
      {label ? <div className="box-lab">{label}</div> : null}
      {children}
    </div>
  );
}

export function Avoid({ label, children }: WithChildren & { label?: string }) {
  return (
    <div className="avoid">
      {label ? <div className="box-lab">{label}</div> : null}
      {children}
    </div>
  );
}

export function Flow({ children }: WithChildren) {
  return <div className="flow">{children}</div>;
}

export function Step({
  n,
  title,
  children,
}: WithChildren & { n?: string; title?: string }) {
  return (
    <div className="step">
      {n ? <div className="step-num">{n}</div> : null}
      {title ? <div className="step-title">{title}</div> : null}
      <div className="step-desc">{children}</div>
    </div>
  );
}

export function FlowCap({ children }: WithChildren) {
  return <div className="flowcap">{children}</div>;
}

export function LevelBanner({
  level = 1,
  title,
  children,
}: WithChildren & { level?: number; title?: string }) {
  return (
    <div className={`lvbanner lvbanner-l${level}`}>
      {title ? <div className="lvbanner-title">{title}</div> : null}
      {children}
    </div>
  );
}

export function Grid3({ children }: WithChildren) {
  return <div className="grid3">{children}</div>;
}

export function Card({
  num,
  title,
  children,
}: WithChildren & { num?: string; title?: string }) {
  return (
    <div className="ccard">
      {num ? <div className="ccard-num">{num}</div> : null}
      {title ? <h4>{title}</h4> : null}
      {children}
    </div>
  );
}

export function IvBlock({ children }: WithChildren) {
  return <div className="ivblock">{children}</div>;
}

export function DefList({ children }: WithChildren) {
  return <dl className="deflist">{children}</dl>;
}

export function Term({ children }: WithChildren) {
  return <dt>{children}</dt>;
}

export function Def({ children }: WithChildren) {
  return <dd>{children}</dd>;
}

export function Chip({ children }: WithChildren) {
  return <span className="chip">{children}</span>;
}

export function Arch({ children }: WithChildren) {
  return <span className="arch">{children}</span>;
}

export function Note({ children }: WithChildren) {
  return <div className="note-src">{children}</div>;
}

export function Formula({ children }: WithChildren) {
  return <div className="formula">{children}</div>;
}

export function QA({
  mod,
  children,
}: WithChildren & { mod?: string }) {
  return (
    <details className="qa" data-mod={mod}>
      {children}
    </details>
  );
}

export function QSummary({ children }: WithChildren) {
  return <summary>{children}</summary>;
}

export function QAnswer({ children }: WithChildren) {
  return <div className="qa-answer">{children}</div>;
}

export function Solution({
  summary = "Ver una solución",
  children,
}: WithChildren & { summary?: string }) {
  return (
    <details className="sol">
      <summary>{summary}</summary>
      <div className="sol-body">{children}</div>
    </details>
  );
}
