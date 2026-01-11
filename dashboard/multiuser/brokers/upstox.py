"""
Upstox API integration for Indian stock trading
FREE API with no subscription fees (alternative to Zerodha)
Documentation: https://upstox.com/developer/api-documentation/
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class UpstoxAPI:
    """Upstox API integration"""

    def __init__(self, api_key: str, api_secret: str = None, access_token: str = None):
        """
        Initialize Upstox API

        Args:
            api_key: Upstox API key
            api_secret: Upstox API secret
            access_token: Access token (if already authenticated)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.upstox = None

        self._initialize()

    def _initialize(self):
        """Initialize Upstox connection"""
        try:
            from upstox_client import Configuration, ApiClient
            from upstox_client.api import LoginApi, OrderApi, PortfolioApi, MarketDataApi

            config = Configuration()
            config.access_token = self.access_token

            self.api_client = ApiClient(config)
            self.login_api = LoginApi(self.api_client)
            self.order_api = OrderApi(self.api_client)
            self.portfolio_api = PortfolioApi(self.api_client)
            self.market_api = MarketDataApi(self.api_client)

        except ImportError:
            raise ImportError(
                "Upstox library not installed. "
                "Install with: pip install upstox-python-sdk"
            )

    def get_profile(self) -> Dict:
        """Get user profile"""
        try:
            response = self.login_api.get_profile()
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            return {"error": str(e)}

    def get_funds(self) -> Dict:
        """Get account funds and margins"""
        try:
            response = self.portfolio_api.get_user_fund_margin()
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error fetching funds: {e}")
            return {"error": str(e)}

    def get_positions(self) -> Dict:
        """Get current positions"""
        try:
            response = self.portfolio_api.get_positions()
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return {"error": str(e)}

    def get_holdings(self) -> List[Dict]:
        """Get holdings"""
        try:
            response = self.portfolio_api.get_holdings()
            return response.to_dict().get('data', [])
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []

    def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict:
        """
        Get quote for symbol

        Args:
            symbol: Stock symbol
            exchange: Exchange (NSE/BSE)

        Returns:
            Quote data
        """
        try:
            instrument_key = f"{exchange}_{symbol}"
            response = self.market_api.get_market_quote_ohlc(instrument_key)
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return {"error": str(e)}

    def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        product: str = "D",  # D=Delivery, I=Intraday
        price: float = None,
        trigger_price: float = None
    ) -> Dict:
        """
        Place an order

        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE/BSE)
            transaction_type: BUY/SELL
            quantity: Order quantity
            order_type: MARKET/LIMIT
            product: D (Delivery) / I (Intraday)
            price: Limit price
            trigger_price: Stop loss trigger price

        Returns:
            Order response
        """
        try:
            from upstox_client.models import PlaceOrderRequest

            order_request = PlaceOrderRequest(
                quantity=quantity,
                product=product,
                validity="DAY",
                price=price or 0,
                tag="TradingAgents",
                instrument_token=f"{exchange}_{symbol}",
                order_type=order_type,
                transaction_type=transaction_type,
                disclosed_quantity=0,
                trigger_price=trigger_price or 0,
                is_amo=False
            )

            response = self.order_api.place_order(order_request)
            return {
                "status": "success",
                "order_id": response.to_dict().get('data', {}).get('order_id'),
                "message": "Order placed successfully"
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
            response = self.order_api.cancel_order(order_id)
            return {
                "status": "success",
                "message": "Order cancelled successfully"
            }
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"status": "error", "error": str(e)}

    def get_orders(self) -> List[Dict]:
        """Get order book"""
        try:
            response = self.order_api.get_order_book()
            return response.to_dict().get('data', [])
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []

    def get_trades(self) -> List[Dict]:
        """Get trade book"""
        try:
            response = self.order_api.get_trade_book()
            return response.to_dict().get('data', [])
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
