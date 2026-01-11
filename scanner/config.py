"""
Scanner Configuration

All thresholds and settings are configurable via YAML or programmatically.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ScreeningConfig:
    """Value screening thresholds - all configurable"""
    pe_ratio_max: float = 15.0
    pb_ratio_max: float = 1.5
    debt_equity_max: float = 0.5
    current_ratio_min: float = 1.5
    roe_min: float = 0.10
    market_cap_min: float = 500_000_000  # $500M
    # Additional optional filters
    dividend_yield_min: Optional[float] = None
    profit_margin_min: Optional[float] = None
    revenue_growth_min: Optional[float] = None


@dataclass
class NewsConfig:
    """News aggregation settings"""
    sources: List[str] = field(default_factory=lambda: [
        "finnhub", "yahoo_rss", "google_rss", "reddit", "sec_edgar"
    ])
    positive_keywords: List[str] = field(default_factory=lambda: [
        "earnings beat", "earnings surprise", "upgrade", "upgraded",
        "acquisition", "acquired", "FDA approved", "FDA approval",
        "revenue growth", "new contract", "buyback", "share repurchase",
        "dividend increase", "beat estimates", "raised guidance",
        "strong quarter", "record revenue", "partnership"
    ])
    negative_keywords: List[str] = field(default_factory=lambda: [
        "lawsuit", "sued", "downgrade", "downgraded",
        "missed estimates", "bankruptcy", "chapter 11",
        "SEC investigation", "fraud", "scandal",
        "layoffs", "restructuring", "profit warning",
        "guidance cut", "weak quarter", "disappointing"
    ])
    # Scoring weights
    positive_weight: int = 3
    negative_weight: int = -3
    news_lookback_hours: int = 72  # Look at last 72 hours of news


@dataclass
class AnalysisConfig:
    """AI analysis settings"""
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434/v1"
    parallel_instances: int = 4
    max_stocks_to_analyze: int = 20
    analysis_timeout_seconds: int = 120


@dataclass
class AlertConfig:
    """Alert delivery settings"""
    dashboard: bool = True
    email_enabled: bool = False
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""  # Use app password for Gmail
    email_recipients: List[str] = field(default_factory=list)
    desktop_enabled: bool = True


@dataclass
class WatchlistConfig:
    """Stock watchlist settings"""
    source: str = "sp500"  # sp500, nasdaq100, custom
    custom_symbols: List[str] = field(default_factory=list)


@dataclass
class ScannerConfig:
    """Main scanner configuration"""
    screening: ScreeningConfig = field(default_factory=ScreeningConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    watchlist: WatchlistConfig = field(default_factory=WatchlistConfig)
    polling_interval_minutes: int = 15

    def to_dict(self) -> Dict:
        """Convert config to dictionary"""
        return {
            "screening": {
                "pe_ratio_max": self.screening.pe_ratio_max,
                "pb_ratio_max": self.screening.pb_ratio_max,
                "debt_equity_max": self.screening.debt_equity_max,
                "current_ratio_min": self.screening.current_ratio_min,
                "roe_min": self.screening.roe_min,
                "market_cap_min": self.screening.market_cap_min,
                "dividend_yield_min": self.screening.dividend_yield_min,
                "profit_margin_min": self.screening.profit_margin_min,
                "revenue_growth_min": self.screening.revenue_growth_min,
            },
            "news": {
                "sources": self.news.sources,
                "positive_keywords": self.news.positive_keywords,
                "negative_keywords": self.news.negative_keywords,
                "positive_weight": self.news.positive_weight,
                "negative_weight": self.news.negative_weight,
                "news_lookback_hours": self.news.news_lookback_hours,
            },
            "analysis": {
                "ollama_model": self.analysis.ollama_model,
                "ollama_base_url": self.analysis.ollama_base_url,
                "parallel_instances": self.analysis.parallel_instances,
                "max_stocks_to_analyze": self.analysis.max_stocks_to_analyze,
                "analysis_timeout_seconds": self.analysis.analysis_timeout_seconds,
            },
            "alerts": {
                "dashboard": self.alerts.dashboard,
                "email_enabled": self.alerts.email_enabled,
                "email_smtp_server": self.alerts.email_smtp_server,
                "email_smtp_port": self.alerts.email_smtp_port,
                "email_sender": self.alerts.email_sender,
                "email_recipients": self.alerts.email_recipients,
                "desktop_enabled": self.alerts.desktop_enabled,
            },
            "watchlist": {
                "source": self.watchlist.source,
                "custom_symbols": self.watchlist.custom_symbols,
            },
            "polling_interval_minutes": self.polling_interval_minutes,
        }

    def save(self, path: str):
        """Save config to YAML file"""
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    @classmethod
    def from_dict(cls, data: Dict) -> "ScannerConfig":
        """Create config from dictionary"""
        config = cls()

        if "screening" in data:
            s = data["screening"]
            config.screening = ScreeningConfig(
                pe_ratio_max=s.get("pe_ratio_max", 15.0),
                pb_ratio_max=s.get("pb_ratio_max", 1.5),
                debt_equity_max=s.get("debt_equity_max", 0.5),
                current_ratio_min=s.get("current_ratio_min", 1.5),
                roe_min=s.get("roe_min", 0.10),
                market_cap_min=s.get("market_cap_min", 500_000_000),
                dividend_yield_min=s.get("dividend_yield_min"),
                profit_margin_min=s.get("profit_margin_min"),
                revenue_growth_min=s.get("revenue_growth_min"),
            )

        if "news" in data:
            n = data["news"]
            config.news = NewsConfig(
                sources=n.get("sources", config.news.sources),
                positive_keywords=n.get("positive_keywords", config.news.positive_keywords),
                negative_keywords=n.get("negative_keywords", config.news.negative_keywords),
                positive_weight=n.get("positive_weight", 3),
                negative_weight=n.get("negative_weight", -3),
                news_lookback_hours=n.get("news_lookback_hours", 72),
            )

        if "analysis" in data:
            a = data["analysis"]
            config.analysis = AnalysisConfig(
                ollama_model=a.get("ollama_model", "llama3.2"),
                ollama_base_url=a.get("ollama_base_url", "http://localhost:11434/v1"),
                parallel_instances=a.get("parallel_instances", 4),
                max_stocks_to_analyze=a.get("max_stocks_to_analyze", 20),
                analysis_timeout_seconds=a.get("analysis_timeout_seconds", 120),
            )

        if "alerts" in data:
            al = data["alerts"]
            config.alerts = AlertConfig(
                dashboard=al.get("dashboard", True),
                email_enabled=al.get("email_enabled", False),
                email_smtp_server=al.get("email_smtp_server", "smtp.gmail.com"),
                email_smtp_port=al.get("email_smtp_port", 587),
                email_sender=al.get("email_sender", ""),
                email_password=al.get("email_password", ""),
                email_recipients=al.get("email_recipients", []),
                desktop_enabled=al.get("desktop_enabled", True),
            )

        if "watchlist" in data:
            w = data["watchlist"]
            config.watchlist = WatchlistConfig(
                source=w.get("source", "sp500"),
                custom_symbols=w.get("custom_symbols", []),
            )

        config.polling_interval_minutes = data.get("polling_interval_minutes", 15)

        return config


def load_config(path: str = None) -> ScannerConfig:
    """Load config from YAML file or return defaults"""
    if path is None:
        # Default path
        path = os.path.join(os.path.dirname(__file__), "scanner_config.yaml")

    if os.path.exists(path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
            return ScannerConfig.from_dict(data)

    return ScannerConfig()


def get_sp500_symbols() -> List[str]:
    """Fetch S&P 500 symbols"""
    try:
        import pandas as pd
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        return df['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception as e:
        print(f"Failed to fetch S&P 500 list: {e}")
        # Fallback to a static list of major stocks
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
            "UNH", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
            "PEP", "KO", "COST", "TMO", "WMT", "MCD", "DIS", "CSCO", "ACN",
            "ABT", "DHR", "VZ", "ADBE", "CRM", "NKE", "NFLX", "INTC", "AMD"
        ]


def get_nasdaq100_symbols() -> List[str]:
    """Fetch NASDAQ 100 symbols"""
    try:
        import pandas as pd
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        for table in tables:
            if 'Ticker' in table.columns:
                return table['Ticker'].tolist()
            if 'Symbol' in table.columns:
                return table['Symbol'].tolist()
    except Exception as e:
        print(f"Failed to fetch NASDAQ 100 list: {e}")

    # Fallback
    return get_sp500_symbols()[:100]


def get_watchlist(config: ScannerConfig) -> List[str]:
    """Get stock symbols based on watchlist config"""
    source = config.watchlist.source.lower()

    if source == "custom":
        return config.watchlist.custom_symbols
    elif source == "nasdaq100":
        return get_nasdaq100_symbols()
    else:  # default to sp500
        return get_sp500_symbols()
