# dotfiles

Personal configuration, versioned. Tool-agnostic: each top-level directory is one tool module symlinked into its target location.

> **Opinionated.** The Cursor module is shaped around **client-side React SPAs and React Native**, **spec-driven development** (`frontend-architect` → `feature-implementer` → `adversarial-frontend-reviewer` → `preflight.sh`), and a **change-class routing model** (`trivial` / `feature` / `epic` — see `cursor/rules/agent-constitution.mdc` §0). The multi-tracker `ticket-refinement` skill handles Linear, Jira, ClickUp, GitHub/GitLab Issues, and Shortcut. Adapt the agents and rules to your stack before adopting wholesale.

Licensed [MIT](./LICENSE).

## Modules

Each module is documented in its own README. The global README (this file) stays tool-agnostic; module specifics live with the module.

| Module | Target | Guide | What it is |
|--------|--------|-------|------------|
| `claude/` | `~/.claude/` | [claude/README.md](./claude/README.md) | **Claude Code** agent factory (actively maintained) — slash commands, subagents, skills, hooks. |
| `cursor/` | `~/.cursor/` | [cursor/README.md](./cursor/README.md) | **Cursor** port of the same model, using Cursor-native agents/rules/hooks. |

Both modules implement the same opinionated, spec-driven, change-class-routed workflow; see their READMEs for the slash commands / agent invocations and walkthroughs.

## Layout

```
~/dotfiles/
├── README.md           # this file — tool-agnostic
├── install.sh          # tool-agnostic symlink installer
├── .gitignore
├── LICENSE
├── claude/             # tool module -> ~/.claude/   (see claude/README.md)
│   ├── README.md
│   ├── CLAUDE.md       # agent constitution (§0 routing by change class)
│   ├── AGENTS.md
│   ├── commands/       # slash commands (/architect, /implement, /ship, /epic-*, …)
│   ├── agents/         # 6 subagents (architect, implementer, reviewer, figma, test-planner, orchestrator)
│   ├── skills/         # portable knowledge: ticket-refinement + 7 React/RN skills
│   ├── scripts/        # preflight.sh (two-tier gate), epic-resume.sh (headless resume)
│   ├── specs/          # global SPEC template + module specs (project specs live per-project)
│   ├── pipeline/       # state + retro templates (epic-class only)
│   ├── usage-tracker/  # time & cost dashboard for sessions (track.sh -> dashboard.html)
│   ├── settings.json   # permissions + hook wiring
│   └── models.yaml     # central role→model registry
└── cursor/             # tool module -> ~/.cursor/   (see cursor/README.md)
    ├── README.md
    ├── AGENTS.md
    ├── agents/ rules/ specs/ skills/ scripts/ pipeline/ hooks/ hooks.json models.yaml
```

Future tools slot in as sibling directories — `zsh/`, `git/`, etc. — and `install.sh` picks them up automatically.

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

## What's intentionally NOT versioned

Only the curated config in each module is committed. Per `.gitignore`, the following are kept out across tools:

- Anything that may hold secrets: `mcp.json`, `.credentials*`, tokens, `.env*`.
- Personal history: `chats/`, `prompt_history.json`, `projects/` (per-project transcripts, terminals, agent notes), `sessions/`, `history`.
- Tool-managed caches/state: `extensions/`, `plugins/`, `skills-cursor/`, `telemetry/`, `usage-data/`, `tasks/`, `statsig*`, `*.bak.*`, `.DS_Store`.

If you later decide to version something that may hold secrets (e.g. `mcp.json`), strip secrets first.

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
