export type TicketStatus = "open" | "in_progress" | "waiting_on_approval" | "resolved";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  status: TicketStatus;
  notes: string | null;
}

export interface PaymentRequest {
  id: number;
  ticket_id: number;
  kind: "invoice" | "rent" | "purchase_order";
  ref_id: number | null;
  sku: string | null;
  size: string | null;
  qty: number | null;
  amount: number;
  reason: string;
  status: "pending" | "approved" | "rejected" | "paid";
  decided_by: string | null;
}

export interface Draft {
  id: number;
  recipient: string;
  body: string;
}

export interface TicketDetail extends Ticket {
  payment_requests: PaymentRequest[];
  drafts: Draft[];
}

export interface AuditEvent {
  seq: number;
  timestamp: string;
  event: string;
  ticket_id: number | null;
  actor: string;
  details: Record<string, any>;
}

export interface Cash {
  balance: number;
  available_after_requests: number;
}

export interface Oversight {
  usage: {
    tokens: number;
    requests: number;
    token_limit: number;
    request_limit: number;
    tokens_today: number;
    daily_limit: number;
  };
  audit: { passed: boolean; message: string };
  blocks: { seq: number; ticket_id: number | null; actor: string; text: string }[];
  payments: { seq: number; ticket_id: number; kind: string; amount: number; balance_after: number }[];
}
