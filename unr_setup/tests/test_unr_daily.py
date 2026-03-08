"""Unit tests for UnR daily context (EMAs, slope, 3-5 day move, undercut)."""

import pytest
from unr_setup.unr_daily import compute_emas, unr_daily_context

# Daily bar = (open, high, low, close)


def _daily_bars_from_closes(closes: list) -> list:
    """Build minimal daily bars from close prices (O=H=L=C for simplicity)."""
    return [(c, c, c, c) for c in closes]


def test_compute_emas_length():
    closes = [100.0 + i for i in range(250)]
    emas = compute_emas(closes)
    assert 20 in emas and 50 in emas and 200 in emas
    assert len(emas[20]) == len(closes)
    assert len(emas[200]) == len(closes)


def test_compute_emas_rising_prices():
    closes = [100.0 + i * 0.5 for i in range(250)]
    emas = compute_emas(closes)
    # EMA should be rising at the end
    assert emas[20][-1] > emas[20][-10]
    assert emas[50][-1] > emas[50][-10]


def test_unr_daily_insufficient_bars():
    bars = _daily_bars_from_closes([100, 101, 102] * 50)  # 150 bars
    assert len(unr_daily_context(bars)) == 0  # need 200 for 200 EMA


def test_unr_daily_enough_bars_returns_list():
    """With 250 bars, context check runs; result is list of (direction, ma_used)."""
    closes = [100.0 + (i % 5) * 0.5 for i in range(250)]
    bars = _daily_bars_from_closes(closes)
    result = unr_daily_context(bars)
    assert isinstance(result, list)


def test_unr_daily_context_returns_list_of_tuples():
    closes = [100.0 + (i % 3) * 0.2 for i in range(250)]
    bars = _daily_bars_from_closes(closes)
    result = unr_daily_context(bars)
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert item[0] in ("long", "short")
        assert item[1] in (20, 50, 200)
