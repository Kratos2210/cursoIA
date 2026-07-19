"use client";

import { useState } from "react";

// Los MISMOS logits del 27_fundamentos_llm.py y su ejercicio: así lo que el
// alumno calcula a mano en el módulo es lo que ve moverse aquí.
const LOGITS = [2.0, 1.0, 0.2, -1.0];
const TOKENS = ["token 0", "token 1", "token 2", "token 3"];

// Port fiel de softmax_con_temperatura: t=0 es el caso especial argmax.
function softmax(logits: number[], t: number): number[] {
  if (t === 0) {
    const top = logits.indexOf(Math.max(...logits));
    return logits.map((_, i) => (i === top ? 1 : 0));
  }
  const max = Math.max(...logits);
  const exps = logits.map((l) => Math.exp((l - max) / t));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map((e) => e / sum);
}

// Port fiel de muestrear_top_p: acumula desde el más probable y PARA al llegar a p.
function nucleo(probs: number[], p: number): number[] {
  const orden = probs.map((_, i) => i).sort((a, b) => probs[b] - probs[a]);
  const dentro: number[] = [];
  let acumulado = 0;
  for (const i of orden) {
    dentro.push(i);
    acumulado += probs[i];
    if (acumulado >= p) break;
  }
  return dentro;
}

export function PlaygroundSoftmax() {
  const [t, setT] = useState(1.0);
  const [p, setP] = useState(0.9);

  const probs = softmax(LOGITS, t);
  const enNucleo = new Set(nucleo(probs, p));
  const r4 = (x: number) => Math.round(x * 10000) / 10000;
  const igualQueT0 = softmax(LOGITS, 0).every((x, i) => r4(x) === r4(probs[i]));

  return (
    <div className="pg" role="group" aria-label="Playground de temperatura y top_p">
      <div className="pg-controls">
        <label>
          temperature = <b>{t.toFixed(1)}</b>
          <input
            type="range" min={0} max={10} step={0.1} value={t}
            onChange={(e) => setT(Number(e.target.value))}
            aria-label="Temperatura"
          />
        </label>
        <label>
          top_p = <b>{p.toFixed(2)}</b>
          <input
            type="range" min={0.05} max={1} step={0.05} value={p}
            onChange={(e) => setP(Number(e.target.value))}
            aria-label="top_p"
          />
        </label>
      </div>

      <div className="pg-bars">
        {probs.map((prob, i) => (
          <div key={i} className={`pg-bar-row${enNucleo.has(i) ? "" : " out"}`}>
            <span className="pg-bar-label">{TOKENS[i]}</span>
            <span className="pg-bar-track">
              <span className="pg-bar-fill" style={{ width: `${prob * 100}%` }} />
            </span>
            <span className="pg-bar-val">{prob.toFixed(4)}</span>
          </div>
        ))}
      </div>

      <p className="pg-note" aria-live="polite">
        {t === 0
          ? "t=0: no hay dado — argmax puro. La «creatividad» no se apagó: se apagó el muestreo."
          : igualQueT0
            ? `t=${t.toFixed(1)} ya es INDISTINGUIBLE de t=0 con 4 decimales: «casi determinista» es determinista.`
            : t >= 8
              ? "Aplana pero JAMÁS reordena: el token 0 sigue arriba. Softmax es monótona."
              : enNucleo.size === 1
                ? `Con top_p=${p.toFixed(2)} el núcleo tiene UN solo token (su prob ${probs[nucleo(probs, p)[0]].toFixed(2)} ≥ ${p.toFixed(2)}): esto es greedy disfrazado.`
                : `El núcleo admite ${enNucleo.size} de 4 tokens (los grises quedan fuera del muestreo).`}
      </p>
    </div>
  );
}
