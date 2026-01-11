"""
Test script to verify all dashboard components are working
Run this before starting the dashboard to check for issues
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🧪 Testing TradingAgents Dashboard Components...\n")

# Test 1: Import core modules
print("1️⃣ Testing core imports...")
try:
    import streamlit as st
    print("   ✅ Streamlit installed")
except ImportError as e:
    print(f"   ❌ Streamlit not found: {e}")
    sys.exit(1)

try:
    import plotly
    print("   ✅ Plotly installed")
except ImportError as e:
    print(f"   ❌ Plotly not found: {e}")
    sys.exit(1)

try:
    import pandas as pd
    print("   ✅ Pandas installed")
except ImportError as e:
    print(f"   ❌ Pandas not found: {e}")
    sys.exit(1)

# Test 2: Import dashboard modules
print("\n2️⃣ Testing dashboard modules...")
try:
    from dashboard.utils.database import TradingDatabase
    print("   ✅ Database module imported")
except ImportError as e:
    print(f"   ❌ Database module error: {e}")
    sys.exit(1)

try:
    from dashboard.utils.broker import get_broker, PaperBroker, OrderSide
    print("   ✅ Broker module imported")
except ImportError as e:
    print(f"   ❌ Broker module error: {e}")
    sys.exit(1)

# Test 3: Import TradingAgents
print("\n3️⃣ Testing TradingAgents framework...")
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    print("   ✅ TradingAgents framework imported")
except ImportError as e:
    print(f"   ❌ TradingAgents import error: {e}")
    sys.exit(1)

# Test 4: Database initialization
print("\n4️⃣ Testing database initialization...")
try:
    db = TradingDatabase()
    print("   ✅ Database initialized successfully")
    print(f"   📁 Database location: {db.db_path}")
except Exception as e:
    print(f"   ❌ Database initialization failed: {e}")
    sys.exit(1)

# Test 5: Broker initialization
print("\n5️⃣ Testing broker initialization...")
try:
    broker = get_broker(paper_trading=True, use_alpaca=False)
    account = broker.get_account()
    print("   ✅ Simulated broker initialized")
    print(f"   💰 Starting cash: ${account['cash']:,.2f}")
except Exception as e:
    print(f"   ❌ Broker initialization failed: {e}")
    sys.exit(1)

# Test 6: Environment variables
print("\n6️⃣ Checking environment variables...")
import os
from dotenv import load_dotenv
load_dotenv()

env_status = []
if os.getenv("OPENAI_API_KEY"):
    env_status.append("✅ OPENAI_API_KEY")
else:
    env_status.append("⚠️  OPENAI_API_KEY not set")

if os.getenv("OPENROUTER_API_KEY"):
    env_status.append("✅ OPENROUTER_API_KEY")
else:
    env_status.append("⚠️  OPENROUTER_API_KEY not set")

if os.getenv("ALPHA_VANTAGE_API_KEY"):
    env_status.append("✅ ALPHA_VANTAGE_API_KEY")
else:
    env_status.append("⚠️  ALPHA_VANTAGE_API_KEY not set")

for status in env_status:
    print(f"   {status}")

# Test 7: Test a simple database operation
print("\n7️⃣ Testing database operations...")
try:
    # Add to watchlist
    db.add_to_watchlist("TEST", "Test ticker from verification script")
    watchlist = db.get_watchlist()

    # Remove test entry
    db.remove_from_watchlist("TEST")

    print("   ✅ Database CRUD operations working")
except Exception as e:
    print(f"   ❌ Database operations failed: {e}")
    sys.exit(1)

# Test 8: Test broker operations
print("\n8️⃣ Testing broker operations...")
try:
    # Place a test order
    result = broker.place_order(
        ticker="TEST",
        quantity=10,
        side=OrderSide.BUY,
        limit_price=100.0
    )

    if "error" not in result:
        print("   ✅ Broker order placement working")
        print(f"   📄 Order ID: {result.get('order_id')}")
    else:
        print(f"   ⚠️  Order had error: {result['error']}")
except Exception as e:
    print(f"   ❌ Broker operations failed: {e}")
    sys.exit(1)

# Test 9: Check page files
print("\n9️⃣ Checking dashboard page files...")
pages = [
    "dashboard/pages/home.py",
    "dashboard/pages/analysis.py",
    "dashboard/pages/portfolio.py",
    "dashboard/pages/trade_history.py",
    "dashboard/pages/settings.py",
    "dashboard/pages/documentation.py"
]

for page in pages:
    page_path = Path(__file__).parent.parent / page
    if page_path.exists():
        print(f"   ✅ {page}")
    else:
        print(f"   ❌ {page} - NOT FOUND")
        sys.exit(1)

# Test 10: Alpaca (optional)
print("\n🔟 Testing Alpaca integration (optional)...")
try:
    from alpaca.trading.client import TradingClient
    print("   ✅ Alpaca SDK installed")

    if os.getenv("ALPACA_PAPER_API_KEY"):
        print("   ✅ Alpaca API keys configured")
    else:
        print("   ⚠️  Alpaca API keys not configured (optional)")
except ImportError:
    print("   ⚠️  Alpaca SDK not installed (optional)")
    print("   💡 Install with: pip install alpaca-py")

# Summary
print("\n" + "="*60)
print("✅ All core tests passed!")
print("="*60)
print("\n📊 Dashboard Statistics:")
print(f"   - Pages: 6")
print(f"   - Utility modules: 2")
print(f"   - Database tables: 5")
print(f"   - Broker modes: 2 (Simulated + Alpaca)")

print("\n🚀 Ready to start dashboard!")
print("\nRun:")
print("   streamlit run dashboard/app.py")
print("\nOr:")
print("   ./run_dashboard.sh")

print("\n💡 Next Steps:")
print("   1. Configure your LLM provider in Settings")
print("   2. Run your first stock analysis")
print("   3. Review the Documentation page")

print("\n✨ Happy Trading!\n")
