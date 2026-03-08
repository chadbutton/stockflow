# Stockflow

UnR watchlist scanner and dashboard: daily scan for setups (Undercut and Run), watchlist by date with performance, and a real-time actionable view with optional live prices from Interactive Brokers.

## Structure

- **backend** – FastAPI server: watchlist by date, realtime actionable (prices + hourly candles), optional IB live feed
- **dashboard** – React + MUI app: Watchlist tab (long/short tables, copy CSV, ATR distance columns) and RealTime Dashboard tab (countdown, actionable table, refresh interval)
- **unr_setup** – UnR setup logic and criteria (Python package)

## Quick start

1. **Install** (from repo root): see `INSTALL.md` for pip/venv and `.\install.ps1` (or `install.sh`).
2. **Run**: `.\launch_dashboard.ps1` (starts backend on :8000, then frontend; run from repo root).
3. **Optional – live IB data**: set `IB_ENABLED=1`, start TWS or IB Gateway with API enabled, then restart backend.

## GitHub

Repo root = this folder (`stockflow`). Clone and run from here.
