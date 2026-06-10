---
# Module-level SPEC for the dotfiles `claude/` module itself (agent infra, not
# product code). Authored by the main agent — the frontend-architect lane and
# writer-guard protect *project* specs (`<project>/.claude/specs/`); this file
# lives at the canonical dotfiles path and is maintained like the rest of the
# module. Append-only convention still applies (bump `.spec.v2.md` on material
# change).
---

# Full automation: ideation → delivery

## Meta
- ticket: n/a (self-improvement epic for the agent factory)
- author_agent: main agent (infra spec — see header note)
- design_source: n/a
- depends_on_spec: n/a
- status: implementing (PR1 in progress)
- version: 1
- created: 2026-06-09
- updated: 2026-06-09

## 1. Intent (the "why")
The epic pipeline already covers every *stage* from refined ticket to retro, but a
human must type every transition, hold the credentials, and watch CI. This epic
removes the typing, not the judgment: automate intake, resume, CI babysitting,
merge-on-green, and post-deploy watch, while converting the two human gates
(spec approval, PR merge) from blocking-in-session to **async one-tap approvals**.
Target state: zero-typing, human-on-exception.

## 2. Scope
### In scope
- Headless resume of autopilot epics (`epic-resume.sh` + scheduling recipe).
- Non-interactive credentials & permission policy for unattended runs.
- CI babysit loop after `pr_open` (poll checks → feed failures to implementer, bounded).
- Spec-judge stage: adversarial SPEC scoring with auto-`/approve-spec` above threshold, escalation below.
- Auto-merge policy (`gh pr merge --auto` + branch protection) as an opt-in.
- Notification spine (Slack) for gates, failures, escalations.
- Post-merge tail: deploy verification + monitoring watch feeding the retro.

### Out of scope (non-goals)
- Removing the two hard gates outright — they become async, never absent, unless a
  project explicitly opts into `auto_merge: true`.
- Auto-merge to protected branches without CI green + required reviews.
- Ticket *writing* (intake consumes existing tickets; it does not invent work).
- Porting any of this to the Cursor module.

## 3. Constraints & non-functional requirements
- Safety: writer-guard lanes stay enforced in headless runs; `--dangerously-skip-permissions` is banned — headless runs use `--permission-mode acceptEdits` at most.
- Cost: every loop is bounded (existing same-stage-3×-stop guard applies headlessly too; resume scheduler must be idempotent and lock per slug).
- §3 `--no-verify` policy and FULL-preflight gate are unchanged.
- Working-tree safety: a headless resume must never touch a repo whose checked-out branch differs from the epic's branch.
- Observability: every headless action logs to `~/.claude/logs/` and (when wired) notifies Slack. Silence is a bug.

## 4. Design context
n/a (no UI).

## 5. Pattern donors
- `scripts/preflight.sh` — arg parsing, logging style, exit-code discipline.
- `agents/pipeline-orchestrator.md` — stage enum, hard-gate semantics, cost guard; new stages/policies extend its existing sections.
- `pipeline/_TEMPLATE.state.yaml` — single source of truth read by the resume script (`stage`, `autopilot`, `branch`, `artifacts.pr_url`).

## 6. Component tree
n/a — module artifacts instead:
```
scripts/epic-resume.sh        # PR1: headless resume trigger (cron/launchd/scheduled agent)
agents/pipeline-orchestrator  # PR3+: ci_watch stage, spec-judge policy, notify hooks
pipeline/_TEMPLATE.state.yaml # PR3+: auto_merge, notify, judge fields
commands/epic-*.md            # touched per PR where behavior changes
```

## 7. Contracts (single source of truth)
### `epic-resume.sh` CLI (PR1)
```
epic-resume.sh [--dry-run] <project-dir> [<project-dir> ...]
```
- Scans `<project>/.claude/pipeline/*.state.yaml` (skips `_TEMPLATE*`).
- Resumes (runs `claude -p "/epic-continue <slug>" --permission-mode acceptEdits`
  from the project root) **only when ALL hold**:
  1. `autopilot: true`
  2. `stage` is not a hard gate (`spec_draft`, `pr_open`) and not `done`
  3. repo's checked-out branch == state `branch` (clobber guard)
  4. per-slug lock acquired (no concurrent resume)
- `pr_open` special case: if `gh pr view <pr_url> --json state` reports `MERGED`,
  the gate has cleared — resume so the orchestrator advances `merged → retro`.
- Exit 0 if all decisions were made (including "skipped"); non-zero only on
  script-level errors. Per-epic actions logged to `~/.claude/logs/epic-resume.log`.

### State YAML additions (later PRs)
```yaml
automation:            # PR3+
  auto_merge: false    # opt-in: gh pr merge --auto when CI green + approvals met
  notify: null         # Slack channel for gate/failure notifications
gates:
  judge_verdict: null  # PR4: approve | escalate (spec-judge)
  judge_score: null
```

