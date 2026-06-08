---
description: Produce the retrospective for a finished epic. Spawns the pipeline-orchestrator subagent, which writes .claude/pipeline/<slug>.retro.md from the template, capturing what stalled, gate failures, forced SPEC amendments, and concrete improvement proposals. Project-level .claude/ fixes may be auto-applied; global ~/.claude/ changes are written as proposals for the human to apply.
allowed-tools: Task
argument-hint: [slug if multiple epics in flight]
---

Use the `pipeline-orchestrator` subagent to write the epic retro.

**Input** (optional slug): `$ARGUMENTS`

**Reminders for the orchestrator** (see your "Retro stage" section):

- Valid from stage `merged` or `done` (or when the user explicitly asks for a retro).
- Write `.claude/pipeline/<slug>.retro.md` from `~/.claude/pipeline/_TEMPLATE.retro.md`. The writer-guard hook allows only YOU to write under `.claude/pipeline/`.
- Capture: stalls, gate failures + retries, SPEC amendments forced mid-flight, time-to-PR, and **concrete proposed changes mapped to specific files**.
- **Self-improvement scope**: you MAY auto-apply low-risk fixes to **project-level** `.claude/` files (and log them). You MUST NOT edit **global** `~/.claude/` files — write those as diffs under `## Proposed global changes (human applies)`.
- Pull retro signal from this epic's `log` entries and any conversation feedback from the user.
- Set `artifacts.retro_path`, `stage: retro` → `done`.

Invoke the agent now via the Task tool.
