"""
Portfolio page with market-segmented views
Stocks (US + Indian) and Crypto tracking with detailed analytics
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.utils.database import TradingDatabase
from dashboard.utils.broker import get_broker

db = TradingDatabase()

# Custom colors
COLORS = {
    'stocks_us': '#1f77b4',
    'stocks_india': '#ff7f0e',
    'crypto': '#f7931a',
    'btc': '#f7931a',
    'eth': '#627eea',
    'positive': '#00d084',
    'negative': '#ff4757',
    'neutral': '#95a5a6',
}

# Crypto detection
CRYPTO_SYMBOLS = {'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'AVAX', 'MATIC', 'LINK',
                  'BTC-USD', 'ETH-USD', 'SOL-USD', 'BTCUSD', 'ETHUSD'}


def is_crypto(symbol: str) -> bool:
    symbol_upper = symbol.upper().replace('-', '')
    return (symbol_upper in CRYPTO_SYMBOLS or 
            symbol_upper.endswith('USD') and symbol_upper[:3] in {'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOG'} or
            symbol_upper.endswith('USDT') or
            '-' in symbol and any(c in symbol.upper() for c in ['BTC', 'ETH', 'SOL']))


def is_indian_stock(symbol: str) -> bool:
    return symbol.endswith('.NS') or symbol.endswith('.BO')


def get_market_label(symbol: str) -> tuple:
    """Get market label and color for a symbol"""
    if is_crypto(symbol):
        return '₿ Crypto', COLORS['crypto']
    elif is_indian_stock(symbol):
        return '🇮🇳 India', COLORS['stocks_india']
    else:
        return '🇺🇸 US', COLORS['stocks_us']


def categorize_positions(positions: list) -> dict:
    return {
        'stocks_us': [p for p in positions if not is_crypto(p.get('ticker', '')) and not is_indian_stock(p.get('ticker', ''))],
        'stocks_india': [p for p in positions if is_indian_stock(p.get('ticker', ''))],
        'crypto': [p for p in positions if is_crypto(p.get('ticker', ''))]
    }


def create_performance_chart(positions: list, title: str):
    """Create a horizontal bar chart for performance"""
    if not positions:
        return None
    
    df = pd.DataFrame(positions)
    df = df.sort_values('unrealized_plpc', ascending=True)
    
    colors = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in df['unrealized_plpc']]
    
    fig = go.Figure(data=[go.Bar(
        y=df['ticker'],
        x=df['unrealized_plpc'],
        orientation='h',
        marker_color=colors,
        text=[f"{v:.1f}%" for v in df['unrealized_plpc']],
        textposition='outside'
    )])
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        xaxis_title='Return (%)',
        yaxis_title='',
        showlegend=False,
        height=max(250, len(positions) * 40),
        margin=dict(l=80, r=60, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#eee', zeroline=True, zerolinecolor='#666'),
        yaxis=dict(showgrid=False)
    )
    
    return fig


def create_treemap(positions: list, title: str):
    """Create a treemap for position sizing"""
    if not positions:
        return None
    
    df = pd.DataFrame(positions)
    
    colors = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in df['unrealized_pl']]
    
    fig = go.Figure(go.Treemap(
        labels=df['ticker'],
        parents=[''] * len(df),
        values=df['market_value'],
        marker=dict(colors=colors),
        textinfo='label+value+percent root',
        texttemplate='%{label}<br>$%{value:,.0f}<br>%{percentRoot:.1%}',
        hovertemplate='<b>%{label}</b><br>Value: $%{value:,.2f}<br>Weight: %{percentRoot:.1%}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        margin=dict(t=60, b=20, l=20, r=20),
        height=400
    )
    
    return fig


def show_stock_portfolio(positions_us: list, positions_india: list):
    """Stock portfolio section"""
    
    all_stocks = positions_us + positions_india
    
    if not all_stocks:
        st.info("📊 No stock positions. Start by analyzing and trading stocks!")
        return
    
    # Summary metrics
    total_us = sum(p.get('market_value', 0) for p in positions_us)
    total_india = sum(p.get('market_value', 0) for p in positions_india)
    pl_us = sum(p.get('unrealized_pl', 0) for p in positions_us)
    pl_india = sum(p.get('unrealized_pl', 0) for p in positions_india)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🇺🇸 US Value", f"${total_us:,.2f}", f"${pl_us:+,.2f}")
    with col2:
        st.metric("🇮🇳 India Value", f"${total_india:,.2f}", f"${pl_india:+,.2f}")
    with col3:
        st.metric("📊 Total", f"${total_us + total_india:,.2f}")
    with col4:
        st.metric("💹 Total P/L", f"${pl_us + pl_india:,.2f}")
    
    st.markdown("---")
    
    # Tabs for US and Indian stocks
    tab_all, tab_us, tab_india = st.tabs(["All Stocks", "🇺🇸 US Stocks", "🇮🇳 Indian Stocks"])
    
    with tab_all:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = create_treemap(all_stocks, "Stock Position Sizes")
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = create_performance_chart(all_stocks, "Stock Performance")
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        # Positions table
        st.markdown("### 📋 All Stock Positions")
        show_detailed_positions_table(all_stocks)
    
    with tab_us:
        if positions_us:
            col1, col2 = st.columns(2)
            with col1:
                fig = create_treemap(positions_us, "US Position Sizes")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = create_performance_chart(positions_us, "US Performance")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 📋 US Stock Positions")
            show_detailed_positions_table(positions_us)
        else:
            st.info("No US stock positions")
    
    with tab_india:
        if positions_india:
            col1, col2 = st.columns(2)
            with col1:
                fig = create_treemap(positions_india, "Indian Position Sizes")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = create_performance_chart(positions_india, "Indian Performance")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 📋 Indian Stock Positions")
            show_detailed_positions_table(positions_india)
        else:
            st.info("No Indian stock positions")


def show_crypto_portfolio(positions: list):
    """Crypto portfolio section with BTC/ETH focus"""
    
    if not positions:
        st.info("₿ No crypto positions. Start trading Bitcoin and other cryptocurrencies!")
        return
    
    # Calculate totals
    total_value = sum(p.get('market_value', 0) for p in positions)
    total_pl = sum(p.get('unrealized_pl', 0) for p in positions)
    
    # Find BTC and ETH
    btc_pos = next((p for p in positions if 'BTC' in p.get('ticker', '').upper()), None)
    eth_pos = next((p for p in positions if 'ETH' in p.get('ticker', '').upper()), None)
    
    btc_value = btc_pos.get('market_value', 0) if btc_pos else 0
    eth_value = eth_pos.get('market_value', 0) if eth_pos else 0
    altcoin_value = total_value - btc_value - eth_value
    
    # Header metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Total Crypto", f"${total_value:,.2f}", f"${total_pl:+,.2f}")
    with col2:
        btc_dom = (btc_value / total_value * 100) if total_value > 0 else 0
        st.metric("₿ Bitcoin", f"${btc_value:,.2f}", f"{btc_dom:.1f}% dom")
    with col3:
        eth_dom = (eth_value / total_value * 100) if total_value > 0 else 0
        st.metric("Ξ Ethereum", f"${eth_value:,.2f}", f"{eth_dom:.1f}%")
    with col4:
        alt_dom = (altcoin_value / total_value * 100) if total_value > 0 else 0
        st.metric("🪙 Altcoins", f"${altcoin_value:,.2f}", f"{alt_dom:.1f}%")
    with col5:
        pl_pct = (total_pl / (total_value - total_pl) * 100) if (total_value - total_pl) > 0 else 0
        st.metric("📈 Return", f"{pl_pct:+.2f}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Dominance chart
        st.markdown("### 🥧 Portfolio Dominance")
        
        labels = []
        values = []
        colors = []
        
        if btc_value > 0:
            labels.append('Bitcoin')
            values.append(btc_value)
            colors.append(COLORS['btc'])
        
        if eth_value > 0:
            labels.append('Ethereum')
            values.append(eth_value)
            colors.append(COLORS['eth'])
        
        # Add other coins
        for p in positions:
            ticker = p.get('ticker', '')
            if 'BTC' not in ticker.upper() and 'ETH' not in ticker.upper():
                labels.append(ticker)
                values.append(p.get('market_value', 0))
                colors.append(px.colors.qualitative.Set2[len(colors) % 8])
        
        fig = go.Figure(data=[go.Pie(
            values=values,
            labels=labels,
            hole=0.5,
            marker_colors=colors,
            textinfo='label+percent',
            textposition='outside',
            pull=[0.05 if l == 'Bitcoin' else 0 for l in labels]
        )])
        
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation='h', y=-0.1),
            margin=dict(t=20, b=60, l=20, r=20),
            height=400,
            annotations=[dict(
                text=f'${total_value:,.0f}',
                x=0.5, y=0.5,
                font_size=20,
                showarrow=False
            )]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Performance chart
        st.markdown("### 📊 Performance by Coin")
        fig = create_performance_chart(positions, "")
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    # Treemap
    st.markdown("### 🗺️ Position Size Map")
    fig = create_treemap(positions, "")
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed positions
    st.markdown("### 📋 Crypto Positions")
    show_detailed_positions_table(positions, is_crypto=True)


def show_detailed_positions_table(positions: list, is_crypto: bool = False):
    """Show detailed positions table with actions"""
    
    if not positions:
        return
    
    df = pd.DataFrame(positions)
    
    # Add market label
    df['Market'] = df['ticker'].apply(lambda x: get_market_label(x)[0])
    
    # Format for display
    format_dict = {
        'avg_price': '${:.2f}',
        'current_price': '${:.2f}',
        'market_value': '${:,.2f}',
        'unrealized_pl': '${:,.2f}',
        'unrealized_plpc': '{:+.2f}%'
    }
    
    display_cols = ['Market', 'ticker', 'quantity', 'avg_price', 'current_price', 'market_value', 'unrealized_pl', 'unrealized_plpc']
    display_names = ['Market', 'Asset', 'Qty', 'Avg Price', 'Current', 'Value', 'P/L ($)', 'P/L (%)']
    
    available = [c for c in display_cols if c in df.columns]
    df_show = df[available].copy()
    
    col_map = dict(zip(display_cols, display_names))
    df_show.columns = [col_map.get(c, c) for c in df_show.columns]
    
    # Apply styling
    styled = df_show.style
    
    for col, fmt in format_dict.items():
        mapped_col = col_map.get(col, col)
        if mapped_col in df_show.columns:
            styled = styled.format({mapped_col: fmt})
    
    if 'P/L (%)' in df_show.columns:
        styled = styled.background_gradient(subset=['P/L (%)'], cmap='RdYlGn', vmin=-20, vmax=20)
    
    st.dataframe(styled, use_container_width=True, hide_index=True)
    
    # Position actions
    st.markdown("#### 🎯 Position Actions")
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        selected = st.selectbox("Select Position", options=[p['ticker'] for p in positions])
    
    if selected:
        pos = next(p for p in positions if p['ticker'] == selected)
        
        with col2:
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button("📊 Re-analyze", use_container_width=True):
                    st.session_state['analysis_ticker'] = selected
                    st.session_state.current_page = "🔍 Stock Analysis"
                    st.rerun()
            
            with action_col2:
                if st.button("⭐ Add to Watchlist", use_container_width=True):
                    db.add_to_watchlist(selected)
                    st.success(f"Added {selected}")
            
            with action_col3:
                if st.button("💰 Sell Position", type="primary", use_container_width=True):
                    st.session_state['sell_ticker'] = selected
                    st.info(f"Navigate to Trade History to sell {selected}")


def show():
    """Main portfolio display"""
    
    # Header
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    ">
        <h1 style="color: white; margin: 0; font-size: 2.5rem;">💼 Portfolio Management</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Track your stocks and crypto in one place</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get data
    use_alpaca = st.session_state.get('use_alpaca', False)
    paper_trading = st.session_state.get('paper_trading_enabled', True)
    
    try:
        broker = get_broker(paper_trading=paper_trading, use_alpaca=use_alpaca)
        account = broker.get_account()
        positions = broker.get_all_positions()
    except Exception as e:
        st.error(f"Failed to connect to broker: {str(e)}")
        return
    
    # Categorize
    categorized = categorize_positions(positions)
    
    # Calculate totals
    total_stocks = (sum(p.get('market_value', 0) for p in categorized['stocks_us']) +
                   sum(p.get('market_value', 0) for p in categorized['stocks_india']))
    total_crypto = sum(p.get('market_value', 0) for p in categorized['crypto'])
    total_pl = sum(p.get('unrealized_pl', 0) for p in positions)
    
    # Account summary
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Total Value", f"${account.get('portfolio_value', total_stocks + total_crypto):,.2f}")
    with col2:
        st.metric("📊 Stocks", f"${total_stocks:,.2f}")
    with col3:
        st.metric("₿ Crypto", f"${total_crypto:,.2f}")
    with col4:
        st.metric("💵 Cash", f"${account.get('cash', 0):,.2f}")
    with col5:
        st.metric("💹 Total P/L", f"${total_pl:,.2f}")
    
    st.markdown("---")
    
    # Market tabs
    tab_overview, tab_stocks, tab_crypto = st.tabs(["🌍 Overview", "📊 Stocks", "₿ Crypto"])
    
    with tab_overview:
        st.markdown("### 📊 Portfolio Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Asset class allocation
            if total_stocks > 0 or total_crypto > 0:
                fig = go.Figure(data=[go.Pie(
                    values=[total_stocks, total_crypto],
                    labels=['Stocks', 'Crypto'],
                    hole=0.6,
                    marker_colors=[COLORS['stocks_us'], COLORS['crypto']],
                    textinfo='label+percent',
                    textposition='outside'
                )])
                
                fig.update_layout(
                    title=dict(text="Asset Class Allocation", x=0.5),
                    showlegend=True,
                    height=400,
                    margin=dict(t=60, b=40),
                    annotations=[dict(
                        text=f'${total_stocks + total_crypto:,.0f}',
                        x=0.5, y=0.5,
                        font_size=18,
                        showarrow=False
                    )]
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No positions to display")
        
        with col2:
            # Market breakdown
            if positions:
                us_val = sum(p.get('market_value', 0) for p in categorized['stocks_us'])
                india_val = sum(p.get('market_value', 0) for p in categorized['stocks_india'])
                crypto_val = sum(p.get('market_value', 0) for p in categorized['crypto'])
                
                fig = go.Figure(data=[go.Bar(
                    x=['🇺🇸 US Stocks', '🇮🇳 Indian Stocks', '₿ Crypto'],
                    y=[us_val, india_val, crypto_val],
                    marker_color=[COLORS['stocks_us'], COLORS['stocks_india'], COLORS['crypto']],
                    text=[f'${v:,.0f}' for v in [us_val, india_val, crypto_val]],
                    textposition='outside'
                )])
                
                fig.update_layout(
                    title=dict(text="Market Breakdown", x=0.5),
                    showlegend=False,
                    height=400,
                    margin=dict(t=60, b=40),
                    yaxis_title='Value ($)'
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # All positions treemap
        if positions:
            st.markdown("### 🗺️ All Positions Map")
            fig = create_treemap(positions, "")
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    
    with tab_stocks:
        show_stock_portfolio(categorized['stocks_us'], categorized['stocks_india'])
    
    with tab_crypto:
        show_crypto_portfolio(categorized['crypto'])
    
    # Watchlist
    st.markdown("---")
    st.markdown("### ⭐ Watchlist")
    
    watchlist = db.get_watchlist()
    
    if watchlist:
        cols = st.columns(4)
        for i, item in enumerate(watchlist):
            with cols[i % 4]:
                ticker = item['ticker']
                market_label, color = get_market_label(ticker)
                
                st.markdown(f"""
                <div style="
                    background: {color}11;
                    border-left: 3px solid {color};
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 0.5rem;
                ">
                    <div style="font-size: 0.8rem; color: #666;">{market_label}</div>
                    <div style="font-size: 1.2rem; font-weight: bold;">{ticker}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Analyze", key=f"wl_{ticker}", use_container_width=True):
                    st.session_state['analysis_ticker'] = ticker
                    st.session_state.current_page = "🔍 Stock Analysis"
                    st.rerun()
    else:
        st.info("No stocks in watchlist")
