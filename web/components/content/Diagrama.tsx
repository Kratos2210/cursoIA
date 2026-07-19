// Diagrama SVG declarativo para los flujos de arquitectura del curso: cajas +
// aristas con "marcha" animada que muestra la DIRECCIÓN del flujo (los ASCII
// estáticos no podían). Server component: solo SVG + CSS, cero JS en cliente.
// prefers-reduced-motion apaga la animación (ver globals.css).

type DgNode = { x: number; y: number; w: number; label: string; sub?: string };
type DgEdge = { d: string; label?: string; lx?: number; ly?: number; back?: boolean };

export function Diagrama({
  title,
  viewBox,
  nodes,
  edges,
}: {
  title: string;
  viewBox: string;
  nodes: DgNode[];
  edges: DgEdge[];
}) {
  return (
    <figure className="dg">
      <svg viewBox={viewBox} role="img" aria-label={title}>
        <defs>
          <marker id="dgArrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 z" fill="currentColor" />
          </marker>
        </defs>
        {edges.map((e, i) => (
          <g key={i} className={`dg-edge${e.back ? " back" : ""}`}>
            <path d={e.d} markerEnd="url(#dgArrow)" />
            {e.label ? (
              <text x={e.lx} y={e.ly} className="dg-edge-label">
                {e.label}
              </text>
            ) : null}
          </g>
        ))}
        {nodes.map((n, i) => (
          <g key={i} className="dg-node">
            <rect x={n.x} y={n.y} width={n.w} height={n.sub ? 40 : 28} rx={9} />
            <text x={n.x + n.w / 2} y={n.y + 18} textAnchor="middle">
              {n.label}
            </text>
            {n.sub ? (
              <text x={n.x + n.w / 2} y={n.y + 33} textAnchor="middle" className="dg-sub">
                {n.sub}
              </text>
            ) : null}
          </g>
        ))}
      </svg>
      <figcaption>{title}</figcaption>
    </figure>
  );
}
