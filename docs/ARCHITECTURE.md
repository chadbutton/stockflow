# Stock Candlestick Setup Scanner — Architecture Plan

## 1. Executive Summary

This document describes the architecture for a **real-time stock candlestick setup scanner** with backtesting, a Trade Ideas–style dashboard, configurable setups and stock universe, and a phased roadmap toward Slack alerts and Interactive Brokers integration.

**Core value:** Detect predefined technical setups on live and historical candlestick data, surface them on a dashboard with entry/stop/position sizing, and (later) notify via Slack and execute via IB.

**Data efficiency:** Use a **two-phase flow** — daily scan (after market hours) builds a **watchlist** of symbols that meet daily criteria; real-time scanning runs **only on the watchlist** for lower-timeframe trigger signals. This minimizes data loaded from third-party providers.

---

## 2. High-Level Architecture

### 2.1 Two-Phase Flow: Watchlist → Trigger

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CONFIGURATION LAYER                                  │
│  Setup Criteria │ Stock Universe Filters │ Risk/Position Sizing Rules             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
          ┌─────────────────────────────┴─────────────────────────────┐
          ▼                                                             ▼
┌─────────────────────────────┐                         ┌─────────────────────────────┐
│  PHASE 1: DAILY SCAN        │                         │  PHASE 2: REAL-TIME TRIGGER │
│  (after market close)       │                         │  (during market hours)       │
│                             │                         │                             │
│  • Full universe            │   watchlist              │  • Only watchlist symbols    │
│  • Daily bars only          │   (symbols that meet     │  • Lower timeframe only     │
│  • Run setup daily context  │    daily criteria)       │    (e.g. 65min)              │
│  • Output: WATCHLIST        │ ──────────────────────► │  • Run trigger logic        │
│                             │                         │  • Output: Alerts           │
└─────────────────────────────┘                         └─────────────────────────────┘
          │                                                             │
          │  Data: daily EOD (one call per symbol per day)              │  Data: intraday bars only for N symbols
          ▼                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ALERT & PRESENTATION: Dashboard (Trade Ideas–style) │ Slack (Phase 2) │ IB (Phase 3)  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

- **Phase 1 (daily, after hours):** Fetch **daily** OHLCV for the full stock universe (or a screened subset). Run **daily setup context** only (e.g. UnR: 20/50/200 EMA, 3–5 day pullback, undercut, slope). Persist the list of symbols that qualify as the **watchlist** for the next session.
- **Phase 2 (real-time):** Subscribe or poll **only for symbols on the watchlist**. Fetch or stream **lower-timeframe** bars (e.g. 65min). Run **trigger logic** (e.g. Strat 2-1-2) on each new bar. Emit alerts with entry/stop/size when a trigger fires.

**Benefits:** Far less intraday data and fewer API calls — no need to stream 65min (or 1min) for the entire universe, only for the watchlist (often tens to a few hundred symbols).

### 2.2 Legacy Single-Phase View (for reference)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  DATA & SCANNING (alternative: single phase)                                      │
│  Market Data Feed ──► Candlestick Aggregation ──► Setup Scanner (all symbols)    │
│  Historical Data ──► Backtesting Engine (same scanner logic)                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Prefer the two-phase flow for production to reduce cost and latency.

---

---

## 3. Setup Criteria (Define First)

Setup criteria are the **single source of truth** used by both real-time scanning and backtesting. They must be explicit and reproducible.

### 3.1 Setup Definition Model

Each **setup** is a named, versioned rule set that specifies:

| Concept | Description | Example |
|--------|-------------|--------|
| **Name / ID** | Unique identifier and human label | `bull-flag-15m`, `vcp-breakout` |
| **Timeframe(s)** | Candlestick interval(s) to evaluate | 1m, 5m, 15m, 1h, 1D |
| **Pattern / Conditions** | Logical conditions on OHLCV and derived series | See below |
| **Entry logic** | When a bar is considered “trigger” (e.g. break of level, close above) | Close above high of last N bars |
| **Stop logic** | Initial stop (used for risk and position size) | Below swing low, or ATR-based |
| **Optional targets** | R:R or price targets (for display/backtest) | 2R, 3R, or fixed levels |

### 3.2 Condition Building Blocks

Conditions should be composable (AND/OR) and operate on:

- **Price:** Open, High, Low, Close; optional HLC3, HL2.
- **Volume:** Raw volume, volume relative to average (e.g. VWAP or SMA of volume).
- **Derived series:** 
  - ATR (for volatility and stop distance),
  - EMAs/SMAs (e.g. price above 20 EMA),
  - Swing highs/lows (last N bars),
  - Breakouts (price vs level),
  - Candlestick shapes (e.g. body size, wicks, engulfing).
