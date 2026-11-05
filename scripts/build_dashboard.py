"""Build out/dashboard.html from out/comparison.csv.

The page is a single self-contained HTML file (no internet needed): the race rows are embedded
as JSON and drawn with plain JavaScript + SVG. Open it by double-clicking.

Usage: python scripts/build_dashboard.py [--highlight "F4 Saudi Arabia"]
"""
import argparse
import csv
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NUMERIC = ["cars", "total_laps", "neutralised_laps", "green_laps", "neutralised_pct",
           "neutralised_time_pct", "red_flag_minutes", "median_green_lap_s"]

# Known data gaps, shown on the page so nobody over-reads the numbers.
CAVEATS = [
    "F4 Middle East Round 5 (Lusail, 3 races) is not published online, so 12 of 15 races are included.",
    "Italian F4 Barcelona Race 2 has no published timing (Race 3 there was abandoned).",
    "British F4 Zandvoort Rounds 17 and 18 were red-flagged; only the post-restart laps are published.",
    "Red-flag minutes are only detected when the stoppage sits inside one timed lap (F4 Middle East). "
    "Where timing restarts after a red flag (most British/Italian cases) the stopped time is not counted.",
    "Laps are classified from lap times only and not yet cross-checked with race-control messages, "
    "so a Safety Car can't be told apart from a Full Course Yellow, and a very short FCY that slows "
    "the leaders by less than 25% would be missed.",
]

# The page explains the rule using the same numbers the analysis used.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyse_laps import RED_FLAG_FACTOR, THRESHOLD  # noqa: E402


def load_rows(path):
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            for k in NUMERIC:
                r[k] = float(r[k]) if r.get(k) not in (None, "") else 0.0
            r["pace"] = [float(x) for x in (r.pop("lead_pace_s", "") or "").split(";") if x]
            r.pop("source", None)
            rows.append(r)
    return rows


