"""Tests for daily scan: mock data and UnR context -> watchlist."""

from datetime import date

import pytest
from scanner.data_provider import MockDailyProvider, make_unr_bullish_mock_bars
from scanner.daily_scan import run_daily_scan
from scanner.watchlist import WatchlistEntry


def test_mock_bullish_bars_satisfy_unr():
    """Synthetic UnR bullish bars should be detected by unr_daily_context."""
    bars = make_unr_bullish_mock_bars(260)
    assert len(bars) >= 200
    from unr_setup.unr_daily import unr_daily_context
    contexts = unr_daily_context(bars)
    assert len(contexts) >= 1
    assert any(d == "long" and ma in (20, 50, 200) for d, ma in contexts)


def test_run_daily_scan_finds_mock_unr():
    provider = MockDailyProvider()
    provider.set_symbol_bars("UNR_MOCK", make_unr_bullish_mock_bars())
    entries = run_daily_scan(
        symbols=["UNR_MOCK"],
        provider=provider,
        setup_id="unr",
        criteria_dir=None,
        as_of_date=date.today(),
    )
    assert len(entries) >= 1
    assert entries[0].symbol == "UNR_MOCK"
    assert entries[0].direction == "long"
    assert entries[0].ma_used in (20, 50, 200)


def test_run_daily_scan_empty_for_no_data():
    provider = MockDailyProvider()
    entries = run_daily_scan(
        symbols=["EMPTY"],
        provider=provider,
        setup_id="unr",
    )
    assert len(entries) == 0


def test_run_daily_scan_skips_insufficient_bars():
    provider = MockDailyProvider()
    provider.set_symbol_bars("FEW", [(100.0, 101.0, 99.0, 100.0)] * 100)
    entries = run_daily_scan(
        symbols=["FEW"],
        provider=provider,
        setup_id="unr",
        min_bars=250,
    )
    assert len(entries) == 0
