"""
Enhanced Stock Analysis page with Live Monitoring and Override Controls
Real-time progress tracking with manual intervention capabilities
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dashboard.utils.database import TradingDatabase
from dashboard.utils.broker import get_broker, OrderSide
from dashboard.components.live_monitor import get_monitor
from dashboard.utils.config_manager import ConfigManager

db = TradingDatabase()
monitor = get_monitor()


def extract_decision(text: str) -> str:
    """Extract BUY/SELL/HOLD decision from text"""
    text_upper = text.upper()
    if 'BUY' in text_upper and 'SELL' not in text_upper:
        return 'BUY'
    elif 'SELL' in text_upper and 'BUY' not in text_upper:
        return 'SELL'
    elif 'HOLD' in text_upper:
        return 'HOLD'
    return 'HOLD'


def show():
    """Display stock analysis page with live monitoring"""
    st.markdown("<h1 class='main-header'>🔍 Stock Analysis with Live Monitor</h1>", unsafe_allow_html=True)

    # Create two columns: Config on left, Monitor on right
    col_config, col_monitor = st.columns([1, 1])

    with col_config:
        st.markdown("## 📋 Analysis Configuration")

        col1, col2 = st.columns(2)

        with col1:
            ticker = st.text_input("Ticker Symbol", value="NVDA", help="Enter stock ticker").upper()

        with col2:
            analysis_date = st.date_input(
                "Analysis Date",
                value=datetime.now().date(),
                max_value=datetime.now().date()
            )

        col3, col4 = st.columns(2)

        with col3:
            research_depth = st.select_slider(
                "Research Depth",
                options=[1, 2, 3, 4, 5],
                value=1,
                format_func=lambda x: {1: "Quick", 2: "Basic", 3: "Standard", 4: "Deep", 5: "Comprehensive"}[x]
            )

        with col4:
            selected_analysts = st.multiselect(
                "Select Analysts",
                options=["market", "social", "news", "fundamentals", "technical"],
                default=["market", "news", "fundamentals", "technical"]
            )

        # Show current LLM configuration
        config_manager = ConfigManager(db)
        current_tier = config_manager.get_current_tier()
        presets = config_manager.get_tier_presets()
        current_preset = next((p for p in presets if p['tier_name'] == current_tier), None)

        if current_preset:
            st.info(f"🤖 Using: **{current_preset['display_name']}** | "
                    f"Quick: `{current_preset['quick_think_model']}` | "
                    f"Deep: `{current_preset['deep_think_model']}`")

        # Run Analysis Button
        if st.button("🚀 Run Analysis with Live Monitoring", type="primary", use_container_width=True):
            if not ticker or not selected_analysts:
                st.error("Please enter ticker and select analysts")
                return

            # Initialize monitor
            monitor.start_analysis(ticker)

            # Get config from database (enables instant switching without restart)
            config_manager = ConfigManager(db)
            config = config_manager.get_config_dict()

            # Override with user selections from UI
            config["max_debate_rounds"] = research_depth
            config["max_risk_discuss_rounds"] = research_depth

            # Initialize graph
            monitor.log("Initializing TradingAgents framework", "info")
            graph = TradingAgentsGraph(
                selected_analysts=selected_analysts,
                debug=True,
                config=config
            )

            monitor.update_progress(5)

            # Run analysis with monitoring
            analysis_date_str = analysis_date.strftime("%Y-%m-%d")

            try:
                monitor.log(f"Starting analysis for {ticker} on {analysis_date_str}", "info")
                monitor.update_agent("Analyst Team")
                monitor.update_progress(10)

                # Simulate agent progression (in real implementation, hook into graph execution)
                st.session_state['analysis_running'] = True

                # Run the actual analysis
                monitor.log("Executing multi-agent analysis...", "info")

                final_state, decision = graph.propagate(ticker, analysis_date_str)

                monitor.update_progress(90)

                # Check for manual override
                if monitor.is_override_requested():
                    st.warning("⚠️ Manual override requested - please complete override action")
                    monitor.render_live_console()
                    return

                if 'manual_decision' in st.session_state.monitor_state:
                    decision_action = st.session_state.monitor_state['manual_decision']
                    monitor.log(f"Using manual override decision: {decision_action}", "warning")
                else:
                    decision_action = extract_decision(decision)

                monitor.update_progress(100)
                monitor.log("Analysis completed successfully!", "success")

                # Save to database
                analysis_data = {
                    'ticker': ticker,
                    'analysis_date': analysis_date_str,
                    'decision': decision_action,
                    'market_report': final_state.get('market_report', ''),
                    'sentiment_report': final_state.get('sentiment_report', ''),
                    'news_report': final_state.get('news_report', ''),
                    'fundamentals_report': final_state.get('fundamentals_report', ''),
                    'investment_plan': final_state.get('investment_plan', ''),
                    'trader_plan': final_state.get('trader_investment_plan', ''),
                    'risk_decision': final_state.get('final_trade_decision', ''),
                    'final_decision': decision,
                    'status': 'pending'
                }

                analysis_id = db.save_analysis(analysis_data)

                # Store in session
                st.session_state['current_analysis'] = {
                    'id': analysis_id,
                    'ticker': ticker,
                    'decision': decision_action,
                    'final_state': final_state,
                    'decision_text': decision
                }

                st.session_state['analysis_complete'] = True
                st.rerun()

            except Exception as e:
                monitor.log(f"Error during analysis: {str(e)}", "error")
                st.error(f"Analysis failed: {str(e)}")

    with col_monitor:
        # Always show monitor
        if 'analysis_running' in st.session_state or 'analysis_complete' in st.session_state:
            monitor.render_live_console()

    # Show results if analysis is complete
    if st.session_state.get('analysis_complete'):
        st.markdown("---")
        st.markdown("## 📊 Analysis Results")

        analysis = st.session_state.get('current_analysis')
        if analysis:
            final_state = analysis['final_state']
            decision_action = analysis['decision']

            # Decision card
            decision_class = {
                'BUY': 'buy-signal',
                'SELL': 'sell-signal',
                'HOLD': 'hold-signal'
            }.get(decision_action, 'hold-signal')

            st.markdown(
                f"<div class='{decision_class}'><h2>RECOMMENDATION: {decision_action}</h2></div>",
                unsafe_allow_html=True
            )

            # Check if manual override was applied
            if 'manual_decision' in st.session_state.monitor_state:
                st.warning("⚠️ This decision was MANUALLY OVERRIDDEN by you")

            # Reports in tabs
            with st.expander("📈 Analyst Team Reports", expanded=True):
                tabs = st.tabs(["Market", "Sentiment", "News", "Fundamentals", "Technical"])

                with tabs[0]:
                    if final_state.get('market_report'):
                        st.markdown(final_state['market_report'])

                with tabs[1]:
                    if final_state.get('sentiment_report'):
                        st.markdown(final_state['sentiment_report'])

                with tabs[2]:
                    if final_state.get('news_report'):
                        st.markdown(final_state['news_report'])

                with tabs[3]:
                    if final_state.get('fundamentals_report'):
                        st.markdown(final_state['fundamentals_report'])

                with tabs[4]:
                    if final_state.get('technical_report'):
                        st.markdown("### 📊 TradingView-Style Technical Analysis")
                        st.markdown(final_state['technical_report'])

            # Action buttons
            st.markdown("## 🎬 Take Action")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
                    st.session_state['show_execute_modal'] = True
                    st.rerun()

            with col2:
                if st.button("❌ Reject", use_container_width=True):
                    db.update_analysis_status(analysis['id'], 'rejected')
                    monitor.log("Analysis rejected by user", "warning")
                    st.warning("Analysis rejected")

            with col3:
                if st.button("💾 Save to Watchlist", use_container_width=True):
                    db.add_to_watchlist(analysis['ticker'])
                    monitor.log(f"Added {analysis['ticker']} to watchlist", "success")
                    st.success(f"Added {analysis['ticker']} to watchlist")

            with col4:
                if st.button("🔄 New Analysis", use_container_width=True):
                    # Clear session state
                    for key in ['analysis_running', 'analysis_complete', 'current_analysis', 'show_execute_modal']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

    # Execute Trade Modal
    if st.session_state.get('show_execute_modal'):
        st.markdown("---")
        st.markdown("## 💰 Execute Trade")

        analysis = st.session_state.get('current_analysis')

        if analysis:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Ticker:** {analysis['ticker']}")
                st.markdown(f"**Recommendation:** {analysis['decision']}")

                quantity = st.number_input(
                    "Quantity (shares)",
                    min_value=1,
                    value=10,
                    step=1
                )

            with col2:
                # Get quote
                use_alpaca = st.session_state.get('use_alpaca', False)
                paper_trading = st.session_state.get('paper_trading_enabled', True)
                broker = get_broker(paper_trading=paper_trading, use_alpaca=use_alpaca)

                quote = broker.get_quote(analysis['ticker'])
                if quote:
                    estimated_price = (quote['bid_price'] + quote['ask_price']) / 2
                    st.metric("Estimated Price", f"${estimated_price:.2f}")
                    total_value = quantity * estimated_price
                    st.metric("Total Value", f"${total_value:,.2f}")
                else:
                    estimated_price = 100.0
                    st.warning("Using default price")

            col3, col4 = st.columns(2)

            with col3:
                if st.button("✅ Confirm Trade", type="primary", use_container_width=True):
                    try:
                        side = OrderSide.BUY if analysis['decision'] == 'BUY' else OrderSide.SELL

                        result = broker.place_order(
                            ticker=analysis['ticker'],
                            quantity=quantity,
                            side=side
                        )

                        if 'error' not in result:
                            # Log to monitor
                            monitor.add_paper_trade({
                                'ticker': analysis['ticker'],
                                'action': analysis['decision'],
                                'quantity': quantity,
                                'price': estimated_price,
                                'total_value': quantity * estimated_price,
                                'order_id': result.get('order_id')
                            })

                            # Save to database
                            trade_data = {
                                'analysis_id': analysis['id'],
                                'ticker': analysis['ticker'],
                                'action': analysis['decision'],
                                'quantity': quantity,
                                'price': estimated_price,
                                'total_value': quantity * estimated_price,
                                'trade_date': datetime.now().strftime("%Y-%m-%d"),
                                'execution_type': 'paper' if paper_trading else 'live',
                                'order_id': result.get('order_id'),
                                'status': 'executed'
                            }

                            db.save_trade(trade_data)
                            db.update_analysis_status(analysis['id'], 'approved')

                            st.success(f"✅ Trade executed! Order ID: {result.get('order_id')}")
                            st.balloons()

                            st.session_state['show_execute_modal'] = False
                            time.sleep(2)
                            st.rerun()

                    except Exception as e:
                        monitor.log(f"Trade execution failed: {str(e)}", "error")
                        st.error(f"Trade failed: {str(e)}")

            with col4:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state['show_execute_modal'] = False
                    st.rerun()
