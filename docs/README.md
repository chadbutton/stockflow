# Stock Candlestick Setup Scanner — Documentation

Documentation for the real-time candlestick setup scanner with backtesting, Trade Ideas–style dashboard, and phased Slack/IB integration.

| Document | Purpose |
|----------|---------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Full system architecture: **two-phase flow** (daily scan → watchlist → real-time trigger), data providers (§12), phases (1–3). |
| **[SETUP_CRITERIA.md](SETUP_CRITERIA.md)** | How to define setup criteria first: schema, conditions, entry/stop types, examples. |
| **[STOCK_UNIVERSE.md](STOCK_UNIVERSE.md)** | Configurable stock universe: ATR, market cap, volume×price, price filters, session. |
| **[SETUP_UNR.md](SETUP_UNR.md)** | UnR setup spec: daily EMA undercut + 65min Strat 2-1-2 trigger, scoring, DB. |

**Flow:** After market close, run **daily scan** on full universe → build **watchlist** (symbols meeting daily criteria). In real time, load **lower-timeframe data only for the watchlist** and run trigger logic. This reduces data and cost; see ARCHITECTURE §12 for provider comparison.
