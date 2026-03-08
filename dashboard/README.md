# UnR Watchlist Dashboard

Dark-mode React dashboard (Replit-style) for viewing the UnR watchlist by date with performance since that date.

## Prerequisites

- **Node.js 18+** via **nvm** (see below)
- Backend API running (see below)

### Node via nvm

Use nvm to install and switch Node versions.

**Windows (nvm-windows):**

1. Install **nvm-windows**: [releases](https://github.com/coreybutler/nvm-windows/releases) — run `nvm-setup.exe`.
2. **Close and reopen** your terminal, then:
   ```powershell
   nvm install lts
   nvm use lts
   node -v
   npm -v
   ```

**macOS / Linux (nvm):**

1. Install nvm: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash` (or see [nvm](https://github.com/nvm-sh/nvm)).
2. Restart the terminal, then:
   ```bash
   nvm install --lts
   nvm use --lts
   node -v
   npm -v
   ```

**This project:** `dashboard/.nvmrc` specifies Node 20. From the `dashboard` folder run `nvm use` to switch to it, then `npm install` and `npm run dev`.

## Setup

```bash
cd dashboard
npm install
```

## Run

**Quick start (both backend + frontend):** from repo root run:

```powershell
.\launch_dashboard.ps1
```

This opens two windows (API on port 8000, dashboard on 5173). Close a window to stop that process.

**Or run manually:**

1. **Start the API** (from repo root):

   ```bash
   cd backend
   pip install -e .
   set PYTHONPATH=%CD%;%CD%\..\unr_setup
   python -m uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
   ```

   On PowerShell:

   ```powershell
   cd backend
   pip install -e .
   $env:PYTHONPATH = "$(Get-Location);$(Get-Location)\..\unr_setup"
   python -m uvicorn server.app:app --reload --port 8000
   ```

   API runs at **http://localhost:8000**.

2. **Start the dashboard**:

   ```bash
   cd dashboard
   npm run dev
   ```

   App runs at **http://localhost:5173**. The dev server proxies `/api` to the backend.

## Features

- **Date picker**: Choose any day in the past 60 days to see the watchlist as of that date.
- **Performance column**: % return from the selected date to today (green if positive, red if negative).
- **Dark theme**: Replit-style dark UI.

## Caching

The API caches watchlists under `backend/watchlists/watchlist_YYYY-MM-DD.json`. The first time you pick a date it may run the full scan (slow); subsequent loads use the cache. Pre-generate dates by running the scanner for each date and saving into `backend/watchlists/` if needed.
