"""Convert Italian F4 (acisport.it) race PDFs into laps.json + meta.json for analyse_laps.py.

Input:  data/italian/2025/<Round_xx_Venue>/<RACE_n>/race.pdf  (the "join" PDF: results, lap chart,
        best sectors, chronological analysis)
Output: laps.json = {"cars": {car_no: [[lap, seconds], ...]}, "pos": {car_no: finishing_pos}}

Getting the PDFs: acisport.it sits behind a Cloudflare check, so they were downloaded through a real
Chrome session (see README / session notes), not by script.
"""
import json
import pathlib
import re
import sys

import pdfplumber

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/italian/2025")
HEADER_RE = re.compile(r"^(\d+)\s+([A-Z][^()]*?)\s*\((\d+'\d{2}\.\d{3})\)")
LAPTIME_RE = re.compile(r"(\d+)'(\d{2}\.\d{3})")
LOCALTIME_RE = re.compile(r"\d{1,2}:\d{2}'\d{2}\.\d{3}$")
RESULT_RE = re.compile(r"^(\d+)P?\s+(\d+)\s+[A-Z]")


def column_lines(page):
    """Lines of the left half, then the right half of a chronological-analysis page."""
    mid = page.width / 2
    out = []
    for box in ((0, 0, mid, page.height), (mid, 0, page.width, page.height)):
        txt = page.crop(box).extract_text() or ""
        out.extend(txt.splitlines())
    return out


def parse_lap_line(line):
    """'<lap> <segments...> <lap time> <km/h> <local time>' -> (lap, seconds) or None."""
    toks = line.split()
    if len(toks) < 4 or not toks[0].isdigit() or not LOCALTIME_RE.match(toks[-1]):
        return None
    # lap time is the last m'ss.sss token before the speed / local-time columns
    for tok in reversed(toks[1:-1]):
        m = LAPTIME_RE.fullmatch(tok)
        if m:
            return int(toks[0]), int(m.group(1)) * 60 + float(m.group(2))
    return None


SBS_LAP_RE = re.compile(r"^(\d+)\s+(?:P\s+)?((?:\d+:)?\d{2}\.\d{3})\b")


def parse_side_by_side(page, lines, cars):
    """'Lap Analysis' pages with two cars per page: car numbers on line 5, left/right columns."""
    nums = lines[4].split() if len(lines) > 4 else []
    if not nums or not all(n.isdigit() for n in nums):
        return
    mid = page.width / 2
    halves = [(0, 0, mid, page.height), (mid, 0, page.width, page.height)]
    for car, box in zip(nums, halves if len(nums) == 2 else [(0, 0, page.width, page.height)]):
        txt = page.crop(box).extract_text() or ""
        laps = cars.setdefault(car, [])
        for l in txt.splitlines():
            m = SBS_LAP_RE.match(l.strip())
            if m:
                t = m.group(2).split(":")
                secs = float(t[-1]) + (int(t[0]) * 60 if len(t) == 2 else 0)
                laps.append([int(m.group(1)), secs])


def parse_race(pdf_path):
    cars, pos, title, date = {}, {}, "", ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.splitlines()
            if len(lines) > 2 and not date:
                date = lines[1].strip()
            is_results = (re.search(r"- Results .*Race", text) and "by Class" not in text) or \
                (page.page_number == 1 and lines and lines[0].startswith("Clas"))
            if is_results and not pos:
                title = next((l for l in lines if "Results" in l), title)
                for l in lines:
                    m = RESULT_RE.match(l)
                    if m:
                        pos.setdefault(m.group(2), int(m.group(1)))
            if "Lap Analysis" in lines[:4] or (len(lines) > 3 and lines[3] == "Lap Analysis"):
                parse_side_by_side(page, lines, cars)  # Barcelona (Spanish timing provider) layout
                continue
            if "Chronological Analysis" not in text:
                continue
            current = None
            for l in column_lines(page):
                h = HEADER_RE.match(l)
                if h:
                    current = h.group(1)
                    cars.setdefault(current, [])
                    continue
                lap = parse_lap_line(l)
                if lap and current:
                    cars[current].append(list(lap))
    for c in cars:  # dedupe + sort
        cars[c] = sorted({n: [n, t] for n, t in cars[c]}.values())
    return cars, pos, title, date


def main():
    for pdf in sorted(ROOT.rglob("race.pdf")):
        cars, pos, title, date = parse_race(pdf)
        rnd = pdf.parent.parent.name  # Round_01_Misano
        (pdf.parent / "laps.json").write_text(json.dumps({"cars": cars, "pos": pos}))
        (pdf.parent / "meta.json").write_text(json.dumps({
            "event": rnd.replace("_", " ", 1).replace("_", " - ", 1), "date": date,
            "session": pdf.parent.name.replace("_", " "), "title": title}, indent=1))
        n_laps = max((len(v) for v in cars.values()), default=0)
        print(f"{rnd:22} {pdf.parent.name:7} cars={len(cars):2} classified={len(pos):2} max_laps={n_laps}")


if __name__ == "__main__":
    main()
