"""Combine per-series CSVs from analyse_laps.py into out/comparison.csv and print a summary table.

Usage: python scripts/compare.py out/saudi_2025.csv out/f4me_2025.csv
"""
import csv
import pathlib
import sys

rows = [r for f in sys.argv[1:] for r in csv.DictReader(open(f))]
out = pathlib.Path("out/comparison.csv")
with out.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

print(f"{'Series':18} {'Races':>5} {'Laps':>5} {'Neut':>5} {'Neut%':>6} {'Green/race':>10} "
      f"{'Clean races':>11} {'Red-flag min':>12}")
for s in dict.fromkeys(r["series"] for r in rows):
    rs = [r for r in rows if r["series"] == s]
    laps = sum(int(r["total_laps"]) for r in rs)
    neut = sum(int(r["neutralised_laps"]) for r in rs)
    green = sum(int(r["green_laps"]) for r in rs)
    clean = sum(1 for r in rs if int(r["neutralised_laps"]) == 0)
    red = sum(float(r["red_flag_minutes"]) for r in rs)
    print(f"{s:18} {len(rs):5} {laps:5} {neut:5} {100*neut/laps:5.1f}% {green/len(rs):10.1f} "
          f"{clean:>5} ({100*clean/len(rs):3.0f}%) {red:12.1f}")
print(f"\nwrote {out}")
