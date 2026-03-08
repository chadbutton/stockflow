# Setup Criteria — Definition Guide

This document defines **generic setup criteria** that apply to **any setup**. Criteria are **configurable**: stored in files (YAML/JSON) or a database, and loaded at runtime so the same scanner/backtester can run any setup by id without code changes.

---

## 1. Storage and configuration

Setup criteria can be stored in any of these ways (the application chooses one and makes the source configurable):

| Storage | Description | Configurable via |
|--------|-------------|------------------|
| **YAML/JSON files** | One file per setup under a directory (e.g. `config/setups/*.yaml`) | Path or env var (e.g. `SETUP_CRITERIA_DIR`) |
| **Single manifest** | One YAML/JSON file listing or embedding all setups | Path or env var |
| **Database** | Rows in a `setup_criteria` table (JSON blob or columns) | Connection string / config |

The only requirement: the **same schema** (see below) is used so that any setup type (UnR, bull flag, VCP, etc.) can be loaded by `setup_id` and passed to the scanner. Each setup implementation (e.g. UnR evaluator) reads the fields it needs from the generic criteria plus any **setup_specific** section.

---

## 2. Setup Schema (Generic, for any setup)

Each setup is a single, versioned definition with the following structure.

```yaml
# Generic fields (used by any setup)
setup_id: bull-flag-15m
name: Bull Flag (15m)
version: "1.0"
timeframes: [ "15m" ]

entry:
  type: breakout_above
  level_source: range_high
  range_bars: 10
  confirm: close

stop:
  type: swing_low
  lookback_bars: 10
  atr_multiplier: null

targets:
  - type: risk_multiple
    r: 2
  - type: risk_multiple
    r: 3

conditions:
  - type: price_above_ma
    ma: ema
    period: 20
  - type: volume_above_avg
    period: 20
    multiplier: 1.5

# Setup-specific parameters (interpreted by that setup's evaluator)
setup_specific: {}
```

- **setup_id**, **name**, **version**, **timeframes**: identity and scope.
- **entry**, **stop**, **targets**, **conditions**: generic building blocks; setup-specific evaluators may use a subset or extend via **setup_specific**.
- **setup_specific**: arbitrary key-value (e.g. for UnR: `daily_emas`, `trigger_timeframe`, `pullback_days_min`, `strat_pattern`). Storage is flexible; the evaluator for that setup type reads what it needs.

---

## 3. Condition Types (Building Blocks)

Define a small set of reusable condition types. Scanner and backtester both implement these.

| Condition Type | Description | Parameters (example) |
|----------------|-------------|----------------------|
| `price_above_ma` / `price_below_ma` | Close vs moving average | `ma`: ema/sma, `period` |
| `high_above_level` / `close_above_level` | Price vs fixed or derived level | `level_source`: e.g. `swing_high`, `range_high` |
| `volume_above_avg` | Volume vs average volume | `period`, `multiplier` |
| `atr_above` / `atr_below` | ATR filter (volatility) | `period`, `min` or `max` |
| `body_range_ratio` | Body size vs full range (candlestick shape) | `min`, `max` |
| `range_contraction` | Recent range/volatility contracting | `bars`, `max_volume_ratio` or `max_range_ratio` |
| `swing_high` / `swing_low` | N-bar swing high/low detected | `lookback` |
| `multi_timeframe` | Condition on another timeframe | `timeframe`, `condition` (nested) |

Conditions are combined with **AND** (all required) or **OR** (any) per setup.

---

## 4. Entry Types

| Entry Type | Description |
|------------|-------------|
| `breakout_above` | Trigger when close (or high) breaks above a level (e.g. range high, swing high). |
| `breakout_below` | Same, for breakdowns. |
| `close_above_ma` | Close above a moving average (e.g. EMA 20). |
| `reversal_signal` | E.g. engulfing or pin bar at support; level from swing low. |

Entry always produces: **entry_price** (e.g. close of trigger bar or next open), **trigger_time**, and **symbol/timeframe**.

---

## 5. Stop Types

| Stop Type | Description |
|-----------|-------------|
| `swing_low` | Low of last N bars (long) or swing_high (short). |
| `range_low` / `range_high` | Low/high of the consolidation range used for breakout. |
| `atr_below_entry` | Entry − (ATR × multiplier); same idea for short. |
| `fixed` | Fixed price or offset from entry (e.g. −$0.50). |

Stop is computed from the **same bar/window** used for entry so it is deterministic in backtest and live.

---

## 6. Position Sizing (Shared Rule)

Not part of “setup shape” but part of “alert output”:

- **Risk % per trade:** e.g. 0.5% or 1%.
- **Risk per share** = |entry − stop| (optional: + buffer for slippage).
- **Shares** = (account_equity × risk%) / risk_per_share; then apply lot size and max position cap.

This is applied **after** a setup matches; same formula in live and backtest.

---

## 7. Example: Bull Flag (Text Definition)

- **Timeframe:** 15m.
- **Conditions:**  
  - Close above 20 EMA (prior trend).  
  - Last 10 bars form a range; volume in last 5 bars &lt; 80% of 20-bar avg volume.  
  - Current bar closes above 10-bar high with volume &gt; 1.5× 20-bar avg.
- **Entry:** Close of current bar (or next bar open).
- **Stop:** Low of the 10-bar range (or 1-bar buffer).
- **Targets (optional):** 2R, 3R.

---

## 8. Example: VCP Breakout (Text Definition)

- **Timeframe:** 15m (or 5m).
- **Conditions:**  
  - At least 2–3 “contractions” in range (each pullback smaller).  
  - Price holds above 20 EMA.  
  - Current bar closes above the last contraction high with elevated volume.
- **Entry:** Close of breakout bar.
- **Stop:** Below last contraction low or below 20 EMA.
- **Targets (optional):** 2R, 3R.

---

## 9. Implementation Checklist

1. **Choose format:** YAML/JSON files under `config/setups/` or a small DB table.
2. **Implement parser:** Load setup definition → in-memory structure (same for scanner and backtester).
3. **Implement conditions:** One function per condition type; input = OHLCV + params, output = bool.
4. **Implement entry/stop resolution:** Given OHLCV window and setup definition → entry_price, stop_price (and optional targets).
5. **Wire into scanner:** On each new bar, run “evaluate setup”; if true, emit alert with entry, stop, and (from risk rule) size.
6. **Wire into backtester:** Same “evaluate setup” on historical bars; record trades and P&amp;L.

Once this is in place, adding a new setup is a new config file (or row), not a code change.
