"""
Fast Value Screener (Stage 1)

Screens 1000s of stocks in ~30 seconds using bulk yfinance data.
Filters based on configurable value metrics.
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

from .config import ScannerConfig, ScreeningConfig


@dataclass
class ScreenedStock:
    """Result from screening"""
    symbol: str
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    debt_equity: Optional[float]
    current_ratio: Optional[float]
    roe: Optional[float]
    market_cap: Optional[float]
    price: Optional[float]
    dividend_yield: Optional[float]
    profit_margin: Optional[float]
    revenue_growth: Optional[float]
    sector: Optional[str]
    industry: Optional[str]
    score: float = 0.0  # Composite value score


class ValueScreener:
    """Fast bulk stock screener using yfinance"""

    def __init__(self, config: ScannerConfig):
        self.config = config
        self.screening = config.screening

    def fetch_stock_data(self, symbol: str) -> Optional[Dict]:
        """Fetch fundamental data for a single stock"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or 'symbol' not in info:
                return None

            return {
                'symbol': symbol,
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'debt_equity': info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else None,
                'current_ratio': info.get('currentRatio'),
                'roe': info.get('returnOnEquity'),
                'market_cap': info.get('marketCap'),
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'dividend_yield': info.get('dividendYield'),
                'profit_margin': info.get('profitMargins'),
                'revenue_growth': info.get('revenueGrowth'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'name': info.get('shortName', symbol),
            }
        except Exception as e:
            # Silent fail for individual stocks
            return None

    def fetch_bulk_data(self, symbols: List[str], max_workers: int = 20) -> List[Dict]:
        """Fetch data for multiple stocks in parallel"""
        results = []
        failed = []

        print(f"Fetching data for {len(symbols)} stocks...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.fetch_stock_data, symbol): symbol
                for symbol in symbols
            }

            completed = 0
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                completed += 1

                if completed % 50 == 0:
                    print(f"Progress: {completed}/{len(symbols)} stocks fetched")

                try:
                    data = future.result()
                    if data:
                        results.append(data)
                    else:
                        failed.append(symbol)
                except Exception as e:
                    failed.append(symbol)

        elapsed = time.time() - start_time
        print(f"Fetched {len(results)} stocks in {elapsed:.1f}s ({len(failed)} failed)")

        return results

    def passes_filter(self, stock: Dict) -> bool:
        """Check if stock passes all screening criteria"""
        s = self.screening

        # P/E ratio filter
        if stock.get('pe_ratio') is not None:
            if stock['pe_ratio'] <= 0 or stock['pe_ratio'] > s.pe_ratio_max:
                return False

        # P/B ratio filter
        if stock.get('pb_ratio') is not None:
            if stock['pb_ratio'] <= 0 or stock['pb_ratio'] > s.pb_ratio_max:
                return False

        # Debt/Equity filter
        if stock.get('debt_equity') is not None:
            if stock['debt_equity'] > s.debt_equity_max:
                return False

        # Current ratio filter
        if stock.get('current_ratio') is not None:
            if stock['current_ratio'] < s.current_ratio_min:
                return False

        # ROE filter
        if stock.get('roe') is not None:
            if stock['roe'] < s.roe_min:
                return False

        # Market cap filter
        if stock.get('market_cap') is not None:
            if stock['market_cap'] < s.market_cap_min:
                return False

        # Optional filters
        if s.dividend_yield_min is not None and stock.get('dividend_yield') is not None:
            if stock['dividend_yield'] < s.dividend_yield_min:
                return False

        if s.profit_margin_min is not None and stock.get('profit_margin') is not None:
            if stock['profit_margin'] < s.profit_margin_min:
                return False

        if s.revenue_growth_min is not None and stock.get('revenue_growth') is not None:
            if stock['revenue_growth'] < s.revenue_growth_min:
                return False

        return True

    def calculate_value_score(self, stock: Dict) -> float:
        """Calculate composite value score (0-100)"""
        score = 50.0  # Base score
        s = self.screening

        # Lower P/E is better (max 20 points)
        if stock.get('pe_ratio') and stock['pe_ratio'] > 0:
            pe_score = max(0, (s.pe_ratio_max - stock['pe_ratio']) / s.pe_ratio_max * 20)
            score += pe_score

        # Lower P/B is better (max 15 points)
        if stock.get('pb_ratio') and stock['pb_ratio'] > 0:
            pb_score = max(0, (s.pb_ratio_max - stock['pb_ratio']) / s.pb_ratio_max * 15)
            score += pb_score

        # Lower debt is better (max 10 points)
        if stock.get('debt_equity') is not None:
            debt_score = max(0, (s.debt_equity_max - stock['debt_equity']) / s.debt_equity_max * 10)
            score += debt_score

        # Higher ROE is better (max 15 points)
        if stock.get('roe') and stock['roe'] > 0:
            roe_score = min(15, stock['roe'] / 0.20 * 15)  # 20% ROE = max score
            score += roe_score

        # Higher current ratio is better (max 10 points)
        if stock.get('current_ratio') and stock['current_ratio'] > 0:
            cr_score = min(10, (stock['current_ratio'] - 1) / 2 * 10)
            score += cr_score

        return min(100, max(0, score))

    def screen(self, symbols: List[str]) -> List[ScreenedStock]:
        """
        Screen stocks and return filtered results sorted by value score.

        Args:
            symbols: List of stock symbols to screen

        Returns:
            List of ScreenedStock objects that pass filters, sorted by score
        """
        print(f"\n{'='*60}")
        print(f"STAGE 1: VALUE SCREENING")
        print(f"{'='*60}")
        print(f"Screening {len(symbols)} stocks with criteria:")
        print(f"  P/E < {self.screening.pe_ratio_max}")
        print(f"  P/B < {self.screening.pb_ratio_max}")
        print(f"  Debt/Equity < {self.screening.debt_equity_max}")
        print(f"  Current Ratio > {self.screening.current_ratio_min}")
        print(f"  ROE > {self.screening.roe_min*100:.0f}%")
        print(f"  Market Cap > ${self.screening.market_cap_min/1e9:.1f}B")
        print()

        # Fetch all data in parallel
        all_data = self.fetch_bulk_data(symbols)

        # Filter and score
        passed = []
        for stock in all_data:
            if self.passes_filter(stock):
                score = self.calculate_value_score(stock)
                screened = ScreenedStock(
                    symbol=stock['symbol'],
                    pe_ratio=stock.get('pe_ratio'),
                    pb_ratio=stock.get('pb_ratio'),
                    debt_equity=stock.get('debt_equity'),
                    current_ratio=stock.get('current_ratio'),
                    roe=stock.get('roe'),
                    market_cap=stock.get('market_cap'),
                    price=stock.get('price'),
                    dividend_yield=stock.get('dividend_yield'),
                    profit_margin=stock.get('profit_margin'),
                    revenue_growth=stock.get('revenue_growth'),
                    sector=stock.get('sector'),
                    industry=stock.get('industry'),
                    score=score,
                )
                passed.append(screened)

        # Sort by score descending
        passed.sort(key=lambda x: x.score, reverse=True)

        print(f"\nScreening complete: {len(passed)}/{len(all_data)} stocks passed filters")
        print(f"{'='*60}\n")

        return passed

    def screen_to_dataframe(self, symbols: List[str]) -> pd.DataFrame:
        """Screen stocks and return results as DataFrame"""
        results = self.screen(symbols)

        if not results:
            return pd.DataFrame()

        data = []
        for r in results:
            data.append({
                'Symbol': r.symbol,
                'Score': round(r.score, 1),
                'P/E': round(r.pe_ratio, 2) if r.pe_ratio else None,
                'P/B': round(r.pb_ratio, 2) if r.pb_ratio else None,
                'D/E': round(r.debt_equity, 2) if r.debt_equity else None,
                'Current': round(r.current_ratio, 2) if r.current_ratio else None,
                'ROE': f"{r.roe*100:.1f}%" if r.roe else None,
                'Mkt Cap': f"${r.market_cap/1e9:.1f}B" if r.market_cap else None,
                'Price': f"${r.price:.2f}" if r.price else None,
                'Sector': r.sector,
            })

        return pd.DataFrame(data)


# Quick test
if __name__ == "__main__":
    from .config import ScannerConfig, get_sp500_symbols

    config = ScannerConfig()
    screener = ValueScreener(config)

    # Test with a small sample
    symbols = ["AAPL", "MSFT", "GOOGL", "JPM", "BAC", "WMT", "KO", "PEP"]
    results = screener.screen(symbols)

    print("\nTop Value Stocks:")
    for stock in results[:5]:
        print(f"  {stock.symbol}: Score={stock.score:.1f}, P/E={stock.pe_ratio}, P/B={stock.pb_ratio}")
