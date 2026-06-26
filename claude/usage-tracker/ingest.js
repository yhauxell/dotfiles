#!/usr/bin/env node
'use strict';
/*
 * ingest.js — parse Claude Code session transcripts into a SQLite DB.
 *
 * Data source: ~/.claude/projects/<encoded-project>/**.jsonl  (assistant turns
 * carry message.usage; user lines carry prompts). Storage: the sqlite3 CLI
 * (Node has no built-in driver here) — we stream JSONL in Node, then pipe one
 * transactional batch of SQL to `sqlite3 <db>`.
 *
 * Full re-scan each run; writes are idempotent (tables are cleared then
 * rebuilt), so re-running never double-counts. ~57MB / 100+ files parses in
 * a couple of seconds.
 *
 * Usage:
 *   node ingest.js [--projects <dir>] [--db <path>] [--pricing <path>] [--filter <substr>]
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const readline = require('readline');
const { execFileSync } = require('child_process');

// ---- args ----------------------------------------------------------------
const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : def;
};
const HOME = os.homedir();
const PROJECTS = opt('--projects', path.join(HOME, '.claude', 'projects'));
const DB = opt('--db', path.join(__dirname, 'usage.sqlite'));
const PRICING_PATH = opt('--pricing', path.join(__dirname, 'pricing.json'));
const FILTER = opt('--filter', null);

// ---- pricing -------------------------------------------------------------
const pricing = JSON.parse(fs.readFileSync(PRICING_PATH, 'utf8'));
const MULT = pricing._multipliers;
const STOOLS = pricing._serverTools;
const FAMILIES = pricing.families;

function familyOf(model) {
  if (!model) return 'unknown';
  const m = model.toLowerCase();
  if (m.includes('opus')) return 'opus';
  if (m.includes('sonnet')) return 'sonnet';
  if (m.includes('haiku')) return 'haiku';
  if (m.includes('fable')) return 'fable';
  return 'unknown';
}

function costOf(family, u) {
  const r = FAMILIES[family];
  if (!r) return 0; // unknown model -> 0, flagged via family
  const inRate = r.input / 1e6;
  const outRate = r.output / 1e6;
  let c = 0;
  c += (u.input_tokens || 0) * inRate;
  c += (u.output_tokens || 0) * outRate;
  c += (u.cache_creation_5m || 0) * inRate * MULT.cacheWrite5m;
  c += (u.cache_creation_1h || 0) * inRate * MULT.cacheWrite1h;
  c += (u.cache_read_tokens || 0) * inRate * MULT.cacheRead;
  c += (u.web_search || 0) * (STOOLS.webSearchPer1k / 1000);
  c += (u.web_fetch || 0) * (STOOLS.webFetchPer1k / 1000);
  return c;
}

// ---- gather files --------------------------------------------------------
function walk(dir, acc) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); }
  catch { return acc; }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walk(full, acc);
    else if (e.isFile() && e.name.endsWith('.jsonl')) acc.push(full);
  }
  return acc;
}

// project dir = first path segment under PROJECTS
function projectDirOf(file) {
  const rel = path.relative(PROJECTS, file);
  return rel.split(path.sep)[0];
}

const day = (iso) => (iso ? String(iso).slice(0, 10) : null);

// ---- parse ---------------------------------------------------------------
const messages = new Map();   // uuid -> row
const prompts = new Map();     // uuid -> row
const seenSessions = new Set();

async function parseFile(file) {
  const projectDir = projectDirOf(file);
  const rl = readline.createInterface({
    input: fs.createReadStream(file),
    crlfDelay: Infinity,
  });
  for await (const line of rl) {
    if (!line.trim()) continue;
    let o;
    try { o = JSON.parse(line); } catch { continue; }

    if (o.type === 'assistant' && o.message && o.message.usage && o.uuid) {
      const u = o.message.usage;
      const cc = u.cache_creation || {};
      const model = o.message.model || null;
      const family = familyOf(model);
      const usage = {
        input_tokens: u.input_tokens || 0,
        output_tokens: u.output_tokens || 0,
        cache_creation_5m: cc.ephemeral_5m_input_tokens != null
          ? cc.ephemeral_5m_input_tokens
          : (u.cache_creation_input_tokens || 0),
        cache_creation_1h: cc.ephemeral_1h_input_tokens || 0,
        cache_read_tokens: u.cache_read_input_tokens || 0,
        web_search: (u.server_tool_use && u.server_tool_use.web_search_requests) || 0,
        web_fetch: (u.server_tool_use && u.server_tool_use.web_fetch_requests) || 0,
      };
      messages.set(o.uuid, {
        uuid: o.uuid,
        session_id: o.sessionId || null,
        ts: o.timestamp || null,
        day: day(o.timestamp),
        model,
        family,
        is_1m: model && model.includes('[1m]') ? 1 : 0,
        attribution_skill: o.attributionSkill || null,
        project_dir: projectDir,
        cwd: o.cwd || null,
        git_branch: o.gitBranch || null,
        ...usage,
        cost_usd: costOf(family, usage),
      });
      if (o.sessionId) seenSessions.add(o.sessionId);
    } else if (o.type === 'user' && o.uuid && o.message) {
      // capture textual prompt content for task drill-down
      let text = null;
      const c = o.message.content;
      if (typeof c === 'string') text = c;
      else if (Array.isArray(c)) {
        text = c.map(p => (typeof p === 'string' ? p : p && p.type === 'text' ? p.text : ''))
                .filter(Boolean).join('\n');
      }
      if (text) {
        prompts.set(o.uuid, {
          uuid: o.uuid,
          session_id: o.sessionId || null,
          ts: o.timestamp || null,
          text: text.slice(0, 2000),
          project_dir: projectDir,
          cwd: o.cwd || null,
          git_branch: o.gitBranch || null,
        });
      }
    }
  }
}

// ---- session aggregation -------------------------------------------------
function buildSessions() {
  const byId = new Map();
  const ensure = (id) => {
    if (!byId.has(id)) byId.set(id, {
      session_id: id, tss: [], skills: {}, families: new Set(),
      project_dir: null, cwd: null, git_branch: null,
      message_count: 0, input: 0, output: 0, cc: 0, cr: 0, cost: 0,
      firstPrompt: null, firstPromptTs: null,
    });
    return byId.get(id);
  };

  for (const m of messages.values()) {
    if (!m.session_id) continue;
    const s = ensure(m.session_id);
    if (m.ts) s.tss.push(m.ts);
    s.message_count++;
    s.input += m.input_tokens;
    s.output += m.output_tokens;
    s.cc += m.cache_creation_5m + m.cache_creation_1h;
    s.cr += m.cache_read_tokens;
    s.cost += m.cost_usd;
    if (m.family) s.families.add(m.family);
    if (m.attribution_skill) s.skills[m.attribution_skill] = (s.skills[m.attribution_skill] || 0) + 1;
    if (m.project_dir) s.project_dir = m.project_dir;
    if (m.cwd) s.cwd = m.cwd;
    if (m.git_branch) s.git_branch = m.git_branch;
  }
  for (const p of prompts.values()) {
    if (!p.session_id) continue;
    const s = ensure(p.session_id);
    if (p.ts) s.tss.push(p.ts);
    if (p.text && (!s.firstPromptTs || (p.ts && p.ts < s.firstPromptTs))) {
      // ignore slash-command-only noise when a richer prompt exists later? keep first.
      s.firstPrompt = p.text.replace(/\s+/g, ' ').slice(0, 280);
      s.firstPromptTs = p.ts;
    }
    if (!s.project_dir) s.project_dir = p.project_dir;
    if (!s.cwd) s.cwd = p.cwd;
    if (!s.git_branch) s.git_branch = p.git_branch;
  }

  const rows = [];
  for (const s of byId.values()) {
    const tss = s.tss.filter(Boolean).sort();
    const first = tss[0] || null;
    const last = tss[tss.length - 1] || null;
    let duration = 0, active = 0;
    if (first && last) duration = Math.round((Date.parse(last) - Date.parse(first)) / 1000);
    for (let i = 1; i < tss.length; i++) {
      const gap = (Date.parse(tss[i]) - Date.parse(tss[i - 1])) / 1000;
      if (gap > 0) active += Math.min(gap, 300); // cap idle gaps at 5 min
    }
    const topSkill = Object.entries(s.skills).sort((a, b) => b[1] - a[1])[0];
    rows.push({
      session_id: s.session_id,
      project_dir: s.project_dir,
      cwd: s.cwd,
      git_branch: s.git_branch,
      first_ts: first,
      last_ts: last,
      duration_sec: duration,
      active_sec: Math.round(active),
      message_count: s.message_count,
      models: [...s.families].sort().join(','),
      top_skill: topSkill ? topSkill[0] : null,
      first_prompt: s.firstPrompt,
      input_tokens: s.input,
      output_tokens: s.output,
      cache_creation_tokens: s.cc,
      cache_read_tokens: s.cr,
      cost_usd: s.cost,
    });
  }
  return rows;
}

// ---- SQL emission --------------------------------------------------------
const sq = (v) => (v == null ? 'NULL' : `'${String(v).replace(/'/g, "''")}'`);
const nq = (v) => (v == null || Number.isNaN(v) ? 0 : Number(v));

function emitSQL(sessionRows) {
  const out = [];
  out.push('BEGIN;');
  out.push('DELETE FROM messages; DELETE FROM sessions; DELETE FROM prompts;');

  for (const m of messages.values()) {
    out.push(
      `INSERT OR REPLACE INTO messages VALUES (${sq(m.uuid)},${sq(m.session_id)},${sq(m.ts)},${sq(m.day)},${sq(m.model)},${sq(m.family)},${nq(m.is_1m)},${sq(m.attribution_skill)},${sq(m.project_dir)},${sq(m.cwd)},${sq(m.git_branch)},${nq(m.input_tokens)},${nq(m.output_tokens)},${nq(m.cache_creation_5m)},${nq(m.cache_creation_1h)},${nq(m.cache_read_tokens)},${nq(m.web_search)},${nq(m.web_fetch)},${nq(m.cost_usd)});`
    );
  }
  for (const p of prompts.values()) {
    out.push(`INSERT OR REPLACE INTO prompts VALUES (${sq(p.uuid)},${sq(p.session_id)},${sq(p.ts)},${sq(p.text)});`);
  }
  for (const s of sessionRows) {
    out.push(
      `INSERT OR REPLACE INTO sessions VALUES (${sq(s.session_id)},${sq(s.project_dir)},${sq(s.cwd)},${sq(s.git_branch)},${sq(s.first_ts)},${sq(s.last_ts)},${nq(s.duration_sec)},${nq(s.active_sec)},${nq(s.message_count)},${sq(s.models)},${sq(s.top_skill)},${sq(s.first_prompt)},${nq(s.input_tokens)},${nq(s.output_tokens)},${nq(s.cache_creation_tokens)},${nq(s.cache_read_tokens)},${nq(s.cost_usd)});`
    );
  }
  out.push('COMMIT;');
  return out.join('\n');
}

// ---- main ----------------------------------------------------------------
(async () => {
  let files = walk(PROJECTS, []);
  if (FILTER) files = files.filter(f => f.includes(FILTER));
  if (!files.length) {
    console.error(`No .jsonl transcripts found under ${PROJECTS}` + (FILTER ? ` matching "${FILTER}"` : ''));
    process.exit(1);
  }

  const t0 = Date.now();
  for (const f of files) await parseFile(f);
  const sessionRows = buildSessions();

  // init schema, then load data
  execFileSync('sqlite3', [DB], { input: fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8') });
  execFileSync('sqlite3', [DB], { input: emitSQL(sessionRows), maxBuffer: 1024 * 1024 * 256 });

  const flagged = [...messages.values()].filter(m => m.family === 'unknown');
  const unknownModels = [...new Set(flagged.map(m => m.model))];

  console.log(`Ingested ${files.length} files in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  console.log(`  messages: ${messages.size}  prompts: ${prompts.size}  sessions: ${sessionRows.length}`);
  if (unknownModels.length) {
    console.log(`  ⚠ ${flagged.length} turns on unpriced models (cost=0): ${unknownModels.join(', ')}`);
    console.log(`    add them to pricing.json "families" to include their cost.`);
  }
  console.log(`  DB: ${DB}`);
})();
