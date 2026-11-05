"""Download F4 Middle East 2025 race PDFs from getraceresults.com and convert them to laps.json.

Output: data/f4me/2025/<round>/<race>/{classification,laptimes,...}.pdf + laps.json + meta.json
laps.json = {"cars": {car_no: [[lap, seconds], ...]}, "pos": {car_no: finishing_pos}}
"""
import html
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

import pdfplumber

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "f4me" / "2025"
HEADERS = {"User-Agent": "Mozilla/5.0 (f4-flag-tracker)"}
VENUE_LABEL = {"Round_01": "Yas Marina (GP)", "Round_02": "Yas Marina (Corkscrew)",
               "Round_03": "Dubai Autodrome", "Round_04": "Yas Marina (GP)"}
EVENTS = [  # (round label, getraceresults venue, event name)
    ("Round_01", "YAS Marina Circuit", "FORMULA MIDDLE EAST 2025"),
    ("Round_02", "YAS Marina Circuit", "YMRC - YAS RACING SERIES ROUND 2"),
    ("Round_03", "Dubai Autodrome", "Formula 4 & Formula Regional Middle East Championship - Round 3"),
    ("Round_04", "YAS Marina Circuit", "YAS RACING SERIES - YMRC - ROUND 4"),
]
RACE_RE = re.compile(r"(?:F4|Formula 4) Middle East(?: Championship)? - Race(?: - | )?(\d)(?: - (.+))?\.pdf$", re.I)
TIME_RE = re.compile(r"^(?:\d+:)?\d{1,2}\.\d{3}$")


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
        return r.read()


def race_links(venue, event):
    q = urllib.parse.urlencode({"evenement": venue, "race": event})
    page = get(f"https://getraceresults.com/Results/organisator/2025?{q}").decode("utf-8", "replace")
    out = {}
    for href in set(re.findall(r'href="([^"]+\.pdf)"', page)):
        href = html.unescape(href)
        name = urllib.parse.unquote(urllib.parse.unquote(href.rsplit("/", 1)[-1]))
        m = RACE_RE.search(name)
        if m:
            kind = (m.group(2) or "classification").lower().replace(" ", "_")
            out.setdefault(f"RACE_{m.group(1)}", {})[kind] = href
    return out


def pdf_text(path):
    with pdfplumber.open(path) as p:
        return "\n".join(pg.extract_text() or "" for pg in p.pages)


def to_seconds(t):
    parts = t.split(":")
    return float(parts[-1]) + (int(parts[0]) * 60 if len(parts) == 2 else 0)


def parse_laptimes(text):
    """Laptimes PDF rows: '<no> <name> <laps> 1 - 10 t1 ... t10' then '11 - 20 t11 ...'."""
    cars, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^(\d+)\s+(.+?)\s+(\d+)\s+(\d+) - \d+\s+(.*)$", line)
        cont = re.match(r"^(\d+) - \d+\s*(.*)$", line)
        # variant (Zandvoort): "<no> <name> [laps]" alone on a line, times on the next "1 - 25 ..." line
        own = re.match(r"^(\d+)\s+[^\d\s][^:]*?(?:\s+\d+)?$", line)
        if own and not cont and " - " not in line and not re.search(r"\b(19|20)\d\d$", line):
            current = own.group(1)
            cars[current] = []
            continue
        if m and int(m.group(4)) == 1:
            current = m.group(1)
            start, rest = 1, m.group(5)
            cars[current] = []
        elif cont and current:
            start, rest = int(cont.group(1)), cont.group(2)
        else:
            continue
        for i, tok in enumerate(rest.split()):
            if TIME_RE.match(tok):
                cars[current].append([start + i, to_seconds(tok)])
    return cars


def parse_classification(text):
    pos = {}
    for line in text.splitlines():
        m = re.match(r"^(\d+)\s+(\d+)\s+\S", line)
        if m and m.group(1) not in pos.values():
            pos.setdefault(m.group(2), int(m.group(1)))
    return pos


def main():
    for rnd, venue, event in EVENTS:
        for race, docs in sorted(race_links(venue, event).items()):
            d = OUT / rnd / race
            d.mkdir(parents=True, exist_ok=True)
            for kind, url in docs.items():
                f = d / f"{kind}.pdf"
                if not f.exists():
                    f.write_bytes(get(url)); time.sleep(0.3)
                print("ok", rnd, race, kind)
            if "laptimes" not in docs or "classification" not in docs:
                print("!! missing laptimes/classification", rnd, race); continue
            lt, cl = pdf_text(d / "laptimes.pdf"), pdf_text(d / "classification.pdf")
            date = re.search(r"^(\d{1,2} \w+ 20\d\d)$", cl, re.M)
            (d / "meta.json").write_text(json.dumps({
                "event": f"{rnd.replace('_', ' ')} - {VENUE_LABEL[rnd]}",
                "date": date.group(1) if date else "", "session": race.replace("_", " ")}, indent=1))
            (d / "laps.json").write_text(json.dumps(
                {"cars": parse_laptimes(lt), "pos": parse_classification(cl)}))


if __name__ == "__main__":
    main()
