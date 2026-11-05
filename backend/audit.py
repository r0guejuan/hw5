"""Append-only audit trail for everything the agents and approvers do.

output/audit_trail.json stays a valid JSON array, one entry per line. Each write
replaces only the closing bracket, so earlier entries are never rewritten. Each
entry stores the hash of the one before it, so an edit or deletion breaks the
chain, and `python audit.py` reports where.

If the trail can't be written, audit() raises and the work stops, because an
unaudited agent should not keep running.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = Path(os.getenv("AUDIT_TRAIL_PATH") or ROOT / "output" / "audit_trail.json")
TAIL = b"\n]\n"
MAX_TEXT = 4000
SENSITIVE_KEY = re.compile(r"key|token|secret|password|authorization|approval_code", re.IGNORECASE)
SENSITIVE_TEXT = [
    (re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_-]{8,}"), "[REDACTED_KEY]"),
    (re.compile(r"Bearer\s+\S+", re.IGNORECASE), "[REDACTED_KEY]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[REDACTED_NUMBER]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[REDACTED_EMAIL]"),
]
# Token counts are safe numbers, even though their names contain "token".
SAFE_KEYS = {"input_tokens", "output_tokens", "total_tokens", "tokens_used_today", "token_limit"}
_lock = threading.Lock()


class AuditError(RuntimeError):
    """The trail is unwritable or damaged."""


def redact(value, key: str = ""):
    """Remove secrets and shorten long text before anything is logged."""
    if key and key not in SAFE_KEYS and SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    text = str(value)
    for secret_name in ("PORTKEY_API_KEY", "APPROVAL_CODE"):
        secret = os.getenv(secret_name)
        if secret:
            text = text.replace(secret, "[REDACTED]")
    for pattern, replacement in SENSITIVE_TEXT:
        text = pattern.sub(replacement, text)
    return text if len(text) <= MAX_TEXT else f"{text[:MAX_TEXT]}... [truncated]"


def entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def audit(event: str, *, run_id: str | None = None, ticket_id: int | None = None,
          actor: str = "system", **details) -> None:
    """Add one entry to the trail."""
    with _lock:
        try:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(AUDIT_PATH, os.O_RDWR | os.O_CREAT, 0o640)
            with os.fdopen(fd, "r+b") as file:
                fcntl.flock(file, fcntl.LOCK_EX)
                data = file.read()
                if data and not data.endswith(TAIL):
                    raise AuditError("The audit trail does not end the way it should.")
                last = json.loads(data[: -len(TAIL)].rsplit(b"\n", 1)[-1]) if data else None
                entry = {
                    "seq": last["seq"] + 1 if last else 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    "event": event,
                    "run_id": run_id,
                    "ticket_id": ticket_id,
                    "actor": actor,
                    "details": redact(details),
                    "prev_hash": last["hash"] if last else None,
                }
                entry["hash"] = entry_hash(entry)
                line = json.dumps(entry, ensure_ascii=False).encode()
                if data:
                    file.seek(len(data) - len(TAIL))
                    file.write(b",\n" + line + TAIL)
                else:
                    file.write(b"[\n" + line + TAIL)
                file.flush()
                os.fsync(file.fileno())
        except AuditError:
            raise
        except (OSError, ValueError, KeyError) as exc:
            raise AuditError(f"Could not write the audit trail: {type(exc).__name__}") from exc


def read_trail() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def verify_trail() -> tuple[bool, str]:
    """Check the sequence and hash chain of every entry."""
    previous = None
    entries = read_trail()
    for position, entry in enumerate(entries, start=1):
        if entry["seq"] != position:
            return False, f"Entry {position} has the wrong sequence number."
        if entry["prev_hash"] != (previous["hash"] if previous else None):
            return False, f"Entry {position} does not link to the entry before it."
        if entry["hash"] != entry_hash(entry):
            return False, f"Entry {position} was changed after it was written."
        previous = entry
    return True, f"{len(entries)} entries verified."


def tokens_used_today() -> int:
    """Add up the tokens from today's finished tickets (UTC)."""
    today = datetime.now(timezone.utc).date().isoformat()
    return sum(
        entry["details"].get("usage", {}).get("input_tokens", 0)
        + entry["details"].get("usage", {}).get("output_tokens", 0)
        for entry in read_trail()
        if entry["event"] == "ticket_end" and entry["timestamp"].startswith(today)
    )


if __name__ == "__main__":
    passed, message = verify_trail()
    print(message)
    sys.exit(0 if passed else 1)
