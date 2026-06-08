# dotfiles

Personal configuration, versioned. Tool-agnostic: each top-level directory is one tool module symlinked into its target location.

> **Opinionated.** The Cursor module is shaped around **client-side React SPAs and React Native**, **spec-driven development** (`frontend-architect` → `feature-implementer` → `adversarial-frontend-reviewer` → `preflight.sh`), and a **change-class routing model** (`trivial` / `feature` / `epic` — see `cursor/rules/agent-constitution.mdc` §0). The multi-tracker `ticket-refinement` skill handles Linear, Jira, ClickUp, GitHub/GitLab Issues, and Shortcut. Adapt the agents and rules to your stack before adopting wholesale.

Licensed [MIT](./LICENSE).

## Layout

```
~/dotfiles/
├── README.md
├── install.sh          # tool-agnostic symlink installer
├── .gitignore
└── cursor/             # tool module -> ~/.cursor/
    ├── AGENTS.md
    ├── agents/         # 5 subagents (architect, implementer, reviewer, figma, test-planner) + opt-in orchestrator
    ├── rules/          # agent constitution (§0 routing by change class)
    ├── specs/          # global SPEC template (project specs live per-project)
    ├── skills/         # portable knowledge: ticket-refinement + 7 React/RN skills
    ├── scripts/        # preflight.sh (replaces former pr-preflight subagent)
    ├── pipeline/       # state YAML template (epic-class only)
    ├── hooks/          # ticket router, gate router, writer-guard, spec-archive
    ├── hooks.json
    └── models.yaml     # central role→model registry
```

Future tools slot in as sibling directories — `claude/`, `zsh/`, `git/`, etc. — and `install.sh` picks them up automatically.

## How `install.sh` works

For each tool module under `~/dotfiles/`:

1. **Target directory**: defaults to `$HOME/.<toolname>` (e.g. `cursor/` → `~/.cursor/`, `claude/` → `~/.claude/`). Override by creating `<tool>/.dotfile.conf` with a `TARGET="..."` line.
2. **Symlink every top-level item** inside the tool dir to the target.
3. **Idempotent**:
   - already-correct symlinks → left alone
   - wrong symlinks → relinked
   - real files/dirs → backed up to `<name>.bak.<timestamp>` then replaced

### Usage

```bash
./install.sh              # install all tools
./install.sh cursor       # install one tool
./install.sh cursor zsh   # install a subset
```

## What's intentionally NOT versioned (Cursor module)

- `mcp.json` — may contain API tokens.
- `chats/`, `prompt_history.json` — personal conversation history.
- `projects/` — per-project transcripts, terminals, agent notes.
- `extensions/`, `plugins/`, `skills-cursor/` — Cursor-managed installs/caches.
- `cli-config.json`, `ide_state.json`, `statsig-cache.json`, etc. — local state.

If you later decide to version `mcp.json`, strip secrets first.

## Adding a new tool module

### Example A: Claude (default target works)

Conventional location is `~/.claude/`, so the default rule applies:

```bash
mkdir -p ~/dotfiles/claude
mv ~/.claude/<artifact> ~/dotfiles/claude/<artifact>
./install.sh claude
```

No config file needed. `~/dotfiles/claude/<artifact>` is now symlinked at `~/.claude/<artifact>`.

### Example B: Top-level dotfiles (git, bash, zsh)

These tools want files at `$HOME` (e.g. `~/.gitconfig`, not `~/.git/.gitconfig`). Add a `.dotfile.conf` to override:

```bash
mkdir -p ~/dotfiles/git
cat > ~/dotfiles/git/.dotfile.conf <<'EOF'
TARGET="$HOME"
EOF
mv ~/.gitconfig ~/dotfiles/git/.gitconfig
./install.sh git
```

Result: `~/.gitconfig` is symlinked to `~/dotfiles/git/.gitconfig`.

### Example C: Tools with non-standard locations (VS Code, Sublime)

```bash
mkdir -p ~/dotfiles/vscode
cat > ~/dotfiles/vscode/.dotfile.conf <<'EOF'
TARGET="$HOME/Library/Application Support/Code/User"
EOF
```

## Install on a new machine

```bash
git clone <your-remote>:dotfiles ~/dotfiles
cd ~/dotfiles
./install.sh
```

---

# Using the Cursor module

The Cursor module is an **agent factory** for spec-driven frontend development. The pipeline is opt-in by **change class** — decide up front whether the work is `trivial`, `feature`, or `epic`, then use the matching amount of process.

Entry points:

