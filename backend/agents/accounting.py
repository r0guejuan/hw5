"""Accounting agent: cash, invoices, margins, and payments prepared for approval.

It has no pay tool. Only a person can release money, through backend/approvals.py.
"""

from agents.team import build_agent

accounting_agent = build_agent("accounting")
