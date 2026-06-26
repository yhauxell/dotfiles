#!/usr/bin/env node
'use strict';
/*
 * build-dashboard.js — query the usage SQLite DB and emit a self-contained
 * dashboard.html (no network, no CDN, vanilla SVG charts).
 *
 * Usage: node build-dashboard.js [--db <path>] [--out <path>] [--sessions <N>]
 */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i >= 0 && args[i + 1] ? args[i + 1] : d; };
const DB = opt('--db', path.join(__dirname, 'usage.sqlite'));
const OUT = opt('--out', path.join(__dirname, 'dashboard.html'));
const SESSION_LIMIT = parseInt(opt('--sessions', '300'), 10);
const SINCE = opt('--since', null);   // YYYY-MM-DD inclusive (billing-cycle start)
const UNTIL = opt('--until', null);   // YYYY-MM-DD inclusive

if (!fs.existsSync(DB)) {
  console.error(`DB not found: ${DB}\nRun "node ingest.js" first.`);
  process.exit(1);
}
const pricing = JSON.parse(fs.readFileSync(path.join(__dirname, 'pricing.json'), 'utf8'));
// Calibration: scale notional cost to match an external meter. Set
// pricing.calibration to (your meter reading) / (this dashboard's notional for
// the same --since window). 1.0 = raw list pricing.
const CAL = +(pricing.calibration ?? 1) || 1;
const C = (expr) => `ROUND((${expr})*${CAL},2)`; // calibrated cost expression

// Date-window filters (on messages.day and sessions.first_ts).
const mWhere = [SINCE && `day >= '${SINCE}'`, UNTIL && `day <= '${UNTIL}'`].filter(Boolean);
const sWhere = [SINCE && `substr(first_ts,1,10) >= '${SINCE}'`, UNTIL && `substr(first_ts,1,10) <= '${UNTIL}'`].filter(Boolean);
const WM = mWhere.length ? 'WHERE ' + mWhere.join(' AND ') : '';
const WS = sWhere.length ? 'WHERE ' + sWhere.join(' AND ') : '';
const andM = mWhere.length ? 'AND ' + mWhere.join(' AND ') : '';

const q = (sql) => JSON.parse(execFileSync('sqlite3', ['-json', DB, sql], { maxBuffer: 1024 * 1024 * 256 }).toString() || '[]');

const totals = q(`SELECT
    (SELECT ${C('SUM(cost_usd)')} FROM messages ${WM}) AS cost,
    (SELECT SUM(input_tokens) FROM messages ${WM}) AS fresh_in,
    (SELECT SUM(output_tokens) FROM messages ${WM}) AS out_tok,
    (SELECT SUM(cache_creation_5m+cache_creation_1h) FROM messages ${WM}) AS cache_write,
    (SELECT SUM(cache_read_tokens) FROM messages ${WM}) AS cache_read,
    (SELECT COUNT(*) FROM messages ${WM}) AS turns,
    (SELECT COUNT(*) FROM sessions ${WS}) AS sessions,
    (SELECT ROUND(SUM(active_sec)/3600.0,1) FROM sessions ${WS}) AS active_hrs`)[0];

const daily = q(`SELECT m.day AS day, ${C('SUM(m.cost_usd)')} AS cost, COUNT(*) AS turns,
    (SELECT ROUND(SUM(active_sec)/3600.0,2) FROM sessions s WHERE substr(s.first_ts,1,10)=m.day) AS active_hrs
  FROM messages m ${WM} GROUP BY m.day ORDER BY m.day`);

const byFlow = q(`SELECT COALESCE(attribution_skill,'(conversation)') AS flow,
    ${C('SUM(cost_usd)')} AS cost, COUNT(*) AS turns,
    ${C('SUM(cost_usd)/COUNT(*)')} AS cost_per_turn
  FROM messages ${WM} GROUP BY flow ORDER BY cost DESC`);

const byFamily = q(`SELECT family, ${C('SUM(cost_usd)')} AS cost, COUNT(*) AS turns,
    SUM(input_tokens+output_tokens) AS billed_tokens
  FROM messages ${WM} GROUP BY family ORDER BY cost DESC`);

const byProject = q(`SELECT project_dir, ${C('SUM(cost_usd)')} AS cost,
    COUNT(DISTINCT session_id) AS sessions
  FROM messages ${WM} GROUP BY project_dir ORDER BY cost DESC LIMIT 15`);

const sessions = q(`SELECT session_id, substr(first_ts,1,10) AS day, first_ts, project_dir, git_branch,
    top_skill, message_count, duration_sec, active_sec, models, ${C('cost_usd')} AS cost_usd,
    input_tokens, output_tokens, cache_read_tokens, first_prompt
  FROM sessions ${WS} ORDER BY first_ts DESC LIMIT ${SESSION_LIMIT}`);

