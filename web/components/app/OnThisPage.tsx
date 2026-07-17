"use client";

import { useEffect, useState } from "react";

type Heading = { id: string; text: string; level: number };

// "En esta página" table of contents. Reads the h2/h3 (id'd by rehype-slug) from
// the rendered article at mount — no build-time extraction — and highlights the
// section in view with an IntersectionObserver. Renders both a sticky rail
// (desktop, ≥1200px) and a collapsible <details> (narrower); CSS shows one.
export function OnThisPage() {
  const [items, setItems] = useState<Heading[]>([]);
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    const article = document.querySelector(".article");
    if (!article) return;
    const els = Array.from(
      article.querySelectorAll<HTMLElement>("h2[id], h3[id]")
    );
    setItems(
      els.map((el) => ({
        id: el.id,
        text: el.textContent ?? "",
        level: Number(el.tagName[1]),
      }))
    );
    if (els.length < 2) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive((visible[0].target as HTMLElement).id);
      },
      { rootMargin: "0px 0px -70% 0px", threshold: 0 }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Modules with barely any structure don't need a TOC.
  if (items.length < 2) return null;

  const list = (
    <ul className="otp-list">
      {items.map((it) => (
        <li key={it.id} className={`otp-l${it.level}${active === it.id ? " active" : ""}`}>
          <a href={`#${it.id}`}>{it.text}</a>
        </li>
      ))}
    </ul>
  );

  return (
    <div className="otp">
      <details className="otp-inline">
        <summary>En esta página</summary>
        {list}
      </details>
      <nav className="otp-rail" aria-label="En esta página">
        <p className="otp-head">En esta página</p>
        {list}
      </nav>
    </div>
  );
}
