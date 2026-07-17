"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import { LEVELS, EXTRA_ITEMS, ALL_IDS, type Item } from "@/lib/roadmap";
import { useApp } from "./AppProvider";

export function Sidebar() {
  const { ready, theme, isDone, doneCount, toggleTheme, reset, navOpen, closeNav } = useApp();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const match = (it: Item) => !q || it.title.toLowerCase().includes(q) || it.num.toLowerCase().includes(q);

  const groups = useMemo(
    () =>
      LEVELS.map((lvl) => ({ lvl, items: lvl.items.filter(match) })).filter((g) => g.items.length > 0),
    [q]
  );
  const extras = useMemo(() => EXTRA_ITEMS.filter(match), [q]);
  const noHits = q.length > 0 && groups.length === 0 && extras.length === 0;

  const pct = ready ? Math.round((doneCount(ALL_IDS) / ALL_IDS.length) * 100) : 0;

  const Row = ({ it }: { it: Item }) => {
    const active = pathname === it.href;
    return (
      <Link href={it.href} className={`navlink${active ? " active" : ""}`}>
        <span className="num">{it.num}</span>
        <span className="grow">{it.title}</span>
        {ready && isDone(it.id) ? <span className="check">✓</span> : null}
      </Link>
    );
  };

  return (
    <>
      <div
        className={`nav-overlay${navOpen ? " open" : ""}`}
        onClick={closeNav}
        aria-hidden
      />
      <aside id="course-sidebar" className={`sidebar${navOpen ? " open" : ""}`}>
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
        {groups.map(({ lvl, items }) => {
          const done = ready ? doneCount(lvl.items.map((i) => i.id)) : 0;
          return (
            <div key={lvl.key}>
              <div className="navsec">
                <span className="dot" style={{ background: `var(${lvl.colorVar})` }} />
                {lvl.short}
                <span className="cnt">
                  {done}/{lvl.items.length}
                </span>
              </div>
              {items.map((it) => (
                <Row key={it.id} it={it} />
              ))}
            </div>
          );
        })}

        {extras.length ? (
          <div>
            <div className="navsec">
              <span className="dot" style={{ background: "var(--ink-faint)" }} />
              Referencia
            </div>
            {extras.map((it) => (
              <Row key={it.id} it={it} />
            ))}
          </div>
        ) : null}

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
          <button
            className="theme"
            onClick={toggleTheme}
            aria-label={theme === "light" ? "Cambiar a tema oscuro" : "Cambiar a tema claro"}
          >
            {theme === "light" ? "◐ Oscuro" : "◑ Claro"}
          </button>
          <button className="reset" title="Reiniciar progreso" onClick={reset} aria-label="Reiniciar progreso">
            ↺
          </button>
        </div>
      </div>
      </aside>
    </>
  );
}
