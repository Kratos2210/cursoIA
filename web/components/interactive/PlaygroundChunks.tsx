"use client";

import { useState } from "react";

// Troceo por ventana deslizante (simplificado a caracteres para VERLO; el
// RecursiveCharacterTextSplitter del m11 además respeta párrafos y frases).
const TEXTO =
  "La política de devoluciones de la tienda acepta cambios dentro de los 30 días presentando la boleta de compra. " +
  "Si el producto llegó dañado, el reembolso se procesa en un máximo de 5 días hábiles tras recibir la evidencia. " +
  "Los envíos a provincia demoran entre 2 y 4 días según el courier. " +
  "Para reclamos, el libro de reclamaciones está disponible en tienda y en la web.";

const COLORES = ["var(--l1)", "var(--l3)", "var(--l5)", "var(--l7)", "var(--l2)", "var(--l4)", "var(--l6)", "var(--l8)"];

function trocear(texto: string, tam: number, solape: number): { ini: number; fin: number }[] {
  const paso = Math.max(tam - solape, 1); // solape ≥ tam sería un bucle infinito
  const chunks: { ini: number; fin: number }[] = [];
  for (let ini = 0; ini < texto.length; ini += paso) {
    chunks.push({ ini, fin: Math.min(ini + tam, texto.length) });
    if (ini + tam >= texto.length) break;
  }
  return chunks;
}

export function PlaygroundChunks() {
  const [tam, setTam] = useState(140);
  const [solape, setSolape] = useState(30);

  const solapeReal = Math.min(solape, tam - 10);
  const chunks = trocear(TEXTO, tam, solapeReal);

  return (
    <div className="pg" role="group" aria-label="Playground de chunking">
      <div className="pg-controls">
        <label>
          chunk_size = <b>{tam}</b>
          <input
            type="range" min={60} max={300} step={10} value={tam}
            onChange={(e) => setTam(Number(e.target.value))}
            aria-label="Tamaño del chunk"
          />
        </label>
        <label>
          overlap = <b>{solapeReal}</b>
          <input
            type="range" min={0} max={80} step={10} value={solape}
            onChange={(e) => setSolape(Number(e.target.value))}
            aria-label="Solape entre chunks"
          />
        </label>
      </div>

      <div className="pg-chunks">
        {chunks.map((c, i) => (
          <div key={i} className="pg-chunk" style={{ borderColor: COLORES[i % COLORES.length] }}>
            <span className="pg-chunk-n" style={{ background: COLORES[i % COLORES.length] }}>
              #{i} · {c.fin - c.ini} chars
            </span>
            {i > 0 && solapeReal > 0 ? (
              <mark>{TEXTO.slice(c.ini, Math.min(chunks[i - 1].fin, c.fin))}</mark>
            ) : null}
            {TEXTO.slice(i > 0 && solapeReal > 0 ? Math.min(chunks[i - 1].fin, c.fin) : c.ini, c.fin)}
          </div>
        ))}
      </div>

      <p className="pg-note" aria-live="polite">
        {chunks.length} chunks. {solapeReal === 0
          ? "Sin solape: una frase partida al borde pierde su contexto en AMBOS chunks — súbelo y mira lo resaltado."
          : `El texto resaltado se REPITE entre chunks vecinos: ese solape es el seguro para que una idea cortada al borde sobreviva completa en al menos un chunk (a cambio de indexar ${chunks.reduce((n, c) => n + (c.fin - c.ini), 0) - TEXTO.length} chars de más).`}
        {" "}Chunks muy chicos pierden contexto; muy grandes diluyen la búsqueda (m11).
      </p>
    </div>
  );
}
