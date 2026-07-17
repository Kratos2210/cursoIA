"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import { LEVELS, ALL_IDS, TOTAL_ITEMS } from "@/lib/roadmap";
import { useApp } from "./AppProvider";

export function Sidebar() {
  const { ready, theme, isDone, doneCount, toggleTheme, reset } = useApp();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const levels = useMemo(() => {
    return LEVELS.map((lvl) => {
      const items = [
        ...lvl.mods.map((m) => ({
          id: m.id,
          num: m.num,
          title: m.title,
          built: !!m.built,
          isProject: false,
          href: `/modulo/${/^\d+$/.test(m.num) ? m.num : m.id}`,
        })),
        {
          id: lvl.proj.id,
          num: "★",
          title: lvl.proj.title,
          built: false,
          isProject: true,
          href: `/proyecto/${lvl.n}`,
        },
      ].filter((it) => !q || it.title.toLowerCase().includes(q) || it.num.includes(q));
      return { lvl, items };
    }).filter((g) => g.items.length > 0);
  }, [q]);

  const pct = ready ? Math.round((doneCount(ALL_IDS) / TOTAL_ITEMS) * 100) : 0;
  const noHits = q.length > 0 && levels.length === 0;

  return (
    <aside className="sidebar">
      <Link href="/" className="brand">
        <span className="brand-mark">
          <span />
        </span>
        <span style={{ lineHeight: 1.1 }}>
          <span className="brand-name">AI Engineer</span>
          <span className="brand-sub">Ruta de cero a pro</span>
        </span>
      </Link>

      <div className="search">
        <span aria-hidden>⌕</span>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar módulo…"
          aria-label="Buscar módulo"
        />
      </div>

      <nav className="nav" aria-label="Índice del curso">
        {levels.map(({ lvl, items }) => {
          const groupIds = [...lvl.mods.map((m) => m.id), lvl.proj.id];
          const done = ready ? doneCount(groupIds) : 0;
          return (
            <div key={lvl.id}>
              <div className="navsec">
                <span className="dot" style={{ background: `var(${lvl.colorVar})` }} />
                {lvl.shortName}
                <span className="cnt">
                  {done}/{groupIds.length}
                </span>
              </div>
              {items.map((it) => {
                const active = pathname === it.href;
                return (
                  <Link
                    key={it.id}
                    href={it.href}
                    className={`navlink${active ? " active" : ""}${it.isProject ? " is-project" : ""}`}
                  >
                    <span
                      className="num"
                      style={it.isProject ? { color: `var(${lvl.colorVar})` } : undefined}
                    >
                      {it.num}
                    </span>
                    <span className="grow">{it.title}</span>
                    {ready && isDone(it.id) ? <span className="check">✓</span> : null}
                    {!it.built && !(ready && isDone(it.id)) ? <span className="soon">pronto</span> : null}
                  </Link>
                );
              })}
            </div>
          );
        })}
        {noHits ? <p className="nav-empty">Sin resultados para “{query}”</p> : null}
      </nav>

      <div className="sidebar-foot">
        <div className="prog-row">
          <span className="prog-label">Progreso global</span>
          <span className="prog-pct">{pct}%</span>
        </div>
        <div className="prog-track">
          <div className="prog-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="foot-btns">
          <button className="theme" onClick={toggleTheme}>
            {theme === "light" ? "◐ Oscuro" : "◑ Claro"}
          </button>
          <button className="reset" title="Reiniciar progreso" onClick={reset} aria-label="Reiniciar progreso">
            ↺
          </button>
        </div>
      </div>
    </aside>
  );
}
