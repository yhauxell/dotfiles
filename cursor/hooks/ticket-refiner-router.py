#!/usr/bin/env python3
"""
beforeSubmitPrompt hook: detects pasted ticket URLs / ticket keys and routes
the main agent to apply the `ticket-refinement` skill before doing anything
else.

Supported tracker URL hosts: ClickUp, Linear, Jira (atlassian.net), GitHub
Issues, GitLab Issues, Shortcut. Ticket-key heuristic also matches generic
`PROJ-123`-style identifiers, so most other trackers work too.

History: previously routed to a `ticket-refiner` subagent. That agent was
demoted to a skill (cursor/skills/ticket-refinement/SKILL.md) — the main
agent now applies the skill directly, no subagent rental needed.

Fails open on parse errors or unsupported Cursor versions — never blocks
prompt submission.
"""

import json
import re
import sys
from typing import Any, Dict, Optional, Tuple


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


def _extract_text(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    for key in ("prompt", "input", "content", "message", "text", "user_prompt"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return key, value

    args = payload.get("arguments")
    if isinstance(args, dict):
        for key in ("prompt", "input", "content", "text"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return f"arguments.{key}", value

    return None, None


def _should_route(text: str) -> bool:
    if TICKET_URL_RE.search(text):
        return True
    if TICKET_ID_RE.search(text):
        return True
    return False


def _already_invokes_skill(text: str) -> bool:
    t = text.lower()
    return "ticket-refinement" in t or "ticket-refiner" in t


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print(json.dumps({"permission": "allow"}))
        return 0

    try:
        payload = json.loads(raw)
    except Exception:
        print(json.dumps({"permission": "allow"}))
        return 0

    _, text = _extract_text(payload if isinstance(payload, dict) else {})
    if not text:
        print(json.dumps({"permission": "allow"}))
        return 0

    if not _should_route(text) or _already_invokes_skill(text):
        print(json.dumps({"permission": "allow"}))
        return 0

    updated = (
        "A ticket URL or ticket key was detected in this prompt. Before "
        "doing anything else, apply the `ticket-refinement` skill "
        "(~/.cursor/skills/ticket-refinement/SKILL.md) to produce a refined "
        "engineering story (Gherkin AC, impacted areas, API/data impacts, "
        "edge cases). Then proceed with the original request, using the "
        "refined story as context.\n\n"
        "Skip refinement only if the change_class is `trivial` (copy tweak, "
        "single-file refactor, dep bump).\n\n"
        "Original request:\n"
        f"{text.strip()}\n"
    )

    print(json.dumps({"permission": "allow", "updated_input": updated}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
