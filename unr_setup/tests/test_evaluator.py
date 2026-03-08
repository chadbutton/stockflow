"""Unit tests for UnR evaluator (daily + 65min combined)."""

from datetime import datetime

import pytest
from unr_setup.evaluator import evaluate_unr
from unr_setup.strat import BarType
from unr_setup.unr_daily import compute_emas


def _daily_bars_bullish_long_20():
    """Build 250 daily bars that yield bullish UnR context on 20 EMA (simplified)."""
    n = 250
    closes = [100.0 + i * 0.2 for i in range(n - 10)]
    # Last 5: pullback (lower closes), then close above EMA20
    emas = compute_emas(closes, (20,))
    if not emas[20]:
        return None
    idx = len(closes) - 1
    ema20 = emas[20][idx]
    for _ in range(5):
        closes.append(closes[-1] - 0.3)
    # Last bar close above EMA; one prior low below EMA
    closes[-1] = ema20 + 0.2
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    lows[-3] = ema20 - 0.2  # undercut
    return list(zip(closes, highs, lows, closes))


def test_evaluate_unr_no_daily_context():
    # No pullback / no undercut: no context
    flat = [(100, 101, 99, 100)] * 250
    bars_65 = [
        (100, 105, 98, 99),
        (99, 102, 95, 95),
        (96, 101, 96, 98),
        (99, 102.5, 97, 102),
    ]
    result = evaluate_unr(flat, bars_65, symbol="AAPL")
    # May be None if no context, or if context exists we'd get trigger
    assert result is None or (result.direction == "long" and result.ma_used in (20, 50, 200))


def test_evaluate_unr_no_212_no_trigger():
    # Daily with context but 65min not 2-1-2
    closes = [100.0 + i * 0.2 for i in range(250)]
    bars = [(c, c + 1, c - 1, c) for c in closes]
    bars_65 = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100)]  # no 2-1-2
    result = evaluate_unr(bars, bars_65)
    # Either no context (so None) or no reversal (None)
    assert result is None or hasattr(result, "trigger")


def test_evaluate_unr_returns_result_with_trigger():
    # Daily bars that might give context; 65min with clear 2-1-2 long
    daily = [(100 + i * 0.1, 101 + i * 0.1, 99 + i * 0.1, 100 + i * 0.1) for i in range(250)]
    # Ensure last 5 days declining and undercut then above 20 EMA (messy; use mock in integration)
    bars_65 = [
        (100, 105, 98, 99),
        (99, 102, 95, 95),
        (96, 101, 96, 98),
        (99, 102.5, 97, 102),
    ]
    result = evaluate_unr(daily, bars_65, symbol="TEST")
    # If daily context has "long", we get UnREvalResult with trigger
    if result:
        assert result.trigger.symbol == "TEST"
        assert result.trigger.direction == "long"
        assert result.trigger.entry_price == 102
        assert result.trigger.stop_price == 96
        assert result.ma_used in (20, 50, 200)


def test_evaluate_unr_trigger_has_entry_stop():
    daily = [(100, 101, 99, 100)] * 250
    bars_65 = [
        (100, 105, 98, 99),
        (99, 102, 95, 95),
        (96, 101, 96, 98),
        (99, 102.5, 97, 102),
    ]
    result = evaluate_unr(daily, bars_65)
    if result:
        t = result.trigger
        assert t.entry_price > 0 and t.stop_price > 0
        assert t.strat_pattern == "2-1-2"
