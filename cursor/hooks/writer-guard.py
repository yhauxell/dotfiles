#!/usr/bin/env python3
"""
afterFileEdit hook: enforces the single-writer invariants from the agent
constitution by detecting unauthorized writes to protected paths and
emitting a strong follow-up message demanding rollback. Also appends every
violation to ~/.cursor/audit/writer-violations.jsonl for later review.

Protected paths and their sole authorized writer (`name:` in agent frontmatter):

    .cursor/specs/**         -> frontend-architect
    .cursor/pipeline/**      -> pipeline-orchestrator
    docs/test-plans/**       -> manual-test-planner

Why this is post-hoc, not pre-emptive:
- Cursor exposes `afterFileEdit`, not a pre-write hook. We cannot block a
  write; we can detect it immediately and demand the offender revert.
- `failClosed: true` in hooks.json is still set so that any error in this
  script surfaces clearly — silent rule violations are exactly what we want
  to prevent.

Event payload (best-effort parse — Cursor's exact schema may evolve):
- We look for the edited file path under any of: `file`, `path`, `file_path`,
  `target`, `arguments.path`, `event.path`.
- We look for the editing agent under any of: `agent`, `subagent`,
  `subagent_name`, `caller`, `actor.name`.
- If we cannot identify either, we record an "ambiguous" violation and pass.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple

# --- Protected-path policy --------------------------------------------------

# Each entry: (path-prefix, authorized agent name, human label)
POLICY = [
    (".cursor/specs/",      "frontend-architect",    "SPEC"),
    (".cursor/pipeline/",   "pipeline-orchestrator", "pipeline state"),
    ("docs/test-plans/",    "manual-test-planner",   "manual test plan"),
]

AUDIT_DIR = os.path.expanduser("~/.cursor/audit")
AUDIT_LOG = os.path.join(AUDIT_DIR, "writer-violations.jsonl")


# --- Payload parsing --------------------------------------------------------

def _first_str(payload: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[str]:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    args = payload.get("arguments")
    if isinstance(args, dict):
        for k in keys:
            v = args.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    actor = payload.get("actor")
    if isinstance(actor, dict):
        v = actor.get("name")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_path(payload: Dict[str, Any]) -> Optional[str]:
    return _first_str(payload, ("file", "path", "file_path", "target"))


def _extract_agent(payload: Dict[str, Any]) -> Optional[str]:
    return _first_str(payload, ("agent", "subagent", "subagent_name", "caller"))


# --- Policy evaluation ------------------------------------------------------

def _normalize_repo_relative(file_path: str) -> str:
    # Strip leading "./" and any absolute repo prefix; return as repo-relative.
    p = file_path
    if p.startswith("./"):
        p = p[2:]
    # Best-effort: trim everything up to the first occurrence of a protected
    # path segment so absolute paths from different machines still match.
    for prefix, _, _ in POLICY:
        idx = p.find(prefix)
        if idx >= 0:
            return p[idx:]
    return p


def _evaluate(file_path: str, agent: Optional[str]) -> Optional[Tuple[str, str, str]]:
    """Return (label, authorized_agent, matched_prefix) if violation, else None."""
    norm = _normalize_repo_relative(file_path)
    for prefix, owner, label in POLICY:
        if norm.startswith(prefix):
            if agent == owner:
                return None  # authorized writer
            return label, owner, prefix
    return None


# --- Audit log --------------------------------------------------------------

def _audit(record: Dict[str, Any]) -> None:
    try:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Never let audit failure break the hook.
        pass


# --- Main -------------------------------------------------------------------

def _allow() -> int:
    sys.stdout.write(json.dumps({"permission": "allow"}))
    return 0


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return _allow()

    try:
        payload = json.loads(raw)
    except Exception:
        return _allow()
    if not isinstance(payload, dict):
        return _allow()

    file_path = _extract_path(payload)
    if not file_path:
        return _allow()

    agent = _extract_agent(payload)

    violation = _evaluate(file_path, agent)
    if violation is None:
        return _allow()

    label, owner, prefix = violation
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    _audit({
        "ts": now,
        "file": file_path,
        "matched_prefix": prefix,
        "label": label,
        "authorized_agent": owner,
        "offending_agent": agent or "<unknown>",
    })

    if agent is None:
        # Ambiguous: log but do not bother the user with a confident demand.
        return _allow()

    followup = (
        f"VIOLATION of single-writer rule (per ~/.cursor/rules/agent-constitution.mdc §1):\n"
        f"- file: {file_path}\n"
        f"- this path is owned by `{owner}` (the {label} writer)\n"
        f"- editor: `{agent}` is not authorized to write here\n\n"
        f"Required action NOW, before any other work:\n"
        f"1. Revert the change to {file_path} (e.g. `git checkout -- {file_path}` if tracked, or delete if newly created).\n"
        f"2. If this write was actually necessary, stop and hand off to `{owner}` "
        f"via the Task tool — do not retry the write yourself.\n"
        f"3. Acknowledge the violation in chat so the user can audit.\n\n"
        f"This violation has been logged to ~/.cursor/audit/writer-violations.jsonl."
    )

    sys.stdout.write(json.dumps({
        "permission": "allow",
        "followup_message": followup,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
