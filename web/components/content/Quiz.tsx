"use client";

import { useState, type ReactNode } from "react";

export type QuizOption = { node: ReactNode; ok?: boolean };
export type QuizItem = { prompt: ReactNode; options: QuizOption[]; feedback: ReactNode };

// Interactive self-assessment (v2 behavior): click an option to reveal the
// correct answer, wrong pick highlighted, feedback shown; score appears once
// every question is answered.
export function Quiz({ title, items }: { title: string; items: QuizItem[] }) {
  const [picked, setPicked] = useState<(number | null)[]>(() => items.map(() => null));

  const choose = (qi: number, oi: number) => {
    setPicked((prev) => {
      if (prev[qi] !== null) return prev;
      const next = [...prev];
      next[qi] = oi;
      return next;
    });
  };

  const answered = picked.filter((p) => p !== null).length;
  const allDone = answered === items.length;
  const correct = items.filter((it, qi) => picked[qi] !== null && it.options[picked[qi]!]?.ok).length;

  return (
    <div className="quiz">
      <div className="quiz-head">{title}</div>
      <div className="quiz-sub">
        <span className="hint">Responde para ver si ya lo tienes</span>
        {allDone ? (
          <span className={`quiz-score${correct === items.length ? " perfect" : ""}`}>
            {correct} / {items.length}
          </span>
        ) : null}
      </div>

      {items.map((it, qi) => {
        const done = picked[qi] !== null;
        return (
          <div className="q" key={qi}>
            <p className="enun">
              {qi + 1} · {it.prompt}
            </p>
            <div className="opts">
              {it.options.map((op, oi) => {
                let cls = "opt";
                if (done) {
                  if (op.ok) cls += " correct";
                  else if (picked[qi] === oi) cls += " wrong";
                  else cls += " dim";
                }
                return (
                  <button
                    key={oi}
                    type="button"
                    className={cls}
                    disabled={done}
                    onClick={() => choose(qi, oi)}
                  >
                    {op.node}
                  </button>
                );
              })}
            </div>
            {done ? <p className="fb">{it.feedback}</p> : null}
          </div>
        );
      })}
    </div>
  );
}
