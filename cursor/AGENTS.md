## Cursor agents (recommended)

This setup provides a small set of **user-level Cursor subagents** for frontend (React SPA / React Native) work, plus skills, scripts, and hooks. The system is opt-in by change class — see the constitution's §0 for routing.

These live in `~/.cursor/` so they apply **globally across projects**.

### Routing by change class

Before invoking any subagent, decide the change class. This is the single most important decision in the pipeline.

| Class | Heuristic | What you use |
|-------|-----------|--------------|
| **`trivial`** | One file, no new user-visible behavior (copy tweak, typo, dep bump). | Main agent edits directly. Run `cursor/scripts/preflight.sh` before commit. No subagents, no SPEC. |
| **`feature`** | New user-visible flow OR change touches ≥2 of {component, store, api, route}. | `ticket-refinement` skill → (optional) `figma-design-implementer` → `frontend-architect` → `feature-implementer` → `adversarial-frontend-reviewer` → `preflight.sh`. Invoked directly; **no orchestrator**. |
| **`epic`** | Multi-feature or multi-session. Worth tracking state. | Same agents, driven by `pipeline-orchestrator` with `.cursor/pipeline/<slug>.state.yaml`. |

Default to the lightest class that fits. Over-classifying burns Opus rentals on trivial work.

### Subagents (5 total)

- **`figma-design-implementer`** (situational — only when a Figma URL is present)
  - **Purpose**: Design intake. Fetches a Figma node and emits a structured **Design context** block — token/component/icon mapping, visual states, design-driven a11y, design-driven constraints, open questions for the architect. Does **not** design architecture, state, data, routing, or testing.
  - **Location**: `~/.cursor/agents/figma-design-implementer.md`
  - **How to use**: Provide a Figma URL. The agent emits a `## Design context (handoff to frontend-architect)` block. Pass that block to `frontend-architect` to produce the SPEC. Exception: pure static UI changes (no state/data/navigation) can be implemented directly from the design context.

- **`frontend-architect`** (core)
  - **Purpose**: Senior frontend architect for React SPAs and React Native. Designs new features end-to-end and emits a strict, machine-friendly **SPEC artifact** for spec-driven development. Studies the codebase first; produces an opinionated, codebase-aware plan with explicit decisions, rejected alternatives, and an atomic task list a downstream coding subagent can execute task-by-task. Designs only — does not implement or review.
  - **Location**: `~/.cursor/agents/frontend-architect.md`
  - **Outputs**: (1) architectural plan in chat, (2) SPEC at `.cursor/specs/<slug>.spec.md`. Specs are append-only — bumped to `*.spec.v2.md`, `*.spec.v3.md` on changes. Older versions auto-archived by `spec-archive.py` hook.
  - **How to use**: Invoke at the start of a new feature. Provide the refined story (from `ticket-refinement` skill) and Figma context (if any). The architect returns a plan + a SPEC ready to be consumed by `feature-implementer`.

- **`feature-implementer`** (core)
  - **Purpose**: Senior frontend engineer that executes the SPEC. Parses `.cursor/specs/<slug>.spec.md`, runs tasks T1..Tn in dependency order, runs each task's `verify_commands` before moving on, and **stops** when reality contradicts the SPEC.
  - **Location**: `~/.cursor/agents/feature-implementer.md`
  - **How to use**: After the architect has produced a SPEC, say "implement `.cursor/specs/<slug>.spec.md`" (or "continue implementation" to resume).
  - **Stop conditions**: draft SPEC, invalid file/donor path, contract collision, scope expansion outside `## File manifest`, missing design decision, two consecutive verify failures on the same root cause, skill/rule/SPEC conflict, reality contradicting the SPEC.

- **`adversarial-frontend-reviewer`** (core)
  - **Purpose**: Aggressive, red-team code review of the current branch focused on React and React Native. Multi-pass adversarial sweeps over correctness, hooks, type safety, state/async, performance, accessibility, security, styling, tests, and architectural drift. Outputs severity-ranked, evidence-backed findings (`file:line` + concrete fixes).
  - **Location**: `~/.cursor/agents/adversarial-frontend-reviewer.md`
  - **How to use**: Ask Cursor to run `adversarial-frontend-reviewer` against the current branch (it auto-detects the base branch).

- **`manual-test-planner`** (opt-in only)
  - **Purpose**: Manual QA specialist. Reads the current branch's diff against its base and produces a simple manual test plan at `docs/test-plans/<branch-slug>.md`.
  - **Location**: `~/.cursor/agents/manual-test-planner.md`
  - **How to use**: Invoke explicitly when you want a human-readable QA plan for the change. **The auto-chain on `subagentStop` of the reviewer has been removed** — this agent runs only when you ask for it.

