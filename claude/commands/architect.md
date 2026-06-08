---
description: Design a feature end-to-end. Spawns the frontend-architect subagent to produce an architectural plan in chat AND a SPEC at .claude/specs/<slug>.spec.md. Use for `feature` or `epic` class changes.
allowed-tools: Task
argument-hint: <refined story or feature description; optionally a design-context block>
---

Use the `frontend-architect` subagent to design the following feature.

**Inputs**:

$ARGUMENTS

**Required outputs**:

1. An architectural plan in chat (rationale, decisions, tradeoffs, risks, open questions).
2. A SPEC artifact written to `.claude/specs/<slug>.spec.md` — see the architect's prompt for the exact structure.

**Reminders for the architect**:

- Run Pass 0 (codebase recon) before forming decisions.
- Load relevant skills from `~/.claude/skills/` per `CLAUDE.md` §4 context-loading order.
- The SPEC is the only file you write. The `writer-guard` PreToolUse hook will BLOCK any other write.
- If a Figma URL is present in the input but no design-context block, ask the user to run `@figma-design-implementer` first.
- After writing the SPEC, tell the user to run `/implement <slug>` next.

Invoke the agent now via the Task tool.
