"""
The Strat (Rob Smith): bar classification and reversal pattern detection.

Bar types:
- 1: Inside bar (high < prev high AND low > prev low)
- 2U: Two-up (breaks previous high only)
- 2D: Two-down (breaks previous low only)
- 3: Outside bar (breaks both high and low)

Reversal patterns: 2-1-2, 2-2, 1-2-2, 3-1-2, 1-3 (all supported).
"""

from enum import Enum
from typing import List, Optional, Tuple

# (open, high, low, close) per bar
OHLC = Tuple[float, float, float, float]

# Result: (direction, entry_price, stop_price)
ReversalResult = Tuple[str, float, float]


class BarType(str, Enum):
    INSIDE = "1"
    TWO_UP = "2U"
    TWO_DOWN = "2D"
    OUTSIDE = "3"


def classify_bar(prev: OHLC, curr: OHLC) -> BarType:
    """
    Classify current bar relative to previous bar (The Strat).
    prev, curr are (open, high, low, close).
    """
    ph, pl = prev[1], prev[2]
    ch, cl = curr[1], curr[2]

    breaks_high = ch > ph
    breaks_low = cl < pl

    if not breaks_high and not breaks_low:
        return BarType.INSIDE
    if breaks_high and breaks_low:
        return BarType.OUTSIDE
    if breaks_high:
        return BarType.TWO_UP
    return BarType.TWO_DOWN


def classify_bars(bars: List[OHLC]) -> List[BarType]:
    """Classify each bar (index 0 has no previous bar -> None)."""
    if len(bars) < 2:
        return []
    return [classify_bar(bars[i], bars[i + 1]) for i in range(len(bars) - 1)]


def is_212_reversal(
    bars: List[OHLC],
    types: Optional[List[BarType]] = None,
) -> Optional[Tuple[str, float, float]]:
    """
    Detect 2-1-2 reversal on the last 4 bars (bar0, bar1, bar2, bar3).
    Sequence: bar1 = 2D or 2U, bar2 = inside bar1, bar3 = opposite direction breaking bar2.
    bars: at least 4 OHLC bars (oldest first).
    types: optional pre-classified types (type of bar i+1 vs bar i); need last 3 for bars[-4:].

    Returns:
        None if no 2-1-2.
        ("long", entry_price, stop_price) for bullish 2-1-2 (2D -> 1 -> 2U).
        ("short", entry_price, stop_price) for bearish 2-1-2 (2U -> 1 -> 2D).
    Entry = close of trigger bar (bar3); stop = opposite side of inside bar (bar2).
    """
    if len(bars) < 4:
        return None

    last4 = bars[-4:]
    bar0, bar1, bar2, bar3 = last4[0], last4[1], last4[2], last4[3]

    if types is None:
        t01 = classify_bar(bar0, bar1)  # bar1 type
        t12 = classify_bar(bar1, bar2)  # bar2 = inside
        t23 = classify_bar(bar2, bar3)  # bar3 type
    else:
        if len(types) < 3:
            return None
        t01, t12, t23 = types[-3], types[-2], types[-1]

    inside_high = bar2[1]
    inside_low = bar2[2]
    close3 = bar3[3]

    # Bullish 2-1-2: bar1=2D, bar2=1, bar3=2U (break inside high only)
    if t01 == BarType.TWO_DOWN and t12 == BarType.INSIDE and t23 == BarType.TWO_UP:
        if bar3[1] > inside_high and bar3[2] >= bar2[2]:
            return ("long", close3, inside_low)

    # Bearish 2-1-2: bar1=2U, bar2=1, bar3=2D (break inside low only)
    if t01 == BarType.TWO_UP and t12 == BarType.INSIDE and t23 == BarType.TWO_DOWN:
        if bar3[2] < inside_low and bar3[1] <= bar2[1]:
            return ("short", close3, inside_high)

    return None


def is_22_reversal(
    bars: List[OHLC],
    types: Optional[List[BarType]] = None,
) -> Optional[ReversalResult]:
    """
    2-2 reversal: two directional bars, opposite. Bar1=2D, bar2=2U (bullish) or bar1=2U, bar2=2D (bearish).
    Entry = close of bar2 (break of bar1); stop = opposite side of bar1.
    Needs 3 bars (bar0, bar1, bar2).
    """
    if len(bars) < 3:
        return None
    last3 = bars[-3:]
    bar0, bar1, bar2 = last3[0], last3[1], last3[2]
    if types is None:
        t01 = classify_bar(bar0, bar1)
        t12 = classify_bar(bar1, bar2)
    else:
        if len(types) < 2:
            return None
        t01, t12 = types[-2], types[-1]
    close2 = bar2[3]
    # Bullish: bar1=2D, bar2=2U; bar2 breaks bar1 high
    if t01 == BarType.TWO_DOWN and t12 == BarType.TWO_UP:
        if bar2[1] > bar1[1]:
            return ("long", close2, bar1[2])
    # Bearish: bar1=2U, bar2=2D; bar2 breaks bar1 low
    if t01 == BarType.TWO_UP and t12 == BarType.TWO_DOWN:
        if bar2[2] < bar1[2]:
            return ("short", close2, bar1[1])
    return None


