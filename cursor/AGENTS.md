## Cursor agents (recommended)

This setup provides a set of **user-level Cursor subagents** that form a spec-driven development pipeline (Mission Definition → Generation → Verification), plus optional hooks that route tracker tickets to the refiner and chain the manual test planner after review.

These live in `~/.cursor/` so they apply **globally across projects**.

### Subagents

- **`ticket-refiner`**
  - **Purpose**: Turn a raw ticket / user story from any tracker (Linear, Jira, ClickUp, GitHub Issues, GitLab Issues, Shortcut, or a raw idea) into engineering-ready requirements: acceptance criteria (Gherkin), impacted areas, API/data impacts, and edge cases.
  - **Location**: `~/.cursor/agents/ticket-refiner.md`
  - **How to use**: Paste a ticket URL or ticket key (e.g. `PROJ-123`) and ask Cursor to refine it. The optional `beforeSubmitPrompt` hook will auto-route detected tickets.

- **`figma-design-implementer`**
  - **Purpose**: **Design intake.** Fetches a Figma node and emits a structured **Design context** block — token/component/icon mapping, visual states, design-driven a11y, design-driven constraints, and open questions for the architect. Does **not** design architecture, state, data, routing, or testing — it feeds `frontend-architect`, which writes the SPEC.
  - **Location**: `~/.cursor/agents/figma-design-implementer.md`
  - **How to use**: Provide a Figma URL. The agent emits a `## Design context (handoff to frontend-architect)` block. Pass that block to `frontend-architect` to produce the SPEC. Exception: pure static UI changes (no state/data/navigation) can be implemented directly from the design context without invoking the architect.

- **`pr-preflight`**
  - **Purpose**: Run the repo’s quality gates (mirrors Husky `pre-commit`/`pre-push`: `lint-staged`, `lint`, `compile-ts`, `test`) and summarize failures so CI/PR checks pass first try.
  - **Location**: `~/.cursor/agents/pr-preflight.md`
  - **How to use**: Ask Cursor to run `pr-preflight` before you commit/push or open a PR.
  - **Recommended workflow**: Run this **at the end of a work session** before concluding “everything is good to go”.

- **`adversarial-frontend-reviewer`**
  - **Purpose**: Aggressive, red-team code review of the current branch focused on React and React Native. Studies project architecture first (Pass 0), then runs multi-pass adversarial sweeps over correctness, hooks, type safety, state/async, performance, accessibility, security, styling, tests, and architectural drift. Outputs severity-ranked, evidence-backed findings (`file:line` + concrete fixes), not generic advice.
  - **Location**: `~/.cursor/agents/adversarial-frontend-reviewer.md`
  - **How to use**: Ask Cursor to run `adversarial-frontend-reviewer` against the current branch (it auto-detects the base branch).
  - **Auto-chains to**: `manual-test-planner` (via the `subagentStop` hook) — once the reviewer finishes, the parent agent is prompted to generate a manual QA test plan.

- **`manual-test-planner`**
  - **Purpose**: Manual QA specialist. Reads the current branch's diff against its base and produces a simple, easy-to-follow manual test plan (cases, edge cases, regression checks, cross-platform/a11y spot-checks) intended for a human tester. Outputs a markdown file at `docs/test-plans/<branch-slug>.md`. Plain language, behavior-focused — no implementation details.
  - **Location**: `~/.cursor/agents/manual-test-planner.md`
  - **How to use**: Either (a) auto-triggered by the hook on `subagentStop` of `adversarial-frontend-reviewer`, or (b) invoke explicitly: "run `manual-test-planner` for this branch".
  - **Output convention**: append-only — never overwrites an existing plan; bumps the `version` and adds a dated `Update` section + `Change log` entry.

- **`frontend-architect`**
  - **Purpose**: Senior frontend architect for React and React Native. Designs new features (or significant changes) end-to-end and emits a strict, machine-friendly **SPEC artifact** for spec-driven development. Covers module boundaries, component architecture, state/data/async strategy, routing, performance, a11y, security, telemetry, testing, rollout. Studies the codebase first, then produces an opinionated, codebase-aware plan with explicit decisions, rejected alternatives, and an atomic task list a downstream coding subagent can execute task-by-task. Designs only — does not implement or review.
  - **Location**: `~/.cursor/agents/frontend-architect.md`
  - **Outputs**:
    1. Architectural plan in chat (rationale, decisions, tradeoffs).
    2. SPEC file written to `.cursor/specs/<feature-slug>.spec.md` (the only file the agent writes). Specs are append-only — bumped to `*.spec.v2.md`, `*.spec.v3.md` on changes.
  - **How to use**: Invoke at the start of a new feature or when a non-trivial design decision is needed. Provide the ticket/spec/Figma; the agent returns a high-fidelity plan and a SPEC file ready to be consumed by `feature-implementer`.
  - **Recommended workflow**: Run `frontend-architect` **before** implementation begins → hand the SPEC to `feature-implementer` → before each commit run `adversarial-frontend-reviewer` + `pr-preflight` (see gate below).

