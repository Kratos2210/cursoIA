"use client";

import Link from "next/link";
import { ALL_IDS } from "@/lib/roadmap";
import { useApp } from "./AppProvider";

// Top bar shown only on narrow screens (CSS-gated). Holds the brand, the global
// progress %, and the hamburger that opens the off-canvas sidebar drawer.
export function MobileBar() {
  const { ready, doneCount, navOpen, toggleNav } = useApp();
  const pct = ready ? Math.round((doneCount(ALL_IDS) / ALL_IDS.length) * 100) : 0;

  return (
    <div className="mobile-bar">
      <button
        type="button"
        className="mb-burger"
        onClick={toggleNav}
        aria-label={navOpen ? "Cerrar el índice" : "Abrir el índice"}
        aria-expanded={navOpen}
        aria-controls="course-sidebar"
      >
        ☰
      </button>
      <Link href="/" className="mb-brand">
        AI Engineer
      </Link>
      <span className="mb-pct" aria-label={`Progreso ${pct}%`}>
        {pct}%
      </span>
    </div>
  );
}
