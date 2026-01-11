"""
Home/Dashboard page with market-segmented views
Stocks (US + Indian) and Crypto tracking with rich visualizations
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.utils.database import TradingDatabase
from dashboard.utils.broker import get_broker

db = TradingDatabase()

# Custom colors for different markets
COLORS = {
    'stocks_us': '#1f77b4',      # Blue
    'stocks_india': '#ff7f0e',   # Orange
    'crypto': '#f7931a',         # Bitcoin orange
    'positive': '#00d084',       # Green
    'negative': '#ff4757',       # Red
    'neutral': '#95a5a6',        # Gray
}

# Crypto symbols detection
CRYPTO_SYMBOLS = {'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'AVAX', 'MATIC', 'LINK',
                  'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'BTCUSD', 'ETHUSD'}


def is_crypto(symbol: str) -> bool:
    """Check if a symbol is cryptocurrency"""
    symbol_upper = symbol.upper().replace('-', '')
    return (symbol_upper in CRYPTO_SYMBOLS or 
            symbol_upper.endswith('USD') and symbol_upper[:3] in {'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOG'} or
            symbol_upper.endswith('USDT') or
            '-' in symbol and any(c in symbol.upper() for c in ['BTC', 'ETH', 'SOL']))


def is_indian_stock(symbol: str) -> bool:
    """Check if a symbol is Indian stock"""
    return symbol.endswith('.NS') or symbol.endswith('.BO')


def categorize_positions(positions: list) -> dict:
    """Categorize positions by market type"""
    categorized = {
        'stocks_us': [],
        'stocks_india': [],
        'crypto': []
    }
    
    for pos in positions:
        ticker = pos.get('ticker', pos.get('symbol', ''))
        if is_crypto(ticker):
            categorized['crypto'].append(pos)
        elif is_indian_stock(ticker):
            categorized['stocks_india'].append(pos)
        else:
            categorized['stocks_us'].append(pos)
    
    return categorized


def create_market_summary_card(title: str, value: float, change: float, icon: str, color: str):
    """Create a styled market summary card"""
    change_color = COLORS['positive'] if change >= 0 else COLORS['negative']
    change_icon = '▲' if change >= 0 else '▼'
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}22 0%, {color}11 100%);
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    ">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="color: #666; font-size: 0.9rem;">{title}</div>
        <div style="font-size: 1.8rem; font-weight: bold; color: #1a1a2e;">${value:,.2f}</div>
        <div style="color: {change_color}; font-size: 0.95rem; margin-top: 0.3rem;">
            {change_icon} {abs(change):.2f}%
        </div>
    </div>
    """, unsafe_allow_html=True)


def create_donut_chart(data: list, names: list, title: str, colors: list = None):
    """Create a styled donut chart"""
    fig = go.Figure(data=[go.Pie(
        values=data,
        labels=names,
        hole=0.6,
        marker_colors=colors or px.colors.qualitative.Set2,
        textinfo='label+percent',
        textposition='outside',
        pull=[0.02] * len(data)
    )])
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.2),
        margin=dict(t=60, b=60, l=20, r=20),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_bar_chart(tickers: list, values: list, title: str, y_label: str):
    """Create a styled bar chart for P/L"""
    colors = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in values]
    
    fig = go.Figure(data=[go.Bar(
        x=tickers,
        y=values,
        marker_color=colors,
        text=[f"${v:,.0f}" for v in values],
        textposition='outside'
    )])
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        xaxis_title='',
        yaxis_title=y_label,
        showlegend=False,
        margin=dict(t=60, b=40, l=60, r=20),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#eee')
    )
    
    return fig


