"""
Zerodha Kite API integration for Indian stock trading
Documentation: https://kite.trade/docs/connect/v3/
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ZerodhaKiteAPI:
    """Zerodha Kite API integration"""

    def __init__(self, api_key: str, api_secret: str = None, access_token: str = None):
        """
        Initialize Zerodha Kite API

        Args:
            api_key: Kite API key
            api_secret: Kite API secret
            access_token: Access token (if already authenticated)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.kite = None

        self._initialize()

    def _initialize(self):
        """Initialize Kite connection"""
        try:
            from kiteconnect import KiteConnect

            self.kite = KiteConnect(api_key=self.api_key)

            if self.access_token:
                self.kite.set_access_token(self.access_token)

        except ImportError:
            raise ImportError(
                "Kite Connect library not installed. "
                "Install with: pip install kiteconnect"
            )

    def get_login_url(self) -> str:
        """
        Get login URL for user authentication

        Returns:
            Login URL
        """
        return self.kite.login_url()

    def generate_session(self, request_token: str) -> Dict:
        """
        Generate access token from request token

        Args:
            request_token: Request token from login callback

        Returns:
            Session data with access_token
        """
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data['access_token']
            self.kite.set_access_token(self.access_token)

            return data

        except Exception as e:
            logger.error(f"Error generating session: {e}")
            raise

    def get_profile(self) -> Dict:
        """Get user profile"""
        try:
            return self.kite.profile()
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            return {"error": str(e)}

    def get_margins(self) -> Dict:
        """Get account margins"""
        try:
            return self.kite.margins()
        except Exception as e:
            logger.error(f"Error fetching margins: {e}")
            return {"error": str(e)}

    def get_positions(self) -> Dict:
        """Get current positions"""
        try:
            return self.kite.positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return {"error": str(e)}

    def get_holdings(self) -> List[Dict]:
        """Get holdings (long-term investments)"""
        try:
            return self.kite.holdings()
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []

    def get_quote(self, instruments: List[str]) -> Dict:
        """
        Get real-time quotes for instruments

        Args:
            instruments: List of instruments (e.g., ["NSE:INFY", "BSE:SENSEX"])

        Returns:
            Quote data
        """
        try:
            return self.kite.quote(instruments)
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return {"error": str(e)}

    def get_ltp(self, instruments: List[str]) -> Dict:
        """
        Get last traded price

        Args:
            instruments: List of instruments

        Returns:
            LTP data
        """
        try:
            return self.kite.ltp(instruments)
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}")
            return {"error": str(e)}

    def place_order(
        self,
        tradingsymbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        product: str = "CNC",
        price: float = None,
        trigger_price: float = None,
        validity: str = "DAY"
    ) -> Dict:
        """
        Place an order

        Args:
            tradingsymbol: Trading symbol (e.g., "INFY", "RELIANCE")
            exchange: Exchange (NSE/BSE)
            transaction_type: BUY/SELL
            quantity: Order quantity
            order_type: MARKET/LIMIT/SL/SL-M
            product: CNC/MIS/NRML
            price: Order price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)
            validity: DAY/IOC

        Returns:
            Order response with order_id
        """
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=product,
                order_type=order_type,
                price=price,
                trigger_price=trigger_price,
                validity=validity
            )

            return {
                "status": "success",
                "order_id": order_id,
                "message": f"Order placed successfully: {order_id}"
            }

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to place order: {str(e)}"
            }

    def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        price: float = None,
        order_type: str = None,
        trigger_price: float = None,
        validity: str = None
    ) -> Dict:
        """Modify an existing order"""
        try:
            self.kite.modify_order(
                variety=self.kite.VARIETY_REGULAR,
                order_id=order_id,
                quantity=quantity,
                price=price,
                order_type=order_type,
                trigger_price=trigger_price,
                validity=validity
            )

            return {
                "status": "success",
                "order_id": order_id,
                "message": "Order modified successfully"
            }

        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            return {"status": "error", "error": str(e)}

    def cancel_order(self, order_id: str, variety: str = "regular") -> Dict:
        """Cancel an order"""
        try:
            self.kite.cancel_order(
                variety=variety,
                order_id=order_id
            )

            return {
                "status": "success",
                "order_id": order_id,
                "message": "Order cancelled successfully"
            }

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"status": "error", "error": str(e)}

    def get_orders(self) -> List[Dict]:
        """Get all orders for the day"""
        try:
            return self.kite.orders()
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []

    def get_order_history(self, order_id: str) -> List[Dict]:
        """Get order history"""
        try:
            return self.kite.order_history(order_id)
        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            return []

    def get_trades(self) -> List[Dict]:
        """Get all trades for the day"""
        try:
            return self.kite.trades()
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []

    def get_instruments(self, exchange: str = None) -> List[Dict]:
        """
        Get instrument master

        Args:
            exchange: Exchange (NSE/BSE/NFO/CDS/MCX)

        Returns:
            List of instruments
        """
        try:
            return self.kite.instruments(exchange)
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return []

    def get_historical_data(
        self,
        instrument_token: int,
        from_date: str,
        to_date: str,
        interval: str
    ) -> List[Dict]:
        """
        Get historical candle data

        Args:
            instrument_token: Instrument token
            from_date: From date (YYYY-MM-DD)
            to_date: To date (YYYY-MM-DD)
            interval: Candle interval (minute/day/3minute/5minute/10minute/15minute/30minute/60minute)

        Returns:
            Historical candle data
        """
        try:
            return self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []


# Helper functions for Indian markets

def convert_to_kite_symbol(ticker: str, exchange: str = "NSE") -> str:
    """
    Convert standard ticker to Kite format

    Args:
        ticker: Stock ticker (e.g., "INFY", "RELIANCE")
        exchange: Exchange (NSE/BSE)

    Returns:
        Kite format: "NSE:INFY"
    """
    return f"{exchange}:{ticker}"


def parse_kite_symbol(kite_symbol: str) -> tuple:
    """
    Parse Kite symbol to exchange and ticker

    Args:
        kite_symbol: "NSE:INFY"

    Returns:
        (exchange, ticker): ("NSE", "INFY")
    """
    parts = kite_symbol.split(":")
    if len(parts) == 2:
        return parts[0], parts[1]
    return "NSE", kite_symbol


# Popular Indian stocks for reference
INDIAN_STOCKS = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "HINDUNILVR": "Hindustan Unilever",
    "ICICIBANK": "ICICI Bank",
    "BHARTIARTL": "Bharti Airtel",
    "SBIN": "State Bank of India",
    "BAJFINANCE": "Bajaj Finance",
    "ITC": "ITC Limited",
    "WIPRO": "Wipro",
    "MARUTI": "Maruti Suzuki",
    "ASIANPAINT": "Asian Paints",
    "HCLTECH": "HCL Technologies",
    "KOTAKBANK": "Kotak Mahindra Bank",
}
