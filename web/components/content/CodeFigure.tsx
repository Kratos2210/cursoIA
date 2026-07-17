"use client";

import { useRef, useState } from "react";

// Dark code figure with a caption and a copy button (v2 look). The `output`
// variant tints the text green for "expected output" blocks.
export function CodeFigure({
  caption,
  code,
  output = false,
  copyable = true,
}: {
  caption: string;
  code: string;
  output?: boolean;
  copyable?: boolean;
}) {
  const preRef = useRef<HTMLPreElement>(null);
  const [label, setLabel] = useState("Copiar");

  const copy = () => {
    const text = preRef.current?.textContent ?? code;
    navigator.clipboard?.writeText(text);
    setLabel("¡Copiado!");
    setTimeout(() => setLabel("Copiar"), 1500);
  };

  return (
    <figure className={`codefig${output ? " is-output" : ""}`}>
      <figcaption>
        <span className="cap">{caption}</span>
        {copyable && !output ? (
          <button type="button" className="copy" onClick={copy}>
            {label}
          </button>
        ) : null}
      </figcaption>
      <pre ref={preRef}>
        <code>{code}</code>
      </pre>
    </figure>
  );
}
