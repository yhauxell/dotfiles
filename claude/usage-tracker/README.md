# Usage tracker

Tracks **time and money spent** across your Claude Code sessions and renders it as a
self-contained HTML dashboard — to see trends, drill into individual tasks, and find
which **flows** (slash commands / skills) cost the most so you can tune them.

Zero npm dependencies: Node parses the session transcripts, the system `sqlite3`
CLI is the storage + query engine, and the dashboard is a single static HTML file
with hand-rolled SVG charts (no network, no CDN).

## What it reads

`~/.claude/projects/<encoded-project>/**.jsonl` — the transcripts Claude Code writes
for every session. Each assistant turn carries a `usage` block (token counts incl.
cache tiers), a `model`, a timestamp, an `attributionSkill` (the flow that produced
it), and `gitBranch`/`cwd`. User lines carry the prompt text used as the task label.

Nothing is sent anywhere. The DB and dashboard stay on disk and are gitignored.

## Run it

```bash
cd ~/.claude/usage-tracker      # (symlink to ~/dotfiles/claude/usage-tracker)
./track.sh --open               # ingest everything + rebuild dashboard + open it
```

Or step by step:

```bash
node ingest.js                  # transcripts -> usage.sqlite (full re-scan, idempotent)
node build-dashboard.js         # usage.sqlite -> dashboard.html
```

Useful flags:

- `node ingest.js --filter panel-next` — only ingest transcripts whose path matches a substring.
- `node ingest.js --projects <dir>` / `--db <path>` / `--pricing <path>` — override locations.
- `node build-dashboard.js --sessions 100` — cap the sessions table.

## ⚠️ About the money figure

Costs are **notional list-API prices** (`pricing.json`, USD per 1M tokens). If you're on
a Claude subscription (Pro/Max) you are **not billed per token** — treat the dollar value
as an *equivalent cost* for comparing the relative expense of flows and sessions, not as
your actual bill. Edit `pricing.json` when rates change or to price a new model.

Cache and long-context rates derive from each model's base input rate via the
multipliers in `pricing.json` (5-min cache write = 1.25×, 1-hour = 2×, cache read = 0.1×).
Known under-count: the >200K long-context premium on `[1m]` models is recorded
(`is_1m`) but not yet applied.

## What the dashboard shows

- **Headline cards**: notional cost, active time, sessions, turns, cost/active-hour, output tokens, cache-read share.
- **Daily cost trend** with an active-hours overlay (active time caps idle gaps at 5 min, so resumed-session spans don't inflate it).
- **Cost by model** family.
- **Cost by flow / skill** — the spend per pipeline stage (`architect`, `implement`, `epic-continue`, `ticket-refinement`, …) with cost-per-turn, so you can see which flows are expensive.
- **Cache efficiency** — fresh vs cache-write vs cache-read tokens.
- **Cost by project**.
- **Sessions table** — sortable; each row is a task (date, top flow, branch, turns, active time, cost, cache %, prompt label).

## Files

| File | Role |
|------|------|
| `ingest.js` | Parse transcripts → SQLite. |
| `build-dashboard.js` | SQLite → `dashboard.html`. |
| `schema.sql` | Table definitions (messages, sessions, prompts). |
| `pricing.json` | Editable rate table. |
| `track.sh` | Ingest + build (+ `--open`) in one command. |
| `usage.sqlite`, `dashboard.html` | Generated, gitignored. |

## Keeping it current

Re-run `./track.sh` whenever you want fresh numbers. To automate, drop it in cron — e.g.
nightly:

```
0 20 * * * ~/.claude/usage-tracker/track.sh >/dev/null 2>&1
```
