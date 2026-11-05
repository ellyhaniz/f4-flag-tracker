# F4 Flag Tracker — 2025

How much racing did each F4 series lose to Safety Car / Full Course Yellow / red flags?
Compares **F4 Saudi Arabia** with **F4 Middle East (ex-F4 UAE)**, **Italian F4** and **British F4**
using the official lap-by-lap timing documents.

Open **`out/dashboard.html`** in any browser to see the result.

## Run it

Needs Python 3 with two packages:

```bash
pip install openpyxl pdfplumber
```

Rebuild everything from the data already downloaded:

```bash
python scripts/run_all.py
```

Re-download the series that can be fetched by script, then rebuild:

```bash
python scripts/run_all.py --fetch
```

## What happens, step by step

```
 official timing sites ──fetch──▶ data/<series>/2025/<round>/<race>/   (PDF / XLSX + laps.json)
                                          │
                              analyse_laps.py (one CSV per series)
                                          │
                                 compare.py ──▶ out/comparison.csv (one row per race)
                                          │
                           build_dashboard.py ──▶ out/dashboard.html
```

### 1. Getting the data (`scripts/fetch_*.py`, `parse_italian.py`)

| Series | Source | Script | Notes |
|---|---|---|---|
| F4 Saudi Arabia | its-results.com (public API behind the results site) | `fetch_saudi.py` | Downloads every race document; uses the "Lap by lap" spreadsheet |
| F4 Middle East | getraceresults.com | `fetch_f4me.py` | Race classification + laptimes PDFs → `laps.json`. Round 5 (Lusail) isn't published |
| Italian F4 | acisport.it | `parse_italian.py` | **Manual download** (Cloudflare blocks scripts): save each race's "Race N" PDF as `data/italian/2025/Round_0X_Venue/RACE_N/race.pdf` |
| British F4 | tsl-timing.com weekend PDF books | `fetch_british.py` | 9 of 10 weekends |
| British F4 Zandvoort | getraceresults.com | `fetch_zandvoort.py` | Rounds 16–18; reuses the F4 Middle East parser |

Every race ends up as `laps.json`:

```json
{"cars": {"12": [[1, 118.138], [2, 110.837], ...]},   // car number -> [lap, seconds]
 "pos":  {"12": 1, "26": 2, ...}}                       // car number -> finishing position
```

(Saudi uses its `Lap_by_lap.xlsx` directly; `analyse_laps.py` reads both.)

### 2. Spotting neutralised laps (`scripts/analyse_laps.py`)

For each race:

1. Take the **top 3 finishers** and, for every lap number, the **median** of their three lap times
   → the "lead pace" on that lap. (Leaders stay on the same lap as each other, and a median of
   three means one driver's spin can't flag a lap on its own.)
2. **Normal pace** = median of the laps within 10% of the fastest lead-pace lap (lap 1 excluded,
   standing start). Using only the quick laps keeps the baseline honest even in races that were
   mostly behind the Safety Car.
3. A lap is **neutralised** if lead pace > **1.25 ×** normal pace (`THRESHOLD`).
   Safety Car laps typically run 1.4–2× slower, so the gap is wide.
4. A lap > **3 ×** normal pace contains a **red-flag stoppage** (`RED_FLAG_FACTOR`); its extra time is
   reported in minutes.

Output columns per race: `total_laps`, `neutralised_laps`, `green_laps`, `neutralised_pct`,
`neutralised_time_pct`, `red_flag_minutes`, `median_green_lap_s`, `neutralised_lap_numbers`.

### 3. Comparing (`scripts/compare.py`)

Stacks the per-series CSVs into `out/comparison.csv` and prints the season summary
(neutralised %, green laps per race, share of fully-green races).

### 4. Dashboard (`scripts/build_dashboard.py`)

Embeds the CSV rows as JSON into one self-contained HTML file — no internet or libraries needed.
Change the highlighted series with `--highlight "British F4"`.

## Known gaps / caveats

- F4 Middle East Round 5 (Lusail) and Italian Barcelona Race 2 are not published online.
- British Zandvoort Rounds 17–18 only publish post-restart laps.
- Red flags are only measured when the stoppage sits inside one timed lap. When timing restarts
  after a red flag, the stopped time isn't counted (affects British/Italian).
- Classification is from lap times only; not yet cross-checked against race-control messages,
  so Safety Car vs Full Course Yellow isn't distinguished.
