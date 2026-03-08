"""Data models for UnR triggers and resolved trades."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Trigger:
    """A single UnR setup trigger (persisted for scoring)."""

    setup_id: str
    symbol: str
    direction: str  # "long" | "short"
    ma_used: int  # 20 | 50 | 200
    trigger_time: datetime
    entry_price: float
    stop_price: float
    timeframe: str
    strat_pattern: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_row(self) -> tuple:
        return (
            self.setup_id,
            self.symbol,
            self.direction,
            self.ma_used,
            self.trigger_time.isoformat(),
            self.entry_price,
            self.stop_price,
            self.timeframe,
            self.strat_pattern,
        )


@dataclass
class ResolvedTrade:
    """Outcome of a triggered setup (for scoring)."""

    triggered_setup_id: int
    exit_time: datetime
    exit_price: float
    r_multiple: float
    outcome: str  # "win" | "loss" | "breakeven"
