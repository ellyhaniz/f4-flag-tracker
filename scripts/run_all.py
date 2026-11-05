"""Rebuild everything: (optionally re-download) -> analyse each series -> compare -> dashboard.

    python scripts/run_all.py            # use the data already in data/, rebuild out/
    python scripts/run_all.py --fetch    # re-download Saudi, F4 Middle East and British first

Italian F4 can't be fetched by script (acisport.it has a Cloudflare bot check); its PDFs are
downloaded by hand into data/italian/2025/... and then parsed by parse_italian.py.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

SERIES = [  # (label, data folder, output csv)
    ("F4 Saudi Arabia", "data/saudi/2025", "out/saudi_2025.csv"),
    ("F4 Middle East", "data/f4me/2025", "out/f4me_2025.csv"),
    ("Italian F4", "data/italian/2025", "out/italian_2025.csv"),
    ("British F4", "data/british/2025", "out/british_2025.csv"),
]


def run(*args, cwd=ROOT):
    print("\n$", " ".join(str(a) for a in args))
    subprocess.run([PY, *args], cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="re-download the scriptable series first")
    a = ap.parse_args()
    if a.fetch:
        run("scripts/fetch_saudi.py")
        run("scripts/fetch_f4me.py")
        run("scripts/fetch_british.py")
        run("fetch_zandvoort.py", cwd=ROOT / "scripts")  # imports fetch_f4me from the same folder
    run("scripts/parse_italian.py", "data/italian/2025")
    for label, folder, out in SERIES:
        run("scripts/analyse_laps.py", folder, "--series", label, "--out", out)
    run("scripts/compare.py", *[out for _, _, out in SERIES])
    run("scripts/build_dashboard.py")
    print(f"\nDone. Open {ROOT / 'out' / 'dashboard.html'} in your browser.")


if __name__ == "__main__":
    main()
