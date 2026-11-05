"""Campus Customs API for the React dashboard.

Run from the backend folder:
  uvicorn main:app --reload --port 8000

Shop data comes from the MCP server. Agents can't reach these routes, so
approving a payment here always means a person clicked approve.
"""

from __future__ import annotations

import asyncio
import os
import shutil

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp.exceptions import ToolError

from agents.boss import run_ticket
from agents.config import ROOT
from agents.team import mcp_call
from approvals import decide_request
from audit import audit, read_trail, tokens_used_today, verify_trail
from guardrails import DAILY_TOKEN_LIMIT, USAGE_LIMITS
from models import PaymentDecision, TicketRun
from server import DB_PATH

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
BOARD_EVENTS = {
    "ticket_start",
    "ticket_end",
    "agent_start",
    "agent_end",
    "agent_error",
    "delegation",
    "delegation_reply",
    "delegation_failed",
    "tool_call",
    "tool_result",
    "tool_error",
    "guardrail_block",
    "prompt_injection_suspected",
    "human_decision",
    "payment_made",
    "payment_refused",
    "ticket_resolved",
    "database_reset",
}

app = FastAPI(title="Campus Customs Multi-Agent Operations")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# One run at a time, so tickets can't compete for the same cash or double the token spend.
run_lock = asyncio.Lock()


@app.exception_handler(ToolError)
async def tool_refused(request: Request, exc: ToolError) -> JSONResponse:
    """Pass MCP refusals to the dashboard as readable errors."""
    message = str(exc)
    return JSONResponse({"detail": message}, status_code=404 if message.startswith("No ") else 409)


@app.get("/api/tickets")
async def list_tickets() -> list[dict]:
    return await mcp_call("list_tickets")


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int) -> dict:
    return await mcp_call("get_ticket", {"ticket_id": ticket_id})


@app.post("/api/tickets/{ticket_id}/run")
async def run_team(ticket_id: int) -> TicketRun:
    if run_lock.locked():
        raise HTTPException(409, "The agents are already working a ticket.")
    async with run_lock:
        ticket = await mcp_call("get_ticket", {"ticket_id": ticket_id})
        if ticket["status"] == "resolved":
            raise HTTPException(409, f"Ticket {ticket_id} is already resolved.")
        return await run_ticket(ticket_id)


@app.get("/api/events")
def recent_events(
    limit: int = Query(100, ge=1, le=500),
    ticket_id: int | None = None,
    after_seq: int = Query(0, ge=0),
) -> list[dict]:
    """Return agent events since the last reset, oldest first.

    Use after_seq to fetch only new ones. The full history stays in the audit trail.
    """
    trail = read_trail()
    last_reset = max((e["seq"] for e in trail if e["event"] == "database_reset"), default=0)
    events = [
        entry
        for entry in trail
        if entry["event"] in BOARD_EVENTS
        and entry["seq"] > max(after_seq, last_reset - 1)
        and (ticket_id is None or entry["ticket_id"] == ticket_id)
    ]
    return events[-limit:]


@app.get("/api/oversight")
def oversight(ticket_id: int | None = None) -> dict:
    """Return token use, audit health, guardrail blocks, and payments since the last reset."""
    trail = read_trail()
    last_reset = max((e["seq"] for e in trail if e["event"] == "database_reset"), default=0)
    recent = [e for e in trail if e["seq"] >= last_reset]
    ticket_events = [e for e in recent if e["ticket_id"] == ticket_id]
    start = max((i for i, e in enumerate(ticket_events) if e["event"] == "ticket_start"), default=None)
    run = ticket_events[start:] if start is not None else []
    replies = [e["details"]["usage"] for e in run if e["event"] == "agent_step" and e["details"].get("model")]
    passed, message = verify_trail()
    return {
        "usage": {
            "tokens": sum(r["input_tokens"] + r["output_tokens"] for r in replies),
            "requests": len(replies),
            "token_limit": USAGE_LIMITS.total_tokens_limit,
            "request_limit": USAGE_LIMITS.request_limit,
            "tokens_today": tokens_used_today(),
            "daily_limit": DAILY_TOKEN_LIMIT,
        },
        "audit": {"passed": passed, "message": message},
        "blocks": [
            {
                "seq": e["seq"],
                "ticket_id": e["ticket_id"],
                "actor": e["actor"],
                "text": e["details"].get("reason") or e["details"].get("error") or e["details"].get("matched"),
            }
            for e in recent
            if e["event"] in ("guardrail_block", "tool_error", "payment_refused", "prompt_injection_suspected")
        ][-8:],
        "payments": [
            {
                "seq": e["seq"],
                "ticket_id": e["ticket_id"],
                "kind": e["details"]["kind"],
                "amount": e["details"]["amount"],
                "balance_after": e["details"]["balance_after"],
            }
            for e in recent
            if e["event"] == "payment_made"
        ],
    }


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int, body: PaymentDecision) -> dict:
    """Let a person close a ticket. MCP refuses if a payment is still unpaid."""
    note = f"Resolved by {body.approver}."
    result = await mcp_call("update_ticket", {"ticket_id": ticket_id, "status": "resolved", "note": note})
    audit("ticket_resolved", ticket_id=ticket_id, actor=body.approver, note=note)
    return result


@app.post("/api/payments/{request_id}/approve")
async def approve_payment(request_id: int, body: PaymentDecision) -> dict:
    """Pay an approved request, then close the ticket if nothing is left to pay."""
    receipt = await decide_request(request_id, True, body.approver)
    ticket_id = receipt["ticket_id"]
    ticket = await mcp_call("get_ticket", {"ticket_id": ticket_id})
    unpaid = [r for r in ticket["payment_requests"] if r["status"] in ("pending", "approved")]
    if not unpaid and ticket["status"] == "waiting_on_approval":
        note = f"All payments approved by {body.approver} and paid."
        await mcp_call("update_ticket", {"ticket_id": ticket_id, "status": "resolved", "note": note})
        audit("ticket_resolved", ticket_id=ticket_id, actor=body.approver, note=note)
        return {**receipt, "ticket_status": "resolved"}
    return {**receipt, "ticket_status": ticket["status"]}


@app.post("/api/payments/{request_id}/reject")
async def reject_payment(request_id: int, body: PaymentDecision) -> dict:
    return await decide_request(request_id, False, body.approver)


@app.get("/api/cash")
async def checking_balance() -> dict:
    cash = await mcp_call("check_cash")
    checking = next((a for a in cash["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account found.")
    return {
        "account": "checking",
        "balance": checking["balance"],
        "date": checking["date"],
        "available_after_requests": cash["available_after_requests"],
        "unpaid_requests": cash["unpaid_requests"],
    }


@app.post("/api/reset")
async def reset_database() -> dict:
    """Copy the original database over the working copy. The audit trail stays."""
    if run_lock.locked():
        raise HTTPException(409, "Wait for the agents to finish before resetting.")
    async with run_lock:
        temporary = DB_PATH.with_suffix(".resetting")
        shutil.copyfile(ORIGINAL_DB, temporary)
        os.replace(temporary, DB_PATH)
        audit("database_reset", actor="dashboard", database=DB_PATH.name, source=ORIGINAL_DB.name)
    return {"reset": True, "database": DB_PATH.name}
