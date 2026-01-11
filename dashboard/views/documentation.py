"""
Documentation page with guides and help
"""

import streamlit as st


def show():
    """Display documentation page"""
    st.markdown("<h1 class='main-header'>📚 Documentation</h1>", unsafe_allow_html=True)

    # Quick Start Guide
    with st.expander("🚀 Quick Start Guide", expanded=True):
        st.markdown("""
        ### Getting Started with TradingAgents Dashboard

        #### 1. Configure Your Settings
        - Go to **Settings** page
        - Set your **Trading Mode** (Paper Trading recommended for beginners)
        - Configure **API Keys** for your LLM provider and data sources
        - Choose your **Broker** (Simulated or Alpaca)

        #### 2. Run Your First Analysis
        - Navigate to **Stock Analysis** page
        - Enter a ticker symbol (e.g., NVDA, AAPL, SPY)
        - Select analysis date and research depth
        - Choose which analyst agents to include
        - Click **Run Analysis**

        #### 3. Review & Execute
        - Review the comprehensive analysis from all agent teams
        - Check the final BUY/SELL/HOLD recommendation
        - Click **Approve & Execute** to place the trade
        - Or click **Reject** to decline the recommendation

        #### 4. Monitor Your Portfolio
        - View your **Portfolio** page to see current holdings
        - Check **Trade History** to review past trades
        - Monitor performance and unrealized P/L
        """)

    # How It Works
    with st.expander("🔍 How TradingAgents Works"):
        st.markdown("""
        ### Multi-Agent Architecture

        TradingAgents uses a hierarchical team of specialized LLM agents:

        #### 1. **Analyst Team** (Data Gathering & Analysis)
        - **Market Analyst**: Technical indicators (MACD, RSI, Moving Averages)
        - **Sentiment Analyst**: Social media and sentiment scoring
        - **News Analyst**: Global news and macroeconomic events
        - **Fundamentals Analyst**: Financial statements and company metrics

        #### 2. **Research Team** (Strategic Evaluation)
        - **Bull Researcher**: Identifies reasons to buy
        - **Bear Researcher**: Identifies risks and reasons to sell
        - **Research Manager**: Synthesizes both perspectives into recommendation

        #### 3. **Trading Team** (Execution Planning)
        - **Trader**: Creates detailed trading plan based on research
        - Considers timing, position sizing, and entry/exit points

        #### 4. **Risk Management Team** (Final Validation)
        - **Aggressive Analyst**: Evaluates upside potential
        - **Conservative Analyst**: Evaluates downside risks
        - **Neutral Analyst**: Provides balanced perspective
        - **Portfolio Manager**: Makes final BUY/SELL/HOLD decision

        ### Debate & Consensus
        - Agents engage in structured debates (configurable rounds)
        - Multiple perspectives ensure thorough analysis
        - Final decision incorporates risk management and portfolio considerations
        """)

    # Best Practices
    with st.expander("💡 Best Practices"):
        st.markdown("""
        ### Trading Best Practices

        #### Risk Management
        1. **Start with Paper Trading**: Test strategies without real money
        2. **Position Sizing**: Never risk more than 1-2% of portfolio on single trade
        3. **Diversification**: Don't put all eggs in one basket
        4. **Stop Losses**: Always set stop loss orders
        5. **Take Profits**: Have clear exit strategy for winners

        #### Using TradingAgents Effectively
        1. **Research Depth**: Use higher depth for important decisions
        2. **Multiple Analyses**: Run analysis multiple times and compare
        3. **Review All Reports**: Don't just look at final recommendation
        4. **Manual Override**: You're the final decision maker
        5. **Track Performance**: Review trade history regularly

        #### LLM Model Selection
        1. **For Testing**: Use cheaper models (gpt-4o-mini, llama-3.3-8b)
        2. **For Real Decisions**: Use advanced models (DeepSeek R1, Claude Sonnet 4, o1)
        3. **Balance Cost/Quality**: DeepSeek V3 offers best value
        4. **Quick vs Deep**: Use fast models for quick analysis, reasoning models for deep analysis

        #### Market Conditions
        1. **Bull Market**: More aggressive with long positions
        2. **Bear Market**: Focus on capital preservation
        3. **Volatile Markets**: Reduce position sizes
        4. **Low Volume**: Avoid trading during low liquidity
        """)

    # API Configuration
    with st.expander("🔧 API Configuration Guide"):
        st.markdown("""
        ### Required API Keys

        #### LLM Providers (Choose One)

        **OpenAI** (Recommended for Beginners)
        - Create account at [platform.openai.com](https://platform.openai.com)
        - Generate API key in API settings
        - Set environment variable: `OPENAI_API_KEY`
        - Recommended models: gpt-4o-mini (quick), o4-mini (deep)

        **OpenRouter** (Best Value)
        - Create account at [openrouter.ai](https://openrouter.ai)
        - Generate API key in settings
        - Set environment variable: `OPENROUTER_API_KEY`
        - Access to 100+ models including DeepSeek R1, Claude, GPT-4
        - Recommended: DeepSeek V3 (quick), DeepSeek R1 (deep)

        **Anthropic**
        - Create account at [console.anthropic.com](https://console.anthropic.com)
        - Generate API key
        - Set environment variable: `ANTHROPIC_API_KEY`
        - Recommended: claude-3-5-haiku (quick), claude-sonnet-4 (deep)

        #### Data Providers

        **Alpha Vantage** (Recommended)
        - Free tier: 25 requests/day
        - Premium: Unlimited requests
        - Get key at [alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)
        - Set environment variable: `ALPHA_VANTAGE_API_KEY`

        **Yahoo Finance** (Free Alternative)
        - No API key required
        - Uses yfinance Python library
        - Rate limited, less reliable

        #### Broker (Optional)

        **Alpaca**
        - Paper Trading: Free with unlimited virtual money
        - Create account at [alpaca.markets](https://alpaca.markets)
        - Get paper trading keys from dashboard
        - Set environment variables:
          - `ALPACA_PAPER_API_KEY`
          - `ALPACA_PAPER_SECRET_KEY`

        ### Environment Variables Setup

        Create `.env` file in project root:
        ```
        # LLM Provider (choose one)
        OPENAI_API_KEY=sk-...
        OPENROUTER_API_KEY=sk-or-v1-...
        ANTHROPIC_API_KEY=sk-ant-...

        # Data Provider
        ALPHA_VANTAGE_API_KEY=your_key

        # Broker (optional)
        ALPACA_PAPER_API_KEY=your_key
        ALPACA_PAPER_SECRET_KEY=your_secret
        ```
        """)

    # LLM Model Recommendations
    with st.expander("🤖 LLM Model Recommendations"):
        st.markdown("""
        ### Best Models for Stock Trading (2025)

        #### Tier 1: Premium (Best Accuracy)
        | Model | Provider | Cost | Best For |
        |-------|----------|------|----------|
        | DeepSeek R1 | OpenRouter | $2.19/M | Complex reasoning, multi-step analysis |
        | Claude Sonnet 4 | Anthropic/OpenRouter | $3-15/M | Superior decision-making |
        | o1 | OpenAI | $15/M input | Deep reasoning, critical decisions |
        | Claude Opus 4 | Anthropic | $15-75/M | Highest quality analysis |

        #### Tier 2: Balanced (Best Value)
        | Model | Provider | Cost | Best For |
        |-------|----------|------|----------|
        | DeepSeek V3 | OpenRouter | $0.27/M | Best cost/performance ratio |
        | Llama 3.3 70B | OpenRouter | $0.35/M | Solid all-around performance |
        | GPT-4o | OpenAI/OpenRouter | $2.50-10/M | Reliable analysis |
        | Qwen 2.5 72B | OpenRouter | $0.35/M | Strong analytical skills |

        #### Tier 3: Budget (Testing)
        | Model | Provider | Cost | Best For |
        |-------|----------|------|----------|
        | Llama 3.3 8B | OpenRouter | FREE | Quick tests |
        | Gemini Flash 2.0 | Google/OpenRouter | FREE | Rapid iterations |
        | gpt-4o-mini | OpenAI | $0.15-0.60/M | Development |

        ### Recommended Combinations

        **For Serious Trading:**
        - Quick: DeepSeek V3 ($0.27/M)
        - Deep: DeepSeek R1 ($2.19/M)
        - Total Cost: ~$20-50/month for 50 analyses

        **For High-Stakes Decisions:**
        - Quick: GPT-4o
        - Deep: Claude Opus 4 or o1
        - Total Cost: ~$100-200/month for 50 analyses

        **For Testing/Learning:**
        - Quick: Llama 3.3 8B (FREE)
        - Deep: DeepSeek V3 ($0.27/M)
        - Total Cost: ~$5/month for 50 analyses

        ### Why DeepSeek R1 is Excellent for Trading:
        1. **Chain-of-Thought Reasoning**: Shows its thinking process
        2. **Multi-Step Analysis**: Breaks down complex decisions
        3. **Risk Assessment**: Strong at evaluating pros/cons
        4. **Cost-Effective**: 10x cheaper than o1 with similar quality
        5. **Fast**: Faster inference than o1
        """)

    # Troubleshooting
    with st.expander("🔧 Troubleshooting"):
        st.markdown("""
        ### Common Issues

        #### "API Key Not Found"
        - Ensure `.env` file is in project root
        - Check environment variable names match exactly
        - Restart dashboard after adding keys

        #### "Analysis Failed"
        - Check API key is valid and has credits
        - Verify internet connection
        - Check rate limits (Alpha Vantage: 25/day free tier)
        - Try reducing research depth

        #### "Broker Connection Failed"
        - Verify API keys are correct
        - Check if using paper trading keys for paper mode
        - Ensure Alpaca account is active

        #### "No Data Returned"
        - Verify ticker symbol is correct
        - Check if market is open (for real-time data)
        - Try different data provider
        - Ensure analysis date is not weekend/holiday

        #### "Slow Analysis"
        - Reduce research depth
        - Use faster models (gpt-4o-mini, llama-3.3-8b)
        - Reduce number of analysts
        - Check internet speed

        ### Getting Help
        - GitHub Issues: [github.com/vigneshbumpy/TradingAgents](https://github.com/vigneshbumpy/TradingAgents)
        - Discord: [Vignesh Research Community](https://discord.com/invite/hk9PGKShPK)
        - Documentation: Check README.md in project root
        """)

    # Disclaimer
    with st.expander("⚠️ Important Disclaimer"):
        st.markdown("""
        ### Risk Disclaimer

        **IMPORTANT: READ CAREFULLY**

        1. **Not Financial Advice**: This tool is for educational and research purposes only. It does NOT constitute financial, investment, or trading advice.

        2. **No Guarantees**: Past performance does not indicate future results. LLM-based analysis is non-deterministic and can produce different outputs for same inputs.

        3. **You Are Responsible**: You are solely responsible for your trading decisions and their consequences. Always do your own research.

        4. **Risk of Loss**: Trading stocks involves substantial risk of loss. Only trade with money you can afford to lose.

        5. **AI Limitations**: LLMs can make mistakes, hallucinate data, or miss critical information. Always verify information independently.

        6. **Market Volatility**: Markets can be extremely volatile. News and events can change rapidly, making any analysis outdated.

        7. **Paper Trading First**: Always test strategies with paper trading before risking real money.

        8. **Professional Advice**: Consider consulting with a licensed financial advisor before making investment decisions.

        9. **Regulatory Compliance**: Ensure your trading activities comply with local laws and regulations.

        10. **Beta Software**: This dashboard is experimental software. Bugs and errors may occur. Use at your own risk.

        **By using this tool, you acknowledge and accept these risks.**
        """)

    # About
    st.markdown("---")
    st.markdown("## ℹ️ About TradingAgents")

    st.markdown("""
    **TradingAgents** is a multi-agent LLM trading framework developed by [Vignesh Research](https://Vignesh.ai/).

    - **GitHub**: [github.com/vigneshbumpy/TradingAgents](https://github.com/vigneshbumpy/TradingAgents)
    - **Paper**: [arXiv:2412.20138](https://arxiv.org/abs/2412.20138)
    - **Discord**: [Vignesh Research Community](https://discord.com/invite/hk9PGKShPK)
    - **Version**: 1.0.0
    - **License**: See LICENSE file

    **Dashboard Created By**: Claude Code (Anthropic)
    """)
