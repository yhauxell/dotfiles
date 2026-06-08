#!/usr/bin/env python3
"""
beforeSubmitPrompt hook: when the user asks to commit, push, open a PR, or ship,
rewrite the prompt to run the mandatory verification gate first.

Does not block submission (failClosed: false). Best-effort prompt injection only.
"""

import json
import re
import sys
from typing import Any, Dict, Optional, Tuple


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

ALREADY_ROUTED_RE = re.compile(
    r"\b(adversarial-frontend-reviewer|preflight\.sh|pr-preflight|run (the )?gate|pipeline-orchestrator)\b",
    re.IGNORECASE,
)


def _extract_text(payload: Dict[str, Any]) -> Optional[str]:
    for key in ("prompt", "input", "content", "message", "text", "user_prompt"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    args = payload.get("arguments")
    if isinstance(args, dict):
        for key in ("prompt", "input", "content", "text"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


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

    text = _extract_text(payload if isinstance(payload, dict) else {})
    if not text:
        print(json.dumps({"permission": "allow"}))
        return 0

    if not SHIP_RE.search(text) or OPT_OUT_RE.search(text) or ALREADY_ROUTED_RE.search(text):
        print(json.dumps({"permission": "allow"}))
        return 0

    updated = (
        "Before committing, pushing, or opening a PR, run the mandatory pre-ship gate "
        "(per agent-constitution §3):\n"
        "1. `adversarial-frontend-reviewer` — must be Approve or Approve with comments.\n"
        "2. `cursor/scripts/preflight.sh` — must report PASS (run via Bash).\n"
        "If an epic pipeline state exists, invoke `pipeline-orchestrator` with "
        "`run gate` instead.\n"
        "For `trivial`-class changes, only step 2 is required.\n"
        "Only proceed with the user's original request after the gate passes, "
        "unless they explicitly opted out with 'skip gate'.\n\n"
        "Original request:\n"
        f"{text.strip()}\n"
    )

    print(json.dumps({"permission": "allow", "updated_input": updated}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
