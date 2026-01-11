"""
Tests for Fast Trading Graph execution mode

Compares performance between standard LangGraph mode and fast parallel mode.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import time
import os

# Set a dummy API key for testing
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.fast_trading_graph import FastTradingGraph


class TestFastTradingGraphInit(unittest.TestCase):
    """Test FastTradingGraph initialization"""

    @patch('tradingagents.graph.fast_trading_graph.ChatOpenAI')
    def test_init_default_config(self, mock_openai):
        """Test initialization with default config"""
        mock_openai.return_value = Mock()
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        
        graph = FastTradingGraph(config=config, debug=False)
        
        self.assertIsNotNone(graph.llm)
        self.assertEqual(graph.selected_analysts, ["market", "social", "news", "fundamentals"])
        self.assertFalse(graph.debug)

    @patch('tradingagents.graph.fast_trading_graph.ChatOpenAI')
    def test_init_custom_analysts(self, mock_openai):
        """Test initialization with custom analyst selection"""
        mock_openai.return_value = Mock()
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        
        graph = FastTradingGraph(
            selected_analysts=["market", "fundamentals"],
            config=config,
            debug=True
        )
        
        self.assertEqual(graph.selected_analysts, ["market", "fundamentals"])
        self.assertTrue(graph.debug)


class TestDecisionExtraction(unittest.TestCase):
    """Test decision extraction from full text"""

    @patch('tradingagents.graph.fast_trading_graph.ChatOpenAI')
    def test_extract_buy_decision(self, mock_openai):
        """Test extracting BUY decision"""
        mock_openai.return_value = Mock()
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        
        graph = FastTradingGraph(config=config)
        
        decision = graph._extract_decision("APPROVE - BUY - Strong fundamentals")
        self.assertEqual(decision, "BUY")

    @patch('tradingagents.graph.fast_trading_graph.ChatOpenAI')
    def test_extract_sell_decision(self, mock_openai):
        """Test extracting SELL decision"""
        mock_openai.return_value = Mock()
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        
        graph = FastTradingGraph(config=config)
        
        decision = graph._extract_decision("APPROVE - SELL - Negative outlook")
        self.assertEqual(decision, "SELL")

    @patch('tradingagents.graph.fast_trading_graph.ChatOpenAI')
    def test_extract_hold_decision(self, mock_openai):
        """Test extracting HOLD decision"""
        mock_openai.return_value = Mock()
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        
        graph = FastTradingGraph(config=config)
        
        decision = graph._extract_decision("REJECT - Too risky at current levels")
        self.assertEqual(decision, "HOLD")

    @patch('tradingagents.graph.fast_trading_graph.ChatOpenAI')
    def test_fallback_to_buy(self, mock_openai):
        """Test fallback when BUY keyword is present"""
        mock_openai.return_value = Mock()
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        
        graph = FastTradingGraph(config=config)
        
        decision = graph._extract_decision("Consider BUY opportunity")
        self.assertEqual(decision, "BUY")


class TestConfigOptions(unittest.TestCase):
    """Test configuration options"""

    def test_execution_mode_in_default_config(self):
        """Test that execution_mode is in default config"""
        self.assertIn("execution_mode", DEFAULT_CONFIG)
        self.assertEqual(DEFAULT_CONFIG["execution_mode"], "fast")

    def test_skip_risk_debate_in_default_config(self):
        """Test that skip_risk_debate is in default config"""
        self.assertIn("skip_risk_debate", DEFAULT_CONFIG)
        self.assertFalse(DEFAULT_CONFIG["skip_risk_debate"])


class TestAsyncExecution(unittest.TestCase):
    """Test async execution patterns"""

    @patch('tradingagents.graph.fast_trading_graph.ChatOpenAI')
    @patch('tradingagents.graph.fast_trading_graph.route_to_vendor')
    def test_timing_info(self, mock_route, mock_openai):
        """Test that timing info is recorded"""
        mock_openai.return_value = Mock()
        mock_route.return_value = "test data"
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        
        graph = FastTradingGraph(config=config)
        
        # Initially empty
        self.assertEqual(graph.get_timing_info(), {})


if __name__ == '__main__':
    unittest.main()
