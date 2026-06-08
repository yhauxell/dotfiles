---
description: Composite pre-commit gate — runs /review then /preflight in that order, then prompts the user to commit. The canonical "ready to ship" command for feature and epic classes per CLAUDE.md §3.
allowed-tools: Task, Bash(~/.claude/scripts/preflight.sh:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git merge-base:*)
---

Run the mandatory pre-commit gate from `CLAUDE.md` §3:

**Step 1 — Adversarial review** (via `adversarial-frontend-reviewer` subagent):

Invoke the reviewer with the Task tool. Wait for the verdict.

- If verdict is `Block` or `Request changes`: **stop here**. Surface findings to the user. Do not proceed to preflight.
- If verdict is `Approve` or `Approve with comments`: proceed to step 2.

**Step 2 — Preflight quality gate**:

!`~/.claude/scripts/preflight.sh`

- If `FAIL`: stop. Identify the failing gate, propose a fix.
- If `PASS`: proceed to step 3.

**Step 3 — Commit prompt**:

Both gates passed. Tell the user:

> Both gates passed. Ready to commit. The reviewer verdict was `<Approve | Approve with comments>` and preflight returned `PASS`. Do you want me to draft the commit message, or will you commit manually?

Per `CLAUDE.md` provenance §7, when drafting the commit message include the `change_class` and (for feature/epic) a link to the SPEC.

Do NOT commit unless the user explicitly says so. Never commit unless gate steps 1 and 2 both pass — unless the user opts out with `skip gate` (per `pipeline-gate-router.py` hook semantics).
