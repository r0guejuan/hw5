import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { agentStates, delegationLinks, latestRun, money, STATUS_LABELS, toFeedItem, type FeedItem } from "./activity";
import { api } from "./api";
import { ActivityFeed } from "./components/ActivityFeed";
import { AgentBoard } from "./components/AgentBoard";
import { Approvals } from "./components/Approvals";
import { CashChart } from "./components/CashChart";
import { Celebration } from "./components/Celebration";
import { Customize } from "./components/Customize";
import { DelegationMap } from "./components/DelegationMap";
import { Guardrails } from "./components/Guardrails";
import { TicketList } from "./components/TicketList";
import { TokenMeter } from "./components/TokenMeter";
import { useLayout, type PanelId } from "./layout";
import type { AuditEvent, Cash, Oversight, Ticket, TicketDetail } from "./types";

const POLL_MS = 1500;
const CELEBRATE_MS = 4000;

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const id = Number(new URLSearchParams(window.location.search).get("ticket"));
    return id || null;
  });
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [approver, setApprover] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(false);
  const [oversight, setOversight] = useState<Oversight | null>(null);
  const [celebrating, setCelebrating] = useState<number | null>(null);
  const lastStatuses = useRef(new Map<number, string>());
  const [layout, setLayout] = useLayout();
  const [customizing, setCustomizing] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [ticketRows, cashRow] = await Promise.all([api.tickets(), api.cash()]);
      setTickets(ticketRows);
      setCash(cashRow);
      if (selectedId !== null) {
        const [ticket, rows, stats] = await Promise.all([
          api.ticket(selectedId),
          api.events(selectedId),
          api.oversight(selectedId),
        ]);
        setDetail(ticket);
        setEvents(rows);
        setOversight(stats);
      }
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, [selectedId]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (selectedId === null && tickets.length > 0) setSelectedId(tickets[0].id);
  }, [tickets, selectedId]);

  useEffect(() => {
    const justResolved = tickets.find((ticket) => {
      const before = lastStatuses.current.get(ticket.id);
      return ticket.status === "resolved" && before !== undefined && before !== "resolved";
    });
    tickets.forEach((ticket) => lastStatuses.current.set(ticket.id, ticket.status));
    if (justResolved) setCelebrating(justResolved.id);
  }, [tickets]);

  useEffect(() => {
    if (celebrating === null) return;
    const timer = setTimeout(() => setCelebrating(null), CELEBRATE_MS);
    return () => clearTimeout(timer);
  }, [celebrating]);

  const selectTicket = (id: number) => {
    setSelectedId(id);
    setDetail(null);
    setEvents([]);
    setError("");
  };

  const act = async (work: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Something went wrong.");
    } finally {
      setBusy(false);
      await refresh();
    }
  };

  const runTeam = async () => {
    if (selectedId === null) return;
    setRunningId(selectedId);
    await act(() => api.run(selectedId));
    setRunningId(null);
  };

  const resetBoard = () => {
    if (window.confirm("Reset all tickets and cash to their original values?")) {
      setDetail(null);
      setEvents([]);
      act(api.reset);
    }
  };

  const run = useMemo(() => latestRun(events), [events]);
  const states = useMemo(() => agentStates(run), [run]);
  const links = useMemo(() => delegationLinks(run), [run]);
  const feed = useMemo(
    () => run.map(toFeedItem).filter((item): item is FeedItem => item !== null),
    [run],
  );
  const finished = [...run].reverse().find((event) => event.event === "ticket_end");
  const outcome = finished?.details.outcome;
  const runError = finished?.details.error;
  const requests = detail?.payment_requests ?? [];
  const unpaid = requests.some((r) => r.status === "pending" || r.status === "approved");
  const isRunning = runningId !== null;
  const canRun = detail !== null && detail.status !== "resolved" && !isRunning && !busy;
  const canResolve = detail?.status === "waiting_on_approval" && !unpaid && !isRunning;

  const panelContent: Record<PanelId, ReactNode> = {
    summary: (outcome || runError) && detail && (
      <section className="summary" aria-labelledby="summary-heading">
        <h3 id="summary-heading">Summary</h3>
        {outcome && <p>{outcome.summary}</p>}
        {runError && <p className="error-text">{runError}</p>}
        {outcome?.human_actions?.length > 0 && detail.status !== "resolved" && (
          <>
            <h4>Left for a person</h4>
            <ul>
              {outcome.human_actions.map((action: string) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </>
        )}
        {canResolve && (
          <div className="resolve">
            <label className="approver">
              Your name
              <input value={approver} onChange={(e) => setApprover(e.target.value)} placeholder="Required to resolve" />
            </label>
            <button
              disabled={!approver.trim() || busy}
              onClick={() => act(() => api.resolve(detail.id, approver.trim()))}
            >
              Mark resolved
            </button>
          </div>
        )}
      </section>
    ),
    approvals: unpaid && (
      <Approvals
        requests={requests}
        approver={approver}
        busy={busy || isRunning}
        onApproverChange={setApprover}
        onDecide={(id, approved) =>
          act(() => (approved ? api.approve(id, approver.trim()) : api.reject(id, approver.trim())))
        }
      />
    ),
    drafts: detail && detail.drafts.length > 0 && (
      <section aria-labelledby="drafts-heading">
        <h3 id="drafts-heading">Customer draft</h3>
        {detail.drafts.map((draft) => (
          <article key={draft.id} className="draft">
            <p className="muted">To {draft.recipient} · Not sent</p>
            <p>{draft.body}</p>
          </article>
        ))}
      </section>
    ),
    agents: <AgentBoard states={states} cheering={celebrating !== null} />,
    map: <DelegationMap links={links} states={states} />,
    activity: <ActivityFeed items={feed} />,
    tokens: oversight && <TokenMeter usage={oversight.usage} />,
    guardrails: oversight && <Guardrails audit={oversight.audit} blocks={oversight.blocks} />,
    cash: oversight && cash && <CashChart payments={oversight.payments} cash={cash} />,
  };

  return (
    <div className="app">
      {celebrating !== null && <Celebration ticketId={celebrating} />}
      <header className="topbar">
        <div>
          <p className="eyebrow">Campus Customs</p>
          <h1>Operations board</h1>
        </div>
        <div className="topbar-right">
          <div className="balance" aria-live="polite">
            <span>Checking balance</span>
            <strong>{cash ? money(cash.balance) : "—"}</strong>
            {cash && cash.available_after_requests !== cash.balance && (
              <small>{money(cash.available_after_requests)} after pending requests</small>
            )}
          </div>
          <button onClick={() => setCustomizing(true)}>Customize</button>
          <button onClick={resetBoard} disabled={isRunning || busy}>
            Reset board
          </button>
        </div>
      </header>

      {offline && (
        <p className="alert" role="alert">
          Can't reach the backend at http://localhost:8000. Check that the server is running.
        </p>
      )}

      {customizing && <Customize layout={layout} onChange={setLayout} onClose={() => setCustomizing(false)} />}

      <main className={`layout tickets-${layout.side}`}>
        <TicketList tickets={tickets} selectedId={selectedId} runningId={runningId} onSelect={selectTicket} />

        <div className="workspace">
          {detail ? (
            <>
              <section className="ticket-head">
                <div>
                  <p className="eyebrow">
                    Ticket {detail.id} · {detail.requester}
                  </p>
                  <h2>{detail.subject}</h2>
                  <p className="muted">{detail.notes?.split("\n")[0]}</p>
                </div>
                <div className="ticket-actions">
                  <span className={`badge ${runningId === detail.id ? "running" : detail.status}`}>
                    {runningId === detail.id ? "Agents working" : STATUS_LABELS[detail.status]}
                  </span>
                  <button className="primary" onClick={runTeam} disabled={!canRun}>
                    {runningId === detail.id ? "Running…" : run.length ? "Run again" : "Start agent team"}
                  </button>
                </div>
              </section>

              {error && (
                <p className="alert" role="alert">
                  {error}
                </p>
              )}

              <div className="panels">
                {layout.panels
                  .filter((panel) => panel.visible && panelContent[panel.id])
                  .map((panel) => (
                    <div key={panel.id} className={`panel-slot ${panel.wide ? "wide" : ""}`}>
                      {panelContent[panel.id]}
                    </div>
                  ))}
              </div>
            </>
          ) : (
            <p className="empty">Loading ticket…</p>
          )}
        </div>
      </main>
    </div>
  );
}
