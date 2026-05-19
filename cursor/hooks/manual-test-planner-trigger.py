#!/usr/bin/env python3
"""
subagentStop hook: fires after the `adversarial-frontend-reviewer` subagent stops.

Behavior:
- Reads the subagentStop event JSON on stdin (and discards it; the matcher
  in hooks.json already gates this hook to the adversarial reviewer).
- Returns a `followup_message` instructing the parent agent to invoke the
  `manual-test-planner` subagent and save the resulting test plan to
  `docs/test-plans/<branch-slug>.md`.
- Fails open (returns empty JSON) on any unexpected error so the parent
  workflow is never blocked by the hook.
"""

import json
import sys


def main() -> int:
    try:
        sys.stdin.read()
    except Exception:
        pass

    followup = (
        "The `adversarial-frontend-reviewer` subagent just finished. "
        "Run the `manual-test-planner` subagent next to produce a manual QA "
        "test plan for this branch's changes. The subagent will save the "
        "plan as a markdown file at `docs/test-plans/<branch-slug>.md` "
        "(creating the directory if needed). Keep the output simple, easy "
        "to follow, and focused on observable user-facing behavior — it is "
        "for human testers, not for AI consumption."
    )

    try:
        sys.stdout.write(json.dumps({"followup_message": followup}))
        sys.stdout.flush()
    except Exception:
        sys.stdout.write("{}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