def show_stocks_dashboard(positions_us: list, positions_india: list):
    """Display stocks dashboard (US + India)"""
    
    all_stock_positions = positions_us + positions_india
    
    if not all_stock_positions:
        st.info("📊 No stock positions yet. Start by analyzing stocks!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### 🇺🇸 US Stocks
            - **Broker**: Alpaca (Paper & Live)
            - **Markets**: NYSE, NASDAQ
            - **Examples**: AAPL, NVDA, TSLA, MSFT
            """)
        with col2:
            st.markdown("""
            ### 🇮🇳 Indian Stocks
            - **Brokers**: Zerodha, Upstox
            - **Markets**: NSE, BSE
            - **Examples**: RELIANCE.NS, TCS.NS
            """)
        return
    
    # Calculate totals
    total_us = sum(p.get('market_value', 0) for p in positions_us)
    total_india = sum(p.get('market_value', 0) for p in positions_india)
    total_stocks = total_us + total_india
    
    pl_us = sum(p.get('unrealized_pl', 0) for p in positions_us)
    pl_india = sum(p.get('unrealized_pl', 0) for p in positions_india)
    
    # Summary cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        create_market_summary_card(
            "Total Stock Value", total_stocks,
            ((pl_us + pl_india) / total_stocks * 100) if total_stocks > 0 else 0,
            "📊", COLORS['stocks_us']
        )
    
    with col2:
        create_market_summary_card(
            "US Stocks", total_us,
            (pl_us / total_us * 100) if total_us > 0 else 0,
            "🇺🇸", COLORS['stocks_us']
        )
    
    with col3:
        create_market_summary_card(
            "Indian Stocks", total_india,
            (pl_india / total_india * 100) if total_india > 0 else 0,
            "🇮🇳", COLORS['stocks_india']
        )
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Market allocation
        if total_us > 0 or total_india > 0:
            allocation_data = []
            allocation_names = []
            allocation_colors = []
            
            if total_us > 0:
                allocation_data.append(total_us)
                allocation_names.append('US Stocks')
                allocation_colors.append(COLORS['stocks_us'])
            
            if total_india > 0:
                allocation_data.append(total_india)
                allocation_names.append('Indian Stocks')
                allocation_colors.append(COLORS['stocks_india'])
            
            fig = create_donut_chart(allocation_data, allocation_names, 
                                     "Market Allocation", allocation_colors)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Position P/L
        if all_stock_positions:
            tickers = [p['ticker'] for p in all_stock_positions]
            pls = [p.get('unrealized_pl', 0) for p in all_stock_positions]
            fig = create_bar_chart(tickers, pls, "Unrealized P/L by Position", "P/L ($)")
            st.plotly_chart(fig, use_container_width=True)
    
    # Positions table
    st.markdown("### 📋 Stock Positions")
    
    if positions_us:
        with st.expander("🇺🇸 US Stock Positions", expanded=True):
            show_positions_table(positions_us)
    
    if positions_india:
        with st.expander("🇮🇳 Indian Stock Positions", expanded=True):
            show_positions_table(positions_india)


def show_crypto_dashboard(positions: list):
    """Display crypto dashboard with BTC-focused visualizations"""
    
    if not positions:
        st.info("₿ No crypto positions yet. Start trading Bitcoin and other cryptocurrencies!")
        
        st.markdown("""
        ### 🌐 Supported Cryptocurrencies
        
        | Exchange | Assets | Features |
        |----------|--------|----------|
        | **Binance** | BTC, ETH, SOL, + 350 coins | Spot & Futures |
        | **Coinbase** | BTC, ETH, + 200 coins | Easy on-ramp |
        
        **Popular pairs**: BTC-USD, ETH-USD, SOL-USD
        """)
        return
    
    # Calculate totals
    total_crypto = sum(p.get('market_value', 0) for p in positions)
    total_pl = sum(p.get('unrealized_pl', 0) for p in positions)
    
    # Find BTC position
    btc_position = next((p for p in positions if 'BTC' in p.get('ticker', '').upper()), None)
    btc_value = btc_position.get('market_value', 0) if btc_position else 0
    btc_pl = btc_position.get('unrealized_pl', 0) if btc_position else 0
    
    # ETH position
    eth_position = next((p for p in positions if 'ETH' in p.get('ticker', '').upper()), None)
    eth_value = eth_position.get('market_value', 0) if eth_position else 0
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        create_market_summary_card(
            "Total Crypto", total_crypto,
            (total_pl / total_crypto * 100) if total_crypto > 0 else 0,
            "💰", COLORS['crypto']
        )
    
    with col2:
        btc_dominance = (btc_value / total_crypto * 100) if total_crypto > 0 else 0
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #f7931a22 0%, #f7931a11 100%);
            border-left: 4px solid #f7931a;
            border-radius: 8px;
            padding: 1.2rem;
        ">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">₿</div>
            <div style="color: #666; font-size: 0.9rem;">Bitcoin Value</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #1a1a2e;">${btc_value:,.2f}</div>
            <div style="color: #666; font-size: 0.9rem; margin-top: 0.3rem;">
                Dominance: {btc_dominance:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #627eea22 0%, #627eea11 100%);
            border-left: 4px solid #627eea;
            border-radius: 8px;
            padding: 1.2rem;
        ">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">Ξ</div>
            <div style="color: #666; font-size: 0.9rem;">Ethereum Value</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: #1a1a2e;">${eth_value:,.2f}</div>
            <div style="color: #666; font-size: 0.9rem; margin-top: 0.3rem;">
                {(eth_value / total_crypto * 100) if total_crypto > 0 else 0:.1f}% of portfolio
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pl_color = COLORS['positive'] if total_pl >= 0 else COLORS['negative']
        pl_icon = '▲' if total_pl >= 0 else '▼'
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {pl_color}22 0%, {pl_color}11 100%);
            border-left: 4px solid {pl_color};
            border-radius: 8px;
            padding: 1.2rem;
        ">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📈</div>
            <div style="color: #666; font-size: 0.9rem;">Total P/L</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: {pl_color};">{pl_icon} ${abs(total_pl):,.2f}</div>
            <div style="color: {pl_color}; font-size: 0.9rem; margin-top: 0.3rem;">
                {(total_pl / total_crypto * 100) if total_crypto > 0 else 0:+.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Crypto allocation donut
        tickers = [p['ticker'] for p in positions]
        values = [p.get('market_value', 0) for p in positions]
        
        # Custom colors for crypto
        crypto_colors = ['#f7931a', '#627eea', '#14f195', '#e84142', '#2775ca', '#26a17b']
        fig = create_donut_chart(values, tickers, "Crypto Portfolio Allocation", 
                                 crypto_colors[:len(tickers)])
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # P/L by coin
        tickers = [p['ticker'] for p in positions]
        pls = [p.get('unrealized_pl', 0) for p in positions]
        fig = create_bar_chart(tickers, pls, "Unrealized P/L by Coin", "P/L ($)")
        st.plotly_chart(fig, use_container_width=True)
    
    # Positions table
    st.markdown("### 📋 Crypto Positions")
    show_positions_table(positions, is_crypto=True)


def show_positions_table(positions: list, is_crypto: bool = False):
    """Display positions with actionable buttons"""
    if not positions:
        st.info("No positions")
        return
        
    # Header
    cols = st.columns([1.5, 1, 1, 1, 1, 2])
    cols[0].markdown("**Asset**")
    cols[1].markdown("**Qty**")
    cols[2].markdown("**Avg**")
    cols[3].markdown("**Price**")
    cols[4].markdown("**P/L**")
    cols[5].markdown("**Actions**")
    
    st.markdown("---")
    
    for pos in positions:
        ticker = pos.get('ticker', pos.get('symbol', ''))
        qty = pos.get('quantity', 0)
        avg = pos.get('avg_price', 0)
        current = pos.get('current_price', 0)
        pl = pos.get('unrealized_pl', 0)
        pl_pct = pos.get('unrealized_plpc', 0)
        
        # Style P/L
        pl_color = "green" if pl >= 0 else "red"
        
        cols = st.columns([1.5, 1, 1, 1, 1, 2])
        
        with cols[0]:
            st.markdown(f"**{ticker}**")
        with cols[1]:
            st.markdown(f"{qty}")
        with cols[2]:
            st.markdown(f"${avg:.2f}")
        with cols[3]:
            st.markdown(f"${current:.2f}")
        with cols[4]:
            st.markdown(f":{pl_color}[{pl_pct:+.2f}%]")
            
        with cols[5]:
            # Action buttons
            b1, b2, b3 = st.columns(3)
            if b1.button("➕", key=f"buy_{ticker}", help="Buy more", use_container_width=True):
                st.session_state.qt_symbol = ticker
                st.session_state.qt_action = "BUY"
                st.rerun()
                
            if b2.button("➖", key=f"sell_{ticker}", help="Sell some", use_container_width=True):
                st.session_state.qt_symbol = ticker
                st.session_state.qt_action = "SELL"
                st.rerun()
                
            if b3.button("✖️", key=f"close_{ticker}", help="Close position", use_container_width=True):
                st.session_state.qt_symbol = ticker
                st.session_state.qt_action = "SELL"
                st.session_state.qt_quantity = int(qty)
                st.rerun()
        
        st.markdown("<div style='margin: -10px 0 10px 0; border-bottom: 1px solid #f0f0f0;'></div>", unsafe_allow_html=True)


def show():
    """Main dashboard display"""
    
    # Header with gradient
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    ">
        <h1 style="color: white; margin: 0; font-size: 2.5rem;">📊 Trading Dashboard</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Multi-Market Portfolio Tracker</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get broker data
    use_alpaca = st.session_state.get('use_alpaca', False)
    paper_trading = st.session_state.get('paper_trading_enabled', True)
    
    try:
        broker = get_broker(paper_trading=paper_trading, use_alpaca=use_alpaca)
        account = broker.get_account()
        positions = broker.get_all_positions()
    except Exception as e:
        st.error(f"Failed to connect to broker: {str(e)}")
        account = {"error": str(e)}
        positions = []
    
    # --- PHASE 4 DASHBOARD IMPROVEMENTS ---
    from dashboard.components.quick_trade import render_quick_trade
    from dashboard.components.live_prices import render_live_prices, get_default_watchlist

    # 1. Live Prices Ticker
    watchlist = db.get_watchlist() # Ensure db has this method or fallback
    if not watchlist:
        watchlist = [{"ticker": s} for s in get_default_watchlist()] # Fallback format
    
    # Extract symbols list
    watchlist_symbols = [w.get('ticker', w.get('symbol')) for w in watchlist]
    # Limit to top 6 for layout
    render_live_prices(watchlist_symbols[:6])
    
    st.markdown("---")

    # 2. Quick Trade Widget
    render_quick_trade(db)
    
    # --------------------------------------
    
    # Categorize positions
    categorized = categorize_positions(positions)
    
    # Calculate totals
    total_stocks = (sum(p.get('market_value', 0) for p in categorized['stocks_us']) +
                   sum(p.get('market_value', 0) for p in categorized['stocks_india']))
    total_crypto = sum(p.get('market_value', 0) for p in categorized['crypto'])
    total_portfolio = account.get('portfolio_value', total_stocks + total_crypto)
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Total Portfolio", f"${total_portfolio:,.2f}")
    with col2:
        st.metric("📊 Stocks", f"${total_stocks:,.2f}")
    with col3:
        st.metric("₿ Crypto", f"${total_crypto:,.2f}")
    with col4:
        cash = account.get('cash', 0) if "error" not in account else 0
        st.metric("💵 Cash", f"${cash:,.2f}")
    
    st.markdown("---")
    
    # Market tabs
    tab_stocks, tab_crypto, tab_overview = st.tabs(["📊 Stocks", "₿ Crypto", "🌍 Overview"])
    
    with tab_stocks:
        show_stocks_dashboard(categorized['stocks_us'], categorized['stocks_india'])
    
    with tab_crypto:
        show_crypto_dashboard(categorized['crypto'])
    
    with tab_overview:
        st.markdown("### 🌍 Portfolio Overview")
        
        # Overall allocation
        col1, col2 = st.columns(2)
        
        with col1:
            if total_stocks > 0 or total_crypto > 0:
                fig = create_donut_chart(
                    [total_stocks, total_crypto],
                    ['Stocks', 'Crypto'],
                    "Asset Class Allocation",
                    [COLORS['stocks_us'], COLORS['crypto']]
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No positions to display")
        
        with col2:
            # Recent activity
            st.markdown("### 📋 Recent Analyses")
            recent_analyses = db.get_recent_analyses(limit=5)
            
            if recent_analyses:
                for analysis in recent_analyses:
                    ticker = analysis['ticker']
                    market_icon = "₿" if is_crypto(ticker) else ("🇮🇳" if is_indian_stock(ticker) else "🇺🇸")
                    decision = analysis['decision']
                    decision_color = COLORS['positive'] if decision == 'BUY' else (COLORS['negative'] if decision == 'SELL' else COLORS['neutral'])
                    
                    st.markdown(f"""
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 0.75rem;
                        background: #f8f9fa;
                        border-radius: 8px;
                        margin-bottom: 0.5rem;
                    ">
                        <span>{market_icon} <strong>{ticker}</strong></span>
                        <span style="color: {decision_color}; font-weight: bold;">{decision}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No recent analyses")
        
        # Recent trades
        st.markdown("### 📊 Recent Trades")
        recent_trades = db.get_trades(limit=5)
        
        if recent_trades:
            import pandas as pd
            trades_df = pd.DataFrame(recent_trades)
            
            if 'ticker' in trades_df.columns:
                trades_df['Market'] = trades_df['ticker'].apply(
                    lambda x: '₿' if is_crypto(x) else ('🇮🇳' if is_indian_stock(x) else '🇺🇸')
                )
                
                display_cols = ['Market', 'ticker', 'action', 'quantity', 'price', 'trade_date']
                available = [c for c in display_cols if c in trades_df.columns]
                st.dataframe(trades_df[available], use_container_width=True, hide_index=True)
        else:
            st.info("No trades yet")
    
    # Quick actions
    st.markdown("---")
    st.markdown("### 🚀 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Analyze Stock", use_container_width=True):
            st.session_state.current_page = "🔍 Stock Analysis"
            st.rerun()
    
    with col2:
        if st.button("🤖 Automation", use_container_width=True):
            st.session_state.current_page = "🤖 Automation"
            st.rerun()
    
    with col3:
        if st.button("💼 Portfolio", use_container_width=True):
            st.session_state.current_page = "💼 Portfolio"
            st.rerun()
    
    with col4:
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.current_page = "⚙️ Settings"
            st.rerun()
