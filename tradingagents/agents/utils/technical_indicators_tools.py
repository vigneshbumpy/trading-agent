from langchain_core.tools import tool
from typing import Annotated, Literal
from tradingagents.dataflows.interface import route_to_vendor

# Valid indicators supported by the system
VALID_INDICATORS = [
    'close_50_sma', 'close_200_sma', 'close_10_ema',
    'macd', 'macds', 'macdh', 'rsi',
    'boll', 'boll_ub', 'boll_lb',
    'atr', 'vwma', 'mfi'
]

@tool
def get_indicators(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator - MUST be one of: close_50_sma, close_200_sma, close_10_ema, macd, macds, macdh, rsi, boll, boll_ub, boll_lb, atr, vwma, mfi"],
    curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"] = 30,
) -> str:
    """
    Retrieve technical indicators for a given ticker symbol.

    IMPORTANT: The indicator parameter MUST be one of the following valid options:
    - Moving Averages: close_50_sma, close_200_sma, close_10_ema
    - MACD: macd (MACD line), macds (signal line), macdh (histogram)
    - RSI: rsi (Relative Strength Index)
    - Bollinger Bands: boll (middle), boll_ub (upper), boll_lb (lower)
    - Other: atr (Average True Range), vwma (Volume Weighted MA), mfi (Money Flow Index)

    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, NVDA, TSLA
        indicator (str): Technical indicator - must be one of the valid options listed above
        curr_date (str): The current trading date, format YYYY-mm-dd
        look_back_days (int): How many days to look back, default is 30
    Returns:
        str: A formatted dataframe containing the technical indicator data.
    """
    # Validate indicator
    if not indicator or indicator.strip() == '':
        return f"Error: indicator parameter is required. Valid options: {', '.join(VALID_INDICATORS)}"

    indicator = indicator.strip().lower()
    if indicator not in VALID_INDICATORS:
        return f"Error: '{indicator}' is not valid. Choose from: {', '.join(VALID_INDICATORS)}"

    return route_to_vendor("get_indicators", symbol, indicator, curr_date, look_back_days)