import { agentName } from "../activity";
import type { Oversight } from "../types";

export function Guardrails({ audit, blocks }: Pick<Oversight, "audit" | "blocks">) {
  return (
    <section aria-labelledby="guardrails-heading">
      <h3 id="guardrails-heading">Guardrails and audit</h3>
      <p className={`audit-status ${audit.passed ? "ok" : "bad"}`}>
        {audit.passed ? "Audit trail OK" : "Audit trail check failed"}: {audit.message}
      </p>
      {blocks.length === 0 ? (
        <p className="empty">No blocked or refused actions yet.</p>
      ) : (
        <ul className="blocks">
          {[...blocks].reverse().map((block) => (
            <li key={block.seq}>
              <strong>{agentName(block.actor)}</strong>
              {block.ticket_id ? ` on ticket ${block.ticket_id}` : ""}: {block.text}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
