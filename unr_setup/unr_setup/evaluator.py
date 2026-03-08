"""
UnR evaluator: combine daily context + 65-min Strat reversal (2-1-2, 2-2, 1-2-2, 3-1-2, 1-3); return trigger with entry/stop.

Uses configurable SetupCriteria when provided (setup_id, timeframe, strat_reversal_patterns).
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from unr_setup.models import Trigger
from unr_setup.setup_criteria import SetupCriteria, load_criteria
from unr_setup.strat import DEFAULT_STRAT_REVERSAL_PATTERNS, detect_strat_reversal
from unr_setup.unr_daily import unr_daily_context

OHLC = tuple


@dataclass
class UnREvalResult:
    """Result of evaluating UnR on daily + 65min bars."""

    trigger: Trigger
    ma_used: int
    direction: str


def evaluate_unr(
    daily_bars: List[OHLC],
    bars_65min: List[OHLC],
    symbol: str = "",
    trigger_time: Optional[datetime] = None,
    setup_id: str = "unr",
    timeframe: str = "65min",
    criteria: Optional[SetupCriteria] = None,
    criteria_dir: Optional[Union[str, Path]] = None,
) -> Optional[UnREvalResult]:
    """
    Evaluate UnR: daily context must have at least one (direction, ma_used);
    65-min must show one of the configured Strat reversal patterns in same direction. Return trigger with entry/stop or None.

    If criteria is provided (or criteria_dir to load from), setup_id, timeframe, and
    strat_reversal_patterns (e.g. ["2-1-2", "2-2", "1-2-2", "3-1-2", "1-3"]) are taken from config.
    """
    if criteria is None and criteria_dir is not None:
        loaded = load_criteria(criteria_dir)
        criteria = loaded.get("unr")
    if criteria:
        setup_id = criteria.setup_id
        timeframe = criteria.get_specific("trigger_timeframe", "65min")

    contexts = unr_daily_context(daily_bars, criteria=criteria)
    if not contexts:
        return None

    patterns = (
        criteria.get_specific("strat_reversal_patterns", DEFAULT_STRAT_REVERSAL_PATTERNS)
        if criteria
        else DEFAULT_STRAT_REVERSAL_PATTERNS
    )
    reversal = detect_strat_reversal(bars_65min, patterns=patterns)
    if not reversal:
        return None

    direction, entry_price, stop_price, strat_pattern = reversal

    # Match: daily context must include this direction and we use first matching MA
    for ctx_dir, ma_used in contexts:
        if ctx_dir == direction:
            t = trigger_time or datetime.utcnow()
            trigger = Trigger(
                setup_id=setup_id,
                symbol=symbol,
                direction=direction,
                ma_used=ma_used,
                trigger_time=t,
                entry_price=entry_price,
                stop_price=stop_price,
                timeframe=timeframe,
                strat_pattern=strat_pattern,
            )
            return UnREvalResult(trigger=trigger, ma_used=ma_used, direction=direction)

    return None
