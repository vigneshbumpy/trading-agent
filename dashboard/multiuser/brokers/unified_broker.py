"""
Unified broker interface supporting Indian, US, and Crypto markets
Supports: Zerodha (India), Upstox (India), Alpaca (US), Binance (Crypto), Coinbase (Crypto)
"""

from typing import Dict, List, Optional
from enum import Enum
from abc import ABC, abstractmethod


class Market(str, Enum):
    """Supported markets"""
    INDIA_NSE = "NSE"  # National Stock Exchange of India
    INDIA_BSE = "BSE"  # Bombay Stock Exchange
    US_NYSE = "NYSE"   # New York Stock Exchange
    US_NASDAQ = "NASDAQ"  # NASDAQ
    US_AMEX = "AMEX"   # American Stock Exchange
    CRYPTO = "CRYPTO"  # Cryptocurrency markets (24/7)


class BrokerType(str, Enum):
    """Supported brokers"""
    ZERODHA = "zerodha"      # Indian broker
    UPSTOX = "upstox"        # Indian broker
    ALPACA = "alpaca"        # US broker
    BINANCE = "binance"      # Crypto broker
    COINBASE = "coinbase"    # Crypto broker
    INTERACTIVE_BROKERS = "interactive_brokers"  # Global broker
    SIMULATED = "simulated"  # Paper trading


class UnifiedBrokerInterface(ABC):
    """Base interface that all brokers must implement"""

    @abstractmethod
    def get_account_info(self) -> Dict:
        """Get account information"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        pass

    @abstractmethod
    def get_quote(self, symbol: str, exchange: str) -> Dict:
        """Get real-time quote"""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        exchange: str,
        action: str,  # BUY/SELL
        quantity: float,
        order_type: str = "MARKET",
        price: float = None
    ) -> Dict:
        """Place an order"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        pass

    @abstractmethod
    def get_orders(self) -> List[Dict]:
        """Get all orders"""
        pass

    @abstractmethod
    def get_supported_markets(self) -> List[Market]:
        """Get list of supported markets"""
        pass


class BrokerFactory:
    """Factory to create appropriate broker instance"""

    @staticmethod
    def create_broker(
        broker_type: BrokerType,
        credentials: Dict
    ) -> UnifiedBrokerInterface:
        """
        Create broker instance

        Args:
            broker_type: Type of broker
            credentials: API credentials

        Returns:
            Broker instance
        """
        if broker_type == BrokerType.ZERODHA:
            from dashboard.multiuser.brokers.zerodha import ZerodhaKiteAPI
            return ZerodhaBrokerAdapter(
                api_key=credentials.get('api_key'),
                api_secret=credentials.get('api_secret'),
                access_token=credentials.get('access_token')
            )

        elif broker_type == BrokerType.UPSTOX:
            from dashboard.multiuser.brokers.upstox import UpstoxAPI
            return UpstoxBrokerAdapter(
                api_key=credentials.get('api_key'),
                api_secret=credentials.get('api_secret'),
                access_token=credentials.get('access_token')
            )

        elif broker_type == BrokerType.ALPACA:
            from dashboard.utils.broker import AlpacaBroker
            return AlpacaBrokerAdapter(
                paper_trading=credentials.get('paper_trading', True)
            )

        elif broker_type == BrokerType.BINANCE:
            from dashboard.multiuser.brokers.binance import BinanceAPI
            return BinanceBrokerAdapter(
                api_key=credentials.get('api_key'),
                api_secret=credentials.get('api_secret'),
                testnet=credentials.get('testnet', True)
            )

        elif broker_type == BrokerType.COINBASE:
            from dashboard.multiuser.brokers.coinbase import CoinbaseAPI
            return CoinbaseBrokerAdapter(
                api_key=credentials.get('api_key'),
                api_secret=credentials.get('api_secret'),
                sandbox=credentials.get('sandbox', True)
            )

        elif broker_type == BrokerType.SIMULATED:
            from dashboard.utils.broker import PaperBroker
            return SimulatedBrokerAdapter()

        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")


