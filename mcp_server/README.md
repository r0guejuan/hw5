# Campus Customs MCP Server

This MCP server gives the Campus Customs agent team one shared set of tools for checking shop data. Agents use it to look up stock, vendors, and rent from the database, so they don't have to guess.

## Database

The server uses `data/campus_customs_new.db`, the working copy of the shop database. It never touches the original, `data/campus_customs.db`.

Tools return database values or arithmetic on those values, and return an error when a record doesn't exist. Board tools add two tables to the working copy the first time they run: `payment_requests` and `drafts`.

## Tools

**Ticket checks (read-only)**

| Tool | Reads | Ticket | What it returns |
|---|---|---|---|
| `check_vendors()` | `vendors`, `invoices`, `desk` | 101 | Each vendor's specialty, lead time, open invoices, days overdue, whether it can ship, and its earliest delivery date |
| `check_rent(lease_id)` | `leases`, `cash_accounts`, `desk` | 102 | The landlord, rent, due date, days until due, and each cash account's balance before and after rent |
| `check_product(sku, size, qty)` | `inventory`, `pricing` | 103 | Stock on hand, shortfall, unit cost, list price, unit margin, list total, and restock cost |

`check_product` also confirms the stock shortage on ticket 101, and `check_vendors` also shows the vendor block on ticket 103.

**Board**

| Tool | What it does |
|---|---|
| `list_tickets()` | Lists every ticket and its status for the dashboard |
| `list_open_tickets()` | Lists tickets that aren't resolved |
| `get_ticket(ticket_id)` | Returns a ticket with its payment requests and drafts |
| `check_cash()` | Shows cash, unpaid requests, and what would be left |
| `save_draft(ticket_id, recipient, body)` | Saves a customer message on the board and never sends it |
| `update_ticket(ticket_id, status, note)` | Sets a ticket's status and adds a note |

**Payments**

| Tool | What it does |
|---|---|
| `request_invoice_payment(ticket_id, invoice_id, reason)` | Prepares an open invoice for human approval |
| `request_rent_payment(ticket_id, lease_id, reason)` | Prepares a lease's next rent for human approval |
| `request_purchase_order(ticket_id, vendor_id, sku, size, qty, reason)` | Prepares a restock for human approval |
| `decide_request(request_id, approved, approver, approval_code)` | Records a person's approve or reject decision |
| `pay(request_id, account)` | Pays a request a person approved, then updates the related tables |

**Human only:** no agent is given `decide_request` or `pay`. A person uses them through `backend/approvals.py`. `decide_request` needs `APPROVAL_CODE` from `.env`, so it refuses every call when that isn't set, including calls through `.mcp.json`.

## Rules the tools enforce

- `request_invoice_payment`, `request_rent_payment`, and `request_purchase_order` refuse anything that exceeds the cash left after unpaid requests.
- `request_rent_payment` needs the lease linked to the ticket.
- `request_purchase_order` must match the ticket's product and stay within its shortfall.
- `pay` refuses a request with no human approval, a payment the account can't cover, a purchase order for a vendor with an open invoice, and a request that no longer matches its invoice or lease.
- `save_draft` only saves drafts for the ticket's requester, and it refuses internal details and discount offers.
- `update_ticket` won't resolve a ticket that has an unpaid request.

## Setup

Follow the setup steps in the main `README.md`. They create the virtual environment and the working database.

## Run

From the project root, with the virtual environment active:

```bash
python mcp_server/server.py
```

To serve over HTTP at `http://127.0.0.1:8001/mcp` instead:

```bash
python mcp_server/server.py --http
```
