"""
Settings page for configuring API keys, broker, and preferences
"""

import streamlit as st
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.utils.database import TradingDatabase
from dashboard.utils.config_manager import ConfigManager

db = TradingDatabase()


def show():
    """Display settings page with tier-based presets"""
    st.markdown("<h1 class='main-header'>⚙️ Settings</h1>", unsafe_allow_html=True)

    # Initialize config manager
    config_manager = ConfigManager(db)

    # Get current tier and available presets
    current_tier = config_manager.get_current_tier() or 'budget'
    presets = config_manager.get_tier_presets()

    # LLM Configuration Section
    st.markdown("## 🤖 LLM Configuration")
    st.markdown("Choose your LLM tier. You can switch anytime without restarting.")

    # Tier selector with radio buttons
    tier_options = []
    tier_map = {}

    for preset in presets:
        label = preset['display_name']
        if preset['is_recommended']:
            label += " ⭐"
        tier_options.append(label)
        tier_map[label] = preset

    # Show current selection
    current_label = next(
        (label for label, preset in tier_map.items()
         if preset['tier_name'] == current_tier),
        tier_options[0]
    )

    try:
        current_index = tier_options.index(current_label)
    except ValueError:
        current_index = 0

    selected_label = st.radio(
        "Select Your Tier:",
        options=tier_options,
        index=current_index,
        key="tier_selector"
    )

    selected_preset = tier_map[selected_label]

    # Show tier details
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Provider", selected_preset['provider'].title())
    with col2:
        st.metric("Estimated Cost", selected_preset['estimated_cost_month'])
    with col3:
        st.metric("Speed", selected_preset['speed_rating'])

    # Show model details in expander
    with st.expander("📋 Model Configuration", expanded=True):
        st.markdown(f"**Quick Thinking Model:** `{selected_preset['quick_think_model']}`")
        st.markdown(f"**Deep Thinking Model:** `{selected_preset['deep_think_model']}`")
        st.markdown(f"**Quality Rating:** {selected_preset['quality_rating']}")

    # API Key input if required
    api_key_provided = False
    key_exists = False
    if selected_preset['requires_api_key']:
        st.markdown("---")
        st.markdown(f"### 🔑 API Key Required: {selected_preset['api_key_name']}")

        # Check if key already exists
        key_exists = config_manager.check_api_key_available(selected_preset['api_key_name'])

        if key_exists:
            st.success(f"✅ API key configured for {selected_preset['api_key_name']}")
            if st.button("🔄 Update API Key", key="update_key"):
                st.session_state['show_key_input'] = True

        if not key_exists or st.session_state.get('show_key_input', False):
            api_key = st.text_input(
                f"Enter {selected_preset['provider'].title()} API Key",
                type="password",
                key=f"api_key_{selected_preset['tier_name']}"
            )

            if api_key:
                api_key_provided = True

            # Show helpful links based on provider
            if selected_preset['provider'] == 'openrouter':
                st.info("🔗 Get your OpenRouter API key at [openrouter.ai/keys](https://openrouter.ai/keys)")
            elif selected_preset['provider'] == 'anthropic':
                st.info("🔗 Get your Anthropic API key at [console.anthropic.com](https://console.anthropic.com)")
            elif selected_preset['provider'] == 'openai':
                st.info("🔗 Get your OpenAI API key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)")
    else:
        api_key_provided = True  # No key required for budget tier

    # Apply tier button
    st.markdown("---")

    tier_changed = selected_preset['tier_name'] != current_tier
    can_apply = not selected_preset['requires_api_key'] or key_exists or api_key_provided

    if tier_changed:
        if not can_apply:
            st.warning(f"⚠️ Please provide {selected_preset['api_key_name']} to use this tier")

        if st.button(
            f"✅ Switch to {selected_preset['display_name']}",
            type="primary",
            disabled=not can_apply,
            use_container_width=True
        ):
            try:
                # Save API key if provided
                if api_key_provided and selected_preset['requires_api_key']:
                    api_key = st.session_state.get(f"api_key_{selected_preset['tier_name']}")
                    if api_key:
                        config_manager.secrets_manager.save_secret(
                            selected_preset['api_key_name'],
                            api_key,
                            selected_preset['provider']
                        )

                # Apply tier preset
                config_manager.apply_tier_preset(selected_preset['tier_name'])

                st.success(f"✅ Switched to {selected_preset['display_name']}!")
                st.info("🔄 Settings applied instantly. Your next analysis will use the new configuration.")
                st.session_state['show_key_input'] = False
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error applying tier: {str(e)}")
    else:
        st.info(f"ℹ️ Currently using: **{selected_preset['display_name']}**")

    st.markdown("---")

    # Broker Configuration
    st.markdown("## 💼 Broker Configuration")
    st.markdown("Configure brokers for Indian, US, and Crypto markets")

    broker_tabs = st.tabs(["🇮🇳 Indian Markets", "🇺🇸 US Markets", "₿ Crypto Markets"])

    with broker_tabs[0]:
        st.markdown("### Indian Stock Brokers")
        st.info("Configure Zerodha or Upstox for NSE/BSE trading")
        
        indian_broker = st.selectbox(
            "Select Indian Broker",
            ["Zerodha", "Upstox", "None"],
            key="indian_broker"
        )
        
        if indian_broker != "None":
            api_key = st.text_input(f"{indian_broker} API Key", type="password", key="indian_api_key")
            api_secret = st.text_input(f"{indian_broker} API Secret", type="password", key="indian_api_secret")
            
            if st.button(f"Save {indian_broker} Credentials", key="save_indian"):
                # Save to secrets
                config_manager.secrets_manager.save_secret(
                    f"{indian_broker.upper()}_API_KEY",
                    api_key,
                    "broker"
                )
                config_manager.secrets_manager.save_secret(
                    f"{indian_broker.upper()}_API_SECRET",
                    api_secret,
                    "broker"
                )
                st.success(f"✅ {indian_broker} credentials saved!")

    with broker_tabs[1]:
        st.markdown("### US Stock Brokers")
        st.info("Configure Alpaca for NYSE/NASDAQ trading")
        
        us_broker = st.selectbox(
            "Select US Broker",
            ["Alpaca", "None"],
            key="us_broker"
        )
        
        if us_broker == "Alpaca":
            alpaca_key = st.text_input("Alpaca API Key", type="password", key="alpaca_key")
            alpaca_secret = st.text_input("Alpaca API Secret", type="password", key="alpaca_secret")
            paper_trading = st.checkbox("Use Paper Trading (Recommended)", value=True, key="alpaca_paper")
            
            if st.button("Save Alpaca Credentials", key="save_alpaca"):
                config_manager.secrets_manager.save_secret("ALPACA_API_KEY", alpaca_key, "broker")
                config_manager.secrets_manager.save_secret("ALPACA_API_SECRET", alpaca_secret, "broker")
                db.save_setting("alpaca_paper_trading", str(paper_trading))
                st.success("✅ Alpaca credentials saved!")

    with broker_tabs[2]:
        st.markdown("### Crypto Brokers")
        st.info("Configure Binance or Coinbase for cryptocurrency trading")
        
        crypto_broker = st.selectbox(
            "Select Crypto Broker",
            ["Binance", "Coinbase", "None"],
            key="crypto_broker"
        )
        
        if crypto_broker == "Binance":
            st.markdown("#### Binance Configuration")
            binance_key = st.text_input("Binance API Key", type="password", key="binance_key")
            binance_secret = st.text_input("Binance API Secret", type="password", key="binance_secret")
            binance_testnet = st.checkbox("Use Testnet (Paper Trading - Recommended)", value=True, key="binance_testnet")
            
            st.info("🔗 Get Binance API keys at [binance.com/en/my/settings/api-management](https://www.binance.com/en/my/settings/api-management)")
            
            if st.button("Save Binance Credentials", key="save_binance"):
                config_manager.secrets_manager.save_secret("BINANCE_API_KEY", binance_key, "broker")
                config_manager.secrets_manager.save_secret("BINANCE_API_SECRET", binance_secret, "broker")
                db.save_setting("binance_testnet", str(binance_testnet))
                st.success("✅ Binance credentials saved!")
        
        elif crypto_broker == "Coinbase":
            st.markdown("#### Coinbase Configuration")
            coinbase_key = st.text_input("Coinbase API Key", type="password", key="coinbase_key")
            coinbase_secret = st.text_input("Coinbase API Secret", type="password", key="coinbase_secret")
            coinbase_sandbox = st.checkbox("Use Sandbox (Paper Trading - Recommended)", value=True, key="coinbase_sandbox")
            
            st.info("🔗 Get Coinbase API keys at [coinbase.com/advanced-trade](https://www.coinbase.com/advanced-trade)")
            
            if st.button("Save Coinbase Credentials", key="save_coinbase"):
                config_manager.secrets_manager.save_secret("COINBASE_API_KEY", coinbase_key, "broker")
                config_manager.secrets_manager.save_secret("COINBASE_API_SECRET", coinbase_secret, "broker")
                db.save_setting("coinbase_sandbox", str(coinbase_sandbox))
                st.success("✅ Coinbase credentials saved!")

    st.markdown("---")

    # Advanced Settings
    with st.expander("⚙️ Advanced Settings", expanded=False):
        st.markdown("### Research Configuration")

        max_debate = st.slider(
            "Maximum Debate Rounds",
            min_value=1,
            max_value=5,
            value=config_manager.get('max_debate_rounds', 1),
            help="Number of rounds for bull/bear debate"
        )

        max_risk = st.slider(
            "Maximum Risk Discussion Rounds",
            min_value=1,
            max_value=5,
            value=config_manager.get('max_risk_discuss_rounds', 1),
            help="Number of rounds for risk analysis"
        )

        if st.button("Save Advanced Settings", key="save_advanced"):
            config_manager.set('max_debate_rounds', max_debate)
            config_manager.set('max_risk_discuss_rounds', max_risk)
            st.success("✅ Advanced settings saved!")

    st.markdown("---")

    # Risk Management
    st.markdown("## ⚠️ Risk Management")

    max_position_size = st.slider(
        "Maximum Position Size (%)",
        min_value=1,
        max_value=50,
        value=10,
        help="Maximum % of portfolio per position"
    )

    max_total_exposure = st.slider(
        "Maximum Total Exposure (%)",
        min_value=10,
        max_value=100,
        value=80,
        help="Maximum % of portfolio in stocks (rest in cash)"
    )

    stop_loss_pct = st.slider(
        "Default Stop Loss (%)",
        min_value=1,
        max_value=30,
        value=10,
        help="Default stop loss percentage"
    )

    st.markdown("---")

    # Database Management
    st.markdown("## 🗄️ Database Management")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 View Database Stats", use_container_width=True):
            analyses_count = len(db.get_recent_analyses(limit=1000))
            trades_count = len(db.get_trades(limit=1000))
            watchlist_count = len(db.get_watchlist())

            st.info(f"""
            **Database Statistics:**
            - Analyses: {analyses_count}
            - Trades: {trades_count}
            - Watchlist: {watchlist_count}
            """)

    with col2:
        if st.button("🗑️ Clear All Data", use_container_width=True, type="secondary"):
            st.warning("This will delete all analyses, trades, and watchlist entries!")
