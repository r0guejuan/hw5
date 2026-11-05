"""The human side of payments. Agents have no access to this file.

A person's decision goes to the MCP decide_request tool with the approval code
from .env. An approved request then goes through the MCP pay tool, which applies
the shop's cash and vendor rules. Everything here is written to the audit trail.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "mcp_server"))
from server import mcp  # noqa: E402

from audit import audit  # noqa: E402


async def decide_request(request_id: int, approved: bool, approver: str) -> dict:
    """Record a person's decision. If approved, pay the request."""
    arguments = {
        "request_id": request_id,
        "approved": approved,
        "approver": approver,
        "approval_code": os.getenv("APPROVAL_CODE", ""),
    }
    # Written first, so a trail failure stops the decision before anything changes.
    audit("human_decision_attempt", actor=approver, request_id=request_id, approved=approved)
    async with Client(mcp) as client:
        try:
            decision = (await client.call_tool("decide_request", arguments)).structured_content
            audit("human_decision", actor=approver, **decision)
            if not approved:
                return decision
            receipt = (await client.call_tool("pay", {"request_id": request_id})).structured_content
        except Exception as exc:
            audit("payment_refused", actor=approver, request_id=request_id, approved=approved, reason=str(exc))
            raise
    audit("payment_made", actor=approver, **receipt)
    return receipt
