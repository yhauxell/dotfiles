#!/usr/bin/env python3
"""
UserPromptSubmit hook: detects pasted ticket URLs / ticket keys and routes
the main agent to apply the `ticket-refinement` skill before doing anything
else.

Supported tracker URL hosts: ClickUp, Linear, Jira (atlassian.net), GitHub
Issues, GitLab Issues, Shortcut. Ticket-key heuristic also matches generic
`PROJ-123`-style identifiers, so most other trackers work too.

Claude Code event contract (UserPromptSubmit):
- stdin: JSON with at least `prompt` (the user's submitted text).
- stdout: extra context to inject into the prompt (printed verbatim).
- exit 0: continue normally.
- exit 2: block the prompt (NOT used here — this hook is informational).

Fails open on parse errors or unexpected payload shapes.
"""

import json
import re
import sys


TICKET_URL_RE = re.compile(
    r"https?://[^\s]*"
    r"(?:"
    r"clickup\.com|"
    r"linear\.app|"
    r"atlassian\.net|"
    r"github\.com/[^\s]+/issues|"
    r"gitlab\.com/[^\s]+/issues|"
    r"app\.shortcut\.com"
    r")"
    r"[^\s]*",
    re.IGNORECASE,
)

TICKET_ID_RE = re.compile(r"\b[A-Z]{2,20}-\d{1,8}\b")


def _extract_prompt(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("prompt", "user_prompt", "input", "content", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _should_route(text):
    if TICKET_URL_RE.search(text):
        return True
    if TICKET_ID_RE.search(text):
        return True
    return False


def _already_invokes_skill(text):
    t = text.lower()
    return "ticket-refinement" in t or "ticket-refiner" in t


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

    if not _should_route(text) or _already_invokes_skill(text):
        return 0

    # Print extra context for Claude. It becomes part of the conversation
    # for this turn (per the Claude Code UserPromptSubmit hook contract).
    sys.stdout.write(
        "[ticket-refiner-router] A ticket URL or ticket key was detected "
        "in this prompt. Per CLAUDE.md §0, before doing anything else "
        "apply the `ticket-refinement` skill "
        "(~/.claude/skills/ticket-refinement/SKILL.md) to produce a refined "
        "engineering story (Gherkin AC, impacted areas, API/data impacts, "
        "edge cases). Then proceed with the original request, using the "
        "refined story as context. Skip refinement only if the change_class "
        "is `trivial`.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
