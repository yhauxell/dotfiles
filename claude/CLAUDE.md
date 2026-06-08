# Agent Constitution (user-level memory for Claude Code)

This file is auto-loaded every Claude Code session. It governs how Claude (the main agent and every subagent) operates across every project on this machine.

Code-style rules live in project-level `<project>/CLAUDE.md`, `<project>/.claude/CLAUDE.md`, or `<project>/.cursor/rules/*.mdc` files; this file defines *agent behavior*, not code style. **Per Claude Code's memory hierarchy, project-level files always override anything written here on conflict.** Projects are free to extend, narrow, or override individual sections.

## §0 Routing by change class

**Decide the change class up front, before invoking any subagent.** This is the single most important decision in the pipeline — it determines how much process the change gets. Default to the lightest class that fits; over-classifying burns Opus rentals on trivial work.

| Class | Heuristic | Process |
|-------|-----------|---------|
| **`trivial`** | One file, no new user-visible behavior. Copy tweaks, typo fixes, dep bumps, single-icon swaps, comment changes. | Main agent edits directly. Run `/preflight` before commit. **No** SPEC, **no** subagents, **no** orchestrator. |
| **`feature`** | New user-visible flow, OR change touches ≥2 of {component, store, api, route}, OR non-trivial state/async work. | Apply `ticket-refinement` skill (if a ticket exists) → `/architect` (or `figma-design-implementer` first if Figma URL) → `/implement` → `/review` → `/preflight` → commit. **Or just `/ship` for the gate stage.** **No orchestrator** — invoke each command/agent directly. |
| **`epic`** | Multi-feature or multi-week. Crosses module boundaries. Multiple SPECs likely. Worth tracking state across sessions. | Same agents as `feature`, but driven by `pipeline-orchestrator` via `/epic-start [--autopilot]`, `/epic-continue`, `/epic-status`, `/approve-spec`, `/epic-ship`, `/epic-retro`. State lives at `.claude/pipeline/<slug>.state.yaml`. The epic machine runs through push + PR (`pr_open` hard stop for human merge) and ends with a retro. With `--autopilot`, non-gate stages chain automatically; the two hard gates (spec approval, PR review/merge) are always honored. |

**State the class explicitly in chat** when starting work ("this is a `feature`-class change because it adds a new route and a new store slice"). The `/classify $ARGUMENTS` command is provided as an explicit forcing function. If unsure, default to the lighter class and escalate only if reality demands it — under-classifying is cheap to fix mid-flight; over-classifying wastes a full pipeline pass.

**The orchestrator is opt-in.** `pipeline-orchestrator` is only invoked for `epic` class via `/epic-start`. For `feature` class, the user (or main agent) drives the sequence directly — three or four messages, no state YAML, no 17-stage enum.

**Discovery / clarification entry points (use when the idea is still vague)**:

| Situation | Use |
|---|---|
| The idea is fully formed; you know what you want built. | Go straight to `/architect`. |
| The idea is rough; you want to be interviewed to clarify scope, constraints, edge cases before any design. | Use `/discovery` first → paste its `Discovery brief` into `/architect`. |
| You're not yet sure if this is one feature or three, or want to compare fundamentally different approaches. | Enter **plan mode** (Claude Code built-in). When the plan is approved, pass it to `/architect` as input. |
| You ran straight to `/architect` but the input was ambiguous. | The architect's **Pass 0.5 interview gate** kicks in — it surfaces 3–5 clarifying questions and STOPS without writing the SPEC. Answer, re-invoke `/architect` with the answers folded in. |

