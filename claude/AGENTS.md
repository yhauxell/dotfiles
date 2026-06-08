# Claude Code Agentic SDLC

This setup provides a small set of **user-level Claude Code subagents**, **slash commands**, **skills**, and **hooks** for frontend (React SPA / React Native) work. The system is opt-in by change class — see `CLAUDE.md` §0 for routing.

These live in `~/.claude/` so they apply **globally across projects**.

## Routing by change class

Before invoking anything, decide the change class. This is the single most important decision in the pipeline.

| Class | Heuristic | What you use |
|-------|-----------|--------------|
| **`trivial`** | One file, no new user-visible behavior (copy tweak, typo, dep bump). | Main agent edits directly. `/preflight` before commit. No subagents, no SPEC. |
| **`feature`** | New user-visible flow OR change touches ≥2 of {component, store, api, route}. | `ticket-refinement` skill → (optional) `figma-design-implementer` → `/architect` → `/implement` → `/review` → `/preflight` (or just `/ship`). Direct invocation; **no orchestrator**. |
| **`epic`** | Multi-feature or multi-session. Worth tracking state. | Same agents, driven by `pipeline-orchestrator` via `/epic-start` etc. |

Default to the lightest class that fits. Over-classifying burns Opus rentals on trivial work.

## Subagents (6 total)

Stored in `~/.claude/agents/<name>.md` with Claude Code frontmatter (`name`, `description`, `tools`, `model`).

- **`frontend-architect`** (core, slash command: `/architect`)
  - **Purpose**: Designs new features end-to-end and emits a strict, machine-friendly **SPEC artifact** for spec-driven development. Pinned to `claude-opus-4-7` for reasoning depth.
  - **Owns**: `.claude/specs/**` (only agent allowed to write here — enforced by writer-guard).
  - **Outputs**: (1) architectural plan in chat, (2) SPEC at `.claude/specs/<slug>.spec.md`. Specs are append-only — bumped to `*.spec.v2.md`, `*.spec.v3.md`. Older versions auto-archived by `spec-archive.py`.

- **`feature-implementer`** (core, slash command: `/implement`)
  - **Purpose**: Executes the SPEC task-by-task. Parses `.claude/specs/<slug>.spec.md`, runs each task's `verify_commands`, **stops** when reality contradicts the SPEC. Pinned to `claude-sonnet-4-6`.
  - **Stop conditions**: draft SPEC, invalid file/donor path, contract collision, scope expansion outside `## File manifest`, missing design decision, two consecutive verify failures on the same root cause, skill/rule/SPEC conflict, reality contradicting the SPEC.

- **`adversarial-frontend-reviewer`** (core, slash command: `/review`)
  - **Purpose**: Aggressive, red-team code review of the current branch. Multi-pass adversarial sweeps over correctness, hooks, type safety, state/async, performance, accessibility, security, styling, tests, and architectural drift. Outputs severity-ranked, evidence-backed findings (`file:line` + concrete fixes). Pinned to `claude-opus-4-7`.
  - **Read-only**: `tools:` excludes Edit/Write; the writer-guard is a second line of defense.

- **`figma-design-implementer`** (situational, no dedicated slash command — invoke directly with `@figma-design-implementer`)
  - **Purpose**: Design intake. Fetches a Figma node and emits a structured **Design context** block — token/component/icon mapping, visual states, design-driven a11y, design-driven constraints, open questions for the architect. Uses the Figma MCP tools (`get_design_context`, `get_metadata`, `get_variable_defs`, `get_screenshot`).
  - **Read-only** (no Edit/Write tools).

- **`manual-test-planner`** (opt-in, slash command: `/test-plan`)
  - **Purpose**: Manual QA specialist. Reads the current branch's diff against its base and produces a simple manual test plan at `docs/test-plans/<branch-slug>.md`.
  - **Owns**: `docs/test-plans/**` (only agent allowed to write here).
  - **Opt-in only**: the Cursor module's `subagentStop` auto-chain has NOT been ported. This agent runs only when you ask for it.

- **`pipeline-orchestrator`** (opt-in — `epic` class only, slash commands: `/epic-start`, `/epic-continue`, `/epic-status`, `/approve-spec`)
  - **Purpose**: L3 conductor that tracks pipeline progress in `.claude/pipeline/<slug>.state.yaml`, launches one downstream subagent per step, and stops at human checkpoints (SPEC approval, ship). For `trivial` and `feature` classes, do not invoke it.
  - **Owns**: `.claude/pipeline/**` (only agent allowed to write here).

## Slash commands

