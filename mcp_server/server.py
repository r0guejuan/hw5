"""Campus Customs MCP server: shared database tools for the agent team.

Every tool works on data/campus_customs_new.db, never the original database.
Answers come from database rows or arithmetic on those rows. When a row does
not exist, the tool returns an error instead of guessing.

Agents can prepare payments but cannot approve them. decide_request needs the
APPROVAL_CODE, which no agent is given, and pay refuses anything a person has
not approved. Business rules live in these tools, so they hold for every client.

Run from this folder (stdio):  python server.py
Run (HTTP):                    python server.py --http
HTTP URL:                      http://127.0.0.1:8001/mcp
"""

from __future__ import annotations

import argparse
import calendar
import hmac
import os
import re
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("CAMPUS_DB_PATH") or ROOT / "data" / "campus_customs_new.db")

# Added to the working copy on first write, so a reset from the original still works.
BOARD_TABLES = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    ref_id INTEGER,
    vendor_id INTEGER,
    sku TEXT,
    size TEXT,
    qty INTEGER,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    decided_by TEXT,
    decided_at TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    recipient TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
"""
UNPAID = "('pending', 'approved')"
AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
MAX_NOTE_CHARS = 1000
MAX_DRAFT_CHARS = 1500
# Customers must not see these, however a draft was written.
INTERNAL_TERMS = re.compile(
    r"\b(invoices?|vendors?|suppliers?|unit cost|restock cost|margins?|cash|balance|payment requests?)\b",
    re.IGNORECASE,
)
DISCOUNT_PROMISE = re.compile(r"\d+\s*(%|percent)|\$\s*\d+[\d.,]*\s*off\b", re.IGNORECASE)

mcp = FastMCP("campus-customs")


def connect(write: bool = False) -> sqlite3.Connection:
    """Open the working database, without creating a missing file.

    Reads use a read-only connection. Anything that touches the board tables
    passes write=True, which also makes sure those tables exist.
    """
    if not DB_PATH.exists():
        raise ToolError(f"Database not found: {DB_PATH.name}")
    mode = "rw" if write else "ro"
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    if write:
        conn.executescript(BOARD_TABLES)
    return conn


def shop_today(conn: sqlite3.Connection) -> date:
    """Return the shop's "today" from desk.date_today."""
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    if row is None:
        raise ToolError("The desk table has no date_today row.")
    return date.fromisoformat(row["date_today"])


@mcp.tool
def check_product(sku: str, size: str, qty: int) -> dict:
    """Check whether a quantity of one SKU and size can be filled from stock.

    Returns on-hand stock, the shortfall, unit cost, list price, unit margin,
    the order total at list price, and the cost of restocking the shortfall.
    Use it for customer orders and discount requests. It does not suggest a
    discount, because the database has no discount policy.
    """
    if qty < 1:
        raise ToolError("qty must be at least 1.")
    with closing(connect()) as conn:
        row = conn.execute(
            """
            SELECT i.sku, i.name, i.size, i.qty, i.location,
                   p.unit_cost, p.list_price
            FROM inventory AS i
            JOIN pricing AS p ON p.sku = i.sku
            WHERE i.sku = ? AND i.size = ?
            """,
            (sku, size),
        ).fetchone()
    if row is None:
        raise ToolError(f"No stock and pricing found for {sku}, size {size}.")
    shortfall = max(qty - row["qty"], 0)
    return {
        "sku": row["sku"],
        "name": row["name"],
        "size": row["size"],
        "location": row["location"],
        "requested_qty": qty,
        "on_hand": row["qty"],
        "can_fill": shortfall == 0,
        "shortfall": shortfall,
        "unit_cost": row["unit_cost"],
        "list_price": row["list_price"],
        "unit_margin": round(row["list_price"] - row["unit_cost"], 2),
        "list_total": round(qty * row["list_price"], 2),
        "restock_cost": round(shortfall * row["unit_cost"], 2),
    }