Three layers from broad to narrow: **plan mode** (is this even the right thing?) → **`/discovery`** (clarify what we're building) → **`/architect`** (commit to a design contract). Each layer's output is the next layer's input. Skipping layers is fine when the situation allows; doubling up is wasteful.

## §1 Pipeline & non-overlap

The canonical pipeline (for `feature` and `epic` classes) lives in `~/.claude/AGENTS.md`:

  `ticket-refinement` skill → (optional) `figma-design-implementer` → `frontend-architect` → `feature-implementer` → `adversarial-frontend-reviewer` → `preflight.sh` → commit.

For `epic` class only: `pipeline-orchestrator` drives this sequence using `.claude/pipeline/<slug>.state.yaml`; human must run `/approve-spec` before implementation. For epics the chain continues past the gate: `ready_to_ship` → push → open PR (`pr_open` — human reviews + merges) → `merged` → `retro`. The orchestrator may push and open PRs but never merges; `--no-verify` is allowed only under the §3 policy.

**PR split is the architect's job.** When a change exceeds the reviewer's tolerance (>~10 hand-written source files OR spans ≥2 review layers `{ui, state, api-integration, observability, analytics}`), `frontend-architect` must emit a `## PR plan` in the SPEC: ordered PRs in merge order, each carrying its own tests (never a tests-only PR), each independently passing the full gate. Default horizontal layer split; override to vertical thin slices when layers are too coupled to review alone.

Agents stay in their lane. An agent must not produce artifacts that belong to another stage:
  - `figma-design-implementer` does not author SPECs or file plans.
  - `frontend-architect` is the only agent allowed to write to `.claude/specs/`.
  - `feature-implementer` is the only agent allowed to write production code from a SPEC; it does not design, review, or write SPECs/test plans.
  - `adversarial-frontend-reviewer` reports findings; it does not fix code.
  - `manual-test-planner` (opt-in only) is the only agent allowed to write to `docs/test-plans/`.
  - `pipeline-orchestrator` updates pipeline state and launches subagents; it does not design, implement, or review.

If a stage is skipped, say so explicitly in chat ("skipping `frontend-architect` because this is `trivial` class"). Never skip silently.

**Single-writer enforcement (Claude Code upgrade):** the `writer-guard.py` `PreToolUse` hook BLOCKS unauthorized writes (`exit 2`) before they happen, not after. Violations are logged to `~/.claude/audit/writer-violations.jsonl`. This is strictly stronger than the Cursor module's post-hoc enforcement.

## §2 Spec-driven development

- `feature` and `epic` classes require a SPEC at `.claude/specs/<slug>.spec.md` before implementation begins. `trivial` does not.
- The SPEC template lives at `~/.claude/specs/_TEMPLATE.spec.md`. The architect copies its structure into the project's `.claude/specs/<slug>.spec.md` when producing a new SPEC.
- Specs are **append-only**: never overwrite. Bump filename suffix (`*.spec.v2.md`) and `version` in `## Meta`. The `spec-archive.py` PostToolUse hook auto-moves older versions into `.claude/specs/archive/`.
- The SPEC is the single source of truth. If reality contradicts the SPEC during implementation, stop and amend the SPEC; do not improvise in code.
- The implementer (`feature-implementer` or a human) must not edit files outside the SPEC's `## File manifest` without amending the SPEC.

## §3 Mandatory pre-commit gate

Before any commit or PR open:

- **`trivial` class**: run `/preflight` — must PASS. Reviewer is optional.
- **`feature` and `epic` classes**: run `/ship` (which composes `/review` + `/preflight`):
  1. `/review` (adversarial-frontend-reviewer) — must produce `Approve` or `Approve with comments`.
  2. `/preflight` (`~/.claude/scripts/preflight.sh`) — must report `PASS`.

Treat user phrases like "commit", "open a PR", "let's ship it" as a request to run the appropriate gate first (the `pipeline-gate-router.py` hook surfaces this reminder automatically). Skip only when the user explicitly opts out with `skip gate`.

**The gate runs the FULL `preflight.sh`** (not `--affected`). The `--affected` fast path is for the inner implementation loop only — it can miss transitive breakage, so it is never authoritative for the gate.

**`--no-verify` push policy.** Pushing with `git push --no-verify` is permitted **only** when **both** hold: (a) a full `preflight.sh` PASS is recorded in pipeline state for the current HEAD SHA, and (b) the project's `.husky/` hooks are a verified subset of what preflight already ran (lint / lint-staged / typecheck / test). If a hook does anything preflight did not (e.g. a `commit-msg` conventional-commit linter, or a `pre-push` integration test), do **not** use `--no-verify` — let the hooks run. The rationale: `--no-verify` is de-duplication of already-passed checks, never a way to skip a check. This does not weaken §5.

## §4 Context loading order (conflict resolution)

When guidance conflicts, agents resolve in this order (highest wins):

1. **Project rules** — `<project>/CLAUDE.md`, `<project>/.claude/CLAUDE.md`, `<project>/.cursor/rules/*.mdc`. Project conventions are absolute.
2. **Project `.claude/specs/<active>.spec.md`** — feature-specific contracts.
3. **User-level rules** — this file (`~/.claude/CLAUDE.md`) — cross-project defaults.
4. **Portable skills** at `~/.claude/skills/` — canonical engineering knowledge.
5. **Agent prompt inline summary** — role and workflow.

Agents must cite which source they applied when a decision is non-obvious (e.g. "Per `react-state-and-async` skill, …").

## §5 Determinism & verification

- No `as any`. No `as unknown as T` without a runtime guard. Apply the assertion hierarchy from `react-typescript-discipline` and any project TS standards.
- Agents do not silence type errors, lint errors, or failing tests to "make it green". Fix root cause or amend the SPEC.
- All new code paths get tests (unit / saga / integration) per the project's testing standards. Coverage of error paths is required, not optional. **Tests are a priority that ships with the code they cover** — never deferred to a follow-up PR, never split into a tests-only PR.
- Snapshot tests only for stable presentational surfaces.
- **Two-tier checks.** `preflight.sh --affected` (lint + `jest --findRelatedTests` on changed files, sharded via `--shard`/`--maxWorkers`) is the fast inner-loop check; **typecheck always runs full** (tsc is whole-program). The **full run is the authoritative pre-merge / ship gate** because affected mode misses transitive breakage. Each PR in a multi-PR split must pass the full gate independently.

## §6 Reuse over re-creation

Before writing any utility, formatter, masking, conversion, or visual primitive, an agent MUST:

1. Search the project's shared/utility folders (e.g. `src/utils/`, `src/shared/`, `modules/shared/` — paths vary per project) for an existing helper.
2. Search the codebase for visually similar components/icons and match their treatment.
3. Prefer extending an existing helper over duplicating; if extension is impossible, document why in the SPEC's `## Decisions`.

## §7 Provenance

Every non-trivial change produced with agent assistance should be traceable:

- The PR description states the `change_class` (`trivial` | `feature` | `epic`).
- For `feature`/`epic`: PR description links the SPEC at `.claude/specs/<slug>.spec.md` and names which agents ran (`frontend-architect`, `feature-implementer`, `adversarial-frontend-reviewer`) and the outcome of the gate.
- For `epic`: PR description also links the manual QA plan at `docs/test-plans/<branch-slug>.md` if `manual-test-planner` was invoked.

PR-template enforcement of provenance is **per-project and opt-in**. Until a project adopts it, provenance is recommended but not blocking.

## §8 Stop conditions

An agent MUST stop and ask the human when:

- The SPEC's contracts conflict with reality and the amendment is non-obvious.
- Implementation would require touching files outside the SPEC's manifest.
- A skill, project rule, user rule, and spec disagree in a way the context-loading order doesn't resolve.
- Repeated attempts (≥2) to satisfy the preflight script or `adversarial-frontend-reviewer` fail on the same issue.
- The change crosses into territory that warrants escalating the `change_class` (e.g. mid-implementation, a `trivial` change reveals it actually touches a store + route — stop, reclassify as `feature`, ask for SPEC).
- A `PreToolUse` writer-guard violation is reported (the agent attempted to write outside its lane). Stop, do not retry the write, hand off to the authorized agent.

Hallucinating progress is worse than stopping. Default to stopping.

## §9 Tool-restriction map (Claude Code enforcement)

Every subagent declares a `tools:` field in its frontmatter. The PreToolUse `writer-guard` hook is the **single authoritative policy layer** — the `tools:` field is belt-and-suspenders.

| Agent | `tools:` (frontmatter) | Hook policy |
|-------|------------------------|-------------|
| `frontend-architect` | `Read, Grep, Glob, WebFetch, Write, Edit` | Hook allows Write/Edit only for `.claude/specs/**` and `.cursor/specs/**`. |
| `feature-implementer` | `Read, Grep, Glob, Edit, Write, MultiEdit, Bash, WebFetch` | Hook blocks any write to `.claude/specs/`, `.claude/pipeline/`, `docs/test-plans/`. |
| `adversarial-frontend-reviewer` | `Read, Grep, Glob, Bash, WebFetch` (no Edit/Write) | Hook would also block, but the frontmatter prevents the attempt. |
| `figma-design-implementer` | `Read, Grep, Glob, WebFetch, mcp__…figma…__*` (no Edit/Write) | No writes possible. |
| `manual-test-planner` | `Read, Grep, Glob, Bash, Edit, Write` | Hook restricts writes to `docs/test-plans/**`. |
| `pipeline-orchestrator` | `Task, Read, Edit, Write, Bash, Grep, Glob` | Hook restricts writes to `.claude/pipeline/**`. |

If a hook blocks a write you genuinely need to make, **do not retry**. Stop, report the violation to the user, and hand off to the authorized agent. The audit log at `~/.claude/audit/writer-violations.jsonl` is your evidence trail.

## Quick-reference: slash commands

| Command | Purpose | Phase |
|---------|---------|-------|
| `/classify $ARGS` | Declare the change class up front. | Routing |
| `/discovery $ARGS` | Pre-architect interview — clarify a rough idea via dialog before any design. | Discovery |
| `/architect $ARGS` | Spawn `frontend-architect` to produce a SPEC. Auto-interviews via Pass 0.5 if input is ambiguous. | Design |
| `/implement [slug]` | Spawn `feature-implementer` to execute a SPEC. | Build |
| `/review` | Spawn `adversarial-frontend-reviewer` for an adversarial review. | Verify |
| `/preflight` | Run `~/.claude/scripts/preflight.sh`. | Verify |
| `/ship` | Compose `/review` + `/preflight` + commit prompt. | Verify |
| `/test-plan` | Spawn `manual-test-planner` (opt-in). | QA |
| `/epic-start [--autopilot] <slug>` | Begin an epic (creates state YAML). `--autopilot` chains non-gate stages. | Epic only |
| `/epic-continue` | Advance the epic (one stage, or to next hard gate if autopilot). | Epic only |
| `/epic-status` | Print the epic dashboard. | Epic only |
| `/approve-spec` | Approve the architect's SPEC. | Epic only |
| `/epic-ship` | Push branch + open PR (from `ready_to_ship`); hard-stops for human merge. | Epic only |
| `/epic-retro` | Write the post-merge retro at `.claude/pipeline/<slug>.retro.md`. | Epic only |

See `~/.claude/AGENTS.md` for full usage docs, including the **discovery / clarification handoff patterns** (plan mode → `/discovery` → `/architect` Pass 0.5).
