"use client";

import Link from "next/link";
import { LEVELS, ITEMS, ALL_IDS, TOTAL_ITEMS, TOTAL_MODULES } from "@/lib/roadmap";
import { useApp } from "./AppProvider";

export function Dashboard() {
  const { ready, isDone, doneCount } = useApp();

  const pct = ready ? Math.round((doneCount(ALL_IDS) / TOTAL_ITEMS) * 100) : 0;
  const firstBuilt = ITEMS.find((i) => i.kind === "module" && i.built);
  const firstIncomplete = ITEMS.find((i) => i.kind === "module" && i.built && !(ready && isDone(i.id))) ?? firstBuilt;
  const continueHref = firstIncomplete?.href ?? "/modulo/00";
  const continueLabel = ready && doneCount(ALL_IDS) > 0 ? "Continuar" : "Comenzar el curso";

  const stats = [
    { value: `${TOTAL_MODULES}`, label: "Módulos" },
    { value: "6", label: "Proyectos" },
    { value: "6", label: "Niveles" },
    { value: `${pct}%`, label: "Completado" },
  ];

  return (
    <section className="view">
      <div className="hero">
        <p className="eyebrow">
          <span className="rule" />
          Roadmap · de cero a AI Engineer
        </p>
        <h1>Conviértete en AI Engineer, un proyecto a la vez</h1>
        <p className="lede">
          Seis niveles que van de <b>cero absoluto</b> (instalar Python) a <b>sistemas de IA en
          producción</b>. Cada nivel termina con un <b>proyecto integrador</b> que une todo lo
          aprendido — al final tendrás un portafolio, no solo apuntes.
        </p>
        <div className="cta-row">
          <Link href={continueHref} className="btn-primary">
            {continueLabel} →
          </Link>
          <Link href="/modulo/00" className="btn-ghost">
            Empezar desde cero
          </Link>
        </div>
      </div>

      <div className="stats">
        {stats.map((s) => (
          <div className="stat" key={s.label}>
            <div className="stat-val">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      <h2 className="roadmap-h">El roadmap</h2>
      <p className="roadmap-sub">
        Sigue el orden. No pases de nivel sin terminar su proyecto integrador — ahí es donde de
        verdad aprendes.
      </p>

      <div className="roadmap">
        {LEVELS.map((lvl, i) => {
          const color = `var(${lvl.colorVar})`;
          const groupIds = [...lvl.mods.map((m) => m.id), lvl.proj.id];
          const done = ready ? doneCount(groupIds) : 0;
          const levelDone = done === groupIds.length;
          const railColor = i === LEVELS.length - 1 ? "var(--accent)" : levelDone ? color : "var(--line-2)";
          const projDone = ready && isDone(lvl.proj.id);
          return (
            <div className="rm-row" key={lvl.id}>
              <div className="rm-rail">
                <span
                  className="rm-node"
                  style={{
                    background: `color-mix(in srgb, ${color} 10%, transparent)`,
                    border: `1px solid ${color}`,
                    color,
                  }}
                >
                  {lvl.n}
                </span>
                <span className="rm-line" style={{ background: railColor }} />
              </div>
              <div className="rm-body">
                <div className="rm-card">
                  <div className="rm-card-head">
                    <h3>{lvl.name}</h3>
                    <span className="rm-count">
                      {done}/{groupIds.length} módulos
                    </span>
                  </div>
                  <p className="rm-desc">{lvl.desc}</p>
                  <div className="rm-chips">
                    {lvl.mods.map((m) => {
                      const slug = /^\d+$/.test(m.num) ? m.num : m.id;
                      const mdone = ready && isDone(m.id);
                      return (
                        <Link
                          key={m.id}
                          href={`/modulo/${slug}`}
                          className={`chip${mdone ? " done" : ""}`}
                        >
                          <span className="n">{m.num}</span> {m.title}
                          {mdone ? <span className="check">✓</span> : null}
                        </Link>
                      );
                    })}
                  </div>
                  <Link
                    href={`/proyecto/${lvl.n}`}
                    className="rm-proj"
                    style={{
                      background: `color-mix(in srgb, ${color} 10%, transparent)`,
                      borderColor: color,
                    }}
                  >
                    <span className="star" style={{ color }}>
                      ★
                    </span>
                    <span style={{ minWidth: 0 }}>
                      <span className="kicker" style={{ color }}>
                        Proyecto integrador
                      </span>
                      <span className="ptitle">
                        {lvl.proj.title}
                        {projDone ? <span style={{ color: "var(--good)" }}> ✓</span> : null}
                      </span>
                    </span>
                    <span className="arrow" style={{ color }}>
                      →
                    </span>
                  </Link>
                </div>
              </div>
            </div>
          );
        })}

        <div className="rm-finish">
          <div style={{ display: "flex", justifyContent: "center" }}>
            <span className="node">◈</span>
          </div>
          <p>
            AI Engineer{" "}
            <span>— con 6 proyectos reales en tu portafolio y el examen final aprobado.</span>
          </p>
        </div>
      </div>
    </section>
  );
}
