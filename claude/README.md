# Claude Code module

An **agent factory** for spec-driven frontend development (client-side React SPAs / React Native), driven through Claude Code's **slash commands**, **subagents**, **skills**, and **hooks**. Symlinked to `~/.claude/` by the repo's `install.sh`.

The pipeline is **opt-in by change class** — decide up front whether the work is `trivial`, `feature`, or `epic`, then use the matching amount of process.

## Entry points

| File | What it is |
|------|------------|
| `CLAUDE.md` | The agent constitution — auto-loaded every session. §0 defines change-class routing; §3 the mandatory gate; §5 verification + two-tier checks. |
| `AGENTS.md` | Agent registry, model selection, hooks reference, end-to-end chain. |
| `commands/` | Slash commands (`/classify`, `/discovery`, `/architect`, `/implement`, `/review`, `/preflight`, `/ship`, `/test-plan`, and the `/epic-*` family). |
| `agents/` | 6 subagents (architect, implementer, reviewer, figma, test-planner, orchestrator). |
| `skills/` | Portable knowledge: `ticket-refinement` + 7 React/RN skills, auto-loaded in Pass 0. |
| `scripts/preflight.sh` | The quality gate (lint / typecheck / test). Supports a two-tier fast path. |
| `scripts/epic-resume.sh` | Headless resume trigger for autopilot epics (cron / launchd / scheduled agent). |
| `specs/full-automation.spec.md` | Module SPEC: the ideation→delivery automation roadmap (PR1 = `epic-resume.sh`). |
| `specs/_TEMPLATE.spec.md` | Global SPEC template. Real specs live per-project under `<project>/.claude/specs/`. |
| `pipeline/_TEMPLATE.state.yaml`, `pipeline/_TEMPLATE.retro.md` | Epic state + retro templates (epic-class only). |
| `usage-tracker/` | Time & cost dashboard for your sessions (`track.sh` → `dashboard.html`). See its own [README](usage-tracker/README.md). |
| `settings.json` | Permissions + hook wiring (UserPromptSubmit, PreToolUse, PostToolUse). |
| `models.yaml` | Central role→model registry. |

## 1. The only decision that matters: change class

State it explicitly in chat (*"this is a feature-class change because it adds a route + a store slice"*). Default to the lightest class; escalate mid-flight if reality demands. `/classify <description>` is an explicit forcing function.

| Class | When | Process |
|-------|------|---------|
| **`trivial`** | One file, no new behavior | Main agent + `/preflight` |
| **`feature`** | New flow OR ≥2 of {component, store, api, route} | `/architect` → `/implement` → `/review` → `/preflight` (or `/ship`) |
| **`epic`** | Multi-week, multi-feature, worth tracking state | `pipeline-orchestrator` via `/epic-*`, optionally `--autopilot` |

## 2a. Trivial walkthrough

```text
You: "Fix the typo in src/pages/Login.tsx:42 and bump react-query to ^5.50."
  → Main agent edits directly.
You: "Commit."
  → pipeline-gate-router hook prepends "run /preflight first".
  → Main agent runs /preflight, reports PASS, commits.
```
No SPEC, no subagents.

## 2b. Feature walkthrough (no orchestrator)

```text
[1] You: "Implement PROJ-123: <ticket URL or text>"
    → ticket-refiner-router hook detects the key; main agent applies the
      ticket-refinement skill → refined story in chat.
[2] (Optional, only if Figma) "@figma-design-implementer <Figma URL>" → Design context block.
[3] /architect <refined story [+ design context]>
    → Pass 0.5 may interview you if the input is ambiguous (it STOPS, you answer, re-invoke).
    → Writes .claude/specs/<slug>.spec.md, including a `## PR plan` if the change is large/multi-layer.
[4] /implement <slug>
    → Runs tasks T1..Tn, runs each task's verify_commands, stops if reality contradicts the SPEC.
[5] /ship  (composes /review + /preflight)
    → Reviewer must Approve / Approve-with-comments; full preflight must PASS. Then commit.
```
Three or four messages. No state file.

## 2c. Epic walkthrough (orchestrator-driven)

Use only when work spans weeks / multiple slices and you need state across sessions. The epic machine now runs **through push + PR and ends with a retro**.

```text
/epic-start [--autopilot] PROJ-555: refactor checkout flow
  → Creates .claude/pipeline/proj-555.state.yaml, runs first stage, stops.