const generatedAt = execFileSync('date', ['+%Y-%m-%d %H:%M']).toString().trim();
const windowLabel = (SINCE || UNTIL) ? `${SINCE || '…'} → ${UNTIL || 'now'}` : 'all time';

const DATA = { totals, daily, byFlow, byFamily, byProject, sessions, generatedAt, families: pricing.families, windowLabel, calibration: CAL };

const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Code — usage tracker</title>
<style>
  :root{--bg:#0f1117;--panel:#171a23;--panel2:#1d212c;--ink:#e6e9ef;--mut:#8a93a6;--line:#2a2f3c;
    --c1:#7aa2f7;--c2:#9ece6a;--c3:#e0af68;--c4:#bb9af7;--c5:#f7768e;--c6:#7dcfff;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  header{padding:22px 28px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}
  h1{font-size:18px;margin:0;font-weight:650}
  .sub{color:var(--mut);font-size:12px}
  .wrap{padding:24px 28px;max-width:1320px;margin:0 auto}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:26px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
  .card .k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
  .card .v{font-size:26px;font-weight:680;margin-top:6px}
  .card .v small{font-size:13px;color:var(--mut);font-weight:500}
  .grid{display:grid;grid-template-columns:1.6fr 1fr;gap:18px;margin-bottom:18px}
  @media(max-width:900px){.grid{grid-template-columns:1fr}}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
  .panel h2{font-size:13px;margin:0 0 14px;font-weight:600;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
  .note{color:var(--mut);font-size:11px;margin-top:8px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
  th{color:var(--mut);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;user-select:none}
  td.task{white-space:normal;max-width:420px;color:var(--mut)}
  td.num{text-align:right;font-variant-numeric:tabular-nums}
  .bar-row{display:flex;align-items:center;gap:10px;margin:7px 0;font-size:13px}
  .bar-row .lbl{width:160px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .bar-row .track{flex:1;background:var(--panel2);border-radius:5px;height:18px;position:relative;overflow:hidden}
  .bar-row .fill{height:100%;border-radius:5px}
  .bar-row .val{width:118px;text-align:right;color:var(--mut);font-variant-numeric:tabular-nums}
  .legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;font-size:12px;color:var(--mut)}
  .legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}
  .pill{display:inline-block;padding:1px 7px;border-radius:99px;background:var(--panel2);color:var(--mut);font-size:11px}
  svg text{fill:var(--mut);font-size:10px}
  .axis{stroke:var(--line)}
  a{color:var(--c1)}
</style></head>
<body>
<header>
  <h1>Claude Code · usage tracker</h1>
  <span class="sub">generated ${generatedAt}</span>
  <span class="sub">window: ${windowLabel}</span>
  <span class="sub">${CAL === 1 ? 'notional list-API cost — comparative, not your subscription bill' : 'calibrated ×' + CAL + ' to external meter'}</span>
</header>
<div class="wrap">
  <div class="cards" id="cards"></div>
  <div class="grid">
    <div class="panel"><h2>Daily notional cost</h2><div id="dailyChart"></div>
      <div class="note">Bars = $/day · line = active hours/day (capped at 5-min idle gaps).</div></div>
    <div class="panel"><h2>Cost by model</h2><div id="familyChart"></div></div>
  </div>
  <div class="grid">
    <div class="panel"><h2>Cost by flow / skill</h2><div id="flowChart"></div>
      <div class="note">Where the spend goes per pipeline stage. "(conversation)" = turns with no slash-command attribution.</div></div>
    <div class="panel"><h2>Cache efficiency</h2><div id="cacheChart"></div>
      <div class="note">Cache reads bill at 10% of input. A high read share means the harness is reusing context cheaply.</div></div>
  </div>
  <div class="panel" style="margin-bottom:18px"><h2>Cost by project</h2><div id="projectChart"></div></div>
  <div class="panel">
    <h2>Sessions <span class="pill" id="sessCount"></span></h2>
    <div style="overflow:auto;max-height:560px">
      <table id="sessTable"><thead><tr>
        <th data-k="day">Date</th><th data-k="top_skill">Top flow</th><th data-k="git_branch">Branch</th>
        <th data-k="message_count" class="num">Turns</th><th data-k="active_sec" class="num">Active</th>
        <th data-k="cost_usd" class="num">Cost</th><th data-k="cache_ratio" class="num">Cache%</th>
        <th data-k="first_prompt">Task</th>
      </tr></thead><tbody></tbody></table>
    </div>
    <div class="note">Active = summed gaps capped at 5 min/turn (resumed-session spans are excluded). Cache% = cache-read share of input tokens.</div>
  </div>
</div>
<script>
const DATA = ${JSON.stringify(DATA)};
const PAL = ['#7aa2f7','#9ece6a','#e0af68','#bb9af7','#f7768e','#7dcfff','#ff9e64','#9aa5ce'];
const fmt$ = n => '$'+(+n||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtN = n => (+n||0).toLocaleString();
const fmtTok = n => { n=+n||0; if(n>=1e9)return (n/1e9).toFixed(1)+'B'; if(n>=1e6)return (n/1e6).toFixed(1)+'M'; if(n>=1e3)return (n/1e3).toFixed(1)+'k'; return ''+n; };
const fmtDur = s => { s=Math.round(+s||0); let h=Math.floor(s/3600),m=Math.round((s%3600)/60); if(m===60){h++;m=0;} return h?h+'h'+(m?(' '+m+'m'):''):m+'m'; };
const el = (h)=>{const t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstChild;};

// ---- cards ----
const t = DATA.totals;
const cacheRatio = t.cache_read/(t.fresh_in+t.cache_read)*100;
const cards = [
  ['Notional cost', fmt$(t.cost)],
  ['Active time', t.active_hrs+' <small>hrs</small>'],
  ['Sessions', fmtN(t.sessions)],
  ['Assistant turns', fmtN(t.turns)],
  ['Cost / active hr', fmt$(t.cost/(t.active_hrs||1))],
  ['Output tokens', fmtTok(t.out_tok)],
  ['Cache-read share', cacheRatio.toFixed(1)+'<small>%</small>'],
];
document.getElementById('cards').append(...cards.map(([k,v])=>el(\`<div class="card"><div class="k">\${k}</div><div class="v">\${v}</div></div>\`)));

// ---- horizontal bars helper ----
function hbars(node, rows, label, value, fmt, color){
  const max = Math.max(...rows.map(value),1);
  node.append(...rows.map((r,i)=>{
    const w = (value(r)/max*100).toFixed(1);
    const col = typeof color==='function'?color(r,i):color||PAL[i%PAL.length];
    return el(\`<div class="bar-row"><span class="lbl" title="\${label(r)}">\${label(r)}</span>
      <span class="track"><span class="fill" style="width:\${w}%;background:\${col}"></span></span>
      <span class="val">\${fmt(r)}</span></div>\`);
  }));
}

// flow
hbars(document.getElementById('flowChart'), DATA.byFlow.slice(0,12),
  r=>r.flow, r=>r.cost, r=>\`\${fmt$(r.cost)} · \${r.turns}t · \${fmt$(r.cost_per_turn)}/t\`);

// family
const famCol={opus:'#bb9af7',sonnet:'#7aa2f7',haiku:'#9ece6a',fable:'#e0af68',unknown:'#565f73'};
hbars(document.getElementById('familyChart'), DATA.byFamily,
  r=>r.family, r=>r.cost, r=>\`\${fmt$(r.cost)} · \${r.turns}t\`, r=>famCol[r.family]||'#565f73');

// project
hbars(document.getElementById('projectChart'), DATA.byProject,
  r=>(r.project_dir||'').replace(/^-?Users-[^-]+-/,'…/').slice(0,52), r=>r.cost,
  r=>\`\${fmt$(r.cost)} · \${r.sessions} sess\`);

// ---- daily combo chart (SVG) ----
function dailyChart(){
  const d=DATA.daily; if(!d.length){return;}
  const W=720,H=240,pl=44,pr=44,pt=12,pb=28, iw=W-pl-pr, ih=H-pt-pb;
  const maxC=Math.max(...d.map(x=>x.cost),0.01), maxH=Math.max(...d.map(x=>x.active_hrs||0),0.01);
  const bw=iw/d.length*0.7, step=iw/d.length;
  let s=\`<svg viewBox="0 0 \${W} \${H}" width="100%">\`;
  s+=\`<line class="axis" x1="\${pl}" y1="\${pt+ih}" x2="\${pl+iw}" y2="\${pt+ih}"/>\`;
  // y grid (cost)
  for(let g=0;g<=2;g++){const y=pt+ih-ih*g/2;const v=maxC*g/2;
    s+=\`<line class="axis" x1="\${pl}" y1="\${y}" x2="\${pl+iw}" y2="\${y}" opacity=".4"/><text x="4" y="\${y+3}">$\${v.toFixed(0)}</text>\`;}
  d.forEach((x,i)=>{
    const bh=x.cost/maxC*ih, bx=pl+step*i+(step-bw)/2, by=pt+ih-bh;
    s+=\`<rect x="\${bx}" y="\${by}" width="\${bw}" height="\${bh}" rx="2" fill="#7aa2f7"><title>\${x.day}: \${fmt$(x.cost)} · \${x.turns} turns · \${(x.active_hrs||0).toFixed(1)}h active</title></rect>\`;
    if(i%Math.ceil(d.length/8)===0||i===d.length-1) s+=\`<text x="\${pl+step*i+step/2}" y="\${H-8}" text-anchor="middle">\${x.day.slice(5)}</text>\`;
  });
  // active-hours line
  const pts=d.map((x,i)=>[pl+step*i+step/2, pt+ih-(x.active_hrs||0)/maxH*ih]);
  s+=\`<polyline fill="none" stroke="#e0af68" stroke-width="2" points="\${pts.map(p=>p.join(',')).join(' ')}"/>\`;
  pts.forEach((p,i)=>s+=\`<circle cx="\${p[0]}" cy="\${p[1]}" r="2.5" fill="#e0af68"><title>\${d[i].day}: \${(d[i].active_hrs||0).toFixed(1)}h active</title></circle>\`);
  s+=\`<text x="\${pl+iw}" y="10" text-anchor="end" fill="#e0af68">active hrs ▲ \${maxH.toFixed(1)}</text>\`;
  s+='</svg>';
  document.getElementById('dailyChart').innerHTML=s;
}
dailyChart();

// ---- cache efficiency stacked bar ----
function cacheChart(){
  const fresh=t.fresh_in, write=t.cache_write, read=t.cache_read, tot=fresh+write+read;
  const segs=[['Fresh input',fresh,'#f7768e'],['Cache write',write,'#e0af68'],['Cache read',read,'#9ece6a']];
  let s='<div style="display:flex;height:30px;border-radius:6px;overflow:hidden;margin-bottom:12px">';
  segs.forEach(([n,v,c])=>{s+=\`<div title="\${n}: \${fmtTok(v)} (\${(v/tot*100).toFixed(1)}%)" style="width:\${v/tot*100}%;background:\${c}"></div>\`;});
  s+='</div><div class="legend">'+segs.map(([n,v,c])=>\`<span><i style="background:\${c}"></i>\${n} · \${fmtTok(v)}</span>\`).join('')+'</div>';
  document.getElementById('cacheChart').innerHTML=s;
}
cacheChart();

// ---- sessions table ----
const tb=document.querySelector('#sessTable tbody');
document.getElementById('sessCount').textContent=DATA.sessions.length+' shown';
function rowsHTML(rows){
  return rows.map(s=>{
    const ratio=s.input_tokens?(s.cache_read_tokens/(s.input_tokens+s.cache_read_tokens)*100):0;
    return \`<tr>
      <td>\${s.day||''}</td>
      <td>\${s.top_skill?('<span class="pill">'+s.top_skill+'</span>'):'<span class="sub">—</span>'}</td>
      <td>\${(s.git_branch||'').slice(0,24)}</td>
      <td class="num">\${fmtN(s.message_count)}</td>
      <td class="num">\${fmtDur(s.active_sec)}</td>
      <td class="num">\${fmt$(s.cost_usd)}</td>
      <td class="num">\${ratio.toFixed(0)}%</td>
      <td class="task" title="\${(s.first_prompt||'').replace(/"/g,'&quot;')}">\${(s.first_prompt||'').slice(0,90)}</td>
    </tr>\`;
  }).join('');
}
let sortK='cost_usd', sortDir=-1;
function render(){
  const rows=[...DATA.sessions].sort((a,b)=>{
    let av=a[sortK],bv=b[sortK];
    if(sortK==='cache_ratio'){av=a.input_tokens?a.cache_read_tokens/(a.input_tokens+a.cache_read_tokens):0;bv=b.input_tokens?b.cache_read_tokens/(b.input_tokens+b.cache_read_tokens):0;}
    if(typeof av==='string')return sortDir*(''+av).localeCompare(''+bv);
    return sortDir*((av||0)-(bv||0));
  });
  tb.innerHTML=rowsHTML(rows);
}
document.querySelectorAll('#sessTable th').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k; if(k===sortK)sortDir*=-1; else{sortK=k;sortDir=-1;} render();
});
render();
</script>
</body></html>`;

fs.writeFileSync(OUT, html);
console.log(`Dashboard written: ${OUT}`);
console.log(`  ${totals.sessions} sessions · ${totals.turns} turns · $${totals.cost} notional · ${totals.active_hrs}h active`);
