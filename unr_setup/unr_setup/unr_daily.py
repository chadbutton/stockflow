"""
UnR daily context (Gil Morales): 20/50/200 EMA, 3-5 day move to MA, MA slope.

Bullish: price falls 3-5 days to a lower *upsloping* MA (undercut).
Bearish: price rises 3-5 days to a *downsloping* MA.

Parameters can come from configurable SetupCriteria (setup_specific).
"""

from typing import List, Optional, Tuple, Union

from unr_setup.setup_criteria import SetupCriteria

# Daily bar: (open, high, low, close) or (open, high, low, close, volume)
OHLC = Tuple[float, ...]


def _ema(series: List[float], period: int) -> List[float]:
    """Exponential moving average; first value at index period-1."""
    if not series or len(series) < period:
        return []
    k = 2.0 / (period + 1)
    out = [0.0] * len(series)
    out[period - 1] = sum(series[:period]) / period
    for i in range(period, len(series)):
        out[i] = series[i] * k + out[i - 1] * (1 - k)
    return out


def compute_emas(closes: List[float], periods: Tuple[int, ...] = (20, 50, 200)) -> dict:
    """
    Compute EMAs for given periods. Returns {20: [..], 50: [..], 200: [..]}.
    Each list aligned to closes; leading values before EMA is valid are 0.
    """
    result = {}
    for p in periods:
        ema_vals = _ema(closes, p)
        result[p] = ema_vals
    return result


def compute_sma(series: List[float], period: int) -> List[float]:
    """
    Simple moving average. First value at index period-1.
    Same length as series; leading values are 0.
    """
    if not series or len(series) < period:
        return []
    out = [0.0] * len(series)
    for i in range(period - 1, len(series)):
        out[i] = sum(series[i - period + 1 : i + 1]) / period
    return out


def _slope_upsloping(ema_series: List[float], idx: int, lookback: int = 5) -> bool:
    """EMA at idx is higher than lookback bars ago."""
    if idx < lookback or len(ema_series) < idx + 1:
        return False
    return ema_series[idx] > ema_series[idx - lookback]


def _slope_downsloping(ema_series: List[float], idx: int, lookback: int = 5) -> bool:
    """EMA at idx is lower than lookback bars ago."""
    if idx < lookback or len(ema_series) < idx + 1:
        return False
    return ema_series[idx] < ema_series[idx - lookback]


def _undercut_then_back_above(lows: List[float], closes: List[float], ma_vals: List[float], idx: int, window: int) -> bool:
    """In the last `window` days (including idx), price went below MA and closed back above (bullish undercut)."""
    start = max(0, idx - window + 1)
    for i in range(start, idx + 1):
        if lows[i] < ma_vals[i] and closes[idx] > ma_vals[idx]:
            return True
    return False


def _rally_then_back_below(highs: List[float], closes: List[float], ma_vals: List[float], idx: int, window: int) -> bool:
    """In the last `window` days, price went above MA and closed back below (bearish)."""
    start = max(0, idx - window + 1)
    for i in range(start, idx + 1):
        if highs[i] > ma_vals[i] and closes[idx] < ma_vals[idx]:
            return True
    return False


def _price_falling_n_days(closes: List[float], idx: int, n_min: int = 3, n_max: int = 5) -> bool:
    """Price declined over the last 3-5 days (close lower than n bars ago)."""
    for n in range(n_min, n_max + 1):
        if idx >= n and closes[idx] < closes[idx - n]:
            return True
    return False


def _close_is_lowest_in_last_n_days(closes: List[float], idx: int, n: int = 3) -> bool:
    """Current close is the lowest close among the last n days (true pullback, not just down open>close with higher highs)."""
    if idx < n:
        return False
    return closes[idx] <= min(closes[idx - i] for i in range(1, n + 1))


def _highs_decreasing_last_n_days(highs: List[float], idx: int, n: int = 3) -> bool:
    """Highs are (non-strictly) decreasing over the last n days: today's high <= yesterday's <= ... (lower highs = pullback)."""
    if idx < n:
        return False
    for i in range(1, n):
        if highs[idx - i + 1] > highs[idx - i]:
            return False
    return True


def _lows_increasing_last_n_days(lows: List[float], idx: int, n: int = 3) -> bool:
    """Lows are (non-strictly) increasing over the last n days: today's low >= yesterday's >= ... (higher lows = rally into resistance)."""
    if idx < n:
        return False
    for i in range(1, n):
        if lows[idx - i + 1] < lows[idx - i]:
            return False
    return True


def _price_rising_n_days(closes: List[float], idx: int, n_min: int = 3, n_max: int = 5) -> bool:
    """Price advanced over the last 3-5 days."""
    for n in range(n_min, n_max + 1):
        if idx >= n and closes[idx] > closes[idx - n]:
            return True
    return False


def _close_to_ma(close: float, ma: float, pct: float) -> bool:
    """Price is within pct of MA (e.g. 0.02 = within 2%)."""
    if ma <= 0:
        return False
    ratio = close / ma
    return (1.0 - pct) <= ratio <= (1.0 + pct)


