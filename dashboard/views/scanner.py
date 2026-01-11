"""
Stock Scanner Dashboard View

Fast bulk stock scanning with configurable criteria.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scanner.config import ScannerConfig, load_config, get_watchlist
from scanner.screener import ValueScreener
from scanner.news_aggregator import NewsAggregator
from scanner.parallel_analyzer import ParallelAnalyzer
from scanner.alerts import AlertManager


def show():
    """Display the stock scanner dashboard"""
    st.markdown("<h1 class='main-header'>🔍 Stock Scanner</h1>", unsafe_allow_html=True)
    st.markdown("Fast bulk scanning: Value + News + AI Analysis")

    # Initialize session state
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = None
    if 'scan_running' not in st.session_state:
        st.session_state.scan_running = False

    # Sidebar: Configuration
    with st.sidebar:
        st.markdown("### Scanner Settings")

        # Watchlist source
        watchlist_source = st.selectbox(
            "Stock Universe",
            ["S&P 500", "NASDAQ 100", "Custom"],
            index=0
        )

        custom_symbols = []
        if watchlist_source == "Custom":
            symbols_input = st.text_area(
                "Enter symbols (comma-separated)",
                "AAPL, MSFT, GOOGL, AMZN, META"
            )
            custom_symbols = [s.strip().upper() for s in symbols_input.split(",")]

        st.markdown("---")
        st.markdown("### Value Filters")

        pe_max = st.slider("Max P/E Ratio", 5.0, 50.0, 15.0)
        pb_max = st.slider("Max P/B Ratio", 0.5, 5.0, 1.5)
        de_max = st.slider("Max Debt/Equity", 0.0, 2.0, 0.5)
        roe_min = st.slider("Min ROE %", 0.0, 30.0, 10.0)
        market_cap_min = st.selectbox(
            "Min Market Cap",
            ["$100M", "$500M", "$1B", "$10B"],
            index=1
        )

        st.markdown("---")
        st.markdown("### Analysis Settings")

        max_analyze = st.slider("Max stocks for AI analysis", 5, 50, 20)
        parallel_workers = st.slider("Parallel workers", 1, 8, 4)

    # Build config from UI
    config = ScannerConfig()
    config.screening.pe_ratio_max = pe_max
    config.screening.pb_ratio_max = pb_max
    config.screening.debt_equity_max = de_max
    config.screening.roe_min = roe_min / 100

    cap_map = {"$100M": 100e6, "$500M": 500e6, "$1B": 1e9, "$10B": 10e9}
    config.screening.market_cap_min = cap_map[market_cap_min]

    config.analysis.max_stocks_to_analyze = max_analyze
    config.analysis.parallel_instances = parallel_workers

    if watchlist_source == "Custom":
        config.watchlist.source = "custom"
        config.watchlist.custom_symbols = custom_symbols
    elif watchlist_source == "NASDAQ 100":
        config.watchlist.source = "nasdaq100"
    else:
        config.watchlist.source = "sp500"

    # Main content
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Scan Pipeline")
        st.markdown("""
        1. **Value Screen** → Filter 1000s stocks by fundamentals (~30s)
        2. **News Filter** → Score by news sentiment (~2min)
        3. **AI Analysis** → Deep analysis on top picks (~10min)
        """)

    with col2:
        if st.button("🚀 Run Scan", disabled=st.session_state.scan_running, type="primary"):
            st.session_state.scan_running = True
            st.rerun()

    # Run scan
    if st.session_state.scan_running:
        run_scan(config)
        st.session_state.scan_running = False

    # Display results
    if st.session_state.scan_results:
        display_results(st.session_state.scan_results)


def run_scan(config: ScannerConfig):
    """Execute the scanning pipeline with progress display"""

    progress = st.progress(0)
    status = st.empty()

    try:
        # Get symbols
        status.info("📋 Loading stock universe...")
        symbols = get_watchlist(config)
        st.write(f"Scanning {len(symbols)} stocks")
        progress.progress(5)

        # Stage 1: Value screening
        status.info("📊 Stage 1: Value screening...")
        screener = ValueScreener(config)
        screened = screener.screen(symbols)
        progress.progress(30)

        if not screened:
            status.warning("No stocks passed value screening")
            st.session_state.scan_results = {'screened': [], 'candidates': [], 'results': []}
            return

        st.success(f"✅ Stage 1: {len(screened)} stocks passed value filters")

        # Stage 2: News filtering
        status.info("📰 Stage 2: News filtering...")
        aggregator = NewsAggregator(config)
        candidates = aggregator.get_top_candidates(
            screened,
            top_n=config.analysis.max_stocks_to_analyze
        )
        progress.progress(60)

        if not candidates:
            status.warning("No stocks with positive news catalyst")
            st.session_state.scan_results = {'screened': screened, 'candidates': [], 'results': []}
            return

        st.success(f"✅ Stage 2: {len(candidates)} candidates for AI analysis")

        # Stage 3: AI analysis
        status.info("🤖 Stage 3: AI deep analysis...")
        analyzer = ParallelAnalyzer(config)
        results = analyzer.analyze_batch(candidates)
        progress.progress(100)

        st.success(f"✅ Stage 3: Analysis complete!")

        # Store results
        st.session_state.scan_results = {
            'screened': screened,
            'candidates': candidates,
            'results': results,
            'timestamp': datetime.now()
        }

        # Send alerts
        alert_manager = AlertManager(config)
        alert_manager.send_alerts(results)

        status.success("🎉 Scan complete!")

    except Exception as e:
        status.error(f"Scan failed: {str(e)}")
        st.exception(e)


def display_results(data: dict):
    """Display scan results"""

    results = data.get('results', [])
    timestamp = data.get('timestamp', datetime.now())

    st.markdown(f"### Results ({timestamp.strftime('%Y-%m-%d %H:%M')})")

    if not results:
        st.info("No results to display. Run a scan first.")
        return

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["🎯 BUY Signals", "📊 All Results", "📈 Screened Stocks"])

    with tab1:
        buys = [r for r in results if r.signal == 'BUY']

        if not buys:
            st.info("No BUY signals in this scan")
        else:
            st.success(f"Found {len(buys)} BUY signal(s)")

            for r in buys:
                with st.expander(f"🟢 {r.symbol} - {r.confidence:.0f}% confidence", expanded=True):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("Signal", r.signal)
                        st.metric("Confidence", f"{r.confidence:.0f}%")
                        st.metric("Score", f"{r.score:.1f}")

                    with col2:
                        st.markdown(f"**Value:** {r.value_analysis}")
                        st.markdown(f"**News:** {r.news_analysis}")
                        st.markdown(f"**Risk:** {r.risk_assessment}")

                    st.markdown(f"**➡️ Action:** {r.action_recommendation}")

    with tab2:
        # Convert to dataframe
        df_data = []
        for r in results:
            df_data.append({
                'Symbol': r.symbol,
                'Signal': r.signal,
                'Confidence': f"{r.confidence:.0f}%",
                'Score': round(r.score, 1),
                'Action': r.action_recommendation[:50] + "..." if len(r.action_recommendation) > 50 else r.action_recommendation
            })

        df = pd.DataFrame(df_data)

        # Color code by signal
        def highlight_signal(val):
            if val == 'BUY':
                return 'background-color: #d4edda'
            elif val == 'SELL' or val == 'AVOID':
                return 'background-color: #f8d7da'
            return ''

        st.dataframe(
            df.style.applymap(highlight_signal, subset=['Signal']),
            use_container_width=True
        )

    with tab3:
        screened = data.get('screened', [])
        if screened:
            df = pd.DataFrame([{
                'Symbol': s.symbol,
                'Score': round(s.score, 1),
                'P/E': round(s.pe_ratio, 2) if s.pe_ratio else None,
                'P/B': round(s.pb_ratio, 2) if s.pb_ratio else None,
                'ROE': f"{s.roe*100:.1f}%" if s.roe else None,
                'Sector': s.sector
            } for s in screened[:50]])

            st.dataframe(df, use_container_width=True)
            st.caption(f"Showing top 50 of {len(screened)} screened stocks")


if __name__ == "__main__":
    show()
