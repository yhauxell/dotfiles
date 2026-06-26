-- Usage-tracker schema. Storage engine is the sqlite3 CLI (no node driver).
-- Idempotent: ingest uses INSERT OR REPLACE keyed on uuid/session_id, so
-- re-running over the same transcripts never double-counts.

PRAGMA journal_mode = WAL;

-- One row per assistant turn that reported usage.
CREATE TABLE IF NOT EXISTS messages (
  uuid                 TEXT PRIMARY KEY,
  session_id           TEXT NOT NULL,
  ts                   TEXT NOT NULL,            -- ISO-8601
  day                  TEXT NOT NULL,            -- YYYY-MM-DD (local-naive, from ts)
  model                TEXT,
  family               TEXT,                     -- opus|sonnet|haiku|fable|unknown
  is_1m                INTEGER DEFAULT 0,        -- 1 if model id carried a [1m] suffix
  attribution_skill    TEXT,                     -- flow/skill that produced this turn
  project_dir          TEXT,                     -- encoded ~/.claude/projects/<dir>
  cwd                  TEXT,
  git_branch           TEXT,
  input_tokens         INTEGER DEFAULT 0,
  output_tokens        INTEGER DEFAULT 0,
  cache_creation_5m    INTEGER DEFAULT 0,
  cache_creation_1h    INTEGER DEFAULT 0,
  cache_read_tokens    INTEGER DEFAULT 0,
  web_search           INTEGER DEFAULT 0,
  web_fetch            INTEGER DEFAULT 0,
  cost_usd             REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_day ON messages(day);
CREATE INDEX IF NOT EXISTS idx_messages_skill ON messages(attribution_skill);

-- One row per session (aggregated from messages + prompt metadata).
CREATE TABLE IF NOT EXISTS sessions (
  session_id           TEXT PRIMARY KEY,
  project_dir          TEXT,
  cwd                  TEXT,
  git_branch           TEXT,
  first_ts             TEXT,
  last_ts              TEXT,
  duration_sec         INTEGER DEFAULT 0,        -- wall clock: last - first
  active_sec           INTEGER DEFAULT 0,        -- sum of inter-msg gaps capped at 300s
  message_count        INTEGER DEFAULT 0,
  models               TEXT,                     -- comma-joined distinct families
  top_skill            TEXT,                     -- skill with the most turns
  first_prompt         TEXT,                     -- opening user prompt (task label)
  input_tokens         INTEGER DEFAULT 0,
  output_tokens        INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens    INTEGER DEFAULT 0,
  cost_usd             REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sessions_day ON sessions(first_ts);

-- Captured user prompts (task detail / drill-down).
CREATE TABLE IF NOT EXISTS prompts (
  uuid                 TEXT PRIMARY KEY,
  session_id           TEXT NOT NULL,
  ts                   TEXT,
  text                 TEXT
);
CREATE INDEX IF NOT EXISTS idx_prompts_session ON prompts(session_id);

-- Bookkeeping for incremental ingest (mtime per file).
CREATE TABLE IF NOT EXISTS ingest_state (
  file_path            TEXT PRIMARY KEY,
  mtime_ms             INTEGER,
  ingested_at          TEXT
);
