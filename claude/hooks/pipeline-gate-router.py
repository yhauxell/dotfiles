#!/usr/bin/env python3
"""
UserPromptSubmit hook: when the user asks to commit, push, open a PR, or
ship, inject a reminder to run the mandatory verification gate first.

Claude Code event contract (UserPromptSubmit):
- stdin: JSON with `prompt`.
- stdout: extra context injected into the prompt.
- exit 0: continue.

Does NOT block submission. Best-effort prompt injection only. Opt out with
`skip gate` (or similar) in the prompt.
"""

import json
import re
import sys


SHIP_RE = re.compile(
    r"\b("
    r"commit|let'?s commit|git commit|"
    r"open a pr|open pr|create pr|pull request|"
    r"push|git push|"
    r"ship it|let'?s ship|ready to merge|merge"
    r")\b",
    re.IGNORECASE,
)

OPT_OUT_RE = re.compile(
    r"\b(skip (the )?gate|skip preflight|skip review|no gate|without gate)\b",
    re.IGNORECASE,
)

# NOTE: alternations starting with `/` (slash) cannot use `\b` at the left edge:
# `\b` is a transition between a word char and non-word char, and `/` itself
# is non-word, so `\b/ship` never matches if preceded by a non-word char
# (space, start-of-string, etc.). We use a non-anchored search instead.
ALREADY_ROUTED_RE = re.compile(
    r"("
    r"\badversarial-frontend-reviewer\b|"
    r"\bpreflight\.sh\b|"
    r"/review\b|/preflight\b|/ship\b|"
    r"\bpipeline-orchestrator\b|"
    r"\brun (the )?gate\b"
    r")",
    re.IGNORECASE,
)


def _extract_prompt(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("prompt", "user_prompt", "input", "content", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except Exception:
        return 0

    text = _extract_prompt(payload)
    if not text:
        return 0

    if not SHIP_RE.search(text):
        return 0
    if OPT_OUT_RE.search(text) or ALREADY_ROUTED_RE.search(text):
        return 0

    sys.stdout.write(
        "[pipeline-gate-router] Before committing, pushing, or opening a "
        "PR, run the mandatory pre-ship gate (per CLAUDE.md §3):\n"
        "  - For feature/epic class: run `/ship` (composes `/review` + "
        "`/preflight`).\n"
        "  - For trivial class: run `/preflight` only.\n"
        "  - If an epic pipeline state exists, use `pipeline-orchestrator` "
        "with `run gate`.\n"
        "Only proceed with the original request after the gate passes, "
        "unless the user explicitly opted out with `skip gate`.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
