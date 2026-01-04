"""
Stock Analysis page with live agent execution and action buttons
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
from dashboard.utils.config_manager import ConfigManager

db = TradingDatabase()


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
    """Display stock analysis page"""
    st.markdown("<h1 class='main-header'>🔍 Stock Analysis</h1>", unsafe_allow_html=True)

    # Analysis Configuration
    st.markdown("## 📋 Analysis Configuration")

    col1, col2 = st.columns(2)

    with col1:
        ticker = st.text_input("Ticker Symbol", value="NVDA", help="Enter stock ticker (e.g., NVDA, AAPL, SPY)").upper()

    with col2:
        analysis_date = st.date_input(
            "Analysis Date",
            value=datetime.now().date(),
            max_value=datetime.now().date(),
            help="Date for analysis (cannot be future)"
        )

    col3, col4 = st.columns(2)

    with col3:
        research_depth = st.select_slider(
            "Research Depth",
            options=[1, 2, 3, 4, 5],
            value=1,
            format_func=lambda x: {1: "Quick", 2: "Basic", 3: "Standard", 4: "Deep", 5: "Comprehensive"}[x],
            help="Number of debate rounds between agents"
        )

    with col4:
        selected_analysts = st.multiselect(
            "Select Analysts",
            options=["market", "social", "news", "fundamentals", "technical"],
            default=["market", "news", "fundamentals", "technical"],
            help="Choose which analyst agents to include. Technical = TradingView-style chart analysis"
        )

    st.markdown("---")

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
    if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
        if not ticker:
            st.error("Please enter a ticker symbol")
            return

        if not selected_analysts:
            st.error("Please select at least one analyst")
            return

        # Get config from database (enables instant switching without restart)
        config_manager = ConfigManager(db)
        config = config_manager.get_config_dict()

        # Override with user selections from UI
        config["max_debate_rounds"] = research_depth
        config["max_risk_discuss_rounds"] = research_depth

        # Initialize graph
        with st.spinner("Initializing TradingAgents..."):
            graph = TradingAgentsGraph(
                selected_analysts=selected_analysts,
                debug=True,
                config=config
            )

        # Progress tracking
        st.markdown("## 🔄 Analysis Progress")

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Create containers for live updates
        analyst_container = st.container()
        research_container = st.container()
        trading_container = st.container()
        risk_container = st.container()

        # Run analysis
        try:
            analysis_date_str = analysis_date.strftime("%Y-%m-%d")

            with st.spinner(f"Analyzing {ticker} for {analysis_date_str}..."):
                status_text.text("Running analyst team...")
                progress_bar.progress(10)

                final_state, decision = graph.propagate(ticker, analysis_date_str)

                progress_bar.progress(100)
                status_text.text("Analysis complete!")

            st.success("✅ Analysis completed successfully!")

            # Extract decision
            decision_action = extract_decision(decision)

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

            # Store in session state
            st.session_state['current_analysis'] = {
                'id': analysis_id,
                'ticker': ticker,
                'decision': decision_action,
                'final_state': final_state,
                'decision_text': decision
            }

            # Display results
            st.markdown("---")
            st.markdown("## 📊 Analysis Results")

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

            # Analyst Reports
            with st.expander("📈 Analyst Team Reports", expanded=True):
                tabs = st.tabs(["Market", "Sentiment", "News", "Fundamentals", "Technical"])

                with tabs[0]:
                    if final_state.get('market_report'):
                        st.markdown(final_state['market_report'])
                    else:
                        st.info("Market analysis not included")

                with tabs[1]:
                    if final_state.get('sentiment_report'):
                        st.markdown(final_state['sentiment_report'])
                    else:
                        st.info("Sentiment analysis not included")

                with tabs[2]:
                    if final_state.get('news_report'):
                        st.markdown(final_state['news_report'])
                    else:
                        st.info("News analysis not included")

                with tabs[3]:
                    if final_state.get('fundamentals_report'):
                        st.markdown(final_state['fundamentals_report'])
                    else:
                        st.info("Fundamentals analysis not included")

                with tabs[4]:
                    if final_state.get('technical_report'):
                        st.markdown("### 📊 TradingView-Style Technical Analysis")
                        st.markdown(final_state['technical_report'])
                    else:
                        st.info("Technical analysis not included")

            # Research Team
            with st.expander("🎯 Research Team Decision"):
                if final_state.get('investment_plan'):
                    st.markdown(final_state['investment_plan'])
                else:
                    st.info("Research decision not available")

            # Trading Team
            with st.expander("💼 Trading Team Plan"):
                if final_state.get('trader_investment_plan'):
                    st.markdown(final_state['trader_investment_plan'])
                else:
                    st.info("Trading plan not available")

            # Risk Management
            with st.expander("⚠️ Risk Management Decision"):
                if final_state.get('final_trade_decision'):
                    st.markdown(final_state['final_trade_decision'])
                else:
                    st.info("Risk decision not available")

            # Final Decision
            st.markdown("### 🎯 Final Portfolio Manager Decision")
            st.markdown(decision)

            st.markdown("---")

            # Action Buttons
            st.markdown("## 🎬 Take Action")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
                    st.session_state['show_execute_modal'] = True
                    st.rerun()

            with col2:
                if st.button("❌ Reject", use_container_width=True):
                    db.update_analysis_status(analysis_id, 'rejected')
                    st.warning("Analysis rejected and saved.")

            with col3:
                if st.button("💾 Save to Watchlist", use_container_width=True):
                    db.add_to_watchlist(ticker, f"From analysis on {analysis_date_str}")
                    st.success(f"Added {ticker} to watchlist")

            with col4:
                if st.button("🔄 Re-analyze", use_container_width=True):
                    st.rerun()

        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
            st.exception(e)

    # Execute Trade Modal
    if st.session_state.get('show_execute_modal', False):
        st.markdown("---")
        st.markdown("## 💰 Execute Trade")

        analysis = st.session_state.get('current_analysis')

        if analysis:
            st.markdown(f"**Ticker:** {analysis['ticker']}")
            st.markdown(f"**Recommendation:** {analysis['decision']}")

            col1, col2 = st.columns(2)

            with col1:
                quantity = st.number_input(
                    "Quantity (shares)",
                    min_value=1,
                    value=10,
                    step=1,
                    help="Number of shares to trade"
                )

            with col2:
                # Get current quote
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
                    estimated_price = 100.0  # Default
                    st.warning("Could not fetch quote, using default price")

            col3, col4 = st.columns(2)

            with col3:
                if st.button("✅ Confirm Trade", type="primary", use_container_width=True):
                    # Execute trade
                    try:
                        side = OrderSide.BUY if analysis['decision'] == 'BUY' else OrderSide.SELL

                        result = broker.place_order(
                            ticker=analysis['ticker'],
                            quantity=quantity,
                            side=side
                        )

                        if 'error' in result:
                            st.error(f"Trade failed: {result['error']}")
                        else:
                            # Save trade to database
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
                                'status': 'executed',
                                'notes': f"Executed from analysis #{analysis['id']}"
                            }

                            db.save_trade(trade_data)
                            db.update_analysis_status(analysis['id'], 'approved')

                            st.success(f"✅ Trade executed! Order ID: {result.get('order_id')}")
                            st.balloons()

                            # Clear modal
                            st.session_state['show_execute_modal'] = False
                            time.sleep(2)
                            st.rerun()

                    except Exception as e:
                        st.error(f"Trade execution failed: {str(e)}")

            with col4:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state['show_execute_modal'] = False
                    st.rerun()
