"""Shared datatypes for the Campus Customs agent team."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_on_approval", "resolved"]


class PaymentDecision(BaseModel):
    """The person clicking approve or reject on the dashboard."""

    approver: str = Field(min_length=1, max_length=100)


class TicketOutcome(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    status: TicketStatus
    summary: str = Field(description="What the team found and decided, using only tool results.")
    human_actions: list[str] = Field(
        default_factory=list,
        description="Decisions or approvals a person still has to make.",
    )


class Delegation(BaseModel):
    """One request from an agent to a teammate."""

    from_agent: AgentName
    to_agent: AgentName
    question: str
    reply: str = ""
    status: Literal["running", "done", "error"] = "running"


class ToolCall(BaseModel):
    """One tool an agent called."""

    agent: AgentName
    tool: str
    args: dict | str | None = None


class UsageSummary(BaseModel):
    requests: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class TicketRun(BaseModel):
    """Everything that happened while the team worked one ticket."""

    ticket_id: int
    ok: bool
    outcome: TicketOutcome | None = None
    error: str | None = None
    models_used: list[str] = Field(default_factory=list)
    delegations: list[Delegation] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: UsageSummary = Field(default_factory=UsageSummary)
