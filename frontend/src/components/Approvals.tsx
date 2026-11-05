import { money } from "../activity";
import type { PaymentRequest } from "../types";

interface Props {
  requests: PaymentRequest[];
  approver: string;
  busy: boolean;
  onApproverChange: (value: string) => void;
  onDecide: (id: number, approved: boolean) => void;
}

function title(request: PaymentRequest): string {
  if (request.kind === "invoice") return `Invoice ${request.ref_id}`;
  if (request.kind === "rent") return "Rent";
  return `Purchase order: ${request.qty} × ${request.sku}, size ${request.size}`;
}

export function Approvals({ requests, approver, busy, onApproverChange, onDecide }: Props) {
  const open = requests.filter((r) => r.status === "pending" || r.status === "approved");
  if (open.length === 0) return null;
  const ready = approver.trim().length > 0 && !busy;
  return (
    <section className="approvals" aria-labelledby="approvals-heading">
      <h3 id="approvals-heading">Needs your approval</h3>
      <label className="approver">
        Your name
        <input value={approver} onChange={(e) => onApproverChange(e.target.value)} placeholder="Required to approve" />
      </label>
      {open.map((request) => (
        <article key={request.id} className="approval">
          <div>
            <strong>{title(request)}</strong>
            <p>{request.reason}</p>
          </div>
          <div className="approval-actions">
            <span className="amount">{money(request.amount)}</span>
            <button className="primary" disabled={!ready} onClick={() => onDecide(request.id, true)}>
              {request.status === "approved" ? "Try payment again" : "Approve"}
            </button>
            {request.status === "pending" && (
              <button disabled={!ready} onClick={() => onDecide(request.id, false)}>
                Reject
              </button>
            )}
          </div>
        </article>
      ))}
    </section>
  );
}
