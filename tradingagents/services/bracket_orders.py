"""
Bracket Order Manager - Stop-Loss and Take-Profit Functionality

Manages bracket orders (OCO - One Cancels Other) for risk management:
- Stop-loss orders to limit downside
- Take-profit orders to lock in gains
- Trailing stops to protect profits as price moves favorably
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    FILLED = "filled"


@dataclass
class BracketOrder:
    """Represents a bracket order with stop-loss and take-profit"""
    id: str
    symbol: str
    entry_price: float
    quantity: float
    action: str  # BUY or SELL
    
    # Stop-loss
    stop_loss_price: Optional[float] = None
    stop_loss_pct: Optional[float] = None  # As decimal (0.02 = 2%)
    
    # Take-profit
    take_profit_price: Optional[float] = None
    take_profit_pct: Optional[float] = None  # As decimal (0.04 = 4%)
    
    # Trailing stop
    trailing_stop_pct: Optional[float] = None  # As decimal
    trailing_stop_activation_pct: Optional[float] = None  # Activate after X% profit
    highest_price: Optional[float] = None  # Track highest for trailing
    lowest_price: Optional[float] = None   # Track lowest for trailing (shorts)
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    stop_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None
    trigger_reason: Optional[str] = None
    
    def calculate_stop_loss_price(self) -> Optional[float]:
        """Calculate stop-loss price from percentage"""
        if self.stop_loss_price:
            return self.stop_loss_price
        if self.stop_loss_pct and self.entry_price:
            if self.action == "BUY":
                return self.entry_price * (1 - self.stop_loss_pct)
            else:  # Short position
                return self.entry_price * (1 + self.stop_loss_pct)
        return None
    
    def calculate_take_profit_price(self) -> Optional[float]:
        """Calculate take-profit price from percentage"""
        if self.take_profit_price:
            return self.take_profit_price
        if self.take_profit_pct and self.entry_price:
            if self.action == "BUY":
                return self.entry_price * (1 + self.take_profit_pct)
            else:  # Short position
                return self.entry_price * (1 - self.take_profit_pct)
        return None
    
    def update_trailing_stop(self, current_price: float) -> Optional[float]:
        """Update trailing stop based on current price"""
        if not self.trailing_stop_pct:
            return None
        
        # Check if trailing stop should be activated
        if self.trailing_stop_activation_pct:
            if self.action == "BUY":
                profit_pct = (current_price - self.entry_price) / self.entry_price
                if profit_pct < self.trailing_stop_activation_pct:
                    return None  # Not activated yet
            else:  # Short
                profit_pct = (self.entry_price - current_price) / self.entry_price
                if profit_pct < self.trailing_stop_activation_pct:
                    return None
        
        if self.action == "BUY":
            # For long positions, track highest price
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price
            
            # Trailing stop is X% below the highest price
            new_stop = self.highest_price * (1 - self.trailing_stop_pct)
            
            # Only move stop up, never down
            current_stop = self.stop_loss_price or self.calculate_stop_loss_price() or 0
            if new_stop > current_stop:
                self.stop_loss_price = new_stop
                return new_stop
        else:  # Short position
            # For short positions, track lowest price
            if self.lowest_price is None or current_price < self.lowest_price:
                self.lowest_price = current_price
            
            # Trailing stop is X% above the lowest price
            new_stop = self.lowest_price * (1 + self.trailing_stop_pct)
            
            # Only move stop down, never up
            current_stop = self.stop_loss_price or self.calculate_stop_loss_price() or float('inf')
            if new_stop < current_stop:
                self.stop_loss_price = new_stop
                return new_stop
        
        return None
    
    def check_triggered(self, current_price: float) -> Optional[str]:
        """Check if stop-loss or take-profit has been triggered
        
        Returns:
            'stop_loss', 'take_profit', or None
        """
        stop_price = self.stop_loss_price or self.calculate_stop_loss_price()
        tp_price = self.take_profit_price or self.calculate_take_profit_price()
        
        if self.action == "BUY":
            # Long position
            if stop_price and current_price <= stop_price:
                return "stop_loss"
            if tp_price and current_price >= tp_price:
                return "take_profit"
        else:
            # Short position
            if stop_price and current_price >= stop_price:
                return "stop_loss"
            if tp_price and current_price <= tp_price:
                return "take_profit"
        
        return None


class BracketOrderManager:
    """Manages bracket orders with stop-loss, take-profit, and trailing stops"""
    
    def __init__(
        self,
        execution_service=None,
        price_fetcher: Callable[[str], float] = None,
        check_interval: float = 5.0,  # Check every 5 seconds
        auto_start: bool = False
    ):
        """
        Initialize bracket order manager
        
        Args:
            execution_service: TradeExecutionService for executing stop/TP orders
            price_fetcher: Function to get current price for a symbol
            check_interval: How often to check prices (seconds)
            auto_start: Start monitoring thread automatically
        """
        self.execution_service = execution_service
        self.price_fetcher = price_fetcher
        self.check_interval = check_interval
        
        # Active bracket orders
        self.bracket_orders: Dict[str, BracketOrder] = {}  # id -> BracketOrder
        self.symbol_orders: Dict[str, List[str]] = {}  # symbol -> [order_ids]
        
        # Callbacks
        self.on_stop_loss: Optional[Callable[[BracketOrder, float], None]] = None
        self.on_take_profit: Optional[Callable[[BracketOrder, float], None]] = None
        self.on_trailing_update: Optional[Callable[[BracketOrder, float], None]] = None
        
        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Stats
        self.stats = {
            "total_brackets": 0,
            "stop_losses_triggered": 0,
            "take_profits_triggered": 0,
            "trailing_stops_updated": 0
        }
        
        if auto_start:
            self.start_monitoring()
    
    def create_bracket_order(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        action: str,
        stop_loss_pct: float = 0.02,  # 2% default
        take_profit_pct: float = 0.04,  # 4% default
        trailing_stop_pct: Optional[float] = None,
        trailing_activation_pct: Optional[float] = 0.03,  # Activate after 3% profit
        order_id: Optional[str] = None
    ) -> BracketOrder:
        """
        Create a new bracket order
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price of the position
            quantity: Position quantity
            action: BUY or SELL
            stop_loss_pct: Stop-loss percentage (0.02 = 2%)
            take_profit_pct: Take-profit percentage (0.04 = 4%)
            trailing_stop_pct: Trailing stop percentage (optional)
            trailing_activation_pct: Activate trailing after X% profit
            order_id: Optional custom order ID
        
        Returns:
            BracketOrder instance
        """
        bracket_id = order_id or f"bracket_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        bracket = BracketOrder(
            id=bracket_id,
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            action=action,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            trailing_stop_pct=trailing_stop_pct,
            trailing_stop_activation_pct=trailing_activation_pct,
            status=OrderStatus.ACTIVE,
            highest_price=entry_price if action == "BUY" else None,
            lowest_price=entry_price if action == "SELL" else None
        )
        
        with self._lock:
            self.bracket_orders[bracket_id] = bracket
            
            if symbol not in self.symbol_orders:
                self.symbol_orders[symbol] = []
            self.symbol_orders[symbol].append(bracket_id)
            
            self.stats["total_brackets"] += 1
        
        logger.info(
            f"Created bracket order {bracket_id}: {action} {quantity} {symbol} @ {entry_price} | "
            f"SL: {bracket.calculate_stop_loss_price():.2f} | TP: {bracket.calculate_take_profit_price():.2f}"
        )
        
        return bracket
    
    def cancel_bracket_order(self, bracket_id: str) -> bool:
        """Cancel a bracket order"""
        with self._lock:
            if bracket_id in self.bracket_orders:
                bracket = self.bracket_orders[bracket_id]
                bracket.status = OrderStatus.CANCELLED
                
                # Remove from symbol tracking
                if bracket.symbol in self.symbol_orders:
                    if bracket_id in self.symbol_orders[bracket.symbol]:
                        self.symbol_orders[bracket.symbol].remove(bracket_id)
                
                del self.bracket_orders[bracket_id]
                logger.info(f"Cancelled bracket order {bracket_id}")
                return True
        return False
    
    def update_prices(self, prices: Dict[str, float]):
        """
        Update prices and check for triggered orders
        
        Args:
            prices: Dict of symbol -> current_price
        """
        triggered = []
        
        with self._lock:
            for bracket_id, bracket in list(self.bracket_orders.items()):
                if bracket.status != OrderStatus.ACTIVE:
                    continue
                
                if bracket.symbol not in prices:
                    continue
                
                current_price = prices[bracket.symbol]
                
                # Update trailing stop if applicable
                if bracket.trailing_stop_pct:
                    new_stop = bracket.update_trailing_stop(current_price)
                    if new_stop:
                        self.stats["trailing_stops_updated"] += 1
                        logger.info(f"Trailing stop updated for {bracket.symbol}: {new_stop:.2f}")
                        if self.on_trailing_update:
                            self.on_trailing_update(bracket, new_stop)
                
                # Check if triggered
                trigger = bracket.check_triggered(current_price)
                if trigger:
                    bracket.status = OrderStatus.TRIGGERED
                    bracket.triggered_at = datetime.now()
                    bracket.trigger_reason = trigger
                    triggered.append((bracket, current_price, trigger))
        
        # Execute triggered orders (outside lock)
        for bracket, price, trigger in triggered:
            self._execute_exit(bracket, price, trigger)
    
    def _execute_exit(self, bracket: BracketOrder, current_price: float, trigger: str):
        """Execute stop-loss or take-profit exit"""
        exit_action = "SELL" if bracket.action == "BUY" else "BUY"
        
        logger.info(
            f"🔔 {trigger.upper()} triggered for {bracket.symbol}: "
            f"Entry: {bracket.entry_price:.2f} -> Exit: {current_price:.2f}"
        )
        
        # Calculate P&L
        if bracket.action == "BUY":
            pnl = (current_price - bracket.entry_price) * bracket.quantity
            pnl_pct = (current_price - bracket.entry_price) / bracket.entry_price * 100
        else:
            pnl = (bracket.entry_price - current_price) * bracket.quantity
            pnl_pct = (bracket.entry_price - current_price) / bracket.entry_price * 100
        
        logger.info(f"   P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
        
        # Update stats
        if trigger == "stop_loss":
            self.stats["stop_losses_triggered"] += 1
            if self.on_stop_loss:
                self.on_stop_loss(bracket, current_price)
        else:
            self.stats["take_profits_triggered"] += 1
            if self.on_take_profit:
                self.on_take_profit(bracket, current_price)
        
        # Execute exit trade if execution service available
        if self.execution_service:
            result = self.execution_service.execute_trade(
                symbol=bracket.symbol,
                action=exit_action,
                quantity=bracket.quantity,
                order_type="MARKET"
            )
            
            if result.get("status") == "success":
                bracket.status = OrderStatus.FILLED
                logger.info(f"✅ Exit order filled for {bracket.symbol}")
            else:
                logger.error(f"❌ Exit order failed: {result.get('error')}")
        else:
            bracket.status = OrderStatus.FILLED  # Simulated fill
        
        # Clean up
        with self._lock:
            if bracket.id in self.bracket_orders:
                del self.bracket_orders[bracket.id]
            if bracket.symbol in self.symbol_orders:
                if bracket.id in self.symbol_orders[bracket.symbol]:
                    self.symbol_orders[bracket.symbol].remove(bracket.id)
    
    def start_monitoring(self):
        """Start the price monitoring thread"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Bracket order monitoring started")
    
    def stop_monitoring(self):
        """Stop the price monitoring thread"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        logger.info("Bracket order monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                if self.price_fetcher and self.bracket_orders:
                    # Get unique symbols
                    symbols = set(b.symbol for b in self.bracket_orders.values() if b.status == OrderStatus.ACTIVE)
                    
                    # Fetch prices
                    prices = {}
                    for symbol in symbols:
                        try:
                            price = self.price_fetcher(symbol)
                            if price and price > 0:
                                prices[symbol] = price
                        except Exception as e:
                            logger.warning(f"Failed to get price for {symbol}: {e}")
                    
                    # Update and check triggers
                    if prices:
                        self.update_prices(prices)
                
            except Exception as e:
                logger.error(f"Error in bracket monitoring: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    def get_active_brackets(self) -> List[BracketOrder]:
        """Get all active bracket orders"""
        with self._lock:
            return [b for b in self.bracket_orders.values() if b.status == OrderStatus.ACTIVE]
    
    def get_bracket_for_symbol(self, symbol: str) -> Optional[BracketOrder]:
        """Get active bracket order for a symbol"""
        with self._lock:
            if symbol in self.symbol_orders:
                for bracket_id in self.symbol_orders[symbol]:
                    if bracket_id in self.bracket_orders:
                        bracket = self.bracket_orders[bracket_id]
                        if bracket.status == OrderStatus.ACTIVE:
                            return bracket
        return None
    
    def get_stats(self) -> Dict:
        """Get bracket order statistics"""
        return {
            **self.stats,
            "active_brackets": len([b for b in self.bracket_orders.values() if b.status == OrderStatus.ACTIVE])
        }


def create_bracket_manager(
    execution_service=None,
    config: Dict = None
) -> BracketOrderManager:
    """
    Factory function to create bracket order manager
    
    Args:
        execution_service: TradeExecutionService instance
        config: Configuration dict
    
    Returns:
        BracketOrderManager instance
    """
    config = config or {}
    
    return BracketOrderManager(
        execution_service=execution_service,
        check_interval=config.get("check_interval", 5.0),
        auto_start=config.get("auto_start", False)
    )
