import { useState } from "react";
import { money } from "../activity";
import type { Cash, Oversight } from "../types";

const WIDTH = 640;
const HEIGHT = 210;
const LEFT = 62;
const RIGHT = 16;
const TOP = 14;
const BOTTOM = 30;
const KINDS: Record<string, string> = { invoice: "Invoice", rent: "Rent", purchase_order: "Restock" };

interface Point {
  label: string;
  value: number;
  pending?: boolean;
}

export function CashChart({ payments, cash }: { payments: Oversight["payments"]; cash: Cash }) {
  const [hover, setHover] = useState<number | null>(null);
  const start = payments.length ? payments[0].balance_after + payments[0].amount : cash.balance;
  const points: Point[] = [
    { label: "Start", value: start },
    ...payments.map((p) => ({ label: KINDS[p.kind] ?? p.kind, value: p.balance_after })),
  ];
  const hasPending = cash.available_after_requests !== cash.balance;
  if (hasPending) points.push({ label: "After pending", value: cash.available_after_requests, pending: true });

  const top = Math.max(start, 1);
  const floor = Math.min(0, ...points.map((p) => p.value));
  const x = (i: number) =>
    points.length === 1 ? LEFT : LEFT + (i * (WIDTH - LEFT - RIGHT - 40)) / (points.length - 1);
  const y = (value: number) => TOP + ((top - value) * (HEIGHT - TOP - BOTTOM)) / (top - floor);
  const step = (from: number, to: number) =>
    points
      .slice(from, to + 1)
      .map((p, i) => (i === 0 ? `M${x(from)} ${y(p.value)}` : `H${x(from + i)}V${y(p.value)}`))
      .join("");
  const paidEnd = points.length - (hasPending ? 2 : 1);
  const ticks = [top, top / 2, 0];

  return (
    <section aria-labelledby="cash-heading">
      <h3 id="cash-heading">Cash flow</h3>
      <div className="chart-wrap">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`Checking balance is ${money(cash.balance)}.`}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line className="chart-grid" x1={LEFT} x2={WIDTH - RIGHT} y1={y(tick)} y2={y(tick)} />
              <text className="chart-axis" x={LEFT - 8} y={y(tick) + 4} textAnchor="end">
                ${Math.round(tick).toLocaleString()}
              </text>
            </g>
          ))}
          {paidEnd > 0 && <path className="chart-line" d={step(0, paidEnd)} />}
          {hasPending && <path className="chart-pending" d={step(paidEnd, paidEnd + 1)} />}
          {points.map((point, i) => (
            <g key={i}>
              <text className="chart-axis" x={x(i)} y={HEIGHT - 8} textAnchor={i === 0 ? "start" : "middle"}>
                {point.label}
              </text>
              <circle className={`chart-dot ${point.pending ? "pending" : ""}`} cx={x(i)} cy={y(point.value)} r="5" />
              <circle
                className="chart-hit"
                cx={x(i)}
                cy={y(point.value)}
                r="16"
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
              />
            </g>
          ))}
        </svg>
        {hover !== null && (
          <div
            className="chart-tip"
            style={{ left: `${(x(hover) / WIDTH) * 100}%`, top: `${(y(points[hover].value) / HEIGHT) * 100}%` }}
          >
            {points[hover].label}: {money(points[hover].value)}
          </div>
        )}
      </div>
      <table className="cash-table">
        <thead>
          <tr>
            <th>Step</th>
            <th className="num">Checking</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point, i) => (
            <tr key={i}>
              <td>{point.label}</td>
              <td className="num">{money(point.value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
