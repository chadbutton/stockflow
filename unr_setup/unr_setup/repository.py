"""
Persistence for triggered setups and resolved trades (SQLite).
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from unr_setup.models import Trigger, ResolvedTrade


def _get_conn(path: str):
    return sqlite3.connect(path)


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS triggered_setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setup_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            ma_used INTEGER NOT NULL,
            trigger_time TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_price REAL NOT NULL,
            timeframe TEXT NOT NULL,
            strat_pattern TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS resolved_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            triggered_setup_id INTEGER NOT NULL REFERENCES triggered_setups(id),
            exit_time TEXT NOT NULL,
            exit_price REAL NOT NULL,
            r_multiple REAL NOT NULL,
            outcome TEXT NOT NULL
        );
    """)
    conn.commit()


class TriggerRepository:
    """Save and load triggers; optional resolved trades for scoring."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        conn = _get_conn(db_path)
        init_schema(conn)
        conn.close()

    def _conn(self) -> sqlite3.Connection:
        return _get_conn(self.db_path)

    def save(self, trigger: Trigger) -> int:
        """Persist trigger; returns id."""
        conn = self._conn()
        try:
            cur = conn.execute(
                """INSERT INTO triggered_setups
                   (setup_id, symbol, direction, ma_used, trigger_time, entry_price, stop_price, timeframe, strat_pattern)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                trigger.to_row(),
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            conn.close()

    def get_by_id(self, id: int) -> Optional[Trigger]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT id, setup_id, symbol, direction, ma_used, trigger_time, entry_price, stop_price, timeframe, strat_pattern, created_at FROM triggered_setups WHERE id = ?",
                (id,),
            ).fetchone()
            if not row:
                return None
            return _row_to_trigger(row)
        finally:
            conn.close()

    def list_for_scoring(self, setup_id: str, ma_used: int, direction: str) -> List[Trigger]:
        """All triggers matching (setup_id, ma_used, direction) for score computation."""
        conn = self._conn()
        try:
            rows = conn.execute(
                """SELECT id, setup_id, symbol, direction, ma_used, trigger_time, entry_price, stop_price, timeframe, strat_pattern, created_at
                   FROM triggered_setups WHERE setup_id = ? AND ma_used = ? AND direction = ? ORDER BY trigger_time""",
                (setup_id, ma_used, direction),
            ).fetchall()
            return [_row_to_trigger(r) for r in rows]
        finally:
            conn.close()

    def add_resolved(self, resolved: ResolvedTrade) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO resolved_trades (triggered_setup_id, exit_time, exit_price, r_multiple, outcome)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    resolved.triggered_setup_id,
                    resolved.exit_time.isoformat(),
                    resolved.exit_price,
                    resolved.r_multiple,
                    resolved.outcome,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_resolved_for_trigger_ids(self, trigger_ids: List[int]) -> List[ResolvedTrade]:
        """Load resolved trades for given trigger IDs."""
        if not trigger_ids:
            return []
        conn = self._conn()
        try:
            placeholders = ",".join("?" * len(trigger_ids))
            rows = conn.execute(
                f"SELECT triggered_setup_id, exit_time, exit_price, r_multiple, outcome FROM resolved_trades WHERE triggered_setup_id IN ({placeholders})",
                trigger_ids,
            ).fetchall()
            return [
                ResolvedTrade(
                    triggered_setup_id=r[0],
                    exit_time=datetime.fromisoformat(r[1]),
                    exit_price=r[2],
                    r_multiple=r[3],
                    outcome=r[4],
                )
                for r in rows
            ]
        finally:
            conn.close()


def _row_to_trigger(row) -> Trigger:
    return Trigger(
        id=row[0],
        setup_id=row[1],
        symbol=row[2],
        direction=row[3],
        ma_used=row[4],
        trigger_time=datetime.fromisoformat(row[5]),
        entry_price=row[6],
        stop_price=row[7],
        timeframe=row[8],
        strat_pattern=row[9],
        created_at=datetime.fromisoformat(row[10]) if row[10] else None,
    )
