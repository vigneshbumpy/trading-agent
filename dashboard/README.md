# TradingAgents Dashboard

A comprehensive Streamlit-based web dashboard for the TradingAgents framework with real-time analysis, portfolio tracking, and broker integration.

## Features

### 🏠 Dashboard Page
- Portfolio overview and account summary
- Current positions with P/L tracking
- Recent analyses and trades
- Quick action buttons

### 🔍 Stock Analysis Page
- Interactive stock analysis configuration
- Live agent execution with progress tracking
- Comprehensive reports from all agent teams
- Action buttons: Approve, Reject, Save to Watchlist
- Trade execution with broker integration

### 💼 Portfolio Page
- Current holdings and positions
- Portfolio allocation visualization
- Performance metrics and P/L tracking
- Position management actions
- Watchlist management

### 📊 Trade History Page
- Complete trade history with filters
- Trading analytics and visualizations
- Export functionality (CSV)
- Performance tracking

### ⚙️ Settings Page
- Trading mode configuration (Paper/Live)
- Broker setup (Simulated/Alpaca)
- LLM provider configuration
- Risk management settings
- Research defaults

### 📚 Documentation Page
- Quick start guide
- How TradingAgents works
- Best practices
- API configuration guide
- LLM model recommendations
- Troubleshooting

## Installation

### 1. Install Dashboard Dependencies

```bash
cd dashboard
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create or update `.env` file in the project root:

```bash
# LLM Provider (choose one or multiple)
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-v1-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Data Provider
ALPHA_VANTAGE_API_KEY=your_key

# Broker (optional, for Alpaca integration)
ALPACA_PAPER_API_KEY=your_key
ALPACA_PAPER_SECRET_KEY=your_secret

# For live trading (use with caution!)
ALPACA_LIVE_API_KEY=your_key
ALPACA_LIVE_SECRET_KEY=your_secret
```

## Usage

### Start the Dashboard

```bash
# From project root
cd /Users/vigneshnagarajan/personal/TradingAgents
streamlit run dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### First Time Setup

1. **Configure Settings**: Go to Settings page and set up:
   - Trading mode (start with Paper Trading)
   - LLM provider and API keys
   - Broker (start with Simulated)

2. **Run First Analysis**: Go to Stock Analysis page:
   - Enter ticker (e.g., NVDA)
   - Select analysts and research depth
   - Click "Run Analysis"

3. **Review Results**:
   - Read through all team reports
   - Check final recommendation
   - Use action buttons to approve/reject

4. **Execute Trade**:
   - If approved, enter quantity
   - Confirm execution
   - Trade will be saved to database

5. **Monitor Portfolio**:
   - Check Portfolio page for holdings
   - Review Trade History for past trades
   - Track performance

## Broker Integration

### Simulated Broker (Default)
- No external API required
- Starts with $100,000 virtual cash
- All trades tracked in memory
- Perfect for testing

### Alpaca Integration
- Real broker API integration
- Supports both paper and live trading
- Requires Alpaca account and API keys

**Setup Alpaca:**
1. Create account at [alpaca.markets](https://alpaca.markets)
2. Get API keys from dashboard
3. Add keys to `.env` file
4. Select "Alpaca" in Settings

## LLM Model Recommendations

### Best Models for Stock Trading (via OpenRouter)

**Most Recommended:**
- **DeepSeek R1**: Exceptional reasoning with chain-of-thought ($2.19/M tokens)
- **DeepSeek V3**: Best value for complex analysis ($0.27/M tokens)
- **Claude Sonnet 4**: Superior decision-making ($3-15/M tokens)

**Recommended Configuration:**
- Quick Thinking: `deepseek/deepseek-chat` (DeepSeek V3)
- Deep Thinking: `deepseek/deepseek-r1` (DeepSeek R1)
- Total cost: ~$20-50/month for 50 analyses

**For Testing:**
- Quick: `meta-llama/llama-3.3-8b-instruct` (FREE)
- Deep: `deepseek/deepseek-chat` ($0.27/M)

See Documentation page in dashboard for complete model comparison.

## Database

The dashboard uses SQLite for data persistence:
- Location: `dashboard/data/trading.db`
- Auto-created on first run
- Stores: analyses, trades, portfolio, watchlist, settings

**Tables:**
- `analyses`: All stock analyses with reports
- `trades`: Trade history
- `portfolio`: Current holdings
- `watchlist`: Saved tickers
- `settings`: User preferences

## File Structure

```
dashboard/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Dashboard dependencies
├── README.md              # This file
├── pages/                 # Dashboard pages
│   ├── __init__.py
│   ├── home.py           # Dashboard/overview
│   ├── analysis.py       # Stock analysis
│   ├── portfolio.py      # Portfolio management
│   ├── trade_history.py  # Trade history
│   ├── settings.py       # Settings and configuration
│   └── documentation.py  # Help and docs
├── utils/                 # Utility modules
│   ├── __init__.py
│   ├── database.py       # SQLite database operations
│   └── broker.py         # Broker integrations
├── components/            # Reusable UI components (future)
└── data/                  # Database files (auto-created)
    └── trading.db
```

## Best Practices

### Risk Management
1. **Start with Paper Trading**: Test thoroughly before real money
2. **Position Sizing**: Never risk more than 1-2% per trade
3. **Diversification**: Don't concentrate in one stock
4. **Stop Losses**: Always have exit strategy
5. **Review Regularly**: Check trade history and performance

### Using the Dashboard
1. **Run Multiple Analyses**: Compare results over time
2. **Read All Reports**: Don't just trust the final recommendation
3. **Manual Override**: You make the final decision
4. **Track Performance**: Review trade history monthly
5. **Adjust Research Depth**: Use higher depth for important decisions

### Cost Management
1. **Use Cheaper Models for Testing**: llama-3.3-8b, gemini-flash (FREE)
2. **Optimize Research Depth**: Depth=1 for quick checks, 3-5 for important decisions
3. **Select Relevant Analysts**: Don't always use all 4 analysts
4. **Batch Analyses**: Analyze multiple stocks in one session

## Troubleshooting

### Dashboard Won't Start
```bash
# Check if streamlit is installed
streamlit --version

# Reinstall if needed
pip install streamlit

# Try starting with verbose output
streamlit run dashboard/app.py --logger.level=debug
```

### API Errors
- Check `.env` file exists and has correct keys
- Verify API key has credits/quota
- Check internet connection
- Review Settings page for API status

### Database Errors
```bash
# Reset database (WARNING: deletes all data)
rm dashboard/data/trading.db

# Restart dashboard to recreate
streamlit run dashboard/app.py
```

### Analysis Fails
- Reduce research depth to 1
- Use fewer analysts
- Try different LLM model
- Check ticker symbol is valid
- Verify analysis date is not future/weekend

## Support

- **GitHub**: [vigneshbumpy/TradingAgents](https://github.com/vigneshbumpy/TradingAgents)
- **Discord**: [Vignesh Research Community](https://discord.com/invite/hk9PGKShPK)
- **Documentation**: Check Documentation page in dashboard

## Disclaimer

⚠️ **IMPORTANT**: This tool is for educational and research purposes only. It does NOT constitute financial advice. Trading stocks involves substantial risk of loss. Always do your own research and never trade with money you can't afford to lose.

See full disclaimer in Documentation page.

## License

See main project LICENSE file.