def compute_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> List[float]:
    """
    Average True Range (ATR) using Wilder's smoothing (RMA), matching most platforms.
    TR = max(H-L, |H-prev_close|, |L-prev_close|). First ATR = SMA(TR, period), then
    ATR[i] = (ATR[i-1]*(period-1) + TR[i])/period.
    """
    n = len(closes)
    if n < 2 or len(highs) != n or len(lows) != n:
        return []
    tr = [0.0] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    atr = [0.0] * n
    if n < period:
        return atr
    atr[period - 1] = sum(tr[:period]) / period
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _close_to_ma_atr(close: float, ma: float, atr: float, atr_mult: float) -> bool:
    """Price is within atr_mult * ATR of the MA."""
    if atr <= 0:
        return False
    return abs(close - ma) <= atr_mult * atr


def unr_daily_context(
    daily_bars: List[OHLC],
    pullback_days_min: int = 3,
    slope_lookback: int = 5,
    criteria: Optional[SetupCriteria] = None,
    ema_periods: Optional[Tuple[int, ...]] = None,
) -> List[Tuple[str, int]]:
    """
    Determine UnR context for the most recent day (last bar).
    daily_bars: list of (open, high, low, close[, ...]); oldest first.
    Returns list of (direction, ma_used): e.g. [("long", 20), ("long", 50)] or [("short", 200)].

    If criteria is provided, pullback_days_min, slope_lookback and ema_periods
    are read from criteria.setup_specific. Explicit args override criteria.
    """
    require_ma_slope = True
    ma_proximity_pct = 0.02
    atr_period = 14
    atr_mult: Optional[float] = 1
    use_sma_periods: List[int] = [50, 200]
    rising_days_min = 3
    if criteria:
        if ema_periods is None:
            ema_periods = tuple(criteria.get_specific("daily_emas", [20, 50, 200]))
        use_sma_periods = list(criteria.get_specific("use_sma_periods", [50, 200]))
        pullback_days_min = criteria.get_specific("pullback_days_min", pullback_days_min)
        slope_lookback = criteria.get_specific("slope_lookback", slope_lookback)
        require_ma_slope = criteria.get_specific("require_ma_slope", True)
        ma_proximity_pct = criteria.get_specific("ma_proximity_pct", 0.02)
        atr_period = criteria.get_specific("atr_period", 14)
        atr_mult = criteria.get_specific("atr_mult", 1)
        rising_days_min = criteria.get_specific("rising_days_min", 3)
    if ema_periods is None:
        ema_periods = (20, 50, 200)

    min_bars = max(ema_periods) if ema_periods else 200
    if len(daily_bars) < min_bars:
        return []

    closes = [b[3] for b in daily_bars]
    highs = [b[1] for b in daily_bars]
    lows = [b[2] for b in daily_bars]
    idx = len(closes) - 1

    emas = compute_emas(closes, ema_periods)
    for p in use_sma_periods:
        if p in ema_periods:
            emas[p] = compute_sma(closes, p)
    use_atr = atr_mult is not None and atr_mult > 0
    atr_vals: List[float] = []
    if use_atr:
        atr_vals = compute_atr(highs, lows, closes, atr_period)
    result = []

    for ma_period in ema_periods:
        ema_vals = emas.get(ma_period)
        if not ema_vals or idx >= len(ema_vals) or ema_vals[idx] == 0:
            continue

        ma = ema_vals[idx]

        # Long only when price is at or above 50 MA (never list long when below 50 MA)
        ema_50_vals = emas.get(50)
        if 50 in ema_periods:
            if ema_50_vals and idx < len(ema_50_vals) and ema_50_vals[idx] > 0:
                long_above_50 = closes[idx] >= ema_50_vals[idx]
            else:
                long_above_50 = False  # can't verify 50 MA, don't allow long
        else:
            long_above_50 = True  # 50 MA not in config

        # Long: past 3 days have lower highs (decreasing highs = pullback structure); close to MA, above 50 MA
        slope_ok_bull = not require_ma_slope or _slope_upsloping(ema_vals, idx, slope_lookback)
        price_ok_bull = _highs_decreasing_last_n_days(highs, idx, 3)
        if use_atr and idx < len(atr_vals) and atr_vals[idx] > 0:
            near_ma = _close_to_ma_atr(closes[idx], ma, atr_vals[idx], atr_mult) and closes[idx] >= ma
        else:
            near_ma = _close_to_ma(closes[idx], ma, ma_proximity_pct) and closes[idx] >= ma
        near_ok_bull = near_ma
        if slope_ok_bull and price_ok_bull and near_ok_bull and long_above_50:
            result.append(("long", ma_period))

        # Short: past 3 days have higher lows (increasing lows = rally structure); strictly below MA, close to MA
        slope_ok_bear = not require_ma_slope or _slope_downsloping(ema_vals, idx, slope_lookback)
        price_ok_bear = _lows_increasing_last_n_days(lows, idx, 3)
        if slope_ok_bear and price_ok_bear:
            if use_atr and idx < len(atr_vals) and atr_vals[idx] > 0:
                near_ok_bear = _close_to_ma_atr(closes[idx], ma, atr_vals[idx], atr_mult) and closes[idx] < ma
            else:
                near_ok_bear = _close_to_ma(closes[idx], ma, ma_proximity_pct) and closes[idx] < ma
            if near_ok_bear:
                result.append(("short", ma_period))

    return result