Stored in `~/.claude/commands/<name>.md` with Claude Code frontmatter (`description`, `allowed-tools`, `argument-hint`). The slash-command UX is the **default** way to drive the pipeline; direct agent invocation (`@agent-name`) is the fallback.

| Command | Purpose | Spawns |
|---------|---------|--------|
| `/classify $ARGS` | Declare change class up front. | (none — main agent reasoning) |
| `/discovery $ARGS` | Pre-architect interview to clarify a rough idea before any design. Emits a Discovery brief ready to paste into `/architect`. | (none — runs in main thread as an interview) |
| `/architect $ARGS` | Design feature → write SPEC. Pass 0.5 auto-interviews you if input is ambiguous. | `frontend-architect` via Task |
| `/implement [slug]` | Execute SPEC task-by-task. | `feature-implementer` via Task |
| `/review` | Adversarial branch review. | `adversarial-frontend-reviewer` via Task |
| `/preflight` | Run lint/typecheck/test gate. | `~/.claude/scripts/preflight.sh` (Bash) |
| `/ship` | Compose `/review` + `/preflight` + commit prompt. | reviewer + script |
| `/test-plan` | Generate manual QA plan. | `manual-test-planner` via Task |
| `/epic-start [--autopilot] <slug>` | Begin epic; create state YAML. `--autopilot` chains non-gate stages. | `pipeline-orchestrator` via Task |
| `/epic-continue` | Advance epic by one stage (or to next hard gate if autopilot). | `pipeline-orchestrator` via Task |
| `/epic-status` | Print epic dashboard (inline, no model rental). | (direct Read + Bash) |
| `/approve-spec` | Approve architect's SPEC. | `pipeline-orchestrator` via Task |
| `/epic-ship` | Push branch + open PR (from `ready_to_ship`); hard-stops at `pr_open`. | `pipeline-orchestrator` via Task |
| `/epic-retro` | Write `.claude/pipeline/<slug>.retro.md` after merge. | `pipeline-orchestrator` via Task |

## Discovery / clarification patterns

The pipeline has **three discovery layers**, ordered from broad to narrow. Each layer's output is the next layer's input. Skipping layers is fine when the situation allows; doubling up is wasteful.

```
plan mode  (built-in Claude Code)   → "is this even the right thing to build?"
   ↓
/discovery <vague idea>             → "what specifically are we building?"
   ↓
/architect <story or brief>         → "here's the design contract"
   │   (if ambiguous, Pass 0.5 interview kicks in and the architect STOPS
   │    until you re-invoke with answers folded in)
   ↓
/implement <slug>                   → execute
```

### When to use each entry point

| Situation | Use |
|---|---|
| The idea is fully formed; you know what you want built. | Go straight to `/architect`. |
| The idea is rough; you want to be interviewed to clarify scope, constraints, edge cases. | `/discovery` first → paste its Discovery brief into `/architect`. |
| You're not yet sure if this is one feature or three, or want to compare 2–3 fundamentally different approaches. | **Plan mode**. When the plan is approved, pass it to `/architect` as input. |
| You ran straight to `/architect` but the input was ambiguous. | The architect's **Pass 0.5 interview gate** kicks in automatically — it surfaces 3–5 clarifying questions and STOPS without writing the SPEC. Answer, re-invoke `/architect` with the answers folded in. |
| You're in plan mode already and want to lock in the design. | Exit plan mode, then `/architect` with the approved plan as input. The architect treats the plan as authoritative and skips re-litigating decisions. |

### Plan mode + architect — complementary, not duplicative

- **Plan mode** (built into Claude Code) is for *socratic exploration* — should we build this at all, and roughly how? Enforces read-only tools. Has built-in `AskUserQuestion` and explicit `ExitPlanMode` approval. Output: a markdown plan file for human approval.
- **`/architect`** is for *committing* to a design that downstream agents can execute. Output: a contract-grade SPEC for `feature-implementer` to parse and execute.

Plan mode operates above the pipeline; the architect operates inside it. They share the codebase recon idiom but consume / produce different artifacts. When using both:

1. Plan mode produces a plan file (e.g. `~/.claude/plans/feat-foo.md`).
2. Pass the plan to the architect: `/architect <description of feature, with reference to @~/.claude/plans/feat-foo.md as approved context>`.
3. Architect treats the plan as authoritative → Pass 0.5 will likely say "no clarifying questions; proceeding to design" because the plan already covered them → emits the SPEC.

### `/discovery` — the lightweight interview

`/discovery` is **lighter than plan mode** (no read-only enforcement, no formal approval gate) and **lighter than `/architect` Pass 0.5** (no codebase recon, no commitment to producing a SPEC — just an interview).

