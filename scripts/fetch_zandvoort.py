"""British F4 Rounds 16-18 (Zandvoort, 26-27 July 2025) were timed by the getraceresults.com provider,
not TSL. Same PDF format as F4 Middle East, so this reuses fetch_f4me's parsers.

Event race numbers -> championship rounds: Race no.2 = R16, no.9 = R17, no.16 = R18.
R17 and R18 were red-flagged; only the post-restart part is published, so their lap counts
cover the restarted race only (the stoppage itself is not in the data).
"""
import json
import pathlib
import urllib.parse

import fetch_f4me as f

BASE = "https://resultscdn.getraceresults.com/2025/Circuit%20Zandvoort/Caterham%20Zandvoort/"
NAME = "Wera Tools F4 British F4 Championship Certified by the FIA - Race no.{n}{restart}{kind}.pdf"
RACES = [(16, 2, ""), (17, 9, " - Restart"), (18, 16, " - Restart")]
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "british" / "2025" / "Weekend_06_Zandvoort"


def main():
    for rnd, n, restart in RACES:
        d = OUT / f"RACE_{rnd:02d}"
        d.mkdir(parents=True, exist_ok=True)
        for kind, suffix in (("classification", ""), ("laptimes", " - laptimes")):
            p = d / f"{kind}.pdf"
            if not p.exists():
                p.write_bytes(f.get(BASE + urllib.parse.quote(NAME.format(n=n, restart=restart, kind=suffix))))
        lt, cl = f.pdf_text(d / "laptimes.pdf"), f.pdf_text(d / "classification.pdf")
        cars, pos = f.parse_laptimes(lt), f.parse_classification(cl)
        (d / "laps.json").write_text(json.dumps({"cars": cars, "pos": pos}))
        (d / "meta.json").write_text(json.dumps({
            "event": "Weekend 06 - Zandvoort", "date": "26-27 July 2025", "session": f"Round {rnd}",
            "note": "restart part only (red-flagged)" if restart else ""}, indent=1))
        print(f"Zandvoort Round {rnd}: cars={len(cars)} classified={len(pos)} "
              f"laps={max((len(v) for v in cars.values()), default=0)} {restart}")


if __name__ == "__main__":
    main()
