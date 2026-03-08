"""
Debug why PLTR (or one symbol) doesn't match UnR daily. Run from backend/: python scripts/debug_unr_pltr.py [SYMBOL] [AS_OF]
"""
import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scanner.data_provider import YahooDailyProvider
from unr_setup.unr_daily import (
    compute_emas,
    unr_daily_context,
)
from unr_setup.setup_criteria import load_criteria

def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "PLTR"
    as_of = sys.argv[2] if len(sys.argv) > 2 else "2025-03-07"
    if len(as_of) == 10:
        as_of_date = date.fromisoformat(as_of)
    else:
        as_of_date = date.today()

    root = Path(__file__).resolve().parent.parent.parent
    criteria_path = root / "unr_setup" / "config" / "setups"
    loaded = load_criteria(str(criteria_path)) if criteria_path.exists() else {}
    criteria = loaded.get("unr")

    provider = YahooDailyProvider()
    calendar_days = int(250 * (365 / 252)) + 60
    start = as_of_date - timedelta(days=calendar_days)
    end = as_of_date
    bars = provider.get_daily_bars(symbol, start, end)

    print(f"Symbol: {symbol}  As-of: {as_of_date}")
    print(f"Bars: {len(bars)}  (need 200+ for 200 EMA)")
    if not bars:
        print("No data from Yahoo. Check symbol and date.")
        return
    last_bar = bars[-1]
    print(f"Last bar: O={last_bar[0]:.2f} H={last_bar[1]:.2f} L={last_bar[2]:.2f} C={last_bar[3]:.2f}")

    closes = [b[3] for b in bars]
    highs = [b[1] for b in bars]
    lows = [b[2] for b in bars]
    idx = len(closes) - 1
    ema_periods = (20, 50, 200) if criteria is None else tuple(criteria.get_specific("daily_emas", [20, 50, 200]))
    emas = compute_emas(closes, ema_periods)

    print("\nPer MA:")
    for p in ema_periods:
        ema_vals = emas.get(p)
        if not ema_vals or idx >= len(ema_vals):
            print(f"  MA{p}: no data")
            continue
        ema_last = ema_vals[idx]
        # slope (need idx - 5 valid for 200 EMA)
        slope_ok = idx >= 5 and ema_vals[idx] > ema_vals[idx - 5] if (idx - 5 < len(ema_vals)) else False
        if p == 200 and idx < 204:
            slope_ok = False  # 200 EMA needs 205+ bars for slope (ema_vals[idx-5] valid)
        # price falling 3-5 days
        fall_ok = any(idx >= n and closes[idx] < closes[idx - n] for n in range(3, 6))
        # undercut then back above: in last 5 days low < MA and current close > MA
        window_start = max(0, idx - 4)
        undercut_any = any(lows[i] < ema_vals[i] for i in range(window_start, idx + 1))
        close_above = closes[idx] > ema_last
        undercut_ok = undercut_any and close_above
        print(f"  MA{p}: EMA={ema_last:.2f}  close>EMA={close_above}  slope_5d_up={slope_ok}  price_fall_3_5d={fall_ok}  undercut_then_above={undercut_ok}")

    result = unr_daily_context(bars, criteria=criteria)
    print(f"\nunr_daily_context result: {result}")
    if not result:
        print("No match. Fix: ensure last bar date is correct (Yahoo end=exclusive, we now add 1 day), and that close > EMA on last bar with prior undercut and 3-5 day pullback.")


if __name__ == "__main__":
    main()
