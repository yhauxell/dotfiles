---
description: Run the quality gate — lint, typecheck, tests — via ~/.claude/scripts/preflight.sh. Replaces the former pr-preflight subagent (demoted because this work is entirely mechanical, no model rental needed).
allowed-tools: Bash(~/.claude/scripts/preflight.sh:*), Bash(./cursor/scripts/preflight.sh:*)
argument-hint: [--keep-going | --staged-only]
---

Run the preflight quality gate:

!`~/.claude/scripts/preflight.sh $ARGUMENTS`

Interpret the output:

- **PASS** → ready for commit. Confirm what was run.
- **FAIL** → identify the failing gate(s) from the summary, extract the key error(s), propose the smallest fix. Do not commit.

If the script reports "no recognized scripts in package.json", note that this project doesn't follow the standard `lint-staged`/`lint`/`typecheck`/`test` convention — surface this to the user instead of pretending it passed.

Per `CLAUDE.md` §3:

- For `trivial` class: this is the entire pre-commit gate.
- For `feature`/`epic` class: this is gate step 2 (run `/review` first, or use `/ship` to compose both).