class ZerodhaBrokerAdapter(UnifiedBrokerInterface):
    """Adapter for Zerodha Kite API"""

    def __init__(self, api_key: str, api_secret: str = None, access_token: str = None):
        from dashboard.multiuser.brokers.zerodha import ZerodhaKiteAPI
        self.broker = ZerodhaKiteAPI(api_key, api_secret, access_token)

    def get_account_info(self) -> Dict:
        margins = self.broker.get_margins()
        profile = self.broker.get_profile()

        return {
            "broker": "zerodha",
            "account_id": profile.get('user_id'),
            "name": profile.get('user_name'),
            "email": profile.get('email'),
            "cash": margins.get('equity', {}).get('available', {}).get('cash', 0),
            "buying_power": margins.get('equity', {}).get('available', {}).get('live_balance', 0),
            "currency": "INR"
        }

    def get_positions(self) -> List[Dict]:
        positions_data = self.broker.get_positions()
        positions = []

        for pos in positions_data.get('day', []) + positions_data.get('net', []):
            positions.append({
                "symbol": pos['tradingsymbol'],
                "exchange": pos['exchange'],
                "quantity": pos['quantity'],
                "avg_price": pos['average_price'],
                "current_price": pos['last_price'],
                "pnl": pos['pnl'],
                "market": Market.INDIA_NSE if pos['exchange'] == 'NSE' else Market.INDIA_BSE
            })

        return positions

    def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict:
        from dashboard.multiuser.brokers.zerodha import convert_to_kite_symbol
        kite_symbol = convert_to_kite_symbol(symbol, exchange)
        quote = self.broker.get_quote([kite_symbol])

        if kite_symbol in quote:
            q = quote[kite_symbol]
            return {
                "symbol": symbol,
                "exchange": exchange,
                "last_price": q.get('last_price'),
                "bid": q.get('depth', {}).get('buy', [{}])[0].get('price'),
                "ask": q.get('depth', {}).get('sell', [{}])[0].get('price'),
                "volume": q.get('volume'),
                "market": Market.INDIA_NSE if exchange == 'NSE' else Market.INDIA_BSE
            }

        return {"error": "Quote not found"}

    def place_order(
        self,
        symbol: str,
        exchange: str,
        action: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float = None
    ) -> Dict:
        result = self.broker.place_order(
            tradingsymbol=symbol,
            exchange=exchange,
            transaction_type=action,
            quantity=int(quantity),
            order_type=order_type,
            product="CNC",  # Delivery
            price=price
        )

        return result

    def cancel_order(self, order_id: str) -> Dict:
        return self.broker.cancel_order(order_id)

    def get_orders(self) -> List[Dict]:
        return self.broker.get_orders()

    def get_supported_markets(self) -> List[Market]:
        return [Market.INDIA_NSE, Market.INDIA_BSE]


