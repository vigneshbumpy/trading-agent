"""
Risk limits and safety controls for automated trading
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RiskLimits:
    """Manage risk limits and safety controls"""

    def __init__(
        self,
        max_position_size: float = 0.1,  # 10% max position per symbol
        max_daily_trades: int = 10,
        max_daily_loss: float = 0.05,  # 5% max daily loss
        max_portfolio_risk: float = 0.2,  # 20% max portfolio at risk
        max_concentration: float = 0.3,  # 30% max concentration in single market
        min_balance_required: float = 0.1  # 10% minimum balance to keep
    ):
        """
        Initialize risk limits

        Args:
            max_position_size: Maximum position size as fraction of portfolio
            max_daily_trades: Maximum trades per day
            max_daily_loss: Maximum daily loss as fraction of portfolio
            max_portfolio_risk: Maximum portfolio at risk
            max_concentration: Maximum concentration in single market
            min_balance_required: Minimum balance to keep as fraction
        """
        self.max_position_size = max_position_size
        self.max_daily_trades = max_daily_trades
        self.max_daily_loss = max_daily_loss
        self.max_portfolio_risk = max_portfolio_risk
        self.max_concentration = max_concentration
        self.min_balance_required = min_balance_required

        # Track daily activity
        self.daily_trades: Dict[str, int] = defaultdict(int)  # date -> count
        self.daily_pnl: Dict[str, float] = defaultdict(float)  # date -> PnL
        self.positions: Dict[str, Dict] = {}  # symbol -> position info
        self.market_exposure: Dict[str, float] = defaultdict(float)  # market -> exposure

    def can_trade(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        portfolio_value: float,
        market: str
    ) -> Dict:
        """
        Check if trade is allowed based on risk limits

        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Order quantity
            price: Order price
            portfolio_value: Total portfolio value
            market: Market type

        Returns:
            Dict with allowed flag and reason
        """
        today = datetime.now().date().isoformat()

        # Check daily trade limit
        if self.daily_trades[today] >= self.max_daily_trades:
            return {
                "allowed": False,
                "reason": f"Daily trade limit reached ({self.max_daily_trades})",
                "limit_type": "daily_trades"
            }

        # Check daily loss limit
        daily_loss = abs(self.daily_pnl[today]) if self.daily_pnl[today] < 0 else 0
        if daily_loss >= portfolio_value * self.max_daily_loss:
            return {
                "allowed": False,
                "reason": f"Daily loss limit reached ({self.max_daily_loss * 100}%)",
                "limit_type": "daily_loss"
            }

        # Check position size limit
        trade_value = quantity * price
        position_size = trade_value / portfolio_value if portfolio_value > 0 else 0

        if position_size > self.max_position_size:
            return {
                "allowed": False,
                "reason": f"Position size exceeds limit ({self.max_position_size * 100}%)",
                "limit_type": "position_size",
                "position_size": position_size
            }

        # Check minimum balance
        available_balance = portfolio_value * (1 - self.min_balance_required)
        if action == "BUY" and trade_value > available_balance:
            return {
                "allowed": False,
                "reason": f"Insufficient balance (must keep {self.min_balance_required * 100}% reserve)",
                "limit_type": "balance"
            }

        # Check market concentration
        current_exposure = self.market_exposure.get(market, 0)
        new_exposure = current_exposure + (trade_value if action == "BUY" else -trade_value)
        concentration = new_exposure / portfolio_value if portfolio_value > 0 else 0

        if concentration > self.max_concentration:
            return {
                "allowed": False,
                "reason": f"Market concentration limit exceeded ({self.max_concentration * 100}%)",
                "limit_type": "concentration",
                "concentration": concentration
            }

        # Check portfolio risk
        total_risk = sum(abs(pnl) for pnl in self.daily_pnl.values() if pnl < 0)
        if total_risk >= portfolio_value * self.max_portfolio_risk:
            return {
                "allowed": False,
                "reason": f"Portfolio risk limit reached ({self.max_portfolio_risk * 100}%)",
                "limit_type": "portfolio_risk"
            }

        # Circuit Breaker: Volatility Check (VIX)
        # We fetch VIX here. Ideally this should be cached or passed in context.
        # For safety/simplicity we'll try to fetch it but fail open if unavailable to avoid blocking 
        # unless explicitly configured to require it.
        try:
            import yfinance as yf
            # Check market conditions
            if market in ["US_NYSE", "US_NASDAQ", "US_AMEX"]:
                vix = yf.Ticker("^VIX").history(period="1d")
                if not vix.empty:
                    current_vix = vix["Close"].iloc[-1]
                    # VIX > 35 is usually considered potential crash/panic territory
                    if current_vix > 35:
                        return {
                            "allowed": False,
                            "reason": f"Circuit Breaker Active: High Volatility (VIX: {current_vix:.2f})",
                            "limit_type": "circuit_breaker"
                        }
        except Exception as e:
            logger.warning(f"Failed to check VIX: {e}")

        return {
            "allowed": True,
            "reason": "All risk checks passed"
        }

    def record_trade(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        market: str
    ):
        """Record a trade for risk tracking"""
        today = datetime.now().date().isoformat()
        self.daily_trades[today] += 1

        trade_value = quantity * price

        # Update market exposure
        if action == "BUY":
            self.market_exposure[market] += trade_value
        else:  # SELL
            self.market_exposure[market] -= trade_value

        # Update position tracking
        if symbol in self.positions:
            pos = self.positions[symbol]
            if action == "BUY":
                pos["quantity"] += quantity
                pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + price * quantity) / (pos["quantity"] + quantity)
            else:
                pos["quantity"] -= quantity
        else:
            if action == "BUY":
                self.positions[symbol] = {
                    "quantity": quantity,
                    "avg_price": price
                }

    def record_pnl(self, pnl: float, date: Optional[str] = None):
        """Record P&L for a date"""
        if date is None:
            date = datetime.now().date().isoformat()
        self.daily_pnl[date] += pnl

    def reset_daily_counts(self):
        """Reset daily tracking (call at start of new day)"""
        today = datetime.now().date().isoformat()
        # Keep only today's data
        self.daily_trades = {today: self.daily_trades.get(today, 0)}
        self.daily_pnl = {today: self.daily_pnl.get(today, 0)}

    def get_risk_summary(self, portfolio_value: float) -> Dict:
        """Get current risk summary"""
        today = datetime.now().date().isoformat()

        return {
            "daily_trades": self.daily_trades.get(today, 0),
            "max_daily_trades": self.max_daily_trades,
            "daily_pnl": self.daily_pnl.get(today, 0),
            "daily_pnl_percent": (self.daily_pnl.get(today, 0) / portfolio_value * 100) if portfolio_value > 0 else 0,
            "max_daily_loss": self.max_daily_loss * 100,
            "market_exposure": dict(self.market_exposure),
            "positions_count": len(self.positions),
            "total_exposure": sum(self.market_exposure.values()),
            "exposure_percent": (sum(self.market_exposure.values()) / portfolio_value * 100) if portfolio_value > 0 else 0
        }

    def update_limits(self, **kwargs):
        """Update risk limits"""
        if "max_position_size" in kwargs:
            self.max_position_size = float(kwargs["max_position_size"])
        if "max_daily_trades" in kwargs:
            self.max_daily_trades = int(kwargs["max_daily_trades"])
        if "max_daily_loss" in kwargs:
            self.max_daily_loss = float(kwargs["max_daily_loss"])
        if "max_portfolio_risk" in kwargs:
            self.max_portfolio_risk = float(kwargs["max_portfolio_risk"])
        if "max_concentration" in kwargs:
            self.max_concentration = float(kwargs["max_concentration"])
        if "min_balance_required" in kwargs:
            self.min_balance_required = float(kwargs["min_balance_required"])


def create_risk_limits(config: Dict) -> RiskLimits:
    """
    Create risk limits from config

    Args:
        config: Configuration dict

    Returns:
        RiskLimits instance
    """
    return RiskLimits(
        max_position_size=config.get("max_position_size", 0.1),
        max_daily_trades=config.get("max_daily_trades", 10),
        max_daily_loss=config.get("max_daily_loss", 0.05),
        max_portfolio_risk=config.get("max_portfolio_risk", 0.2),
        max_concentration=config.get("max_concentration", 0.3),
        min_balance_required=config.get("min_balance_required", 0.1)
    )
