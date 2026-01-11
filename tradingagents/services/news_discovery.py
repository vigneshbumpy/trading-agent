"""
Real-time News & Stock Discovery Service
Uses web scraping to find trending stocks - NO HARDCODING!
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from tradingagents.services.stock_scraper import StockScraper, create_stock_scraper

logger = logging.getLogger(__name__)


class NewsDiscoveryService:
    """
    Discovers trending stocks from real sources via web scraping
    
    Sources:
    - Yahoo Finance (Trending, Gainers, Most Active)
    - Finviz (Momentum Screener)
    - CoinGecko (Crypto Trending)
    - TradingView (Trading Ideas)
    - Reddit WSB (Social Sentiment)
    - NSE India (Indian Markets)
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.scraper = create_stock_scraper(config)
        
        # Configuration
        self.max_stocks = self.config.get('max_stocks', 15)
        self.include_crypto = self.config.get('include_crypto', True)
        self.include_indian = self.config.get('include_indian', True)
        self.min_confidence = self.config.get('min_confidence', 0.5)
        
        # API keys (optional - for premium sources)
        self.finnhub_key = os.getenv('FINNHUB_API_KEY', '')
        self.alphavantage_key = os.getenv('ALPHA_VANTAGE_API_KEY', '')
        
        # Cache
        self._cache = {}
        self._cache_time = None
        self._cache_duration = timedelta(minutes=5)
        
        logger.info("NewsDiscoveryService initialized with real web scraping")
    
    def discover_trending_stocks(self) -> List[Dict]:
        """
        Discover trending stocks from multiple real sources
        
        Returns:
            List of trending stocks with sentiment and confidence scores
        """
        # Check cache
        if self._cache_time and datetime.now() - self._cache_time < self._cache_duration:
            logger.info("Using cached trending stocks")
            return self._cache.get('trending', [])
        
        logger.info("🔍 Scraping real sources for trending stocks...")
        
        trending = []
        
        try:
            # Get all trending from scraper
            all_trending = self.scraper.get_all_trending()
            
            # Filter based on config
            for stock in all_trending:
                market = stock.get('market', 'US')
                
                # Filter by market
                if market == 'CRYPTO' and not self.include_crypto:
                    continue
                if market == 'INDIA' and not self.include_indian:
                    continue
                
                # Filter by confidence
                if stock.get('confidence', 0) < self.min_confidence:
                    continue
                
                trending.append(stock)
            
            # Add news sentiment if API keys available
            if self.alphavantage_key:
                trending = self._enrich_with_news_sentiment(trending[:10])
            
            logger.info(f"✅ Found {len(trending)} trending stocks from real sources")
            
        except Exception as e:
            logger.error(f"Error discovering stocks: {e}")
            # Fallback to basic scraping
            trending = self._fallback_discovery()
        
        # Cache results
        self._cache['trending'] = trending[:self.max_stocks]
        self._cache_time = datetime.now()
        
        return trending[:self.max_stocks]
    
    def _enrich_with_news_sentiment(self, stocks: List[Dict]) -> List[Dict]:
        """Enrich stocks with news sentiment from Alpha Vantage"""
        import requests
        
        enriched = []
        
        for stock in stocks:
            ticker = stock['ticker'].replace('.NS', '')
            
            try:
                url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={self.alphavantage_key}&limit=5"
                response = requests.get(url, timeout=10)
                data = response.json()
                
                if 'feed' in data and len(data['feed']) > 0:
                    # Calculate average sentiment
                    sentiments = [float(item.get('overall_sentiment_score', 0)) for item in data['feed'][:5]]
                    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
                    
                    # Update stock sentiment (combine with existing)
                    existing_sentiment = stock.get('sentiment', 0.5)
                    combined_sentiment = (existing_sentiment * 0.6) + ((avg_sentiment + 1) / 2 * 0.4)  # Normalize -1 to 1 → 0 to 1
                    
                    stock['sentiment'] = combined_sentiment
                    stock['news_sentiment'] = avg_sentiment
                    stock['news_count'] = len(data['feed'])
                    
                    # Get headlines
                    stock['headlines'] = [item.get('title', '')[:100] for item in data['feed'][:3]]
                
                enriched.append(stock)
                
            except Exception as e:
                logger.debug(f"Could not enrich {ticker}: {e}")
                enriched.append(stock)
        
        return enriched
    
    def _fallback_discovery(self) -> List[Dict]:
        """Fallback if main scraping fails - uses yfinance"""
        logger.info("Using fallback discovery method...")
        stocks = []
        
        try:
            import yfinance as yf
            
            # Get major indices components that are moving
            tickers_to_check = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
                'AMD', 'NFLX', 'CRM', 'PYPL', 'UBER', 'COIN', 'SQ'
            ]
            
            for ticker in tickers_to_check:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period='2d')
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        prev_price = hist['Close'].iloc[0]
                        change_pct = ((current_price - prev_price) / prev_price) * 100
                        
                        if abs(change_pct) > 1:  # Significant move
                            stocks.append({
                                'ticker': ticker,
                                'name': ticker,
                                'price': current_price,
                                'change_pct': change_pct,
                                'sentiment': 0.7 if change_pct > 0 else 0.3,
                                'confidence': min(0.8, 0.5 + abs(change_pct) / 20),
                                'action': 'BUY' if change_pct > 2 else ('SELL' if change_pct < -2 else 'HOLD'),
                                'score': abs(change_pct) / 10,
                                'sources': ['yfinance_fallback'],
                                'market': 'US'
                            })
                except:
                    continue
            
            # Add crypto fallback
            if self.include_crypto:
                for crypto in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
                    try:
                        c = yf.Ticker(crypto)
                        hist = c.history(period='1d', interval='1h')
                        
                        if not hist.empty:
                            current = hist['Close'].iloc[-1]
                            prev = hist['Close'].iloc[0]
                            change = ((current - prev) / prev) * 100
                            
                            stocks.append({
                                'ticker': crypto.replace('-USD', ''),
                                'price': current,
                                'change_pct': change,
                                'sentiment': 0.6 if change > 0 else 0.4,
                                'confidence': 0.6,
                                'action': 'BUY' if change > 2 else ('SELL' if change < -2 else 'HOLD'),
                                'score': 0.6,
                                'sources': ['yfinance_crypto'],
                                'market': 'CRYPTO'
                            })
                    except:
                        continue
            
            stocks.sort(key=lambda x: x.get('score', 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Fallback discovery failed: {e}")
        
        return stocks
    
    def get_crypto_trending(self) -> List[Dict]:
        """Get only crypto trending"""
        all_trending = self.discover_trending_stocks()
        return [s for s in all_trending if s.get('market') == 'CRYPTO']
    
    def get_us_trending(self) -> List[Dict]:
        """Get only US stocks trending"""
        all_trending = self.discover_trending_stocks()
        return [s for s in all_trending if s.get('market') == 'US']
    
    def get_indian_trending(self) -> List[Dict]:
        """Get only Indian stocks trending"""
        all_trending = self.discover_trending_stocks()
        return [s for s in all_trending if s.get('market') == 'INDIA']
    
    def get_actionable_stocks(self, min_confidence: float = 0.65) -> List[Dict]:
        """Get only stocks with high confidence actionable signals"""
        all_trending = self.discover_trending_stocks()
        return [
            s for s in all_trending 
            if s.get('confidence', 0) >= min_confidence and s.get('action') != 'HOLD'
        ]


def create_news_discovery(config: Dict = None) -> NewsDiscoveryService:
    """Factory function to create news discovery service"""
    return NewsDiscoveryService(config)
