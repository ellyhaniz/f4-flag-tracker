"""Download every race document (PDF + XLS) for F4 Saudi Arabia 2025 from its-results.com.

Output: data/saudi/2025/<round>/<race>/<doc>.{pdf,xlsx}
"""
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

API = "https://api3.its-results.com/v1"
CHAMPIONSHIP = "f4sac"
SEASON_NAME = "2025"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "saudi" / SEASON_NAME


HEADERS = {"User-Agent": "Mozilla/5.0 (f4-flag-tracker)"}


def fetch(url, timeout=30):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout)


def get_json(path):
    with fetch(f"{API}{path}") as r:
        return json.load(r)


def download(kind, result_id, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return "skip"
    q = urllib.parse.urlencode({"result": result_id, "name": dest.name})
    with fetch(f"{API}/download-{kind}?{q}", timeout=60) as r:
        dest.write_bytes(r.read())
    time.sleep(0.3)
    return "ok"


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def main():
    cs = get_json(f"/Cs/getChampionship/{CHAMPIONSHIP}")
    season = next(s for s in get_json(f"/Cs/getSeasons/{cs['id']}") if s["name"] == SEASON_NAME)
    for event in get_json(f"/Cs/getEvents/{season['id']}"):
        round_dir = OUT / slug(event["name"].split(" - ")[0])  # e.g. Round_01
        for folder in get_json(f"/Results/getFolders/{event['id']}"):
            for session in get_json(f"/Results/getSessions/{folder['id']}"):
                if not session["name"].upper().startswith("RACE"):
                    continue
                race_dir = round_dir / slug(session["name"])
                race_dir.mkdir(parents=True, exist_ok=True)
                (race_dir / "meta.json").write_text(json.dumps(
                    {"event": event["name"], "date": event.get("beginDate"),
                     "session": session["name"], "day": session.get("day")}, indent=1))
                for res in get_json(f"/Results/getResults/{session['id']}"):
                    if not res.get("online"):
                        continue
                    base = slug(res["name"])
                    if res.get("pdfUploaded"):
                        st = download("pdf", res["id"], race_dir / f"{base}.pdf")
                        print(st, race_dir.relative_to(OUT), base, "pdf")
                    if res.get("xlsUploaded"):
                        st = download("xls", res["id"], race_dir / f"{base}.xlsx")
                        print(st, race_dir.relative_to(OUT), base, "xlsx")


if __name__ == "__main__":
    main()
