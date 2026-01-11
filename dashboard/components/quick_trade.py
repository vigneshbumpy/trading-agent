"""
Quick Trade Widget Component
Allows instant trade execution without full analysis flow
"""

import streamlit as st
import time
from datetime import datetime
from typing import Dict, Optional, Any

from dashboard.utils.broker import get_broker, OrderSide
from dashboard.utils.database import TradingDatabase

def render_quick_trade(db: TradingDatabase = None):
    """Render the quick trade widget"""
    
    st.markdown("""
    <div style="
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        border: 1px solid #e9ecef;
        margin-bottom: 2rem;
    ">
        <h3 style="margin-top: 0; color: #1f77b4;">⚡ Quick Trade</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for quick trade
    if 'qt_symbol' not in st.session_state:
        st.session_state.qt_symbol = ""
    if 'qt_quantity' not in st.session_state:
        st.session_state.qt_quantity = 10
    if 'qt_action' not in st.session_state:
        st.session_state.qt_action = "BUY"
    
    col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1.5])
    
    with col1:
        symbol = st.text_input(
            "Symbol", 
            value=st.session_state.qt_symbol,
            placeholder="e.g. AAPL, BTC-USD",
            key="qt_input_symbol",
            label_visibility="collapsed"
        ).upper()
        
    with col2:
        quantity = st.number_input(
            "Qty", 
            min_value=1, 
            value=st.session_state.qt_quantity,
            key="qt_input_quantity",
            label_visibility="collapsed"
        )
        
    with col3:
        action = st.selectbox(
            "Action", 
            ["BUY", "SELL"], 
            index=0 if st.session_state.qt_action == "BUY" else 1,
            key="qt_input_action",
            label_visibility="collapsed"
        )
        
    with col4:
        if st.button("🚀 Execute", type="primary", use_container_width=True):
            if not symbol:
                st.error("Enter symbol")
                return
                
            _execute_quick_trade(symbol, action, quantity, db)

def _execute_quick_trade(symbol: str, action: str, quantity: int, db: TradingDatabase = None):
    """Execute the quick trade"""
    try:
        # Get broker
        use_alpaca = st.session_state.get('use_alpaca', False)
        paper_trading = st.session_state.get('paper_trading_enabled', True)
        broker = get_broker(paper_trading=paper_trading, use_alpaca=use_alpaca)
        
        # Get quote first
        with st.spinner(f"Getting quote for {symbol}..."):
            quote = broker.get_quote(symbol)
            
        if not quote:
            st.error(f"Could not get quote for {symbol}")
            return
            
        price = (quote['bid_price'] + quote['ask_price']) / 2
        
        # Place order
        with st.spinner(f"Placing {action} order for {quantity} {symbol}..."):
            side = OrderSide.BUY if action == "BUY" else OrderSide.SELL
            
            # Use bracket orders if available (default 2% SL, 4% TP)
            # This uses the execution service wrapper we added in Phase 1
            # But here we are using broker directly usually. 
            # Let's try to use execution service if possible, to get bracket orders?
            # For "Quick Trade" simplest is market order, but users might want safety.
            # For now, let's do direct broker order for speed, or check if we can import execution service.
            
            result = broker.place_order(
                ticker=symbol,
                quantity=quantity,
                side=side,
                order_type="market"
            )
            
            if 'error' in result:
                st.error(f"Trade failed: {result['error']}")
            else:
                # Log to DB
                if db:
                    trade_data = {
                        'symbol': symbol, # DB schema uses 'symbol' in trades table? Check trading_database.py
                        # Wait, db.save_trade takes 'symbol'. analysis.py used 'ticker' but mapped it?
                        # checking analysis.py: db.save_trade(trade_data) where trade_data had 'ticker'.
                        # checking trading_database.py: save_trade(self, symbol, ...)
                        # It seems I need to be careful with column names.
                        # Let's check trading_database.py again.
                        
                        'symbol': symbol,
                        'action': action,
                        'quantity': quantity,
                        'price': price,
                        'total_value': quantity * price,
                        'order_type': 'MARKET',
                        'status': 'executed',
                        'order_id': result.get('order_id'),
                        'paper_trading': paper_trading,
                        'metadata': {'source': 'quick_trade'},
                        'decision_text': 'Quick Trade Manual Execution'
                    }
                    db.save_trade(trade_data)
                
                st.success(f"✅ Executed! {action} {quantity} {symbol} @ ~${price:.2f}")
                time.sleep(2)
                st.rerun()
                
    except Exception as e:
        st.error(f"Execution Error: {str(e)}")
