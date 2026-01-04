# 🚀 Quick Start - TradingAgents

Get started with AI-powered stock trading in 5 minutes!

---

## ⚡ Fastest Way to Start (FREE with Ollama)

```bash
# 1. Install Ollama (one-time)
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh
# Windows: Download from https://ollama.ai/download

# 2. Pull required models (one-time)
ollama pull llama3.2
ollama pull qwen2.5:32b

# 3. Install dependencies
pip install -r requirements.txt
pip install -r dashboard/requirements.txt

# 4. Start dashboard
streamlit run dashboard/app.py

# 5. Open http://localhost:8501 in browser
```

**That's it!** Budget tier (Ollama) works out of the box - no API keys needed for LLM!

---

## 🔑 LLM Tier Options

TradingAgents offers **three LLM tiers** you can switch between anytime:

| Tier | Provider | Cost | Quality | Speed |
|------|----------|------|---------|-------|
| **Budget** (Default) | Ollama (Local) | FREE | Good | Medium (depends on hardware) |
| **Best Value** ⭐ | OpenRouter | $15-30/mo | Excellent | Very Fast |
| **Premium** | Anthropic | $50-100/mo | Best | Fast |

### Switching Tiers (In Dashboard)

1. Go to **Settings** page
2. Select your preferred tier
3. Enter API key if required
4. Click **Switch** - applies instantly!

### API Keys (Only for Best Value/Premium)

**OpenRouter (Best Value Tier):**
- Get key: https://openrouter.ai/keys
- Sign up with Google/GitHub → Keys → Create

**Anthropic (Premium Tier):**
- Get key: https://console.anthropic.com
- Create account → API Keys → Create

---

## 📈 Data API (Required for All Tiers)

### **Alpha Vantage (Stock Data) - FREE**

**Get it here:** https://www.alphavantage.co/support/#api-key

1. Enter your email
2. Receive key instantly
3. **Option A (Dashboard):** Go to Settings → enter key when prompted
4. **Option B (.env file):**
   ```bash
   # Create .env file
   echo "ALPHA_VANTAGE_API_KEY=your_key_here" >> .env
   ```

**Free tier:** 60 API calls/minute (TradingAgents-enhanced rate limit)

---

## 📊 First Stock Analysis

1. **Start dashboard** (if not running):
   ```bash
   streamlit run dashboard/app.py
   ```

2. **Go to "Stock Analysis" page** (sidebar)

3. **Enter a stock ticker**:
   - US stocks: `NVDA`, `AAPL`, `MSFT`, `TSLA`, `GOOGL`
   - Indian stocks: `RELIANCE.NS`, `TCS.NS`, `INFY.NS`

4. **Select analysts** (recommended):
   - ✅ market
   - ✅ news
   - ✅ fundamentals
   - ✅ technical (TradingView-style) 🆕

5. **Click "Run Analysis"**

6. **Wait 2-4 minutes** for multi-agent AI analysis

7. **Review results**:
   - Overall recommendation (BUY/SELL/HOLD)
   - Analyst reports (5 tabs)
   - Technical analysis with TradingView rating
   - Support/resistance levels
   - Risk assessment

8. **Take action**:
   - ✅ Approve & Execute (paper trade)
   - ❌ Reject
   - 💾 Save to Watchlist
   - 🔄 Re-analyze

---

## 🎯 What Each Analyst Does

| Analyst | What It Analyzes |
|---------|-----------------|
| **Market** | Price trends, technical indicators (MACD, RSI, Bollinger) |
| **News** | Recent news, sentiment, market events |
| **Fundamentals** | Financial statements, P/E ratio, earnings, balance sheet |
| **Technical** 🆕 | TradingView-style chart analysis, 15+ indicators, support/resistance |
| **Research Team** | Bull vs Bear debate on whether to invest |
| **Trading Team** | Specific entry/exit prices, position sizing |
| **Risk Team** | Risk assessment, stop-loss recommendations |

---

## 💰 Paper Trading (FREE)

**What is paper trading?**
- Simulated trading with $100,000 virtual cash
- Test strategies without risking real money
- Perfect for learning and testing

**How to use:**
1. Run analysis
2. Click "Approve & Execute"
3. Enter quantity (shares)
4. Click "Confirm Trade"
5. View in Portfolio page

**Recommended:** Practice with paper trading for 2-4 weeks before live trading!

---

## 🔧 Live Trading (Optional)

Want to trade with real money? Connect a broker:

### **US Stocks (FREE):**
- **Alpaca**: https://alpaca.markets/
- Get API keys → Add to .env

### **Indian Stocks:**
- **Upstox** (FREE API): https://upstox.com/developer/
- **Zerodha** (₹2,000/month): https://kite.trade/

See Settings page → Broker Setup for details.

---

## 📖 Full Documentation

- **COMPLETE_GUIDE.md** - Everything you need to know
- **README.md** - Original project documentation

---

## ⚠️ Important Notes

### **Trading Risks**
- AI is not perfect - always verify recommendations
- Start with paper trading
- Never risk more than 1-2% per trade
- Use stop losses
- This is not financial advice - DYOR

### **Costs**
- **Budget tier (Ollama):** FREE - runs locally
- **Best Value tier (OpenRouter):** $15-30/month (50 analyses)
- **Premium tier (Anthropic):** $50-100/month (50 analyses)
- Alpha Vantage data: FREE (60 calls/min)
- Paper trading: FREE
- Alpaca (US stocks): FREE
- Upstox (Indian stocks): FREE API

### **System Requirements**
- Python 3.11+
- 4GB RAM minimum
- Internet connection

---

## 🚨 Troubleshooting

### **"API key not found" error**
```bash
# Option 1: Check in Dashboard Settings
# Go to Settings page → Your tier should show API key status

# Option 2: Check database
sqlite3 dashboard/trading.db "SELECT key_name FROM secrets"

# Option 3: Check .env (legacy)
cat .env 2>/dev/null | grep API_KEY

# If keys exist in .env but not in database, they auto-migrate on next startup
```

### **"Module not found" error**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
pip install --upgrade -r dashboard/requirements.txt
```

### **Dashboard won't start**
```bash
# Check if port 8501 is already in use
lsof -i :8501

# Kill existing process (if needed)
kill -9 <PID>

# Or use different port
streamlit run dashboard/app.py --server.port 8502
```

### **Slow analysis**
- First run is always slower (loading models)
- Subsequent runs are faster (cached)
- **Budget tier (Ollama):** Speed depends on your hardware
  - Recommended: 16GB+ RAM, modern CPU
  - For faster results, upgrade to Best Value tier
- **Best Value tier (OpenRouter):** Very fast cloud inference
- Switch tiers instantly in Settings page

---

## 🎓 Next Steps

1. ✅ Run your first analysis
2. ✅ Review all 5 analyst reports
3. ✅ Try technical analysis (TradingView-style)
4. ✅ Execute paper trades
5. ✅ Track portfolio
6. ⏳ Test different stocks
7. ⏳ Try live monitoring & override
8. ⏳ Connect real broker (optional)
9. ⏳ Deploy to cloud (optional)

---

## 💬 Need Help?

- **Documentation**: Read COMPLETE_GUIDE.md
- **GitHub Issues**: https://github.com/vigneshbumpy/TradingAgents/issues
- **Discord**: https://discord.com/invite/hk9PGKShPK

---

**Happy Trading! 🚀📈**

*Built with ❤️ using TradingAgents Multi-Agent Framework*
