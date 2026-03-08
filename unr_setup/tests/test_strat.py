"""Unit tests for The Strat bar classification and reversal patterns (2-1-2, 2-2, 1-2-2, 3-1-2, 1-3)."""

import pytest
from unr_setup.strat import (
    BarType,
    classify_bar,
    classify_bars,
    is_212_reversal,
    is_22_reversal,
    is_13_reversal,
    detect_strat_reversal,
)

# OHLC = (open, high, low, close)
# Bar type is determined by current bar's high/low vs previous bar's high/low


def test_classify_inside_bar():
    prev = (100, 110, 95, 105)
    curr = (102, 108, 97, 104)  # high < 110, low > 95
    assert classify_bar(prev, curr) == BarType.INSIDE


def test_classify_two_up():
    prev = (100, 110, 95, 105)
    curr = (106, 115, 100, 112)  # breaks high only (115 > 110, low 100 >= 95)
    assert classify_bar(prev, curr) == BarType.TWO_UP


def test_classify_two_down():
    prev = (100, 110, 95, 105)
    curr = (98, 108, 90, 92)  # breaks low only (90 < 95, high 108 <= 110)
    assert classify_bar(prev, curr) == BarType.TWO_DOWN


def test_classify_outside_bar():
    prev = (100, 110, 95, 105)
    curr = (99, 112, 94, 106)  # breaks both (112 > 110, 94 < 95)
    assert classify_bar(prev, curr) == BarType.OUTSIDE


def test_classify_bars():
    bars = [
        (100, 110, 95, 105),
        (102, 108, 97, 104),
        (103, 109, 98, 107),
        (106, 115, 100, 112),
    ]
    types = classify_bars(bars)
    assert len(types) == 3
    assert types[0] == BarType.INSIDE   # bar1 vs bar0
    assert types[1] == BarType.INSIDE   # bar2 vs bar1
    assert types[2] == BarType.TWO_UP   # bar3 vs bar2


def test_212_insufficient_bars():
    assert is_212_reversal([]) is None
    assert is_212_reversal([(1, 2, 0, 1)]) is None
    assert is_212_reversal([(1, 2, 0, 1), (1, 2, 0, 1), (1, 2, 0, 1)]) is None  # need 4 bars


def test_212_bullish_reversal():
    # bar0, bar1=2D, bar2=inside bar1, bar3=2U breaking bar2 high
    bar0 = (100, 105, 98, 99)
    bar1 = (99, 102, 95, 95)   # 2D: breaks bar0 low (95<98), not high
    bar2 = (96, 101, 96, 98)   # inside bar1: high<102, low>95
    bar3 = (99, 102.5, 97, 102)  # 2U: break bar2 high (102.5>101), low 97 >= 96
    bars = [bar0, bar1, bar2, bar3]
    result = is_212_reversal(bars)
    assert result is not None
    direction, entry, stop = result
    assert direction == "long"
    assert entry == 102
    assert stop == 96


def test_212_bearish_reversal():
    bar0 = (100, 102, 97, 101)
    bar1 = (101, 106, 102, 105)  # 2U: breaks bar0 high
    bar2 = (104, 105, 103, 104)  # inside bar1
    bar3 = (104, 104.5, 102, 102.5)  # 2D: break bar2 low (102 < 103), high <= 105
    bars = [bar0, bar1, bar2, bar3]
    result = is_212_reversal(bars)
    assert result is not None
    direction, entry, stop = result
    assert direction == "short"
    assert entry == 102.5
    assert stop == 105


def test_212_no_reversal_wrong_sequence():
    # 1 -> 1 -> 2U (no 2D first)
    bar0 = (100, 105, 98, 102)
    bar1 = (102, 104, 99, 101)   # inside bar0
    bar2 = (101, 103, 100, 102)  # inside bar1
    bar3 = (102, 106, 101, 105)  # 2U
    bars = [bar0, bar1, bar2, bar3]
    assert is_212_reversal(bars) is None


def test_212_bullish_2u_must_not_break_inside_low():
    bar0 = (100, 105, 98, 99)
    bar1 = (99, 102, 95, 95)
    bar2 = (96, 101, 96, 98)
    bar3 = (99, 102.5, 95.5, 102)  # low 95.5 < bar2 low 96 -> invalid 2U
    bars = [bar0, bar1, bar2, bar3]
    assert is_212_reversal(bars) is None


def test_22_bullish_reversal():
    # bar0, bar1=2D, bar2=2U breaking bar1 high
    bar0 = (100, 105, 98, 99)
    bar1 = (99, 102, 95, 95)   # 2D
    bar2 = (96, 103, 97, 102)  # 2U: high 103 > bar1 high 102
    bars = [bar0, bar1, bar2]
    result = is_22_reversal(bars)
    assert result is not None
    direction, entry, stop = result
    assert direction == "long"
    assert entry == 102
    assert stop == 95


def test_22_bearish_reversal():
    bar0 = (98, 99, 95, 98)
    bar1 = (99, 104, 100, 103)  # 2U
    bar2 = (103, 103.5, 99, 99.5)  # 2D: low 99 < bar1 low 100
    bars = [bar0, bar1, bar2]
    result = is_22_reversal(bars)
    assert result is not None
    direction, entry, stop = result
    assert direction == "short"
    assert stop == 104


def test_detect_strat_reversal_returns_pattern_name():
    # 2-2 bullish should be detected and return pattern name
    bars = [
        (100, 105, 98, 99),
        (99, 102, 95, 95),
        (96, 103, 97, 102),
    ]
    result = detect_strat_reversal(bars)
    assert result is not None
    direction, entry, stop, name = result
    assert name == "2-2"
    assert direction == "long"


def test_detect_strat_reversal_tries_order():
    # Bars that match 2-1-2: should return 2-1-2 if it's first in list
    bars = [
        (100, 105, 98, 99),
        (99, 102, 95, 95),
        (96, 101, 96, 98),
        (99, 102.5, 97, 102),
    ]
    result = detect_strat_reversal(bars, patterns=["2-1-2", "2-2"])
    assert result is not None
    assert result[3] == "2-1-2"
    result_22_first = detect_strat_reversal(bars, patterns=["2-2", "2-1-2"])
    # 2-2 needs only 3 bars; last 3 are 102,95,95 then 101,96,98 then 102.5,97,102. bar1 101 inside 102,95? 101<102 and 96>95 so inside. bar2 102.5,97,102 vs 101,96,98: 102.5>101 and 97<96 so that's outside not 2U. So last 3 don't form 2-2. So 2-2 won't match on last 3, 2-1-2 will on last 4.
    assert result_22_first is not None
    assert result_22_first[3] == "2-1-2"


def test_13_reversal_bullish():
    # bar0, bar1=inside, bar2=outside; close above mid(bar1)
    bar0 = (100, 105, 95, 102)
    bar1 = (101, 104, 96, 103)   # inside bar0
    bar2 = (103, 106, 94, 105)   # outside bar1; close 105 > mid(100)
    bars = [bar0, bar1, bar2]
    result = is_13_reversal(bars)
    assert result is not None
    direction, entry, stop = result
    assert direction == "long"
    assert entry == 105
    assert stop == 94
