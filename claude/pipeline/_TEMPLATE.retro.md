# Retro template (do not use in place — orchestrator copies to the active project).
# Path: <project>/.claude/pipeline/<feature-slug>.retro.md
#
# Written by pipeline-orchestrator at the `retro` stage (via /epic-retro or
# autopilot after merge). The writer-guard hook restricts writes under
# .claude/pipeline/** to the orchestrator.
#
# Self-improvement scope:
#   - Project-level .claude/ fixes MAY be auto-applied (and logged below).
#   - Global ~/.claude/ changes are PROPOSALS ONLY — the human applies them.

# Retro — <slug>

## Meta
- slug: <kebab-feature-slug>
- ticket: <TICKET-KEY or n/a>
- pr: <pr_url(s)>
- spec: <.claude/specs/<slug>.spec.md>
- dates: started <YYYY-MM-DD> · merged <YYYY-MM-DD>
- autopilot: <true|false>

## 1. What happened (timeline)
One-line per stage transition, pulled from the state `log`. Note any `blocked` events.
- <stage → stage>: <note>

## 2. What went well
- <bullet — keep doing this>

## 3. What slowed us down
For each: symptom → root cause → which artifact is responsible.
- **<symptom>** — root cause: <…> — owner artifact: `<file>`

## 4. Gate failures & retries
- preflight failures: <count, which gate, fixed how>
- reviewer findings that required rework: <count, themes>
- repeated-failure stops (≥2 on same root cause): <yes/no, what>

## 5. SPEC drift
- Amendments forced mid-implementation: <list, why the original SPEC was wrong>
- File-manifest violations attempted: <any writes outside manifest>

## 6. Metrics (best-effort)
- Files changed (hand-written source): <n>
- PRs opened: <n> (matched the SPEC `## PR plan`? <yes/no>)
- Time spec-approved → pr_open: <duration>
- Human touchpoints: <n> (target on autopilot: 2 — approve-spec + merge)

## 7. Applied fixes (project-level — already done)
Low-risk changes the orchestrator applied to this repo's `.claude/` during the retro.
- `<.claude/...>`: <what changed and why>
- _None_

## 8. Proposed global changes (human applies)
Concrete diffs/descriptions for `~/.claude/` (agents, user CLAUDE.md, skills, preflight.sh, templates). NOT auto-applied.
- **Target**: `~/.claude/<file>`
  - **Problem**: <what this epic revealed>
  - **Proposed change**: <specific edit — quote the lines or describe precisely>
  - **Expected benefit**: <why it helps the next epic>
- _None_

## 9. Action items
- [ ] <owner> — <action> — <when>
