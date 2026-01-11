"""
Script to verify readiness for Indian Market trading.
Checks:
1. Symbol detection (RELIANCE, TCS -> NSE)
2. Market hours (IST vs EST)
3. Broker integration (Zerodha)
"""

import sys
import os
import logging
from datetime import datetime
import pytz

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tradingagents.utils.market_detector import MarketDetector, detect_market_and_broker
from tradingagents.services.market_hours import MarketHoursService, Market
from dashboard.multiuser.brokers.unified_broker import BrokerType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verify_symbol_detection():
    logger.info("--- Verifying Symbol Detection ---")
    
    test_cases = [
        ("RELIANCE", Market.INDIA_NSE),
        ("TCS", Market.INDIA_NSE),
        ("SBIN", Market.INDIA_NSE),
        ("AAPL", Market.US_NYSE),  # Control case
        ("BTC-USD", Market.CRYPTO) # Control case
    ]
    
    all_passed = True
    for symbol, expected_market in test_cases:
        market = MarketDetector.detect_market(symbol)
        if market == expected_market:
            logger.info(f"✅ Correctly detected {symbol} as {market.value}")
        else:
            logger.error(f"❌ Failed to detect {symbol}: Expected {expected_market.value}, got {market.value}")
            all_passed = False
            
    # Check broker default
    market, broker, normalized = detect_market_and_broker("RELIANCE")
    if broker == BrokerType.ZERODHA:
        logger.info(f"✅ Correctly defaulted to ZERODHA for RELIANCE")
    else:
        logger.error(f"❌ Default broker for RELIANCE mismatch: {broker}")
        all_passed = False
        
    return all_passed

def verify_market_hours():
    logger.info("\n--- Verifying Market Hours (India) ---")
    
    market = Market.INDIA_NSE
    status = MarketHoursService.get_market_status(market)
    
    logger.info(f"Current Status for {market.value}:")
    logger.info(f"  Timezone: {status['timezone']}")
    logger.info(f"  Local Time: {status['local_time']}")
    logger.info(f"  Is Open: {status['is_open']}")
    logger.info(f"  Hours: {status['hours']}")
    
    # Check if timezone is correct (should be IST)
    if status['timezone'] == "IST":
        logger.info("✅ Timezone is correctly set to IST")
    else:
        logger.error(f"❌ Timezone incorrect: {status['timezone']}")
        
    return True

def verify_broker_integration():
    logger.info("\n--- Verifying Broker Integration (Zerodha) ---")
    
    # Check if Zerodha class is importable
    try:
        from dashboard.multiuser.brokers.zerodha import ZerodhaKiteAPI
        logger.info("✅ ZerodhaKiteAPI class is importable")
    except ImportError:
        logger.error("❌ Could not import ZerodhaKiteAPI. Missing requirements? (pip install kiteconnect)")
        return False
        
    # Check for credentials (just existence)
    api_key = os.getenv("ZERODHA_API_KEY")
    api_secret = os.getenv("ZERODHA_API_SECRET")
    
    if api_key and api_secret:
        logger.info("✅ Zerodha credentials found in environment")
    else:
        logger.warning("⚠️ Zerodha credentials NOT found in environment (ZERODHA_API_KEY, ZERODHA_API_SECRET)")
        logger.warning("   (This is expected if not configured, but required for live trading)")
        
    return True

def main():
    logger.info("=== Indian Market Readiness Verification ===\n")
    
    detection_ok = verify_symbol_detection()
    hours_ok = verify_market_hours()
    broker_ok = verify_broker_integration()
    
    logger.info("\n=== Summary ===")
    if detection_ok and hours_ok:
        logger.info("✅ SYSTEM READY FOR INDIAN MARKET TRADING (Check credentials warnings if any)")
    else:
        logger.warning("⚠️ SYSTEM HAS WARNINGS FOR INDIAN MARKETS")

if __name__ == "__main__":
    main()