class AlpacaBrokerAdapter(UnifiedBrokerInterface):
    """Adapter for Alpaca (US markets)"""

    def __init__(self, paper_trading: bool = True):
        from dashboard.utils.broker import AlpacaBroker
        self.broker = AlpacaBroker(paper_trading=paper_trading)

    def get_account_info(self) -> Dict:
        account = self.broker.get_account()

        return {
            "broker": "alpaca",
            "account_id": account.get('account_number'),
            "cash": account.get('cash'),
            "buying_power": account.get('buying_power'),
            "portfolio_value": account.get('portfolio_value'),
            "currency": "USD"
        }

    def get_positions(self) -> List[Dict]:
        positions = self.broker.get_all_positions()

        for pos in positions:
            pos['symbol'] = pos['ticker']
            pos['exchange'] = 'NYSE'  # Default
            pos['market'] = Market.US_NYSE
            pos['avg_price'] = pos.get('avg_price', 0)
            pos['current_price'] = pos.get('current_price', 0)
            pos['pnl'] = pos.get('unrealized_pl', 0)

        return positions

    def get_quote(self, symbol: str, exchange: str = "NYSE") -> Dict:
        quote = self.broker.get_quote(symbol)

        if quote:
            return {
                "symbol": symbol,
                "exchange": exchange,
                "last_price": (quote['bid_price'] + quote['ask_price']) / 2,
                "bid": quote['bid_price'],
                "ask": quote['ask_price'],
                "market": Market.US_NYSE if exchange == 'NYSE' else Market.US_NASDAQ
            }

        return {"error": "Quote not found"}

    def place_order(
        self,
        symbol: str,
        exchange: str,
        action: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float = None
    ) -> Dict:
        from dashboard.utils.broker import OrderSide, OrderType

        side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
        otype = OrderType.MARKET if order_type == "MARKET" else OrderType.LIMIT

        result = self.broker.place_order(
            ticker=symbol,
            quantity=quantity,
            side=side,
            order_type=otype,
            limit_price=price
        )

        return result

    def cancel_order(self, order_id: str) -> Dict:
        success = self.broker.cancel_order(order_id)
        return {"status": "success" if success else "error"}

    def get_orders(self) -> List[Dict]:
        # Alpaca broker doesn't have this method in our implementation
        return []

    def get_supported_markets(self) -> List[Market]:
        return [Market.US_NYSE, Market.US_NASDAQ, Market.US_AMEX]


class SimulatedBrokerAdapter(UnifiedBrokerInterface):
    """Adapter for simulated paper trading (supports all markets)"""

    def __init__(self):
        from dashboard.utils.broker import PaperBroker
        self.broker = PaperBroker()

    def get_account_info(self) -> Dict:
        account = self.broker.get_account()

        return {
            "broker": "simulated",
            "account_id": "PAPER_SIM",
            "cash": account['cash'],
            "buying_power": account['buying_power'],
            "portfolio_value": account['portfolio_value'],
            "currency": "USD"  # Can handle multi-currency
        }

    def get_positions(self) -> List[Dict]:
        positions = self.broker.get_all_positions()

        for pos in positions:
            if pos:
                pos['symbol'] = pos['ticker']
                pos['exchange'] = 'SIMULATED'
                pos['market'] = Market.US_NYSE  # Default
                pos['pnl'] = pos.get('unrealized_pl', 0)

        return positions

    def get_quote(self, symbol: str, exchange: str = "NYSE") -> Dict:
        quote = self.broker.get_quote(symbol)

        if quote:
            return {
                "symbol": symbol,
                "exchange": exchange,
                "last_price": (quote['bid_price'] + quote['ask_price']) / 2,
                "bid": quote['bid_price'],
                "ask": quote['ask_price'],
                "market": Market.US_NYSE
            }

        return {"error": "Quote not found"}

    def place_order(
        self,
        symbol: str,
        exchange: str,
        action: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float = None
    ) -> Dict:
        from dashboard.utils.broker import OrderSide, OrderType

        side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
        otype = OrderType.MARKET if order_type == "MARKET" else OrderType.LIMIT

        result = self.broker.place_order(
            ticker=symbol,
            quantity=quantity,
            side=side,
            order_type=otype,
            limit_price=price or 100.0
        )

        return result

    def cancel_order(self, order_id: str) -> Dict:
        return {"status": "error", "message": "Simulated orders execute immediately"}

    def get_orders(self) -> List[Dict]:
        return []

    def get_supported_markets(self) -> List[Market]:
        return list(Market)  # Supports all markets in simulation


