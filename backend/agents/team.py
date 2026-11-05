"""What every agent shares: audited MCP tools, delegation, and the agent loop.

Any agent can ask any other agent for help through ask_teammate. Shop facts only
come from the MCP server. Every tool call passes through guarded_tool_call, and
every loop step goes to the audit trail as it happens.
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from fastmcp import Client
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset

from agents.config import ROOT, build_model
from audit import AuditError, audit
from guardrails import (
    MAX_CHAIN,
    MAX_DELEGATIONS,
    MAX_PER_TEAMMATE,
    MAX_QUESTION_CHARS,
    ROLE_TOOLS,
    SOFT_REQUEST_LIMIT,
    USAGE_LIMITS,
    check_tool_call,
)
from models import AgentName, Delegation, ToolCall

sys.path.insert(0, str(ROOT / "mcp_server"))
from server import mcp as campus_mcp  # noqa: E402

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
TEAMMATE_TIMEOUT = 90.0  # seconds for one teammate's whole run

TEAM: dict[str, Agent] = {}


@dataclass
class TicketState:
    """Shared record of one ticket's run."""

    run_id: str
    delegations: list[Delegation] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    models_used: set[str] = field(default_factory=set)
    call_counts: dict = field(default_factory=dict)
    blocks: int = 0


@dataclass
class TeamDeps:
    agent: AgentName
    ticket_id: int
    chain: tuple[str, ...]
    state: TicketState


def log(deps: TeamDeps, event: str, **details) -> None:
    audit(event, run_id=deps.state.run_id, ticket_id=deps.ticket_id, actor=deps.agent, **details)


async def mcp_call(tool: str, args: dict | None = None):
    """Call an MCP tool from outside an agent, such as for a safety check."""
    async with Client(campus_mcp) as client:
        data = (await client.call_tool(tool, args or {})).structured_content
    return data.get("result", data)


async def guarded_tool_call(ctx: RunContext[TeamDeps], call_tool, name: str, args: dict):
    """Check, audit, and run one MCP tool call."""
    deps = ctx.deps
    reason = check_tool_call(deps.agent, deps.ticket_id, name, args, deps.state.call_counts)
    if reason:
        deps.state.blocks += 1
        log(deps, "guardrail_block", tool=name, args=args, reason=reason)
        return f"BLOCKED: {reason}"
    log(deps, "tool_call", tool=name, args=args)
    started = time.monotonic()
    try:
        result = await call_tool(name, args)
    except AuditError:
        raise
    except Exception as exc:
        log(deps, "tool_error", tool=name, error=str(exc), seconds=round(time.monotonic() - started, 3))
        raise
    log(deps, "tool_result", tool=name, result=result, seconds=round(time.monotonic() - started, 3))
    return result


mcp_tools = MCPToolset(campus_mcp, max_retries=2, process_tool_call=guarded_tool_call)


def log_step(deps: TeamDeps, step: int, node) -> None:
    """Write one agent-loop step to the audit trail."""
    details = {"step": step, "node": type(node).__name__}
    if Agent.is_call_tools_node(node):
        response = node.model_response
        if response.model_name:
            deps.state.models_used.add(response.model_name)
        details.update(
            model=response.model_name,
            finish_reason=response.finish_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            text=" ".join(p.content for p in response.parts if p.part_kind == "text"),
            tool_calls=[
                {"tool": p.tool_name, "args": p.args} for p in response.parts if p.part_kind == "tool-call"
            ],
        )
        for part in response.parts:
            if part.part_kind == "tool-call" and part.tool_name != "ask_teammate":
                deps.state.tool_calls.append(ToolCall(agent=deps.agent, tool=part.tool_name, args=part.args))
    log(deps, "agent_step", **details)


async def run_agent(name: AgentName, prompt: str, deps: TeamDeps, usage):
    """Run one agent's loop one step at a time, auditing every step."""
    log(deps, "agent_start", chain=list(deps.chain), prompt=prompt)
    step = 0
    try:
        async with TEAM[name].iter(prompt, deps=deps, usage=usage, usage_limits=USAGE_LIMITS) as run:
            async for node in run:
                step += 1
                log_step(deps, step, node)
    except Exception as exc:
        log(deps, "agent_error", steps=step, error=f"{type(exc).__name__}: {exc}")
        raise
    log(deps, "agent_end", steps=step, output=str(run.result.output))
    return run.result


async def ask_teammate(ctx: RunContext[TeamDeps], teammate: AgentName, question: str) -> str:
    """Ask another agent on the team for help and get their reply.

    Args:
        teammate: boss, inventory, accounting, facilities, or customer_service.
        question: A focused request with the facts they need from your tool results.
    """
    deps = ctx.deps
    asked = sum(d.to_agent == teammate for d in deps.state.delegations)
    reason = None
    if teammate in deps.chain:
        reason = f"{teammate} is already working on this request. Use what you have and answer."
    elif len(deps.chain) >= MAX_CHAIN:
        reason = "This request has been passed along too many times. Answer with what you have."
    elif len(question) > MAX_QUESTION_CHARS:
        reason = "That request is too long. Send a shorter one."
    elif (
        len(deps.state.delegations) >= MAX_DELEGATIONS
        or asked >= MAX_PER_TEAMMATE
        or ctx.usage.requests >= SOFT_REQUEST_LIMIT
    ):
        reason = "No more help is available for this ticket. Answer now with what you have."
    if reason:
        deps.state.blocks += 1
        log(deps, "guardrail_block", tool="ask_teammate", teammate=teammate, reason=reason)
        return reason

    # Teammates see earlier replies, so nobody repeats work that is already done.
    notes = "\n\n".join(
        f"{d.to_agent} said: {d.reply}" for d in deps.state.delegations if d.status == "done"
    )
    delegation = Delegation(from_agent=deps.agent, to_agent=teammate, question=question)
    deps.state.delegations.append(delegation)
    log(deps, "delegation", to_agent=teammate, question=question)
    teammate_deps = TeamDeps(teammate, deps.ticket_id, (*deps.chain, teammate), deps.state)
    prompt = f"Ticket {deps.ticket_id}. Request from {deps.agent}: {question}"
    if notes:
        prompt += f"\n\nTeam notes so far:\n{notes}"
    try:
        result = await asyncio.wait_for(
            run_agent(teammate, prompt, teammate_deps, ctx.usage), timeout=TEAMMATE_TIMEOUT
        )
    except (UsageLimitExceeded, AuditError):
        delegation.status = "error"
        raise
    except Exception as exc:  # the caller gets a clear note and can carry on
        delegation.status = "error"
        delegation.reply = f"{teammate} failed: {type(exc).__name__}"
        log(deps, "delegation_failed", to_agent=teammate, error=delegation.reply)
        return delegation.reply
    delegation.status = "done"
    delegation.reply = str(result.output)
    log(deps, "delegation_reply", from_agent=teammate, reply=delegation.reply)
    return delegation.reply


def build_agent(name: AgentName, output_type: type = str) -> Agent:
    """Create an agent with its prompt, its allowed MCP tools, and ask_teammate."""
    tools = ROLE_TOOLS[name]
    agent = Agent(
        build_model(),
        name=name,
        deps_type=TeamDeps,
        output_type=output_type,
        instructions=(PROMPTS / f"{name}.md").read_text(encoding="utf-8"),
        toolsets=[mcp_tools.filtered(lambda ctx, tool: tool.name in tools)],
    )
    agent.tool(ask_teammate)
    TEAM[name] = agent
    return agent
