"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "./AppProvider";

type Doc = {
  slug: string;
  href: string;
  num: string;
  title: string;
  group: string;
  headings: { id: string; text: string }[];
  text: string;
};

// Accent-insensitive lowercase: "Evaluación" and "evaluacion" must meet.
function norm(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

type Hit = {
  doc: Doc;
  score: number;
  anchor: string | null; // heading id when the match lives in a heading
  snippet: string | null;
};

// Every query term must appear somewhere in the doc (title, heading or body);
// the score just orders the survivors: title > heading > body occurrences.
function search(docs: (Doc & { ntitle: string; nheads: string[]; ntext: string })[],
                query: string): Hit[] {
  const terms = norm(query).split(/\s+/).filter(Boolean);
  if (!terms.length) return [];
  const hits: Hit[] = [];
  for (const doc of docs) {
    let score = 0;
    let anchor: string | null = null;
    let firstBody = -1;
    let ok = true;
    for (const term of terms) {
      let found = 0;
      if (doc.ntitle.includes(term)) found = 8;
      const h = doc.nheads.findIndex((t) => t.includes(term));
      if (h !== -1) {
        found = Math.max(found, 4);
        anchor ??= doc.headings[h].id;
      }
      const at = doc.ntext.indexOf(term);
      if (at !== -1) {
        found = Math.max(found, 1);
        score += Math.min(doc.ntext.split(term).length - 1, 5);
        if (firstBody === -1) firstBody = at;
      }
      if (!found) {
        ok = false;
        break;
      }
      score += found;
    }
    if (!ok) continue;
    const snippet =
      firstBody === -1
        ? null
        : "…" + doc.text.slice(Math.max(0, firstBody - 30), firstBody + 90).trim() + "…";
    hits.push({ doc, score, anchor, snippet });
  }
  return hits.sort((a, b) => b.score - a.score).slice(0, 12);
}

export function SearchPalette() {
  const { searchOpen, closeSearch } = useApp();
  const router = useRouter();
  const [docs, setDocs] = useState<(Doc & { ntitle: string; nheads: string[]; ntext: string })[] | null>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // The 664 KB index is fetched ONCE, and only when the palette first opens —
  // regular navigation never pays for it.
  useEffect(() => {
    if (!searchOpen || docs) return;
    let alive = true;
    fetch("/search-index.json")
      .then((r) => r.json())
      .then((data: { docs: Doc[] }) => {
        if (!alive) return;
        setDocs(
          data.docs.map((d) => ({
            ...d,
            ntitle: norm(`${d.num} ${d.title}`),
            nheads: d.headings.map((h) => norm(h.text)),
            ntext: norm(d.text),
          }))
        );
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [searchOpen, docs]);

  useEffect(() => {
    if (searchOpen) {
      setQuery("");
      setActive(0);
      // Focus after the overlay paints.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [searchOpen]);

  const hits = useMemo(() => (docs && query ? search(docs, query) : []), [docs, query]);

  if (!searchOpen) return null;

  const go = (hit: Hit) => {
    closeSearch();
    router.push(hit.anchor ? `${hit.doc.href}#${hit.anchor}` : hit.doc.href);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") closeSearch();
    else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, hits.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && hits[active]) {
      e.preventDefault();
      go(hits[active]);
    }
  };

  return (
    <div className="palette-overlay" onClick={closeSearch}>
      <div
        className="palette"
        role="dialog"
        aria-modal="true"
        aria-label="Buscar en todo el curso"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className="palette-input">
          <span aria-hidden>⌕</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
            }}
            placeholder="Buscar en todo el curso… (título, sección o contenido)"
            aria-label="Buscar en todo el curso"
          />
          <kbd>esc</kbd>
        </div>
        <div className="palette-results" role="listbox" aria-label="Resultados">
          {!docs && query ? <p className="palette-note">Cargando el índice…</p> : null}
          {docs && query && hits.length === 0 ? (
            <p className="palette-note">Sin resultados para “{query}”</p>
          ) : null}
          {!query ? (
            <p className="palette-note">
              Escribe para buscar en los 58 conceptos y recursos. Abre esta búsqueda con{" "}
              <kbd>⌘K</kbd> / <kbd>Ctrl K</kbd> desde cualquier página.
            </p>
          ) : null}
          {hits.map((hit, i) => (
            <button
              key={hit.doc.slug + (hit.anchor ?? "")}
              role="option"
              aria-selected={i === active}
              className={`palette-hit${i === active ? " active" : ""}`}
              onMouseEnter={() => setActive(i)}
              onClick={() => go(hit)}
            >
              <span className="hit-head">
                <span className="hit-num">{hit.doc.num}</span>
                <span className="hit-title">{hit.doc.title}</span>
                <span className="hit-group">{hit.doc.group}</span>
              </span>
              {hit.snippet ? <span className="hit-snippet">{hit.snippet}</span> : null}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
