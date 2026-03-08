"""
Daily scan: for each symbol in universe, fetch daily bars and run setup daily context.
Produces watchlist (symbols that meet criteria).
"""

from datetime import date, timedelta
from typing import List, Optional, Union

from unr_setup.setup_criteria import SetupCriteria, load_criteria
from unr_setup.unr_daily import compute_atr, compute_emas, compute_sma, unr_daily_context

from scanner.data_provider import DailyDataProvider
from scanner.watchlist import WatchlistEntry


def run_daily_scan(
    symbols: List[str],
    provider: DailyDataProvider,
    setup_id: str = "unr",
    criteria: Optional[SetupCriteria] = None,
    criteria_dir: Optional[Union[str, None]] = None,
    as_of_date: Optional[date] = None,
    min_bars: int = 250,
) -> List[WatchlistEntry]:
    """
    Run daily setup context for each symbol. Returns watchlist entries that meet criteria.

    - symbols: list of tickers to scan
    - provider: supplies daily OHLC bars per symbol
    - setup_id: e.g. "unr"
    - criteria: optional; if None and criteria_dir set, load from config
    - as_of_date: date of the "last bar" (default: today)
    - min_bars: minimum daily bars to fetch (need 200+ for 200 EMA)
    """
    if criteria is None and criteria_dir:
        loaded = load_criteria(criteria_dir)
        criteria = loaded.get(setup_id)
    as_of = as_of_date or date.today()
    end = as_of
    # Need enough calendar days for min_bars trading days (~252/year)
    calendar_days = int(min_bars * (365 / 252)) + 60
    start = end - timedelta(days=calendar_days)

    ema_periods = (20, 50, 200)
    use_sma_periods: List[int] = [50, 200]
    atr_period = 14
    if criteria:
        ema_periods = tuple(criteria.get_specific("daily_emas", [20, 50, 200]))
        use_sma_periods = list(criteria.get_specific("use_sma_periods", [50, 200]))
        atr_period = criteria.get_specific("atr_period", 14)

    entries: List[WatchlistEntry] = []
    for symbol in symbols:
        bars = provider.get_daily_bars(symbol, start, end)
        if len(bars) < min_bars:
            continue
        highs = [b[1] for b in bars]
        lows = [b[2] for b in bars]
        closes = [b[3] for b in bars]
        idx = len(closes) - 1
        mas = compute_emas(closes, ema_periods)
        for p in use_sma_periods:
            if p in ema_periods:
                mas[p] = compute_sma(closes, p)
        atr_vals = compute_atr(highs, lows, closes, atr_period)
        price = closes[idx] if closes else None
        ema_20 = mas[20][idx] if 20 in mas and idx < len(mas[20]) else None
        ma_50 = mas[50][idx] if 50 in mas and idx < len(mas[50]) else None
        ma_200 = mas[200][idx] if 200 in mas and idx < len(mas[200]) else None
        atr = atr_vals[idx] if atr_vals and idx < len(atr_vals) and atr_vals[idx] else None

        contexts = unr_daily_context(bars, criteria=criteria)
        for direction, ma_used in contexts:
            entries.append(
                WatchlistEntry(
                    symbol=symbol,
                    setup_id=setup_id,
                    direction=direction,
                    ma_used=ma_used,
                    as_of_date=as_of.isoformat(),
                    price=round(price, 2) if price is not None else None,
                    ema_20=round(ema_20, 2) if ema_20 is not None else None,
                    ma_50=round(ma_50, 2) if ma_50 is not None else None,
                    ma_200=round(ma_200, 2) if ma_200 is not None else None,
                    atr=round(atr, 2) if atr is not None else None,
                )
            )
    return entries
