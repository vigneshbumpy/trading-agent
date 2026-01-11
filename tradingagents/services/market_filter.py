"""
Market Filter Service
Filters stocks based on technical momentum criteria to avoid wasting compute/LLM costs on weak setups.
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Tuple

class MarketFilter:
    def __init__(self):
        pass

    def check_momentum(self, ticker: str) -> Tuple[bool, str]:
        """
        Check if stock has sufficient momentum for analysis.
        Returns: (passed: bool, reason: str)
        """
        try:
            # Fetch last 3 months data (approx 65 days)
            df = yf.download(ticker, period="3mo", progress=False)
            
            if df.empty or len(df) < 50:
                print(f"Insufficient data for {ticker}")
                return False, "Insufficient Data"

            # Clean column names (MultiIndex issue in new yfinance)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            current_price = df['Close'].iloc[-1]
            volume = df['Volume'].iloc[-1]
            
            # 1. Price vs SMA 20
            # If price is below 20-day SMA, it's short-term bearish
            sma_20 = df['Close'].rolling(window=20).mean().iloc[-1]
            
            if current_price < sma_20:
                return False, f"Price ${current_price:.2f} < SMA20 ${sma_20:.2f}"

            # 2. RSI check (Avoid < 40)
            # We want momentum, so RSI should not be too low.
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]
            
            if rsi_val < 40:
                return False, f"Weak Momentum (RSI: {rsi_val:.1f})"

            # 3. Volume check (optional, e.g. > 100k)
            avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
            if avg_vol < 100000:
                return False, f"Low Volume ({avg_vol:,.0f})"
            
            return True, "Passed Momentum Check"

        except Exception as e:
            print(f"Error checking momentum for {ticker}: {e}")
            return True, "Error (Default Allow)" # Fail open to avoid blocking due to API errors

market_filter = MarketFilter()
