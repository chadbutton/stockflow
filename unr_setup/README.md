# UnR Setup Component

Standalone component for the **UnR (Undercut and Run)** setup: Gil Morales–style undercut of 20/50/200 EMA on the daily chart, with a **65-minute** trigger using The Strat **2-1-2** reversal (Rob Smith). Includes trigger persistence and a **score out of 100** from historical pattern performance.

## Features

- **Configurable setup criteria:** Any setup uses the same generic criteria schema (entry, stop, conditions, timeframes) plus `setup_specific` key-value. Load from **YAML or JSON** files (directory or single file); source is configurable via path or env var `SETUP_CRITERIA_DIR`.
- **The Strat:** Bar classification (1 = inside, 2U/2D = one-side, 3 = outside) and **2-1-2** reversal detection on 65-min bars.
- **UnR daily context:** 20/50/200 EMA (configurable); 3–5 day pullback to MA; MA slope (upsloping for long, downsloping for short).
- **Evaluator:** Combines daily context + 65-min bars; returns trigger with entry/stop and `ma_used`. UnR params (daily_emas, pullback_days, trigger_timeframe, strat_pattern) come from criteria when provided.
- **Persistence:** Store every trigger in SQLite (or inject another DB) for metric analysis.
- **Scoring:** Score 0–100 from historical triggers + resolved outcomes (same pattern = same setup_id, ma_used, direction).

## Install

From repo root:

```bash
pip install -e ".[dev]"
```

## Run tests

```bash
pytest tests/ -v
```

## Usage (minimal)

```python
from unr_setup import evaluate_unr, load_criteria, TriggerRepository, compute_score

# Optional: load criteria from config (directory or file)
criteria_dir = "config/setups"  # or set env SETUP_CRITERIA_DIR
criteria = load_criteria(criteria_dir).get("unr")

# Daily: last N days OHLC (list of (open, high, low, close))
daily_bars = [...]
# 65-min: last 4+ bars (open, high, low, close)
bars_65 = [...]

# Evaluate (uses criteria if provided)
result = evaluate_unr(daily_bars, bars_65, symbol="AAPL", criteria=criteria)
# Or: result = evaluate_unr(daily_bars, bars_65, criteria_dir=criteria_dir)
if result:
    trigger = result.trigger  # entry, stop, direction, ma_used
    repo = TriggerRepository("triggers.db")
    repo.save(trigger)
    score = compute_score(repo, setup_id="unr", ma_used=trigger.ma_used, direction=trigger.direction)
```

## Docs

- Full setup specification: `docs/SETUP_UNR.md`
- Architecture: `docs/ARCHITECTURE.md`
