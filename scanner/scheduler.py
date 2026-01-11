"""
Scanner Scheduler - Automated polling every 15-30 minutes
"""

import time
from datetime import datetime
from typing import List, Optional

from .config import ScannerConfig, get_watchlist
from .screener import ValueScreener
from .news_aggregator import NewsAggregator
from .parallel_analyzer import ParallelAnalyzer, AnalysisResult
from .alerts import AlertManager


class ScannerScheduler:
    """Orchestrates the full scanning pipeline"""

    def __init__(self, config: ScannerConfig):
        self.config = config
        self.screener = ValueScreener(config)
        self.news_aggregator = NewsAggregator(config)
        self.analyzer = ParallelAnalyzer(config)
        self.alert_manager = AlertManager(config)
        self.last_results: List[AnalysisResult] = []

    def run_scan(self, symbols: List[str] = None) -> List[AnalysisResult]:
        """Run complete scanning pipeline"""
        start_time = time.time()

        print(f"\n{'#'*60}")
        print(f"STOCK SCANNER STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*60}")

        # Get symbols if not provided
        if symbols is None:
            symbols = get_watchlist(self.config)
        print(f"Scanning {len(symbols)} stocks...\n")

        # Stage 1: Fast value screening
        screened = self.screener.screen(symbols)
        if not screened:
            print("No stocks passed value screening")
            return []

        # Stage 2: News filtering
        candidates = self.news_aggregator.get_top_candidates(
            screened,
            top_n=self.config.analysis.max_stocks_to_analyze
        )
        if not candidates:
            print("No stocks with positive news catalyst")
            return []

        # Stage 3: AI analysis
        results = self.analyzer.analyze_batch(candidates)

        # Send alerts
        self.alert_manager.send_alerts(results)

        # Store results
        self.last_results = results

        elapsed = time.time() - start_time
        print(f"\n{'#'*60}")
        print(f"SCAN COMPLETE in {elapsed:.1f}s")
        print(f"{'#'*60}\n")

        # Print summary
        print(self.analyzer.format_results(results))

        return results

    def run_scheduled(self):
        """Run scanner on schedule (blocking)"""
        interval = self.config.polling_interval_minutes * 60

        print(f"Starting scheduled scanner (every {self.config.polling_interval_minutes} min)")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                self.run_scan()
                print(f"\nNext scan in {self.config.polling_interval_minutes} minutes...")
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\nScanner stopped")
                break
            except Exception as e:
                print(f"Scan error: {e}")
                print(f"Retrying in {self.config.polling_interval_minutes} minutes...")
                time.sleep(interval)

    def get_last_results(self) -> List[AnalysisResult]:
        """Get results from last scan"""
        return self.last_results


def run_once(config: ScannerConfig = None, symbols: List[str] = None) -> List[AnalysisResult]:
    """Convenience function for single scan"""
    if config is None:
        config = ScannerConfig()
    scheduler = ScannerScheduler(config)
    return scheduler.run_scan(symbols)