def summarise(rows):
    out = []
    for s in dict.fromkeys(r["series"] for r in rows):
        rs = [r for r in rows if r["series"] == s]
        laps = sum(r["total_laps"] for r in rs)
        neut = sum(r["neutralised_laps"] for r in rs)
        out.append({
            "series": s, "races": len(rs), "laps": int(laps), "neutralised": int(neut),
            "neutralised_pct": round(100 * neut / laps, 1),
            "green_per_race": round(sum(r["green_laps"] for r in rs) / len(rs), 1),
            "clean_races": sum(1 for r in rs if r["neutralised_laps"] == 0),
            "clean_pct": round(100 * sum(1 for r in rs if r["neutralised_laps"] == 0) / len(rs)),
            "worst": max(rs, key=lambda r: r["neutralised_pct"]),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "out" / "comparison.csv"))
    ap.add_argument("--out", default=str(ROOT / "out" / "dashboard.html"))
    ap.add_argument("--highlight", default="F4 Saudi Arabia")
    a = ap.parse_args()
    rows = load_rows(a.csv)
    data = {
        "rows": rows, "summary": summarise(rows), "highlight": a.highlight, "caveats": CAVEATS,
        "threshold": THRESHOLD, "red_flag_factor": RED_FLAG_FACTOR,
        "built": datetime.date.today().isoformat(),
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    pathlib.Path(a.out).write_text(html, encoding="utf-8")
    print(f"wrote {a.out} ({len(rows)} races, {len(data['summary'])} series)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>F4 Flag Tracker</title>
<style>
:root {
  color-scheme: light;
  --surface-0: #f5f4f1; --surface-1: #fcfcfb; --border: #e3e2de; --grid: #ebeae6;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #6f6e69;
  --hl: #9e1b32; --hl-soft: #f5d6db; --other: #8a8984; --other-soft: #e3e2de;
  --neut: #eda100; --neut-soft: #fde7b0; --red: #d03b3b; --red-soft: #f3c4c4;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c; --grid: #262624;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #9a998f;
    --hl: #e8333f; --hl-soft: #4d1219; --other: #75746f; --other-soft: #383835;
    --neut: #fab219; --neut-soft: #5c4300; --red: #e66767; --red-soft: #4a1c1c;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c; --grid: #262624;
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #9a998f;
  --hl: #e8333f; --hl-soft: #4d1219; --other: #75746f; --other-soft: #383835;
    --neut: #fab219; --neut-soft: #5c4300; --red: #e66767; --red-soft: #4a1c1c;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface-0); color: var(--text-primary); border-top: 5px solid var(--hl);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1080px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 28px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 17px; margin: 0 0 4px; }
.sub { color: var(--text-secondary); margin: 0 0 24px; max-width: 70ch; }
.note { color: var(--text-muted); font-size: 13px; margin: 0 0 16px; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px;
  padding: 20px; margin-bottom: 20px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;
  margin-bottom: 20px; }
.tile { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.tile.hl { border-color: var(--hl); box-shadow: inset 4px 0 0 var(--hl); }
.tile .name { color: var(--text-secondary); font-size: 13px; font-weight: 600; }
.tile .big { font-size: 34px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.15; }
.tile .small { color: var(--text-muted); font-size: 13px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 760px) { .grid2 { grid-template-columns: 1fr; } }
svg { display: block; width: 100%; height: auto; overflow: visible; }
svg text { fill: var(--text-secondary); font-size: 12px; }
svg .lbl { fill: var(--text-primary); font-weight: 600; font-variant-numeric: tabular-nums; }
.legend { display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary); margin: 4px 0 8px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px;
  vertical-align: -1px; }
.tip { position: fixed; pointer-events: none; background: var(--surface-1); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 13px;
  box-shadow: 0 4px 16px rgba(0,0,0,.15); opacity: 0; transition: opacity .1s; max-width: 280px; z-index: 10; }
.tip b { display: block; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; align-items: center; }
.controls button { font: inherit; font-size: 13px; padding: 6px 12px; border-radius: 999px;
  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary); cursor: pointer; }
.controls button[aria-pressed="true"] { background: var(--text-primary); color: var(--surface-1); border-color: var(--text-primary); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--grid); white-space: nowrap; }
th { color: var(--text-secondary); font-weight: 600; cursor: pointer; user-select: none; }
th.num, td.num { text-align: right; }
tr.hl td:first-child { box-shadow: inset 3px 0 0 var(--hl); }
.bar-cell { display: inline-block; height: 8px; border-radius: 4px; vertical-align: middle; margin-right: 6px; }
ul.caveats { margin: 0; padding-left: 18px; color: var(--text-secondary); font-size: 14px; }
ul.caveats li { margin-bottom: 6px; }
.defs { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin: 12px 0 20px; }
.def { border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
.def > b { display: block; margin-bottom: 4px; }
.def p { margin: 0; color: var(--text-secondary); font-size: 14px; }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: 0; }
h3 { font-size: 15px; margin: 20px 0 8px; }
.neut-word { color: var(--neut); }
.rf-swatch { background: repeating-linear-gradient(135deg, var(--red) 0 2px, var(--red-soft) 2px 4px) !important; }
/* collapsible explainer: the whole heading row is the click target, chevron rotates when open */
details > summary { list-style: none; cursor: pointer; position: relative; padding-right: 36px; }
details > summary::-webkit-details-marker { display: none; }
details > summary h2 { display: inline; margin: 0; }
details > summary .toggle-hint { display: block; color: var(--text-muted); font-size: 13px; margin-top: 2px; }
details > summary::after { content: ""; position: absolute; right: 6px; top: 6px; width: 9px; height: 9px;
  border-right: 2px solid var(--text-secondary); border-bottom: 2px solid var(--text-secondary);
  transform: rotate(45deg); transition: transform .15s; }
details[open] > summary::after { transform: rotate(-135deg); top: 10px; }
details > summary:focus-visible { outline: 2px solid var(--hl); outline-offset: 4px; border-radius: 4px; }
details[open] > summary .toggle-hint { display: none; }
table.rules td { white-space: normal; vertical-align: top; }
table.rules td:first-child { font-weight: 600; width: 30%; }
table.rules td:nth-child(2) { width: 14%; }
.yes, .no { display: inline-block; font-weight: 600; font-size: 12px; padding: 1px 8px; border-radius: 999px; }
.yes { background: var(--neut-soft); color: var(--text-primary); }
.no { background: var(--other-soft); color: var(--text-primary); }
ol.steps { margin: 0 0 8px; padding-left: 20px; color: var(--text-secondary); font-size: 14px; }
ol.steps li { margin-bottom: 4px; }
ol.steps b { color: var(--text-primary); }
.ex-head { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin: 4px 0 8px; }
.ex-head select { font: inherit; font-size: 13px; padding: 5px 8px; border-radius: 8px; max-width: 100%;
  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary); }