Use it when you want to think out loud with structure but plan mode feels heavyweight. Typical session:

```
You: "/discovery I want to add some kind of notifications panel to the dashboard"

Claude (acting as interviewer):
  "Restating: a notifications panel on the dashboard that surfaces ___ to ___ users.
   Did I get that right?

   Phase A — Outcome (4 questions):
   1. Who is this for? (admin / end-user / both)
   2. What kinds of notifications? (system / user-generated / mix)
   3. Does it need real-time push or is poll-on-load enough?
   4. What does 'shipped' look like in one sentence?"

You: <answers>

Claude: <next batch — phase B, scope and surface>
   ... and so on for 2–4 batches.

Claude (after enough is captured):
  "## Discovery brief
   <structured block per the template>"

You: "/architect <paste the discovery brief>"
```

The Discovery brief format includes: Outcome, Scope and surface, Hard constraints, Trade-off preferences, Edge cases to design for, Open questions for the architect, Suggested next step (including which `change_class`).

### `/architect` Pass 0.5 — the safety net

Even if you go straight to `/architect`, the architect now runs a **clarification gate** between recon (Pass 0) and framing (Pass 1). If it finds consequential ambiguity in your input, it emits 3–5 questions and STOPS without writing the SPEC. You answer in chat, re-invoke `/architect` with the answers folded in, and the architect proceeds with confidence.

This catches the "I thought I knew what I wanted, but the architect surfaced an edge case I hadn't considered" case — making the SPEC less confidently-wrong.

What Pass 0.5 asks about (in priority order):
1. **"Done" definition** — observable outcome
2. **Hard constraints** — performance, deadline, compliance, parity
3. **Scope boundaries** — what's explicitly out
4. **Trade-off preferences** — when defaults conflict
5. **Edge cases with large blast radius** — empty/error/concurrency/etc.

Each question includes "Default if you say 'use your judgment': <X>" so you can unblock with a one-line "use your judgment on all" reply when you genuinely don't have a preference.

## Skills (cross-project knowledge base)

Platform-specific engineering knowledge lives in **portable skills** at `~/.claude/skills/`, not inline in agent prompts. Agents load the relevant skills during their Pass 0 (after stack detection) and apply them as the canonical reference.

| Skill | What it covers |
|---|---|
| `ticket-refinement` | Refine raw tickets into Gherkin AC, impacted areas, edge cases. Tracker-agnostic. Applied by the main agent on every ticket input. |
| `react-spa-architecture` | SPA routing, code splitting, error boundaries, URL-as-state, route-level auth gating, anti-patterns. |
| `react-native-architecture` | List virtualization, Reanimated/worklets, platform files, navigation lifecycle, image perf, deep linking, Hermes/JSI, AppState, memory cleanup. |
| `react-state-and-async` | Source-of-truth boundaries (server vs client vs URL vs form), cancellation, race conditions, optimistic updates, error model, persistence/migration. |
| `react-performance` | Memoization, virtualization, code splitting, bundle hygiene, render budgets, concurrent rendering, animation budget. |
| `react-accessibility` | Roles/labels, focus, touch targets, dynamic type, reduced motion, screen reader paths — for both web SPA and RN. |
| `react-testing-discipline` | Behavior > implementation, RTL/RNTL, redux-saga-test-plan, snapshot policy, mocking at boundaries, async assertions. |
| `react-typescript-discipline` | Assertion hierarchy, the `as any` ban, discriminated unions, branded types, runtime validation, error model, public-API barrels. |

**Loading rules** (followed by both `frontend-architect` and `adversarial-frontend-reviewer`):

- After stack detection, load architecture skills matching the stack: `react-spa-architecture` (if SPA), `react-native-architecture` (if RN), or both.
- Always load `react-state-and-async`, `react-performance`, `react-accessibility`, `react-testing-discipline`, `react-typescript-discipline` when the diff/feature touches their concern.
- **Conflict resolution**: project rules override skills. Skills override the agent prompt's inline summary. The agent prompt drives role and workflow; the skills provide the engineering content.

## Scripts

- **`~/.claude/scripts/preflight.sh`** — detects package manager (pnpm > yarn > npm), runs the available gate scripts (`lint-staged`, `lint`, `compile-ts`/`typecheck`/`tsc`, `test`), prints a summary, exits 0 on PASS / 1 on FAIL. Flags: `--keep-going`, `--staged-only`, `--affected[=<base>]`, `--base=<ref>`, `--shard=<i/N>`, `-h`.
  - Invoked by `/preflight`, `/ship`, and inside `feature-implementer`'s Pass 2.
  - **Two-tier checks**: `--affected` is the inner-loop fast path — lint + unit tests run only on files changed vs the base ref (`jest --findRelatedTests`), with `--maxWorkers=50%` and optional jest-native `--shard`. **Typecheck always runs full** (tsc is whole-program). Affected mode is NOT authoritative: it can miss transitive breakage, so the **full run is the pre-merge / ship gate**. The orchestrator uses `--affected` while implementing and the full run before `ready_to_ship`.

