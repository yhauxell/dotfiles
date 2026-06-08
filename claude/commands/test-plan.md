---
description: Generate a manual QA test plan for the current branch's diff. Spawns the manual-test-planner subagent. Opt-in only — there is no auto-chain after /review (the Cursor module's subagentStop auto-chain was NOT ported).
allowed-tools: Task
---

Use the `manual-test-planner` subagent to produce a manual QA test plan for the current branch's changes.

**Reminders for the planner**:

- Output a single markdown file at `docs/test-plans/<branch-slug>.md`. Create the directory if missing.
- Append-only — if a plan already exists for this branch, append an `### Update <YYYY-MM-DD>` section; do not overwrite.
- Plain language for human testers — no code references, no internal jargon.
- Cap the plan to the actual scope of the diff; do not pad.
- Calibrate severity (P0 = release blocker only).
- Your `tools:` allows Edit/Write but the writer-guard hook restricts you to `docs/test-plans/**`. Attempts to write elsewhere will be BLOCKED.

After writing the plan, report:

- The exact file path.
- Case counts: `P0: N, P1: M, P2: K`.
- The top 3 things you would test first if the tester only had 30 minutes.

Invoke the agent now via the Task tool.
