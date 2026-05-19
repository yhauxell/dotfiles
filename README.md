# dotfiles

Personal configuration, versioned. Tool-agnostic: each top-level directory is one tool module symlinked into its target location.

> **Opinionated.** The Cursor module is shaped around **client-side React SPAs and React Native**, **spec-driven development** (`frontend-architect` → `feature-implementer` → `adversarial-frontend-reviewer` → `pr-preflight`), and a **multi-tracker ticket-refiner** (Linear, Jira, ClickUp, GitHub/GitLab Issues, Shortcut). Adapt the agents and rules to your stack before adopting wholesale.

Licensed [MIT](./LICENSE).

## Layout

```
~/dotfiles/
├── README.md
├── install.sh          # tool-agnostic symlink installer
├── .gitignore
└── cursor/             # tool module -> ~/.cursor/
    ├── AGENTS.md
    ├── agents/
    ├── rules/
    ├── specs/
    ├── skills/
    ├── hooks/
    └── hooks.json
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

## Agent factory context

The Cursor module is the "agent factory" for spec-driven development. Entry points:

- `cursor/AGENTS.md` — the pipeline, agent registry, model selection per agent.
- `cursor/rules/agent-constitution.mdc` — user-level rule (always applied) governing how every agent operates across projects.
- `cursor/specs/_TEMPLATE.spec.md` — global SPEC template. Real specs live per-project under `<project>/.cursor/specs/`.
- `cursor/agents/pipeline-orchestrator.md` — **L3 conductor**: state file + staged subagent launches.
- `cursor/pipeline/_TEMPLATE.state.yaml` — pipeline state template (copy to `<project>/.cursor/pipeline/<slug>.state.yaml`).

### L3 orchestration (quick start)

In any project chat:

```text
start pipeline for PROJ-123: <paste ticket>
continue pipeline
approve spec
continue pipeline
run gate
```

State lives at `<project>/.cursor/pipeline/<slug>.state.yaml`. Commit it for team visibility, or add `*.state.yaml` to the project `.gitignore` if you prefer local-only.