/epic-continue            → figma-design-implementer (if Figma) or frontend-architect
/epic-continue            → architect writes SPEC → stage spec_draft. HARD STOP.
/approve-spec             → checkpoints.spec_approved = true
/epic-continue            → feature-implementer
/epic-continue            → reviewer → FULL preflight (records PASS + HEAD SHA)
/epic-ship                → push branch + open PR → stage pr_open. HARD STOP (you review + merge).
(you merge on GitHub)
/epic-retro               → writes .claude/pipeline/<slug>.retro.md
```

- **`/epic-status`** prints the dashboard (read-only, no model rental). Resume a stale epic anytime.
- **Autopilot** (`--autopilot` or `enable autopilot`): `/epic-continue` chains non-gate stages automatically. It **always stops at the two hard gates** — `spec_draft` (→ `/approve-spec`) and `pr_open` (→ you review + merge). It never auto-merges and never skips review.
- Commit the state YAML for team visibility, or gitignore `*.state.yaml` for local-only.

### Headless resume (`scripts/epic-resume.sh`)

Autopilot only chains stages inside a live session. To advance epics **unattended** — overnight, or after a gate clears — schedule `epic-resume.sh`:

```bash
epic-resume.sh [--dry-run] <project-dir> [<project-dir> ...]
```

It scans each project's `.claude/pipeline/*.state.yaml` and runs `claude -p "/epic-continue <slug>" --permission-mode acceptEdits` from the project root, but **only** when: `autopilot: true`, the stage is not a hard gate (`spec_draft`, `pr_open`) or `done`, the repo's checked-out branch matches the epic's branch (clobber guard), and a per-slug lock is free. One exception at `pr_open`: if `gh pr view` reports the PR **merged**, the human gate has cleared and it resumes so the orchestrator advances `merged → retro`. Decisions log to `~/.claude/logs/epic-resume.log`.

Schedule it however you like — cron (`*/30 9-18 * * 1-5 ~/.claude/scripts/epic-resume.sh ~/work/my-app`), launchd, or a Claude Code scheduled task. The full automation roadmap (CI babysit loop, spec-judge, auto-merge opt-in, deploy watch) lives in `specs/full-automation.spec.md`.

### PR split (architect's job)

When a change exceeds reviewer tolerance — **>~10 hand-written source files** (excluding lockfiles/generated/snapshots) **OR** spans **≥2 review layers** `{ui, state, api-integration, observability, analytics}` — `frontend-architect` emits a `## PR plan` in the SPEC: ordered PRs in merge order, each carrying its own tests (never a tests-only PR), each independently passing the full gate. Default is a horizontal layer split; it overrides to vertical thin slices when layers are too coupled to review alone.

### Ship: push + `--no-verify` policy

`/epic-ship` pushes and opens the PR but **never merges** (`pr_open` is a hard stop). It may push with `git push --no-verify` **only** when both hold: (a) a full `preflight.sh` PASS is recorded in state for the current HEAD SHA, and (b) the project's `.husky/` hooks are a verified subset of what preflight already ran. Otherwise the hooks run. Rationale: `--no-verify` is de-duplication of already-passed checks, never a way to skip a check.

> Requires git/gh permissions in `settings.json` (`Bash(git push:*)`, `Bash(gh pr create:*)`, …). Add them via `/permissions` if the push step prompts.

## 3. Two-tier checks (`preflight.sh`)

- **Inner loop (fast):** `preflight.sh --affected[=<base>]` — lint + unit tests run only on files changed vs the base ref (`jest --findRelatedTests`), with `--maxWorkers=50%` and optional jest-native `--shard=<i/N>`. **Typecheck always runs full** (tsc is whole-program).
- **Ship gate (authoritative):** the full run (no `--affected`). Affected mode can miss transitive breakage, so it is never the gate. Each PR in a multi-PR split must pass the full gate independently.

Flags: `--keep-going`, `--staged-only`, `--affected[=<base>]`, `--base=<ref>`, `--shard=<i/N>`, `-h`.

## 4. What runs automatically (hooks, wired in `settings.json`)

| Hook | Event | Behavior |
|------|-------|----------|
| `ticket-refiner-router.py` | `UserPromptSubmit` | Tracker URL / `PROJ-123` key → prepends "apply ticket-refinement skill first". |
| `pipeline-gate-router.py` | `UserPromptSubmit` | commit/push/PR/ship mentioned → prepends "run `/ship` first". Opt out: `skip gate`. |
| `writer-guard.py` | `PreToolUse` (`Edit\|Write\|MultiEdit`) | **BLOCKS** (exit 2) unauthorized writes to `.claude/specs/`, `.claude/pipeline/`, `docs/test-plans/`. Logs to `~/.claude/audit/writer-violations.jsonl`. |
| `spec-archive.py` | `PostToolUse` (`Edit\|Write\|MultiEdit`) | When `.spec.vN.md` (N≥2) is written, moves older versions to `.claude/specs/archive/`. |

## 4.5 Usage tracking (time & cost dashboard)

`usage-tracker/` turns your session transcripts into a self-contained HTML dashboard so you can see where time and money go — and tune the expensive flows. Zero npm deps: Node parses the transcripts, the system `sqlite3` CLI stores/queries, charts are hand-rolled SVG (no network/CDN).