@mcp.tool
def check_vendors() -> dict:
    """List every vendor and whether an open invoice is blocking shipments.

    Each vendor includes its specialty, lead time, and open invoices with days
    overdue. A vendor with an open invoice has can_ship false and no delivery
    date. Otherwise earliest_delivery is the shop's today plus lead_days.
    """
    with closing(connect()) as conn:
        today = shop_today(conn)
        vendors = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors ORDER BY id"
        ).fetchall()
        invoices = conn.execute(
            """
            SELECT id, vendor_id, amount, due_date, description
            FROM invoices
            WHERE status = 'open'
            ORDER BY due_date, id
            """
        ).fetchall()

    results = []
    for vendor in vendors:
        open_invoices = [
            {
                "invoice_id": invoice["id"],
                "amount": invoice["amount"],
                "due_date": invoice["due_date"],
                "days_overdue": max(
                    (today - date.fromisoformat(invoice["due_date"])).days, 0
                ),
                "description": invoice["description"],
            }
            for invoice in invoices
            if invoice["vendor_id"] == vendor["id"]
        ]
        can_ship = not open_invoices
        delivery = today + timedelta(days=vendor["lead_days"])
        results.append(
            {
                "vendor_id": vendor["id"],
                "name": vendor["name"],
                "specialty": vendor["specialty"],
                "lead_days": vendor["lead_days"],
                "can_ship": can_ship,
                "earliest_delivery": delivery.isoformat() if can_ship else None,
                "open_invoices": open_invoices,
                "open_total": round(sum(i["amount"] for i in open_invoices), 2),
            }
        )
    return {"today": today.isoformat(), "vendors": results}


@mcp.tool
def check_rent(lease_id: int) -> dict:
    """Check a lease's rent, due date, and whether cash can cover it.

    Returns the landlord, monthly rent, next due date, and days until due
    (negative when overdue), plus each cash account's balance before and after
    the rent. This tool only checks. It does not pay anything.
    """
    with closing(connect()) as conn:
        today = shop_today(conn)
        lease = conn.execute(
            """
            SELECT id, space_name, landlord, monthly_rent, next_due
            FROM leases
            WHERE id = ?
            """,
            (lease_id,),
        ).fetchone()
        if lease is None:
            raise ToolError(f"No lease found with id {lease_id}.")
        accounts = conn.execute(
            "SELECT name, balance FROM cash_accounts ORDER BY name"
        ).fetchall()

    rent = lease["monthly_rent"]
    return {
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": rent,
        "next_due": lease["next_due"],
        "today": today.isoformat(),
        "days_until_due": (date.fromisoformat(lease["next_due"]) - today).days,
        "accounts": [
            {
                "name": account["name"],
                "balance": account["balance"],
                "balance_after_rent": round(account["balance"] - rent, 2),
                "can_cover": account["balance"] >= rent,
            }
            for account in accounts
        ],
    }


def next_month(day: date) -> date:
    """Return the same day next month, or that month's last day if it is shorter."""
    year = day.year + day.month // 12
    month = day.month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def require_ticket(conn: sqlite3.Connection, ticket_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise ToolError(f"No ticket found with id {ticket_id}.")
    return row


def cash_summary(conn: sqlite3.Connection) -> dict:
    """Return cash on hand and what is left once unpaid requests are counted."""
    balance = conn.execute("SELECT SUM(balance) AS total FROM cash_accounts").fetchone()["total"] or 0
    requested = conn.execute(
        f"SELECT SUM(amount) AS total FROM payment_requests WHERE status IN {UNPAID}"
    ).fetchone()["total"] or 0
    return {
        "total_balance": round(balance, 2),
        "requested_not_paid": round(requested, 2),
        "available_after_requests": round(balance - requested, 2),
    }


def add_request(conn: sqlite3.Connection, ticket_id: int, kind: str, amount: float, reason: str, *,
                ref_id: int | None = None, vendor_id: int | None = None, sku: str | None = None,
                size: str | None = None, qty: int | None = None) -> dict:
    """Create a pending request, or return the matching unpaid one."""
    if not reason.strip():
        raise ToolError("reason must not be empty.")
    require_ticket(conn, ticket_id)
    existing = conn.execute(
        f"""
        SELECT id FROM payment_requests
        WHERE kind = ? AND ref_id IS ? AND vendor_id IS ? AND sku IS ? AND size IS ?
          AND status IN {UNPAID}
        """,
        (kind, ref_id, vendor_id, sku, size),
    ).fetchone()
    if existing:
        request_id = existing["id"]
    else:
        available = cash_summary(conn)["available_after_requests"]
        if amount > available:
            raise ToolError(
                f"Refused: this needs {amount:.2f}, but only {available:.2f} is left after "
                f"unpaid requests. The gap is {amount - available:.2f}."
            )
        request_id = conn.execute(
            """
            INSERT INTO payment_requests
                (ticket_id, kind, ref_id, vendor_id, sku, size, qty, amount, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, kind, ref_id, vendor_id, sku, size, qty, amount, reason.strip()),
        ).lastrowid
    row = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
    cash = cash_summary(conn)
    return {
        **dict(row),
        "already_requested": existing is not None,
        "cash": cash,
        "note": "Waiting for human approval. Nothing has been paid.",
    }


@mcp.tool
def list_tickets() -> list[dict]:
    """List every ticket with its status, including resolved tickets."""
    with closing(connect()) as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    return [dict(row) for row in rows]


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket on the board that is not resolved."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket with its payment requests and saved customer drafts."""
    with closing(connect(write=True)) as conn:
        ticket = dict(require_ticket(conn, ticket_id))
        ticket["payment_requests"] = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM payment_requests WHERE ticket_id = ? ORDER BY id", (ticket_id,)
            )
        ]
        ticket["drafts"] = [
            dict(row)
            for row in conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))
        ]
    return ticket


