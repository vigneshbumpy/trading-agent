"""
Binance Spot API integration for crypto trading
Documentation: https://binance-docs.github.io/apidocs/spot/en/
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class BinanceAPI:
    """Binance Spot API integration"""

    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        """
        Initialize Binance API

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (paper trading)
        """
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.testnet = testnet
        self.client = None

        self._initialize()

    def _initialize(self):
        """Initialize Binance client"""
        try:
            from binance.client import Client

            if self.testnet:
                # Use testnet for paper trading
                self.client = Client(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    testnet=True
                )
            else:
                self.client = Client(
                    api_key=self.api_key,
                    api_secret=self.api_secret
                )

        except ImportError:
            raise ImportError(
                "python-binance library not installed. "
                "Install with: pip install python-binance"
            )
        except Exception as e:
            logger.error(f"Error initializing Binance client: {e}")
            raise

    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            account = self.client.get_account()
            balances = {}
            
            for balance in account.get('balances', []):
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                if free > 0 or locked > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': free + locked
                    }

            return {
                "account_type": "SPOT",
                "balances": balances,
                "can_trade": account.get('canTrade', False),
                "can_withdraw": account.get('canWithdraw', False),
                "can_deposit": account.get('canDeposit', False)
            }
        except Exception as e:
            logger.error(f"Error fetching account info: {e}")
            return {"error": str(e)}

    def get_positions(self) -> List[Dict]:
        """Get all open positions (crypto balances)"""
        try:
            account = self.client.get_account()
            positions = []

            for balance in account.get('balances', []):
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked

                if total > 0:
                    # Get current price for the asset
                    ticker = f"{asset}USDT"
                    try:
                        ticker_price = self.client.get_symbol_ticker(symbol=ticker)
                        current_price = float(ticker_price['price'])
                    except:
                        # If USDT pair doesn't exist, try BTC pair
                        try:
                            ticker = f"{asset}BTC"
                            ticker_price = self.client.get_symbol_ticker(symbol=ticker)
                            btc_price = float(ticker_price['price'])
                            btc_usdt = float(self.client.get_symbol_ticker(symbol="BTCUSDT")['price'])
                            current_price = btc_price * btc_usdt
                        except:
                            current_price = 0

                    positions.append({
                        "symbol": asset,
                        "quantity": total,
                        "free": free,
                        "locked": locked,
                        "current_price": current_price,
                        "market_value": total * current_price if current_price > 0 else 0
                    })

            return positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_quote(self, symbol: str) -> Dict:
        """
        Get real-time quote for a symbol

        Args:
            symbol: Trading pair (e.g., "BTCUSDT", "ETHUSDT")

        Returns:
            Quote data
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            order_book = self.client.get_order_book(symbol=symbol, limit=5)
            
            bid_price = float(order_book['bids'][0][0]) if order_book['bids'] else float(ticker['price'])
            ask_price = float(order_book['asks'][0][0]) if order_book['asks'] else float(ticker['price'])
            last_price = float(ticker['price'])

            return {
                "symbol": symbol,
                "last_price": last_price,
                "bid": bid_price,
                "ask": ask_price,
                "bid_size": float(order_book['bids'][0][1]) if order_book['bids'] else 0,
                "ask_size": float(order_book['asks'][0][1]) if order_book['asks'] else 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {"error": str(e)}

    def place_order(
        self,
        symbol: str,
        side: str,  # BUY or SELL
        quantity: float = None,
        price: float = None,
        order_type: str = "MARKET"
    ) -> Dict:
        """
        Place an order

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: BUY or SELL
            quantity: Order quantity (for MARKET orders or LIMIT orders)
            price: Limit price (for LIMIT orders)
            order_type: MARKET or LIMIT

        Returns:
            Order response
        """
        try:
            from binance.enums import ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT, SIDE_BUY, SIDE_SELL

            binance_side = SIDE_BUY if side.upper() == "BUY" else SIDE_SELL

            if order_type.upper() == "MARKET":
                if not quantity:
                    return {"status": "error", "error": "Quantity required for market orders"}

                order = self.client.create_order(
                    symbol=symbol,
                    side=binance_side,
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity
                )
            else:  # LIMIT order
                if not quantity or not price:
                    return {"status": "error", "error": "Quantity and price required for limit orders"}

                order = self.client.create_order(
                    symbol=symbol,
                    side=binance_side,
                    type=ORDER_TYPE_LIMIT,
                    timeInForce='GTC',  # Good Till Cancel
                    quantity=quantity,
                    price=price
                )

            return {
                "status": "success",
                "order_id": str(order['orderId']),
                "symbol": order['symbol'],
                "side": order['side'],
                "type": order['type'],
                "quantity": float(order['executedQty']) if 'executedQty' in order else float(order['origQty']),
                "price": float(order.get('price', 0)),
                "status": order['status'],
                "message": f"Order placed successfully: {order['orderId']}"
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to place order: {str(e)}"
            }

    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order"""
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            return {
                "status": "success",
                "order_id": str(result['orderId']),
                "message": "Order cancelled successfully"
            }
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"status": "error", "error": str(e)}

    def get_orders(self, symbol: str = None) -> List[Dict]:
        """Get all open orders"""
        try:
            if symbol:
                orders = self.client.get_open_orders(symbol=symbol)
            else:
                orders = self.client.get_open_orders()

            return [
                {
                    "order_id": str(order['orderId']),
                    "symbol": order['symbol'],
                    "side": order['side'],
                    "type": order['type'],
                    "quantity": float(order['origQty']),
                    "price": float(order.get('price', 0)),
                    "status": order['status'],
                    "time": order['time']
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []

    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """Get order status"""
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return {
                "order_id": str(order['orderId']),
                "symbol": order['symbol'],
                "side": order['side'],
                "type": order['type'],
                "quantity": float(order['origQty']),
                "executed_quantity": float(order['executedQty']),
                "price": float(order.get('price', 0)),
                "status": order['status'],
                "time": order['time']
            }
        except Exception as e:
            logger.error(f"Error fetching order status: {e}")
            return {"error": str(e)}


# Helper functions for crypto markets

def convert_to_binance_symbol(base: str, quote: str = "USDT") -> str:
    """
    Convert crypto symbol to Binance format

    Args:
        base: Base currency (e.g., "BTC", "ETH")
        quote: Quote currency (default: "USDT")

    Returns:
        Binance symbol: "BTCUSDT"
    """
    return f"{base}{quote}"


def parse_binance_symbol(symbol: str) -> tuple:
    """
    Parse Binance symbol to base and quote

    Args:
        symbol: "BTCUSDT"

    Returns:
        (base, quote): ("BTC", "USDT")
    """
    # Common quote currencies
    quotes = ["USDT", "BUSD", "BTC", "ETH", "BNB", "USDC"]
    
    for quote in quotes:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            return base, quote
    
    # Default to USDT if not found
    return symbol[:-4], "USDT"


# Popular crypto pairs for reference
CRYPTO_PAIRS = {
    "BTCUSDT": "Bitcoin/USDT",
    "ETHUSDT": "Ethereum/USDT",
    "BNBUSDT": "Binance Coin/USDT",
    "ADAUSDT": "Cardano/USDT",
    "SOLUSDT": "Solana/USDT",
    "XRPUSDT": "Ripple/USDT",
    "DOTUSDT": "Polkadot/USDT",
    "DOGEUSDT": "Dogecoin/USDT",
    "MATICUSDT": "Polygon/USDT",
    "AVAXUSDT": "Avalanche/USDT",
}
