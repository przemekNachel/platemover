#!/usr/bin/env python3
"""
Plate puzzle solver - Flask web app.

- Drag plates to set CURRENT positions (pins fixed in one column,
  plates slide underneath, like the real mechanism).
- Link wizard: tells you exactly which arrow to press (choosing safe
  moves to avoid costly blocked attempts). You then DRAG the plates
  above to mirror what happened in the game and hit Confirm - the app
  derives all links from the before/after difference. A "Blocked"
  button covers moves that didn't happen.
- BFS finds the shortest solution; step through with Next/Prev.

Directions are ALWAYS swapped: in-game arrows are mirrored vs the
puzzle numbering, so the app shows the arrow you actually press.

Run:
    pip install flask
    python3 plate_solver_app.py
Then open http://<server-ip>:5050
"""

from collections import deque

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

MAX_POS = 7
GOAL_POS = 4
N_PLATES = 6

DEFAULT_START = [4, 4, 4, 4, 4, 4]
DEFAULT_LINKS = {}


def solve(start, effects):
    n = len(start)
    goal = tuple([GOAL_POS] * n)
    prev = {start: None}
    q = deque([start])
    while q:
        st = q.popleft()
        if st == goal:
            path = []
            while prev[st] is not None:
                pst, mv = prev[st]
                path.append({"plate": mv[0] + 1, "dir": mv[1], "state": list(st)})
                st = pst
            path.reverse()
            return path
        for i in range(n):
            for d in (-1, +1):
                s = list(st)
                s[i] += d
                if not (1 <= s[i] <= MAX_POS):
                    continue
                ok = True
                for j, sign in effects.get(i, []):
                    s[j] += sign * d
                    if not (1 <= s[j] <= MAX_POS):
                        ok = False
                        break
                if not ok:
                    continue
                ns = tuple(s)
                if ns not in prev:
                    prev[ns] = (st, (i, d))
                    q.append(ns)
    return None


@app.route("/api/solve", methods=["POST"])
def api_solve():
    data = request.get_json(force=True)
    try:
        start = tuple(int(p) for p in data["start"])
        if len(start) != N_PLATES or not all(1 <= p <= MAX_POS for p in start):
            raise ValueError
        effects = {}
        for i_str, lst in data.get("links", {}).items():
            i = int(i_str) - 1
            effects[i] = []
            for j_str, sign in lst.items():
                j = int(j_str) - 1
                sign = int(sign)
                if sign not in (-1, 1) or j == i or not (0 <= j < N_PLATES):
                    continue
                effects[i].append((j, sign))
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Invalid configuration."}), 400

    path = solve(start, effects)
    if path is None:
        return jsonify({"solvable": False})
    return jsonify({"solvable": True, "start": list(start), "moves": path})


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stone plate solver</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#0f0c08; --stone:#1d1812; --stone2:#272019; --stone3:#322a20;
  --edge:#4a3d2c; --parch:#e6d8ba; --parch-dim:#a8966f;
  --bronze:#c98f3d; --bronze-hi:#e8b462; --ember:#b34a2a; --moss:#7d8f53;
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  background:var(--ink); color:var(--parch);
  font-family:'JetBrains Mono',monospace; font-size:15px;
  min-height:100vh; display:flex; flex-direction:column; align-items:center;
  padding:28px 12px 64px; width:100%; overflow-x:hidden;
  background-image:radial-gradient(ellipse 80% 50% at 50% -10%, #2a2114 0%, transparent 60%);
}
h1{
  font-family:'Cinzel',serif; font-weight:700; letter-spacing:.12em;
  font-size:clamp(20px,4vw,32px); color:var(--bronze-hi);
  text-shadow:0 2px 8px rgba(0,0,0,.8); margin-bottom:4px; text-align:center;
}
.sub{color:var(--parch-dim); font-size:13px; margin-bottom:24px; text-align:center}
#setup,#solution{width:100%; max-width:760px; min-width:0}
.card{
  background:var(--stone); border:1px solid var(--edge); border-radius:10px;
  padding:18px; width:100%;
  box-shadow:0 12px 40px rgba(0,0,0,.6), inset 0 1px 0 rgba(230,216,186,.05);
}
.card + .card{margin-top:16px}
h2{font-family:'Cinzel',serif; font-weight:500; font-size:16px; letter-spacing:.08em;
   color:var(--bronze); margin-bottom:12px; border-bottom:1px solid var(--edge); padding-bottom:8px}
