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
    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input("Ticker Symbol", value="NVDA", help="Enter stock ticker").upper()
    with col2:
        analysis_date = st.date_input("Analysis Date", value=datetime.now().date(), max_value=datetime.now().date())
    
    col3, col4 = st.columns(2)
    with col3:
        research_depth = st.select_slider("Depth", options=[1, 3, 5], value=3, format_func=lambda x: {1: "Quick", 3: "Standard", 5: "Deep"}[x])
    with col4:
        # Default all selected for ease
        selected_analysts = st.multiselect("Analysts", 
                                         options=["market", "social", "news", "fundamentals", "technical"],
                                         default=["market", "news", "fundamentals"],
                                         label_visibility="collapsed")
    
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

        # Run analysis with live streaming
        try:
            analysis_date_str = analysis_date.strftime("%Y-%m-%d")

            # Simple progress display
            progress_container = st.container()
            with progress_container:
                st.markdown("### 🔄 Analysis Progress")
                progress_placeholder = st.empty()
                completed_steps = []

            # Stream the graph execution
            init_agent_state = graph.propagator.create_initial_state(ticker, analysis_date_str)
            args = graph.propagator.get_graph_args()

            trace = []
            seen_agents = set()
            
            # Use status container for cleaner UI
            with st.status("🤖 AI Agents Analyzing...", expanded=True) as status:
                for chunk in graph.graph.stream(init_agent_state, **args):
                    messages = chunk.get("messages", [])
                    if messages and len(messages) > 0:
                        msg = messages[-1]
                        trace.append(chunk)

                        # Get agent name
                        agent_name = getattr(msg, 'name', None) or type(msg).__name__

                        if agent_name and agent_name not in seen_agents and agent_name != 'HumanMessage':
                            seen_agents.add(agent_name)
                            status.write(f"✅ {agent_name} completed")
                
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

            # Get final state from last chunk
            if trace:
                final_state = trace[-1]
            else:
                final_state = graph.graph.invoke(init_agent_state, **args)

            graph.curr_state = final_state
            decision = graph.process_signal(final_state.get("final_trade_decision", "HOLD"))

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

            # Display Trading Summary
            st.markdown("---")
            st.markdown("## 📊 Trading Summary")

            # Main recommendation card
            decision_colors = {
                'BUY': ('#28a745', '#d4edda', '🟢'),
                'SELL': ('#dc3545', '#f8d7da', '🔴'),
                'HOLD': ('#ffc107', '#fff3cd', '🟡')
            }
            color, bg_color, emoji = decision_colors.get(decision_action, ('#6c757d', '#e9ecef', '⚪'))

            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border-left: 5px solid {color}; margin-bottom: 20px;">
                <h1 style="color: {color}; margin: 0;">{emoji} {decision_action}</h1>
                <p style="color: #333; font-size: 1.1em; margin-top: 10px;">{ticker} - {analysis_date_str}</p>
            </div>
            """, unsafe_allow_html=True)

            # Key Metrics Row
            col1, col2, col3, col4 = st.columns(4)

            # Extract time horizon and confidence from decision text
            decision_lower = decision.lower()
            time_horizon = "Short Term" if "short" in decision_lower else "Long Term" if "long" in decision_lower else "Medium Term"
            risk_level = "High" if "high risk" in decision_lower or "volatile" in decision_lower else "Medium" if "moderate" in decision_lower else "Low"

            with col1:
                st.metric("Action", decision_action)
            with col2:
                st.metric("Time Horizon", time_horizon)
            with col3:
                st.metric("Risk Level", risk_level)
            with col4:
                confidence = "High" if "strong" in decision_lower or "confident" in decision_lower else "Medium"
                st.metric("Confidence", confidence)

            st.markdown("---")

            # Trading Decision Summary
            st.markdown("### 🎯 Final Decision")
            if final_state.get('final_trade_decision'):
                st.markdown(final_state['final_trade_decision'])
            else:
                st.markdown(decision)

            # Key Insights in columns
            st.markdown("---")
            st.markdown("### 📈 Key Insights")

            insight_col1, insight_col2 = st.columns(2)

            with insight_col1:
                st.markdown("**Market Analysis**")
                if final_state.get('market_report'):
                    # Extract first 300 chars as summary
                    market_summary = final_state['market_report'][:500] + "..." if len(final_state.get('market_report', '')) > 500 else final_state.get('market_report', 'N/A')
                    st.markdown(market_summary)
                else:
                    st.info("Not analyzed")

                st.markdown("**News Sentiment**")
                if final_state.get('news_report'):
                    news_summary = final_state['news_report'][:500] + "..." if len(final_state.get('news_report', '')) > 500 else final_state.get('news_report', 'N/A')
                    st.markdown(news_summary)
                else:
                    st.info("Not analyzed")

            with insight_col2:
                st.markdown("**Fundamentals**")
                if final_state.get('fundamentals_report'):
                    fund_summary = final_state['fundamentals_report'][:500] + "..." if len(final_state.get('fundamentals_report', '')) > 500 else final_state.get('fundamentals_report', 'N/A')
                    st.markdown(fund_summary)
                else:
                    st.info("Not analyzed")

                st.markdown("**Technical Analysis**")
                if final_state.get('technical_report'):
                    tech_summary = final_state['technical_report'][:500] + "..." if len(final_state.get('technical_report', '')) > 500 else final_state.get('technical_report', 'N/A')
                    st.markdown(tech_summary)
                else:
                    st.info("Not analyzed")

            # Detailed Reports (collapsed by default)
            st.markdown("---")
            with st.expander("📋 View Full Reports", expanded=False):
                tabs = st.tabs(["Market", "News", "Fundamentals", "Technical", "Investment Plan"])

                with tabs[0]:
                    st.markdown(final_state.get('market_report', 'Not available'))
                with tabs[1]:
                    st.markdown(final_state.get('news_report', 'Not available'))
                with tabs[2]:
                    st.markdown(final_state.get('fundamentals_report', 'Not available'))
                with tabs[3]:
                    st.markdown(final_state.get('technical_report', 'Not available'))
                with tabs[4]:
                    st.markdown(final_state.get('investment_plan', 'Not available'))

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
