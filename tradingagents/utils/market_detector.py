"""
Market detection utility to route symbols to correct brokers
"""

from typing import Dict, Optional, Tuple
from dashboard.multiuser.brokers.unified_broker import (
    Market,
    BrokerType,
    get_market_for_ticker,
    is_indian_market,
    is_us_market,
    is_crypto_market,
    POPULAR_STOCKS
)


class MarketDetector:
    """Detect market type and route to appropriate broker"""

    # Indian stock patterns
    INDIAN_STOCK_PATTERNS = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN",
        "BHARTIARTL", "ITC", "WIPRO", "MARUTI", "HINDUNILVR",
        "BAJFINANCE", "ASIANPAINT", "HCLTECH", "KOTAKBANK"
    ]

    # Crypto patterns
    CRYPTO_BASES = [
        "BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "DOGE",
        "MATIC", "AVAX", "LINK", "UNI", "ATOM", "ALGO", "VET",
        "TRX", "LTC", "BCH", "EOS", "XLM"
    ]

    # US stock patterns (common tickers)
    US_STOCK_PATTERNS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
        "JPM", "V", "JNJ", "WMT", "PG", "MA", "DIS", "NFLX",
        "ADBE", "INTC", "CSCO", "PEP", "COST"
    ]

    @staticmethod
    def detect_market(symbol: str) -> Market:
        """
        Detect market type from symbol

        Args:
            symbol: Trading symbol (e.g., "BTC-USD", "AAPL", "RELIANCE")

        Returns:
            Market enum
        """
        symbol_upper = symbol.upper().strip()

        # Check for crypto patterns
        if MarketDetector._is_crypto_symbol(symbol_upper):
            return Market.CRYPTO

        # Check Indian stocks
        if MarketDetector._is_indian_stock(symbol_upper):
            return Market.INDIA_NSE  # Default to NSE

        # Check US stocks
        if MarketDetector._is_us_stock(symbol_upper):
            return Market.US_NYSE  # Default to NYSE

        # Use unified broker function as fallback
        return get_market_for_ticker(symbol_upper)

    @staticmethod
    def _is_crypto_symbol(symbol: str) -> bool:
        """Check if symbol is crypto"""
        # Check for common crypto patterns
        if "-" in symbol:
            base = symbol.split("-")[0]
            return base in MarketDetector.CRYPTO_BASES

        if symbol.endswith("USDT") or symbol.endswith("BTC") or symbol.endswith("USD"):
            base = symbol.replace("USDT", "").replace("BTC", "").replace("USD", "")
            return base in MarketDetector.CRYPTO_BASES or len(base) <= 5

        # Check if it's a known crypto base
        return symbol in MarketDetector.CRYPTO_BASES

    @staticmethod
    def _is_indian_stock(symbol: str) -> bool:
        """Check if symbol is Indian stock"""
        # Check popular stocks
        for market in [Market.INDIA_NSE, Market.INDIA_BSE]:
            if symbol in POPULAR_STOCKS.get(market, {}):
                return True

        # Check patterns
        return symbol in MarketDetector.INDIAN_STOCK_PATTERNS

    @staticmethod
    def _is_us_stock(symbol: str) -> bool:
        """Check if symbol is US stock"""
        # Check popular stocks
        for market in [Market.US_NYSE, Market.US_NASDAQ, Market.US_AMEX]:
            if symbol in POPULAR_STOCKS.get(market, {}):
                return True

        # Check patterns
        return symbol in MarketDetector.US_STOCK_PATTERNS

    @staticmethod
    def get_broker_type(market: Market, preferred_broker: Optional[BrokerType] = None) -> BrokerType:
        """
        Get appropriate broker type for market

        Args:
            market: Market enum
            preferred_broker: Preferred broker (if available)

        Returns:
            BrokerType enum
        """
        if preferred_broker:
            # Validate that preferred broker supports the market
            if MarketDetector._broker_supports_market(preferred_broker, market):
                return preferred_broker

        # Default broker selection
        if is_indian_market(market):
            return BrokerType.ZERODHA  # Default to Zerodha
        elif is_us_market(market):
            return BrokerType.ALPACA  # Default to Alpaca
        elif is_crypto_market(market):
            return BrokerType.BINANCE  # Default to Binance
        else:
            return BrokerType.SIMULATED  # Fallback to simulated

    @staticmethod
    def _broker_supports_market(broker_type: BrokerType, market: Market) -> bool:
        """Check if broker supports the market"""
        if is_indian_market(market):
            return broker_type in [BrokerType.ZERODHA, BrokerType.UPSTOX, BrokerType.SIMULATED]
        elif is_us_market(market):
            return broker_type in [BrokerType.ALPACA, BrokerType.SIMULATED]
        elif is_crypto_market(market):
            return broker_type in [BrokerType.BINANCE, BrokerType.COINBASE, BrokerType.SIMULATED]
        return False

    @staticmethod
    def normalize_symbol(symbol: str, market: Market, broker_type: BrokerType) -> str:
        """
        Normalize symbol format for specific broker

        Args:
            symbol: Original symbol
            market: Market type
            broker_type: Broker type

        Returns:
            Normalized symbol
        """
        if is_crypto_market(market):
            if broker_type == BrokerType.BINANCE:
                # Convert to Binance format (BTCUSDT)
                if "-" in symbol:
                    base = symbol.split("-")[0]
                    return f"{base}USDT"
                elif not symbol.endswith("USDT") and not symbol.endswith("BTC"):
                    return f"{symbol}USDT"
                return symbol
            elif broker_type == BrokerType.COINBASE:
                # Convert to Coinbase format (BTC-USD)
                if not "-" in symbol:
                    if symbol.endswith("USDT"):
                        base = symbol.replace("USDT", "")
                        return f"{base}-USD"
                    return f"{symbol}-USD"
                elif symbol.endswith("USDT"):
                    base = symbol.replace("USDT", "")
                    return f"{base}-USD"
                return symbol

        # For stocks, return as-is (brokers handle their own formats)
        return symbol

    @staticmethod
    def get_exchange_for_market(market: Market) -> str:
        """
        Get default exchange string for market

        Args:
            market: Market enum

        Returns:
            Exchange string
        """
        if market == Market.INDIA_NSE:
            return "NSE"
        elif market == Market.INDIA_BSE:
            return "BSE"
        elif market == Market.US_NYSE:
            return "NYSE"
        elif market == Market.US_NASDAQ:
            return "NASDAQ"
        elif market == Market.US_AMEX:
            return "AMEX"
        elif market == Market.CRYPTO:
            return "CRYPTO"
        else:
            return "UNKNOWN"


def detect_market_and_broker(
    symbol: str,
    preferred_broker: Optional[BrokerType] = None
) -> Tuple[Market, BrokerType, str]:
    """
    Detect market, broker, and normalized symbol in one call

    Args:
        symbol: Trading symbol
        preferred_broker: Preferred broker type

    Returns:
        Tuple of (market, broker_type, normalized_symbol)
    """
    market = MarketDetector.detect_market(symbol)
    broker_type = MarketDetector.get_broker_type(market, preferred_broker)
    normalized_symbol = MarketDetector.normalize_symbol(symbol, market, broker_type)

    return market, broker_type, normalized_symbol