class BinanceBrokerAdapter(UnifiedBrokerInterface):
    """Adapter for Binance (Crypto markets)"""

    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        from dashboard.multiuser.brokers.binance import BinanceAPI, convert_to_binance_symbol
        self.broker = BinanceAPI(api_key, api_secret, testnet)
        self.convert_symbol = convert_to_binance_symbol

    def get_account_info(self) -> Dict:
        account = self.broker.get_account_info()
        
        if "error" in account:
            return account

        # Calculate total USDT balance
        balances = account.get("balances", {})
        total_usdt = balances.get("USDT", {}).get("total", 0)

        return {
            "broker": "binance",
            "account_id": "BINANCE_SPOT",
            "cash": total_usdt,
            "buying_power": total_usdt,
            "portfolio_value": total_usdt,
            "currency": "USDT",
            "balances": balances
        }

    def get_positions(self) -> List[Dict]:
        positions = self.broker.get_positions()
        
        for pos in positions:
            pos['exchange'] = 'BINANCE'
            pos['market'] = Market.CRYPTO
            pos['avg_price'] = pos.get('current_price', 0)
            pos['pnl'] = 0  # Calculate if needed

        return positions

    def get_quote(self, symbol: str, exchange: str = "BINANCE") -> Dict:
        # Convert symbol to Binance format if needed
        if "-" in symbol:
            # Convert BTC-USD to BTCUSDT
            base = symbol.split("-")[0]
            symbol = self.convert_symbol(base, "USDT")
        elif not symbol.endswith("USDT") and not symbol.endswith("BTC") and not symbol.endswith("BUSD"):
            # Assume it's a base currency, add USDT
            symbol = self.convert_symbol(symbol, "USDT")

        quote = self.broker.get_quote(symbol)
        
        if "error" in quote:
            return quote

        quote['exchange'] = exchange
        quote['market'] = Market.CRYPTO
        return quote

    def place_order(
        self,
        symbol: str,
        exchange: str,
        action: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float = None
    ) -> Dict:
        # Convert symbol to Binance format
        if "-" in symbol:
            base = symbol.split("-")[0]
            symbol = self.convert_symbol(base, "USDT")
        elif not symbol.endswith("USDT") and not symbol.endswith("BTC") and not symbol.endswith("BUSD"):
            symbol = self.convert_symbol(symbol, "USDT")

        result = self.broker.place_order(
            symbol=symbol,
            side=action,
            quantity=quantity,
            price=price,
            order_type=order_type
        )

        return result

    def cancel_order(self, order_id: str) -> Dict:
        # Binance requires symbol, but we'll try to get it from order history
        # For now, return error - this should be improved
        return {"status": "error", "message": "Cancel order requires symbol. Use broker-specific method."}

    def get_orders(self) -> List[Dict]:
        return self.broker.get_orders()

    def get_supported_markets(self) -> List[Market]:
        return [Market.CRYPTO]


class CoinbaseBrokerAdapter(UnifiedBrokerInterface):
    """Adapter for Coinbase (Crypto markets)"""

    def __init__(self, api_key: str = None, api_secret: str = None, sandbox: bool = True):
        from dashboard.multiuser.brokers.coinbase import CoinbaseAPI, convert_to_coinbase_symbol
        self.broker = CoinbaseAPI(api_key, api_secret, sandbox)
        self.convert_symbol = convert_to_coinbase_symbol

    def get_account_info(self) -> Dict:
        account = self.broker.get_account_info()
        
        if "error" in account:
            return account

        balances = account.get("balances", {})
        total_usd = account.get("total_balance", 0)

        return {
            "broker": "coinbase",
            "account_id": "COINBASE_ADVANCED",
            "cash": balances.get("USD", {}).get("total", total_usd),
            "buying_power": balances.get("USD", {}).get("total", total_usd),
            "portfolio_value": total_usd,
            "currency": "USD",
            "balances": balances
        }

    def get_positions(self) -> List[Dict]:
        positions = self.broker.get_positions()
        
        for pos in positions:
            pos['exchange'] = 'COINBASE'
            pos['market'] = Market.CRYPTO
            pos['avg_price'] = pos.get('current_price', 0)
            pos['pnl'] = 0  # Calculate if needed

        return positions

    def get_quote(self, symbol: str, exchange: str = "COINBASE") -> Dict:
        # Convert symbol to Coinbase format if needed
        if not "-" in symbol:
            # Assume it's a base currency, add USD
            symbol = self.convert_symbol(symbol, "USD")
        elif symbol.endswith("USDT"):
            # Convert USDT to USD
            base = symbol.replace("USDT", "")
            symbol = self.convert_symbol(base, "USD")

        quote = self.broker.get_quote(symbol)
        
        if "error" in quote:
            return quote

        quote['exchange'] = exchange
        quote['market'] = Market.CRYPTO
        return quote

    def place_order(
        self,
        symbol: str,
        exchange: str,
        action: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float = None
    ) -> Dict:
        # Convert symbol to Coinbase format
        if not "-" in symbol:
            symbol = self.convert_symbol(symbol, "USD")
        elif symbol.endswith("USDT"):
            base = symbol.replace("USDT", "")
            symbol = self.convert_symbol(base, "USD")

        result = self.broker.place_order(
            symbol=symbol,
            side=action,
            quantity=quantity,
            price=price,
            order_type=order_type
        )

        return result

    def cancel_order(self, order_id: str) -> Dict:
        return self.broker.cancel_order(order_id)

    def get_orders(self) -> List[Dict]:
        return self.broker.get_orders()

    def get_supported_markets(self) -> List[Market]:
        return [Market.CRYPTO]


