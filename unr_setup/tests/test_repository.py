"""Unit tests for trigger and resolved-trade persistence."""

from datetime import datetime

import pytest
from unr_setup.models import Trigger, ResolvedTrade
from unr_setup.repository import TriggerRepository


def test_save_and_get_trigger():
    repo = TriggerRepository(":memory:")
    t = Trigger(
        setup_id="unr",
        symbol="AAPL",
        direction="long",
        ma_used=20,
        trigger_time=datetime.utcnow(),
        entry_price=150.0,
        stop_price=148.0,
        timeframe="65min",
        strat_pattern="2-1-2",
    )
    id = repo.save(t)
    assert id > 0
    loaded = repo.get_by_id(id)
    assert loaded is not None
    assert loaded.symbol == "AAPL"
    assert loaded.entry_price == 150.0
    assert loaded.ma_used == 20


def test_list_for_scoring():
    repo = TriggerRepository(":memory:")
    now = datetime.utcnow()
    for sym, ma in [("AAPL", 20), ("MSFT", 20), ("GOOG", 50)]:
        repo.save(Trigger("unr", sym, "long", ma, now, 100.0, 98.0, "65min", "2-1-2"))
    list_20 = repo.list_for_scoring("unr", 20, "long")
    list_50 = repo.list_for_scoring("unr", 50, "long")
    assert len(list_20) == 2
    assert len(list_50) == 1
    assert list_50[0].symbol == "GOOG"


def test_add_resolved_and_get():
    repo = TriggerRepository(":memory:")
    id = repo.save(Trigger("unr", "AAPL", "long", 20, datetime.utcnow(), 150.0, 148.0, "65min", "2-1-2"))
    repo.add_resolved(ResolvedTrade(id, datetime.utcnow(), 154.0, 2.0, "win"))
    resolved = repo.get_resolved_for_trigger_ids([id])
    assert len(resolved) == 1
    assert resolved[0].outcome == "win"
    assert resolved[0].r_multiple == 2.0
