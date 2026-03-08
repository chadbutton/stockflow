"""Unit tests for configurable setup criteria loading."""

import json
from pathlib import Path

import pytest
from unr_setup.setup_criteria import (
    SetupCriteria,
    load_criteria,
    get_criteria,
    _load_file,
)


def test_setup_criteria_from_dict():
    d = {
        "setup_id": "test",
        "name": "Test Setup",
        "version": "1.0",
        "timeframes": ["15m"],
        "entry": {"type": "breakout_above"},
        "stop": {"type": "swing_low"},
        "setup_specific": {"ema_period": 20},
    }
    c = SetupCriteria.from_dict(d)
    assert c.setup_id == "test"
    assert c.name == "Test Setup"
    assert c.get_specific("ema_period") == 20
    assert c.get_specific("missing", 99) == 99


def test_load_criteria_from_json_file(tmp_path):
    path = tmp_path / "unr.json"
    path.write_text(json.dumps({
        "setup_id": "unr",
        "name": "UnR",
        "setup_specific": {"daily_emas": [20, 50, 200]},
    }), encoding="utf-8")
    result = load_criteria(path)
    assert "unr" in result
    assert result["unr"].setup_id == "unr"
    assert result["unr"].get_specific("daily_emas") == [20, 50, 200]


def test_load_criteria_from_directory(tmp_path):
    (tmp_path / "unr.json").write_text(json.dumps({"setup_id": "unr", "name": "UnR"}), encoding="utf-8")
    (tmp_path / "other.json").write_text(json.dumps({"setup_id": "other", "name": "Other"}), encoding="utf-8")
    result = load_criteria(tmp_path)
    assert len(result) == 2
    assert result["unr"].setup_id == "unr"
    assert result["other"].setup_id == "other"


def test_load_criteria_nonexistent_returns_empty():
    result = load_criteria(Path("/nonexistent/path/12345"))
    assert result == {}


def test_get_criteria_uses_cache():
    cache = {}
    one = get_criteria(criteria_dir=None, cache=cache, env_key="SETUP_CRITERIA_DIR")
    assert one == {}
    cache["unr"] = SetupCriteria.from_dict({"setup_id": "unr", "name": "UnR"})
    two = get_criteria(criteria_dir=None, cache=cache)
    assert two == cache
    assert two["unr"].setup_id == "unr"
