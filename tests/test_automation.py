"""
Integration tests for automated trading system
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from tradingagents.services.execution_service import TradeExecutionService
from tradingagents.services.automation_service import AutomationService
from tradingagents.services.position_sizing import PositionSizingCalculator, PositionSizingMethod
from tradingagents.services.risk_limits import RiskLimits
from tradingagents.services.market_hours import MarketHoursService
from tradingagents.utils.market_detector import MarketDetector, detect_market_and_broker
from dashboard.multiuser.brokers.unified_broker import Market, BrokerType


class TestMarketDetector(unittest.TestCase):
    """Test market detection"""

    def test_detect_crypto_market(self):
        """Test crypto market detection"""
        market = MarketDetector.detect_market("BTC-USD")
        self.assertEqual(market, Market.CRYPTO)

        market = MarketDetector.detect_market("ETHUSDT")
        self.assertEqual(market, Market.CRYPTO)

    def test_detect_us_market(self):
        """Test US market detection"""
        market = MarketDetector.detect_market("AAPL")
        self.assertIn(market, [Market.US_NYSE, Market.US_NASDAQ])

    def test_detect_indian_market(self):
        """Test Indian market detection"""
        market = MarketDetector.detect_market("RELIANCE")
        self.assertIn(market, [Market.INDIA_NSE, Market.INDIA_BSE])


class TestMarketHours(unittest.TestCase):
    """Test market hours service"""

    def test_crypto_always_open(self):
        """Test that crypto markets are always open"""
        is_open = MarketHoursService.is_market_open(Market.CRYPTO)
        self.assertTrue(is_open)

    def test_get_market_status(self):
        """Test getting market status"""
        status = MarketHoursService.get_market_status(Market.CRYPTO)
        self.assertEqual(status["market"], "CRYPTO")
        self.assertTrue(status["is_open"])


class TestPositionSizing(unittest.TestCase):
    """Test position sizing"""

    def test_fixed_sizing(self):
        """Test fixed position sizing"""
        calculator = PositionSizingCalculator(
            method=PositionSizingMethod.FIXED,
            fixed_amount=1000.0
        )

        result = calculator.calculate_position_size(
            portfolio_value=10000.0,
            price=100.0
        )

        self.assertEqual(result["method"], "fixed")
        self.assertEqual(result["quantity"], 10.0)

    def test_percentage_sizing(self):
        """Test percentage position sizing"""
        calculator = PositionSizingCalculator(
            method=PositionSizingMethod.PERCENTAGE,
            percentage=0.02  # 2%
        )

        result = calculator.calculate_position_size(
            portfolio_value=10000.0,
            price=100.0
        )

        self.assertEqual(result["method"], "percentage")
        self.assertEqual(result["dollar_amount"], 200.0)
        self.assertEqual(result["quantity"], 2.0)


class TestRiskLimits(unittest.TestCase):
    """Test risk limits"""

    def test_daily_trade_limit(self):
        """Test daily trade limit"""
        risk_limits = RiskLimits(max_daily_trades=5)

        # Make 5 trades
        for i in range(5):
            risk_limits.record_trade("AAPL", "BUY", 10, 100.0, "US")

        # 6th trade should be blocked
        result = risk_limits.can_trade(
            symbol="AAPL",
            action="BUY",
            quantity=10,
            price=100.0,
            portfolio_value=10000.0,
            market="US"
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["limit_type"], "daily_trades")

    def test_position_size_limit(self):
        """Test position size limit"""
        risk_limits = RiskLimits(max_position_size=0.1)  # 10% max

        result = risk_limits.can_trade(
            symbol="AAPL",
            action="BUY",
            quantity=200,  # 20% of portfolio
            price=100.0,
            portfolio_value=10000.0,
            market="US"
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["limit_type"], "position_size")


class TestExecutionService(unittest.TestCase):
    """Test execution service"""

    def setUp(self):
        """Set up test fixtures"""
        self.execution_service = TradeExecutionService()

    def test_parse_decision_buy(self):
        """Test parsing BUY decision"""
        decision = self.execution_service.parse_decision("Based on analysis, I recommend BUY")
        self.assertEqual(decision["action"], "BUY")

    def test_parse_decision_sell(self):
        """Test parsing SELL decision"""
        decision = self.execution_service.parse_decision("The analysis suggests SELL")
        self.assertEqual(decision["action"], "SELL")

    def test_parse_decision_hold(self):
        """Test parsing HOLD decision"""
        decision = self.execution_service.parse_decision("I recommend HOLD")
        self.assertEqual(decision["action"], "HOLD")


class TestAutomationService(unittest.TestCase):
    """Test automation service"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock trading graph
        self.mock_graph = Mock()
        self.mock_graph.propagate = Mock(return_value=(
            {"final_trade_decision": "BUY"},
            "BUY"
        ))

        # Mock execution service
        self.mock_execution = Mock()
        self.mock_execution.parse_decision = Mock(return_value={"action": "BUY"})
        self.mock_execution.get_broker = Mock(return_value=Mock())
        self.mock_execution.execute_trade = Mock(return_value={"status": "success"})

        self.automation = AutomationService(
            trading_graph=self.mock_graph,
            execution_service=self.mock_execution,
            watchlist=["AAPL"],
            config={"auto_execute": False}  # Don't actually execute in tests
        )

    def test_service_initialization(self):
        """Test service initialization"""
        self.assertFalse(self.automation.is_running)
        self.assertEqual(self.automation.watchlist, ["AAPL"])

    def test_start_stop(self):
        """Test starting and stopping service"""
        self.automation.start()
        self.assertTrue(self.automation.is_running)

        self.automation.stop()
        self.assertFalse(self.automation.is_running)

    def test_pause_resume(self):
        """Test pausing and resuming service"""
        self.automation.start()
        self.automation.pause()
        self.assertTrue(self.automation.is_paused)

        self.automation.resume()
        self.assertFalse(self.automation.is_paused)

        self.automation.stop()


if __name__ == '__main__':
    unittest.main()
