# Stock Universe — Configurable Definition

The **stock universe** is the set of symbols the real-time scanner and backtester run on. It should be configurable via filters (no code change) so you can focus on liquid, tradeable names that fit your setup logic.

---

## 0. Starter Universe (Default)

For initial use, the universe is **most liquid US stocks, minimum ~$40M market cap, USA indexes** (NYSE/NASDAQ), and **must include** names like PLTR, TSLA, GOOG, MSFT, AAPL, etc.

| Rule | Description |
|------|-------------|
| **Liquidity** | Most liquid (e.g. top by average dollar volume or S&P 500 / NASDAQ 100 style). |
| **Market cap** | Min **$40M** (exclude micro-caps); no max unless you want mid-cap only. |
| **USA indexes** | Constituents of US indexes (NYSE, NASDAQ); no OTC or non-US. |
| **Must include** | PLTR, TSLA, GOOG, GOOGL, MSFT, AAPL, AMZN, NVDA, META, and other liquid large caps. |

**Static list:** A starter file is provided at `backend/config/universe_liquid_us.txt` with 200+ symbols satisfying the above. Use it as the default universe for the daily scan; add/remove tickers as needed. When you have a screener or data API, you can replace this with a dynamically generated list using the same filters.

---

## 1. Universe Modes

| Mode | Description | Use case |
|------|-------------|----------|
| **Static list** | Explicit ticker list (e.g. watchlist, file). | Curated names; small universe. |
| **Screener** | Rules applied to a broader universe (e.g. all US equities or a sector). | Larger scan; filter by liquidity, cap, price, ATR. |
| **Hybrid** | Start from static list, then apply filters (e.g. min dollar volume). | Combine watchlist with liquidity guard. |

---

## 2. Filter Types (Configurable)

All of these can be exposed as configuration (e.g. YAML/JSON or UI).

### 2.1 Price

- **Price ≥ X** — Minimum price (e.g. $5, $10) to avoid penny stocks and reduce noise.
- **Price ≤ X** — Optional cap (e.g. for options or focus on mid-cap).

### 2.2 Market Cap

- **Min market cap** — Exclude micro-caps (e.g. ≥ $500M or $1B).
- **Max market cap** — Optional (e.g. focus on mid/small cap only).

*Data source: fundamentals or daily snapshot from your data provider.*

### 2.3 Liquidity (Volume × Price)

- **Min average dollar volume** — e.g. (Volume × Price) averaged over last N days ≥ $X.
- **Min share volume** — e.g. average daily volume ≥ Y shares.

These ensure you can enter/exit without moving the market and that your setup bars have meaningful volume.

### 2.4 Volatility (ATR)

- **Min ATR** or **min ATR %** — So that stop distance (e.g. 1× ATR) is not too tight (tick noise) or too wide (poor R).
- **Max ATR / max ATR %** — Optional; exclude extremely volatile names if desired.

*ATR can be computed from daily or intraday bars depending on your timeframes.*

### 2.5 Session

- **Regular session only** — NYSE/NASDAQ regular hours.
- **Include extended hours** — Pre-market and/or after-hours for Phase 3 and for scanning in those sessions.

---

## 3. Example Configuration (YAML)

```yaml
universe:
  mode: screener   # or: static, hybrid

  # For static: list symbols here
  # symbols: [ AAPL, MSFT, ... ]

  # For screener/hybrid: start from a source
  source: us_equities   # or: sector_etf_holdings, file path, etc.

  filters:
    price_min: 5
    price_max: null
    market_cap_min: 500_000_000
    market_cap_max: null
    avg_dollar_volume_min: 1_000_000
    avg_volume_days: 20
    atr_pct_min: 0.01
    atr_pct_max: 0.10
    session: regular   # or: extended

  # Refresh: how often to recompute universe (e.g. pre-market)
  refresh: daily
  refresh_time: "09:00"
```

---

## 4. Implementation Notes

- **Universe provider service:** Input = config; output = list of symbols. Cache result and refresh on schedule (e.g. once pre-market) to avoid repeated API calls.
- **Data dependencies:** Price and volume from daily (or intraday) bars; market cap from fundamentals or provider-specific screener. ATR from same bars you use for setups.
- **Backtest:** Use the same universe logic with **point-in-time** data (e.g. for each backtest date, compute universe as of that date) to avoid look-ahead bias. For simplicity, Phase 1 can use a fixed universe per run.

---

## 5. Relation to Architecture

- **Real-time scanner:** Runs only on symbols in the current universe.
- **Dashboard:** Can show “universe size” and “active filters” so users know what’s being scanned.
- **Backtesting:** Same filters define which symbols and dates are scanned; position sizing uses same risk rules.

Defining the universe in one place (config + universe provider) keeps live and backtest aligned and makes it easy to tune (e.g. stricter ATR or dollar volume) without code changes.