- **Multi-timeframe (optional):** e.g. 15m setup only when 1h trend is up (1h close > 1h MA).

### 3.3 Example Setup Criteria (Illustrative)

- **Bull flag / consolidation breakout**
  - Timeframe: 15m.
  - Conditions: Prior up move (e.g. close > SMA20), then N bars of range with lower volume; current bar closes above range high with volume > 1.5× average.
  - Entry: Close above range high (or next bar open).
  - Stop: Below range low or below last swing low (configurable).
  - Position size: From account risk % and (Entry − Stop) distance.

- **VCP-style breakout**
  - Conditions: Series of contractions in range and/or volume; price holds above a key MA; breakout bar with close above prior contraction high.
  - Entry/stop/size: Same idea as above, with setup-specific levels.

Setup definitions should live in **config** (e.g. JSON/YAML) or a small **setup registry** so they can be edited without code changes and shared between live and backtest.

---

## 4. Stock Universe (Configurable)

The **universe** is the set of symbols the scanner and backtester run on. It should be fully configurable.

### 4.1 Universe Definition

- **Explicit list:** Ticker list (e.g. from a watchlist or file).
- **Screener-style rules** (applied on a daily or intraday refresh):
  - **Price:** Price ≥ X (e.g. $5, $10).
  - **Market cap:** Min (and optionally max) market cap.
  - **Liquidity:**  
    - Min average dollar volume (Volume × Price) over N days.  
    - Min share volume.
  - **Volatility:** Min (and optionally max) ATR or ATR % so setups have meaningful stops and filters are not too noisy.
  - **Session:** Regular session only, or include extended hours (for Phase 3 and pre/post market scans).

### 4.2 Implementation Approach

- **Universe provider:** Module that takes config (price min, cap range, dollar volume, ATR, etc.) and returns list of symbols.
- **Refresh:** Scheduled (e.g. once pre-market) or on-demand; cache result for the day to avoid repeated API calls.
- **Data source:** Same as market data (e.g. fundamentals for cap, daily bars for volume/ATR); can start with a static list and add screening later.

---

## 5. Watchlist (Phase 1 Output)

### 5.1 Role

The **watchlist** is the list of symbols that **meet daily setup criteria** (e.g. UnR daily context: undercut of 20/50/200 EMA, 3–5 day pullback, correct slope). It is produced **after market close** (or pre-market) and is the **only** set of symbols for which lower-timeframe data is requested during the next session.

### 5.2 Storage and Refresh

- **Storage:** Persistent (DB table, file, or cache) keyed by setup_id and date (e.g. `watchlist_unr_2025-03-08`).
- **Refresh:** Once per day after daily bars are available (e.g. after 4pm ET or via scheduled job with provider’s EOD delay). Optionally refresh pre-market if using pre-market daily data.
- **Contents:** Symbol, setup_id, optional metadata (e.g. which MA qualified: 20/50/200). Real-time scanner reads this list and subscribes or polls only these symbols for the trigger timeframe.

### 5.3 Data Volume

- **Daily scan:** One daily bar request per symbol in the **universe** (e.g. 3,000–8,000 symbols). Typically one batch or paginated call per day.
- **Real-time:** Only **watchlist** symbols (e.g. 50–500) need 65min (or 1m) bars — either REST snapshots on a timer or WebSocket streams. This keeps provider usage and cost low.

---

## 6. Real-Time Trigger Scanning (Phase 2)

### 6.1 Data Flow

1. **Watchlist** is loaded at session start (or when daily scan completes).
2. **Lower-timeframe data** (e.g. 65min bars) is fetched or streamed **only for watchlist symbols** from the chosen provider.
3. **Candlestick aggregation** (if needed) builds the trigger timeframe from 1m or 5m if the provider doesn’t offer 65min directly.
4. **Trigger scanner** runs on each new completed bar (per symbol): evaluate trigger logic (e.g. Strat 2-1-2); if it matches, produce an **alert** with entry, stop, and suggested size.

### 6.2 Scanner Engine (Shared with Backtest)

- **Single “evaluate setup” function:** Given OHLCV history + setup definition → returns match (yes/no) and, if match, entry price, stop price, and (if desired) targets.
- **Real-time path:** On bar close, pass rolling window of bars into this function; emit alert when result is match.
- **Backtest path:** Same function, called on historical bars in a loop; no difference in setup logic.

### 6.3 Performance Considerations

- **Watchlist size** directly limits real-time data: smaller watchlist = fewer symbols to stream or poll.
- Run trigger scanner in a dedicated process; consider symbol sharding if watchlist is large.
- Cache indicator state (e.g. last N bars) per symbol so each new bar only does incremental work.

---

## 7. Position Sizing & Risk Per Trade