- **`pipeline-orchestrator`** (opt-in — `epic` class only)
  - **Purpose**: L3 conductor that tracks pipeline progress in `.cursor/pipeline/<slug>.state.yaml`, launches one downstream subagent per step, and stops at human checkpoints (SPEC approval, ship). For `trivial` and `feature` classes, do not invoke it.
  - **Location**: `~/.cursor/agents/pipeline-orchestrator.md`
  - **State template**: `~/.cursor/pipeline/_TEMPLATE.state.yaml`
  - **Commands**: `start epic for …`, `continue epic`, `epic status`, `approve spec`, `run gate`, `run until blocked`.

### Demoted from the subagent registry

These are NOT subagents anymore — they were rentals where there was no model decision to make.

- **`ticket-refinement`** (was `ticket-refiner` subagent → now a skill at `~/.cursor/skills/ticket-refinement/`). The main agent applies the skill directly.
- **`preflight`** (was `pr-preflight` subagent → now `cursor/scripts/preflight.sh`). The main agent invokes the script via Bash, then interprets PASS/FAIL.

### Skills (cross-project knowledge base)

Platform-specific engineering knowledge lives in **portable skills** at `~/.cursor/skills/`, not inline in agent prompts. Agents load the relevant skills during their Pass 0 (after stack detection) and apply them as the canonical reference.

| Skill | What it covers |
|---|---|
| `ticket-refinement` | Refine raw tickets into Gherkin AC, impacted areas, edge cases. Tracker-agnostic. |
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
- **Conflict resolution**: project `.cursor/rules/*.mdc` override skills (project conventions win). Skills override the agent prompt's inline summary. The agent prompt drives role and workflow; the skills provide the engineering content.

### Scripts

- **`cursor/scripts/preflight.sh`** — detects package manager (pnpm > yarn > npm), runs the available gate scripts (`lint-staged`, `lint`, `compile-ts`/`typecheck`/`tsc`, `test`), prints a summary, exits 0 on PASS / 1 on FAIL.
  - Flags: `--keep-going` (run all gates, report at end), `--staged-only` (just lint-staged for fast checks), `-h` (help).
  - Replaces the former `pr-preflight` subagent. The main agent runs it and interprets the output.

### Model selection per agent

Each agent declares **both** `model_role:` (semantic) and `model:` (concrete slug) in its frontmatter. The role is the source of truth.

| Agent | Role | Pinned model | Rationale |
|---|---|---|---|
| `figma-design-implementer` | `visual` | `gemini-3.1-pro` | Multimodal is the dominant skill; strongest vision in the lineup at workhorse price. |
| `frontend-architect` | `architect` | `claude-4.7-opus` | Architectural reasoning + decision quality matters most. Errors cascade into the SPEC. |
| `feature-implementer` | `implementer` | `gpt-5.3-codex` | Agentic coding + instruction-following. Less opinionated than Opus — a feature, since this agent must NOT re-design. |
| `adversarial-frontend-reviewer` | `reviewer` | `claude-4.7-opus` | Finding non-obvious bugs is pure reasoning depth. False negatives ship to prod. |
| `manual-test-planner` | `writer` | `claude-4.6-sonnet` | Writes for humans; needs behavioral reasoning and good prose at workhorse price. |
| `pipeline-orchestrator` | `conductor` | `claude-4.6-sonnet` | State machine + dispatch. |

