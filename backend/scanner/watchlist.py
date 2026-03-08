"""Watchlist model and persistence (JSON)."""

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import List


@dataclass
class WatchlistEntry:
    """One symbol that meets daily criteria for a setup."""

    symbol: str
    setup_id: str
    direction: str  # "long" | "short"
    ma_used: int  # 20 | 50 | 200 for UnR
    as_of_date: str  # YYYY-MM-DD
    price: float | None = None  # close on as_of_date
    ema_20: float | None = None  # 20-period EMA
    ma_50: float | None = None   # 50-period SMA
    ma_200: float | None = None  # 200-period SMA
    atr: float | None = None     # 14-period ATR (Wilder's) on as_of_date

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WatchlistEntry":
        return cls(
            symbol=d["symbol"],
            setup_id=d["setup_id"],
            direction=d["direction"],
            ma_used=d["ma_used"],
            as_of_date=d["as_of_date"],
            price=d.get("price"),
            ema_20=d.get("ema_20") or d.get("ma_20"),  # backward compat
            ma_50=d.get("ma_50"),
            ma_200=d.get("ma_200"),
            atr=d.get("atr"),
        )


def save_watchlist(entries: List[WatchlistEntry], path: str | Path) -> None:
    import json
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "as_of_date": entries[0].as_of_date if entries else "",
        "setup_id": entries[0].setup_id if entries else "",
        "entries": [e.to_dict() for e in entries],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_watchlist(path: str | Path) -> List[WatchlistEntry]:
    import json
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [WatchlistEntry.from_dict(e) for e in data.get("entries", [])]
