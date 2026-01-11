"""
Broker integration module supporting Alpaca API
Handles both paper trading and live trading
"""

import os
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good till canceled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill


class BrokerInterface:
    """Base interface for broker implementations"""

    def __init__(self, paper_trading: bool = True):
        self.paper_trading = paper_trading

    def get_account(self) -> Dict:
        """Get account information"""
        raise NotImplementedError

    def get_position(self, ticker: str) -> Optional[Dict]:
        """Get current position for a ticker"""
        raise NotImplementedError

    def get_all_positions(self) -> List[Dict]:
        """Get all open positions"""
        raise NotImplementedError

    def place_order(
        self,
        ticker: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None
    ) -> Dict:
        """Place an order"""
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        raise NotImplementedError

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order status"""
        raise NotImplementedError

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get current quote for a ticker"""
        raise NotImplementedError


class AlpacaBroker(BrokerInterface):
    """Alpaca broker implementation"""

    def __init__(self, paper_trading: bool = True):
        super().__init__(paper_trading)
        self.api = None
        self._initialize_api()

    def _initialize_api(self):
        """Initialize Alpaca API"""
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient

            # Get API credentials from environment
            if self.paper_trading:
                api_key = os.getenv("ALPACA_PAPER_API_KEY")
                api_secret = os.getenv("ALPACA_PAPER_SECRET_KEY")
            else:
                api_key = os.getenv("ALPACA_LIVE_API_KEY")
                api_secret = os.getenv("ALPACA_LIVE_SECRET_KEY")

            if not api_key or not api_secret:
                raise ValueError(
                    f"Alpaca API credentials not found. "
                    f"Please set {'ALPACA_PAPER' if self.paper_trading else 'ALPACA_LIVE'}_API_KEY "
                    f"and {'ALPACA_PAPER' if self.paper_trading else 'ALPACA_LIVE'}_SECRET_KEY"
                )

            # Initialize trading client
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=api_secret,
                paper=self.paper_trading
            )

            # Initialize data client
            self.data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=api_secret
            )

        except ImportError:
            raise ImportError(
                "Alpaca SDK not installed. Install with: pip install alpaca-py"
            )

    def get_account(self) -> Dict:
        """Get account information"""
        try:
            account = self.trading_client.get_account()
            return {
                "account_number": account.account_number,
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "account_blocked": account.account_blocked,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_position(self, ticker: str) -> Optional[Dict]:
        """Get current position for a ticker"""
        try:
            position = self.trading_client.get_open_position(ticker)
            return {
                "ticker": position.symbol,
                "quantity": float(position.qty),
                "avg_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "market_value": float(position.market_value),
                "cost_basis": float(position.cost_basis),
                "unrealized_pl": float(position.unrealized_pl),
                "unrealized_plpc": float(position.unrealized_plpc),
            }
        except Exception:
            return None

    def get_all_positions(self) -> List[Dict]:
        """Get all open positions"""
        try:
            positions = self.trading_client.get_all_positions()
            return [
                {
                    "ticker": pos.symbol,
                    "quantity": float(pos.qty),
                    "avg_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                }
                for pos in positions
            ]
        except Exception as e:
            return []

    def place_order(
        self,
        ticker: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None
    ) -> Dict:
        """Place an order"""
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce as AlpacaTIF

            # Convert our enums to Alpaca enums
            alpaca_side = AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
            alpaca_tif = getattr(AlpacaTIF, time_in_force.value.upper())

            # Create order request
            if order_type == OrderType.MARKET:
                order_data = MarketOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif
                )
            else:  # LIMIT order
                if not limit_price:
                    raise ValueError("Limit price required for limit orders")
                order_data = LimitOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=limit_price
                )

            # Submit order
            order = self.trading_client.submit_order(order_data)

            return {
                "order_id": str(order.id),
                "ticker": order.symbol,
                "quantity": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            return True
        except Exception:
            return False

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order status"""
        try:
            order = self.trading_client.get_order_by_id(order_id)
            return {
                "order_id": str(order.id),
                "ticker": order.symbol,
                "quantity": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            }
        except Exception:
            return None

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get current quote for a ticker"""
        try:
            from alpaca.data.requests import StockLatestQuoteRequest

            request = StockLatestQuoteRequest(symbol_or_symbols=ticker)
            quotes = self.data_client.get_stock_latest_quote(request)
            quote = quotes[ticker]

            return {
                "ticker": ticker,
                "bid_price": float(quote.bid_price),
                "ask_price": float(quote.ask_price),
                "bid_size": int(quote.bid_size),
                "ask_size": int(quote.ask_size),
                "timestamp": quote.timestamp.isoformat() if quote.timestamp else None,
            }
        except Exception:
            return None


class PaperBroker(BrokerInterface):
    """Simulated paper trading broker (no external API)"""

    def __init__(self):
        super().__init__(paper_trading=True)
        self.cash = 100000.0  # Starting cash
        self.positions = {}  # {ticker: {"quantity": float, "avg_price": float}}
        self.orders = {}  # {order_id: order_dict}
        self.order_counter = 1

    def get_account(self) -> Dict:
        """Get simulated account information"""
        portfolio_value = self.cash
        for ticker, pos in self.positions.items():
            # For simulation, use avg_price as current price
            portfolio_value += pos["quantity"] * pos["avg_price"]

        return {
            "account_number": "PAPER_SIM",
            "cash": self.cash,
            "portfolio_value": portfolio_value,
            "buying_power": self.cash,
            "equity": portfolio_value,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
        }

    def get_position(self, ticker: str) -> Optional[Dict]:
        """Get simulated position"""
        if ticker not in self.positions:
            return None

        pos = self.positions[ticker]
        current_price = pos["avg_price"]  # Simplified simulation

        return {
            "ticker": ticker,
            "quantity": pos["quantity"],
            "avg_price": pos["avg_price"],
            "current_price": current_price,
            "market_value": pos["quantity"] * current_price,
            "cost_basis": pos["quantity"] * pos["avg_price"],
            "unrealized_pl": pos["quantity"] * (current_price - pos["avg_price"]),
            "unrealized_plpc": ((current_price / pos["avg_price"]) - 1) * 100,
        }

    def get_all_positions(self) -> List[Dict]:
        """Get all simulated positions"""
        return [self.get_position(ticker) for ticker in self.positions.keys()]

    def place_order(
        self,
        ticker: str,
        quantity: float,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: Optional[float] = None
    ) -> Dict:
        """Place a simulated order"""
        # Use limit price if provided, otherwise use a dummy price
        price = limit_price if limit_price else 100.0

        order_id = f"SIM_{self.order_counter}"
        self.order_counter += 1

        # Simulate immediate execution
        if side == OrderSide.BUY:
            total_cost = quantity * price
            if total_cost > self.cash:
                return {"error": "Insufficient funds"}

            self.cash -= total_cost
            if ticker in self.positions:
                old_qty = self.positions[ticker]["quantity"]
                old_avg = self.positions[ticker]["avg_price"]
                new_qty = old_qty + quantity
                new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
                self.positions[ticker] = {"quantity": new_qty, "avg_price": new_avg}
            else:
                self.positions[ticker] = {"quantity": quantity, "avg_price": price}

        else:  # SELL
            if ticker not in self.positions or self.positions[ticker]["quantity"] < quantity:
                return {"error": "Insufficient shares"}

            self.cash += quantity * price
            self.positions[ticker]["quantity"] -= quantity

            if self.positions[ticker]["quantity"] == 0:
                del self.positions[ticker]

        order = {
            "order_id": order_id,
            "ticker": ticker,
            "quantity": quantity,
            "side": side.value,
            "type": order_type.value,
            "status": "filled",
            "submitted_at": datetime.now().isoformat(),
            "filled_avg_price": price,
        }

        self.orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        """Cancel simulated order (always returns False as orders execute immediately)"""
        return False

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get simulated order"""
        return self.orders.get(order_id)

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get simulated quote"""
        # Return dummy quote
        return {
            "ticker": ticker,
            "bid_price": 100.0,
            "ask_price": 100.05,
            "bid_size": 100,
            "ask_size": 100,
            "timestamp": datetime.now().isoformat(),
        }


def get_broker(paper_trading: bool = True, use_alpaca: bool = False) -> BrokerInterface:
    """Factory function to get appropriate broker instance"""
    if use_alpaca:
        return AlpacaBroker(paper_trading=paper_trading)
    else:
        return PaperBroker()
