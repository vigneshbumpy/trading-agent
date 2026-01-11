"""
Position sizing calculator with risk-based sizing logic
"""

from typing import Dict, Optional, Literal
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PositionSizingMethod(str, Enum):
    """Position sizing methods"""
    FIXED = "fixed"  # Fixed dollar amount
    PERCENTAGE = "percentage"  # Percentage of portfolio
    RISK_BASED = "risk_based"  # Based on risk per trade
    KELLY = "kelly"  # Kelly Criterion


class PositionSizingCalculator:
    """Calculate position sizes based on various methods"""

    def __init__(
        self,
        method: PositionSizingMethod = PositionSizingMethod.PERCENTAGE,
        fixed_amount: float = 1000.0,
        percentage: float = 0.02,  # 2% of portfolio
        risk_per_trade: float = 0.01,  # 1% risk per trade
        max_position_size: float = 0.1,  # 10% max position
        min_position_size: float = 0.01  # 1% min position
    ):
        """
        Initialize position sizing calculator

        Args:
            method: Sizing method
            fixed_amount: Fixed dollar amount (for FIXED method)
            percentage: Percentage of portfolio (for PERCENTAGE method)
            risk_per_trade: Risk percentage per trade (for RISK_BASED method)
            max_position_size: Maximum position size (as fraction)
            min_position_size: Minimum position size (as fraction)
        """
        self.method = method
        self.fixed_amount = fixed_amount
        self.percentage = percentage
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        self.min_position_size = min_position_size

    def calculate_position_size(
        self,
        portfolio_value: float,
        price: float,
        stop_loss: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None
    ) -> Dict:
        """
        Calculate position size

        Args:
            portfolio_value: Total portfolio value
            price: Current price of asset
            stop_loss: Stop loss price (for risk-based sizing)
            win_rate: Win rate (for Kelly Criterion)
            avg_win: Average win amount (for Kelly Criterion)
            avg_loss: Average loss amount (for Kelly Criterion)

        Returns:
            Dict with position size details
        """
        if self.method == PositionSizingMethod.FIXED:
            return self._calculate_fixed(portfolio_value, price)
        elif self.method == PositionSizingMethod.PERCENTAGE:
            return self._calculate_percentage(portfolio_value, price)
        elif self.method == PositionSizingMethod.RISK_BASED:
            return self._calculate_risk_based(portfolio_value, price, stop_loss)
        elif self.method == PositionSizingMethod.KELLY:
            return self._calculate_kelly(portfolio_value, price, win_rate, avg_win, avg_loss)
        else:
            raise ValueError(f"Unknown position sizing method: {self.method}")

    def _calculate_fixed(self, portfolio_value: float, price: float) -> Dict:
        """Calculate fixed dollar amount position"""
        dollar_amount = min(self.fixed_amount, portfolio_value * self.max_position_size)
        quantity = dollar_amount / price if price > 0 else 0

        return {
            "method": "fixed",
            "dollar_amount": dollar_amount,
            "quantity": quantity,
            "percentage_of_portfolio": (dollar_amount / portfolio_value) if portfolio_value > 0 else 0
        }

    def _calculate_percentage(self, portfolio_value: float, price: float) -> Dict:
        """Calculate percentage-based position"""
        # Clamp percentage between min and max
        percentage = max(self.min_position_size, min(self.percentage, self.max_position_size))
        dollar_amount = portfolio_value * percentage
        quantity = dollar_amount / price if price > 0 else 0

        return {
            "method": "percentage",
            "dollar_amount": dollar_amount,
            "quantity": quantity,
            "percentage_of_portfolio": percentage
        }

    def _calculate_risk_based(
        self,
        portfolio_value: float,
        price: float,
        stop_loss: Optional[float]
    ) -> Dict:
        """Calculate risk-based position size"""
        if stop_loss is None or stop_loss <= 0:
            # Fallback to percentage if no stop loss
            return self._calculate_percentage(portfolio_value, price)

        # Calculate risk per share
        risk_per_share = abs(price - stop_loss)
        if risk_per_share == 0:
            return self._calculate_percentage(portfolio_value, price)

        # Risk amount in dollars
        risk_amount = portfolio_value * self.risk_per_trade

        # Calculate quantity based on risk
        quantity = risk_amount / risk_per_share

        # Calculate dollar amount
        dollar_amount = quantity * price

        # Apply max position size limit
        max_dollar = portfolio_value * self.max_position_size
        if dollar_amount > max_dollar:
            dollar_amount = max_dollar
            quantity = dollar_amount / price

        percentage = (dollar_amount / portfolio_value) if portfolio_value > 0 else 0

        return {
            "method": "risk_based",
            "dollar_amount": dollar_amount,
            "quantity": quantity,
            "percentage_of_portfolio": percentage,
            "risk_amount": risk_amount,
            "risk_per_share": risk_per_share
        }

    def _calculate_kelly(
        self,
        portfolio_value: float,
        price: float,
        win_rate: Optional[float],
        avg_win: Optional[float],
        avg_loss: Optional[float]
    ) -> Dict:
        """Calculate position size using Kelly Criterion"""
        if win_rate is None or avg_win is None or avg_loss is None:
            # Fallback to percentage if Kelly data not available
            return self._calculate_percentage(portfolio_value, price)

        if avg_loss == 0:
            return self._calculate_percentage(portfolio_value, price)

        # Kelly percentage: (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        # Simplified: win_rate - (1 - win_rate) / (avg_win / avg_loss)
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1
        kelly_percentage = win_rate - (1 - win_rate) / win_loss_ratio

        # Apply fractional Kelly (use 25% of full Kelly for safety)
        kelly_percentage = kelly_percentage * 0.25

        # Clamp between min and max
        kelly_percentage = max(self.min_position_size, min(kelly_percentage, self.max_position_size))

        dollar_amount = portfolio_value * kelly_percentage
        quantity = dollar_amount / price if price > 0 else 0

        return {
            "method": "kelly",
            "dollar_amount": dollar_amount,
            "quantity": quantity,
            "percentage_of_portfolio": kelly_percentage,
            "kelly_percentage": kelly_percentage,
            "win_rate": win_rate,
            "win_loss_ratio": win_loss_ratio
        }

    def update_config(self, **kwargs):
        """Update configuration"""
        if "method" in kwargs:
            self.method = PositionSizingMethod(kwargs["method"])
        if "fixed_amount" in kwargs:
            self.fixed_amount = float(kwargs["fixed_amount"])
        if "percentage" in kwargs:
            self.percentage = float(kwargs["percentage"])
        if "risk_per_trade" in kwargs:
            self.risk_per_trade = float(kwargs["risk_per_trade"])
        if "max_position_size" in kwargs:
            self.max_position_size = float(kwargs["max_position_size"])
        if "min_position_size" in kwargs:
            self.min_position_size = float(kwargs["min_position_size"])


def create_position_sizer(config: Dict) -> PositionSizingCalculator:
    """
    Create position sizer from config

    Args:
        config: Configuration dict

    Returns:
        PositionSizingCalculator instance
    """
    return PositionSizingCalculator(
        method=PositionSizingMethod(config.get("method", "percentage")),
        fixed_amount=config.get("fixed_amount", 1000.0),
        percentage=config.get("percentage", 0.02),
        risk_per_trade=config.get("risk_per_trade", 0.01),
        max_position_size=config.get("max_position_size", 0.1),
        min_position_size=config.get("min_position_size", 0.01)
    )
