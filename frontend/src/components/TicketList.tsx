import { useState } from "react";
import { STATUS_LABELS } from "../activity";
import type { Ticket, TicketStatus } from "../types";

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  runningId: number | null;
  onSelect: (id: number) => void;
}

const STAGES: TicketStatus[] = ["open", "in_progress", "waiting_on_approval", "resolved"];

export function TicketList({ tickets, selectedId, runningId, onSelect }: Props) {
  const [filter, setFilter] = useState<TicketStatus | null>(null);
  const stageOf = (ticket: Ticket): TicketStatus => (ticket.id === runningId ? "in_progress" : ticket.status);
  const shown = filter ? tickets.filter((ticket) => stageOf(ticket) === filter) : tickets;

  return (
    <nav className="ticket-list" aria-label="Tickets">
      <h2>Stages</h2>
      <div className="stage-counts" role="group" aria-label="Filter tickets by stage">
        {STAGES.map((stage) => (
          <button
            key={stage}
            className={`${stage === "resolved" ? "resolved" : "unresolved"} ${filter === stage ? "active" : ""}`}
            aria-pressed={filter === stage}
            onClick={() => setFilter(filter === stage ? null : stage)}
          >
            <strong>{tickets.filter((ticket) => stageOf(ticket) === stage).length}</strong>
            <span>{STATUS_LABELS[stage]}</span>
          </button>
        ))}
      </div>
      <div className="list-head">
        <h2>{filter ? `${STATUS_LABELS[filter]} tickets` : "All tickets"}</h2>
        {filter && (
          <button className="link" onClick={() => setFilter(null)}>
            Show all
          </button>
        )}
      </div>
      {shown.length === 0 && <p className="empty">No tickets in this stage.</p>}
      {shown.map((ticket) => {
        const resolved = stageOf(ticket) === "resolved";
        return (
          <button
            key={ticket.id}
            className={`ticket-row ${resolved ? "resolved" : "unresolved"} ${ticket.id === selectedId ? "selected" : ""}`}
            aria-current={ticket.id === selectedId}
            onClick={() => onSelect(ticket.id)}
          >
            <span className="ticket-id">#{ticket.id}</span>
            <span className="ticket-subject">{ticket.subject}</span>
            <span className="ticket-requester">{ticket.requester}</span>
            <span className="badge">{ticket.id === runningId ? "Agents working" : STATUS_LABELS[ticket.status]}</span>
          </button>
        );
      })}
    </nav>
  );
}