## Model registry

Each agent declares a `model:` field in its frontmatter using Claude Code's tier aliases (`opus`, `sonnet`, `haiku`). These auto-resolve to Anthropic's current top model in each tier, so the pipeline picks up new releases without per-agent edits. A semantic `model_role:` comment is kept for informational symmetry with the Cursor module.

| Agent | Role | `model:` alias | Resolves to (May 2026) |
|---|---|---|---|
| `frontend-architect` | `architect` | `opus` | claude-opus-4-7 (NextOpus moving forward) |
| `feature-implementer` | `implementer` | `sonnet` | claude-sonnet-4-6 |
| `adversarial-frontend-reviewer` | `reviewer` | `opus` | claude-opus-4-7 |
| `figma-design-implementer` | `visual` | `sonnet` | claude-sonnet-4-6 (with Figma MCP tools) |
| `manual-test-planner` | `writer` | `sonnet` | claude-sonnet-4-6 |
| `pipeline-orchestrator` | `conductor` | `sonnet` | claude-sonnet-4-6 |

**Pinning**: if you need reproducibility, replace the alias with a specific slug (e.g. `claude-opus-4-7`, `claude-sonnet-4-6`). Available slugs are listed at https://docs.claude.com/en/about-claude/models/overview. Anthropic's current latest is "NextOpus" (the next-gen Opus); aliases `opus`/`sonnet`/`haiku` always resolve to the current tier leader.

**Override**: edit the `model:` field in `~/.claude/agents/<name>.md`. Removing it falls back to the session's model. You can also use `model: inherit` to explicitly inherit from the parent.

**Central registry**: `~/.claude/models.yaml` (informational; documents the role→tier mapping). The `mechanical` role was retired — `ticket-refinement` is a skill and `preflight` is a script.

## End-to-end agent chain

For a `feature`-class change (no orchestrator, slash-command driven):

```
Ticket (Linear / Jira / ClickUp / GitHub / …) or raw idea
   │
   ├── (vague idea?) → plan mode OR /discovery → clarified brief
   │                                                            │
   ├── (ticket detected by hook?) → main agent applies `ticket-refinement` skill → refined story
   │                                                            │
   │                                                            ├── (if Figma URL) @figma-design-implementer
   │                                                            │      └── Design context block (handoff)
   │                                                            ▼
   │                                                       /architect <refined story OR discovery brief>
   │                                                            │
   │                                                            ├── Pass 0   — codebase recon
   │                                                            ├── Pass 0.5 — interview gate (ambiguity? STOP, ask user, wait)
   │                                                            ├── Pass 1-4 — frame → design → sequence → critique
   │                                                            ├── architectural plan (chat)
   │                                                            └── SPEC at .claude/specs/<slug>.spec.md
   │                                                            │
   │                                                            ▼
   │                                                       /implement <slug>  (executes SPEC task-by-task)
   │                                                            │
   │                                                            ▼
   │                                                       /ship  (composes /review + /preflight)
   │                                                            │
   │                                                            ▼
   │                                                          Commit / PR
```

For an `epic`-class change, swap the user-driven chain for `pipeline-orchestrator` driving the same agents with state YAML and `/approve-spec` checkpoint. The discovery layers (plan mode, `/discovery`, architect Pass 0.5) apply to epics too — invoke them *before* `/epic-start`, since the orchestrator's first stage assumes a refined brief is already in context.

The epic stage machine now runs past the gate to a PR and a retro:

```
spec_approved → implemented → reviewed → preflight_passed (FULL) → ready_to_ship
  → pushed (git push; --no-verify only if a full PASS is recorded for HEAD
            AND .husky/ hooks are a subset of what preflight ran)
  → pr_open  (gh pr create — HARD STOP: human reviews + merges)
  → merged   (user confirms) → retro (.claude/pipeline/<slug>.retro.md) → done
```

- **Autopilot** (`/epic-start --autopilot` or `enable autopilot`): the orchestrator chains non-gate stages automatically on `/epic-continue`, stopping ONLY at the two hard gates — `spec_draft` (→ `/approve-spec`) and `pr_open` (→ human merges). It never auto-merges and never skips review.
- **Retro self-improvement scope**: project-level `.claude/` fixes may be auto-applied; global `~/.claude/` changes are written as proposals for the human to apply.