.hint{color:var(--parch-dim); font-size:12px; line-height:1.6; margin-bottom:10px}
button{
  font-family:'Cinzel',serif; letter-spacing:.08em; font-weight:700; font-size:14px;
  background:linear-gradient(180deg,var(--bronze) 0%,#9a6c2c 100%);
  color:#1a1206; border:1px solid #6e4d1e; border-radius:8px;
  padding:11px 22px; cursor:pointer; transition:filter .15s, transform .05s;
}
button:hover{filter:brightness(1.15)}
button:active{transform:translateY(1px)}
button.ghost{background:var(--stone3); color:var(--parch); border:1px solid var(--edge); font-weight:500}
button.danger{background:linear-gradient(180deg,#7a4030 0%,#5e2e1e 100%); color:#eed9cd; border-color:#4e271a}
button:disabled{opacity:.35; cursor:default; filter:none}
.actions{display:flex; gap:10px; justify-content:center; margin-top:18px; flex-wrap:wrap}
/* ---------- plates (shared) ---------- */
.plate{display:flex; align-items:center; gap:10px; margin-bottom:12px}
.plate .label{
  font-family:'Cinzel',serif; width:24px; text-align:right; color:var(--parch-dim);
  font-size:15px; flex:none;
}
.plate.active .label{color:var(--bronze-hi)}
.rowwrap{
  position:relative; flex:1; height:50px; border-radius:8px; overflow:hidden;
  border:1px solid var(--edge); background:var(--ink);
  transition:border-color .25s, box-shadow .25s; min-width:0;
}
.plate.active .rowwrap{border-color:var(--bronze); box-shadow:0 0 16px rgba(201,143,61,.25)}
.rowwrap.drag{touch-action:none; cursor:grab}
.rowwrap.drag:active{cursor:grabbing}
.slab{
  position:absolute; inset:0;
  background:linear-gradient(180deg,var(--stone3) 0%,var(--stone2) 100%);
  transition:transform .35s cubic-bezier(.4,.1,.2,1);
  will-change:transform;
}
.slab.nosnap{transition:none}
.notch{
  position:absolute; top:50%; transform:translate(-50%,-50%);
  width:9px; height:9px; border-radius:50%;
  background:var(--ink); border:1px solid var(--edge);
}
.notch.mid{border-color:var(--bronze); width:11px; height:11px}
.pinfixed{
  position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
  width:18px; height:18px; border-radius:50%; pointer-events:none;
  background:radial-gradient(circle at 35% 30%, var(--bronze-hi), var(--bronze) 55%, #7a5520);
  border:1px solid #6e4d1e; box-shadow:0 2px 6px rgba(0,0,0,.7);
  z-index:2;
}
.pinguide{
  position:absolute; left:50%; top:0; bottom:0; width:1px; pointer-events:none;
  background:rgba(201,143,61,.25); z-index:1;
}
.plate.solved .pinfixed{
  background:radial-gradient(circle at 35% 30%, #b9cb8a, var(--moss) 55%, #4d5a30);
  border-color:#4d5a30;
}
/* ---------- wizard ---------- */
.wizhead{display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px}
.wizhead .which{font-family:'Cinzel',serif; color:var(--bronze-hi); font-size:16px}
.wizhead .count{color:var(--parch-dim); font-size:12px}
.wizmove{
  display:flex; align-items:center; justify-content:center; gap:14px;
  padding:14px; margin:10px 0; border-radius:10px;
  background:var(--stone2); border:1px solid var(--edge);
}
.wizmove .arrow{font-size:34px; line-height:1; color:var(--bronze-hi); text-shadow:0 0 12px rgba(232,180,98,.4)}
.wizmove .what{font-family:'Cinzel',serif; font-size:16px}
.wizmove .what b{color:var(--bronze-hi)}
.picon{display:inline-flex; flex-direction:column; gap:3px; margin-left:8px; vertical-align:middle}
.picon i{display:block; width:20px; height:3px; background:#e9e4d8; border-radius:1.5px}
.picon i.cur{background:#4da3ff; box-shadow:0 0 4px rgba(77,163,255,.6)}
.picon i.aff{background:var(--bronze-hi); box-shadow:0 0 4px rgba(232,180,98,.6)}
.movewrap{display:flex; flex-direction:column; align-items:center; gap:8px}
.moverow{display:flex; align-items:center; gap:12px}
.moverow .picon{margin-left:0; gap:4px}
.moverow .picon i{width:30px; height:3px}
.moverow .arrow{font-size:34px; line-height:1; color:var(--bronze-hi); text-shadow:0 0 12px rgba(232,180,98,.4)}
.movetext{font-size:12px; letter-spacing:.1em; color:var(--parch-dim); font-family:'Cinzel',serif}
.wizhint{
  background:var(--stone2); border:1px solid var(--edge); border-radius:8px;
  padding:10px 12px; font-size:12px; line-height:1.6; color:var(--parch-dim); margin-top:10px;
}
.wizhint b{color:var(--parch)}
.caution{border-color:var(--ember)}
.wiznav{display:flex; gap:8px; justify-content:flex-end; margin-top:14px; flex-wrap:wrap}
details{margin-top:14px}
summary{cursor:pointer; color:var(--parch-dim); font-size:13px}
details table{width:100%; border-collapse:collapse; font-size:12px; margin-top:10px}
details th{color:var(--parch-dim); font-weight:400; text-align:center; padding:5px 2px}
details td{padding:4px 2px; text-align:center}
details td.rowhead{color:var(--bronze); font-weight:600; text-align:left; padding-right:6px}
select{
  background:var(--stone3); color:var(--parch); border:1px solid var(--edge);
  border-radius:6px; padding:4px 3px; font-family:inherit; font-size:12px; cursor:pointer; max-width:100%;
}
select.reg{color:var(--moss); border-color:var(--moss)}
select.rev{color:var(--ember); border-color:var(--ember)}
/* ---------- solution ---------- */
.instruction{
  display:flex; align-items:center; justify-content:center; gap:16px;
  padding:16px; margin-bottom:16px; border-radius:10px;
  background:var(--stone2); border:1px solid var(--edge);
}
.instruction .arrow{font-size:38px; line-height:1; color:var(--bronze-hi); text-shadow:0 0 14px rgba(232,180,98,.45)}
.instruction .what{font-family:'Cinzel',serif; font-size:18px; letter-spacing:.06em}
.instruction .what b{color:var(--bronze-hi)}
.progress{height:6px; background:var(--stone3); border-radius:3px; overflow:hidden; margin-bottom:14px}
.progress div{height:100%; background:var(--bronze); transition:width .25s}
.stepinfo{text-align:center; color:var(--parch-dim); font-size:12px; margin-bottom:12px}
.banner{text-align:center; font-family:'Cinzel',serif; font-size:20px; letter-spacing:.1em; color:var(--moss); padding:12px; display:none}
.error{color:var(--ember); text-align:center; margin-top:12px; display:none}
.hidden{display:none}
</style>
</head>
<body>

<h1>Stone plate solver</h1>
<div class="sub">Set every pin to the middle notch</div>

<!-- ============ SETUP ============ -->
<div id="setup">
  <div class="card">
    <h2>Current positions</h2>
    <div class="hint">Drag each plate so the pin sits on the same notch as in the game.</div>
    <div id="setupPlates"></div>
  </div>

  <div class="card">
    <h2>Link wizard</h2>
    <div id="wizard"></div>
    <details id="matrixDetails">
      <summary>Manual link matrix (advanced)</summary>
      <div class="hint" style="margin-top:8px">
        When you move the <span style="color:#4da3ff">blue</span> plate (row),
        the <span style="color:var(--bronze-hi)">gold</span> plate (column) follows:
        <span style="color:var(--moss)">reg</span> = same direction,
        <span style="color:var(--ember)">rev</span> = opposite. One-directional.
      </div>
      <table id="linkTable"></table>
    </details>
    <div class="actions">
      <button id="solveBtn">Solve</button>
      <button class="ghost" id="resetBtn">Reset all</button>
    </div>
    <div class="error" id="errBox"></div>
  </div>
</div>

<!-- ============ SOLUTION ============ -->
<div id="solution" class="card hidden">
  <h2>Solution</h2>
  <div class="instruction" id="instr"></div>
  <div class="progress"><div id="progBar" style="width:0%"></div></div>
  <div class="stepinfo" id="stepInfo"></div>
  <div id="solPlates"></div>
  <div class="banner" id="doneBanner">&#9884; All pins centered &#9884;</div>
  <div class="actions">
    <button class="ghost" id="prevBtn">&#9664; Prev</button>
    <button id="nextBtn">Next &#9654;</button>
    <button class="ghost" id="backBtn">Edit puzzle</button>
  </div>
  <div class="hint" style="text-align:center; margin-top:10px">Tip: arrow keys also step</div>
</div>

<script>
const N = 6, MAXPOS = 7, GOAL = 4;
const DEF_START = {{ default_start | safe }};
const DEF_LINKS = {{ default_links | safe }};

/* Directions are ALWAYS mirrored: solver dir d -> in-game arrow for -d */
function gameArrow(d) { return -d > 0 ? '\u2192' : '\u2190'; }
function gameWord(d)  { return -d > 0 ? 'RIGHT' : 'LEFT'; }
/* small stack icon: 6 horizontal lines, the targeted plate's line highlighted */
function plateIcon(n, cls) {
  let s = '<span class="picon">';
  for (let k = 1; k <= N; k++) s += `<i${k === n ? ` class="${cls || 'cur'}"` : ''}></i>`;
  return s + '</span>';
}
/* big instruction: arrow on the side it points to, small text below */
function bigMove(plate, d) {
  const a = `<span class="arrow">${gameArrow(d)}</span>`;
  const left = gameArrow(d) === '\u2190';
  return `<div class="movewrap">
    <div class="moverow">${left ? a : ''}${plateIcon(plate)}${left ? '' : a}</div>
    <div class="movetext">Move ${plate} ${gameWord(d)}</div>
  </div>`;
}

/* ================= shared plate renderer ================= */
function makePlateRow(container, idx, prefix) {
  const row = document.createElement('div');
  row.className = 'plate'; row.id = `${prefix}plate${idx}`;
  let notches = '';
  for (let p = 1; p <= MAXPOS; p++) {
    const pct = ((p - 0.5) / MAXPOS * 100).toFixed(3);
    notches += `<div class="notch${p === GOAL ? ' mid' : ''}" style="left:${pct}%"></div>`;
  }
  row.innerHTML = `<div class="label">P${idx + 1}</div>
    <div class="rowwrap" id="${prefix}wrap${idx}">
      <div class="slab" id="${prefix}slab${idx}">${notches}</div>
      <div class="pinguide"></div>
      <div class="pinfixed"></div>
    </div>`;
  container.appendChild(row);
}
function setPlate(prefix, idx, pos) {
  const wrap = document.getElementById(`${prefix}wrap${idx}`);
  const slab = document.getElementById(`${prefix}slab${idx}`);
  const sp = wrap.clientWidth / MAXPOS;
  slab.style.transform = `translateX(${(GOAL - pos) * sp}px)`;
  document.getElementById(`${prefix}plate${idx}`).classList.toggle('solved', pos === GOAL);
}

/* ================= current positions (draggable) ================= */
const curPos = DEF_START.slice();
const setupBox = document.getElementById('setupPlates');
for (let i = 0; i < N; i++) {
  makePlateRow(setupBox, i, 's');
  const wrap = document.getElementById('swrap' + i);
  wrap.classList.add('drag');
  const slab = document.getElementById('sslab' + i);
  let dragging = false, startX = 0, baseT = 0, sp = 0;
  wrap.addEventListener('pointerdown', e => {
    dragging = true; wrap.setPointerCapture(e.pointerId);
    sp = wrap.clientWidth / MAXPOS;
    startX = e.clientX; baseT = (GOAL - curPos[i]) * sp;
    slab.classList.add('nosnap');
  });
  wrap.addEventListener('pointermove', e => {
    if (!dragging) return;
    let t = baseT + (e.clientX - startX);
    t = Math.max((GOAL - MAXPOS) * sp, Math.min((GOAL - 1) * sp, t));
    slab.style.transform = `translateX(${t}px)`;
  });
  const finish = e => {
    if (!dragging) return;
    dragging = false;
    let t = baseT + (e.clientX - startX);
    t = Math.max((GOAL - MAXPOS) * sp, Math.min((GOAL - 1) * sp, t));
    curPos[i] = Math.min(MAXPOS, Math.max(1, Math.round(GOAL - t / sp)));
    slab.classList.remove('nosnap');
    setPlate('s', i, curPos[i]);
  };
  wrap.addEventListener('pointerup', finish);
  wrap.addEventListener('pointercancel', finish);
}
function refreshSetup() { for (let i = 0; i < N; i++) setPlate('s', i, curPos[i]); }
window.addEventListener('resize', () => {
  refreshSetup();
  if (!document.getElementById('solution').classList.contains('hidden')) render();
});

/* ================= manual matrix ================= */
const linkTable = document.getElementById('linkTable');
let head = '<tr><th></th>';
for (let j = 1; j <= N; j++) head += `<th>${plateIcon(j, 'aff')}</th>`;
linkTable.innerHTML = head + '</tr>';
for (let i = 1; i <= N; i++) {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td class="rowhead">${plateIcon(i)}</td>`;
  for (let j = 1; j <= N; j++) {
    const td = document.createElement('td');
    if (i === j) { td.textContent = '\u2014'; td.style.color = 'var(--edge)'; }
    else {
      const sel = document.createElement('select');
      sel.id = `link${i}_${j}`;
      sel.add(new Option('\u00b7', '0'));
      sel.add(new Option('reg', '1'));
      sel.add(new Option('rev', '-1'));
      sel.onchange = () => { sel.className = sel.value === '1' ? 'reg' : sel.value === '-1' ? 'rev' : ''; };
      td.appendChild(sel);
    }
    tr.appendChild(td);
  }
  linkTable.appendChild(tr);
}
function setLink(i, j, v) {
  const sel = document.getElementById(`link${i}_${j}`);
  sel.value = String(v); sel.onchange();
}
function getLink(i, j) { return +document.getElementById(`link${i}_${j}`).value; }
function knownRow(i) {
  const r = {};
  for (let j = 1; j <= N; j++) {
    if (j === i) continue;
    const v = getLink(i, j);
    if (v !== 0) r[j] = v;
  }
  return r;
}

/* ================= link wizard =================
   Flow: idle -> pick (auto) -> await -> [confirm | blocked] -> pick ... -> done
   In 'await', the user performs the instructed move IN GAME, then drags the
   plates above to mirror the result and hits Confirm. Links are derived from
   the before/after diff. 'Blocked' restores the snapshot.                  */
let wizTested = new Set();
let wizCur = null, wizDir = 0, wizSnap = null, wizRisk = '';
let wizBlockedDirs = {};
let wizPhase = 'idle';

function edgeList(excl) {
  const out = [];
  for (let k = 0; k < N; k++) {
    if (k === excl) continue;
    if (curPos[k] === 1 || curPos[k] === MAXPOS) out.push(k);
  }
  return out;
}
function dirCandidates(i0) {
  const i = i0 + 1, pos = curPos[i0], row = knownRow(i);
  const cands = [];
  for (const d of [-1, 1]) {
    if (wizBlockedDirs[d]) continue;
    if (pos + d < 1 || pos + d > MAXPOS) continue;
    let det = false;
    for (const j in row) {
      const nj = curPos[j - 1] + row[j] * d;
      if (nj < 1 || nj > MAXPOS) { det = true; break; }
    }
    if (det) continue;
    let risk = 0;
    for (const k of edgeList(i0)) if (!((k + 1) in row)) risk++;
    const towardMid = Math.abs(pos + d - GOAL) < Math.abs(pos - GOAL) ? 0 : 1;
    cands.push({ d, risk, towardMid });
  }
  cands.sort((a, b) => a.risk - b.risk || a.towardMid - b.towardMid);
  return cands;
}
function pickNext() {
  const un = [...Array(N).keys()].filter(k => !wizTested.has(k));
  if (!un.length) return null;
  un.sort((a, b) => {
    const ea = (curPos[a] === 1 || curPos[a] === MAXPOS) ? 0 : 1;
    const eb = (curPos[b] === 1 || curPos[b] === MAXPOS) ? 0 : 1;
    return ea - eb || a - b;
  });
  for (const k of un) {
    const save = wizBlockedDirs; wizBlockedDirs = {};
    const ok = dirCandidates(k).length > 0;
    wizBlockedDirs = save;
    if (ok) return k;
  }
  return un[0];
}

const wizBox = document.getElementById('wizard');
function wizReset() { wizTested = new Set(); wizPhase = 'idle'; wizCur = null; renderWizard(); }

function renderWizard() {
  if (wizPhase === 'idle') {
    wizBox.innerHTML = `
      <div class="hint">1. Drag the plates above to match the game exactly.<br>
      2. Start the wizard &mdash; it will tell you which arrow to press, choosing moves
      that cannot be blocked whenever possible (blocked attempts cost!).<br>
      3. After each move, drag the plates above to mirror what you see in the game and confirm.
      The links are worked out automatically from the difference.</div>
      <div class="wiznav"><button id="wizStart">Start wizard</button></div>`;
    document.getElementById('wizStart').onclick = () => { wizPhase = 'pick'; renderWizard(); };
    return;
  }

  if (wizPhase === 'pick') {
    const nxt = pickNext();
    if (nxt === null) {
      wizPhase = 'done';
      wizBox.innerHTML = `<div class="wizhint">All plates tested &mdash; links are in the matrix below and
        the positions above match the game. Hit <b>Solve</b>.
        <div class="wiznav"><button class="ghost" id="wizAgain">Run wizard again</button></div></div>`;
      document.getElementById('matrixDetails').open = true;
      document.getElementById('wizAgain').onclick = () => { wizTested = new Set(); wizPhase = 'pick'; renderWizard(); };
      return;
    }
    wizCur = nxt; wizBlockedDirs = {};
    prepInstruct();
  }

  const i = wizCur + 1;
  const headHtml = `<div class="wizhead">
      <span class="which">Testing plate ${i}</span>
      <span class="count">${wizTested.size} / ${N} done</span>
    </div>`;

  if (wizPhase === 'await') {
    if (wizDir === 0) {
      wizBox.innerHTML = headHtml + `
        <div class="wizhint caution">No safe direction available for plate ${i} right now
        (edges or known links block everything). Skip it and rerun the wizard later.</div>
        <div class="wiznav"><button class="ghost" id="wizSkip">Skip plate ${i}</button></div>`;
      document.getElementById('wizSkip').onclick = wizSkip;
      return;
    }
    let html = headHtml + `
      <div class="wizmove">${bigMove(i, wizDir)}</div>
      <div class="hint">Do this move in the game. Then <b>drag the plates above</b> so they
      show exactly what you see now (including any plates that moved along), and press Confirm.
      If the move was blocked, just press Confirm without dragging anything.</div>`;
    if (wizRisk) {
      html += `<div class="wizhint caution">Heads up: ${wizRisk} stand at an edge and plate ${i}'s links
        are unknown, so this <b>could</b> be blocked &mdash; no safer test exists right now.</div>`;
    }
    html += `<div id="wizMsg"></div>
      <div class="wiznav">
        <button id="wizOk">Confirm new state</button>
        <button class="ghost" id="wizSkip">Skip</button>
      </div>`;
    wizBox.innerHTML = html;
    document.getElementById('wizSkip').onclick = wizSkip;
    document.getElementById('wizOk').onclick = wizConfirm;
    return;
  }

  if (wizPhase === 'blocked') {
    const suspects = [];
    for (const k of edgeList(wizCur)) {
      const sign = curPos[k] === MAXPOS ? (wizDir === 1 ? 1 : -1)
                                        : (wizDir === 1 ? -1 : 1);
      suspects.push({ k, sign });
    }
    let auto = '';
    if (suspects.length === 1) {
      const s = suspects[0];
      setLink(i, s.k + 1, s.sign);
      auto = `Only <b>P${s.k + 1}</b> stands at an edge, so plate ${i} must be linked to it
        <b>${s.sign === 1 ? 'reg (same direction)' : 'rev (opposite)'}</b> &mdash; filled in.`;
    } else if (suspects.length > 1) {
      auto = `Plates at edges: ${suspects.map(s =>
        `<b>P${s.k + 1}</b> (${s.sign === 1 ? 'reg' : 'rev'} if it is the culprit)`).join(', ')}.
        At least one of these links exists &mdash; the next successful move of plate ${i} will tell which.`;
    } else {
      auto = `Strange &mdash; no plate stands at an edge, so this block should be impossible.
        Double-check the positions above match the game.`;
    }
    let html = headHtml +
      `<div class="wizhint caution">Blocked &mdash; positions unchanged. ${auto}</div><div class="wiznav">`;
    const more = dirCandidates(wizCur);
    if (more.length) html += `<button id="wizOther">Try ${gameArrow(more[0].d)} instead</button>`;
    html += `<button class="ghost" id="wizSkip">Skip plate ${i}</button></div>`;
    wizBox.innerHTML = html;
    if (more.length) document.getElementById('wizOther').onclick = () => { prepInstruct(); renderWizard(); };
    document.getElementById('wizSkip').onclick = wizSkip;
    return;
  }
}

function prepInstruct() {
  const cands = dirCandidates(wizCur);
  if (!cands.length) { wizDir = 0; wizRisk = ''; }
  else {
    wizDir = cands[0].d;
    wizSnap = curPos.slice();
    wizRisk = cands[0].risk > 0
      ? edgeList(wizCur).map(k => 'P' + (k + 1)).join(', ') : '';
  }
  wizPhase = 'await';
}
function wizSkip() { wizTested.add(wizCur); wizCur = null; wizPhase = 'pick'; renderWizard(); }
function wizConfirm() {
  const i = wizCur + 1;
  const msgBox = document.getElementById('wizMsg');
  const d = curPos[wizCur] - wizSnap[wizCur];
  const othersChanged = [...Array(N).keys()]
    .some(k => k !== wizCur && curPos[k] !== wizSnap[k]);

  if (d === 0) {
    if (othersChanged) {
      msgBox.innerHTML = `<div class="wizhint caution">Plate ${i} is unchanged but other plates were
        dragged &mdash; that can't result from this move. If plate ${i} really didn't move,
        drag the others back; otherwise drag plate ${i} to its new notch.</div>`;
      return;
    }
    /* nothing changed at all -> the move was blocked */
    wizBlockedDirs[wizDir] = true;
    wizPhase = 'blocked'; renderWizard();
    return;
  }

  const problems = [];
  if (Math.abs(d) > 1) problems.push(`Plate ${i} moved ${Math.abs(d)} steps above &mdash; tests are
    single-step, please re-drag.`);
  for (let k = 0; k < N; k++) {
    if (k === wizCur) continue;
    if (Math.abs(curPos[k] - wizSnap[k]) > 1)
      problems.push(`P${k + 1} moved more than one step &mdash; that can't result from a single move, please re-drag.`);
  }
  if (problems.length) {
    msgBox.innerHTML = `<div class="wizhint caution">${problems.join('<br>')}</div>`;
    return;
  }
  for (let k = 0; k < N; k++) {
    if (k === wizCur) continue;
    const dk = curPos[k] - wizSnap[k];
    setLink(i, k + 1, dk === 0 ? 0 : dk * d);   // dk/d = dk*d for d = +-1
  }
  wizTested.add(wizCur); wizCur = null; wizPhase = 'pick';
  renderWizard();
}

/* ================= defaults / reset ================= */
function applyDefaults() {
  for (let i = 0; i < N; i++) curPos[i] = DEF_START[i];
  refreshSetup();
  for (let i = 1; i <= N; i++)
    for (let j = 1; j <= N; j++) {
      if (i === j) continue;
      setLink(i, j, (DEF_LINKS[i] && DEF_LINKS[i][j]) || 0);
    }
  wizReset();
}
document.getElementById('resetBtn').onclick = applyDefaults;

/* ================= solve ================= */
let moves = [], startState = [], step = 0, solBuilt = false;

document.getElementById('solveBtn').onclick = async () => {
  const links = {};
  for (let i = 1; i <= N; i++) {
    links[i] = {};
    for (let j = 1; j <= N; j++) {
      if (i === j) continue;
      const v = getLink(i, j);
      if (v !== 0) links[i][j] = v;
    }
  }
  const err = document.getElementById('errBox');
  err.style.display = 'none';
  const btn = document.getElementById('solveBtn');
  btn.disabled = true; btn.textContent = 'Solving\u2026';
  try {
    const r = await fetch('/api/solve', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({start: curPos, links})
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Server error');
    if (!data.solvable) throw new Error('No solution exists for this configuration.');
    moves = data.moves; startState = data.start; step = 0;
    document.getElementById('setup').classList.add('hidden');
    document.getElementById('solution').classList.remove('hidden');
    if (!solBuilt) {
      const box = document.getElementById('solPlates');
      for (let i = 0; i < N; i++) makePlateRow(box, i, 'q');
      solBuilt = true;
    }
    render();
  } catch (e) {
    err.textContent = e.message; err.style.display = 'block';
  } finally {
    btn.disabled = false; btn.textContent = 'Solve';
  }
};

document.getElementById('backBtn').onclick = () => {
  document.getElementById('solution').classList.add('hidden');
  document.getElementById('setup').classList.remove('hidden');
  refreshSetup();
};

/* ================= step view ================= */
function stateAt(k) { return k === 0 ? startState : moves[k - 1].state; }

function render() {
  const st = stateAt(step);
  const done = step === moves.length;
  for (let i = 0; i < N; i++) {
    setPlate('q', i, st[i]);
    document.getElementById('qplate' + i).classList.toggle(
      'active', !done && (moves[step].plate - 1) === i);
  }
  const instr = document.getElementById('instr');
  const banner = document.getElementById('doneBanner');
  if (done) { instr.style.display = 'none'; banner.style.display = 'block'; }
  else {
    instr.style.display = 'flex'; banner.style.display = 'none';
    const mv = moves[step];
    instr.innerHTML = bigMove(mv.plate, mv.dir);
  }
  document.getElementById('progBar').style.width = (step / moves.length * 100) + '%';
  document.getElementById('stepInfo').textContent =
    done ? `Finished \u2014 ${moves.length} moves total` : `Step ${step + 1} of ${moves.length}`;
  document.getElementById('prevBtn').disabled = step === 0;
  document.getElementById('nextBtn').disabled = done;
}

document.getElementById('nextBtn').onclick = () => { if (step < moves.length) { step++; render(); } };
document.getElementById('prevBtn').onclick = () => { if (step > 0) { step--; render(); } };
document.addEventListener('keydown', e => {
  if (document.getElementById('solution').classList.contains('hidden')) return;
  if (e.key === 'ArrowRight') document.getElementById('nextBtn').click();
  if (e.key === 'ArrowLeft') document.getElementById('prevBtn').click();
});

/* init */
applyDefaults();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    import json
    return render_template_string(
        PAGE,
        default_start=json.dumps(DEFAULT_START),
        default_links=json.dumps({k: v for k, v in DEFAULT_LINKS.items()}),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
