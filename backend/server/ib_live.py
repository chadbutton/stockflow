"""
Interactive Brokers live (tick) price feed via ib_insync.
Run TWS or IB Gateway and set IB_HOST, IB_PORT (e.g. 127.0.0.1, 4002).
Prices are cached in memory; realtime endpoint uses them when available.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Optional

# Lazy import ib_insync so backend starts even if not installed / IB not used
_ib: Optional[object] = None

def _ensure_ib():
    global _ib
    if _ib is None:
        try:
            import ib_insync as _ib_mod
            _ib = _ib_mod
        except ImportError:
            _ib = False
    return _ib


# Thread-safe shared state
_lock = threading.Lock()
_symbols_requested: set[str] = set()
_price_cache: dict[str, float] = {}
_tickers: dict[str, object] = {}
_ib_conn: Optional[object] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_connected = False


def set_symbols(symbols: list[str]) -> None:
    """Request that these symbols be subscribed for live data (additive)."""
    _ensure_ib()
    with _lock:
        _symbols_requested.update(symbols)


def get_price(symbol: str) -> Optional[float]:
    """Return last live price for symbol, or None if not available."""
    with _lock:
        return _price_cache.get(symbol)


def get_prices(symbols: list[str]) -> dict[str, float]:
    """Return dict of symbol -> price for any symbols we have in cache."""
    with _lock:
        return {s: _price_cache[s] for s in symbols if s in _price_cache}


def is_connected() -> bool:
    return _connected


def _run_async_loop(host: str, port: int, client_id: int) -> None:
    global _ib_conn, _connected, _price_cache, _tickers
    ib_mod = _ensure_ib()
    if not ib_mod:
        return
    IB = getattr(ib_mod, "IB", None)
    Stock = getattr(ib_mod, "Stock", None)
    if not IB or not Stock:
        return

    async def run() -> None:
        global _ib_conn, _connected, _price_cache, _tickers
        ib = IB()
        try:
            await ib.connectAsync(host=host, port=port, clientId=client_id)
            _ib_conn = ib
            _connected = True
        except Exception:
            _connected = False
            return

        try:
            while True:
                await asyncio.sleep(0.25)
                with _lock:
                    to_sub = _symbols_requested.copy()
                for sym in to_sub:
                    if sym in _tickers:
                        continue
                    try:
                        contract = Stock(sym, "SMART", "USD")
                        ticker = ib.reqMktData(contract, "", False, False)
                        with _lock:
                            _tickers[sym] = ticker
                    except Exception:
                        pass

                with _lock:
                    current = set(_tickers.keys())
                for sym in list(current):
                    if sym not in _symbols_requested:
                        try:
                            ticker = _tickers.get(sym)
                            if ticker is not None:
                                ib.cancelMktData(ticker.contract)
                        except Exception:
                            pass
                        with _lock:
                            _tickers.pop(sym, None)
                            _price_cache.pop(sym, None)

                for sym, ticker in list(_tickers.items()):
                    try:
                        p = ticker.marketPrice()
                        if p is None:
                            continue
                        p = float(p)
                        if p != p or p <= 0:
                            continue
                        with _lock:
                            _price_cache[sym] = p
                    except (TypeError, ValueError, Exception):
                        pass
        except asyncio.CancelledError:
            pass
        finally:
            try:
                ib.disconnect()
            except Exception:
                pass
            _connected = False
            _ib_conn = None
            with _lock:
                _tickers.clear()
                _price_cache.clear()

    try:
        asyncio.run(run())
    except Exception:
        _connected = False


def start(host: str = "127.0.0.1", port: int = 4002, client_id: int = 10) -> None:
    """Start the IB live feed in a background thread. Call once at app startup if IB is enabled."""
    if not _ensure_ib():
        return
    t = threading.Thread(target=_run_async_loop, args=(host, port, client_id), daemon=True)
    t.start()
