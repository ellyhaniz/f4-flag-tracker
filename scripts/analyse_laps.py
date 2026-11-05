"""Classify each race lap as green or neutralised (SC / FCY / red-flag restart) from its-results
"Lap by lap" spreadsheets, and write a per-race summary CSV.

Method: for every lap number, take the median lap time of the top-3 classified finishers (the "lead pace").
A lap is neutralised when the lead pace is > THRESHOLD x the race's normal pace (median of laps within
10% of the fastest). Leaders stay on the same lap as each other, and the median of 3 means one car's
spin can't flag a lap. Lap 1 is excluded from the baseline (standing start) but still classified.
A lap > RED_FLAG_FACTOR x normal pace contains a red-flag stoppage; its extra time is reported in minutes.

Reads its-results "Lap_by_lap.xlsx" (Saudi) or laps.json written by fetch_f4me.py.

Usage: python scripts/analyse_laps.py data/saudi/2025 --series "F4 Saudi Arabia" --out out/saudi_2025.csv
"""
import argparse
import csv
import json
import pathlib
import re
import statistics
import warnings

import openpyxl

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
THRESHOLD = 1.25
RED_FLAG_FACTOR = 3.0
DRIVER_RE = re.compile(r"No\.\s*(\d+),\s*(.+?),\s*Pos\.\s*(\S+)")


def to_seconds(t):
    if t is None:
        return None
    t = str(t).strip()
    if not t or t == "-":
        return None
    parts = t.split(":")
    try:
        secs = float(parts[-1])
        if len(parts) >= 2:
            secs += int(parts[-2]) * 60
        if len(parts) == 3:
            secs += int(parts[-3]) * 3600
        return secs
    except ValueError:
        return None


def read_lap_by_lap(path):
    """Return {car_no: [(lap, lap_seconds), ...]} and header info."""
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.worksheets[0]
    cars, pos, current, header = {}, {}, None, []
    col = None
    for row in ws.iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        if not cells:
            continue
        first = str(cells[0])
        if col is None:
            if first == "Lap" and "Lap Time" in [str(c) for c in row]:
                col = {str(c): i for i, c in enumerate(row) if c is not None}
            else:
                header.append(" ".join(str(c) for c in cells))
            continue
        m = DRIVER_RE.match(first)
        if m:
            current = m.group(1)
            cars[current] = []
            pos[current] = int(m.group(3)) if m.group(3).isdigit() else 999
            continue
        if current and first.isdigit():
            lap_t = to_seconds(row[col["Lap Time"]])
            if lap_t:
                cars[current].append((int(first), lap_t))
    return cars, pos, header


def classify(cars, pos, top=3):
    leaders = sorted(cars, key=lambda c: pos.get(c, 999))[:top]
    by_lap = {}
    for c in leaders:
        for n, t in cars[c]:
            by_lap.setdefault(n, []).append(t)
    if not by_lap:
        return None
    pace = {n: statistics.median(ts) for n, ts in sorted(by_lap.items())}
    # Baseline = median of the laps within 10% of the fastest lead-pace lap. Robust even when
    # most of a race was neutralised (a plain median would then be a Safety Car lap).
    racing = [t for n, t in pace.items() if n > 1] or list(pace.values())
    fastest = min(racing)
    base = statistics.median([t for t in racing if t <= fastest * 1.10])
    flags = {n: (t > base * THRESHOLD) for n, t in pace.items()}
    return pace, base, flags


def red_flag_minutes(pace, base):
    """A lap > RED_FLAG_FACTOR x normal pace contains a stoppage; return the excess time in minutes."""
    return sum(t - base for t in pace.values() if t > base * RED_FLAG_FACTOR) / 60


def spans(flagged_laps):
    out, start, prev = [], None, None
    for n in flagged_laps:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append((start, prev)); start = prev = n
    if start is not None:
        out.append((start, prev))
    return ";".join(f"{a}" if a == b else f"{a}-{b}" for a, b in out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--series", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    root = pathlib.Path(a.root)
    files = sorted(list(root.rglob("Lap_by_lap.xlsx")) + list(root.rglob("laps.json")))
    for f in files:
        meta_p = f.parent / "meta.json"
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        if f.suffix == ".json":
            d = json.loads(f.read_text())
            cars, pos = {k: [tuple(x) for x in v] for k, v in d["cars"].items()}, d["pos"]
        else:
            cars, pos, _ = read_lap_by_lap(f)
        res = classify(cars, pos)
        if not res:
            continue
        pace, base, flags = res
        total = len(pace)
        neut = [n for n, v in flags.items() if v]
        neut_time = sum(pace[n] for n in neut)
        race_time = sum(pace.values())
        rows.append({
            "series": a.series,
            "event": meta.get("event", f.parent.parent.name),
            "race": meta.get("session", f.parent.name),
            "date": (meta.get("date") or "")[:17],
            "cars": len(cars),
            "total_laps": total,
            "neutralised_laps": len(neut),
            "green_laps": total - len(neut),
            "neutralised_pct": round(100 * len(neut) / total, 1),
            "neutralised_time_pct": round(100 * neut_time / race_time, 1),
            "red_flag_minutes": round(red_flag_minutes(pace, base), 1),
            "median_green_lap_s": round(base, 3),
            "neutralised_lap_numbers": spans(neut),
            # lead pace (median of top-3) for every lap, ";"-separated seconds, for the dashboard chart
            "lead_pace_s": ";".join(f"{pace[n]:.1f}" for n in sorted(pace)),
            "source": str(f),
        })
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"{r['event'][:10]:10} {r['race']:7} laps={r['total_laps']:3} "
              f"neut={r['neutralised_laps']:2} ({r['neutralised_pct']:5}%) red={r['red_flag_minutes']:4}m "
              f"laps:{r['neutralised_lap_numbers']}")
    tl = sum(r["total_laps"] for r in rows); nl = sum(r["neutralised_laps"] for r in rows)
    print(f"\n{a.series}: {len(rows)} races, {tl} laps, {nl} neutralised ({100*nl/tl:.1f}%)")


if __name__ == "__main__":
    main()
