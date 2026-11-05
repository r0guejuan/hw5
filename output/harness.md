# Campus Customs Harness

Source data: `data/campus_customs.db` (original, never changed). All work happens in the copy, `data/campus_customs_new.db`.

## Database tables

### desk

Sets the shop's "today", which every agent uses to decide what is overdue or coming due.

| Field | Type | Key or link |
|---|---|---|
| `date_today` | TEXT, required | |
| `notes` | TEXT | |

### tickets

The work queue: the Boss reads each ticket and routes it to the right agents.

| Field | Type | Key or link |
|---|---|---|
| `id` | INTEGER | Primary key |
| `type` | TEXT, required | |
| `requester` | TEXT, required | |
| `subject` | TEXT, required | |
| `sku` | TEXT | Matches `inventory.sku` and `pricing.sku` (not enforced) |
| `size` | TEXT | Matches `inventory.size` (not enforced) |
| `qty` | INTEGER | |
| `lease_id` | INTEGER | Foreign key to `leases.id` |
| `invoice_id` | INTEGER | Foreign key to `invoices.id` |
| `status` | TEXT, required | |
| `notes` | TEXT | |
| `created_at` | TEXT, required | |

### inventory

Lets the Inventory agent check stock by SKU and size and spot shortfalls.

| Field | Type | Key or link |
|---|---|---|
| `sku` | TEXT, required | Primary key with `size` |
| `name` | TEXT, required | |
| `size` | TEXT, required | Primary key with `sku` |
| `qty` | INTEGER, required | |
| `location` | TEXT, required | |

### pricing

Gives Accounting the unit cost and list price needed to check margins and discount requests.

| Field | Type | Key or link |
|---|---|---|
| `sku` | TEXT | Primary key; matches `inventory.sku` (not enforced) |
| `unit_cost` | REAL, required | |
| `list_price` | REAL, required | |

### vendors

Tells Inventory who can restock a product and how long delivery takes.

| Field | Type | Key or link |
|---|---|---|
| `id` | INTEGER | Primary key |
| `name` | TEXT, required | |
| `specialty` | TEXT, required | |
| `lead_days` | INTEGER, required | |

### leases

Gives Facilities the rent amount, landlord, and next due date for the shop space.

| Field | Type | Key or link |
|---|---|---|
| `id` | INTEGER | Primary key |
| `space_name` | TEXT, required | |
| `landlord` | TEXT, required | |
| `monthly_rent` | REAL, required | |
| `next_due` | TEXT, required | |
| `notes` | TEXT | |

### cash_accounts

Shows Accounting how much cash is available, so the pay tool can refuse anything that would overdraw it.

| Field | Type | Key or link |
|---|---|---|
| `name` | TEXT | Primary key |
| `balance` | REAL, required | |
| `date` | TEXT, required | |

### payments

Records every approved payment, including who approved it, so agents can prove what was paid.

| Field | Type | Key or link |
|---|---|---|
| `id` | INTEGER | Primary key |
| `kind` | TEXT, required | Says what `ref_id` points to |
| `ref_id` | INTEGER | Paid record's id, such as an invoice or lease (not enforced) |
| `amount` | REAL, required | |
| `account` | TEXT, required | Matches `cash_accounts.name` (not enforced) |
| `paid_at` | TEXT, required | |
| `approved_by` | TEXT, required | |

### invoices

Shows Accounting and Inventory which bills are unpaid, because an open invoice stops that vendor from shipping.

| Field | Type | Key or link |
|---|---|---|
| `id` | INTEGER | Primary key |
| `vendor_id` | INTEGER, required | Foreign key to `vendors.id` |
| `amount` | REAL, required | |
| `due_date` | TEXT, required | |
| `status` | TEXT, required | |
| `description` | TEXT | |

## Open ticket links

| Ticket | Request | Direct links | Follow-on links |
|---|---|---|---|
| 101 `customer_order` | 1 `CC-TEE-WHITE`, size S, for Tauhid Zaman | `inventory` and `pricing` by SKU and size; `invoices` 501 by `invoice_id` | Invoice 501 leads to vendor 1, Bulldog Print Co |
| 102 `rent_notice` | Rent due, from Elm City Properties | `leases` 1 by `lease_id` | `cash_accounts` to pay it; `payments` to record it |
| 103 `price_override` | 20 `CC-HOOD-NAVY`, size M, at a bulk discount, for Yale AI Club | `inventory` and `pricing` by SKU and size | No vendor link is stored; `vendors.specialty` points to Bulldog Print Co, which also ties it to invoice 501 |

## MCP server tools

The `campus-customs` server in `mcp_server/server.py` works on `data/campus_customs_new.db`. These first three tools are read-only and unlock the tickets. The other eleven are listed under MCP tools added for the team.