## 8. File manifest
- [ ] `claude/scripts/epic-resume.sh` (new) — PR1
- [ ] `claude/README.md` (modify: headless automation section) — PR1
- [ ] `README.md` (modify: layout line) — PR1
- [ ] `claude/settings.json` (modify: git/gh allow rules — **human applies**, classifier blocks self-modification) — PR2
- [ ] docs for credential setup (`claude/README.md` troubleshooting) — PR2
- [ ] `claude/agents/pipeline-orchestrator.md` (modify: `ci_watch` loop, notify) — PR3
- [ ] `claude/pipeline/_TEMPLATE.state.yaml` (modify: `automation` block) — PR3
- [ ] `claude/agents/pipeline-orchestrator.md` (modify: spec-judge policy) — PR4
- [ ] `claude/commands/approve-spec.md` (modify: judge-assisted path) — PR4
- [ ] `claude/agents/pipeline-orchestrator.md` + `claude/commands/epic-ship.md` (modify: auto-merge opt-in) — PR5
- [ ] `claude/agents/pipeline-orchestrator.md` (modify: deploy-watch tail feeding retro) — PR6

## 8.5 PR plan
Triggered: >10 files and ≥2 layers (scripts, agent policies, templates, docs). Vertical
slices — each PR is one independently useful automation capability.

| PR | Capability | Files | Depends on | Acceptance |
|----|------------|-------|------------|------------|
| PR1 | Headless resume trigger | `epic-resume.sh`, READMEs | — | `bash -n` clean; dry-run correct on fixture state files (resume / skip-gate / skip-branch-mismatch / pr_open-merged) |
| PR2 | Unattended credentials & permissions | `settings.json` (human), README docs | — | `git push` + `gh` run promptless in a test repo |
| PR3 | CI babysit loop + notification spine | orchestrator, state template | PR1, PR2 | failing check → implementer fix → re-push, bounded at 3; Slack notified |
| PR4 | Spec-judge (async spec gate) | orchestrator, approve-spec | PR3 | judge approves clean SPEC, escalates ambiguous one to Slack |
| PR5 | Auto-merge opt-in | orchestrator, epic-ship | PR3 | `auto_merge: true` → `gh pr merge --auto`; default stays hard stop |
| PR6 | Deploy/monitor tail | orchestrator, retro template | PR5 | post-merge watch result lands in retro |

- **Split mode**: vertical — each capability is independently shippable and revertible.
- **Merge order**: PR1 → PR2 → PR3 → PR4/PR5 (parallel) → PR6.

## 9. Tasks
### T1 — epic-resume.sh (PR1)
- depends_on: []
- files: [`claude/scripts/epic-resume.sh`]
- action: implement the §7 contract; naive YAML field extraction (grep/sed) is fine — state files are machine-written.
- acceptance: §8.5 PR1 row.
- verify_commands: [`bash -n claude/scripts/epic-resume.sh`, dry-run against fixtures]

### T2 — README docs (PR1)
- depends_on: [T1]
- files: [`claude/README.md`, `README.md`]
- action: add "Headless automation" subsection (script usage + cron/launchd/scheduled-agent recipe); update layout line.
- acceptance: docs match the implemented flags.

### T3..T8 — one task per remaining PR row (specced at that PR's start; this spec gets a `.v2` if contracts shift).

## 10. Decisions & rejected alternatives
- **D1: keep both hard gates, make them async.**
  - chosen: Slack-notified one-tap approvals; auto-merge strictly opt-in per epic.
  - rejected: fully autonomous merge — the cost of a bad merge dwarfs the minutes saved.
- **D2: resume via external scheduler invoking `claude -p`, not a long-lived daemon.**
  - chosen: cron/launchd/scheduled agent calling `epic-resume.sh`; state YAML makes this idempotent.
  - rejected: persistent watcher process — more moving parts, no benefit over polling.
- **D3: branch-match clobber guard.**
  - chosen: skip resume when the repo's checked-out branch ≠ epic branch.
  - rejected: auto-checkout/worktree switch — too invasive for a background job; revisit with per-epic worktrees later.
- **D4: `acceptEdits`, never skip-permissions, for headless runs.** Writer-guard and the permission allowlist remain the enforcement layer.

## 11. Open questions
1. Intake trigger (ClickUp tag → `/epic-start`): scheduled agent poll vs webhook→CI? (decide at PR3, when notifications exist to make it observable)
2. Per-epic git worktrees for headless runs (lifts D3's restriction)?
3. Where does "deploy verified" signal come from per project (CI status vs Embrace monitoring window)? Project-specific — PR6 defines the interface only.

## 12. Test strategy
- PR1: `bash -n` + dry-run against fixture state files covering all four decision paths.
- PR3+: rehearsal epic in a sandbox repo; failure injection (red CI) to prove bounded retry; notification assertions are manual (observe Slack).
- n/a: unit/RTL/saga (no product code).

## 13. Rollout & cleanup
- Rollout: capability per PR; everything risky (`auto_merge`, judge auto-approve) ships default-off, opt-in per epic via state YAML.
- Cleanup: none anticipated; D3 restriction revisited under open question 2.

## Change log
- v1 (2026-06-09): initial spec; PR1 implemented alongside.