#ex-summary { color: var(--text-secondary); font-size: 13px; margin: 6px 0 0; }
</style>
</head>
<body>
<main>
  <h1>F4 Flag Tracker — 2025</h1>
  <p class="sub" id="lede"></p>

  <div class="tiles" id="tiles"></div>

  <details class="card" id="explainer">
    <summary>
      <h2>What does “<span class="neut-word">Neutralised</span>” mean?</h2>
      <span class="toggle-hint">Definitions, what counts as a yellow / red flag, and how laps are flagged</span>
    </summary>
    <p class="note" style="margin:12px 0 0">Everything on this page counts <b>race laps</b> only: no practice,
      qualifying or formation laps.</p>
    <div class="defs">
      <div class="def"><b><span class="swatch" style="background:var(--neut)"></span>Neutralised lap</b>
        <p>A race lap where the <b>whole field</b> was slowed and no racing was possible: behind the
        Safety Car, under a Full Course Yellow, or a lap interrupted by a red flag. These are the
        “wasted” laps: they count towards race distance but nobody is racing.</p></div>
      <div class="def"><b><span class="swatch" style="background:var(--other)"></span>Green lap</b>
        <p>Every other race lap: the field is racing at full speed, even if there was a waved yellow
        somewhere on the circuit.</p></div>
      <div class="def"><b>Clean race</b>
        <p>A race with <b>zero</b> neutralised laps from start to flag.</p></div>
      <div class="def"><b><span class="swatch rf-swatch"></span>Red-flag minutes</b>
        <p>Time the race was stopped, when it shows up inside a timed lap. The lap itself is also
        counted as neutralised.</p></div>
    </div>

    <h3>What counts and what doesn't</h3>
    <div class="table-wrap"><table class="rules">
      <thead><tr><th>Situation</th><th>Neutralised?</th><th>Why</th></tr></thead>
      <tbody>
        <tr><td>Safety Car period</td><td><span class="yes">Yes</span></td>
          <td>The whole field queues behind the Safety Car. These laps run roughly 40–100% slower than racing pace,
            so they are always caught.</td></tr>
        <tr><td>Full Course Yellow (FCY) / Virtual Safety Car</td><td><span class="yes">Yes</span></td>
          <td>A speed limit applies across the whole track, so every car slows. Counted when it slows the leaders by more
            than <span class="thr-pct"></span> on that lap. A very short FCY that clips one lap only slightly can fall under that.</td></tr>
        <tr><td>Red flag (race stopped)</td><td><span class="yes">Yes</span></td>
          <td>The lap the race is stopped on, plus any Safety Car laps after the restart. If the stoppage happens
            inside a timed lap (lap more than <span class="rf-x"></span> normal pace), its length is also shown in red-flag minutes.</td></tr>
        <tr><td>Safety Car start (lap 1 behind the SC)</td><td><span class="yes">Yes</span></td>
          <td>Same as any Safety Car lap.</td></tr>
        <tr><td>Local / waved yellow at one marshal post</td><td><span class="no">No</span></td>
          <td>No overtaking in one sector only. The rest of the lap is raced and the leaders lose a second or two,
            far under the <span class="thr-pct"></span> threshold. This is <b>not</b> what the tracker is measuring.</td></tr>
        <tr><td>Normal standing-start lap 1</td><td><span class="no">No</span></td>
          <td>Lap 1 is a bit slower (about 5–15%) because cars start from rest, but it is raced.</td></tr>
        <tr><td>One driver spins, crashes or pits</td><td><span class="no">No</span></td>
          <td>Only the top 3 finishers' lap times are used and the middle one is taken, so one car's
            problem can't flag a lap. It only counts if the incident brings out a Safety Car or FCY.</td></tr>
        <tr><td>Formation lap</td><td><span class="no">No</span></td>
          <td>Not a race lap, so it is not in the timing data.</td></tr>
      </tbody>
    </table></div>

    <h3>How a lap gets flagged</h3>
    <ol class="steps">
      <li><b>Lead pace:</b> for every lap, take the lap times of the top 3 finishers and use the middle one.</li>
      <li><b>Normal pace:</b> the race's typical full-speed lap (the median of laps within 10% of the
        quickest lead-pace lap).</li>
      <li><b>Neutralised</b> if lead pace is more than <span class="thr-x"></span> normal pace
        (<span class="thr-pct"></span> slower). <b>Red flag</b> if it is more than <span class="rf-x"></span> normal pace.</li>
    </ol>

    <div class="ex-head">
      <label for="ex-race" class="note" style="margin:0">See it on a real race:</label>
      <select id="ex-race"></select>
    </div>
    <div class="legend">
      <span><i style="background:var(--other);border-radius:2px"></i>Green lap</span>
      <span><i style="background:var(--neut);border-radius:2px"></i>Neutralised lap</span>
      <span><i class="rf-swatch" style="border-radius:2px"></i>Red-flag lap</span>
    </div>
    <div id="example"></div>
    <p id="ex-summary"></p>
  </details>

  <div class="grid2">
    <section class="card">
      <h2>Share of laps neutralised</h2>
      <p class="note">Safety Car / Full Course Yellow laps ÷ all race laps, whole season.</p>
      <div id="bar-neut"></div>
    </section>
    <section class="card">
      <h2>Races with no neutralised laps</h2>
      <p class="note">Percentage of each series' races that ran fully green.</p>
      <div id="bar-clean"></div>
    </section>
  </div>

  <section class="card">
    <h2>Every race, one dot each</h2>
    <p class="note">Neutralised share of each race. Hover a dot for the race. Dots at 0% ran fully green.</p>
    <div class="legend"><span><i style="background:var(--hl)"></i><span id="lg-hl"></span></span>
      <span><i style="background:var(--other)"></i>Other series</span></div>
    <div id="strip"></div>
  </section>

  <details class="card" id="race-table">
    <summary>
      <h2>Race by race</h2>
      <span class="toggle-hint" id="race-hint">Every race in a table you can filter and sort</span>
    </summary>
    <div class="controls" id="filters" style="margin-top:14px"></div>
    <div class="table-wrap"><table id="tbl"></table></div>
  </details>

  <section class="card">
    <h2>How to read this — and what's missing</h2>
    <ul class="caveats" id="caveats"></ul>
    <p class="note" id="built" style="margin:12px 0 0"></p>
  </section>