@mcp.tool
def check_cash() -> dict:
    """Show cash on hand, unpaid payment requests, and what would be left.

    Use available_after_requests before preparing any new payment, because
    earlier requests on other tickets may already claim the same cash.
    """
    with closing(connect(write=True)) as conn:
        today = shop_today(conn)
        accounts = conn.execute("SELECT name, balance, date FROM cash_accounts ORDER BY name").fetchall()
        requests = conn.execute(
            f"""
            SELECT id, ticket_id, kind, amount, status FROM payment_requests
            WHERE status IN {UNPAID} ORDER BY id
            """
        ).fetchall()
        summary = cash_summary(conn)
    return {
        "today": today.isoformat(),
        "accounts": [dict(row) for row in accounts],
        "unpaid_requests": [dict(row) for row in requests],
        **summary,
    }


@mcp.tool
def request_invoice_payment(ticket_id: int, invoice_id: int, reason: str) -> dict:
    """Prepare an open invoice for human approval. This does not pay it.

    The amount comes from the invoices table.
    """
    with closing(connect(write=True)) as conn, conn:
        invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if invoice is None:
            raise ToolError(f"No invoice found with id {invoice_id}.")
        if invoice["status"] != "open":
            raise ToolError(f"Invoice {invoice_id} is not open. Its status is {invoice['status']}.")
        return add_request(
            conn, ticket_id, "invoice", invoice["amount"], reason,
            ref_id=invoice_id, vendor_id=invoice["vendor_id"],
        )


@mcp.tool
def request_rent_payment(ticket_id: int, lease_id: int, reason: str) -> dict:
    """Prepare a lease's next rent for human approval. This does not pay it.

    The amount comes from the leases table.
    """
    with closing(connect(write=True)) as conn, conn:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            raise ToolError(f"No lease found with id {lease_id}.")
        if require_ticket(conn, ticket_id)["lease_id"] != lease_id:
            raise ToolError(f"Lease {lease_id} is not linked to ticket {ticket_id}.")
        return add_request(conn, ticket_id, "rent", lease["monthly_rent"], reason, ref_id=lease_id)


