---
description: Print the epic dashboard for the current branch (or named slug). Read-only, no subagent rental — directly reads the state YAML and SPEC meta inline.
allowed-tools: Read, Glob, Bash(git branch:*), Bash(git rev-parse:*)
argument-hint: [slug if multiple epics in flight]
---

Print the epic dashboard without running any subagent.

**Steps**:

1. Determine the current branch: !`git branch --show-current`
2. List epic state files: @.claude/pipeline/
3. If a slug was provided in `$ARGUMENTS`, use `.claude/pipeline/$ARGUMENTS.state.yaml`. Otherwise, pick the newest `.state.yaml` whose `branch:` field matches the current git branch. If none, say so and stop.
4. Read the state YAML and (if `artifacts.spec_path` is set) the SPEC's `## Meta` block.
5. Print the dashboard:

```text
## Epic — <slug>
- Stage: <stage>
- Branch: <branch>
- SPEC: <path or "none"> (meta status: <draft|approved|…>)
- Checkpoints: spec_approved=<bool> ship_approved=<bool>
- Gates: reviewer=<verdict> preflight=<result>
- Last log entry: <at — agent_or_script — note>
- Next recommended: <one-line from stage rules>
```

Do NOT modify the state file. Do NOT spawn subagents. This is a pure read.
