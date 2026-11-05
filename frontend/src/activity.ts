import type { AuditEvent, TicketStatus } from "./types";

export const AGENTS = [
  { id: "boss", name: "Boss", role: "Assigns work and makes the final call", tie: "#00356b", tieName: "navy" },
  { id: "inventory", name: "Inventory", role: "Stock, shortfalls, and vendors", tie: "#1f8a4c", tieName: "green" },
  { id: "accounting", name: "Accounting", role: "Cash, invoices, and payments", tie: "#e3a500", tieName: "gold" },
  { id: "facilities", name: "Facilities", role: "Leases and rent", tie: "#d1432f", tieName: "red" },
  { id: "customer_service", name: "Customer Service", role: "Customer drafts", tie: "#c2389a", tieName: "pink" },
];

export const STATUS_LABELS: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In progress",
  waiting_on_approval: "Waiting on approval",
  resolved: "Resolved",
};

export const money = (value: number) =>
  value.toLocaleString("en-US", { style: "currency", currency: "USD" });

export function agentName(id: string): string {
  return AGENTS.find((agent) => agent.id === id)?.name ?? id;
}

export interface FeedItem {
  seq: number;
  actor: string;
  text: string;
  tone: "said" | "tool" | "warning" | "human";
}

/** Agents write Markdown, so remove the bold markers before showing plain text. */
const plain = (value: unknown) => String(value).replace(/\*\*/g, "");

function toolArgs(args: unknown): string {
  if (!args || typeof args !== "object") return "";
  const values = Object.entries(args as Record<string, unknown>)
    .filter(([key]) => !["reason", "body", "note"].includes(key))
    .map(([, value]) => String(value));
  return values.length ? ` (${values.join(", ")})` : "";
}

export function toFeedItem(event: AuditEvent): FeedItem | null {
  const { seq, actor, details: d } = event;
  const name = agentName(actor);
  switch (event.event) {
    case "delegation":
      return { seq, actor: name, tone: "said", text: `Asked ${agentName(d.to_agent)}: ${plain(d.question)}` };
    case "agent_end":
      return actor === "boss" ? null : { seq, actor: name, tone: "said", text: plain(d.output) };
    case "tool_call":
      return { seq, actor: name, tone: "tool", text: `Used ${d.tool}${toolArgs(d.args)}` };
    case "tool_error":
      return { seq, actor: name, tone: "warning", text: `${d.tool} refused: ${d.error}` };
    case "guardrail_block":
      return { seq, actor: name, tone: "warning", text: `Blocked: ${d.reason}` };
    case "agent_error":
    case "delegation_failed":
      return { seq, actor: name, tone: "warning", text: String(d.error) };
    case "human_decision":
      return { seq, actor, tone: "human", text: `Marked request ${d.request_id} as ${d.status}` };
    case "payment_made":
      return { seq, actor, tone: "human", text: `Paid ${money(d.amount)}. Checking is now ${money(d.balance_after)}.` };
    case "ticket_resolved":
      return { seq, actor, tone: "human", text: String(d.note) };
    default:
      return null;
  }
}

export interface AgentState {
  state: "Idle" | "Working" | "Done";
  latest: string;
}

/** Keep only the latest run, plus anything people did after it. */
export function latestRun(events: AuditEvent[]): AuditEvent[] {
  const start = events.map((e) => e.event).lastIndexOf("ticket_start");
  return start === -1 ? events : events.slice(start);
}

export function agentStates(events: AuditEvent[]): Record<string, AgentState> {
  const states: Record<string, AgentState> = {};
  AGENTS.forEach((agent) => (states[agent.id] = { state: "Idle", latest: "" }));
  for (const event of events) {
    const agent = states[event.actor];
    if (!agent) continue;
    if (event.event === "agent_start") agent.state = "Working";
    if (event.event === "agent_end" || event.event === "agent_error") agent.state = "Done";
    const item = toFeedItem(event);
    if (item) agent.latest = item.text;
  }
  return states;
}

export interface Link {
  from: string;
  to: string;
  count: number;
  active: boolean;
}

/** Work out who asked whom in this run, and which requests are still open. */
export function delegationLinks(events: AuditEvent[]): Link[] {
  const links = new Map<string, Link>();
  for (const event of events) {
    if (event.event === "delegation") {
      const key = `${event.actor}>${event.details.to_agent}`;
      const link = links.get(key) ?? { from: event.actor, to: event.details.to_agent, count: 0, active: false };
      link.count += 1;
      link.active = true;
      links.set(key, link);
    }
    if (event.event === "delegation_reply" || event.event === "delegation_failed") {
      const to = event.details.from_agent ?? event.details.to_agent;
      const link = links.get(`${event.actor}>${to}`);
      if (link) link.active = false;
    }
  }
  return [...links.values()];
}
