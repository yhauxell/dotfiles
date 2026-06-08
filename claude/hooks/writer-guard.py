#!/usr/bin/env python3
"""
PreToolUse hook (matcher: Edit|Write|MultiEdit): enforces the single-writer
invariants from CLAUDE.md §1 + §9 by BLOCKING writes to protected paths
when the calling agent is not the authorized owner.

This is the net-new capability vs. the Cursor module. Cursor only had
afterFileEdit (post-hoc) — the best we could do there was demand a revert
after the damage. Claude Code's PreToolUse + exit 2 lets us deny the call
BEFORE the write happens.

Protected paths and their sole authorized writer (matches the `name:` in
each agent's frontmatter):

    .claude/specs/**         -> frontend-architect
    .cursor/specs/**         -> frontend-architect  (cross-tool compat)
    .claude/pipeline/**      -> pipeline-orchestrator
    docs/test-plans/**       -> manual-test-planner

Caller identity:
- We try multiple JSON field names since Claude Code's exact schema for
  passing subagent identity in PreToolUse payloads may evolve. If we
  cannot positively identify the caller as the authorized owner, the
  protected write is BLOCKED (failing closed is the safe default).
- This is intentional: a misidentified main-agent write to .claude/specs/
  is exactly the violation we are trying to prevent.

Claude Code PreToolUse contract:
- stdin: JSON with `tool_name`, `tool_input` (e.g. {"file_path": "..."}),
  plus session/agent metadata.
- stderr: when exit 2, the message is fed back to Claude.
- exit 0: allow the tool call.
- exit 2: BLOCK the tool call (the only deny path for PreToolUse).
- failClosed: true (configured in settings.json) — any unexpected error
  surfaces the failure rather than silently allowing the write.

Every protected-path attempt is logged to:
    ~/.claude/audit/writer-violations.jsonl
including BOTH blocked and allowed writes to protected paths, so the audit
trail captures the full lane-keeping history.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple

# --- Protected-path policy --------------------------------------------------

# Each entry: (path-prefix, authorized agent `name:`, human label)
POLICY = [
    (".claude/specs/",      "frontend-architect",    "SPEC"),
    (".cursor/specs/",      "frontend-architect",    "SPEC (Cursor-compat)"),
    (".claude/pipeline/",   "pipeline-orchestrator", "pipeline state"),
    ("docs/test-plans/",    "manual-test-planner",   "manual test plan"),
]

AUDIT_DIR = os.path.expanduser("~/.claude/audit")
AUDIT_LOG = os.path.join(AUDIT_DIR, "writer-violations.jsonl")


# --- Payload parsing --------------------------------------------------------

def _first_str(d: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_file_path(payload: Dict[str, Any]) -> Optional[str]:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        # Edit, Write, NotebookEdit all use `file_path`.
        # MultiEdit uses `file_path` too.
        v = _first_str(tool_input, ("file_path", "path", "filename", "target"))
        if v:
            return v
    # Fallbacks at top level.
    return _first_str(payload, ("file_path", "path", "filename"))


def _extract_agent_name(payload: Dict[str, Any]) -> Optional[str]:
    """
    Returns the calling agent's type string, or None if not identifiable.

    Claude Code sets `agent_type` in the PreToolUse payload to the
    `subagent_type` value passed to the Agent tool (e.g. "frontend-architect",
    "pipeline-orchestrator").  For the main session agent this field is absent
    or set to a non-subagent value — in either case the protected-path check
    fails closed, which is correct (the main agent should never write directly
    to protected paths; only the designated subagents should).
    """
    return _first_str(payload, ("agent_type",))


# --- Policy evaluation ------------------------------------------------------

def _normalize_repo_relative(file_path: str) -> str:
    p = file_path
    if p.startswith("./"):
        p = p[2:]
    # If absolute, trim everything up to the first protected prefix occurrence
    # so absolute paths from different machines still match.
    for prefix, _, _ in POLICY:
        idx = p.find(prefix)
        if idx >= 0:
            return p[idx:]
    return p


def _evaluate(file_path: str, agent: Optional[str]) -> Optional[Tuple[str, str, str, str]]:
    """
    Return (decision, label, authorized_agent, matched_prefix) if the path
    matches a protected prefix; None if the path is unprotected.

    decision is "allow" or "block".  Fails closed: any caller that cannot
    be positively identified as the authorized owner is blocked.
    """
    norm = _normalize_repo_relative(file_path)
    for prefix, owner, label in POLICY:
        if norm.startswith(prefix):
            if agent == owner:
                return ("allow", label, owner, prefix)
            return ("block", label, owner, prefix)
    return None


# --- Audit log --------------------------------------------------------------

def _audit(record: Dict[str, Any]) -> None:
    try:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


# --- Main -------------------------------------------------------------------

def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0  # nothing to evaluate
    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0


    file_path = _extract_file_path(payload)
    if not file_path:
        return 0

    agent = _extract_agent_name(payload)
    verdict = _evaluate(file_path, agent)
    if verdict is None:
        return 0  # path is not protected; allow

    decision, label, owner, prefix = verdict
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()

    _audit({
        "ts": now,
        "decision": decision,
        "tool_name": payload.get("tool_name", "<unknown>"),
        "file_path": file_path,
        "matched_prefix": prefix,
        "label": label,
        "authorized_agent": owner,
        "offending_agent": agent or "<unknown>",
    })

    if decision == "allow":
        return 0

    # BLOCK: print to stderr and exit 2.
    msg = (
        f"writer-guard: BLOCKED write to {file_path}\n"
        f"  - this path ({prefix}**) is owned by `{owner}` "
        f"(the {label} writer).\n"
        f"  - caller identity: `{agent or '<unknown>'}` is not authorized.\n"
        f"  - if this write was actually necessary, stop and hand off to "
        f"`{owner}` (typically via the matching slash command).\n"
        f"  - violation logged to ~/.claude/audit/writer-violations.jsonl\n"
    )
    sys.stderr.write(msg)
    return 2


if __name__ == "__main__":
    sys.exit(main())
