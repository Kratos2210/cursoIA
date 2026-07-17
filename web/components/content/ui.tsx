import type { ReactNode } from "react";

type Kids = { children?: ReactNode };

// Level / kind tag above a title, e.g. "Nivel 1 · Fundamentos · Módulo 00".
export function KindTag({ colorVar = "--accent", children }: Kids & { colorVar?: string }) {
  return (
    <p className="kind-tag" style={{ color: `var(${colorVar})` }}>
      <span className="bar" style={{ background: `var(${colorVar})` }} />
      {children}
    </p>
  );
}

export function FileRef({ file, tested }: { file: string; tested?: boolean }) {
  return (
    <div className="fileref">
      📋 Copia y ejecuta: <b>{file}</b>
      {tested ? <span className="tested">✓ cubierto por tests</span> : null}
    </div>
  );
}

export function MetaChips({ children }: Kids) {
  return <div className="meta-chips">{children}</div>;
}
export function MetaChip({ icon, label, children }: Kids & { icon: string; label?: string }) {
  return (
    <span className="meta-chip">
      {icon} {label ? <b>{label}</b> : null} {children}
    </span>
  );
}

type BoxKind = "def" | "analogy" | "practice" | "warn";
export function Box({ kind, label, children }: Kids & { kind: BoxKind; label: string }) {
  return (
    <div className={`box ${kind}`}>
      <div className="box-lab">{label}</div>
      {children}
    </div>
  );
}

export function Recap({
  colorVar = "--accent",
  label = "↺ En una frase",
  children,
}: Kids & { colorVar?: string; label?: string }) {
  return (
    <div className="recap" style={{ borderLeftColor: `var(${colorVar})` }}>
      <div className="box-lab" style={{ color: `var(${colorVar})` }}>
        {label}
      </div>
      <p>{children}</p>
    </div>
  );
}

export function Grid3({ children }: Kids) {
  return <div className="grid3">{children}</div>;
}
export function Card({ num, title, children }: Kids & { num: string; title: string }) {
  return (
    <div className="ccard">
      <div className="ccard-num">{num}</div>
      <h4>{title}</h4>
      {children}
    </div>
  );
}

export function TableWrap({ children }: Kids) {
  return <div className="tbl">{children}</div>;
}

export function Solution({ children, summary = "Ver una solución" }: Kids & { summary?: string }) {
  return (
    <details className="solution">
      <summary>{summary}</summary>
      {children}
    </details>
  );
}

// Inline mono code, tinted per surrounding box (see globals.css .box.* .icode).
export function C({ children }: Kids) {
  return <code className="icode">{children}</code>;
}
