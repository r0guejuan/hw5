# Campus Customs Multi-Agent Operations

A team of five AI agents works the shop's open tickets while a person watches and approves payments. It has three parts:

- `mcp_server/`: a FastMCP server, and the only way agents reach shop data
- `backend/`: a FastAPI backend with the PydanticAI agent team
- `frontend/`: a React, Vite, and TypeScript dashboard

Every agent uses only `gpt-6-luna` through Portkey. See `output/harness.md` for the tables, tools, agents, routes, and safety rules.

## Setup

You need Python 3.12 or newer, Node 20 or newer, and a Portkey API key. All commands start from the project root.

**1. Add the database.** The database files aren't in this repo. Unzip the assignment's `data.zip` so this file exists:

```text
data/campus_customs.db
```

**2. Install the Python packages.**

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

**3. Add your settings.**

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable | Value |
|---|---|
| `PORTKEY_API_KEY` | Your Portkey key |
| `PORTKEY_BASE_URL` | `https://api.portkey.ai/v1` |
| `OPENAI_MODEL` | `gpt-6-luna` |
| `APPROVAL_CODE` | Any long random text. Approvals are refused without it. |

**4. Install the dashboard.**

```bash
cd frontend && npm install
```

## Copy the original database

The app only works on `data/campus_customs_new.db`. `data/campus_customs.db` stays untouched. Copy the original over the working copy whenever you need a clean run:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

## Start the MCP server

The backend loads the MCP server by itself, so you don't need this to use the board. Run it on its own to connect another client or test the tools:

```bash
python mcp_server/server.py
```

The project's `.mcp.json` connects it to a vibe coder.

## Start the FastAPI backend

In a new terminal, with the virtual environment active:

```bash
cd backend && uvicorn main:app --reload --port 8000
```

## Start the React board

In another terminal:

```bash
cd frontend && npm run dev
```

Open http://localhost:5173.

## Run all three tickets

Reset the database before every full three-ticket run. Click **Reset board** on the dashboard, or run this while the backend is up:

```bash
curl -X POST http://localhost:8000/api/reset
```

Then, for each ticket:

1. Select the ticket and click **Start agent team**.
2. Enter your name and approve the payments. Approve an invoice before a restock from that vendor.
3. If the ticket has nothing to pay, click **Mark resolved**.

A reset doesn't touch `output/audit_trail.json`, which only appends. To check it for tampering:

```bash
cd backend && python audit.py
```
