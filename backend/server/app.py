"""
Watchlist API: serve watchlist by date with performance since that date.
Run from repo root: uvicorn backend.server.app:app --reload
Or from backend: uvicorn server.app:app --reload
"""
from datetime import date, timedelta
from pathlib import Path
import sys
import os
import json
import time

# #region agent log
try:
    _dl = os.environ.get("DEBUG_LOG")
    if _dl:
        with open(_dl, "a") as _f:
            _f.write(json.dumps({"sessionId": "d56396", "location": "app.py:import", "message": "app.py loading", "data": {}, "timestamp": int(time.time() * 1000), "hypothesisId": "H-B1"}) + "\n")
except Exception:
    pass
# #endregion

# Ensure backend and dev root are on path
_BACKEND = Path(__file__).resolve().parent.parent
_DEV = _BACKEND.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from scanner.daily_scan import run_daily_scan
from scanner.data_provider import YahooDailyProvider
from scanner.watchlist import load_watchlist, save_watchlist

app = FastAPI(title="UnR Watchlist API")


# #region agent log
@app.on_event("startup")
def _log_startup():
    try:
        _dl = os.environ.get("DEBUG_LOG")
        if _dl:
            with open(_dl, "a") as _f:
                _f.write(json.dumps({"sessionId": "d56396", "location": "app.py:startup", "message": "uvicorn app started", "data": {}, "timestamp": int(time.time() * 1000), "hypothesisId": "H-B2"}) + "\n")
    except Exception:
        pass
    # Start IB live feed if configured (TWS or IB Gateway must be running)
    try:
        ib_host = os.environ.get("IB_HOST", "127.0.0.1")
        ib_port = int(os.environ.get("IB_PORT", "4002"))
        ib_client_id = int(os.environ.get("IB_CLIENT_ID", "10"))
        if os.environ.get("IB_ENABLED", "").strip().lower() in ("1", "true", "yes"):
            from server.ib_live import start as ib_start
            ib_start(host=ib_host, port=ib_port, client_id=ib_client_id)
    except Exception:
        pass
# #endregion

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCHLISTS_DIR = _BACKEND / "watchlists"
WATCHLISTS_DIR.mkdir(exist_ok=True)
UNIVERSE_PATH = _BACKEND / "config" / "universe_liquid_us.txt"
CRITERIA_DIR = _DEV / "unr_setup" / "config" / "setups"
MAX_DAYS_BACK = 60


