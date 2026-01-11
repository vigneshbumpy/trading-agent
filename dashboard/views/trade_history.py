"""
Trade History page showing all executed trades
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.utils.database import TradingDatabase

db = TradingDatabase()


def show():
    """Display trade history page"""
    st.markdown("<h1 class='main-header'>📊 Trade History</h1>", unsafe_allow_html=True)

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        ticker_filter = st.text_input("Filter by Ticker", value="", placeholder="e.g., NVDA")

    with col2:
        action_filter = st.selectbox("Filter by Action", options=["All", "BUY", "SELL"])

    with col3:
        limit = st.number_input("Number of Trades", min_value=10, max_value=500, value=50, step=10)

    # Get trades
    if ticker_filter:
        trades = db.get_trades(ticker=ticker_filter.upper(), limit=limit)
    else:
        trades = db.get_trades(limit=limit)

    # Apply action filter
    if action_filter != "All":
        trades = [t for t in trades if t['action'] == action_filter]

    if trades:
        trades_df = pd.DataFrame(trades)

        # Summary Stats
        st.markdown("## 📈 Trading Summary")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_trades = len(trades_df)
            st.metric("Total Trades", total_trades)

        with col2:
            buy_count = len(trades_df[trades_df['action'] == 'BUY'])
            st.metric("Buy Orders", buy_count)

        with col3:
            sell_count = len(trades_df[trades_df['action'] == 'SELL'])
            st.metric("Sell Orders", sell_count)

        with col4:
            total_volume = trades_df['total_value'].sum()
            st.metric("Total Volume", f"${total_volume:,.2f}")

        st.markdown("---")

        # Trades Table
        st.markdown("## 📋 Trade Details")

        # Format the dataframe for display
        display_df = trades_df.copy()
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        display_df['trade_date'] = pd.to_datetime(display_df['trade_date']).dt.strftime('%Y-%m-%d')

        # Select and rename columns
        display_df = display_df[[
            'id', 'ticker', 'action', 'quantity', 'price', 'total_value',
            'trade_date', 'execution_type', 'status', 'created_at'
        ]]

        display_df.columns = [
            'ID', 'Ticker', 'Action', 'Qty', 'Price', 'Total Value',
            'Trade Date', 'Type', 'Status', 'Executed At'
        ]

        # Style the dataframe
        st.dataframe(
            display_df.style.format({
                'Price': '${:.2f}',
                'Total Value': '${:,.2f}'
            }).applymap(
                lambda x: 'background-color: #d4edda' if x == 'BUY' else ('background-color: #f8d7da' if x == 'SELL' else ''),
                subset=['Action']
            ),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        # Visualizations
        st.markdown("## 📊 Trading Analytics")

        col1, col2 = st.columns(2)

        with col1:
            # Trade action distribution
            action_counts = trades_df['action'].value_counts()
            fig_pie = px.pie(
                values=action_counts.values,
                names=action_counts.index,
                title='Trade Distribution (Buy vs Sell)',
                color=action_counts.index,
                color_discrete_map={'BUY': 'green', 'SELL': 'red'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            # Trading volume by ticker
            volume_by_ticker = trades_df.groupby('ticker')['total_value'].sum().sort_values(ascending=False).head(10)
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=volume_by_ticker.index,
                    y=volume_by_ticker.values,
                    marker_color='steelblue'
                )
            ])
            fig_bar.update_layout(
                title='Top 10 Tickers by Trading Volume',
                xaxis_title='Ticker',
                yaxis_title='Total Volume ($)',
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Timeline
        if 'created_at' in trades_df.columns:
            trades_df['created_at_dt'] = pd.to_datetime(trades_df['created_at'])
            trades_timeline = trades_df.groupby([trades_df['created_at_dt'].dt.date, 'action']).size().reset_index(name='count')

            fig_timeline = px.line(
                trades_timeline,
                x='created_at_dt',
                y='count',
                color='action',
                title='Trade Activity Over Time',
                labels={'created_at_dt': 'Date', 'count': 'Number of Trades'},
                color_discrete_map={'BUY': 'green', 'SELL': 'red'}
            )
            st.plotly_chart(fig_timeline, use_container_width=True)

        st.markdown("---")

        # Export functionality
        st.markdown("## 💾 Export Data")

        col1, col2 = st.columns(2)

        with col1:
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"trade_history_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

    else:
        st.info("No trades found. Execute your first trade from the Stock Analysis page.")

        if st.button("🔍 Analyze Stocks", use_container_width=True):
            st.switch_page("pages/analysis.py")
