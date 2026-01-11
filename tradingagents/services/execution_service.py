"""
Trade execution service to connect trading decisions to broker execution
"""

from typing import Dict, Optional, List, Any
import logging
from datetime import datetime

from dashboard.multiuser.brokers.unified_broker import (
    UnifiedBrokerInterface,
    BrokerFactory,
    BrokerType,
    Market
)
from tradingagents.utils.market_detector import MarketDetector, detect_market_and_broker
from tradingagents.services.market_hours import MarketHoursService
from tradingagents.services.bracket_orders import BracketOrderManager, BracketOrder

logger = logging.getLogger(__name__)


class TradeExecutionService:
    """Service to execute trades based on trading decisions"""

    def __init__(
        self,
        broker_configs: Dict[str, Dict] = None,
        default_broker_type: Optional[BrokerType] = None,
        paper_trading: bool = True,
        live_trading_approved: bool = False,
        enable_bracket_orders: bool = True
    ):
        """
        Initialize execution service

        Args:
            broker_configs: Dict mapping broker types to credentials
            default_broker_type: Default broker type to use if not specified
            paper_trading: Enable paper trading mode (default: True)
            live_trading_approved: Whether live trading has been explicitly approved (default: False)
            enable_bracket_orders: Enable stop-loss/take-profit bracket orders (default: True)
        """
        self.broker_configs = broker_configs or {}
        self.default_broker_type = default_broker_type
        self.brokers: Dict[BrokerType, UnifiedBrokerInterface] = {}
        self.execution_history: List[Dict] = []
        self.paper_trading = paper_trading
        self.live_trading_approved = live_trading_approved

        # Safety: Force paper trading if live trading not approved
        if not live_trading_approved:
            self.paper_trading = True
            logger.warning("Live trading not approved. Forcing paper trading mode.")
        
        # Bracket order manager for stop-loss/take-profit
        self.bracket_manager: Optional[BracketOrderManager] = None
        if enable_bracket_orders:
            self.bracket_manager = BracketOrderManager(
                execution_service=self,
                auto_start=False  # Start manually when needed
            )

    def get_broker(
        self,
        market: Market,
        preferred_broker: Optional[BrokerType] = None
    ) -> UnifiedBrokerInterface:
        """
        Get broker instance for market

        Args:
            market: Market type
            preferred_broker: Preferred broker type

        Returns:
            Broker instance
        """
        # Determine broker type
        broker_type = preferred_broker or MarketDetector.get_broker_type(market, self.default_broker_type)

        # Force paper trading for certain brokers if in paper mode
        if self.paper_trading:
            # Use simulated broker for paper trading
            if broker_type not in [BrokerType.SIMULATED]:
                logger.info(f"Paper trading mode: Using simulated broker instead of {broker_type.value}")
                broker_type = BrokerType.SIMULATED

        # Check if broker already initialized
        if broker_type in self.brokers:
            return self.brokers[broker_type]

        # Create new broker instance
        credentials = self.broker_configs.get(broker_type.value, {})
        
        # Ensure paper trading mode for brokers that support it
        if self.paper_trading:
            if broker_type == BrokerType.ALPACA:
                credentials['paper_trading'] = True
            elif broker_type == BrokerType.BINANCE:
                credentials['testnet'] = True
            elif broker_type == BrokerType.COINBASE:
                credentials['sandbox'] = True

        broker = BrokerFactory.create_broker(broker_type, credentials)
        self.brokers[broker_type] = broker

        return broker

    def parse_decision(self, decision_text: str) -> Dict[str, Any]:
        """
        Parse trading decision from text

        Args:
            decision_text: Decision text from trading graph

        Returns:
            Dict with action, symbol, and other parsed info
        """
        decision_upper = decision_text.upper().strip()

        # Extract action
        action = None
        if "BUY" in decision_upper:
            action = "BUY"
        elif "SELL" in decision_upper:
            action = "SELL"
        elif "HOLD" in decision_upper:
            action = "HOLD"
        else:
            # Default to HOLD if unclear
            action = "HOLD"

        return {
            "action": action,
            "raw_decision": decision_text,
            "confidence": self._extract_confidence(decision_text)
        }

    def _extract_confidence(self, decision_text: str) -> float:
        """Extract confidence level from decision text"""
        text_lower = decision_text.lower()
        
        if any(word in text_lower for word in ["strong", "high", "very", "extremely"]):
            return 0.8
        elif any(word in text_lower for word in ["moderate", "medium", "some"]):
            return 0.5
        elif any(word in text_lower for word in ["weak", "low", "uncertain"]):
            return 0.3
        else:
            return 0.5  # Default

    def execute_trade(
        self,
        symbol: str,
        action: str,
        quantity: Optional[float] = None,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        market: Optional[Market] = None,
        broker_type: Optional[BrokerType] = None
    ) -> Dict[str, Any]:
        """
        Execute a trade

        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Order quantity (if None, will be calculated)
            order_type: MARKET or LIMIT
            price: Limit price (for LIMIT orders)
            market: Market type (auto-detected if None)
            broker_type: Broker type (auto-selected if None)

        Returns:
            Execution result
        """
        # Safety check: Prevent live trading if not approved
        if not self.paper_trading and not self.live_trading_approved:
            return {
                "status": "error",
                "error": "Live trading not approved. Please verify paper trading first and explicitly approve live trading.",
                "symbol": symbol,
                "action": action,
                "paper_trading_required": True
            }

        try:
            # Detect market if not provided
            if market is None:
                market = MarketDetector.detect_market(symbol)

            # Check if market is open
            if not MarketHoursService.is_market_open(market):
                return {
                    "status": "error",
                    "error": f"Market {market.value} is currently closed",
                    "symbol": symbol,
                    "action": action
                }

            # Get broker
            broker = self.get_broker(market, broker_type)

            # Normalize symbol
            normalized_symbol = MarketDetector.normalize_symbol(symbol, market, broker_type or MarketDetector.get_broker_type(market))
            exchange = MarketDetector.get_exchange_for_market(market)

            # Get quote for price if needed
            if price is None and order_type == "LIMIT":
                quote = broker.get_quote(normalized_symbol, exchange)
                if "error" not in quote:
                    price = quote.get("last_price", 0)

            # Execute order
            result = broker.place_order(
                symbol=normalized_symbol,
                exchange=exchange,
                action=action,
                quantity=quantity or 1.0,  # Default to 1 if not specified
                order_type=order_type,
                price=price
            )

            # Log execution
            execution_log = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "normalized_symbol": normalized_symbol,
                "action": action,
                "quantity": quantity,
                "order_type": order_type,
                "price": price,
                "market": market.value,
                "broker": broker_type.value if broker_type else "auto",
                "paper_trading": self.paper_trading,
                "result": result
            }

            self.execution_history.append(execution_log)

            return {
                "status": "success" if result.get("status") == "success" else "error",
                "execution_log": execution_log,
                **result
            }

        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "symbol": symbol,
                "action": action
            }

    def execute_decision(
        self,
        symbol: str,
        decision_text: str,
        quantity: Optional[float] = None,
        order_type: str = "MARKET",
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute trade based on decision text

        Args:
            symbol: Trading symbol
            decision_text: Decision text from trading graph
            quantity: Order quantity
            order_type: MARKET or LIMIT
            price: Limit price

        Returns:
            Execution result
        """
        # Parse decision
        parsed = self.parse_decision(decision_text)

        if parsed["action"] == "HOLD":
            return {
                "status": "skipped",
                "reason": "HOLD decision - no trade executed",
                "symbol": symbol,
                "decision": parsed
            }

        # Execute trade
        return self.execute_trade(
            symbol=symbol,
            action=parsed["action"],
            quantity=quantity,
            order_type=order_type,
            price=price
        )

    def get_execution_history(self, limit: int = 100) -> List[Dict]:
        """Get execution history"""
        return self.execution_history[-limit:]

    def cancel_order(self, order_id: str, symbol: str, broker_type: Optional[BrokerType] = None) -> Dict:
        """
        Cancel an order

        Args:
            order_id: Order ID
            symbol: Trading symbol
            broker_type: Broker type

        Returns:
            Cancellation result
        """
        try:
            market = MarketDetector.detect_market(symbol)
            broker = self.get_broker(market, broker_type)

            result = broker.cancel_order(order_id)
            return result

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"status": "error", "error": str(e)}

    def execute_trade_with_brackets(
        self,
        symbol: str,
        action: str,
        quantity: Optional[float] = None,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        market: Optional[Market] = None,
        broker_type: Optional[BrokerType] = None,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04,
        trailing_stop_pct: Optional[float] = None,
        trailing_activation_pct: float = 0.03
    ) -> Dict[str, Any]:
        """
        Execute a trade with automatic stop-loss and take-profit bracket orders.
        
        This creates the main order plus protective orders:
        - Stop-loss: Automatically exit if price moves against you
        - Take-profit: Automatically capture gains at target price
        - Trailing stop: Move stop-loss up as price moves in your favor
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Order quantity
            order_type: MARKET or LIMIT
            price: Limit price (for LIMIT orders)
            market: Market type (auto-detected if None)
            broker_type: Broker type (auto-selected if None)
            stop_loss_pct: Stop-loss percentage (0.02 = 2%, default)
            take_profit_pct: Take-profit percentage (0.04 = 4%, default)
            trailing_stop_pct: Trailing stop percentage (optional)
            trailing_activation_pct: Activate trailing after X% profit (default 3%)
        
        Returns:
            Execution result with bracket order details
        """
        # Execute the main trade
        result = self.execute_trade(
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            price=price,
            market=market,
            broker_type=broker_type
        )
        
        if result.get("status") != "success":
            return result
        
        # Get entry price from result or use current price
        entry_price = result.get("fill_price") or result.get("price") or price
        if entry_price is None:
            # Try to get current price
            try:
                detected_market = market or MarketDetector.detect_market(symbol)
                broker = self.get_broker(detected_market, broker_type)
                normalized_symbol = MarketDetector.normalize_symbol(symbol, detected_market, broker_type or MarketDetector.get_broker_type(detected_market))
                exchange = MarketDetector.get_exchange_for_market(detected_market)
                quote = broker.get_quote(normalized_symbol, exchange)
                entry_price = quote.get("last_price", 0)
            except Exception as e:
                logger.warning(f"Could not get entry price for bracket order: {e}")
                entry_price = 100  # Fallback, will be updated later
        
        final_quantity = quantity or result.get("quantity", 1.0)
        
        # Create bracket order for stop-loss/take-profit tracking
        if self.bracket_manager:
            bracket = self.bracket_manager.create_bracket_order(
                symbol=symbol,
                entry_price=float(entry_price),
                quantity=float(final_quantity),
                action=action,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                trailing_stop_pct=trailing_stop_pct,
                trailing_activation_pct=trailing_activation_pct
            )
            
            result["bracket_order"] = {
                "id": bracket.id,
                "stop_loss_price": bracket.calculate_stop_loss_price(),
                "take_profit_price": bracket.calculate_take_profit_price(),
                "trailing_stop": trailing_stop_pct is not None
            }
            
            logger.info(
                f"Created bracket order for {symbol}: "
                f"SL @ {bracket.calculate_stop_loss_price():.2f}, "
                f"TP @ {bracket.calculate_take_profit_price():.2f}"
            )
        
        return result
    
    def start_bracket_monitoring(self, price_fetcher=None):
        """
        Start monitoring bracket orders for stop-loss/take-profit triggers.
        
        Args:
            price_fetcher: Optional function to get current prices.
                          Signature: (symbol: str) -> float
        """
        if self.bracket_manager:
            if price_fetcher:
                self.bracket_manager.price_fetcher = price_fetcher
            self.bracket_manager.start_monitoring()
            logger.info("Bracket order monitoring started")
    
    def stop_bracket_monitoring(self):
        """Stop monitoring bracket orders."""
        if self.bracket_manager:
            self.bracket_manager.stop_monitoring()
            logger.info("Bracket order monitoring stopped")
    
    def get_active_brackets(self) -> List[Dict]:
        """Get all active bracket orders."""
        if self.bracket_manager:
            brackets = self.bracket_manager.get_active_brackets()
            return [
                {
                    "id": b.id,
                    "symbol": b.symbol,
                    "action": b.action,
                    "entry_price": b.entry_price,
                    "quantity": b.quantity,
                    "stop_loss_price": b.calculate_stop_loss_price(),
                    "take_profit_price": b.calculate_take_profit_price(),
                    "trailing_stop": b.trailing_stop_pct is not None,
                    "status": b.status.value
                }
                for b in brackets
            ]
        return []
    
    def cancel_bracket(self, bracket_id: str) -> bool:
        """Cancel a bracket order."""
        if self.bracket_manager:
            return self.bracket_manager.cancel_bracket_order(bracket_id)
        return False
    
    def get_bracket_stats(self) -> Dict:
        """Get bracket order statistics."""
        if self.bracket_manager:
            return self.bracket_manager.get_stats()
        return {}

