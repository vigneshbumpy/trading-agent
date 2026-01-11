"""
Coinbase Advanced Trade API integration for crypto trading
Documentation: https://docs.cloud.coinbase.com/advanced-trade/docs
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import os
import hmac
import hashlib
import time
import base64
import requests

logger = logging.getLogger(__name__)


class CoinbaseAPI:
    """Coinbase Advanced Trade API integration"""

    def __init__(self, api_key: str = None, api_secret: str = None, sandbox: bool = True):
        """
        Initialize Coinbase API

        Args:
            api_key: Coinbase API key
            api_secret: Coinbase API secret
            sandbox: Use sandbox (paper trading)
        """
        self.api_key = api_key or os.getenv("COINBASE_API_KEY")
        self.api_secret = api_secret or os.getenv("COINBASE_API_SECRET")
        self.sandbox = sandbox
        
        if self.sandbox:
            self.base_url = "https://api.coinbase.com/api/v3/brokerage"
        else:
            self.base_url = "https://api.coinbase.com/api/v3/brokerage"

        if not self.api_key or not self.api_secret:
            logger.warning("Coinbase API credentials not provided. Some functions may not work.")

    def _generate_signature(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate Coinbase API signature"""
        timestamp = str(int(time.time()))
        message = timestamp + method + path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')

        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature_b64,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, path: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        url = f"{self.base_url}{path}"
        body = ""
        
        if data:
            import json
            body = json.dumps(data)
        
        if params:
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            path = f"{path}?{query_string}"

        headers = self._generate_signature(method, path, body)

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return {"error": str(e)}

    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            response = self._make_request("GET", "/accounts")
            
            if "error" in response:
                return response

            accounts = response.get("accounts", [])
            balances = {}
            total_balance = 0

            for account in accounts:
                currency = account.get("currency", {})
                currency_code = currency.get("code", "")
                available = float(account.get("available_balance", {}).get("value", 0))
                hold = float(account.get("hold", {}).get("value", 0))
                total = available + hold

                if total > 0:
                    balances[currency_code] = {
                        "available": available,
                        "hold": hold,
                        "total": total
                    }
                    total_balance += total

            return {
                "accounts": accounts,
                "balances": balances,
                "total_balance": total_balance
            }
        except Exception as e:
            logger.error(f"Error fetching account info: {e}")
            return {"error": str(e)}

    def get_positions(self) -> List[Dict]:
        """Get all open positions (crypto balances)"""
        try:
            response = self._make_request("GET", "/accounts")
            
            if "error" in response:
                return []

            positions = []
            accounts = response.get("accounts", [])

            for account in accounts:
                currency = account.get("currency", {})
                currency_code = currency.get("code", "")
                available = float(account.get("available_balance", {}).get("value", 0))
                hold = float(account.get("hold", {}).get("value", 0))
                total = available + hold

                if total > 0:
                    # Get current price
                    ticker = f"{currency_code}-USD"
                    try:
                        ticker_data = self.get_quote(ticker)
                        current_price = ticker_data.get("last_price", 0)
                    except:
                        current_price = 0

                    positions.append({
                        "symbol": currency_code,
                        "quantity": total,
                        "available": available,
                        "hold": hold,
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
            symbol: Trading pair (e.g., "BTC-USD", "ETH-USD")

        Returns:
            Quote data
        """
        try:
            # Coinbase uses format like "BTC-USD"
            product_id = symbol.replace("-", "-")  # Ensure correct format
            
            response = self._make_request("GET", f"/products/{product_id}/ticker")
            
            if "error" in response:
                return response

            ticker = response.get("ticker", {})
            
            return {
                "symbol": symbol,
                "last_price": float(ticker.get("price", 0)),
                "bid": float(ticker.get("bid", 0)),
                "ask": float(ticker.get("ask", 0)),
                "volume": float(ticker.get("volume", 0)),
                "timestamp": ticker.get("time", datetime.now().isoformat())
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
            symbol: Trading pair (e.g., "BTC-USD")
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price (for LIMIT orders)
            order_type: MARKET or LIMIT

        Returns:
            Order response
        """
        try:
            # Convert symbol format (BTC-USD)
            product_id = symbol.replace("-", "-")
            
            # Convert side
            order_side = "BUY" if side.upper() == "BUY" else "SELL"

            if order_type.upper() == "MARKET":
                if not quantity:
                    return {"status": "error", "error": "Quantity required for market orders"}

                order_config = {
                    "product_id": product_id,
                    "side": order_side,
                    "order_configuration": {
                        "market_market_ioc": {
                            "quote_size": str(quantity) if order_side == "BUY" else None,
                            "base_size": str(quantity) if order_side == "SELL" else None
                        }
                    }
                }
            else:  # LIMIT order
                if not quantity or not price:
                    return {"status": "error", "error": "Quantity and price required for limit orders"}

                order_config = {
                    "product_id": product_id,
                    "side": order_side,
                    "order_configuration": {
                        "limit_limit_gtc": {
                            "base_size": str(quantity),
                            "limit_price": str(price)
                        }
                    }
                }

            response = self._make_request("POST", "/orders", data=order_config)
            
            if "error" in response:
                return {
                    "status": "error",
                    "error": response.get("error", "Unknown error"),
                    "message": f"Failed to place order: {response.get('error')}"
                }

            order = response.get("order", {})
            
            return {
                "status": "success",
                "order_id": order.get("order_id", ""),
                "symbol": product_id,
                "side": order_side,
                "type": order_type,
                "quantity": quantity,
                "price": price if price else 0,
                "status": order.get("status", "PENDING"),
                "message": f"Order placed successfully: {order.get('order_id')}"
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to place order: {str(e)}"
            }

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        try:
            response = self._make_request("DELETE", f"/orders/{order_id}")
            
            if "error" in response:
                return {"status": "error", "error": response.get("error")}

            return {
                "status": "success",
                "order_id": order_id,
                "message": "Order cancelled successfully"
            }
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"status": "error", "error": str(e)}

    def get_orders(self, product_id: str = None) -> List[Dict]:
        """Get all open orders"""
        try:
            params = {}
            if product_id:
                params["product_id"] = product_id

            response = self._make_request("GET", "/orders/historical/batch", params=params)
            
            if "error" in response:
                return []

            orders = response.get("orders", [])
            
            return [
                {
                    "order_id": order.get("order_id", ""),
                    "product_id": order.get("product_id", ""),
                    "side": order.get("side", ""),
                    "type": order.get("order_configuration", {}).get("limit_limit_gtc") and "LIMIT" or "MARKET",
                    "quantity": float(order.get("order_configuration", {}).get("limit_limit_gtc", {}).get("base_size", 0)),
                    "price": float(order.get("order_configuration", {}).get("limit_limit_gtc", {}).get("limit_price", 0)),
                    "status": order.get("status", ""),
                    "time": order.get("creation_time", "")
                }
                for order in orders
                if order.get("status") in ["OPEN", "PENDING"]
            ]
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []

    def get_order_status(self, order_id: str) -> Dict:
        """Get order status"""
        try:
            response = self._make_request("GET", f"/orders/historical/{order_id}")
            
            if "error" in response:
                return response

            order = response.get("order", {})
            
            return {
                "order_id": order.get("order_id", ""),
                "product_id": order.get("product_id", ""),
                "side": order.get("side", ""),
                "status": order.get("status", ""),
                "filled_size": float(order.get("filled_size", 0)),
                "time": order.get("creation_time", "")
            }
        except Exception as e:
            logger.error(f"Error fetching order status: {e}")
            return {"error": str(e)}


# Helper functions for Coinbase

def convert_to_coinbase_symbol(base: str, quote: str = "USD") -> str:
    """
    Convert crypto symbol to Coinbase format

    Args:
        base: Base currency (e.g., "BTC", "ETH")
        quote: Quote currency (default: "USD")

    Returns:
        Coinbase symbol: "BTC-USD"
    """
    return f"{base}-{quote}"


def parse_coinbase_symbol(symbol: str) -> tuple:
    """
    Parse Coinbase symbol to base and quote

    Args:
        symbol: "BTC-USD"

    Returns:
        (base, quote): ("BTC", "USD")
    """
    parts = symbol.split("-")
    if len(parts) == 2:
        return parts[0], parts[1]
    return symbol, "USD"


# Popular crypto pairs for Coinbase
COINBASE_PAIRS = {
    "BTC-USD": "Bitcoin/USD",
    "ETH-USD": "Ethereum/USD",
    "ADA-USD": "Cardano/USD",
    "SOL-USD": "Solana/USD",
    "XRP-USD": "Ripple/USD",
    "DOT-USD": "Polkadot/USD",
    "DOGE-USD": "Dogecoin/USD",
    "MATIC-USD": "Polygon/USD",
    "AVAX-USD": "Avalanche/USD",
    "LINK-USD": "Chainlink/USD",
}
