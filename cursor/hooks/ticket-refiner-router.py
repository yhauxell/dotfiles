#!/usr/bin/env python3
"""
beforeSubmitPrompt hook: routes pasted ticket URLs / ticket keys to the
`ticket-refiner` subagent.

Supported tracker URL hosts: ClickUp, Linear, Jira (atlassian.net), GitHub
Issues, GitLab Issues, Shortcut. Ticket-key heuristic also matches generic
`PROJ-123`-style identifiers, so most other trackers work too.

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
    """
    Best-effort: hook payload shapes can vary by Cursor version/event.
    Return (field_name, text).
    """
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


def _already_invokes_refiner(text: str) -> bool:
    t = text.lower()
    return "ticket-refiner" in t or "use the ticket-refiner" in t


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

    if not _should_route(text) or _already_invokes_refiner(text):
        print(json.dumps({"permission": "allow"}))
        return 0

    updated = (
        "Use the ticket-refiner subagent to refine this ticket / story.\n\n"
        "Input:\n"
        f"{text.strip()}\n"
    )

    print(json.dumps({"permission": "allow", "updated_input": updated}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