@mcp.tool
def request_purchase_order(ticket_id: int, vendor_id: int, sku: str, size: str, qty: int, reason: str) -> dict:
    """Prepare a restock purchase order for human approval. This does not place it.

    The amount is qty times the unit cost in the pricing table, and qty cannot
    exceed the ticket's shortfall. vendor_blocked is true while the vendor has
    an open invoice, and pay refuses the order until that invoice is paid.
    """
    if qty < 1:
        raise ToolError("qty must be at least 1.")
    with closing(connect(write=True)) as conn, conn:
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            raise ToolError(f"No vendor found with id {vendor_id}.")
        product = conn.execute(
            """
            SELECT p.unit_cost, i.qty AS on_hand FROM inventory AS i
            JOIN pricing AS p ON p.sku = i.sku
            WHERE i.sku = ? AND i.size = ?
            """,
            (sku, size),
        ).fetchone()
        if product is None:
            raise ToolError(f"No stock and pricing found for {sku}, size {size}.")
        ticket = require_ticket(conn, ticket_id)
        if (ticket["sku"], ticket["size"]) != (sku, size):
            raise ToolError(f"Ticket {ticket_id} is not for {sku}, size {size}.")
        shortfall = max((ticket["qty"] or 0) - product["on_hand"], 0)
        if qty > shortfall:
            raise ToolError(f"Refused: ticket {ticket_id} is only short {shortfall} of {sku}, size {size}.")
        request = add_request(
            conn, ticket_id, "purchase_order", round(qty * product["unit_cost"], 2), reason,
            vendor_id=vendor_id, sku=sku, size=size, qty=qty,
        )
        blocked = conn.execute(
            "SELECT COUNT(*) AS n FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,)
        ).fetchone()["n"]
    return {**request, "vendor_blocked": blocked > 0}


