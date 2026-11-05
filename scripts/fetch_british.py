"""Download British F4 2025 weekend PDF books from tsl-timing.com and convert each race to laps.json.

Each BTCC weekend's book (<event_id>bf4.pdf) holds qualifying + 3 races; per race it has a
CLASSIFICATION page and SECTOR ANALYSIS pages listing every lap for every driver, headed by
finishing position ("P1 12 Adam AL AZHARI ...").

Output: data/british/2025/<Weekend_xx_Venue>/RACE_<championship round no>/laps.json + meta.json
"""
import json
import pathlib
import re
import time
import urllib.request

import pdfplumber

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "british" / "2025"
HEADERS = {"User-Agent": "Mozilla/5.0 (f4-flag-tracker)"}
EVENTS = [  # tsl-timing event id, venue (Rounds 16-18 at Zandvoort are not on TSL: see fetch_zandvoort)
    (251703, "Donington_Park"), (251831, "Silverstone_GP", "BRSCC"), (252103, "Snetterton"),
    (252303, "Thruxton"), (252503, "Oulton_Park"), (253303, "Knockhill"),
    (253503, "Donington_Park_GP"), (253803, "Silverstone"), (254003, "Brands_Hatch_GP"),
]
TITLE_RE = re.compile(r"^(?:RACE \d+ \()?ROUND (\d+)\)? - (SECTOR ANALYSIS|CLASSIFICATION)")
DRIVER_RE = re.compile(r"^(P?\d+|DNF|DNS|NC|DSQ|EXC)\s+(\d+)\*?\s+\S")
LAPTIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}\.\d{3})$")
TOD_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}\.\d{3}$")


def parse_lap(line):
    toks = line.split()
    if len(toks) < 4 or not toks[0].isdigit() or not TOD_RE.match(toks[-1]):
        return None
    # Sectors, lap time and DIFF are all 3-decimal times (m:ss.sss or ss.sss); speeds have 1-2
    # decimals. The lap time is always the largest of them (sectors and DIFF are both smaller).
    times = []
    for tok in toks[1:-1]:
        m = LAPTIME_RE.match(tok)
        if m:
            times.append(int(m.group(1) or 0) * 60 + float(m.group(2)))
    return [int(toks[0]), max(times)] if times else None


def parse_book(path):
    races = {}  # round no -> {"cars":{}, "pos":{}, "distance": str}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            lines = (page.extract_text() or "").splitlines()
            if len(lines) < 3:
                continue
            m = TITLE_RE.match(lines[1])
            if not m:
                continue
            race = races.setdefault(int(m.group(1)), {"cars": {}, "pos": {}, "distance": ""})
            if m.group(2) == "CLASSIFICATION":
                race["distance"] = lines[2]
                continue
            current = None
            for l in lines[3:]:
                d = DRIVER_RE.match(l)
                if d and "IDEAL" not in l:
                    current = d.group(2)
                    race["cars"].setdefault(current, [])
                    p = d.group(1).lstrip("P")
                    race["pos"][current] = int(p) if p.isdigit() else 999
                    continue
                lap = parse_lap(l)
                if lap and current:
                    race["cars"][current].append(lap)
    return races


def main():
    for i, (eid, venue, *folder) in enumerate(EVENTS, 1):
        i = i + 1 if i >= 6 else i  # weekend 6 = Zandvoort (fetch_zandvoort.py)
        wk = OUT / f"Weekend_{i:02d}_{venue}"
        wk.mkdir(parents=True, exist_ok=True)
        book = wk / "book.pdf"
        if not book.exists():
            url = f"https://www.tsl-timing.com/file/?f={(folder or ['TOCA'])[0]}/2025/{eid}bf4.pdf"
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as r:
                book.write_bytes(r.read())
            time.sleep(0.5)
        for rnd, race in sorted(parse_book(book).items()):
            d = wk / f"RACE_{rnd:02d}"
            d.mkdir(exist_ok=True)
            (d / "laps.json").write_text(json.dumps({"cars": race["cars"], "pos": race["pos"]}))
            (d / "meta.json").write_text(json.dumps({
                "event": f"Weekend {i:02d} - {venue.replace('_', ' ')}", "date": "",
                "session": f"Round {rnd}", "distance": race["distance"]}, indent=1))
            print(f"{wk.name:28} Round {rnd:2} cars={len(race['cars']):2} "
                  f"laps={max((len(v) for v in race['cars'].values()), default=0):2} {race['distance']}")


if __name__ == "__main__":
    main()