</main>
<div class="tip" id="tip" role="tooltip"></div>

<script>
const DATA = __DATA__;
const HL = DATA.highlight;
const $ = (id) => document.getElementById(id);
const fmt = (n, d = 1) => Number(n).toFixed(d);
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const isHL = (s) => s === HL;
const NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}, parent) => { const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };

// ---------- tooltip ----------
const tip = $("tip");
function showTip(html, ev) { tip.innerHTML = html; tip.style.opacity = 1; moveTip(ev); }
function moveTip(ev) { const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + w > innerWidth - 8) x = ev.clientX - w - pad; if (y + h > innerHeight - 8) y = ev.clientY - h - pad;
  tip.style.left = x + "px"; tip.style.top = y + "px"; }
function hideTip() { tip.style.opacity = 0; }

// ---------- headline ----------
const sum = DATA.summary;
const hl = sum.find(s => isHL(s.series));
const others = sum.filter(s => !isHL(s.series));
if (hl && others.length) {
  const avg = others.reduce((a, s) => a + s.neutralised, 0) / others.reduce((a, s) => a + s.laps, 0) * 100;
  $("lede").textContent = `${HL} lost ${fmt(hl.neutralised_pct)}% of its race laps to Safety Car or Full Course `
    + `Yellow periods, against ${fmt(avg)}% across ${others.map(s => s.series).join(", ")} combined `
    + `— about ${fmt(avg / hl.neutralised_pct, 1)}× less neutralised running.`;
}
$("lg-hl").textContent = HL;

