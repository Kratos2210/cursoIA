"use client";

import Link from "next/link";
import {
  LEVELS,
  MODULE_ITEMS,
  EXTRA_ITEMS,
  ALL_IDS,
  TOTAL_MODULES,
  TOTAL_LEVELS,
  TOTAL_EXTRAS,
} from "@/lib/roadmap";
import { useApp } from "./AppProvider";

// Sum the "~NN min" hints of a level's modules into a rough "≈ N h" estimate.
function levelTime(items: { minutes: string | null }[]): string {
  const mins = items.reduce((sum, m) => {
    const n = m.minutes ? parseInt(m.minutes.replace(/[^\d]/g, ""), 10) : 0;
    return sum + (Number.isFinite(n) ? n : 0);
  }, 0);
  if (mins < 60) return `≈ ${mins} min`;
  const h = mins / 60;
  return `≈ ${Number.isInteger(h) ? h : h.toFixed(1)} h`;
}

export function Dashboard() {
  const { ready, isDone, doneCount } = useApp();

  const scrollToRoadmap = () => {
    document.getElementById("roadmap")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const pct = ready ? Math.round((doneCount(ALL_IDS) / ALL_IDS.length) * 100) : 0;
  const firstIncomplete = MODULE_ITEMS.find((i) => !(ready && isDone(i.id))) ?? MODULE_ITEMS[0];
  const continueHref = firstIncomplete?.href ?? "/concepto/00-preparar-el-terreno";
  const continueLabel = ready && doneCount(ALL_IDS) > 0 ? "Continuar" : "Comenzar el curso";

  const stats = [
    { value: `${TOTAL_MODULES}`, label: "Conceptos" },
    { value: `${TOTAL_LEVELS}`, label: "Etapas" },
    { value: `${TOTAL_EXTRAS}`, label: "Recursos" },
    { value: `${pct}%`, label: "Completado" },
  ];

  return (
    <section className="view">
      <div className="hero">
        <p className="eyebrow">
          <span className="rule" />
          Roadmap · de cero a AI Engineer
        </p>
        <h1>Conviértete en AI Engineer, un concepto a la vez</h1>
        <p className="lede">
          Un recorrido por <b>temas</b> —Fundamentos, Prompts y LCEL, Agentes, RAG, Modelos,
          Producción y Proyectos— que va de <b>cero absoluto</b> (instalar Python) a <b>sistemas de
          IA en producción</b>. Cada tema reúne todo lo suyo en un solo sitio, y el objetivo de todas
          las rutas es el mismo: <b>convertirte en AI Engineer</b>. Cada concepto trae un ejemplo
          ejecutable y su autoevaluación.
        </p>
        <div className="cta-row">
          <Link href={continueHref} className="btn-primary">
            {continueLabel} →
          </Link>
          <button type="button" className="btn-ghost" onClick={scrollToRoadmap}>
            Ver el temario
          </button>
          <Link href="/diagnostico" className="btn-ghost">
            ¿Por dónde empiezo?
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

      <h2 className="roadmap-h" id="roadmap">El roadmap</h2>
      <p className="roadmap-sub">
        Ocho etapas temáticas: cada una reúne todo lo suyo. Cada concepto se estudia corriendo su
        ejemplo — no solo leyéndolo — y no avances sin pasar su autoevaluación.
      </p>

      <div className="roadmap">
        {LEVELS.map((lvl, i) => {
          const color = `var(${lvl.colorVar})`;
          const done = ready ? doneCount(lvl.items.map((m) => m.id)) : 0;
          const levelDone = done === lvl.items.length;
          const railColor = i === LEVELS.length - 1 ? "var(--accent)" : levelDone ? color : "var(--line-2)";
          return (
            <div className="rm-row" key={lvl.key}>
              <div className="rm-rail">
                <span
                  className="rm-node"
                  style={{
                    background: `color-mix(in srgb, ${color} 10%, transparent)`,
                    border: `1px solid ${color}`,
                    color,
                  }}
                >
                  {i + 1}
                </span>
                <span className="rm-line" style={{ background: railColor }} />
              </div>
              <div className="rm-body">
                <div className="rm-card">
                  <div className="rm-card-head">
                    <h3>{lvl.name}</h3>
                    <span className="rm-count">
                      {done}/{lvl.items.length} conceptos
                    </span>
                    <span className="rm-time">{levelTime(lvl.items)}</span>
                  </div>
                  <div className="rm-chips">
                    {lvl.items.map((m) => {
                      const mdone = ready && isDone(m.id);
                      return (
                        <Link key={m.id} href={m.href} className={`chip${mdone ? " done" : ""}`}>
                          <span className="n">{m.num}</span> {m.title}
                          {mdone ? <span className="check">✓</span> : null}
                        </Link>
                      );
                    })}
                  </div>
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
            <span>— con proyectos reales en tu portafolio y el examen final aprobado.</span>
          </p>
          <p style={{ marginTop: 6 }}>
            <Link href="/constancia">
              {pct === 100 ? "🎓 Genera tu constancia →" : `Tu constancia se desbloquea al 100% (vas en ${pct}%) →`}
            </Link>
          </p>
        </div>
      </div>

      {EXTRA_ITEMS.length ? (
        <>
          <h2 className="roadmap-h">Referencia y práctica</h2>
          <div className="rm-chips" style={{ marginTop: 8 }}>
            {EXTRA_ITEMS.map((e) => (
              <Link key={e.id} href={e.href} className="chip">
                {e.title}
              </Link>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
