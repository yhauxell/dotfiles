---
description: Adversarial red-team review of the current branch. Spawns the adversarial-frontend-reviewer subagent — multi-pass review focused on React/RN correctness, hooks, type safety, state/async, performance, a11y, security, styling, tests, and architectural drift. Outputs severity-ranked findings with file:line citations.
allowed-tools: Task, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git merge-base:*)
---

Use the `adversarial-frontend-reviewer` subagent to perform an aggressive, evidence-backed review of the current branch's changes.

**Context** (run before invoking):

- Current branch: !`git rev-parse --abbrev-ref HEAD`
- Recent commits on this branch: !`git log -10 --oneline`

**Reminders for the reviewer**:

- Detect the base branch (`main`/`master`/`develop`) via `git merge-base` if ambiguous.
- Run all 3 passes: adversarial sweep → targeted re-read → self-critique.
- Calibrate severity. `Critical` only for crashes, data loss, security, broken UX, or shipped regressions.
- No fixes — your job is findings. Your `tools:` excludes Edit/Write, and the writer-guard would block anyway.
- Output verdict: `Block` | `Request changes` | `Approve with comments` | `Approve`.

If the SPEC exists at `.claude/specs/<slug>.spec.md`, cross-reference the diff against the SPEC's `## File manifest` and flag any drift.

Invoke the agent now via the Task tool.
