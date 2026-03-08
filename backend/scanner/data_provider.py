"""
Data provider abstraction for daily bars. Implement this to plug in real APIs (Alpaca, Polygon, etc.).
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from pathlib import Path
from typing import List, Tuple

# (open, high, low, close) or (open, high, low, close, volume)
OHLC = Tuple[float, float, float, float]
OHLCV = Tuple[float, float, float, float, float]


class DailyDataProvider(ABC):
    """Abstract provider of daily OHLC(V) bars for a symbol."""

    @abstractmethod
    def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> List[OHLC]:
        """
        Return daily bars (oldest first). Each bar is (open, high, low, close) or (o, h, l, c, volume).
        Must have at least max(EMA periods) bars for UnR (e.g. 200).
        """
        pass


class CsvDailyProvider(DailyDataProvider):
    """Load daily bars from CSV files. One file per symbol: config/daily/<SYMBOL>.csv with columns date,open,high,low,close (header optional)."""

    def __init__(self, csv_dir: str | Path):
        self.csv_dir = Path(csv_dir)

    def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> List[OHLC]:
        path = self.csv_dir / f"{symbol.upper()}.csv"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return []
        # Support header: date,open,high,low,close or date,o,h,l,c
        rows = []
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            if parts[0].lower() in ("date", "timestamp"):
                continue
            try:
                d = date.fromisoformat(parts[0][:10])
                o, h, l, c = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                if start <= d <= end:
                    rows.append((d, o, h, l, c))
            except (ValueError, IndexError):
                continue
        rows.sort(key=lambda x: x[0])
        return [(r[1], r[2], r[3], r[4]) for r in rows]


class YahooDailyProvider(DailyDataProvider):
    """Fetch daily OHLC from Yahoo Finance (yfinance). No API key required."""

    def __init__(self, adjusted: bool = True):
        """
        adjusted: If True (default), use Yahoo adjusted OHLC (splits/dividends).
                 If False, use unadjusted — matches TradingView when it shows raw prices.
        """
        self._adjusted = adjusted

    def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> List[OHLC]:
        try:
            import yfinance as yf
        except ImportError:
            return []
        ticker = yf.Ticker(symbol)
        # yfinance end date is exclusive; add 1 day so the bar for `end` is included
        end_inclusive = end + timedelta(days=1)
        df = ticker.history(start=start, end=end_inclusive, auto_adjust=self._adjusted)
        if df is None or df.empty:
            return []
        for col in ("Open", "High", "Low", "Close"):
            if col not in df.columns:
                return []
        rows = []
        for ts, row in df.iterrows():
            d = ts.date() if hasattr(ts, "date") else date(ts.year, ts.month, ts.day)
            if start <= d <= end:
                rows.append((
                    d,
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                ))
        rows.sort(key=lambda x: x[0])
        return [(r[1], r[2], r[3], r[4]) for r in rows]


class MockDailyProvider(DailyDataProvider):
    """
    Mock provider for testing. Can load from CSV or use in-memory generated data.
    """

    def __init__(self, data: dict[str, List[OHLC]] | None = None):
        """
        data: optional dict symbol -> list of (o, h, l, c) bars oldest first.
        If None, get_daily_bars returns [] unless you set data later.
        """
        self._data = data or {}

    def set_symbol_bars(self, symbol: str, bars: List[OHLC]) -> None:
        self._data[symbol] = list(bars)

    def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> List[OHLC]:
        bars = self._data.get(symbol, [])
        # Mock ignores start/end; real provider would filter
        return bars


def make_unr_bullish_mock_bars(
    n_days: int = 260,
    base_price: float = 100.0,
    pullback_days: int = 4,
    undercut_bar_offset: int = 2,
) -> List[OHLC]:
    """
    Build synthetic daily bars that satisfy UnR bullish (20 EMA) context:
    - Uptrend then pullback 3-5 days
    - One bar undercuts 20 EMA (low below EMA), then close back above
    - 20 EMA is upsloping
    Returns oldest-first list of (o, h, l, c).
    """
    import math
    closes = []
    for i in range(n_days):
        # Uptrend then dip
        if i < n_days - pullback_days - 5:
            c = base_price + i * 0.15 + (i % 3) * 0.2
        else:
            # Pullback: last few days down
            j = i - (n_days - pullback_days - 5)
            c = base_price + (n_days - pullback_days - 5) * 0.15 - j * 0.4
        closes.append(c)

    # Ensure 20 EMA is valid and upsloping; ensure one bar undercuts then close above
    k = 2.0 / 21
    ema20 = [0.0] * n_days
    ema20[19] = sum(closes[:20]) / 20
    for i in range(20, n_days):
        ema20[i] = closes[i] * k + ema20[i - 1] * (1 - k)

    idx = n_days - 1
    # Pullback: last 4 days declining so _price_falling_n_days is true (close < close 3–5 ago)
    # Then last bar bounces: close above EMA but still below close from 3 days ago
    close_3_ago = closes[idx - 3]
    ema_last = ema20[idx]
    # Last bar close: above EMA (undercut then back above), below close_3_ago (still “pullback”)
    closes[idx] = min(ema_last + 0.3, close_3_ago - 0.1)
    # One of the recent bars had low below EMA
    undercut_i = idx - undercut_bar_offset
    if undercut_i >= 0:
        low_val = ema20[undercut_i] - 0.2
        closes[undercut_i] = ema20[undercut_i] + 0.1

    bars = []
    for i in range(n_days):
        c = closes[i]
        o = closes[i - 1] if i > 0 else c
        h = max(o, c) + 0.15
        if i == undercut_i and undercut_i >= 0:
            l = ema20[i] - 0.2
        else:
            l = min(o, c) - 0.1
        bars.append((o, h, l, c))
    return bars