- `cursor/AGENTS.md` — agent registry, model selection, hooks reference.
- `cursor/rules/agent-constitution.mdc` — user-level rule (§0 defines change-class routing).
- `cursor/skills/` — portable knowledge base agents load on demand.
- `cursor/scripts/preflight.sh` — the quality gate (replaces the former `pr-preflight` subagent).
- `cursor/specs/_TEMPLATE.spec.md` — global SPEC template. Real specs live per-project under `<project>/.cursor/specs/`.
- `cursor/models.yaml` — central role→model registry. Edit one line when a model slug rolls.

## 1. The only decision that matters: change class

Before touching anything, decide which class fits. State it explicitly in chat (e.g. *"this is a feature-class change because it adds a route + a store slice"*). Default to the lightest class that fits; escalate mid-flight if reality demands.

| Class | When | Process |
|-------|------|---------|
| **`trivial`** | One file, no new behavior | Main agent + `preflight.sh` |
| **`feature`** | New flow OR ≥2 of {component, store, api, route} | Architect → Implementer → Reviewer → `preflight.sh` |
| **`epic`** | Multi-week, multi-feature | `pipeline-orchestrator` drives the above with state YAML |

## 2a. Trivial walkthrough

Examples: typo, dep bump, CSS tweak, copy change.

```text
You: "Fix the typo in src/pages/Login.tsx:42 and bump react-query to ^5.50."
→ Main agent edits directly.

You: "Commit."
→ pipeline-gate-router hook prepends "run preflight first".
→ Main agent runs ./cursor/scripts/preflight.sh, reports PASS.
→ Commits.
```

No SPEC. No subagents. Two messages.

## 2b. Feature walkthrough (no orchestrator)

Examples: new screen, new API integration, new state slice.

```text
[1] You: "Implement PROJ-123: <paste ticket URL or text>"
    → ticket-refiner-router hook detects the key.
    → Main agent applies the `ticket-refinement` skill.
    → Refined story (Gherkin AC, edge cases) printed in chat.

[2] (Optional, only if Figma)
    You: "Use figma-design-implementer for <Figma URL>"
    → Returns a Design context block.

[3] You: "Use frontend-architect to design this from the refined story
         [and the design context]."
    → Architect writes .cursor/specs/<slug>.spec.md.
    → Read it. If gaps: ask for revisions → .spec.v2.md
      (spec-archive hook moves older versions to .cursor/specs/archive/).

[4] You: "Use feature-implementer to execute .cursor/specs/<slug>.spec.md"
    → Runs tasks T1..Tn, runs verify_commands between each, stops if
      reality contradicts the SPEC.

[5] You: "Use adversarial-frontend-reviewer on this branch"
    → Severity-ranked findings. Address them (re-invoke implementer or
      edit directly) and re-run if needed.

[6] You: "Commit"
    → gate-router hook prepends "run reviewer + preflight first".
    → Main agent confirms reviewer verdict was Approve.
    → Runs preflight.sh, reports PASS. Commits.
```

4–6 messages. No state file. No orchestrator.

## 2c. Epic walkthrough (orchestrator-driven)

Use only when work spans weeks or multiple feature slices and you need state across sessions.

```text
You: "start epic for PROJ-555: refactor checkout flow"
→ Creates .cursor/pipeline/proj-555.state.yaml.
→ Prints "Epic — proj-555" dashboard. Stops.

You: "continue epic"
→ Runs figma-design-implementer (if Figma URL) or frontend-architect.

You: "continue epic"
→ Architect writes SPEC, state → spec_draft. HARD STOP.

You: "approve spec"
→ checkpoints.spec_approved = true.

You: "continue epic"
→ Launches feature-implementer.

You: "run gate"
→ reviewer → preflight.sh in order.

You: "mark done"
```

Commit the state YAML for team visibility, or add `*.state.yaml` to `.gitignore` for local-only.

Resume a stale epic next week: open Cursor, type `epic status` for the dashboard.

## 3. What runs automatically (hooks)

You never invoke these — they fire on Cursor events.

| Hook | Fires on | Behavior |
|------|----------|----------|
| `ticket-refiner-router` | `beforeSubmitPrompt` | If prompt contains a tracker URL or `PROJ-123` key, prepends "apply ticket-refinement skill first." |
| `pipeline-gate-router` | `beforeSubmitPrompt` | If prompt mentions commit/push/PR/ship, prepends "run reviewer + preflight first." Opt out: `skip gate`. |
| `writer-guard` | `afterFileEdit` (failClosed) | If wrong agent edits `.cursor/specs/`, `.cursor/pipeline/`, or `docs/test-plans/`, demands revert and logs to `~/.cursor/audit/writer-violations.jsonl`. |
| `spec-archive` | `afterFileEdit` | When `.spec.vN.md` (N≥2) is written, moves older versions to `.cursor/specs/archive/`. |