// ---------- tiles ----------
const order = [...sum].sort((a, b) => a.neutralised_pct - b.neutralised_pct);
$("tiles").innerHTML = order.map(s => `
  <div class="tile ${isHL(s.series) ? "hl" : ""}">
    <div class="name">${esc(s.series)}</div>
    <div class="big">${fmt(s.neutralised_pct)}%</div>
    <div class="small">${s.neutralised} of ${s.laps} laps neutralised · ${s.races} races</div>
    <div class="small">${fmt(s.green_per_race)} green laps per race</div>
  </div>`).join("");

// ---------- horizontal bar chart ----------
function hbar(target, items, valueKey, labelFn, tipFn) {
  const W = 480, rowH = 40, left = 130, right = 56, H = items.length * rowH + 8;
  const max = Math.max(...items.map(d => d[valueKey])) * 1.05 || 1;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": items.map(d => `${d.series} ${labelFn(d)}`).join(", ") });
  const x = v => left + (W - left - right) * v / max;
  items.forEach((d, i) => {
    const y = i * rowH + 8, bh = 20;
    el("text", { x: left - 10, y: y + bh / 2 + 4, "text-anchor": "end",
      style: isHL(d.series) ? "fill:var(--text-primary);font-weight:600" : "" }, svg).textContent = d.series;
    const w = Math.max(2, x(d[valueKey]) - left);
    // bar anchored at the baseline: square at the axis, 4px rounded at the data end
    el("path", { d: `M${left},${y} h${w - 4} a4,4 0 0 1 4,4 v${bh - 8} a4,4 0 0 1 -4,4 h${-(w - 4)} z`,
      fill: isHL(d.series) ? "var(--hl)" : "var(--other)" }, svg);
    el("text", { x: left + w + 8, y: y + bh / 2 + 4, class: "lbl" }, svg).textContent = labelFn(d);
    const hit = el("rect", { x: 0, y: y - 8, width: W, height: rowH, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", ev => showTip(tipFn(d), ev));
    hit.addEventListener("mouseleave", hideTip);
  });
  el("line", { x1: left, x2: left, y1: 0, y2: H, stroke: "var(--border)" }, svg);
  $(target).appendChild(svg);
}
hbar("bar-neut", order, "neutralised_pct", d => fmt(d.neutralised_pct) + "%",
  d => `<b>${esc(d.series)}</b>${d.neutralised} of ${d.laps} laps neutralised<br>Worst race: ${esc(d.worst.event)} ${esc(d.worst.race)} (${fmt(d.worst.neutralised_pct)}%)`);
hbar("bar-clean", [...sum].sort((a, b) => b.clean_pct - a.clean_pct), "clean_pct", d => d.clean_pct + "%",
  d => `<b>${esc(d.series)}</b>${d.clean_races} of ${d.races} races fully green`);

// ---------- strip plot: one dot per race ----------
(function strip() {
  const W = 960, left = 130, right = 24, rowH = 54, top = 8, bottom = 28;
  const series = order.map(s => s.series), H = top + series.length * rowH + bottom;
  const max = Math.max(50, Math.ceil(Math.max(...DATA.rows.map(r => r.neutralised_pct)) / 10) * 10);
  const x = v => left + (W - left - right) * v / max;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Neutralised share of every race, by series" });
  for (let t = 0; t <= max; t += 10) {
    el("line", { x1: x(t), x2: x(t), y1: top, y2: H - bottom, stroke: "var(--grid)" }, svg);
    el("text", { x: x(t), y: H - 8, "text-anchor": "middle" }, svg).textContent = t + "%";
  }
  series.forEach((s, i) => {
    const cy = top + i * rowH + rowH / 2;
    el("text", { x: left - 12, y: cy + 4, "text-anchor": "end",
      style: isHL(s) ? "fill:var(--text-primary);font-weight:600" : "" }, svg).textContent = s;
    const rs = DATA.rows.filter(r => r.series === s);
    // Group races with the same (rounded) value. Small ties stack vertically inside the row;
    // big ties (e.g. many fully-green races at 0%) collapse into one dot with a count label.
    const groups = {};
    rs.forEach(r => (groups[Math.round(r.neutralised_pct)] ||= []).push(r));
    Object.values(groups).forEach(g => {
      const big = g.length > 4;
      (big ? [g] : g.map(r => [r])).forEach((members, j) => {
        const r = members[0], off = big ? 0 : (j % 2 ? 1 : -1) * Math.ceil(j / 2) * 9;
        const cx = x(r.neutralised_pct), rad = big ? 7 : 5;
        const c = el("circle", { cx, cy: cy + off, r: rad,
          fill: isHL(s) ? "var(--hl)" : "var(--other)", stroke: "var(--surface-1)", "stroke-width": 2 }, svg);
        if (big) el("text", { x: cx + 12, y: cy + 4, class: "lbl" }, svg).textContent = `×${members.length}`;
        const hit = el("circle", { cx, cy: cy + off, r: 11, fill: "transparent" }, svg);
        const html = big
          ? `<b>${esc(s)}</b>${members.length} races at ${fmt(r.neutralised_pct, 0)}% neutralised:<br>`
            + members.map(m => `${esc(m.event)} · ${esc(m.race)}`).join("<br>")
          : `<b>${esc(r.series)}</b>${esc(r.event)} · ${esc(r.race)}<br>${r.neutralised_laps} of ${r.total_laps} laps neutralised (${fmt(r.neutralised_pct)}%)`
            + (r.neutralised_lap_numbers ? `<br>Laps: ${esc(prettyLaps(r.neutralised_lap_numbers))}` : "");
        hit.addEventListener("mousemove", ev => { c.setAttribute("r", rad + 2); showTip(html, ev); });
        hit.addEventListener("mouseleave", () => { c.setAttribute("r", rad); hideTip(); });
      });
    });
  });
  $("strip").appendChild(svg);
})();

// ---------- table with filter + sort ----------
const COLS = [
  ["series", "Series"], ["event", "Event"], ["race", "Race"], ["total_laps", "Laps", 1],
  ["neutralised_laps", "Neutralised", 1], ["neutralised_pct", "Neutralised %", 1],
  ["green_laps", "Green laps", 1], ["red_flag_minutes", "Red flag (min)", 1],
  ["neutralised_lap_numbers", "Which laps"],
];
let filter = "All", sortKey = null, sortDir = 1;
const fwrap = $("filters");
["All", ...order.map(s => s.series)].forEach(name => {
  const b = document.createElement("button"); b.textContent = name; b.setAttribute("aria-pressed", name === filter);
  b.onclick = () => { filter = name; [...fwrap.children].forEach(c => c.setAttribute("aria-pressed", c === b)); renderTable(); };
  fwrap.appendChild(b);
});
function renderTable() {
  let rows = DATA.rows.filter(r => filter === "All" || r.series === filter);
  if (sortKey) rows = [...rows].sort((a, b) => (a[sortKey] > b[sortKey] ? 1 : a[sortKey] < b[sortKey] ? -1 : 0) * sortDir);
  const maxPct = Math.max(...DATA.rows.map(r => r.neutralised_pct)) || 1;
  $("tbl").innerHTML = `<thead><tr>${COLS.map(([k, l, n]) =>
      `<th class="${n ? "num" : ""}" data-k="${k}">${l}${sortKey === k ? (sortDir > 0 ? " ↑" : " ↓") : ""}</th>`).join("")}</tr></thead>
    <tbody>${rows.map(r => `<tr class="${isHL(r.series) ? "hl" : ""}">${COLS.map(([k, , n]) => {
      if (k === "neutralised_pct") return `<td class="num"><span class="bar-cell" style="width:${Math.max(2, 60 * r[k] / maxPct)}px;background:${isHL(r.series) ? "var(--hl)" : "var(--other)"}"></span>${fmt(r[k])}%</td>`;
      if (k === "red_flag_minutes") return `<td class="num">${r[k] ? fmt(r[k]) : "–"}</td>`;
      if (k === "neutralised_lap_numbers") return `<td>${r[k] ? esc(prettyLaps(r[k])) : "–"}</td>`;
      return `<td class="${n ? "num" : ""}">${n ? Math.round(r[k]) : esc(r[k] || "–")}</td>`;
    }).join("")}</tr>`).join("")}</tbody>`;
  [...$("tbl").querySelectorAll("th")].forEach(th => th.onclick = () => {
    const k = th.dataset.k; sortDir = sortKey === k ? -sortDir : (k.includes("pct") || k.includes("laps") ? -1 : 1);
    sortKey = k; renderTable(); });
}
renderTable();
$("race-hint").textContent = `All ${DATA.rows.length} races in a table you can filter by series and sort by any column`;

// ---------- explainer: thresholds + example race chart ----------
const T = DATA.threshold, RF = DATA.red_flag_factor;
document.querySelectorAll(".thr-pct").forEach(e => e.textContent = Math.round((T - 1) * 100) + "%");
document.querySelectorAll(".thr-x").forEach(e => e.textContent = T + "×");
document.querySelectorAll(".rf-x").forEach(e => e.textContent = RF + "×");

(function example() {
  const sel = $("ex-race");
  const withPace = DATA.rows.map((r, i) => ({ r, i })).filter(o => o.r.pace.length);
  // group options by series; default = the highlight series' race with the most neutralised laps
  order.forEach(s => {
    const g = document.createElement("optgroup"); g.label = s.series;
    withPace.filter(o => o.r.series === s.series).forEach(o => {
      const opt = document.createElement("option"); opt.value = o.i;
      opt.textContent = `${o.r.event} · ${o.r.race} (${o.r.neutralised_laps} of ${o.r.total_laps} neutralised)`;
      g.appendChild(opt);
    });
    sel.appendChild(g);
  });
  const pool = withPace.filter(o => isHL(o.r.series));
  const def = (pool.length ? pool : withPace).reduce((a, b) => b.r.neutralised_laps > a.r.neutralised_laps ? b : a);
  sel.value = def.i;
  sel.onchange = () => draw(DATA.rows[+sel.value]);
  draw(def.r);

  function draw(r) {
    const box = $("example"); box.innerHTML = "";
    const W = 960, H = 280, left = 56, right = 150, top = 12, bottom = 34;
    const base = r.median_green_lap_s, pace = r.pace, n = pace.length;
    const cap = base * Math.max(RF + 0.25, Math.min(RF + 0.25, Math.max(...pace) / base)); // y-axis top
    const yMax = Math.min(cap, Math.max(base * (T + 0.6), Math.max(...pace) * 1.05));
    const slot = (W - left - right) / n, x = i => left + slot * i, bw = Math.max(4, slot * 0.72);
    const y = v => top + (H - top - bottom) * (1 - Math.min(v, yMax) / yMax);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
      "aria-label": `Lead-pace lap times for ${r.series} ${r.event} ${r.race}` });
    const defs = el("defs", {}, svg);
    const pat = el("pattern", { id: "rf-hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse",
      patternTransform: "rotate(45)" }, defs);
    el("rect", { width: 6, height: 6, fill: "var(--red-soft)" }, pat);
    el("rect", { width: 3, height: 6, fill: "var(--red)" }, pat);
    // y gridlines (seconds)
    const step = yMax > 400 ? 120 : yMax > 200 ? 60 : yMax > 100 ? 30 : 15;
    for (let t = 0; t <= yMax; t += step) {
      el("line", { x1: left, x2: W - right, y1: y(t), y2: y(t), stroke: "var(--grid)" }, svg);
      el("text", { x: left - 8, y: y(t) + 4, "text-anchor": "end" }, svg).textContent =
        t >= 60 ? `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, "0")}` : `${t}s`;
    }
    pace.forEach((v, i) => {
      const red = v > base * RF, neut = v > base * T;
      const yy = y(v), h = y(0) - yy;
      el("path", { d: `M${x(i) + 1},${y(0)} v${-(h - 3)} a3,3 0 0 1 3,-3 h${bw - 6} a3,3 0 0 1 3,3 v${h - 3} z`,
        fill: red ? "url(#rf-hatch)" : neut ? "var(--neut)" : "var(--other)" }, svg);
      if (v > yMax) el("text", { x: x(i) + 1 + bw / 2, y: top + 10, "text-anchor": "middle", class: "lbl" }, svg)
        .textContent = "↑";
      if (n <= 25 || i % 2 === 0) el("text", { x: x(i) + 1 + bw / 2, y: H - bottom + 16, "text-anchor": "middle" }, svg)
        .textContent = i + 1;
      const hit = el("rect", { x: x(i), y: top, width: bw + 2, height: H - top - bottom, fill: "transparent" }, svg);
      hit.addEventListener("mousemove", ev => showTip(`<b>Lap ${i + 1}: ${red ? "red flag" : neut ? "neutralised" : "green"}</b>`
        + `Lead pace ${fmtLap(v)} = ${fmt(v / base * 100, 0)}% of normal pace`, ev));
      hit.addEventListener("mouseleave", hideTip);
    });
    el("text", { x: left + (W - left - right) / 2, y: H - 2, "text-anchor": "middle" }, svg).textContent = "Lap";
    // reference lines, labelled at the right edge
    [[base, "Normal pace " + fmtLap(base), "var(--text-secondary)", ""],
     [base * T, `Neutralised above ${fmtLap(base * T)} (${T}×)`, "var(--neut)", "6 4"],
     [base * RF, `Red flag above ${fmtLap(base * RF)} (${RF}×)`, "var(--red)", "2 4"]].forEach(([v, label, col, dash]) => {
      if (v > yMax) return;
      el("line", { x1: left, x2: W - right + 4, y1: y(v), y2: y(v), stroke: col, "stroke-width": 2,
        "stroke-dasharray": dash }, svg);
      el("text", { x: W - right + 10, y: y(v) + 4, style: "fill:var(--text-primary);font-size:11.5px" }, svg).textContent = label;
    });
    box.appendChild(svg);
    $("ex-summary").textContent = `${r.series} · ${r.event} · ${r.race}: normal pace ${fmtLap(base)}. `
      + (r.neutralised_laps ? `Laps ${prettyLaps(r.neutralised_lap_numbers)} were over the ${T}× line, so ${r.neutralised_laps} of ${r.total_laps} laps count as neutralised.`
                            : `No lap crossed the ${T}× line: a clean race.`)
      + (r.red_flag_minutes ? ` That includes a red-flag stoppage of about ${fmt(r.red_flag_minutes, 0)} minutes.` : "")
      + (Math.max(...pace) > yMax ? " ↑ = lap goes off the top of the chart." : "");
  }
})();
function prettyLaps(s) { return String(s).split(";").join(", ").replace(/-/g, "–"); }
function fmtLap(s) { const m = Math.floor(s / 60), r = s - m * 60; return m ? `${m}:${r.toFixed(1).padStart(4, "0")}` : `${r.toFixed(1)}s`; }

$("caveats").innerHTML = DATA.caveats.map(c => `<li>${esc(c)}</li>`).join("");
$("built").textContent = `Built ${DATA.built} from out/comparison.csv · ${DATA.rows.length} races.`;
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
