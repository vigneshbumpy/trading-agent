"""
Real-time Stock Scraper
Fetches trending stocks from multiple sources via web scraping
No hardcoding - all data is live!
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import json

logger = logging.getLogger(__name__)

# User agent to avoid blocks
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class StockScraper:
    """Scrapes trending stocks from multiple real sources"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = 15
        
        # Cache
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(minutes=10)
    
    def get_all_trending(self) -> List[Dict]:
        """
        Get trending stocks from all sources
        
        Returns:
            List of trending stocks with source and metrics
        """
        all_stocks = []
        
        # Scrape all sources in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(self.scrape_yahoo_trending): 'yahoo_trending',
                executor.submit(self.scrape_yahoo_gainers): 'yahoo_gainers',
                executor.submit(self.scrape_yahoo_most_active): 'yahoo_active',
                executor.submit(self.scrape_finviz_screener): 'finviz',
                executor.submit(self.scrape_coingecko_trending): 'coingecko',
                executor.submit(self.scrape_tradingview_ideas): 'tradingview',
            }
            
            for future in as_completed(futures, timeout=30):
                source = futures[future]
                try:
                    result = future.result()
                    all_stocks.extend(result)
                    logger.info(f"✅ {source}: Found {len(result)} stocks")
                except Exception as e:
                    logger.error(f"❌ {source} failed: {e}")
        
        # Aggregate and rank
        return self._aggregate_stocks(all_stocks)
    
    def scrape_yahoo_trending(self) -> List[Dict]:
        """Scrape Yahoo Finance trending tickers"""
        stocks = []
        cache_key = 'yahoo_trending'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            url = "https://finance.yahoo.com/trending-tickers"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find trending table
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows[:20]:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        ticker = cols[0].get_text(strip=True)
                        name = cols[1].get_text(strip=True)
                        price = self._parse_number(cols[2].get_text(strip=True))
                        change = self._parse_number(cols[3].get_text(strip=True))
                        change_pct = self._parse_number(cols[4].get_text(strip=True).replace('%', ''))
                        
                        if ticker and len(ticker) <= 5:
                            stocks.append({
                                'ticker': ticker,
                                'name': name,
                                'price': price,
                                'change': change,
                                'change_pct': change_pct,
                                'source': 'yahoo_trending',
                                'sentiment': 0.6 if change_pct > 0 else 0.4,
                                'score': abs(change_pct) / 10  # Higher change = higher score
                            })
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"Yahoo trending error: {e}")
        
        return stocks
    
    def scrape_yahoo_gainers(self) -> List[Dict]:
        """Scrape Yahoo Finance top gainers"""
        stocks = []
        cache_key = 'yahoo_gainers'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            url = "https://finance.yahoo.com/gainers"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find stocks in the page
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:15]
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        ticker = cols[0].get_text(strip=True)
                        name = cols[1].get_text(strip=True)
                        price = self._parse_number(cols[2].get_text(strip=True))
                        change_pct = self._parse_number(cols[4].get_text(strip=True).replace('%', '').replace('+', ''))
                        
                        if ticker and len(ticker) <= 5:
                            stocks.append({
                                'ticker': ticker,
                                'name': name,
                                'price': price,
                                'change_pct': change_pct,
                                'source': 'yahoo_gainers',
                                'sentiment': 0.75,  # Gainers are bullish
                                'action': 'BUY',
                                'score': change_pct / 10
                            })
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"Yahoo gainers error: {e}")
        
        return stocks
    
    def scrape_yahoo_most_active(self) -> List[Dict]:
        """Scrape Yahoo Finance most active stocks"""
        stocks = []
        cache_key = 'yahoo_active'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            url = "https://finance.yahoo.com/most-active"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:15]
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 6:
                        ticker = cols[0].get_text(strip=True)
                        name = cols[1].get_text(strip=True)
                        price = self._parse_number(cols[2].get_text(strip=True))
                        change_pct = self._parse_number(cols[4].get_text(strip=True).replace('%', '').replace('+', ''))
                        volume = cols[5].get_text(strip=True)
                        
                        if ticker and len(ticker) <= 5:
                            stocks.append({
                                'ticker': ticker,
                                'name': name,
                                'price': price,
                                'change_pct': change_pct,
                                'volume': volume,
                                'source': 'yahoo_most_active',
                                'sentiment': 0.6 if change_pct > 0 else 0.4,
                                'score': 0.7  # High activity = important
                            })
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"Yahoo most active error: {e}")
        
        return stocks
    
    def scrape_finviz_screener(self) -> List[Dict]:
        """Scrape Finviz for high volume momentum stocks"""
        stocks = []
        cache_key = 'finviz'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            # Finviz screener: unusual volume + price above SMA20
            url = "https://finviz.com/screener.ashx?v=111&f=sh_avgvol_o500,sh_relvol_o1.5,ta_sma20_pa&ft=4"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find stock table
            table = soup.find('table', {'class': 'table-light'})
            if table:
                rows = table.find_all('tr')[1:15]
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 10:
                        ticker = cols[1].get_text(strip=True)
                        name = cols[2].get_text(strip=True)
                        price = self._parse_number(cols[8].get_text(strip=True))
                        change_pct = self._parse_number(cols[9].get_text(strip=True).replace('%', ''))
                        
                        if ticker:
                            stocks.append({
                                'ticker': ticker,
                                'name': name,
                                'price': price,
                                'change_pct': change_pct,
                                'source': 'finviz_momentum',
                                'sentiment': 0.7,  # Momentum stocks
                                'action': 'BUY',
                                'score': 0.75
                            })
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"Finviz error: {e}")
        
        return stocks
    
    def scrape_coingecko_trending(self) -> List[Dict]:
        """Scrape CoinGecko trending cryptocurrencies"""
        stocks = []
        cache_key = 'coingecko'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            # CoinGecko API for trending
            url = "https://api.coingecko.com/api/v3/search/trending"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            
            if 'coins' in data:
                for coin in data['coins'][:10]:
                    item = coin.get('item', {})
                    symbol = item.get('symbol', '').upper()
                    name = item.get('name', '')
                    market_cap_rank = item.get('market_cap_rank', 999)
                    
                    if symbol:
                        stocks.append({
                            'ticker': symbol,
                            'name': name,
                            'market_cap_rank': market_cap_rank,
                            'source': 'coingecko_trending',
                            'sentiment': 0.65,  # Trending = interest
                            'score': 1 - (market_cap_rank / 1000) if market_cap_rank else 0.5,
                            'market': 'CRYPTO'
                        })
            
            # Also get top movers
            url2 = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=10"
            response2 = self.session.get(url2, timeout=self.timeout)
            data2 = response2.json()
            
            for coin in data2[:10]:
                symbol = coin.get('symbol', '').upper()
                change_24h = coin.get('price_change_percentage_24h', 0)
                
                if symbol and abs(change_24h) > 3:  # Significant move
                    stocks.append({
                        'ticker': symbol,
                        'name': coin.get('name', ''),
                        'price': coin.get('current_price', 0),
                        'change_pct': change_24h,
                        'volume': coin.get('total_volume', 0),
                        'source': 'coingecko_movers',
                        'sentiment': 0.7 if change_24h > 0 else 0.3,
                        'action': 'BUY' if change_24h > 5 else ('SELL' if change_24h < -5 else 'HOLD'),
                        'score': abs(change_24h) / 20,
                        'market': 'CRYPTO'
                    })
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"CoinGecko error: {e}")
        
        return stocks
    
    def scrape_tradingview_ideas(self) -> List[Dict]:
        """Scrape TradingView for popular trading ideas"""
        stocks = []
        cache_key = 'tradingview'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            # TradingView ideas page
            url = "https://www.tradingview.com/ideas/stocks/"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find idea cards
            cards = soup.find_all('div', {'class': re.compile('idea-card')})[:15]
            
            for card in cards:
                try:
                    # Extract ticker from the card
                    ticker_elem = card.find('a', {'class': re.compile('symbol')})
                    if ticker_elem:
                        ticker = ticker_elem.get_text(strip=True).upper()
                        
                        # Extract sentiment from idea type (long/short)
                        idea_type = card.find('span', {'class': re.compile('type')})
                        if idea_type:
                            type_text = idea_type.get_text(strip=True).lower()
                            if 'long' in type_text:
                                sentiment = 0.75
                                action = 'BUY'
                            elif 'short' in type_text:
                                sentiment = 0.25
                                action = 'SELL'
                            else:
                                sentiment = 0.5
                                action = 'HOLD'
                        else:
                            sentiment = 0.5
                            action = 'HOLD'
                        
                        if ticker and len(ticker) <= 6:
                            stocks.append({
                                'ticker': ticker,
                                'source': 'tradingview_ideas',
                                'sentiment': sentiment,
                                'action': action,
                                'score': 0.6
                            })
                except:
                    continue
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"TradingView error: {e}")
        
        return stocks
    
    def scrape_reddit_wsb(self) -> List[Dict]:
        """Scrape Reddit WallStreetBets for trending tickers"""
        stocks = []
        cache_key = 'reddit_wsb'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            # Reddit JSON API
            url = "https://www.reddit.com/r/wallstreetbets/hot.json?limit=50"
            headers = {**HEADERS, 'Accept': 'application/json'}
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            data = response.json()
            
            # Common ticker pattern
            ticker_pattern = re.compile(r'\$([A-Z]{2,5})\b|\b([A-Z]{2,5})\b')
            ticker_counts = {}
            
            for post in data.get('data', {}).get('children', []):
                post_data = post.get('data', {})
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')[:500]
                
                # Find tickers
                text = f"{title} {selftext}"
                matches = ticker_pattern.findall(text)
                
                for match in matches:
                    ticker = match[0] or match[1]
                    if ticker and 2 <= len(ticker) <= 5:
                        # Filter out common words
                        if ticker not in {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'HAS', 'HIS', 'HOW', 'MAN', 'NEW', 'NOW', 'OLD', 'SEE', 'WAY', 'WHO', 'BOY', 'DID', 'GET', 'HAS', 'HIM', 'HIS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE', 'WSB', 'DD', 'IMO', 'YOLO', 'FD', 'OTM', 'ITM', 'ATM', 'EOD', 'EOW', 'IV', 'DTE'}:
                            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
            
            # Top mentioned
            sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            for ticker, count in sorted_tickers:
                if count >= 2:  # At least 2 mentions
                    stocks.append({
                        'ticker': ticker,
                        'mentions': count,
                        'source': 'reddit_wsb',
                        'sentiment': 0.6,  # WSB is generally bullish
                        'action': 'BUY' if count >= 5 else 'HOLD',
                        'score': min(1.0, count / 10)
                    })
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"Reddit WSB error: {e}")
        
        return stocks
    
    def scrape_indian_stocks(self) -> List[Dict]:
        """Scrape NSE India for top gainers/movers"""
        stocks = []
        cache_key = 'nse_india'
        
        if self._is_cached(cache_key):
            return self._cache[cache_key]
        
        try:
            # NSE India top gainers
            url = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
            headers = {
                **HEADERS,
                'Accept': 'application/json',
                'Referer': 'https://www.nseindia.com/'
            }
            
            # Need to get cookies first
            self.session.get("https://www.nseindia.com/", timeout=self.timeout)
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                for stock in data.get('NIFTY', {}).get('data', [])[:10]:
                    symbol = stock.get('symbol', '')
                    change_pct = float(stock.get('pChange', 0))
                    
                    if symbol:
                        stocks.append({
                            'ticker': f"{symbol}.NS",
                            'name': symbol,
                            'price': float(stock.get('lastPrice', 0)),
                            'change_pct': change_pct,
                            'source': 'nse_gainers',
                            'sentiment': 0.7,
                            'action': 'BUY',
                            'score': change_pct / 10,
                            'market': 'INDIA'
                        })
            
            self._set_cache(cache_key, stocks)
            
        except Exception as e:
            logger.error(f"NSE India error: {e}")
        
        return stocks
    
    def _aggregate_stocks(self, all_stocks: List[Dict]) -> List[Dict]:
        """Aggregate stocks from multiple sources and rank them"""
        
        # Group by ticker
        aggregated = {}
        
        for stock in all_stocks:
            ticker = stock.get('ticker', '').upper()
            if not ticker:
                continue
            
            if ticker not in aggregated:
                aggregated[ticker] = {
                    'ticker': ticker,
                    'name': stock.get('name', ticker),
                    'sources': [],
                    'sentiments': [],
                    'scores': [],
                    'actions': [],
                    'price': stock.get('price'),
                    'change_pct': stock.get('change_pct'),
                    'market': stock.get('market', 'US')
                }
            
            aggregated[ticker]['sources'].append(stock.get('source', 'unknown'))
            aggregated[ticker]['sentiments'].append(stock.get('sentiment', 0.5))
            aggregated[ticker]['scores'].append(stock.get('score', 0.5))
            if stock.get('action'):
                aggregated[ticker]['actions'].append(stock['action'])
        
        # Calculate final scores
        ranked = []
        for ticker, data in aggregated.items():
            # More sources = more confidence
            source_bonus = len(set(data['sources'])) * 0.1
            
            avg_sentiment = sum(data['sentiments']) / len(data['sentiments'])
            avg_score = sum(data['scores']) / len(data['scores'])
            
            # Determine action
            if data['actions']:
                buy_count = data['actions'].count('BUY')
                sell_count = data['actions'].count('SELL')
                if buy_count > sell_count:
                    action = 'BUY'
                elif sell_count > buy_count:
                    action = 'SELL'
                else:
                    action = 'HOLD'
            else:
                action = 'BUY' if avg_sentiment > 0.55 else ('SELL' if avg_sentiment < 0.45 else 'HOLD')
            
            final_score = avg_score + source_bonus
            confidence = min(0.95, avg_sentiment * 0.6 + (len(data['sources']) / 10) * 0.4)
            
            ranked.append({
                'ticker': ticker,
                'name': data['name'],
                'price': data['price'],
                'change_pct': data['change_pct'],
                'sentiment': avg_sentiment,
                'score': final_score,
                'confidence': confidence,
                'action': action,
                'sources': list(set(data['sources'])),
                'source_count': len(set(data['sources'])),
                'market': data['market'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Sort by score
        ranked.sort(key=lambda x: x['score'], reverse=True)
        
        return ranked
    
    def _parse_number(self, text: str) -> float:
        """Parse number from text"""
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[,$€£₹%+]', '', text)
            return float(cleaned)
        except:
            return 0.0
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and fresh"""
        if key not in self._cache:
            return False
        if key not in self._cache_time:
            return False
        return datetime.now() - self._cache_time[key] < self._cache_duration
    
    def _set_cache(self, key: str, data: List):
        """Set cache data"""
        self._cache[key] = data
        self._cache_time[key] = datetime.now()


def create_stock_scraper(config: Dict = None) -> StockScraper:
    """Factory function"""
    return StockScraper(config)
