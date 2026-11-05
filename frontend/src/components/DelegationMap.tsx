import { AGENTS, type AgentState, type Link } from "../activity";
import { HandsomeDan } from "./HandsomeDan";

const DAN = 60;
const GAP = 46;
const SPOTS: Record<string, { x: number; y: number }> = {
  boss: { x: 320, y: 50 },
  customer_service: { x: 100, y: 140 },
  inventory: { x: 540, y: 140 },
  facilities: { x: 180, y: 290 },
  accounting: { x: 460, y: 290 },
};

/** Stop each line at the Dans, and shift it sideways so two-way traffic stays visible. */
function linePath({ from, to }: Link): string {
  const a = SPOTS[from];
  const b = SPOTS[to];
  const length = Math.hypot(b.x - a.x, b.y - a.y);
  const ux = (b.x - a.x) / length;
  const uy = (b.y - a.y) / length;
  const shift = 7;
  const sx = a.x + ux * GAP - uy * shift;
  const sy = a.y + uy * GAP + ux * shift;
  const ex = b.x - ux * (GAP + 6) - uy * shift;
  const ey = b.y - uy * (GAP + 6) + ux * shift;
  return `M${sx.toFixed(1)} ${sy.toFixed(1)}L${ex.toFixed(1)} ${ey.toFixed(1)}`;
}

export function DelegationMap({ links, states }: { links: Link[]; states: Record<string, AgentState> }) {
  const summary = links.length
    ? links.map((link) => `${link.from} asked ${link.to} ${link.count} time(s)`).join(". ")
    : "No agent has asked another for help yet.";
  return (
    <section className="delegation-map" aria-labelledby="map-heading">
      <h3 id="map-heading">Who's talking to whom</h3>
      <svg viewBox="0 0 640 350" role="img" aria-label={summary}>
        <defs>
          <marker id="map-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M1 1L9 5L1 9" fill="none" stroke="context-stroke" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </marker>
        </defs>
        {links.map((link) => (
          <path
            key={`${link.from}-${link.to}`}
            className={`link-line ${link.active ? "active" : ""}`}
            d={linePath(link)}
            markerEnd="url(#map-arrow)"
          />
        ))}
        {AGENTS.map((agent) => {
          const spot = SPOTS[agent.id];
          return (
            <g key={agent.id} opacity={states[agent.id].state === "Idle" ? 0.55 : 1}>
              <g transform={`translate(${spot.x - DAN / 2} ${spot.y - DAN / 2})`}>
                <HandsomeDan tie={agent.tie} label="" size={DAN} />
              </g>
              <text className="map-label" x={spot.x} y={spot.y + DAN / 2 + 16}>
                {agent.name}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="map-note">
        {links.length ? "Moving lines are requests still in progress." : "Lines appear here when agents ask each other for help."}
      </p>
    </section>
  );
}
