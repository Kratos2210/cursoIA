"use client";

import { useRef, useState, type ComponentPropsWithoutRef } from "react";

// Client override for every <pre> emitted by the MDX pipeline (wired in
// mdx-components.tsx). Shiki produces the highlighted <pre><code> at build time
// and passes it here as props/children; we render it verbatim and float a copy
// button over the top-right corner. The caption bar (when present) is the static
// <figcaption> that rehype-code-title added around this block — see that plugin.
export function CodeBlock(props: ComponentPropsWithoutRef<"pre">) {
  const ref = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);

  const copy = () => {
    const text = ref.current?.textContent ?? "";
    if (!text) return;
    navigator.clipboard
      ?.writeText(text)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => {});
  };

  return (
    <div className="cb">
      <button
        type="button"
        className="copy"
        onClick={copy}
        aria-label={copied ? "Código copiado" : "Copiar código"}
      >
        {copied ? "¡Copiado!" : "Copiar"}
      </button>
      <pre {...props} ref={ref} />
    </div>
  );
}