# Popular stocks by market
POPULAR_STOCKS = {
    Market.INDIA_NSE: {
        "RELIANCE": "Reliance Industries",
        "TCS": "Tata Consultancy Services",
        "HDFCBANK": "HDFC Bank",
        "INFY": "Infosys",
        "ICICIBANK": "ICICI Bank",
        "SBIN": "State Bank of India",
        "BHARTIARTL": "Bharti Airtel",
        "ITC": "ITC Limited",
        "WIPRO": "Wipro",
        "MARUTI": "Maruti Suzuki",
    },
    Market.US_NYSE: {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "AMZN": "Amazon.com Inc.",
        "NVDA": "NVIDIA Corporation",
        "TSLA": "Tesla Inc.",
        "META": "Meta Platforms Inc.",
        "JPM": "JPMorgan Chase & Co.",
        "V": "Visa Inc.",
        "JNJ": "Johnson & Johnson",
    },
    Market.US_NASDAQ: {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "AMZN": "Amazon.com Inc.",
        "NVDA": "NVIDIA Corporation",
        "TSLA": "Tesla Inc.",
        "META": "Meta Platforms Inc.",
        "NFLX": "Netflix Inc.",
        "ADBE": "Adobe Inc.",
        "INTC": "Intel Corporation",
    },
    Market.CRYPTO: {
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "BNB": "Binance Coin",
        "ADA": "Cardano",
        "SOL": "Solana",
        "XRP": "Ripple",
        "DOT": "Polkadot",
        "DOGE": "Dogecoin",
        "MATIC": "Polygon",
        "AVAX": "Avalanche",
    }
}


def get_market_for_ticker(ticker: str) -> Market:
    """
    Auto-detect market for a ticker

    Args:
        ticker: Stock ticker or crypto symbol

    Returns:
        Market enum
    """
    # Check for crypto symbols
    ticker_upper = ticker.upper()
    if "-" in ticker or ticker.endswith("USDT") or ticker.endswith("BTC") or ticker.endswith("USD"):
        # Common crypto patterns
        crypto_bases = ["BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "DOGE", "MATIC", "AVAX", "LINK"]
        base = ticker.split("-")[0] if "-" in ticker else ticker.replace("USDT", "").replace("BTC", "").replace("USD", "")
        if base in crypto_bases or len(base) <= 5:  # Most crypto symbols are short
            return Market.CRYPTO

    # Check Indian stocks
    for market in [Market.INDIA_NSE, Market.INDIA_BSE]:
        if ticker in POPULAR_STOCKS.get(market, {}):
            return market

    # Default to US market
    return Market.US_NYSE


def is_indian_market(market: Market) -> bool:
    """Check if market is Indian"""
    return market in [Market.INDIA_NSE, Market.INDIA_BSE]


def is_us_market(market: Market) -> bool:
    """Check if market is US"""
    return market in [Market.US_NYSE, Market.US_NASDAQ, Market.US_AMEX]


def is_crypto_market(market: Market) -> bool:
    """Check if market is crypto"""
    return market == Market.CRYPTO
