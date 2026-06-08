---
description: Advance an in-progress epic by one stage. Spawns the pipeline-orchestrator subagent, which reads .claude/pipeline/<slug>.state.yaml, decides the next action per its stage rules, launches the right subagent, updates state, and stops.
allowed-tools: Task
argument-hint: [slug if multiple epics in flight]
---

Use the `pipeline-orchestrator` subagent to advance the current epic by one stage.

**Input** (optional slug): `$ARGUMENTS`

**Reminders for the orchestrator**:

- Run Pass 0 (recon) to load state from `.claude/pipeline/<slug>.state.yaml`.
- If multiple epics match the current branch and no slug was provided, ask the user which one.
- Decide the next action per your Pass 1 stage rules.
- Launch exactly one subagent (or run preflight script) per call — **unless** the user said `run until blocked` OR the state has `autopilot: true`, in which case chain non-gate stages automatically per "Autopilot mode".
- Update state via Edit/Write on `.claude/pipeline/<slug>.state.yaml`. The writer-guard hook will only allow YOU to write there.
- Stop at the next hard checkpoint. With autopilot the hard stops are `spec_draft` (→ `/approve-spec`) and `pr_open` (→ human reviews + merges). Without autopilot, also stop after each single stage.

Invoke the agent now via the Task tool.