@mcp.tool
def decide_request(request_id: int, approved: bool, approver: str, approval_code: str) -> dict:
    """Record a person's approve or reject decision on a payment request.

    Needs the APPROVAL_CODE, which only the human approval path has. An agent
    name cannot be the approver. Approving a request that is already approved
    is allowed, so a refused payment can be tried again.
    """
    expected = os.getenv("APPROVAL_CODE", "")
    if not expected or not hmac.compare_digest(approval_code, expected):
        raise ToolError("Refused: a valid human approval code is required.")
    approver = approver.strip()
    if not approver or approver.lower().replace(" ", "_") in AGENT_NAMES:
        raise ToolError("Refused: the approver must be a person.")
    with closing(connect(write=True)) as conn, conn:
        request = conn.execute(
            "SELECT ticket_id, status, decided_by FROM payment_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if request is None:
            raise ToolError(f"No payment request found with id {request_id}.")
        if approved and request["status"] == "approved":
            return {
                "request_id": request_id,
                "ticket_id": request["ticket_id"],
                "status": "approved",
                "decided_by": request["decided_by"],
            }
        if request["status"] != "pending":
            raise ToolError(f"Request {request_id} is already {request['status']}.")
        status = "approved" if approved else "rejected"
        conn.execute(
            "UPDATE payment_requests SET status = ?, decided_by = ?, decided_at = ? WHERE id = ?",
            (status, approver, shop_today(conn).isoformat(), request_id),
        )
    return {
        "request_id": request_id,
        "ticket_id": request["ticket_id"],
        "status": status,
        "decided_by": approver,
    }


@mcp.tool
def pay(request_id: int, account: str = "checking") -> dict:
    """Pay a request that a person has approved, and update the related tables.

    Refuses a request that is not approved, a payment the account cannot
    cover, and a purchase order for a vendor with an open invoice. No agent is
    given this tool. The backend calls it after a person approves the request.
    """
    with closing(connect(write=True)) as conn, conn:
        request = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if request is None:
            raise ToolError(f"No payment request found with id {request_id}.")
        if request["status"] != "approved" or not request["decided_by"]:
            raise ToolError(f"Request {request_id} needs human approval. Its status is {request['status']}.")
        amount, kind = request["amount"], request["kind"]
        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if cash is None:
            raise ToolError(f"No cash account named {account}.")
        if cash["balance"] < amount:
            raise ToolError(f"Refused: {account} has {cash['balance']:.2f}, and this payment needs {amount:.2f}.")
        if kind == "purchase_order":
            blocked = conn.execute(
                "SELECT COUNT(*) AS n FROM invoices WHERE vendor_id = ? AND status = 'open'",
                (request["vendor_id"],),
            ).fetchone()["n"]
            if blocked:
                raise ToolError("Refused: this vendor will not ship while it has an open unpaid invoice.")
        elif kind == "invoice":
            invoice = conn.execute(
                "SELECT amount, status FROM invoices WHERE id = ?", (request["ref_id"],)
            ).fetchone()
            if invoice is None or invoice["status"] != "open" or invoice["amount"] != amount:
                raise ToolError("Refused: the invoice no longer matches this request.")
        else:
            lease = conn.execute(
                "SELECT monthly_rent FROM leases WHERE id = ?", (request["ref_id"],)
            ).fetchone()
            if lease is None or lease["monthly_rent"] != amount:
                raise ToolError("Refused: the lease no longer matches this request.")

        today = shop_today(conn)
        changed = conn.execute(
            "UPDATE payment_requests SET status = 'paid' WHERE id = ? AND status = 'approved'",
            (request_id,),
        ).rowcount
        if not changed:
            raise ToolError(f"Request {request_id} was already handled.")
        conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
            (amount, today.isoformat(), account),
        )
        update = {}
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (request["ref_id"],))
            update = {"invoice_status": "paid"}
        elif kind == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (request["ref_id"],)).fetchone()
            next_due = next_month(date.fromisoformat(lease["next_due"])).isoformat()
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (next_due, request["ref_id"]))
            update = {"lease_next_due": next_due}
        else:
            lead = conn.execute(
                "SELECT lead_days FROM vendors WHERE id = ?", (request["vendor_id"],)
            ).fetchone()["lead_days"]
            update = {"earliest_delivery": (today + timedelta(days=lead)).isoformat()}
        ref_id = request["id"] if kind == "purchase_order" else request["ref_id"]
        payment_id = conn.execute(
            """
            INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, ref_id, amount, account, today.isoformat(), request["decided_by"]),
        ).lastrowid
        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    return {
        "payment_id": payment_id,
        "request_id": request_id,
        "ticket_id": request["ticket_id"],
        "kind": kind,
        "amount": amount,
        "account": account,
        "balance_after": round(balance["balance"], 2),
        "approved_by": request["decided_by"],
        **update,
    }


@mcp.tool
def save_draft(ticket_id: int, recipient: str, body: str) -> dict:
    """Save a customer message on the board. This never sends anything.

    Refuses a draft for anyone but the ticket's requester, and a draft that
    shares internal details or promises a discount.
    """
    if not recipient.strip() or not body.strip():
        raise ToolError("recipient and body must not be empty.")
    if len(body) > MAX_DRAFT_CHARS:
        raise ToolError(f"Draft is too long. The limit is {MAX_DRAFT_CHARS} characters.")
    with closing(connect(write=True)) as conn, conn:
        requester = require_ticket(conn, ticket_id)["requester"]
        if recipient.strip().lower() != requester.lower():
            raise ToolError(f"Refused: drafts for ticket {ticket_id} must go to {requester}.")
        vendor_names = [row["name"] for row in conn.execute("SELECT name FROM vendors")]
        internal = INTERNAL_TERMS.search(body)
        if internal or any(name.lower() in body.lower() for name in vendor_names):
            raise ToolError("Refused: customer drafts cannot include internal business details.")
        if DISCOUNT_PROMISE.search(body):
            raise ToolError("Refused: the shop has no discount policy, so a draft cannot offer one.")
        created_at = shop_today(conn).isoformat()
        draft_id = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, body, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, recipient.strip(), body.strip(), created_at),
        ).lastrowid
    return {"draft_id": draft_id, "ticket_id": ticket_id, "recipient": recipient.strip(), "sent": False}


@mcp.tool
def update_ticket(
    ticket_id: int,
    status: Literal["open", "in_progress", "waiting_on_approval", "resolved"],
    note: str,
) -> dict:
    """Set a ticket's status and add a note after its existing notes.

    Refuses to resolve a ticket that still has an unpaid payment request.
    """
    if not note.strip():
        raise ToolError("note must not be empty.")
    if len(note) > MAX_NOTE_CHARS:
        raise ToolError(f"Note is too long. The limit is {MAX_NOTE_CHARS} characters.")
    with closing(connect(write=True)) as conn, conn:
        ticket = require_ticket(conn, ticket_id)
        unpaid = conn.execute(
            f"SELECT COUNT(*) AS n FROM payment_requests WHERE ticket_id = ? AND status IN {UNPAID}",
            (ticket_id,),
        ).fetchone()["n"]
        if status == "resolved" and unpaid:
            raise ToolError(f"Ticket {ticket_id} still has {unpaid} unpaid payment request(s).")
        notes = "\n".join(part for part in (ticket["notes"], note.strip()) if part)
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
    return {"ticket_id": ticket_id, "status": status, "notes": notes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus Customs MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve Streamable HTTP on port 8001 (keeps FastAPI free on 8000)",
    )
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8001)
    else:
        mcp.run()
