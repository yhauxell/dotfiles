---
description: Execute a SPEC task-by-task. Spawns the feature-implementer subagent which parses .claude/specs/<slug>.spec.md, runs each task's verify_commands, and stops if reality contradicts the SPEC.
allowed-tools: Task
argument-hint: <spec-path or feature-slug>
---

Use the `feature-implementer` subagent to execute the SPEC.

**Input**: `$ARGUMENTS` (a spec path like `.claude/specs/proj-123-feature.spec.md`, a slug like `proj-123-feature`, or `continue implementation` to resume an in-progress SPEC).

**Reminders for the implementer**:

- Resolve to the latest `*.spec.vN.md` if a versioned spec exists.
- If the SPEC's `## Meta` `status` is `draft`, stop and ask the user to confirm it's final.
- Per `CLAUDE.md` §1, you do NOT write to `.claude/specs/`, `docs/test-plans/`, or `.claude/pipeline/`. The `writer-guard` PreToolUse hook will block those paths.
- Two consecutive verify failures on the same root cause → hard stop (`CLAUDE.md` §8).
- After the final task, run `~/.claude/scripts/preflight.sh` as a self-check, then hand off to the user with "run `/ship` next."

Invoke the agent now via the Task tool.
