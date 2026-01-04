from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor
from datetime import datetime
import re


@tool
def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company, e.g. AAPL, NVDA, TSLA"],
    start_date: Annotated[str, "Start date in YYYY-MM-DD format, e.g. 2024-01-15"],
    end_date: Annotated[str, "End date in YYYY-MM-DD format, e.g. 2024-05-10"],
) -> str:
    """
    Retrieve stock price data (OHLCV) for a given ticker symbol.

    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, NVDA, TSLA, GOOGL
        start_date (str): Start date in YYYY-MM-DD format (e.g., 2024-01-15)
        end_date (str): End date in YYYY-MM-DD format (e.g., 2024-05-10)
    Returns:
        str: A formatted dataframe containing Open, High, Low, Close, Volume data.
    """
    # Validate symbol
    if not symbol or symbol.strip() == '':
        return "Error: symbol parameter is required (e.g., AAPL, NVDA)"

    # Validate dates
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    if not start_date or start_date.strip() == '':
        return "Error: start_date is required in YYYY-MM-DD format (e.g., 2024-01-15)"

    if not end_date or end_date.strip() == '':
        return "Error: end_date is required in YYYY-MM-DD format (e.g., 2024-05-10)"

    if not date_pattern.match(start_date):
        return f"Error: start_date '{start_date}' is invalid. Use YYYY-MM-DD format (e.g., 2024-01-15)"

    if not date_pattern.match(end_date):
        return f"Error: end_date '{end_date}' is invalid. Use YYYY-MM-DD format (e.g., 2024-05-10)"

    return route_to_vendor("get_stock_data", symbol.strip().upper(), start_date.strip(), end_date.strip())
