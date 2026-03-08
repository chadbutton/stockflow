# Daily Scan Backend

Finds stocks that meet **daily** setup criteria (Phase 1: watchlist). Uses `unr_setup` for UnR daily context (20/50/200 EMA, 3–5 day pullback, undercut, slope).

## Install

From repo root (install `unr_setup` first, then backend):

```bash
pip install -e unr_setup
pip install -e backend
```

## Run

**Scan using Friday’s data (Yahoo Finance)** — UnR daily matches as of a given date:

```bash
cd backend
pip install -e ../unr_setup
pip install -e .
python -m scanner.cli --yahoo --as-of 2025-03-07 -o watchlist_2025-03-07.json
```

Use the Friday date you want (e.g. `2025-03-07`). Output: watchlist of symbols that meet UnR daily criteria (long/short, MA 20/50/200) printed to stdout and saved to the JSON file.

**Mock data** (one synthetic symbol that satisfies UnR bullish):

```bash
cd backend
python -m scanner.cli --mock
```

**With your own daily data (CSV):**

1. Put one CSV per symbol in a directory, e.g. `config/daily/AAPL.csv`:
   - Columns: `date,open,high,low,close` (header optional)
   - Oldest first
2. Use the starter universe (liquid US, >40M cap, includes PLTR/TSLA/GOOG/MSFT) or your own:
   - Default universe file: `config/universe_liquid_us.txt`
   - Or list symbols in `config/universe.txt` (one per line).
3. Run:

```bash
python -m scanner.cli --universe config/universe_liquid_us.txt --csv-dir config/daily -o watchlist.json
```

**Output:** Watchlist printed to stdout and optionally saved to JSON (`--output`).

## Tuning

- **Criteria:** UnR parameters (daily_emas, pullback_days_min/max, slope_lookback) come from `unr_setup/config/setups/unr.yaml` (or `--criteria-dir`). Edit that file to tweak without code changes.
- **Universe:** Starter list is `config/universe_liquid_us.txt` (liquid US, >40M cap, PLTR/TSLA/GOOG/MSFT etc.). Edit that file or pass `--universe <path>`.
- **As-of date:** Use `--as-of YYYY-MM-DD` to scan as of a specific date (e.g. last trading day).

## Tests

```bash
cd backend
pytest tests/ -v
```

Tests use mock data to assert that the scan finds UnR setups when the synthetic bars satisfy the criteria.