- **`feature-implementer`**
  - **Purpose**: Senior frontend engineer that executes the SPEC produced by `frontend-architect`. Parses `.cursor/specs/<slug>.spec.md`, runs tasks T1..Tn in dependency order, runs each task's `verify_commands` before moving on, and **stops** when reality contradicts the SPEC. Does not make design decisions, does not write SPECs, does not review.
  - **Location**: `~/.cursor/agents/feature-implementer.md`
  - **How to use**: After `frontend-architect` has produced a SPEC, say "implement `.cursor/specs/<slug>.spec.md`" (or "continue implementation" to resume).
  - **Skill loading**: narrow by design — always loads `react-typescript-discipline` and `react-testing-discipline`; conditionally loads `react-state-and-async`, `react-performance`, `react-accessibility` when tasks touch their concern; **does not** load the architecture skills (those are the architect's domain).
  - **Stop conditions** (mandatory): draft SPEC, invalid file/donor path, contract collision, scope expansion outside `## File manifest`, missing design decision, two consecutive verify failures on the same root cause, skill/rule/SPEC conflict, reality contradicting the SPEC.

### Model selection per agent

Each agent's `model:` is pinned in its YAML frontmatter so it does not inherit the parent's model. The pin matches the agent's dominant cognitive load (reasoning depth vs agentic coding vs multimodal vs mechanical execution). Verify the exact slug in Cursor's model picker — slugs can vary by region/plan.

| Agent | Pinned model | Rationale |
|---|---|---|
| `ticket-refiner` | `composer-2` | Lightweight rewrite/structure task. Cheap + fast wins. |
| `figma-design-implementer` | `gemini-3.1-pro` | Multimodal is the dominant skill; Gemini 3 has the strongest vision in the lineup at workhorse price. |
| `frontend-architect` | `claude-4.7-opus` | Architectural reasoning + decision quality matters most. Errors here cascade into the SPEC and all downstream agents. Worth premium. |
| `feature-implementer` | `gpt-5.3-codex` | Agentic coding + instruction-following. Codex is trained for this. Less opinionated than Opus — a feature, since this agent must NOT re-design. |
| `adversarial-frontend-reviewer` | `claude-4.7-opus` | Finding non-obvious bugs is pure reasoning depth. False negatives ship to prod. |
| `pr-preflight` | `composer-2` | Mechanical: runs shell commands, summarizes failures. No creative work. |
| `manual-test-planner` | `claude-4.6-sonnet` | Writes for humans; needs behavioral reasoning and good prose. Sonnet is the strongest writer at workhorse price. |

**Override**: edit the `model:` field in `~/.cursor/agents/<name>.md`. Removing the field falls back to `inherit` (parent agent's model). For Opus/GPT-5.4+ pins, Max Mode must be enabled on the account.

### Portable skills (cross-project knowledge base)

Platform-specific engineering knowledge lives in **portable skills** at `~/.cursor/skills/`, not inline in agent prompts. Agents load the relevant skills during their Pass 0 (after stack detection) and apply them as the canonical reference. Agent prompts carry only summaries; the skill files are authoritative.

| Skill | What it covers |
|---|---|
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
- **Conflict resolution**: project `.cursor/rules/*.mdc` override skills (project conventions win). Skills override the agent prompt's inline summary (skills are authoritative). The agent prompt drives role and workflow; the skills provide the engineering content.

### End-to-end agent chain

The agents form a pipeline. Each one has a single, non-overlapping job:

```
Ticket (Linear / Jira / ClickUp / GitHub / …) or raw idea
   └── ticket-refiner  →  refined engineering story
                           │
                           ├── (if Figma URL) figma-design-implementer
                           │      └── Design context block (handoff)
                           ▼
                     frontend-architect
                           ├── architectural plan (chat)
                           └── SPEC at .cursor/specs/<slug>.spec.md
                           │
                           ▼
                     feature-implementer  (executes SPEC task-by-task; stops on contradiction)
                           │
                           ▼
                     adversarial-frontend-reviewer  →  must Approve
                           │
                           ▼
                     pr-preflight  →  must PASS
                           │
                           ▼
                         Commit / PR
```

**Non-overlap rule**: each agent stays in its lane.
- `ticket-refiner` produces requirements, not architecture.
- `figma-design-implementer` produces a design context block, not file plans / state design / Gherkin AC.
- `frontend-architect` produces architecture and the SPEC. It is the **only** agent that writes a SPEC file.
- `feature-implementer` executes the SPEC. It is the **only** agent that writes production code from a SPEC. It does not design, review, or write SPECs/test plans.
- `adversarial-frontend-reviewer` produces findings, not fixes.
- `pr-preflight` runs the quality gate, nothing else.

If a Figma URL is in the input, the canonical path is **figma-design-implementer → frontend-architect**, not architect alone. The architect treats the design context block as authoritative for the visual layer and folds it into the SPEC's `Pattern donors`, `Component tree`, `Constraints & non-functional requirements`, and `Open questions`. The SPEC's `## Meta` records the Figma source for traceability.

### Spec-driven development

This setup is designed for **spec-driven development**:

1. **Design phase**: `frontend-architect` produces a SPEC at `.cursor/specs/<slug>.spec.md` containing meta (with `design_source` when a Figma context was provided), scope, contracts (TS types, API/route shapes), file manifest, and an ordered list of **atomic, verifiable tasks** (with `depends_on`, `files`, `action`, `acceptance`, `verify_commands`).
2. **Implementation phase**: `feature-implementer` parses the SPEC and executes tasks in order, running `verify_commands` between tasks and stopping to request a SPEC amendment if reality contradicts the plan.
3. **Review phase**: `adversarial-frontend-reviewer` red-teams the diff against the SPEC.
4. **Gate phase**: `pr-preflight` validates lint/types/tests before commit.

**Spec convention**:
- Path: `.cursor/specs/<kebab-feature-slug>.spec.md` (project-local).
- Template: `~/.cursor/specs/_TEMPLATE.spec.md` (global). A project may override by creating its own `.cursor/specs/_TEMPLATE.spec.md`.
- Append-only: never overwrite an existing spec; bump the filename suffix and the `version` in `## Meta`.
- The SPEC is the single source of truth for implementation. Anything not in the SPEC is out of scope; ambiguity must be resolved by amending the SPEC, not by improvising in code.

**Governing rule**: `~/.cursor/rules/agent-constitution.mdc` (user-level, `alwaysApply: true`) defines the pipeline, gate, context-loading order, determinism, reuse, provenance, and stop conditions for every project on this machine. Project-level `.cursor/rules/*.mdc` override it on conflict.

### Mandatory pre-commit gate

**Always run BOTH of these before any commit, in this order — do not commit until both pass:**

1. **`adversarial-frontend-reviewer`** — must produce a verdict of `Approve` or `Approve with comments`. If the verdict is `Block` or `Request changes`, address findings (or consciously accept and document them) before continuing.
2. **`pr-preflight`** — must report `PASS` for `lint-staged`, `lint`, `compile-ts`, and `test`.

This ordering is intentional: the adversarial review may reveal changes that need to be made; running it before `pr-preflight` avoids burning time on lint/test cycles for code that still has correctness or architectural issues.

If the user says “commit”, “let’s commit”, “open a PR”, or anything that implies finalizing the work, treat it as a request to run this gate first. Do not skip either step unless the user explicitly opts out for the current commit.

### User hooks

User hooks live at `~/.cursor/hooks.json` with scripts in `~/.cursor/hooks/`. Two hooks are configured:

#### 1. Ticket auto-routing (optional)
- **Trigger**: `beforeSubmitPrompt` (matcher: `UserPromptSubmit`)
- **Script**: `~/.cursor/hooks/ticket-refiner-router.py`
- **Behavior**: best-effort prompt rewrite that routes pasted ticket URLs (ClickUp, Linear, Jira, GitHub/GitLab Issues, Shortcut) or `PROJ-123`-style ticket keys to the `ticket-refiner` subagent. Generic enough that most tracker URL patterns work.
- **Fail mode**: open — if prompt rewriting isn't supported in your Cursor version, the hook fails silently and you can still invoke `ticket-refiner` manually.

#### 2. Auto-trigger manual test plan after adversarial review
- **Trigger**: `subagentStop` (matcher: `^adversarial-frontend-reviewer$`)
- **Script**: `~/.cursor/hooks/manual-test-planner-trigger.py`
- **Behavior**: emits a `followup_message` instructing the parent agent to invoke `manual-test-planner` and save the plan to `docs/test-plans/<branch-slug>.md`.
- **`loop_limit`**: 1 — the hook fires once per review run; will not infinitely re-trigger.
- **Fail mode**: open — `failClosed: false`, so a hook error never blocks the parent workflow.
- **Opt-out**: tell Cursor "skip the manual test plan this time" or temporarily comment out the `subagentStop` block in `hooks.json`.

Notes:
- Hooks are loaded by Cursor from your `~/.cursor/` directory; Cursor watches `hooks.json` and reloads on save.
- All hook scripts are executable Python (`python3` on `$PATH`).
- Verify behavior in Cursor's **Hooks** settings tab or the **Hooks** output channel.

