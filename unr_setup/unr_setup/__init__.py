"""
UnR (Undercut and Run) setup: daily EMA context + 65min Strat 2-1-2 trigger.
Setup criteria are configurable (YAML/JSON) and shared by any setup.
"""

from unr_setup.strat import (
    BarType,
    classify_bar,
    is_212_reversal,
    is_22_reversal,
    is_122_reversal,
    is_312_reversal,
    is_13_reversal,
    detect_strat_reversal,
    DEFAULT_STRAT_REVERSAL_PATTERNS,
)
from unr_setup.unr_daily import compute_emas, unr_daily_context
from unr_setup.models import Trigger
from unr_setup.evaluator import evaluate_unr, UnREvalResult
from unr_setup.repository import TriggerRepository
from unr_setup.scoring import compute_score
from unr_setup.setup_criteria import SetupCriteria, load_criteria, get_criteria

__all__ = [
    "BarType",
    "classify_bar",
    "is_212_reversal",
    "is_22_reversal",
    "is_122_reversal",
    "is_312_reversal",
    "is_13_reversal",
    "detect_strat_reversal",
    "DEFAULT_STRAT_REVERSAL_PATTERNS",
    "compute_emas",
    "unr_daily_context",
    "Trigger",
    "evaluate_unr",
    "UnREvalResult",
    "TriggerRepository",
    "compute_score",
    "SetupCriteria",
    "load_criteria",
    "get_criteria",
]
