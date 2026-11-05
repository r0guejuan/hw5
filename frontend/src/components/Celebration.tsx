import { useMemo } from "react";

const COLORS = ["#00356b", "#286dc0", "#63aaff", "#ffffff"];

export function Celebration({ ticketId }: { ticketId: number }) {
  const pieces = useMemo(
    () =>
      Array.from({ length: 70 }, (_, index) => ({
        left: `${Math.random() * 100}%`,
        delay: `${Math.random() * 0.9}s`,
        color: COLORS[index % COLORS.length],
      })),
    [],
  );
  return (
    <div className="celebration">
      <p className="celebration-banner" role="status">
        Ticket {ticketId} resolved. Boola boola!
      </p>
      {pieces.map((piece, index) => (
        <span
          key={index}
          className="confetti"
          style={{ left: piece.left, animationDelay: piece.delay, background: piece.color }}
        />
      ))}
    </div>
  );
}
