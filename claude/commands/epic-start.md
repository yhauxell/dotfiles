---
description: Begin an epic-class change. Spawns the pipeline-orchestrator subagent, which creates .claude/pipeline/<slug>.state.yaml and runs the first stage. Per CLAUDE.md §0, epic class is for multi-feature, multi-session work — for feature class use /architect → /implement → /review → /preflight directly. Pass --autopilot to run unattended between non-gate stages.
allowed-tools: Task
argument-hint: [--autopilot] <slug-or-ticket-key>: <description>
---

Use the `pipeline-orchestrator` subagent to start an epic-class pipeline.

**Input**: `$ARGUMENTS`

**Autopilot**: if the input contains `--autopilot`, set `autopilot: true` in the new state file. The orchestrator then chains non-gate stages on each `/epic-continue`, stopping only at the two hard gates (`spec_draft` → `/approve-spec`, and `pr_open` → human reviews + merges). Strip the `--autopilot` token before deriving the slug.

**Reminders for the orchestrator**:

- This is **only** for `epic` class. If the user describes work that's actually `trivial` or `feature`, STOP and tell them to use the lighter path (see your prompt's "When NOT to invoke me" section).
- Run Pass 0 (recon): detect repo root, branch, slug.
- Create `.claude/pipeline/<slug>.state.yaml` from the template at `~/.claude/pipeline/_TEMPLATE.state.yaml`. The `writer-guard` PreToolUse hook BLOCKS writes to `.claude/pipeline/**` from any agent other than you.
- Run the first stage: if the refined story is in context, transition to `refined` and either launch `figma-design-implementer` (if Figma URL) or `frontend-architect`. If no refined story, prompt the user to apply the `ticket-refinement` skill first.
- Stop after one stage. Tell the user to run `/epic-continue` for the next.

Invoke the agent now via the Task tool.
