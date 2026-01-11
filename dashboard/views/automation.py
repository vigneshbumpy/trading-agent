"""
Autonomous Trading Control Panel
Fast, fully automatic trading - no manual watchlist needed
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import json
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.utils.database import TradingDatabase

db = TradingDatabase()


def show():
    """Display autonomous trading control panel"""
    
    # Header
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    ">
        <h1 style="color: white; margin: 0; font-size: 2.5rem;">🤖 Autonomous Trading</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">
            Fully automatic • News-driven • Fast analysis • Paper trading
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'autonomous_trader' not in st.session_state:
        st.session_state.autonomous_trader = None
    if 'trade_log' not in st.session_state:
        st.session_state.trade_log = []
    if 'analysis_log' not in st.session_state:
        st.session_state.analysis_log = []
    
    # Trading Mode Banner
    paper_trading = st.session_state.get('paper_trading_enabled', True)
    
    if paper_trading:
        st.success("📝 **PAPER TRADING MODE** — All trades are simulated. Your money is safe!")
    else:
        st.error("🔴 **LIVE TRADING MODE** — Real money at risk!")
    
    st.markdown("---")
    
    # Status Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    trader = st.session_state.autonomous_trader
    
    with col1:
        if trader and trader.is_running:
            if trader.is_paused:
                st.warning("⏸️ **PAUSED**")
            else:
                st.success("🟢 **RUNNING**")
        else:
            st.info("⚪ **STOPPED**")
    
    with col2:
        trades = len(st.session_state.trade_log) if trader else 0
        st.metric("Trades Today", trades)
    
    with col3:
        analyses = len(st.session_state.analysis_log) if trader else 0
        st.metric("Analyses", analyses)
    
    with col4:
        positions = len(trader.positions) if trader else 0
        st.metric("Open Positions", positions)
    
    st.markdown("---")
    
    # Control Panel
    st.markdown("## 🎮 Control Panel")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        start_clicked = st.button(
            "🚀 **START**",
            type="primary",
            use_container_width=True,
            disabled=trader is not None and trader.is_running
        )
    
    with col2:
        pause_clicked = st.button(
            "⏸️ Pause",
            use_container_width=True,
            disabled=trader is None or not trader.is_running
        )
    
    with col3:
        resume_clicked = st.button(
            "▶️ Resume",
            use_container_width=True,
            disabled=trader is None or not trader.is_paused
        )
    
    with col4:
        stop_clicked = st.button(
            "⏹️ Stop",
            use_container_width=True,
            disabled=trader is None or not trader.is_running
        )
    
    # Handle button clicks
    if start_clicked:
        _start_autonomous_trading()
    
    if pause_clicked and trader:
        trader.pause()
        st.warning("⏸️ Trading paused")
        st.rerun()
    
    if resume_clicked and trader:
        trader.resume()
        st.success("▶️ Trading resumed")
        st.rerun()
    
    if stop_clicked and trader:
        trader.stop()
        st.session_state.autonomous_trader = None
        st.info("⏹️ Trading stopped")
        st.rerun()
    
    st.markdown("---")
    
    # How It Works
    with st.expander("ℹ️ How Autonomous Trading Works", expanded=False):
        st.markdown("""
        ### 🔄 Automatic Trading Cycle (Every 60 seconds)
        
        1. **📰 News Discovery**
           - Scans financial news sources
           - Identifies trending stocks automatically
           - No manual watchlist needed!
        
        2. **⚡ Fast Analysis**
           - Quick technical indicators (RSI, MA, Volume)
           - Combines news sentiment + technical signals
           - 10x faster than multi-agent system
        
        3. **🎯 Trade Execution**
           - Only trades when confidence > 65%
           - Automatic position sizing (2% per trade)
           - Paper trading by default (safe!)
        
        ### 📊 What Gets Traded
        - 🇺🇸 **US Stocks**: AAPL, NVDA, TSLA, etc.
        - 🇮🇳 **Indian Stocks**: RELIANCE, TCS, etc.
        - ₿ **Crypto**: BTC, ETH, SOL (24/7)
        
        ### 🛡️ Safety Features
        - Paper trading by default
        - Max 5 positions at once
        - 2% position size limit
        - 65% minimum confidence threshold
        """)
    
    # Configuration
    with st.expander("⚙️ Configuration", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            scan_interval = st.slider(
                "Scan Interval (seconds)",
                min_value=30,
                max_value=300,
                value=60,
                step=10,
                help="How often to scan for opportunities"
            )
            
            min_confidence = st.slider(
                "Minimum Confidence",
                min_value=0.5,
                max_value=0.9,
                value=0.65,
                step=0.05,
                help="Only trade when confidence exceeds this"
            )
        
        with col2:
            max_positions = st.slider(
                "Max Positions",
                min_value=1,
                max_value=10,
                value=5,
                help="Maximum number of open positions"
            )
            
            position_size = st.slider(
                "Position Size (%)",
                min_value=1,
                max_value=10,
                value=2,
                help="Percentage of portfolio per trade"
            )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            include_us = st.checkbox("🇺🇸 US Stocks", value=True)
        with col2:
            include_india = st.checkbox("🇮🇳 Indian Stocks", value=True)
        with col3:
            include_crypto = st.checkbox("₿ Crypto", value=True)
        
        if st.button("💾 Save Configuration"):
            config = {
                'scan_interval': scan_interval,
                'min_confidence': min_confidence,
                'max_positions': max_positions,
                'position_size_pct': position_size / 100,
                'include_crypto': include_crypto,
                'include_indian': include_india,
                'include_us': include_us
            }
            db.save_setting('autonomous_config', json.dumps(config))
            st.success("✅ Configuration saved!")
    
    st.markdown("---")
    
    # Live Activity Feed
    st.markdown("## 📊 Live Activity")
    
    tab1, tab2, tab3 = st.tabs(["🔄 Recent Trades", "📈 Analyses", "📂 Positions"])
    
    with tab1:
        trades = st.session_state.trade_log[-20:][::-1]  # Last 20, reversed
        
        if trades:
            for trade in trades:
                status_icon = "✅" if trade.get('result', {}).get('status') == 'success' else "❌"
                action_color = "#00d084" if trade['action'] == 'BUY' else "#ff4757"
                
                st.markdown(f"""
                <div style="
                    background: #f8f9fa;
                    border-left: 4px solid {action_color};
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 0.5rem;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: 1.1rem;">{status_icon} {trade['action']} {trade['ticker']}</strong>
                            <span style="color: #666; margin-left: 1rem;">Qty: {trade['quantity']}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #666; font-size: 0.9rem;">{trade['timestamp'][-8:]}</div>
                            <div style="color: {action_color};">Confidence: {trade['confidence']:.0%}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No trades yet. Start autonomous trading to see activity here.")
    
    with tab2:
        analyses = st.session_state.analysis_log[-30:][::-1]
        
        if analyses:
            for analysis in analyses:
                action = analysis['action']
                confidence = analysis['confidence']
                
                if action == 'BUY':
                    color = "#00d084"
                    icon = "📈"
                elif action == 'SELL':
                    color = "#ff4757"
                    icon = "📉"
                else:
                    color = "#95a5a6"
                    icon = "⏸️"
                
                actionable = "✓" if confidence >= 0.65 and action != 'HOLD' else ""
                
                st.markdown(f"""
                <div style="
                    display: flex;
                    justify-content: space-between;
                    padding: 0.5rem 1rem;
                    background: {color}11;
                    border-radius: 6px;
                    margin-bottom: 0.3rem;
                ">
                    <span>{icon} <strong>{analysis['ticker']}</strong> → {action} {actionable}</span>
                    <span style="color: {color};">{confidence:.0%}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No analyses yet. Start autonomous trading to see analysis results.")
    
    with tab3:
        if trader and trader.positions:
            for ticker, pos in trader.positions.items():
                st.markdown(f"""
                <div style="
                    background: #e8f5e9;
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 0.5rem;
                ">
                    <strong>{ticker}</strong>
                    <span style="margin-left: 1rem;">Qty: {pos['quantity']}</span>
                    <span style="margin-left: 1rem; color: #666;">Since: {pos['entry_time'][-8:]}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No open positions")
    
    st.markdown("---")
    
    # Stats
    if trader:
        st.markdown("## 📈 Statistics")
        
        stats = trader.stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Analyses", stats['total_analyses'])
        with col2:
            st.metric("Total Trades", stats['total_trades'])
        with col3:
            success_rate = (stats['successful_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")
        with col4:
            st.metric("Errors", len(trader.errors))
    
    # Auto-refresh
    if trader and trader.is_running and not trader.is_paused:
        time.sleep(0.1)  # Small delay
        st.rerun()


def _start_autonomous_trading():
    """Start autonomous trading"""
    try:
        from tradingagents.services.autonomous_trader import create_autonomous_trader
        
        # Get config
        config_json = db.get_setting('autonomous_config', '{}')
        config = json.loads(config_json) if config_json else {}
        
        # Ensure paper trading
        paper_trading = st.session_state.get('paper_trading_enabled', True)
        
        # Callbacks to update UI
        def on_trade(trade):
            st.session_state.trade_log.append(trade)
        
        def on_analysis(analysis):
            st.session_state.analysis_log.append(analysis)
        
        # Create trader
        trader = create_autonomous_trader(
            paper_trading=paper_trading,
            config=config,
            on_trade=on_trade,
            on_analysis=on_analysis
        )
        
        # Start
        trader.start()
        
        st.session_state.autonomous_trader = trader
        st.session_state.trade_log = []
        st.session_state.analysis_log = []
        
        mode = "📝 PAPER" if paper_trading else "🔴 LIVE"
        st.success(f"🚀 Autonomous trading started in {mode} mode!")
        st.balloons()
        
        st.rerun()
        
    except Exception as e:
        st.error(f"Failed to start: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
