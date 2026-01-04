"""
TradingAgents Streamlit Dashboard
Main application file with multi-page navigation and real-time analysis
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Auto-migrate .env keys to database on first run
try:
    from dashboard.utils.config_manager import ConfigManager
    config_manager = ConfigManager()

    # Check if migration needed (no secrets in database)
    if not config_manager.secrets_manager.list_secrets():
        from dashboard.utils.migrate_env_to_db import migrate_env_to_database
        migrate_env_to_database()
except Exception as e:
    # Don't block app startup if migration fails
    print(f"Migration warning: {e}")

# Page configuration
st.set_page_config(
    page_title="TradingAgents Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
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
    .stButton>button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_running' not in st.session_state:
    st.session_state.analysis_running = False
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []
if 'paper_trading_enabled' not in st.session_state:
    st.session_state.paper_trading_enabled = True
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Dashboard"

# Sidebar navigation
st.sidebar.title("📈 TradingAgents")
st.sidebar.markdown("---")

# Navigation menu with clickable buttons
st.sidebar.markdown("### Navigation")
nav_options = [
    "🏠 Dashboard",
    "🔍 Stock Analysis",
    "💼 Portfolio",
    "📊 Trade History",
    "⚙️ Settings",
    "📚 Documentation"
]

for option in nav_options:
    if st.sidebar.button(option, key=f"nav_{option}", use_container_width=True):
        st.session_state.current_page = option

page = st.session_state.current_page

# Broker status in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### Broker Status")
if st.session_state.paper_trading_enabled:
    st.sidebar.success("📝 Paper Trading Mode")
else:
    st.sidebar.warning("🔴 Live Trading Mode")

# API status
api_status = {}
if os.getenv("OPENAI_API_KEY"):
    api_status["OpenAI"] = "✅"
else:
    api_status["OpenAI"] = "❌"

if os.getenv("ALPHA_VANTAGE_API_KEY"):
    api_status["Alpha Vantage"] = "✅"
else:
    api_status["Alpha Vantage"] = "❌"

st.sidebar.markdown("### API Status")
for api, status in api_status.items():
    st.sidebar.markdown(f"{api}: {status}")

# Main content area
if page == "🏠 Dashboard":
    from views import home
    home.show()
elif page == "🔍 Stock Analysis":
    from views import analysis
    analysis.show()
elif page == "💼 Portfolio":
    from views import portfolio
    portfolio.show()
elif page == "📊 Trade History":
    from views import trade_history
    trade_history.show()
elif page == "⚙️ Settings":
    from views import settings
    settings.show()
elif page == "📚 Documentation":
    from views import documentation
    documentation.show()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
    Built with ❤️ by <a href='https://github.com/vigneshbumpy' target='_blank'>Vignesh Research</a><br>
    Powered by Multi-Agent LLMs
    </div>
    """,
    unsafe_allow_html=True
)
