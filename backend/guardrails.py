"""Guardrails checked in code, so they hold even if a prompt is ignored.

Rules about shop data, such as cash, quantities, and draft content, live in the
MCP tools. This file controls what each agent may do and how much it may spend.
"""

from __future__ import annotations

import json
import os
import re

from pydantic_ai.usage import UsageLimits

# Which MCP tools each agent gets. pay and decide_request are on no list.
ROLE_TOOLS: dict[str, set[str]] = {
    "boss": {"get_ticket", "list_open_tickets", "update_ticket"},
    "inventory": {"get_ticket", "check_product", "check_vendors"},
    "accounting": {
        "get_ticket",
        "check_cash",
        "check_product",
        "check_rent",
        "check_vendors",
        "request_invoice_payment",
        "request_purchase_order",
        "request_rent_payment",
    },
    "facilities": {"get_ticket", "check_rent"},
    "customer_service": {"get_ticket", "save_draft"},
}
HUMAN_ONLY_TOOLS = {"pay", "decide_request"}
WRITE_TOOLS = {
    "request_invoice_payment",
    "request_purchase_order",
    "request_rent_payment",
    "save_draft",
    "update_ticket",
}

# Spending limits. Each ticket's limits are shared by the whole team.
USAGE_LIMITS = UsageLimits(request_limit=24, tool_calls_limit=30, total_tokens_limit=40_000)
DAILY_TOKEN_LIMIT = 250_000
SOFT_REQUEST_LIMIT = 16  # stop delegating here, so the Boss has room to finish
MAX_CHAIN = 3  # boss -> accounting -> inventory is as deep as help can go
MAX_DELEGATIONS = 5  # per ticket
MAX_PER_TEAMMATE = 2  # times one agent can be asked on a ticket
MAX_QUESTION_CHARS = 3000
MAX_WRITES = 6  # database writes per ticket
MAX_SAME_CALL = 2  # identical calls by one agent on a ticket

INJECTION = re.compile(
    r"ignore (all |any |the |your )?(previous|prior|above|earlier)"
    r"|disregard (all |any |the |your )?(previous|prior|above|instructions|rules)"
    r"|system prompt|you are now|new instructions|developer mode"
    r"|(approve|pay|wire|transfer) (this|the|it|me|us|all)\b.*\b(now|immediately|without)",
    re.IGNORECASE,
)


def agents_paused() -> bool:
    """AGENTS_PAUSED=1 is the kill switch for all agent work."""
    return os.getenv("AGENTS_PAUSED", "").strip().lower() in {"1", "true", "yes"}


def suspicious_ticket(ticket: dict) -> str | None:
    """Return the text that looks like a prompt injection, if there is any."""
    for field in ("requester", "subject", "notes"):
        match = INJECTION.search(str(ticket.get(field) or ""))
        if match:
            return f"{field}: {match.group(0)}"
    return None


def check_tool_call(agent: str, ticket_id: int, tool: str, args: dict, counts: dict) -> str | None:
    """Return why a tool call must be blocked, or None if it may run."""
    if tool in HUMAN_ONLY_TOOLS:
        return f"{tool} is only for people."
    if tool not in ROLE_TOOLS[agent]:
        return f"{agent} is not allowed to use {tool}."
    if "ticket_id" in args and args["ticket_id"] != ticket_id:
        return f"This run is limited to ticket {ticket_id}."
    key = f"{agent}:{tool}:{json.dumps(args, sort_keys=True, default=str)}"
    counts[key] = counts.get(key, 0) + 1
    if counts[key] > MAX_SAME_CALL:
        return "You already made this exact call. Use the earlier result."
    if tool in WRITE_TOOLS:
        counts["writes"] = counts.get("writes", 0) + 1
        if counts["writes"] > MAX_WRITES:
            return "This ticket has reached its limit of database writes."
    return None