def is_122_reversal(
    bars: List[OHLC],
    types: Optional[List[BarType]] = None,
) -> Optional[ReversalResult]:
    """
    1-2-2 reversal: bar1=inside, bar2=directional, bar3=opposite directional.
    Bullish: 1 -> 2D -> 2U (bar3 breaks bar2 high). Bearish: 1 -> 2U -> 2D (bar3 breaks bar2 low).
    Needs 4 bars.
    """
    if len(bars) < 4:
        return None
    last4 = bars[-4:]
    bar0, bar1, bar2, bar3 = last4[0], last4[1], last4[2], last4[3]
    if types is None:
        t01 = classify_bar(bar0, bar1)
        t12 = classify_bar(bar1, bar2)
        t23 = classify_bar(bar2, bar3)
    else:
        if len(types) < 3:
            return None
        t01, t12, t23 = types[-3], types[-2], types[-1]
    if t01 != BarType.INSIDE:
        return None
    close3 = bar3[3]
    # Bullish: bar2=2D, bar3=2U breaking bar2 high
    if t12 == BarType.TWO_DOWN and t23 == BarType.TWO_UP:
        if bar3[1] > bar2[1] and bar3[2] >= bar2[2]:
            return ("long", close3, bar2[2])
    # Bearish: bar2=2U, bar3=2D breaking bar2 low
    if t12 == BarType.TWO_UP and t23 == BarType.TWO_DOWN:
        if bar3[2] < bar2[2] and bar3[1] <= bar2[1]:
            return ("short", close3, bar2[1])
    return None


def is_312_reversal(
    bars: List[OHLC],
    types: Optional[List[BarType]] = None,
) -> Optional[ReversalResult]:
    """
    3-1-2 reversal: bar1=outside (3), bar2=inside (1), bar3=directional (2).
    Bullish: 3 -> 1 -> 2U (bar3 breaks bar2 high). Bearish: 3 -> 1 -> 2D (bar3 breaks bar2 low).
    Needs 4 bars.
    """
    if len(bars) < 4:
        return None
    last4 = bars[-4:]
    bar0, bar1, bar2, bar3 = last4[0], last4[1], last4[2], last4[3]
    if types is None:
        t01 = classify_bar(bar0, bar1)
        t12 = classify_bar(bar1, bar2)
        t23 = classify_bar(bar2, bar3)
    else:
        if len(types) < 3:
            return None
        t01, t12, t23 = types[-3], types[-2], types[-1]
    if t01 != BarType.OUTSIDE or t12 != BarType.INSIDE:
        return None
    inside_high, inside_low = bar2[1], bar2[2]
    close3 = bar3[3]
    if t23 == BarType.TWO_UP and bar3[1] > inside_high and bar3[2] >= bar2[2]:
        return ("long", close3, inside_low)
    if t23 == BarType.TWO_DOWN and bar3[2] < inside_low and bar3[1] <= bar2[1]:
        return ("short", close3, inside_high)
    return None


def is_13_reversal(
    bars: List[OHLC],
    types: Optional[List[BarType]] = None,
) -> Optional[ReversalResult]:
    """
    1-3 reversal: bar1=inside, bar2=outside (engulfs bar1). Direction by close vs range.
    Bullish if bar2 close > mid(bar1); bearish if bar2 close < mid(bar1). Stop = opposite side of bar2.
    Needs 3 bars.
    """
    if len(bars) < 3:
        return None
    last3 = bars[-3:]
    bar0, bar1, bar2 = last3[0], last3[1], last3[2]
    if types is None:
        t01 = classify_bar(bar0, bar1)
        t12 = classify_bar(bar1, bar2)
    else:
        if len(types) < 2:
            return None
        t01, t12 = types[-2], types[-1]
    if t01 != BarType.INSIDE or t12 != BarType.OUTSIDE:
        return None
    close2 = bar2[3]
    mid1 = (bar1[1] + bar1[2]) / 2
    if close2 > mid1:
        return ("long", close2, bar2[2])
    return ("short", close2, bar2[1])


# Registry of pattern names to detector functions (each returns ReversalResult or None)
_STRAT_REVERSAL_DETECTORS = {
    "2-1-2": is_212_reversal,
    "2-2": is_22_reversal,
    "1-2-2": is_122_reversal,
    "3-1-2": is_312_reversal,
    "1-3": is_13_reversal,
}

DEFAULT_STRAT_REVERSAL_PATTERNS = ["2-1-2", "2-2", "1-2-2", "3-1-2", "1-3"]


def detect_strat_reversal(
    bars: List[OHLC],
    patterns: Optional[List[str]] = None,
) -> Optional[Tuple[str, float, float, str]]:
    """
    Try each Strat reversal pattern in order; return first match.
    Returns (direction, entry_price, stop_price, pattern_name) or None.
    """
    if patterns is None:
        patterns = DEFAULT_STRAT_REVERSAL_PATTERNS
    for name in patterns:
        fn = _STRAT_REVERSAL_DETECTORS.get(name)
        if fn is None:
            continue
        result = fn(bars)
        if result is not None:
            return (*result, name)
    return None