```bash
~/.claude/usage-tracker/track.sh --open   # ingest all sessions + rebuild dashboard + open it
```

It reads `~/.claude/projects/**.jsonl` (every assistant turn's token usage, model, timestamp, `attributionSkill`, branch) and surfaces: notional cost, active time (idle gaps capped at 5 min so resumed-session spans don't inflate it), a daily cost trend with an active-hours overlay, cost by model, **cost by flow/skill with cost-per-turn** (the pipeline-tuning view), cache efficiency, cost by project, and a sortable per-session task table.

> **Money is notional list-API pricing** (editable `usage-tracker/pricing.json`) — an *equivalent cost* for comparing flows, not your subscription bill. The generated `usage.sqlite` / `dashboard.html` embed prompt text + paths and are gitignored. Full docs: [usage-tracker/README.md](usage-tracker/README.md).

## 5. Reference card

**Slash commands** (`commands/`):

| Command | Purpose |
|---------|---------|
| `/classify` | Declare the change class up front. |
| `/discovery` | Pre-architect interview to clarify a rough idea. |
| `/architect` | Design → SPEC (auto-interviews via Pass 0.5 if ambiguous). |
| `/implement [slug]` | Execute the SPEC task-by-task. |
| `/review` | Adversarial red-team branch review. |
| `/preflight` | Run the lint/typecheck/test gate. |
| `/ship` | Compose `/review` + `/preflight` + commit prompt. |
| `/test-plan` | Manual QA plan (opt-in). |
| `/epic-start [--autopilot]`, `/epic-continue`, `/epic-status`, `/approve-spec`, `/epic-ship`, `/epic-retro` | Epic-class only. |

**Agents** (`agents/`):

| Agent | Owns | When |
|-------|------|------|
| `frontend-architect` | `.claude/specs/` (incl. `## PR plan`) | Feature + epic |
| `feature-implementer` | production code | Feature + epic |
| `adversarial-frontend-reviewer` | findings | Feature + epic |
| `figma-design-implementer` | design-context block | When Figma URL provided |
| `manual-test-planner` | `docs/test-plans/` | Opt-in |
| `pipeline-orchestrator` | `.claude/pipeline/` | Epic only |

## 6. Common scenarios

- **Started trivial, grew mid-flight.** Stop, reclassify (`/classify`), `/architect` from here. §0 mandates reclassification, not improvisation.
- **Pure static UI from Figma.** After `@figma-design-implementer`, implement directly from the design context; skip the architect.
- **Reviewer said `Request changes`/`Block`.** Don't ship. Address findings; two consecutive failures on the same issue → hard stop, fix root cause or amend the SPEC.
- **Skip the gate for one commit.** Include `skip gate` in your commit prompt.
- **Autopilot launched on small work.** The orchestrator self-detects and routes you to the lighter path; if not, invoke commands directly.

## 7. Troubleshooting

- **Writer-guard blocked a legitimate edit to a global template.** The guard matches the literal path `.claude/specs/` or `.claude/pipeline/`. To maintain the *global* templates, edit them at their canonical dotfiles path (`~/dotfiles/claude/specs/…`, `~/dotfiles/claude/pipeline/…`) — that path has no `.claude/specs/` substring, so the guard (which protects *project* artifacts) doesn't fire. Project-spec/pipeline writes stay restricted to their owning agent. Audit log: `~/.claude/audit/writer-violations.jsonl`.
- **Push step prompts / 403.** Add the git/gh rules to `settings.json` via `/permissions`. For a personal repo behind a work GitHub login, authenticate with the right account (e.g. embed the username in the remote URL so git prompts for that account's PAT).
- **`--no-verify` refused.** Expected unless a full preflight PASS is recorded for the current HEAD and `.husky/` is a subset of preflight. Let the hooks run.
- **Preflight "no recognized scripts".** `package.json` lacks `lint-staged`/`lint`/`compile-ts`|`typecheck`|`tsc`/`test`. Add what you have or edit `scripts/preflight.sh`'s gate detection.
- **Hook not firing.** Check `settings.json` hook wiring, that the script is executable (`chmod +x`), and `python3` is on `$PATH`. Use `claude --debug`.

## 8. One-page mental model

```
TICKET / IDEA
   ├─ trivial?  → main agent + /preflight                                  → commit
   ├─ feature?  → ticket-refinement → (/discovery?) → /architect → /implement
   │             → /ship (/review + /preflight)                            → commit
   └─ epic?     → /epic-start [--autopilot] → … → /approve-spec → … 
                 → /epic-ship (push + PR, pr_open hard stop) → merge → /epic-retro
```

Three classes, three lanes. Pick the lightest that fits; escalate only when reality forces it.
