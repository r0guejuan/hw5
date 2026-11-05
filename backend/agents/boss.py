"""Boss agent and the loop that works a ticket from start to finish."""

from __future__ import annotations

import asyncio
import uuid

from pydantic_ai.usage import RunUsage

from agents import accounting, customer_service, facilities, inventory  # noqa: F401
from agents.config import MODEL_NAME
from agents.team import TeamDeps, TicketState, build_agent, mcp_call, run_agent
from audit import AuditError, audit, tokens_used_today
from guardrails import DAILY_TOKEN_LIMIT, USAGE_LIMITS, agents_paused, suspicious_ticket
from models import TicketOutcome, TicketRun, UsageSummary
from server import DB_PATH

TICKET_TIMEOUT = 240.0  # seconds for one whole ticket

boss_agent = build_agent("boss", output_type=TicketOutcome)


async def money_snapshot() -> dict:
    """Read cash through MCP, so a run can prove that no money moved."""
    cash = await mcp_call("check_cash")
    return {"accounts": cash["accounts"], "total_balance": cash["total_balance"]}


async def preflight(ticket_id: int, run_id: str) -> str | None:
    """Return why a ticket must not start. These checks cost no model tokens."""
    if agents_paused():
        return "Agents are paused by AGENTS_PAUSED."
    used = tokens_used_today()
    if used >= DAILY_TOKEN_LIMIT:
        return f"The daily token limit is used up ({used} of {DAILY_TOKEN_LIMIT})."
    ticket = await mcp_call("get_ticket", {"ticket_id": ticket_id})
    flagged = suspicious_ticket(ticket)
    if flagged:
        note = "Held for human review: this ticket contains text that looks like instructions to the agents."
        await mcp_call("update_ticket", {"ticket_id": ticket_id, "status": "waiting_on_approval", "note": note})
        audit("prompt_injection_suspected", run_id=run_id, ticket_id=ticket_id, matched=flagged)
        return note
    return None


async def run_ticket(ticket_id: int) -> TicketRun:
    """Have the Boss work one ticket, and return its outcome and full record."""
    state = TicketState(run_id=uuid.uuid4().hex)
    usage = RunUsage()
    deps = TeamDeps("boss", ticket_id, ("boss",), state)
    audit(
        "ticket_start",
        run_id=state.run_id,
        ticket_id=ticket_id,
        database=DB_PATH.name,
        model=MODEL_NAME,
        limits={
            "requests": USAGE_LIMITS.request_limit,
            "tool_calls": USAGE_LIMITS.tool_calls_limit,
            "total_tokens": USAGE_LIMITS.total_tokens_limit,
        },
    )
    outcome, error = None, None
    before = None
    try:
        refused = await preflight(ticket_id, state.run_id)
        if refused:
            audit("guardrail_block", run_id=state.run_id, ticket_id=ticket_id, reason=refused)
            error = refused
        else:
            before = await money_snapshot()
            result = await asyncio.wait_for(
                run_agent("boss", f"Work ticket {ticket_id}.", deps, usage), timeout=TICKET_TIMEOUT
            )
            outcome = result.output
    except AuditError:
        raise
    except Exception as exc:  # the run record shows what happened before the failure
        error = f"{type(exc).__name__}: {str(exc)[:300]}"

    if before is not None:
        after = await money_snapshot()
        unchanged = before == after
        audit(
            "money_check" if unchanged else "ALERT_money_moved_during_agent_run",
            run_id=state.run_id,
            ticket_id=ticket_id,
            unchanged=unchanged,
            before=before,
            after=after,
        )
        if not unchanged:
            error = "Cash changed during an agent run. Stop and review the audit trail."

    run = TicketRun(
        ticket_id=ticket_id,
        ok=error is None,
        outcome=outcome,
        error=error,
        models_used=sorted(state.models_used),
        delegations=state.delegations,
        tool_calls=state.tool_calls,
        usage=UsageSummary(
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        ),
    )
    audit(
        "ticket_end",
        run_id=state.run_id,
        ticket_id=ticket_id,
        ok=run.ok,
        error=error,
        outcome=outcome.model_dump() if outcome else None,
        models_used=run.models_used,
        usage=run.usage.model_dump(),
        delegations=len(state.delegations),
        guardrail_blocks=state.blocks,
    )
    return run
