"""Tests for watchlist save/load."""

import tempfile
from pathlib import Path

from scanner.watchlist import WatchlistEntry, load_watchlist, save_watchlist


def test_save_and_load_watchlist():
    entries = [
        WatchlistEntry("AAPL", "unr", "long", 20, "2025-03-08"),
        WatchlistEntry("MSFT", "unr", "long", 50, "2025-03-08"),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = Path(f.name)
    try:
        save_watchlist(entries, path)
        loaded = load_watchlist(path)
        assert len(loaded) == 2
        assert loaded[0].symbol == "AAPL"
        assert loaded[1].ma_used == 50
    finally:
        path.unlink(missing_ok=True)


def test_load_empty_missing_file():
    assert load_watchlist(Path("/nonexistent/file.json")) == []
