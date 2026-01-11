# Quick Start - TradingAgents

Get started with AI-powered multi-market trading in 5 minutes!

---

## Installation

```bash
# 1. Clone and enter directory
git clone https://github.com/vigneshbumpy/TradingAgents.git
cd TradingAgents

# 2. Create virtual environment
conda create -n tradingagents python=3.13
conda activate tradingagents

# 3. Install dependencies
pip install -r requirements.txt

# Verify setup
python verify_setup.py

# 4. Start dashboard
streamlit run dashboard/app.py

# 5. Open http://localhost:8501 in browser
```

---

## Supported Markets

| Market | Brokers | Assets |
|--------|---------|--------|
| **Indian** | Zerodha, Upstox | NSE/BSE stocks |
| **US** | Alpaca | NYSE/NASDAQ stocks |
| **Crypto** | Binance, Coinbase | BTC, ETH, and 100+ coins |

---

## LLM Tiers

| Tier | Provider | Cost | Best For |
|------|----------|------|----------|
| **Budget** (Default) | Ollama (Local) | FREE | Testing |
| **Best Value** | OpenRouter | $15-30/mo | Production |
| **Premium** | Anthropic | $50-100/mo | Best quality |

### Budget Tier Setup (FREE)
```bash
# Install Ollama
brew install ollama  # macOS
# or: curl -fsSL https://ollama.ai/install.sh | sh  # Linux

# Pull models
ollama pull llama3.2
ollama pull qwen2.5:32b
```

---

## Running Your First Analysis

1. Start dashboard: `streamlit run dashboard/app.py`
2. Click **"Stock Analysis"** in sidebar
3. Enter ticker (e.g., `NVDA`, `RELIANCE`, `BTC`)
4. Select analysts and click **"Run Analysis"**
5. Review recommendation and reports
6. **Approve & Execute** to paper trade

---

## Automated Trading

### Quick Setup

1. Click **"Automation"** in sidebar
2. Add symbols to watchlist (e.g., `AAPL`, `BTC`, `RELIANCE`)
3. Click **"Start Automation"**
4. System runs in **paper trading mode** by default

### Paper Trading Safety

- All systems start in paper trading mode
- Requires 10+ paper trades before live trading
- Double confirmation required for live trading
- Visual indicators: 📝 Paper | 🔴 Live

### Enable Live Trading (After Verification)

1. Complete 10+ paper trades
2. Go to **Trading Mode Configuration**
3. Check "I understand live trading uses real money"
4. Click **"Enable Live Trading"** (double confirmation)

---

## Broker Configuration

### Settings → Broker Configuration

**Indian Markets:**
- Select Zerodha or Upstox
- Enter API key and secret

**US Markets:**
- Select Alpaca
- Enter API credentials
- Enable paper trading (recommended)

**Crypto Markets:**
- Select Binance or Coinbase
- Enter API credentials
- Enable testnet/sandbox (recommended)

---

## Data API (Required)

### Alpha Vantage (FREE)

1. Get key: https://www.alphavantage.co/support/#api-key
2. Enter in dashboard Settings or add to `.env`:
   ```bash
   echo "ALPHA_VANTAGE_API_KEY=your_key" >> .env
   ```

---

## Project Structure

```
TradingAgents/
├── dashboard/              # Web dashboard (Streamlit)
│   ├── app.py             # Main application
│   ├── views/             # UI pages
│   └── multiuser/brokers/ # Broker integrations
├── tradingagents/         # Core trading framework
│   ├── agents/            # AI analysts & traders
│   ├── graph/             # Trading graph logic
│   ├── services/          # Automation services
│   └── dataflows/         # Data providers
├── cli/                   # Command-line interface
├── scanner/               # Stock scanner
└── tests/                 # Test suite
```

---

## Troubleshooting

### Dashboard won't start
```bash
# Check port
lsof -i :8501

# Use different port
streamlit run dashboard/app.py --server.port 8502
```

### Module not found
```bash
pip install --upgrade -r requirements.txt
```

### API key errors
- Check Settings page in dashboard
- Or verify `.env` file has correct keys

---

## Important Notes

- **Start with paper trading** - Test thoroughly before live trading
- **AI is not perfect** - Always verify recommendations
- **Never risk more than 1-2%** per trade
- **Use stop losses** - Protect your capital
- **This is not financial advice** - DYOR

---

## Need Help?

- **GitHub Issues**: https://github.com/vigneshbumpy/TradingAgents/issues
- **Discord**: https://discord.com/invite/hk9PGKShPK

---

**Happy Trading!**