**Override**: edit the `model:` field in `~/.cursor/agents/<name>.md`. Removing the field falls back to `inherit` (parent agent's model).

#### Model registry (central indirection)

- **Registry**: `~/.cursor/models.yaml` — maps each role to a `primary` and `fallback` slug, with rationale.
- **Roles**: `architect`, `reviewer`, `implementer`, `visual`, `writer`, `conductor`. (The `mechanical` role was retired when `ticket-refiner` and `pr-preflight` were demoted.)
- **When a model slug rolls**: edit one line in `models.yaml`, then update each agent's `model:` field to match (a Phase 3 resolver script will automate this).
- **Fallback**: if Cursor cannot find the pinned `model:`, the parent agent's model is inherited. The `fallback:` slug in `models.yaml` is the human-known safe alternative.

### End-to-end agent chain

For a `feature`-class change (no orchestrator, three or four messages):

```
Ticket (Linear / Jira / ClickUp / GitHub / …) or raw idea
   └── main agent applies the `ticket-refinement` skill  →  refined story
                                                            │
                                                            ├── (if Figma URL) figma-design-implementer
                                                            │      └── Design context block (handoff)
                                                            ▼
                                                      frontend-architect
                                                            ├── architectural plan (chat)
                                                            └── SPEC at .cursor/specs/<slug>.spec.md
                                                            │
                                                            ▼
                                                      feature-implementer  (executes SPEC task-by-task)
                                                            │
                                                            ▼
                                                      adversarial-frontend-reviewer  →  must Approve
                                                            │
                                                            ▼
                                                      cursor/scripts/preflight.sh  →  must PASS
                                                            │
                                                            ▼
                                                          Commit / PR
```

For an `epic`-class change, swap the user-driven chain for `pipeline-orchestrator` driving the same agents with state YAML and `approve spec` checkpoint.

**Non-overlap rule** (enforced by `writer-guard.py` hook):
- `frontend-architect` is the only agent that writes to `.cursor/specs/`.
- `feature-implementer` is the only agent that writes production code from a SPEC.
- `manual-test-planner` is the only agent that writes to `docs/test-plans/`.
- `pipeline-orchestrator` is the only agent that writes to `.cursor/pipeline/`.
- `adversarial-frontend-reviewer` produces findings, not fixes.

Violations are logged to `~/.cursor/audit/writer-violations.jsonl`.

### Spec-driven development

This setup is designed for **spec-driven development**:

1. **Design phase**: `frontend-architect` produces a SPEC at `.cursor/specs/<slug>.spec.md` containing meta (with `design_source` when Figma context was provided), scope, contracts (TS types, API/route shapes), file manifest, and an ordered list of **atomic, verifiable tasks** (with `depends_on`, `files`, `action`, `acceptance`, `verify_commands`).
2. **Implementation phase**: `feature-implementer` parses the SPEC and executes tasks in order, running `verify_commands` between tasks and stopping to request a SPEC amendment if reality contradicts the plan.
3. **Review phase**: `adversarial-frontend-reviewer` red-teams the diff against the SPEC.
4. **Gate phase**: `cursor/scripts/preflight.sh` validates lint/types/tests before commit.

**Spec convention**:
- Path: `.cursor/specs/<kebab-feature-slug>.spec.md` (project-local).
- Template: `~/.cursor/specs/_TEMPLATE.spec.md` (global). A project may override by creating its own `.cursor/specs/_TEMPLATE.spec.md`.
- Append-only: never overwrite an existing spec; bump the filename suffix and the `version` in `## Meta`. The `spec-archive.py` hook auto-moves older versions into `.cursor/specs/archive/`.
- The SPEC is the single source of truth for implementation.

**Governing rule**: `~/.cursor/rules/agent-constitution.mdc` (user-level, `alwaysApply: true`). Project-level `.cursor/rules/*.mdc` override it on conflict.

### Mandatory pre-commit gate

For `feature` and `epic` classes, run **both** before any commit, in order:

1. **`adversarial-frontend-reviewer`** — must produce `Approve` or `Approve with comments`.
2. **`cursor/scripts/preflight.sh`** — must report `PASS`.

For `trivial` class, only step 2.

If the user says "commit", "open a PR", or anything that implies finalizing the work, treat it as a request to run the appropriate gate first. The `pipeline-gate-router.py` hook will rewrite the prompt to remind you.

### User hooks

User hooks live at `~/.cursor/hooks.json` with scripts in `~/.cursor/hooks/`. Four hooks are configured:

#### 1. Ticket auto-routing — `beforeSubmitPrompt`
- **Script**: `~/.cursor/hooks/ticket-refiner-router.py`
- **Behavior**: detects pasted ticket URLs (ClickUp, Linear, Jira, GitHub/GitLab Issues, Shortcut) or `PROJ-123`-style ticket keys and rewrites the prompt to instruct the main agent to apply the `ticket-refinement` skill before doing anything else.
- **Fail mode**: open.

#### 2. Pre-ship gate reminder — `beforeSubmitPrompt`
- **Script**: `~/.cursor/hooks/pipeline-gate-router.py`
- **Behavior**: when the prompt mentions commit, push, open PR, or ship, rewrites to run `adversarial-frontend-reviewer` then `cursor/scripts/preflight.sh` first (or `pipeline-orchestrator` `run gate` for epics). Opt out with `skip gate` in the prompt.
- **Fail mode**: open.

#### 3. Writer-guard — `afterFileEdit`
- **Script**: `~/.cursor/hooks/writer-guard.py`
- **Behavior**: detects unauthorized writes to protected paths (`.cursor/specs/`, `.cursor/pipeline/`, `docs/test-plans/`) and emits a strong `followup_message` demanding the offending agent revert. Logs every violation to `~/.cursor/audit/writer-violations.jsonl`.
- **Fail mode**: closed — silent rule violations are exactly what we want to surface.

#### 4. Spec auto-archive — `afterFileEdit`
- **Script**: `~/.cursor/hooks/spec-archive.py`
- **Behavior**: when a versioned SPEC is written (`.cursor/specs/<slug>.spec.vN.md` with N ≥ 2), moves every older sibling for the same slug into `.cursor/specs/archive/`.
- **Fail mode**: open.

**Removed hook**: the `subagentStop` auto-chain that invoked `manual-test-planner` after every reviewer run has been removed. Test plans are now opt-in.

Notes:
- Hooks are loaded by Cursor from your `~/.cursor/` directory; Cursor watches `hooks.json` and reloads on save.
- All hook scripts are executable Python (`python3` on `$PATH`).
- Verify behavior in Cursor's **Hooks** settings tab or the **Hooks** output channel.
