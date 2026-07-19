"use client";

import { useState } from "react";

// El ciclo del m13, paso a paso: agente → ¿tool? → tool → agente → interrupt()
// → humano decide → fin (o vuelta al agente). Cada "Paso" avanza el grafo; en
// la pausa, el grafo se CONGELA hasta que el humano aprueba o rechaza — que es
// exactamente lo que hace interrupt() + Command(resume=…).
type Fase = "inicio" | "agente" | "tool" | "agente2" | "pausa" | "fin" | "rechazado";

const NODOS: { id: string; x: number; y: number; label: string }[] = [
  { id: "agente", x: 30, y: 20, label: "agente" },
  { id: "tool", x: 250, y: 20, label: "tool" },
  { id: "humano", x: 30, y: 110, label: "interrupt()" },
  { id: "fin", x: 250, y: 110, label: "END" },
];

const ACTIVO: Record<Fase, string[]> = {
  inicio: [],
  agente: ["agente"],
  tool: ["tool"],
  agente2: ["agente"],
  pausa: ["humano"],
  fin: ["fin"],
  rechazado: ["agente"],
};

const RELATO: Record<Fase, string> = {
  inicio: "Estado inicial: llega la petición «archiva el reporte X». Dale a Paso.",
  agente: "El agente razona y decide llamar a la tool `archivar` — la arista condicional lo manda al nodo tool.",
  tool: "La tool se ejecuta y devuelve su resultado al estado. El checkpointer guarda TODO después de cada nodo.",
  agente2: "El agente lee el resultado y propone la acción final… pero archivar es irreversible.",
  pausa: "interrupt(): el grafo se CONGELA (minutos o días — el estado vive en el checkpointer). Nadie ejecuta nada hasta que un humano decida.",
  fin: "Command(resume=«aprobado»): el grafo despierta EXACTAMENTE donde se pausó y termina. Eso es human-in-the-loop.",
  rechazado: "Command(resume=«rechazado»): el grafo despierta y vuelve al agente a re-planificar — el ciclo es un grafo, no una línea.",
};

const SIGUIENTE: Partial<Record<Fase, Fase>> = {
  inicio: "agente",
  agente: "tool",
  tool: "agente2",
  agente2: "pausa",
  rechazado: "pausa",
};

export function PlaygroundGrafo() {
  const [fase, setFase] = useState<Fase>("inicio");
  const activos = new Set(ACTIVO[fase]);

  return (
    <div className="pg" role="group" aria-label="Playground del grafo con pausa humana">
      <svg viewBox="0 0 380 170" className="pg-svg" aria-hidden>
        {/* aristas */}
        <g className="pg-edges">
          <path d="M110 35 H 245" markerEnd="url(#pgArrow)" />
          <path d="M250 45 C 200 75, 140 75, 112 42" markerEnd="url(#pgArrow)" />
          <path d="M65 45 V 105" markerEnd="url(#pgArrow)" />
          <path d="M115 125 H 245" markerEnd="url(#pgArrow)" />
          <path d="M35 105 C 15 70, 15 55, 32 45" markerEnd="url(#pgArrow)" strokeDasharray="4 3" />
        </g>
        <defs>
          <marker id="pgArrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 z" fill="currentColor" />
          </marker>
        </defs>
        {NODOS.map((n) => (
          <g key={n.id} className={`pg-node${activos.has(n.id) ? " on" : ""}`}>
            <rect x={n.x} y={n.y} width={85} height={26} rx={8} />
            <text x={n.x + 42} y={n.y + 17} textAnchor="middle">{n.label}</text>
          </g>
        ))}
      </svg>

      <p className="pg-note" aria-live="polite">{RELATO[fase]}</p>

      <div className="pg-controls">
        {fase === "pausa" ? (
          <>
            <button className="pg-btn" onClick={() => setFase("fin")}>✅ Aprobar</button>
            <button className="pg-btn" onClick={() => setFase("rechazado")}>❌ Rechazar</button>
          </>
        ) : fase === "fin" ? (
          <button className="pg-btn" onClick={() => setFase("inicio")}>↺ Reiniciar</button>
        ) : (
          <button className="pg-btn" onClick={() => setFase(SIGUIENTE[fase] ?? "inicio")}>
            Paso →
          </button>
        )}
      </div>
    </div>
  );
}
