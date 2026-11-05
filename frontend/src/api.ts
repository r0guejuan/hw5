import type { AuditEvent, Cash, Oversight, Ticket, TicketDetail } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_URL + path, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : "The request failed.";
    throw new Error(detail);
  }
  return body as T;
}

function post<T>(path: string, data?: object): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: data ? { "Content-Type": "application/json" } : undefined,
    body: data ? JSON.stringify(data) : undefined,
  });
}

export const api = {
  tickets: () => request<Ticket[]>("/api/tickets"),
  ticket: (id: number) => request<TicketDetail>(`/api/tickets/${id}`),
  events: (id: number) => request<AuditEvent[]>(`/api/events?ticket_id=${id}&limit=500`),
  cash: () => request<Cash>("/api/cash"),
  oversight: (id: number) => request<Oversight>(`/api/oversight?ticket_id=${id}`),
  run: (id: number) => post(`/api/tickets/${id}/run`),
  resolve: (id: number, approver: string) => post(`/api/tickets/${id}/resolve`, { approver }),
  approve: (id: number, approver: string) => post(`/api/payments/${id}/approve`, { approver }),
  reject: (id: number, approver: string) => post(`/api/payments/${id}/reject`, { approver }),
  reset: () => post("/api/reset"),
};
