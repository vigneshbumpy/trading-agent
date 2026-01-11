from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.graph.fast_trading_graph import FastTradingGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "gpt-4o-mini"  # Use a different model
config["quick_think_llm"] = "gpt-4o-mini"  # Use a different model
config["max_debate_rounds"] = 1  # Increase debate rounds

# Configure data vendors (default uses yfinance and alpha_vantage)
config["data_vendors"] = {
    "core_stock_apis": "yfinance",           # Options: yfinance, alpha_vantage, local
    "technical_indicators": "yfinance",      # Options: yfinance, alpha_vantage, local
    "fundamental_data": "alpha_vantage",     # Options: openai, alpha_vantage, local
    "news_data": "alpha_vantage",            # Options: openai, alpha_vantage, google, local
}

# Select execution mode: "fast" (parallel, 3-4x faster) or "standard" (LangGraph)
execution_mode = config.get("execution_mode", "fast")

if execution_mode == "fast":
    print("🚀 Using Fast Mode (parallel execution)")
    ta = FastTradingGraph(debug=True, config=config)
else:
    print("📊 Using Standard Mode (LangGraph)")
    ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
_, decision = ta.propagate("NVDA", "2024-05-10")
print(f"\n{'='*50}")
print(f"FINAL DECISION: {decision}")
print(f"{'='*50}")

# Show timing info if using fast mode
if execution_mode == "fast":
    timing = ta.get_timing_info()
    print(f"\n⏱️  TIMING BREAKDOWN:")
    print(f"   Data fetch:    {timing.get('data_fetch', 0):.2f}s")
    print(f"   Analysts:      {timing.get('analysts', 0):.2f}s")
    print(f"   Decision flow: {timing.get('decision_flow', 0):.2f}s")
    print(f"   TOTAL:         {timing.get('total', 0):.2f}s")

# Memorize mistakes and reflect (only available in standard mode)
# ta.reflect_and_remember(1000) # parameter is the position returns