### `check_vendors()`

- **Reads:** `vendors`, `invoices`, `desk`
- **Unlocks:** Ticket 101
- **Why it fits:** Size S of `CC-TEE-WHITE` has 0 in stock, and this tool shows that open invoice 501 ($840, 3 days overdue) stops Bulldog Print Co from shipping a restock until it is paid.

### `check_rent(lease_id)`

- **Reads:** `leases`, `cash_accounts`, `desk`
- **Unlocks:** Ticket 102
- **Why it fits:** Ticket 102 is an emailed rent notice with no amount, so this tool uses its `lease_id` to confirm the $2,400 owed to Elm City Properties, the 2026-09-02 due date, and whether checking can cover it before anyone asks for payment approval.

### `check_product(sku, size, qty)`

- **Reads:** `inventory`, `pricing`
- **Unlocks:** Ticket 103
- **Why it fits:** Yale AI Club wants 20 size M `CC-HOOD-NAVY` at a discount, and this tool shows the 8 on hand, the 12 short, the $264 restock cost, and the $36 unit margin the Boss needs to judge that request.

## Agent team

Every agent is a PydanticAI agent using only `gpt-6-luna` through Portkey. `backend/agents/config.py` stops the app if `OPENAI_MODEL` names anything else. Shop facts reach agents only through the MCP server, and the backend has no database code of its own.

| Agent | Job | Prompt | MCP tools |
|---|---|---|---|
| Boss | Reads each ticket, decides who works on it, and makes the final call | `boss.md` | `get_ticket`, `list_open_tickets`, `update_ticket` |
| Inventory | Checks stock by SKU and size, spots shortfalls, and finds which vendor can restock | `inventory.md` | `get_ticket`, `check_product`, `check_vendors` |
| Accounting | Watches cash and invoices, checks margins, and prepares payments and purchase orders for human approval | `accounting.md` | `get_ticket`, `check_cash`, `check_product`, `check_rent`, `check_vendors`, `request_invoice_payment`, `request_rent_payment`, `request_purchase_order` |
| Facilities | Handles the shop space, including leases and rent | `facilities.md` | `get_ticket`, `check_rent` |
| Customer Service | Drafts customer messages that stay on the board | `customer_service.md` | `get_ticket`, `save_draft` |

**Full connectivity:** every agent has `ask_teammate`, so any agent can ask any other agent for help. Teammates also see earlier replies on the ticket, so they don't repeat work.

**Agent loop:** `run_ticket` in `backend/agents/boss.py` gives the Boss one ticket. The Boss reads it, delegates, records the decision with `update_ticket`, and returns a `TicketOutcome`. `run_agent` in `backend/agents/team.py` steps through each agent's loop and audits every step.

## MCP tools added for the team

| Tool | Used by | Reads | Writes | Why the team needs it |
|---|---|---|---|---|
| `list_tickets()` | Dashboard only | `tickets` | Nothing | Returns every ticket and its status, including resolved tickets |
| `list_open_tickets()` | Boss | `tickets` | Nothing | Shows which tickets compete for the same cash |
| `get_ticket(ticket_id)` | All agents | `tickets`, `payment_requests`, `drafts` | Nothing | Gives each agent the ticket and its current board state |
| `check_cash()` | Accounting | `cash_accounts`, `payment_requests`, `desk` | Nothing | Shows what is left after unpaid requests |
| `request_invoice_payment(ticket_id, invoice_id, reason)` | Accounting | `invoices`, `tickets`, `payment_requests`, `cash_accounts` | `payment_requests` | Prepares an open invoice for approval, using the amount in the database |
| `request_rent_payment(ticket_id, lease_id, reason)` | Accounting | `leases`, `tickets`, `payment_requests`, `cash_accounts` | `payment_requests` | Prepares the rent on the ticket's linked lease for approval |
| `request_purchase_order(ticket_id, vendor_id, sku, size, qty, reason)` | Accounting | `vendors`, `inventory`, `pricing`, `tickets`, `invoices`, `payment_requests`, `cash_accounts` | `payment_requests` | Prepares a restock for approval, up to the ticket's shortfall |
| `save_draft(ticket_id, recipient, body)` | Customer Service | `tickets`, `vendors`, `desk` | `drafts` | Keeps customer messages on the board and blocks unsafe wording |
| `update_ticket(ticket_id, status, note)` | Boss | `tickets`, `payment_requests` | `tickets` | Records the Boss's call and refuses to resolve a ticket with an unpaid request |
| `decide_request(request_id, approved, approver, approval_code)` | People only | `payment_requests`, `desk` | `payment_requests` | Records a person's approve or reject decision |
| `pay(request_id, account)` | People only | `payment_requests`, `cash_accounts`, `invoices`, `leases`, `vendors`, `desk` | `cash_accounts`, `payments`, `payment_requests`, and `invoices` or `leases` | Pays an approved request and updates the related tables |

