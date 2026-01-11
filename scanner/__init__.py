"""
Stock Scanner Module

Automated stock scanning system using hybrid approach:
1. Fast value screening (1000s → 100)
2. News filtering (100 → 20)
3. AI deep analysis (20 → top picks)
"""

from .config import ScannerConfig, load_config
from .screener import ValueScreener
from .news_aggregator import NewsAggregator
from .parallel_analyzer import ParallelAnalyzer
from .alerts import AlertManager
from .scheduler import ScannerScheduler

__all__ = [
    "ScannerConfig",
    "load_config",
    "ValueScreener",
    "NewsAggregator",
    "ParallelAnalyzer",
    "AlertManager",
    "ScannerScheduler",
]