Every real-time alert should include **entry**, **stop**, and **position size** so the dashboard (and later IB) can display and use them consistently.

### 7.1 Inputs

- **Account risk per trade:** e.g. 0.5% or 1% of equity per trade (configurable).
- **Entry price:** From setup (e.g. breakout bar close or next open).
- **Stop price:** From setup (swing low, ATR-based, or level).
- **Account equity:** For live: from broker or user input; for backtest: from simulation.

### 7.2 Calculation

- **Risk amount** = Account equity × (risk % per trade).
- **Risk per share** = |Entry − Stop| (optionally + slippage/commission).
- **Position size (shares)** = Risk amount / Risk per share; round to lot size if needed.
- **Max position size** can be capped by a rule (e.g. max % of equity or max $).

Result is attached to each alert: **entry**, **stop**, **size (shares)**, and optionally **target(s)**.

---

## 8. Backtesting Component

### 8.1 Purpose

- Validate setup criteria on history.
- Compare performance across setups and parameter sets.
- Use the **same** setup scanner and position sizing as live (no “backtest-only” logic).

### 8.2 Design

- **Historical data:** OHLCV by symbol and timeframe (from same or compatible source as live).
- **Engine:** For each symbol in universe (or backtest universe), for each date/time, call the same **evaluate setup** with historical bars; when setup triggers, record “trade” with entry, stop, size; then simulate fill and track P&amp;L (e.g. hit stop or target or end of data).
- **Output:** Trade list, equity curve, simple stats (win rate, expectancy, max drawdown). Optional: parameter sensitivity, walk-forward.

### 8.3 Consistency

- Same setup criteria, same entry/stop/size rules. Only difference: real-time uses streaming bars; backtest uses stored bars. This keeps live behavior aligned with what was tested.

---

## 9. Dashboard (Trade Ideas–Style)

### 9.1 Goals

- Show **only** symbols that currently match at least one predefined setup (real-time).
- For each match: symbol, setup name, timeframe, entry, stop, position size, and optional chart/thumbnail.
- Fast, clear, and suitable for quick decision-making.

### 9.2 Main Elements

| Element | Description |
|--------|-------------|
| **Alert list / table** | Rows = current setup matches; columns = symbol, setup, timeframe, entry, stop, size, time of trigger. Sort/filter by setup, timeframe, symbol. |
| **Highlighting** | Rows (or symbols) that match setups are visually highlighted; non-matching symbols can be hidden or in a separate “watchlist” view. |
| **Charts** | Optional: small sparkline or full chart for selected row to show the pattern and levels (entry/stop). |
| **Config display** | Optional: show active universe and active setup names so users know what’s being scanned. |

### 9.3 Technical Options

- **Frontend:** Web app (React/Vue/Svelte, etc.) or desktop (Electron) that consumes a **REST or WebSocket API** from the scanning service.
- **Real-time updates:** WebSocket push of new/expired alerts so the list updates without refresh.
- **State:** Server holds “current alerts”; dashboard subscribes and renders; when a setup no longer qualifies (e.g. bar closed below level), remove or mark as expired.

---

## 10. Phased Roadmap

### Phase 1 (First Goal)

- **Setup criteria:** Define and implement 1–3 setups in config; shared “evaluate setup” used everywhere.
- **Stock universe:** Configurable (ATR, market cap, volume×price, price ≥ X, etc.); start with static list + filters.
- **Real-time scanning:** Candlestick aggregation from market data; run scanner on bar close; produce alerts with entry, stop, position size (risk per trade).
- **Dashboard:** Trade Ideas–style: list of active setup matches only; show entry, stop, size; highlight matches; optional charts.
- **Backtesting:** Same setup logic on historical data; basic metrics and trade list.

**Deliverable:** Real-time alerts that match predefined setups, with entry/stop/size, and a dashboard that highlights only those.

### Phase 2

- **Slack integration:** When an alert triggers, send a message to a Slack channel (or user) with symbol, setup, entry, stop, size, and optional link to dashboard/chart.
- **Config:** Slack webhook URL, channel, and toggle per setup or global.

### Phase 3

- **Interactive Brokers:** Connect to IB API (TWS or Gateway); fetch account equity; send orders (regular and extended hours) based on alert entry/stop/size.
- **Safety:** Order type (e.g. bracket: entry + stop loss + optional profit target); size caps; only send when user confirms or when auto-trade is explicitly enabled per setup/symbol.
- **Sessions:** Support regular and after-hours sessions for both scanning and execution.

---

## 11. Technology Suggestions (Summary)

