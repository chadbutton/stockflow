"""Unit tests for score 0-100 from historical triggers + resolved trades."""

from datetime import datetime

import pytest
from unr_setup.models import Trigger, ResolvedTrade
from unr_setup.repository import TriggerRepository
from unr_setup.scoring import compute_score, MIN_SAMPLES_FOR_SCORE, NEUTRAL_SCORE


def test_score_insufficient_samples_returns_neutral():
    repo = TriggerRepository(":memory:")
    now = datetime.utcnow()
    for i in range(3):
        repo.save(Trigger("unr", "AAPL", "long", 20, now, 100.0, 98.0, "65min", "2-1-2"))
    triggers = repo.list_for_scoring("unr", 20, "long")
    ids = [t.id for t in triggers if t.id]
    for tid in ids[:2]:
        repo.add_resolved(ResolvedTrade(tid, now, 102.0, 1.0, "win"))
    score = compute_score(repo, "unr", 20, "long", min_samples=5)
    assert score == NEUTRAL_SCORE


def test_score_all_wins_high():
    repo = TriggerRepository(":memory:")
    now = datetime.utcnow()
    for _ in range(10):
        tid = repo.save(Trigger("unr", "AAPL", "long", 20, now, 100.0, 98.0, "65min", "2-1-2"))
        repo.add_resolved(ResolvedTrade(tid, now, 104.0, 2.0, "win"))
    score = compute_score(repo, "unr", 20, "long", min_samples=5)
    assert score >= 70
    assert 0 <= score <= 100


def test_score_all_losses_low():
    repo = TriggerRepository(":memory:")
    now = datetime.utcnow()
    for _ in range(10):
        tid = repo.save(Trigger("unr", "AAPL", "short", 50, now, 100.0, 102.0, "65min", "2-1-2"))
        repo.add_resolved(ResolvedTrade(tid, now, 102.0, -1.0, "loss"))
    score = compute_score(repo, "unr", 50, "short", min_samples=5)
    assert score <= 50
    assert 0 <= score <= 100


def test_score_mixed_pull_toward_neutral():
    repo = TriggerRepository(":memory:")
    now = datetime.utcnow()
    for i in range(10):
        tid = repo.save(Trigger("unr", "AAPL", "long", 200, now, 100.0, 98.0, "65min", "2-1-2"))
        outcome = "win" if i % 2 == 0 else "loss"
        repo.add_resolved(ResolvedTrade(tid, now, 101.0 if outcome == "win" else 97.0, 0.5 if outcome == "win" else -0.5, outcome))
    score = compute_score(repo, "unr", 200, "long", min_samples=5)
    assert 30 <= score <= 70
    assert 0 <= score <= 100
