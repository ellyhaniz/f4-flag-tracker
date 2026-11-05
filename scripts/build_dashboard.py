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
    "Laps are classified from lap times only: a lap counts as neutralised when the top-3 finishers' "
    "median lap is more than 25% slower than normal race pace. Not yet cross-checked with race control.",
]


def load_rows(path):
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            for k in NUMERIC:
                r[k] = float(r[k]) if r.get(k) not in (None, "") else 0.0
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
  --hl: #2a78d6; --hl-soft: #cde2fb; --other: #8a8984; --other-soft: #e3e2de;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c; --grid: #262624;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #9a998f;
    --hl: #3987e5; --hl-soft: #184f95; --other: #75746f; --other-soft: #383835;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c; --grid: #262624;
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #9a998f;
  --hl: #3987e5; --hl-soft: #184f95; --other: #75746f; --other-soft: #383835;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface-0); color: var(--text-primary);
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
</style>
</head>
<body>
<main>
  <h1>F4 Flag Tracker — 2025</h1>
  <p class="sub" id="lede"></p>

  <div class="tiles" id="tiles"></div>

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

  <section class="card">
    <h2>Race by race</h2>
    <div class="controls" id="filters"></div>
    <div class="table-wrap"><table id="tbl"></table></div>
  </section>

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
            + (r.neutralised_lap_numbers ? `<br>Laps: ${esc(r.neutralised_lap_numbers)}` : "");
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
      return `<td class="${n ? "num" : ""}">${n ? Math.round(r[k]) : esc(r[k] || "–")}</td>`;
    }).join("")}</tr>`).join("")}</tbody>`;
  [...$("tbl").querySelectorAll("th")].forEach(th => th.onclick = () => {
    const k = th.dataset.k; sortDir = sortKey === k ? -sortDir : (k.includes("pct") || k.includes("laps") ? -1 : 1);
    sortKey = k; renderTable(); });
}
renderTable();

$("caveats").innerHTML = DATA.caveats.map(c => `<li>${esc(c)}</li>`).join("");
$("built").textContent = `Built ${DATA.built} from out/comparison.csv · ${DATA.rows.length} races.`;
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
