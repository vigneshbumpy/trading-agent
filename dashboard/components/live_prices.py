"""
Live Prices Component
Displays real-time prices for watchlist symbols using Streamlit auto-refresh
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

from dashboard.utils.broker import get_broker

def render_live_prices(watchlist_symbols: list, interval_seconds: int = 60):
    """
    Render live prices ticker/grid
    
    Args:
        watchlist_symbols: List of symbols to track
        interval_seconds: Auto-refresh interval (default 60s to avoid rate limits)
    """
    if not watchlist_symbols:
        return
        
    st.markdown("### 🔴 Live Market")
    
    # Check if we should update
    last_update = st.session_state.get('last_price_update', datetime.min)
    should_update = (datetime.now() - last_update).total_seconds() > interval_seconds
    
    if 'live_prices' not in st.session_state:
        st.session_state.live_prices = {}
        
    if should_update or st.button("🔄 Refresh Prices", key="refresh_prices_btn", use_container_width=False):
        try:
            use_alpaca = st.session_state.get('use_alpaca', False)
            paper_trading = st.session_state.get('paper_trading_enabled', True)
            broker = get_broker(paper_trading=paper_trading, use_alpaca=use_alpaca)
            
            # Fetch in batch if possible, or loop
            # Unified broker usually has get_quote(symbol)
            new_prices = {}
            for symbol in watchlist_symbols:
                # Add simple caching or batching eventually
                quote = broker.get_quote(symbol)
                if quote and 'bid_price' in quote:
                    price = (quote['bid_price'] + quote['ask_price']) / 2
                    # Get previous price to calc change if available, or just store current
                    prev = st.session_state.live_prices.get(symbol, {}).get('price', price)
                    change = ((price - prev) / prev * 100) if prev > 0 else 0
                    
                    new_prices[symbol] = {
                        'price': price,
                        'change': change,
                        'time': datetime.now().strftime("%H:%M:%S")
                    }
            
            st.session_state.live_prices.update(new_prices)
            st.session_state.last_price_update = datetime.now()
            
        except Exception as e:
            st.caption(f"Price update failed: {e}")
            
    # Display prices in columns
    cols = st.columns(len(watchlist_symbols))
    for i, symbol in enumerate(watchlist_symbols):
        data = st.session_state.live_prices.get(symbol)
        with cols[i % len(cols)]:
            if data:
                price = data['price']
                change = data['change']
                color = "green" if change >= 0 else "red"
                arrow = "▲" if change >= 0 else "▼"
                st.metric(
                    label=symbol,
                    value=f"${price:,.2f}",
                    delta=f"{change:.2f}%"
                )
            else:
                st.metric(label=symbol, value="---")

def get_default_watchlist():
    """Get default watchlist based on market"""
    return ["AAPL", "NVDA", "BTC-USD", "ETH-USD"]