## 4. Reference card

**Agents** (`~/.cursor/agents/`):

| Agent | Role | Owns | When |
|-------|------|------|------|
| `frontend-architect` | SPEC author | `.cursor/specs/` | Feature + epic |
| `feature-implementer` | SPEC executor | production code | Feature + epic |
| `adversarial-frontend-reviewer` | Red-team review | findings | Feature + epic |
| `figma-design-implementer` | Design intake | chat block | When Figma URL provided |
| `manual-test-planner` | Manual QA plan | `docs/test-plans/` | Opt-in only |
| `pipeline-orchestrator` | Conductor | `.cursor/pipeline/` | Epic only |

**Skills** (`~/.cursor/skills/`):

- `ticket-refinement` — applied by the main agent on every ticket input.
- 7 React/RN engineering skills (state, perf, a11y, testing, TS, SPA arch, RN arch) — agents auto-load these in Pass 0 based on stack and what the diff touches.

**Scripts** (`~/.cursor/scripts/`):

- `preflight.sh` — runs lint-staged, lint, typecheck, test. Flags:
  - `--keep-going` (run all gates, report at end)
  - `--staged-only` (fast check)
  - `-h` (help)

**Model registry** (`~/.cursor/models.yaml`):

- Roles: `architect`, `reviewer`, `implementer`, `visual`, `writer`, `conductor`.
- When a slug rolls: edit `models.yaml`'s `primary:`, then update the matching agent's `model:` field.

## 5. Common scenarios

**Started trivial, grew mid-flight.**
Stop. Say: *"this is actually feature-class — use frontend-architect from here."* The constitution §0 mandates reclassification, not improvisation.

**Pure static UI from Figma (no state/data/navigation).**
After `figma-design-implementer`, you can implement directly from the design context. Skip the architect.

**Reviewer verdict was `Request changes` or `Block`.**
Don't commit. Address findings (re-invoke implementer if scope grew, otherwise edit directly). Two consecutive failures on the same issue → hard stop, fix root cause or amend the SPEC.

**You want a manual test plan.**
Explicitly: *"use manual-test-planner for this branch."* Output lands at `docs/test-plans/<branch-slug>.md`. No longer auto-chained after the reviewer.

**Skip the gate for one commit (WIP, hotfix, etc.).**
Include `skip gate` anywhere in your commit prompt.

**Orchestrator launched on small work.**
It should self-detect and tell you to use the lighter path. If it doesn't, stop and invoke agents directly — feature-class is three messages, no orchestrator.

## 6. Troubleshooting

**Writer-guard fired on a legitimate edit.**
Check `~/.cursor/audit/writer-violations.jsonl`. If your agent was misidentified, the audit log shows the offending name. If the rule is genuinely wrong, edit `cursor/hooks/writer-guard.py`'s `POLICY` list.

**Hook script not running.**
Cursor → Hooks settings tab → Hooks output channel. Common causes: not executable (`chmod +x cursor/hooks/<script>.py`), wrong path in `hooks.json`, `python3` not on `$PATH`.

**Model slug 404 (silent fallback).**
Cursor falls back to the parent agent's model without warning. Detect via the model picker. Fix: edit `models.yaml`'s `primary:` to a working slug, then update the affected agent's `model:` field.

**SPEC version chaos.**
Active = highest-numbered `*.spec.vN.md` (or `.spec.md` if unversioned). Older versions live in `.cursor/specs/archive/`. If they don't, the archive hook either didn't fire or failed silently (it's `failClosed: false`). Re-run the architect or move files by hand.

**State YAML diverges from git.**
No built-in reconciliation yet (drift detection is deferred). Either trust the YAML or restart the epic. Treat it as a hint, not source of truth.

**Preflight fails with "no recognized scripts".**
Your `package.json` doesn't have any of: `lint-staged`, `lint`, `compile-ts`/`typecheck`/`tsc`, `test`. Add the ones you have, or edit `cursor/scripts/preflight.sh`'s gate detection.

## 7. One-page mental model

```
TICKET / IDEA
   │
   ├─ trivial?  →  main agent + preflight.sh                    → commit
   │
   ├─ feature?  →  ticket-refinement skill
   │               │
   │               ├─ (Figma?) → figma-design-implementer
   │               ▼
   │               frontend-architect    →  SPEC
   │               feature-implementer   →  code
   │               adversarial-reviewer  →  Approve
   │               preflight.sh          →  PASS
   │                                                            → commit
   │
   └─ epic?     →  pipeline-orchestrator drives all of feature-class
                   with state YAML and `approve spec` checkpoint
                                                                → commit
```

Three classes. Three lanes. Pick the lightest one that fits. Escalate only when reality forces it.
