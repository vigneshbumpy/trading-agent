"""
Tests for Bracket Order Manager and Stop-Loss/Take-Profit functionality
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from tradingagents.services.bracket_orders import (
    BracketOrderManager,
    BracketOrder,
    OrderStatus
)


class TestBracketOrder(unittest.TestCase):
    """Test BracketOrder dataclass"""
    
    def test_calculate_stop_loss_long(self):
        """Test stop-loss calculation for long position"""
        bracket = BracketOrder(
            id="test1",
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="BUY",
            stop_loss_pct=0.02  # 2%
        )
        
        stop_price = bracket.calculate_stop_loss_price()
        self.assertEqual(stop_price, 98.0)  # 100 * (1 - 0.02)
    
    def test_calculate_stop_loss_short(self):
        """Test stop-loss calculation for short position"""
        bracket = BracketOrder(
            id="test2",
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="SELL",
            stop_loss_pct=0.02  # 2%
        )
        
        stop_price = bracket.calculate_stop_loss_price()
        self.assertEqual(stop_price, 102.0)  # 100 * (1 + 0.02)
    
    def test_calculate_take_profit_long(self):
        """Test take-profit calculation for long position"""
        bracket = BracketOrder(
            id="test3",
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="BUY",
            take_profit_pct=0.04  # 4%
        )
        
        tp_price = bracket.calculate_take_profit_price()
        self.assertEqual(tp_price, 104.0)  # 100 * (1 + 0.04)
    
    def test_calculate_take_profit_short(self):
        """Test take-profit calculation for short position"""
        bracket = BracketOrder(
            id="test4",
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="SELL",
            take_profit_pct=0.04  # 4%
        )
        
        tp_price = bracket.calculate_take_profit_price()
        self.assertEqual(tp_price, 96.0)  # 100 * (1 - 0.04)
    
    def test_check_triggered_stop_loss_long(self):
        """Test stop-loss trigger for long position"""
        bracket = BracketOrder(
            id="test5",
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="BUY",
            stop_loss_pct=0.02
        )
        
        # Price above stop - not triggered
        self.assertIsNone(bracket.check_triggered(99.0))
        
        # Price at stop - triggered
        self.assertEqual(bracket.check_triggered(98.0), "stop_loss")
        
        # Price below stop - triggered
        self.assertEqual(bracket.check_triggered(95.0), "stop_loss")
    
    def test_check_triggered_take_profit_long(self):
        """Test take-profit trigger for long position"""
        bracket = BracketOrder(
            id="test6",
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="BUY",
            take_profit_pct=0.04
        )
        
        # Price below target - not triggered
        self.assertIsNone(bracket.check_triggered(103.0))
        
        # Price at target - triggered
        self.assertEqual(bracket.check_triggered(104.0), "take_profit")
        
        # Price above target - triggered
        self.assertEqual(bracket.check_triggered(110.0), "take_profit")
    
    def test_trailing_stop_long(self):
        """Test trailing stop for long position"""
        bracket = BracketOrder(
            id="test7",
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="BUY",
            stop_loss_pct=0.02,
            trailing_stop_pct=0.02,  # 2% trailing
            trailing_stop_activation_pct=None,  # No activation threshold
            highest_price=100.0
        )
        
        # Price goes up to 105 - trailing stop should move
        new_stop = bracket.update_trailing_stop(105.0)
        self.assertIsNotNone(new_stop)
        self.assertEqual(bracket.highest_price, 105.0)
        self.assertAlmostEqual(new_stop, 102.9, places=1)  # 105 * 0.98
        
        # Price goes down to 103 - stop should NOT move down
        old_stop = bracket.stop_loss_price
        new_stop = bracket.update_trailing_stop(103.0)
        self.assertIsNone(new_stop)  # No update
        self.assertEqual(bracket.stop_loss_price, old_stop)  # Stop unchanged


class TestBracketOrderManager(unittest.TestCase):
    """Test BracketOrderManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = BracketOrderManager(auto_start=False)
    
    def test_create_bracket_order(self):
        """Test creating a bracket order"""
        bracket = self.manager.create_bracket_order(
            symbol="AAPL",
            entry_price=150.0,
            quantity=10,
            action="BUY",
            stop_loss_pct=0.02,
            take_profit_pct=0.04
        )
        
        self.assertIsNotNone(bracket)
        self.assertEqual(bracket.symbol, "AAPL")
        self.assertEqual(bracket.entry_price, 150.0)
        self.assertEqual(bracket.status, OrderStatus.ACTIVE)
        self.assertEqual(len(self.manager.bracket_orders), 1)
    
    def test_cancel_bracket_order(self):
        """Test cancelling a bracket order"""
        bracket = self.manager.create_bracket_order(
            symbol="AAPL",
            entry_price=150.0,
            quantity=10,
            action="BUY"
        )
        
        result = self.manager.cancel_bracket_order(bracket.id)
        self.assertTrue(result)
        self.assertEqual(len(self.manager.bracket_orders), 0)
    
    def test_update_prices_triggers_stop_loss(self):
        """Test that price update triggers stop-loss"""
        on_stop_loss = Mock()
        self.manager.on_stop_loss = on_stop_loss
        
        bracket = self.manager.create_bracket_order(
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="BUY",
            stop_loss_pct=0.02
        )
        
        # Price drops to stop-loss
        self.manager.update_prices({"AAPL": 97.0})  # Below 98 stop
        
        # Verify callback was called
        self.assertTrue(on_stop_loss.called)
        self.assertEqual(self.manager.stats["stop_losses_triggered"], 1)
    
    def test_update_prices_triggers_take_profit(self):
        """Test that price update triggers take-profit"""
        on_take_profit = Mock()
        self.manager.on_take_profit = on_take_profit
        
        bracket = self.manager.create_bracket_order(
            symbol="AAPL",
            entry_price=100.0,
            quantity=10,
            action="BUY",
            take_profit_pct=0.04
        )
        
        # Price rises to take-profit
        self.manager.update_prices({"AAPL": 105.0})  # Above 104 target
        
        # Verify callback was called
        self.assertTrue(on_take_profit.called)
        self.assertEqual(self.manager.stats["take_profits_triggered"], 1)
    
    def test_get_active_brackets(self):
        """Test getting active brackets"""
        self.manager.create_bracket_order("AAPL", 100.0, 10, "BUY")
        self.manager.create_bracket_order("GOOGL", 200.0, 5, "BUY")
        
        active = self.manager.get_active_brackets()
        self.assertEqual(len(active), 2)
    
    def test_get_stats(self):
        """Test getting statistics"""
        self.manager.create_bracket_order("AAPL", 100.0, 10, "BUY")
        
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_brackets"], 1)
        self.assertEqual(stats["active_brackets"], 1)


if __name__ == '__main__':
    unittest.main()
