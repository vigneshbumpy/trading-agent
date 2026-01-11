#!/usr/bin/env python3
"""
Stock Scanner - Run from command line

Usage:
    python -m scanner.run_scanner              # Single scan with defaults
    python -m scanner.run_scanner --scheduled  # Run on schedule
    python -m scanner.run_scanner --symbols AAPL MSFT GOOGL  # Custom symbols
"""

import argparse
from .config import ScannerConfig, load_config
from .scheduler import ScannerScheduler, run_once


def main():
    parser = argparse.ArgumentParser(description="Stock Scanner")
    parser.add_argument("--config", help="Path to config YAML file")
    parser.add_argument("--scheduled", action="store_true", help="Run on schedule")
    parser.add_argument("--interval", type=int, help="Polling interval in minutes")
    parser.add_argument("--symbols", nargs="+", help="Stock symbols to scan")
    parser.add_argument("--top", type=int, default=20, help="Max stocks for AI analysis")

    args = parser.parse_args()

    # Load config
    config = load_config(args.config) if args.config else ScannerConfig()

    # Override with CLI args
    if args.interval:
        config.polling_interval_minutes = args.interval
    if args.top:
        config.analysis.max_stocks_to_analyze = args.top

    # Run
    scheduler = ScannerScheduler(config)

    if args.scheduled:
        scheduler.run_scheduled()
    else:
        results = scheduler.run_scan(args.symbols)

        # Print BUY signals prominently
        buys = [r for r in results if r.signal == 'BUY']
        if buys:
            print("\n" + "="*60)
            print("TOP BUY RECOMMENDATIONS:")
            print("="*60)
            for r in buys:
                print(f"\n{r.symbol} - {r.confidence:.0f}% confidence")
                print(f"  Action: {r.action_recommendation}")
                print(f"  Value:  {r.value_analysis}")
                print(f"  News:   {r.news_analysis}")
                print(f"  Risk:   {r.risk_assessment}")


if __name__ == "__main__":
    main()
