---
description: Approve the architect's SPEC for an epic-class change. Spawns the pipeline-orchestrator subagent to set checkpoints.spec_approved=true and transition stage to spec_approved. This is the only way to unblock /epic-continue from launching feature-implementer.
allowed-tools: Task
argument-hint: [slug if multiple epics in flight]
---

Use the `pipeline-orchestrator` subagent to approve the current epic's SPEC.

**Input** (optional slug): `$ARGUMENTS`

**Reminders for the orchestrator**:

- Run Pass 0 (recon) to load state.
- Verify `artifacts.spec_path` is set and the SPEC's `## Open questions` are empty (or the user has waived them).
- Set `checkpoints.spec_approved: true` and `stage: spec_approved`.
- Append a `log` entry recording the approval.
- Do **not** launch `feature-implementer` in the same turn — tell the user to run `/epic-continue` next.

Invoke the agent now via the Task tool.
