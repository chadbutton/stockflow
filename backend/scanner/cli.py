"""
CLI: run daily scan and output watchlist (stdout + optional file).
"""

import argparse
from datetime import date
from pathlib import Path

from scanner.data_provider import MockDailyProvider, make_unr_bullish_mock_bars
from scanner.daily_scan import run_daily_scan
from scanner.watchlist import save_watchlist


def load_universe(path: Path) -> list[str]:
    """Load symbols: one per line, skip empty and # comments."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [s.strip() for s in lines if s.strip() and not s.strip().startswith("#")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily scan: find symbols that meet setup criteria (watchlist).")
    parser.add_argument(
        "--universe",
        type=Path,
        default=Path("config/universe_liquid_us.txt"),
        help="Path to file with one symbol per line (default: liquid US, >40M cap, PLTR/TSLA/GOOG/MSFT etc.)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write watchlist JSON here",
    )
    parser.add_argument(
        "--setup",
        default="unr",
        help="Setup id (e.g. unr)",
    )
    parser.add_argument(
        "--criteria-dir",
        type=Path,
        default=None,
        help="Directory or file with setup criteria YAML/JSON (default: unr_setup/config/setups)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data (one symbol UNR_MOCK with synthetic UnR bullish bars)",
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=None,
        help="Load daily bars from CSV files (one SYMBOL.csv per symbol; columns: date,open,high,low,close)",
    )
    parser.add_argument(
        "--yahoo",
        action="store_true",
        help="Fetch daily bars from Yahoo Finance (yfinance). Use with --as-of for Friday scan.",
    )
    parser.add_argument(
        "--unadjusted",
        action="store_true",
        help="Use unadjusted OHLC from Yahoo (default: adjusted). Use to match TradingView when it shows raw prices.",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Date YYYY-MM-DD (e.g. 2025-03-07 for Friday). Default: today.",
    )
    args = parser.parse_args()

    if args.mock:
        provider = MockDailyProvider()
        provider.set_symbol_bars("UNR_MOCK", make_unr_bullish_mock_bars())
        symbols = ["UNR_MOCK"]
    else:
        symbols = load_universe(args.universe)
        if not symbols:
            print("No symbols in universe. Use --universe <file> or --mock for demo.")
            return
        if args.yahoo:
            from scanner.data_provider import YahooDailyProvider
            provider = YahooDailyProvider(adjusted=not args.unadjusted)
        elif args.csv_dir and args.csv_dir.exists():
            from scanner.data_provider import CsvDailyProvider
            provider = CsvDailyProvider(args.csv_dir)
        else:
            provider = MockDailyProvider()
            print("No data source. Use --yahoo to fetch from Yahoo, --csv-dir <path>, or --mock for demo.")

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    criteria_dir_resolved = str(args.criteria_dir) if args.criteria_dir else None
    if not criteria_dir_resolved:
        root = Path(__file__).resolve().parent.parent.parent
        default_criteria = root / "unr_setup" / "config" / "setups"
        if default_criteria.exists():
            criteria_dir_resolved = str(default_criteria)

    entries = run_daily_scan(
        symbols=symbols,
        provider=provider,
        setup_id=args.setup,
        criteria_dir=criteria_dir_resolved,
        as_of_date=as_of,
    )

    print(f"Watchlist ({args.setup}) as of {as_of}: {len(entries)} symbols")
    for e in entries:
        print(f"  {e.symbol}  {e.direction}  MA{e.ma_used}")
    if args.output:
        save_watchlist(entries, args.output)
        print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
