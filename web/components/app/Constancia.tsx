"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ALL_IDS, ALL_ITEMS, LEVELS, MODULE_ITEMS } from "@/lib/roadmap";
import { useApp } from "./AppProvider";

const NAME_KEY = "curso_ia_nombre";

export function Constancia() {
  const { ready, isDone, doneCount } = useApp();
  const [name, setName] = useState("");

  // The name is personal data: it lives ONLY in this browser's localStorage.
  useEffect(() => {
    try {
      setName(localStorage.getItem(NAME_KEY) ?? "");
    } catch {
      /* private mode */
    }
  }, []);

  const saveName = (value: string) => {
    setName(value);
    try {
      localStorage.setItem(NAME_KEY, value);
    } catch {
      /* private mode */
    }
  };

  const done = ready ? doneCount(ALL_IDS) : 0;
  const pct = Math.round((done / ALL_IDS.length) * 100);
  const complete = ready && done === ALL_IDS.length;
  const pending = ready ? ALL_ITEMS.filter((i) => !isDone(i.id)) : [];

  // Everything below depends on localStorage → render only after hydration.
  if (!ready) {
    return (
      <section className="view">
        <p className="palette-note">Cargando tu progreso…</p>
      </section>
    );
  }

  if (!complete) {
    return (
      <section className="view constancia-view">
        <h1>Tu constancia se desbloquea al 100%</h1>
        <p className="lede">
          La constancia certifica que recorriste <b>todo</b> el curso: los {MODULE_ITEMS.length}{" "}
          conceptos y los {ALL_IDS.length - MODULE_ITEMS.length} recursos. Vas en{" "}
          <b>
            {done}/{ALL_IDS.length} ({pct}%)
          </b>
          .
        </p>
        <div className="prog-track" aria-hidden>
          <div className="prog-fill" style={{ width: `${pct}%` }} />
        </div>
        {pending.length ? (
          <>
            <h2>Te falta{pending.length === 1 ? "" : "n"} {pending.length}:</h2>
            <ul className="constancia-pending">
              {pending.slice(0, 10).map((i) => (
                <li key={i.id}>
                  <Link href={i.href}>
                    {i.num} · {i.title}
                  </Link>
                </li>
              ))}
              {pending.length > 10 ? <li>…y {pending.length - 10} más.</li> : null}
            </ul>
            <Link className="btn-primary" href={pending[0].href}>
              Seguir donde ibas →
            </Link>
          </>
        ) : null}
      </section>
    );
  }

  return (
    <section className="view constancia-view">
      <div className="constancia-card">
        <p className="const-eyebrow">Constancia de finalización</p>
        <h1>AI Engineer · Ruta de cero a pro</h1>
        <p className="const-line">Se deja constancia de que</p>
        <input
          className="const-name"
          value={name}
          onChange={(e) => saveName(e.target.value)}
          placeholder="Escribe tu nombre aquí"
          aria-label="Tu nombre, tal como quieres que aparezca"
        />
        <p className="const-line">
          completó los <b>{MODULE_ITEMS.length} conceptos</b> y los{" "}
          <b>{ALL_IDS.length - MODULE_ITEMS.length} recursos</b> del curso, recorriendo sus{" "}
          {LEVELS.length} rutas:
        </p>
        <ul className="const-rutas">
          {LEVELS.map((l, i) => (
            <li key={l.key}>
              <span className="dot" style={{ background: `var(${l.colorVar})` }} />
              {i + 1} · {l.name}
            </li>
          ))}
        </ul>
        <p className="const-date">
          {new Date().toLocaleDateString("es-PE", { day: "numeric", month: "long", year: "numeric" })}
        </p>
        <p className="const-foot">
          Autoevaluación completada por el propio alumno sobre el material del curso. El progreso
          vive en este navegador.
        </p>
      </div>
      <div className="const-actions">
        <button className="btn-primary" onClick={() => window.print()}>
          🖨 Imprimir / guardar PDF
        </button>
        <Link className="btn-ghost" href="/recurso/examen">
          Repasar con el examen final
        </Link>
      </div>
    </section>
  );
}
