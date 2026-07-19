"use client";

import { useState } from "react";

// Chunks al estilo del corpus del m12: política de una tienda. El chunk 2 habla
// de "reembolso" (sinónimo de devolución) a propósito — es el caso donde el
// re-ranker didáctico ve 0.0 y el real entiende.
const CHUNKS = [
  "La política de la tienda acepta devoluciones dentro de los 30 días presentando la boleta.",
  "El horario de atención de la tienda es de lunes a sábado, de 9 a 18 horas.",
  "Si el producto llegó dañado, el reembolso se procesa en un máximo de 5 días hábiles.",
  "Los envíos a provincia demoran entre 2 y 4 días según el courier elegido.",
];

const PREGUNTAS = [
  "¿cuál es la política de devoluciones de la tienda?",
  "¿me devuelven la plata si llega roto?",
];

// El "cross-encoder real", simulado con una tabla fija: lee pregunta y chunk
// JUNTOS, así que entiende que "devolver la plata" ≈ "reembolso". Los valores
// son ilustrativos (un modelo ONNX no cabe en la página; ver rerank/README.md).
const REAL: Record<string, number[]> = {
  [PREGUNTAS[0]]: [0.93, 0.02, 0.61, 0.05],
  [PREGUNTAS[1]]: [0.44, 0.01, 0.95, 0.07],
};

// Port fiel de re_rankear() del 12: cobertura de palabras >3 letras + bono de frase.
function tokenizar(texto: string): string[] {
  return (texto.toLowerCase().match(/[a-záéíóúñü]+/g) ?? []).filter((p) => p.length > 3);
}

function scoreDidactico(pregunta: string, chunk: string): number {
  const palabras = tokenizar(pregunta);
  const texto = chunk.toLowerCase();
  const cobertura = palabras.filter((p) => texto.includes(p)).length / Math.max(palabras.length, 1);
  const bono = texto.includes(palabras.slice(0, 2).join(" ")) ? 0.5 : 0;
  return cobertura + bono;
}

export function PlaygroundRerank() {
  const [pregunta, setPregunta] = useState(PREGUNTAS[0]);

  const filas = CHUNKS.map((chunk, i) => ({
    chunk,
    didactico: scoreDidactico(pregunta, chunk),
    real: REAL[pregunta][i],
  }));
  const topDidactico = Math.max(...filas.map((f) => f.didactico));
  const todoCero = topDidactico === 0;

  return (
    <div className="pg" role="group" aria-label="Playground de re-ranking">
      <div className="pg-controls">
        {PREGUNTAS.map((q) => (
          <button
            key={q}
            className={`pg-chip${q === pregunta ? " active" : ""}`}
            onClick={() => setPregunta(q)}
          >
            {q}
          </button>
        ))}
      </div>

      <table className="pg-table">
        <thead>
          <tr>
            <th>Chunk</th>
            <th>didáctico<br /><span>¿comparten palabras?</span></th>
            <th>cross-encoder<br /><span>¿RESPONDE la pregunta?</span></th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={i}>
              <td>{f.chunk}</td>
              <td className={f.didactico === topDidactico && !todoCero ? "pg-top" : ""}>
                {f.didactico.toFixed(2)}
              </td>
              <td className={f.real === Math.max(...filas.map((x) => x.real)) ? "pg-top" : ""}>
                {f.real.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="pg-note" aria-live="polite">
        {todoCero
          ? "El didáctico dio 0.0 a TODOS: ninguna palabra de la pregunta aparece en los chunks («devolver la plata» ≠ «reembolso»). Su orden ahora es arbitrario; el cross-encoder sí entiende el sinónimo. Este es el fallo que confiesa el propio m12."
          : "Aquí los dos coinciden: la pregunta comparte palabras con el chunk correcto. Prueba la otra pregunta para ver dónde se rompe el didáctico."}
      </p>
    </div>
  );
}