`check_vendors`, `check_rent`, and `check_product` are documented under MCP server tools.

## Backend routes

- `GET /api/tickets`: returns every ticket and its status.
- `GET /api/tickets/{ticket_id}`: returns one ticket with its payment requests and drafts.
- `POST /api/tickets/{ticket_id}/run`: runs the agent team on one ticket.
- `GET /api/events`: returns agent messages and tool calls since the last reset, filtered by `limit`, `ticket_id`, or `after_seq`.
- `GET /api/oversight`: returns token use, audit trail health, guardrail blocks, and payments since the last reset.
- `POST /api/tickets/{ticket_id}/resolve`: lets a person close a ticket with no unpaid requests.
- `POST /api/payments/{request_id}/approve`: records a person's approval, pays the request, and resolves the ticket when nothing is left to pay.
- `POST /api/payments/{request_id}/reject`: records a person's rejection without paying.
- `GET /api/cash`: returns the checking balance from `cash_accounts` and any unpaid requests.
- `POST /api/reset`: copies the original database over the working copy for a fresh run.

## Dashboard

The React, Vite, and TypeScript dashboard in `frontend/` runs at `http://localhost:5173` and calls the backend at `http://localhost:8000`. The backend's CORS rules allow only that Vite origin.

- **Tickets:** lists all three tickets with their status, and starts the agent team on the selected ticket.
- **Live view:** checks for new events every 1.5 seconds, showing each agent's state and an activity feed.
- **Summary:** shows the Boss's outcome, what's left for a person, and any customer draft.
- **Approvals:** shows pending requests. Approving or rejecting needs a person's name.
- **Balance:** shows checking and updates as payments are made.
- **Stages:** counts tickets in each stage, and clicking a count filters the list. Unresolved tickets are red and resolved tickets are green.
- **Agents:** each agent is an original Handsome Dan bulldog drawing with its own bow tie color. A working agent glows and says "Boola boola!"
- **Delegation map:** draws lines between agents as they ask each other for help, with moving lines for open requests.
- **Token meter:** shows tokens and requests for the current run against the per-ticket limits, plus finished-ticket tokens today against the daily limit.
- **Guardrails and audit:** shows blocked or refused actions and the result of the audit trail's tamper check.
- **Cash flow:** charts checking after each payment, with a dotted line to the balance after pending requests.
- **Celebration:** a resolved ticket sets off confetti and a cheer from all five agents.
- **Customize:** the Customize drawer sets the theme (system, light, or dark), the tickets column side, and each panel's order, width, and visibility. Settings save in the browser. Summary and Approvals can move but can't be hidden, so a person can always approve payments and close tickets.
- **Resolving:** a ticket resolves when the Boss finds nothing left to do, when its last unpaid request is paid, or when a person clicks Mark resolved.

## Shop rules

- `desk.date_today` is "today" for the shop, and it decides what is overdue.
- Vendor lead times come from the `vendors` table.
- A vendor won't ship new product while it has an open unpaid invoice.
- Every payment needs human approval, and a payment updates the related tables.
- The pay tool refuses a payment that would make a balance negative.
- Cash only goes out. Revenue isn't modeled, so no money comes in.
- Reset the working database to the original values before a full run. `POST /api/reset` or the board's Reset button does this.
- Nothing is emailed to customers or sent to vendors. Drafts stay on the board.
- Every agent uses only `gpt-6-luna` through Portkey with `PORTKEY_API_KEY`.
- Shop facts reach agents only through the MCP server.

## Human approval

- Agents can prepare payments but can't approve or pay them. `decide_request` and `pay` are on no agent's tool list, and `guardrails.py` blocks them for agents as well.
- `backend/approvals.py` is the human path, used by the dashboard's approve and reject routes. It sends a person's decision through `decide_request`, then calls `pay`.
- `decide_request` needs `APPROVAL_CODE` from `.env`, and the approver can't be an agent name.
- `pay` refuses a request with no human approval, a payment the account can't cover, a purchase order for a vendor with an open invoice, and a request that no longer matches its invoice or lease.

## Guardrails

Each rule below runs in code, so it still holds if an agent ignores its prompt.