**Non-overlap rule** (enforced by `writer-guard.py` PreToolUse hook — **BLOCKS** the write, not just shouts):

- `frontend-architect` is the only agent that writes to `.claude/specs/`.
- `feature-implementer` is the only agent that writes production code from a SPEC.
- `manual-test-planner` is the only agent that writes to `docs/test-plans/`.
- `pipeline-orchestrator` is the only agent that writes to `.claude/pipeline/`.
- `adversarial-frontend-reviewer` produces findings, not fixes.

Violations are logged to `~/.claude/audit/writer-violations.jsonl`.

## Hooks (4 total, wired in `~/.claude/settings.json`)

| Hook | Event | Behavior | Fail mode |
|------|-------|----------|-----------|
| `ticket-refiner-router.py` | `UserPromptSubmit` | Detects pasted tracker URLs (ClickUp, Linear, Jira, GitHub/GitLab Issues, Shortcut) or `PROJ-123` keys and prepends "apply `ticket-refinement` skill first" to the prompt. | open |
| `pipeline-gate-router.py` | `UserPromptSubmit` | When prompt mentions commit/push/PR/ship, prepends "run `/ship` first". Opt out: `skip gate`. | open |
| `writer-guard.py` | `PreToolUse` (`Edit\|Write\|MultiEdit`) | **BLOCKS** unauthorized writes to protected paths (`exit 2` + stderr message). Logs to `~/.claude/audit/writer-violations.jsonl`. Net-new capability vs. Cursor. | closed |
| `spec-archive.py` | `PostToolUse` (`Edit\|Write\|MultiEdit`) | When `.spec.vN.md` (N≥2) is written, moves older versions to `.claude/specs/archive/`. | open |

**Removed compared to the Cursor module**: the `subagentStop` auto-chain that invoked `manual-test-planner` after every reviewer run has NOT been ported. Test plans are opt-in via `/test-plan`.

## Spec-driven development

This setup is designed for **spec-driven development**:

1. **Design phase**: `frontend-architect` produces a SPEC at `.claude/specs/<slug>.spec.md` containing meta (with `design_source` when Figma context was provided), scope, contracts (TS types, API/route shapes), file manifest, and an ordered list of **atomic, verifiable tasks** (with `depends_on`, `files`, `action`, `acceptance`, `verify_commands`).
2. **Implementation phase**: `feature-implementer` parses the SPEC and executes tasks in order, running `verify_commands` between tasks and stopping to request a SPEC amendment if reality contradicts the plan.
3. **Review phase**: `adversarial-frontend-reviewer` red-teams the diff against the SPEC.
4. **Gate phase**: `~/.claude/scripts/preflight.sh` validates lint/types/tests before commit.

**Spec convention**:

- Path: `.claude/specs/<kebab-feature-slug>.spec.md` (project-local).
- Template: `~/.claude/specs/_TEMPLATE.spec.md` (global). A project may override by creating its own `.claude/specs/_TEMPLATE.spec.md`.
- Append-only: never overwrite. Bump filename suffix (`*.spec.v2.md`) and `version` in `## Meta`. The `spec-archive.py` hook auto-moves older versions into `.claude/specs/archive/`.
- The SPEC is the single source of truth for implementation.

**Governing rule**: `~/.claude/CLAUDE.md` (user-level memory; auto-loaded). Project-level `<project>/CLAUDE.md` or `<project>/.claude/CLAUDE.md` override on conflict.

## Mandatory pre-commit gate

For `feature` and `epic` classes, run **both** before any commit, in order:

1. **`/review`** — must produce `Approve` or `Approve with comments`.
2. **`/preflight`** — must report `PASS`.

Or simply `/ship`, which composes both in the right order.

For `trivial` class, only step 2.

If the user says "commit", "open a PR", or anything that implies finalizing the work, treat it as a request to run the appropriate gate first. The `pipeline-gate-router.py` hook will rewrite the prompt to remind you.

## Coexistence with the Cursor module

The Cursor module at `~/.cursor/` is unaffected by this setup. The two modules use separate per-project directories (`.claude/specs/` vs `.cursor/specs/`, `.claude/pipeline/` vs `.cursor/pipeline/`) and separate hooks. Pick one tool per project; do not run both pipelines on the same feature.

The `preflight.sh` script is duplicated (`~/.claude/scripts/preflight.sh` and `~/.cursor/scripts/preflight.sh`) — they are the same file but live in each module's scripts dir. Either invocation works.
