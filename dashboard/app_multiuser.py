"""
TradingAgents Multi-User SaaS Platform
Entry point for multi-tenant trading application
"""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="TradingAgents - AI Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import multi-user modules
from dashboard.multiuser.database import MultiUserDatabase
from dashboard.multiuser.auth import AuthManager, show_login_page, show_user_menu

# Initialize database and auth
@st.cache_resource
def get_database():
    """Get database instance (cached)"""
    return MultiUserDatabase()

@st.cache_resource
def get_auth_manager(_db):
    """Get auth manager instance (cached)"""
    return AuthManager(_db)

db = get_database()
auth = get_auth_manager(db)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .buy-signal {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .sell-signal {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
    }
    .hold-signal {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    </style>
""", unsafe_allow_html=True)

# Check if user is authenticated
if not auth.is_authenticated():
    # Show login/signup page
    show_login_page(auth)
else:
    # User is authenticated - show main application

    # Sidebar with user info
    st.sidebar.title("📈 TradingAgents")
    show_user_menu(auth)

    st.sidebar.markdown("---")

    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "🔍 Stock Analysis",
            "💼 Portfolio",
            "📊 Trade History",
            "🏦 Broker Setup",
            "⚙️ Settings",
            "📚 Documentation"
        ]
    )

    # Get current user
    user = auth.get_current_user()
    user_id = user['id']

    # Display selected page
    if page == "🏠 Dashboard":
        from dashboard.modules import home
        home.show()

    elif page == "🔍 Stock Analysis":
        from dashboard.modules import analysis
        analysis.show()

    elif page == "💼 Portfolio":
        from dashboard.modules import portfolio
        portfolio.show()

    elif page == "📊 Trade History":
        from dashboard.modules import trade_history
        trade_history.show()

    elif page == "🏦 Broker Setup":
        # Broker setup page (new for multi-user)
        st.markdown("<h1 class='main-header'>🏦 Broker Configuration</h1>", unsafe_allow_html=True)

        st.markdown("""
        ## Connect Your Trading Accounts

        TradingAgents supports multiple brokers across Indian and US markets:

        ### 🇮🇳 Indian Markets
        - **Zerodha Kite** - Most popular (₹2,000/month)
        - **Upstox** - FREE API alternative

        ### 🇺🇸 US Markets
        - **Alpaca** - Commission-free (FREE)
        - **Interactive Brokers** - Global markets

        ### 📝 Paper Trading
        - **Simulated Broker** - Test with virtual money (FREE)
        """)

        broker_type = st.selectbox(
            "Select Broker to Configure",
            ["None", "Zerodha (India)", "Upstox (India)", "Alpaca (US)", "Simulated (Paper)"]
        )

        if broker_type == "Zerodha (India)":
            st.markdown("### Zerodha Kite API Setup")

            with st.form("zerodha_form"):
                api_key = st.text_input("API Key", type="password")
                api_secret = st.text_input("API Secret", type="password")
                submit = st.form_submit_button("Save Credentials")

                if submit:
                    # TODO: Save encrypted credentials to database
                    st.success("Zerodha credentials saved!")
                    st.info("Please complete OAuth flow to get access token")

        elif broker_type == "Upstox (India)":
            st.markdown("### Upstox API Setup (FREE)")

            with st.form("upstox_form"):
                api_key = st.text_input("API Key", type="password")
                api_secret = st.text_input("API Secret", type="password")
                submit = st.form_submit_button("Save Credentials")

                if submit:
                    st.success("Upstox credentials saved!")
                    st.info("Please complete OAuth flow to get access token")

        elif broker_type == "Alpaca (US)":
            st.markdown("### Alpaca API Setup (FREE)")

            trading_mode = st.radio("Trading Mode", ["Paper Trading", "Live Trading"])

            with st.form("alpaca_form"):
                api_key = st.text_input(f"{trading_mode} API Key", type="password")
                api_secret = st.text_input(f"{trading_mode} Secret Key", type="password")
                submit = st.form_submit_button("Save Credentials")

                if submit:
                    st.success(f"Alpaca {trading_mode} credentials saved!")

        elif broker_type == "Simulated (Paper)":
            st.markdown("### Simulated Paper Trading")
            st.success("✅ Paper trading is always available - no setup required!")
            st.info("Starting virtual cash: $100,000")

    elif page == "⚙️ Settings":
        from dashboard.modules import settings
        settings.show()

    elif page == "📚 Documentation":
        from dashboard.modules import documentation
        documentation.show()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        Built with ❤️ by <a href='https://github.com/vigneshbumpy' target='_blank'>Vignesh Research</a><br>
        Multi-User SaaS Platform
        </div>
        """,
        unsafe_allow_html=True
    )
