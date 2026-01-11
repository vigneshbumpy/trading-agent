"""
News Aggregator (Stage 2)

Aggregates news from multiple free sources and scores stocks based on
keyword sentiment analysis (no LLM needed for speed).
"""

import os
import re
import time
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .config import ScannerConfig, NewsConfig
from .screener import ScreenedStock


@dataclass
class NewsItem:
    """Single news article"""
    title: str
    summary: str
    source: str
    url: str
    published: Optional[datetime]
    symbols: List[str] = field(default_factory=list)


@dataclass
class StockNews:
    """News data for a single stock"""
    symbol: str
    news_items: List[NewsItem] = field(default_factory=list)
    news_score: float = 0.0
    positive_count: int = 0
    negative_count: int = 0
    total_news: int = 0


class NewsAggregator:
    """Aggregates news from multiple free sources"""

    def __init__(self, config: ScannerConfig):
        self.config = config
        self.news_config = config.news

        # Compile regex patterns for keywords
        self.positive_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in self.news_config.positive_keywords
        ]
        self.negative_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in self.news_config.negative_keywords
        ]

    def fetch_yahoo_rss(self, symbol: str) -> List[NewsItem]:
        """Fetch news from Yahoo Finance RSS"""
        items = []
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            feed = feedparser.parse(url)

            for entry in feed.entries[:10]:  # Limit to 10 items
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                items.append(NewsItem(
                    title=entry.get('title', ''),
                    summary=entry.get('summary', ''),
                    source='Yahoo Finance',
                    url=entry.get('link', ''),
                    published=published,
                    symbols=[symbol],
                ))
        except Exception as e:
            pass  # Silent fail

        return items

    def fetch_google_rss(self, symbol: str) -> List[NewsItem]:
        """Fetch news from Google News RSS"""
        items = []
        try:
            # Google News RSS for stock symbol
            url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)

            for entry in feed.entries[:10]:
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                items.append(NewsItem(
                    title=entry.get('title', ''),
                    summary=entry.get('summary', ''),
                    source='Google News',
                    url=entry.get('link', ''),
                    published=published,
                    symbols=[symbol],
                ))
        except Exception as e:
            pass

        return items

    def fetch_finnhub(self, symbol: str) -> List[NewsItem]:
        """Fetch news from Finnhub (free tier: 60 requests/min)"""
        items = []
        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            return items

        try:
            # Get news from last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            url = f"https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': symbol,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'token': api_key
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for article in data[:10]:
                    published = None
                    if article.get('datetime'):
                        published = datetime.fromtimestamp(article['datetime'])

                    items.append(NewsItem(
                        title=article.get('headline', ''),
                        summary=article.get('summary', ''),
                        source='Finnhub',
                        url=article.get('url', ''),
                        published=published,
                        symbols=[symbol],
                    ))
        except Exception as e:
            pass

        return items

    def fetch_sec_filings(self, symbol: str) -> List[NewsItem]:
        """Fetch recent SEC filings (8-K, 10-Q, etc.)"""
        items = []
        try:
            # SEC EDGAR RSS feed
            url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={symbol}&type=8-K&dateb=&owner=include&count=10&output=atom"
            feed = feedparser.parse(url)

            for entry in feed.entries[:5]:
                published = None
                if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])

                items.append(NewsItem(
                    title=f"SEC Filing: {entry.get('title', '')}",
                    summary=entry.get('summary', ''),
                    source='SEC EDGAR',
                    url=entry.get('link', ''),
                    published=published,
                    symbols=[symbol],
                ))
        except Exception as e:
            pass

        return items

    def fetch_reddit(self, symbol: str) -> List[NewsItem]:
        """Fetch mentions from Reddit (r/stocks, r/wallstreetbets)"""
        items = []
        try:
            subreddits = ['stocks', 'wallstreetbets', 'investing']
            headers = {'User-Agent': 'TradingAgent/1.0'}

            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/search.json?q={symbol}&restrict_sr=1&sort=new&limit=5"
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    for post in data.get('data', {}).get('children', []):
                        post_data = post.get('data', {})
                        published = None
                        if post_data.get('created_utc'):
                            published = datetime.fromtimestamp(post_data['created_utc'])

                        items.append(NewsItem(
                            title=post_data.get('title', ''),
                            summary=post_data.get('selftext', '')[:500],
                            source=f"Reddit r/{subreddit}",
                            url=f"https://reddit.com{post_data.get('permalink', '')}",
                            published=published,
                            symbols=[symbol],
                        ))

                time.sleep(0.5)  # Rate limit
        except Exception as e:
            pass

        return items

    def fetch_news_for_symbol(self, symbol: str, sources: List[str]) -> StockNews:
        """Fetch news from all configured sources for a symbol"""
        all_news = []

        source_handlers = {
            'yahoo_rss': self.fetch_yahoo_rss,
            'google_rss': self.fetch_google_rss,
            'finnhub': self.fetch_finnhub,
            'sec_edgar': self.fetch_sec_filings,
            'reddit': self.fetch_reddit,
        }

        for source in sources:
            if source in source_handlers:
                try:
                    news = source_handlers[source](symbol)
                    all_news.extend(news)
                except Exception as e:
                    pass

        return StockNews(
            symbol=symbol,
            news_items=all_news,
            total_news=len(all_news),
        )

    def score_text(self, text: str) -> Tuple[int, int]:
        """Score text for positive/negative sentiment using keywords"""
        text_lower = text.lower()
        positive = 0
        negative = 0

        for pattern in self.positive_patterns:
            if pattern.search(text):
                positive += 1

        for pattern in self.negative_patterns:
            if pattern.search(text):
                negative += 1

        return positive, negative

    def score_stock_news(self, stock_news: StockNews) -> StockNews:
        """Calculate news score for a stock"""
        total_positive = 0
        total_negative = 0

        # Filter news by recency
        cutoff = datetime.now() - timedelta(hours=self.news_config.news_lookback_hours)

        for news in stock_news.news_items:
            # Check if news is recent enough
            if news.published and news.published < cutoff:
                continue

            text = f"{news.title} {news.summary}"
            pos, neg = self.score_text(text)
            total_positive += pos
            total_negative += neg

        # Calculate weighted score
        pos_score = total_positive * self.news_config.positive_weight
        neg_score = total_negative * abs(self.news_config.negative_weight)
        stock_news.news_score = pos_score - neg_score
        stock_news.positive_count = total_positive
        stock_news.negative_count = total_negative

        return stock_news

    def aggregate(self, screened_stocks: List[ScreenedStock], max_workers: int = 10) -> List[Tuple[ScreenedStock, StockNews]]:
        """
        Aggregate news for screened stocks and return sorted by combined score.

        Args:
            screened_stocks: List of stocks that passed value screening

        Returns:
            List of (ScreenedStock, StockNews) tuples sorted by combined score
        """
        print(f"\n{'='*60}")
        print(f"STAGE 2: NEWS FILTERING")
        print(f"{'='*60}")
        print(f"Aggregating news for {len(screened_stocks)} stocks...")
        print(f"Sources: {', '.join(self.news_config.sources)}")
        print()

        start_time = time.time()
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_stock = {
                executor.submit(
                    self.fetch_news_for_symbol,
                    stock.symbol,
                    self.news_config.sources
                ): stock
                for stock in screened_stocks
            }

            completed = 0
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                completed += 1

                if completed % 20 == 0:
                    print(f"Progress: {completed}/{len(screened_stocks)} stocks processed")

                try:
                    stock_news = future.result()
                    stock_news = self.score_stock_news(stock_news)
                    results.append((stock, stock_news))
                except Exception as e:
                    results.append((stock, StockNews(symbol=stock.symbol)))

        # Sort by combined score (value score + news score)
        results.sort(
            key=lambda x: x[0].score + x[1].news_score,
            reverse=True
        )

        elapsed = time.time() - start_time
        print(f"\nNews aggregation complete in {elapsed:.1f}s")

        # Count stocks with positive news
        positive_news = sum(1 for _, news in results if news.news_score > 0)
        print(f"Stocks with positive news catalyst: {positive_news}/{len(results)}")
        print(f"{'='*60}\n")

        return results

    def get_top_candidates(
        self,
        screened_stocks: List[ScreenedStock],
        top_n: int = 20
    ) -> List[Tuple[ScreenedStock, StockNews]]:
        """Get top N candidates for deep AI analysis"""
        all_results = self.aggregate(screened_stocks)

        # Filter to stocks with at least some positive news
        candidates = [
            (stock, news) for stock, news in all_results
            if news.news_score >= 0  # At least neutral news
        ]

        return candidates[:top_n]


# Quick test
if __name__ == "__main__":
    from .config import ScannerConfig
    from .screener import ScreenedStock

    config = ScannerConfig()
    aggregator = NewsAggregator(config)

    # Test with a sample stock
    test_stock = ScreenedStock(
        symbol="AAPL",
        pe_ratio=25.0,
        pb_ratio=35.0,
        debt_equity=1.5,
        current_ratio=1.0,
        roe=0.15,
        market_cap=3e12,
        price=175.0,
        dividend_yield=0.005,
        profit_margin=0.25,
        revenue_growth=0.05,
        sector="Technology",
        industry="Consumer Electronics",
        score=60.0,
    )

    results = aggregator.get_top_candidates([test_stock], top_n=5)

    for stock, news in results:
        print(f"\n{stock.symbol}:")
        print(f"  Value Score: {stock.score}")
        print(f"  News Score: {news.news_score}")
        print(f"  News Items: {news.total_news}")
        print(f"  Positive/Negative: {news.positive_count}/{news.negative_count}")