| Layer | Suggestion | Notes |
|-------|------------|--------|
| **Setup criteria** | JSON/YAML or small DB | Versioned, editable without code deploy |
| **Market data** | See §12 for provider comparison | Daily for watchlist; intraday only for watchlist symbols |
| **Candlestick aggregation** | In-house or library (e.g. pandas, numpy) | Same logic for live and backtest |
| **Scanner + backtest** | One codebase (e.g. Python or C#) | Single “evaluate setup” and sizing |
| **Dashboard** | React/Vue + WebSocket + REST | Real-time alert list and optional charts |
| **Alerts API** | REST + WebSocket | List current alerts; push new/expired |
| **Phase 2** | Slack Incoming Webhook or Bot | Simple HTTP POST on alert |
| **Phase 3** | IB API (TWS/Gateway) | Official client libraries; handle reconnects and sessions |

---

## 12. Data Providers for Watchlist + Trigger

The **two-phase flow** (daily scan → watchlist → real-time trigger on lower timeframe) fits providers that offer:

1. **Daily EOD bars** for the full universe (batch or bulk) to build the watchlist.
2. **Intraday bars** (e.g. 1m, 5m, or **65min**) for **only the watchlist symbols**, via REST and/or WebSocket.

Below are providers that work well for this approach. Pricing and limits change; verify on each provider's site.

| Provider | Daily (watchlist build) | Intraday (trigger) | 65min bars | Notes |
|----------|-------------------------|--------------------|------------|--------|
| **Polygon.io** | REST: daily aggregates | REST + WebSocket; custom bars | **Yes** (multiplier=65, timespan=minute) | Strong fit. Custom bar API supports 65min directly. Stocks Developer tier ~$79/mo; check current plans. |
| **Alpaca** | REST: daily bars | REST + WebSocket (1m, etc.) | Build from 1m (e.g. 65×1m) | Free tier: 1m historical; good if you aggregate 65min from 1m. Broker + data in one. |
| **EODHD (EOD Historical Data)** | REST: EOD daily, 30+ years | REST: 1m, 5m, 1h intraday | 1h only natively; 65min via 1m aggregation | Lower cost (~$20/mo); daily + intraday; 65min would be client-side from 1m. |
| **Alpha Vantage** | REST: daily, weekly | REST: intraday (1m, 5m, etc.) | Possible via custom aggregation | Free tier very limited (calls/day); paid for serious scan. |
| **Interactive Brokers** | TWS/Gateway: historical daily | Real-time + historical bars | Depends on contract; often 1m then aggregate | Best if you already use IB for execution (Phase 3); single vendor for data + execution. |

### 12.1 Recommendations by Use Case

- **Minimize cost, have dev time to aggregate:** Use **Alpaca** (free 1m) or **EODHD** (low-cost daily + 1m). Build 65min bars from 1m in your app; run daily scan for watchlist, then request 1m (or 5m) only for watchlist symbols.
- **Simplest API, 65min native:** **Polygon.io** — custom bars with `multiplier=65&timespan=minute` so no client-side aggregation. Good for production and backtesting.
- **Already on IB for trading:** Use **IB** for both daily (watchlist) and intraday (watchlist only); keeps data and execution in one place and supports extended hours.

### 12.2 Data Volume (Rough)

- **Daily scan (Phase 1):** e.g. 5,000 symbols × 1 daily bar each = 5,000 bar requests once per day (batch or paginated).
- **Real-time (Phase 2):** e.g. 200 watchlist symbols × 65min bars. If provider gives 65min natively: ~6 bars/symbol/hour × 200 ≈ 1,200 bar updates/hour. If you aggregate from 1m: 200 symbols × 65 1m-bars per 65min window — still only 200 streams or polling loops, not 5,000.

---

## 13. Risk & Compliance Notes

- **Not financial advice:** System is for research and execution assistance; user is responsible for risk.
- **Data and execution:** Comply with data provider and broker ToS; ensure extended-hours trading is enabled if used.
- **Position sizing:** Always cap size and total exposure; validate orders before sending to IB.

---

## 14. Next Steps

1. **Finalize 1–2 setup criteria** in config format (conditions, entry, stop).
2. **Choose market data provider** (§12): daily EOD for full universe + intraday (e.g. 65min) only for watchlist symbols.
3. **Implement Phase 1:** Daily scan (after close) → run daily context per setup → persist **watchlist** (symbols that meet daily criteria).
4. **Implement Phase 2:** Load watchlist; fetch/stream lower-timeframe data **only for watchlist**; run trigger logic; emit alerts with entry/stop/size.
5. **Implement candlestick aggregation** if provider gives 1m (e.g. build 65min from 1m); validate with backtest.
6. **Dashboard** and alert API; then iterate, add Slack (Phase 2), and IB (Phase 3).

This architecture keeps setup logic unified between live and backtest, makes the universe and risk rules configurable, and delivers Phase 1 (real-time setup alerts + dashboard) before adding Slack and IB.
