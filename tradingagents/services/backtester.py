"""
Backtest Engine
Simulates the trading strategy over a historical period using yfinance data.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import json
from pathlib import Path

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.services.market_hours import MarketHoursService

logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self, trading_graph: TradingAgentsGraph):
        self.graph = trading_graph
        self.results = []
        
    def run(self, ticker: str, start_date: str, end_date: str):
        """
        Run backtest for a single ticker over a date range.
        """
        logger.info(f"Starting backtest for {ticker} from {start_date} to {end_date}")
        
        # Expand dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_dt = start_dt
        while current_dt <= end_dt:
            trade_date = current_dt.strftime("%Y-%m-%d")
            
            # Skip weekends
            if current_dt.weekday() >= 5:
                current_dt += timedelta(days=1)
                continue
                
            logger.info(f"Processing {trade_date}...")
            
            try:
                # In a real backtest, we would mock the tools to return historical data.
                # Since our tools fetch 'current' data or historical data via yfinance,
                # we rely on the tools supporting a specific date. 
                # Note: Most generic tools fetch 'current' data unless modified to accept a date context.
                # Assuming our 'propagator' and 'agents' respect 'trade_date' in state (which they should).
                
                final_state, decision = self.graph.propagate(ticker, trade_date)
                
                result_entry = {
                    "date": trade_date,
                    "ticker": ticker,
                    "action": decision.get("action", "HOLD"),
                    "quantity": decision.get("quantity", 0),
                    "confidence": decision.get("confidence", 0),
                    "price_at_decision": self._get_historical_price(ticker, trade_date)
                }
                
                self.results.append(result_entry)
                
            except Exception as e:
                logger.error(f"Error on {trade_date}: {e}")
            
            current_dt += timedelta(days=1)
            
        self._save_results(ticker)
        return self.results

    def _get_historical_price(self, ticker: str, date_str: str) -> float:
        """Fetch historical close price for a date"""
        try:
            df = yf.download(ticker, start=date_str, end=(datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"), progress=False)
            if not df.empty:
                # Clean column names
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                return float(df['Close'].iloc[0])
        except Exception:
            pass
        return 0.0

    def _save_results(self, ticker: str):
        """Save backtest results to JSON"""
        output_dir = Path("eval_results/backtests")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"backtest_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=4)
            
        logger.info(f"Backtest results saved to {filepath}")

# Usage Example:
# graph = TradingAgentsGraph(...)
# backtester = Backtester(graph)
# results = backtester.run("AAPL", "2023-01-01", "2023-01-07")
