"""Run the agent team from the terminal.

From the backend folder:
  python run_team.py 101        work one ticket
  python run_team.py            work every open ticket, in order
"""

from __future__ import annotations

import asyncio
import json
import sys

from agents.boss import run_ticket
from agents.team import mcp_call


async def main() -> None:
    ticket_ids = [int(arg) for arg in sys.argv[1:]]
    if not ticket_ids:
        ticket_ids = [ticket["id"] for ticket in await mcp_call("list_open_tickets")]
    runs = [(await run_ticket(ticket_id)).model_dump() for ticket_id in ticket_ids]
    print(json.dumps(runs, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
