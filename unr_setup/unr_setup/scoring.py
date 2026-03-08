"""
Score 0-100 from historical triggers + resolved trades (same pattern = same setup_id, ma_used, direction).
"""

from typing import List, Optional

from unr_setup.models import Trigger, ResolvedTrade
from unr_setup.repository import TriggerRepository

MIN_SAMPLES_FOR_SCORE = 5
NEUTRAL_SCORE = 50


def compute_score(
    repo: TriggerRepository,
    setup_id: str,
    ma_used: int,
    direction: str,
    min_samples: int = MIN_SAMPLES_FOR_SCORE,
    neutral: int = NEUTRAL_SCORE,
) -> Optional[int]:
    """
    Compute score 0-100 for the pattern (setup_id, ma_used, direction).
    Uses resolved_trades linked to those triggers: win rate and average R.
    If no resolved trades or sample size < min_samples, return neutral (50) or None (caller can treat as N/A).
    """
    triggers = repo.list_for_scoring(setup_id, ma_used, direction)
    if not triggers:
        return neutral

    trigger_ids = [t.id for t in triggers if t.id is not None]
    resolved = repo.get_resolved_for_trigger_ids(trigger_ids)

    if len(resolved) < min_samples:
        return neutral

    wins = sum(1 for r in resolved if r.outcome == "win")
    win_rate = wins / len(resolved)
    avg_r = sum(r.r_multiple for r in resolved) / len(resolved)

    # Score: blend win rate (0-100) with avg R (e.g. cap at 2R = 100)
    base = win_rate * 100
    r_component = min(100, avg_r * 50)  # 2R avg -> 100
    score = (base * 0.6 + r_component * 0.4)
    # Optional: pull toward 50 when sample size is small
    if len(resolved) < 20:
        weight_prior = 1.0 - len(resolved) / 20.0
        score = score * (1 - weight_prior) + neutral * weight_prior
    return max(0, min(100, int(round(score))))
