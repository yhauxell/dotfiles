---
description: Ship the current epic's branch — push to remote and open a PR. Spawns the pipeline-orchestrator subagent, which verifies the FULL preflight PASS is recorded for the current HEAD, applies the --no-verify policy, pushes, and opens the PR (then HARD STOPS for human review + merge). Only valid at stage `ready_to_ship`.
allowed-tools: Task
argument-hint: [slug if multiple epics in flight]
---

Use the `pipeline-orchestrator` subagent to push the branch and open the PR for the current epic.

**Input** (optional slug): `$ARGUMENTS`

**Reminders for the orchestrator** (see your "Ship the task — push + open PR" section):

- Only proceed from stage `ready_to_ship`. If earlier, run the gate first; if later, report and stop.
- **Preconditions**: `gates.preflight_result: PASS` AND `gates.preflight_result_head == git rev-parse HEAD`, reviewer verdict OK, and `gh auth status` succeeds. If HEAD moved since the PASS, re-run the FULL preflight before pushing.
- **`--no-verify` policy**: allowed ONLY when the full PASS is recorded for the current HEAD AND a runtime read of `.husky/` confirms the hooks are a subset of what preflight already ran. Otherwise let the hooks run. Log the decision.
- Never push to `main`/`master`; ensure a `feat/<slug>` branch.
- If the SPEC has a multi-PR `## PR plan`, open the PRs in declared merge order with stacked bases; report every PR URL.
- After opening: set `artifacts.pr_url`, `stage: pr_open`, and **STOP** — the human reviews and merges. Do not merge.

Invoke the agent now via the Task tool.