| Risk | Guardrail | Where |
|---|---|---|
| An agent moves money | Agents have no payment tools, and each run proves cash didn't change | `guardrails.py`, `agents/boss.py` |
| A fake approval | Approval needs a code no agent is given, and an agent can't be the approver | `decide_request` |
| Overspending | Requests and payments are refused if they exceed available cash | `request_*`, `pay` |
| Paying twice | Duplicate requests are reused, and a paid request can't be paid again | `request_*`, `decide_request`, `pay` |
| Over-ordering | A purchase order must match the ticket's product and stay within its shortfall | `request_purchase_order` |
| Paying a blocked vendor | A purchase order can't be paid while that vendor has an open invoice | `pay` |
| Sharing internal details | Drafts can't mention invoices, vendors, costs, margins, or cash | `save_draft` |
| Promising a discount | Drafts can't offer a percentage or dollar discount | `save_draft` |
| Messaging the wrong person | Drafts can only go to the ticket's requester, and nothing is sent | `save_draft` |
| An agent going out of bounds | Each agent can only use its own tools, and only on its current ticket | `guardrails.py` |
| Prompt injection | Tickets that look like instructions are held for a person before any model call | `guardrails.py`, `agents/boss.py` |
| Agents needing to be stopped | `AGENTS_PAUSED=1` stops all new agent work | `guardrails.py` |
| Leaked secrets | Keys, approval codes, card numbers, and emails are redacted from the audit trail | `audit.py` |

## Token limits

| Limit | Value |
|---|---|
| Model | `gpt-6-luna` only, with reasoning off |
| Output per model reply | 800 tokens |
| Tokens per ticket, across the whole team | 40,000 |
| Model requests per ticket | 24 |
| Tool calls per ticket | 30 |
| Requests before delegation stops, so the Boss can finish | 16 |
| Tokens per day, counted from the audit trail in UTC | 250,000 |
| Delegations per ticket | 5 |
| Times one agent can be asked on a ticket | 2 |
| Agents in one chain of help | 3 |
| Identical calls by one agent on a ticket | 2 |
| Database writes per ticket | 6 |
| Time per teammate, and per ticket | 90 seconds, and 240 seconds |

## Audit trail

`backend/audit.py` appends to `output/audit_trail.json` as agents run. A reset of the database does not touch this file.

- **Append-only:** the file stays a valid JSON array. Each write replaces only the closing bracket, so earlier entries are never rewritten.
- **Tamper evidence:** each entry stores the hash of the entry before it. Run `python audit.py` from `backend/` to check the chain.
- **Stops on failure:** if an entry can't be written, the run stops.
- **Every entry has:** `seq`, `timestamp`, `event`, `run_id`, `ticket_id`, `actor`, `details`, `prev_hash`, and `hash`.
- **Scope:** this covers agent runs and `backend/approvals.py`. Calling MCP tools from another client, such as the vibe coder, is not audited.

| Event | What it records |
|---|---|
| `ticket_start`, `ticket_end` | Database, model, limits, outcome, models used, token usage, and guardrail blocks |
| `agent_start`, `agent_end`, `agent_error` | The agent, its chain, its prompt, and its output or error |
| `agent_step` | Each loop step: model, finish reason, tokens, text, and requested tool calls |
| `tool_call`, `tool_result`, `tool_error` | Each MCP call: arguments, result or refusal, and time taken |
| `delegation`, `delegation_reply`, `delegation_failed` | Who asked whom, the question, and the reply |
| `guardrail_block`, `prompt_injection_suspected` | What was stopped and why |
| `money_check`, `ALERT_money_moved_during_agent_run` | Cash before and after each run |
| `human_decision_attempt`, `human_decision`, `payment_made`, `payment_refused` | Who decided, what they decided, and the payment result |

## Board tables

The tools add these tables to the working copy on first use, so `data/campus_customs.db` stays untouched and a reset still works.

### payment_requests

Holds every prepared payment, so a person can approve or reject it.

| Field | Type | Key or link |
|---|---|---|
| `id` | INTEGER | Primary key |
| `ticket_id` | INTEGER, required | Foreign key to `tickets.id` |
| `kind` | TEXT, required | `invoice`, `rent`, or `purchase_order` |
| `ref_id` | INTEGER | Invoice or lease id |
| `vendor_id` | INTEGER | Foreign key to `vendors.id` |
| `sku` | TEXT | Purchase orders only |
| `size` | TEXT | Purchase orders only |
| `qty` | INTEGER | Purchase orders only |
| `amount` | REAL, required | Taken from the database |
| `reason` | TEXT, required | |
| `status` | TEXT, required | `pending`, `approved`, `rejected`, or `paid` |
| `decided_by` | TEXT | The person who decided |
| `decided_at` | TEXT | Shop date of the decision |

### drafts

Keeps customer messages on the board, because nothing is ever sent.

| Field | Type | Key or link |
|---|---|---|
| `id` | INTEGER | Primary key |
| `ticket_id` | INTEGER, required | Foreign key to `tickets.id` |
| `recipient` | TEXT, required | |
| `body` | TEXT, required | |
| `created_at` | TEXT, required | Shop date |