def load_universe(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    return [s.strip() for s in text.splitlines() if s.strip() and not s.strip().startswith("#")]


def get_current_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch latest close for each symbol via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        return {}
    out = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if hist is not None and not hist.empty and "Close" in hist.columns:
                out[sym] = float(hist["Close"].iloc[-1])
        except Exception:
            continue
    return out


_sector_industry_cache: dict[str, dict] = {}


def get_sector_industry(symbols: list[str]) -> dict[str, dict]:
    """Fetch sector and industry for each symbol via yfinance .info. Cached (daily data, does not change)."""
    try:
        import yfinance as yf
    except ImportError:
        return {}
    global _sector_industry_cache
    out = {}
    missing = [s for s in symbols if s not in _sector_industry_cache]
    for sym in missing:
        try:
            t = yf.Ticker(sym)
            info = getattr(t, "info", None) or {}
            sector = info.get("sector") or info.get("sectorDisp")
            industry = info.get("industry") or info.get("industryDisp")
            _sector_industry_cache[sym] = {
                "sector": str(sector).strip() if sector else None,
                "industry": str(industry).strip() if industry else None,
            }
        except Exception:
            _sector_industry_cache[sym] = {"sector": None, "industry": None}
    for sym in symbols:
        out[sym] = _sector_industry_cache.get(sym) or {"sector": None, "industry": None}
    return out


def get_hourly_ohlc(symbols: list[str]) -> dict[str, dict]:
    """Fetch last 2 hourly candles (prev hour, current hour) per symbol. Keys: prev_hour, current_hour with o,h,l,c."""
    try:
        import yfinance as yf
    except ImportError:
        return {}
    out = {}
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d", interval="1h")
            if hist is None or hist.empty or "Close" not in hist.columns:
                continue
            cols = ["Open", "High", "Low", "Close"]
            if not all(c in hist.columns for c in cols):
                continue
            # Last row = current hour, second-to-last = previous hour
            n = len(hist)
            if n >= 2:
                prev = hist.iloc[-2]
                curr = hist.iloc[-1]
                out[sym] = {
                    "prev_hour": {
                        "o": round(float(prev["Open"]), 2),
                        "h": round(float(prev["High"]), 2),
                        "l": round(float(prev["Low"]), 2),
                        "c": round(float(prev["Close"]), 2),
                    },
                    "current_hour": {
                        "o": round(float(curr["Open"]), 2),
                        "h": round(float(curr["High"]), 2),
                        "l": round(float(curr["Low"]), 2),
                        "c": round(float(curr["Close"]), 2),
                    },
                }
            elif n == 1:
                curr = hist.iloc[-1]
                out[sym] = {
                    "prev_hour": None,
                    "current_hour": {
                        "o": round(float(curr["Open"]), 2),
                        "h": round(float(curr["High"]), 2),
                        "l": round(float(curr["Low"]), 2),
                        "c": round(float(curr["Close"]), 2),
                    },
                }
        except Exception:
            continue
    return out


@app.get("/api/watchlist")
def get_watchlist(
    date_str: str = Query(..., alias="date", description="YYYY-MM-DD, within past 60 days"),
    use_cache: bool = Query(True, description="Use cached watchlist file if exists"),
):
    try:
        as_of = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(400, "Invalid date, use YYYY-MM-DD")
    today = date.today()
    if as_of > today:
        raise HTTPException(400, "Date cannot be in the future")
    if (today - as_of).days > MAX_DAYS_BACK:
        raise HTTPException(400, f"Date must be within the past {MAX_DAYS_BACK} days")

    cache_path = WATCHLISTS_DIR / f"watchlist_{date_str}.json"

    if use_cache and cache_path.exists():
        entries = load_watchlist(cache_path)
    else:
        symbols = load_universe(UNIVERSE_PATH)
        if not symbols:
            raise HTTPException(500, "Universe file empty or missing")
        provider = YahooDailyProvider(adjusted=True)
        criteria_dir = str(CRITERIA_DIR) if CRITERIA_DIR.exists() else None
        entries = run_daily_scan(
            symbols=symbols,
            provider=provider,
            setup_id="unr",
            criteria_dir=criteria_dir,
            as_of_date=as_of,
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        save_watchlist(entries, cache_path)

    unique_symbols = list({e.symbol for e in entries})
    current_prices = get_current_prices(unique_symbols)
    sector_industry = get_sector_industry(unique_symbols)

    rows = []
    for rank, e in enumerate(entries, start=1):
        d = e.to_dict()
        price_as_of = e.price or 0
        current = current_prices.get(e.symbol)
        if current is not None and price_as_of and price_as_of > 0:
            performance_pct = round((current - price_as_of) / price_as_of * 100, 2)
        else:
            performance_pct = None
        d["current_price"] = round(current, 2) if current is not None else None
        d["performance_pct"] = performance_pct
        si = sector_industry.get(e.symbol) or {}
        d["sector"] = si.get("sector")
        d["industry"] = si.get("industry")
        d["rank"] = rank
        rows.append(d)

    return {
        "as_of_date": date_str,
        "setup_id": entries[0].setup_id if entries else "unr",
        "entries": rows,
    }


@app.get("/api/dates")
def get_available_dates():
    """Return list of dates (past 60 days) that have cached watchlists."""
    if not WATCHLISTS_DIR.exists():
        return {"dates": []}
    dates = []
    for f in WATCHLISTS_DIR.glob("watchlist_*.json"):
        try:
            # watchlist_2025-03-07.json
            d = f.stem.replace("watchlist_", "")
            dates.append(d)
        except Exception:
            continue
    return {"dates": sorted(dates, reverse=True)}


def _latest_watchlist_path() -> Path | None:
    """Return path to most recent cached watchlist (prefer today)."""
    if not WATCHLISTS_DIR.exists():
        return None
    today = date.today().isoformat()
    candidate = WATCHLISTS_DIR / f"watchlist_{today}.json"
    if candidate.exists():
        return candidate
    files = list(WATCHLISTS_DIR.glob("watchlist_*.json"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


@app.get("/api/realtime/status")
def get_realtime_status():
    """Return whether live IB data is connected (tick-by-tick)."""
    try:
        from server import ib_live
        return {"ib_connected": ib_live.is_connected()}
    except Exception:
        return {"ib_connected": False}


@app.get("/api/realtime/actionable")
def get_realtime_actionable():
    """
    Return watchlist entries enriched with current price and hourly candles.
    Frontend filters to actionable: long where current < previous_close, short where current > previous_close.
    """
    path = _latest_watchlist_path()
    if not path:
        return {"as_of_date": None, "entries": []}
    entries = load_watchlist(path)
    if not entries:
        return {"as_of_date": path.stem.replace("watchlist_", ""), "entries": []}
    as_of_date = entries[0].as_of_date
    unique_symbols = list({e.symbol for e in entries})
    current_prices = {}
    try:
        from server import ib_live
        ib_live.set_symbols(unique_symbols)
        current_prices = ib_live.get_prices(unique_symbols)
    except Exception:
        pass
    missing = [s for s in unique_symbols if s not in current_prices]
    if missing:
        yf_prices = get_current_prices(missing)
        current_prices = {**current_prices, **yf_prices}
    hourly = get_hourly_ohlc(unique_symbols)
    sector_industry = get_sector_industry(unique_symbols)
    rows = []
    for rank, e in enumerate(entries, start=1):
        prev_close = round(e.price, 2) if e.price is not None else None
        current = current_prices.get(e.symbol)
        current_price = round(current, 2) if current is not None else None
        h = hourly.get(e.symbol) or {}
        prev_hour = h.get("prev_hour")
        current_hour = h.get("current_hour")
        si = sector_industry.get(e.symbol) or {}
        rows.append({
            "symbol": e.symbol,
            "setup_id": e.setup_id,
            "direction": e.direction,
            "ma_used": e.ma_used,
            "previous_close": prev_close,
            "current_price": current_price,
            "prev_hour": prev_hour,
            "current_hour": current_hour,
            "sector": si.get("sector"),
            "industry": si.get("industry"),
            "rank": rank,
        })
    try:
        from server import ib_live
        live = ib_live.is_connected()
    except Exception:
        live = False
    return {"as_of_date": as_of_date, "entries": rows, "live": live}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
