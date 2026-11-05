# Problem 1: Vibe coder prompts

## Prompt 1

> We're back at it, and here is the situation (see attached photo). To start, create a file called AI_prompts.md. I will begin each prompt with the format Problem #:Title moving forward.
>
> Log this under Problem 1: Vibe coder prompts. Each problem should have number and title, at least one prompt typed in my own words, and one follow-up prompt if needed.
>
> *(attached: screenshot of the assignment's "Scenario", "Data", and "Rules of this shop" sections describing the Campus Customs Multi-Agent Operations project)*

# Problem 2: Study the Campus Customs database

## Prompt 1

> Problem 2: Study the Campus Customs database. Open the database data/campus_customs.db and analyze every table and their corresponding fields. Copy the original file to data/campus_customs_new.db which will be a working copy updated in later problems. Inspect the three open tickets and determine how they link to other tables.
>
> Create output/harness.md. For each table, add the fields and one short line about why that table will matter to the agents. We'll continue updating this harness later.

# Problem 3: Build the MCP server

## Prompt 1

> Problem 3: Build the MCP server. Create an MCP server in mcp_server/ using FastMCP that talks to data/campus_customs_new.db. All the agents in this assignment are going to need to use tools on this MCP server. Write three tools that they'll need for the tickets in the database and keep the names clean. NEVER invent any data and only use the information in the database.
>
> Add to output/harness.md and list the three tools on the MCP server. Every tool must include:
>
> * which table it reads
> * which ticket it helps unlock (101,102, or 103)
> * Once sentence on why that tool is the right one for the ticket.
>
> Don't use vague lines like "reads inventory" and be sure to tie the tool to the ticket.
>
> Add a mcp_server/README.md file that explains what the MCP server is for and which database file it uses, and the three tools it has.

# Problem 4: Add the MCP server to vibe coder and test each tool

## Prompt 1

> Problem 4: Add the MCP server to vibe coder and test each tool.
>
> Yo dawg, the professor wants me to connect the mcp server we just built to this project so we can test the tools. Save the connection JSON text in .mcp.json at the project root or however you save local mcp server lists

## Prompt 2

> Use check_vendors to show which vendors can ship and save the evidence in output/mcp_smoke.json

## Prompt 3

> Use check_rent for lease 1 to show the rent due and whether cash covers it, and add the evidence and this prompt to output/mcp_smoke.json

## Prompt 4

> Use check_product for 20 CC-HOOD-NAVY in size M to show the stock shortfall and restock cost, and add the evidence and this prompt to output/mcp_smoke.json

# Problem 5: Build the agent team and grow the MCP tools

## Prompt 1

> Problem 5: Build the agent team and grow the MCP tools.
>
> Homie we need to build out a team of lil agents for Campus Customs using PydanticAI. It's going to need a real boss agent, an inventory agent, an accounting agent, a facilities agent, and a customer service agent. They're going to need full connectivity to work with each other so include prompts, models, and agent loops.
>
> Put those agent prompts in backend/prompts/ with one file per agent. Put datatypes in backend/models.py and the agent files under backend/. Use my PORTKEY_API_KEY from previous projects and ONLY use gpt-6-luna for every agent. The professor said we gotta keep costs down because it's coming out of his paycheck (so make sure to only use that model).

## Prompt 2

> The lil boss man is going to need to do boss stuff and read each ticket and decide which of his underlings is going to work on it, as well as make any final calls.
> That inventory homie is going to need to check the stock by SKU and size and be able to spot shortfalls, and figure out what vendors can restock.
> Accounting bean counter needs to watch the cash and invoices and check the margins so we aren't burning cash. It needs to prepare payments or purchase orders for human approval .
> The facilities bro needs to handle the shop space side like leases and rents and stuff
> Finally the customer service rep needs to draft messages for customers. Like a real team yo.
>
> The mcp server is going to need some tools for all those workers so that they can work on the open tickets. Shop facts are also going to need to come from the MCP server over data/campus_customs_new.db. Don't go making any second shop-tools layer that bypasses the MCP homie.
>
> All those agents need to be audited while they run because I don't trust them. Append each agent-loop step, as well as all the stuff a security person is going to want to see in output/audit_trail.json as they run (make sure it appends and doesn't overwrite). It's gotta be persistent and not overwritten because all these workers are sketchy.
>
> In output/harness.md document each agent and mcp tool. Including the ones added in this problem along with which table the tool uses.
>
> Build in some safety stuff and guardrails so that all these agents don't act up. It's gotta cover the stuff a real business would want when agents touch real customers and real $$ (it's all about those benjamins), so make sure theres some limits to keep token use on lock.
>
> Update mcp_server/README.md so the tool list matches all we got now.

# Problem 6: Plan the three tickets

## Prompt 1

> Problem 6: Plan the three tickets. Alright I gotta do some analysis of the tickets and figure out the flow I expect each to take. Build me a dashboard thing in output/desk_tickets.html that's like a page I can double-click with one tab per ticket (101, 102, 103). Add two empty tabs called "cash" and "reflection" that we're going to need for later problems. Leave them blank for now or maybe a "coming later" note.
>
> On each tab I'm going to fill out in my own words what I expected the flow to be like, and then an "Actual" section will be filled in after the agents run.

# Problem 7: Backend routes

## Prompt 1

> Problem 7: Backend routes.
>
> Cool cool cool. We're going to be building a React frontend dashboard in a future problem so the backend needs to be able to call it. but the backend in backend/main.py. It's going to need to do some things like return the three tickets and their status (open, resolved, etc.), take a ticket id and run the agent team on that ticket, return recent agent events (what each agent said and which tools they used so the board can refresh).
> It's also going to need to approve a paymnt or purchase after a human clicks approve (agents only prepare the pay) and then return the current checking balance from cash_accounts, and reset the dashboard to the original value when it needs a fresh run.
>
> Then start the backend server with this command so that front end can reach it:
> uvicorn main:app --reload --port 8000
>
> In output/harness.md list each route in one line (url/what it does)

# Problem 8: Agent dashboard

## Prompt 1

> Problem 8: Agent dashboard.
>
> So I need a frontend now that is built with Reac, Vite, and Typescript and put it in frontend/. The dashboard has got to look real clean and professional. Give it a modern UI with Yale blue accents. It's got to do a bunch of stuff like:
>
> * list all three tickets
> * let the user pick one ticket and start the agent team on it
> * Show each agent and what they are saying/doing while the ticket runs
> * Mark a ticket resolved when the run finishes
> * Show a short summary of what agent did on the ticket
> * Let a human approve a pay or purchase when asked
> * Show the checking balance (and update as money flows)
>
> The front end should talk to the backend at http://localhost:8000. On the backend allow the vite page origin so the browser can call those routes.
>
> Start the board.

## Prompt 2

> The dashboard is kinda lame. It needs some pictures. Replace the agents with a bunch of Handsome Dans, but give each one a different color bow tie

# Problem 9: Resolve the tickets

## Prompt 1

> Problem 9: Resolve the tickets. Homie now we gotta test the agents on a full run so reset data/campus_customs_new.db so I can start with a clean slate. I'm going to run through all three tickets until each is resolved. Once I run them all, go into my output/desk_tickets.html and fill out the Actual section with which agents worked, what they delegated, and which tools they used. Don't overwrite my expected section.
>
> In the cash tab of the same output/desk_tickets.html itemize the money. Starting checking balance (after the reset)
>
> * For each ticket, how cash changed when that ticket resolved and why (which pay/purchase, dollar amount)
> * Ending checking balance. It must match cash_accounts in the working database.
>
> save output/resolved_tickets.json and include the following for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
> Save output/resolved_board.html - which should be a page I can double click with a screenshot of the react board for each resolved ticket.
>
> Append the real runs to output/audit_trail.json. Complete the output/harness.md so it covers tables, mcp tools, the five agents, api routes, the dashboard, and all the safety rules.

## Prompt 2

> Actually since this is getting loaded onto a public github later (screenshots included) I don't want to use my real name.

*Choices I made:* use the approver name "Obi Juan", and redact the audit trail by replacing the name, recomputing its hashes, and adding a logged redaction entry.

# Problem 10: Reflection

## Prompt 1

> Problem 10: Reflection. Open output/desk_tickets.html and fill the reflection tab. I'm going to answer this in my own vibe, so just log what I write after this:
>
> I would say that the agents performed well on each ticket. They appropriately identified all issues, escalated, and didn't do anything without approval. The Guardrails and audit trail pane I added to the dashboard made it easy to verify that nothing dangerous was performed, and also what each agent refused.
>
> There were a couple surprises in the Actual vs Expected plan I wrote. I expected the agents to communicate more with each other, but instead the boss agent delegated individual tasks to each agent, and there wasn't much inter-agent communication.
>
> If this was one agent vs a team, it could have been simpler because the single agent would have just made each call to the individual tools vs. tasking an agent to do it.
>
> Three new problems the Campus Customs team might face that the agent team could solve:
>
> * Automatic restocking recommendations when inventory is low or gone
> * Customers exchanging merchandise for a different size
> * Refund requests (should default to human approval)
>
> Three new problems the team could not solve:
>
> * Customers merchandise returns (would need to add new tools such as restocking)
> * Fake/scam requests ( would need to add a risk agent with tools such as verify_sender, or check_bank_change, or flag_suspicious_requests).
> * Discount requests (this could be solved with a pricing agent that dynamically prices based on specific margin rules)

# Problem 11: Submit to Github

## Prompt 1

> Problem 11: Submit to Github. Push my code to a public GitHub repo so that my graders can clone it. Make sure everything is safe to push (like don't dox me, expose my secrets, include my hostname, etc.) to the github repo, and do not include the database files under data/.
>
> The layout should look like this (screenshot).
>
> README should explain: copy original database to the working copy when you need a clean run, start MCP server, start FastAPI backend, start react board, reset the database before a full three-ticket run.
>
> *(attached: screenshot of the assignment's expected file tree for hw5/)*
