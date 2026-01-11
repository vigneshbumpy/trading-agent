"""
Enhanced Stock Analysis page with graceful error handling
Shows "Not Available" for failed data sources and provides recommendations based on available data
Includes TradingView chart integration and real-time technical ratings
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.utils.database import TradingDatabase
from dashboard.utils.broker import get_broker, OrderSide
from dashboard.utils.config_manager import ConfigManager

db = TradingDatabase()


# ===== TRADINGVIEW INTEGRATION =====

def get_tradingview_analysis(ticker: str, exchange: str = "NASDAQ") -> dict:
    """
    Get real TradingView technical analysis ratings

    Returns:
        dict with recommendation, buy/sell/neutral counts, and indicator details
    """
    try:
        from tradingview_ta import TA_Handler, Interval

        # Try common exchanges for US stocks
        exchanges_to_try = [exchange, "NASDAQ", "NYSE", "AMEX"]

        for exch in exchanges_to_try:
            try:
                handler = TA_Handler(
                    symbol=ticker,
                    screener="america",
                    exchange=exch,
                    interval=Interval.INTERVAL_1_DAY
                )
                analysis = handler.get_analysis()

                return {
                    'status': 'success',
                    'exchange': exch,
                    'recommendation': analysis.summary['RECOMMENDATION'],
                    'buy': analysis.summary['BUY'],
                    'sell': analysis.summary['SELL'],
                    'neutral': analysis.summary['NEUTRAL'],
                    'oscillators': {
                        'recommendation': analysis.oscillators['RECOMMENDATION'],
                        'buy': analysis.oscillators['BUY'],
                        'sell': analysis.oscillators['SELL'],
                        'neutral': analysis.oscillators['NEUTRAL'],
                    },
                    'moving_averages': {
                        'recommendation': analysis.moving_averages['RECOMMENDATION'],
                        'buy': analysis.moving_averages['BUY'],
                        'sell': analysis.moving_averages['SELL'],
                        'neutral': analysis.moving_averages['NEUTRAL'],
                    },
                    'indicators': {
                        'rsi': analysis.indicators.get('RSI'),
                        'macd': analysis.indicators.get('MACD.macd'),
                        'macd_signal': analysis.indicators.get('MACD.signal'),
                        'ema20': analysis.indicators.get('EMA20'),
                        'sma20': analysis.indicators.get('SMA20'),
                        'sma50': analysis.indicators.get('SMA50'),
                        'sma200': analysis.indicators.get('SMA200'),
                        'adx': analysis.indicators.get('ADX'),
                        'cci': analysis.indicators.get('CCI20'),
                        'atr': analysis.indicators.get('ATR'),
                        'high': analysis.indicators.get('high'),
                        'low': analysis.indicators.get('low'),
                        'close': analysis.indicators.get('close'),
                        'volume': analysis.indicators.get('volume'),
                    }
                }
            except Exception:
                continue

        return {'status': 'error', 'error': f'Could not find {ticker} on any exchange'}

    except ImportError:
        return {'status': 'error', 'error': 'tradingview-ta not installed. Run: pip install tradingview-ta'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def render_tradingview_chart(ticker: str, exchange: str = "NASDAQ", height: int = 500):
    """
    Render an embedded TradingView chart widget
    """
    # TradingView Widget HTML
    widget_html = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container" style="height:{height}px;width:100%">
      <div id="tradingview_chart" style="height:calc(100% - 32px);width:100%"></div>
      <div class="tradingview-widget-copyright">
        <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">
          <span class="blue-text">Track all markets on TradingView</span>
        </a>
      </div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{exchange}:{ticker}",
        "interval": "D",
        "timezone": "America/New_York",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart",
        "hide_side_toolbar": false,
        "studies": [
          "RSI@tv-basicstudies",
          "MASimple@tv-basicstudies",
          "MACD@tv-basicstudies"
        ]
      }});
      </script>
    </div>
    <!-- TradingView Widget END -->
    """

    components.html(widget_html, height=height + 50)


def render_tradingview_technical_analysis(ticker: str, exchange: str = "NASDAQ", height: int = 450):
    """
    Render TradingView Technical Analysis widget showing buy/sell ratings
    """
    widget_html = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
      {{
        "interval": "1D",
        "width": "100%",
        "isTransparent": false,
        "height": {height},
        "symbol": "{exchange}:{ticker}",
        "showIntervalTabs": true,
        "displayMode": "single",
        "locale": "en",
        "colorTheme": "light"
      }}
      </script>
    </div>
    <!-- TradingView Widget END -->
    """

    components.html(widget_html, height=height + 20)

# Default watchlist stocks
DEFAULT_WATCHLIST = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AMD", "INTC", "NFLX"]


class DataFetcher:
    """Fetches data from various sources with graceful error handling"""

    def __init__(self):
        self.results = {}
        self.errors = {}

    def fetch_stock_data(self, ticker: str, start_date: str, end_date: str) -> dict:
        """Fetch stock price data"""
        try:
            from tradingagents.dataflows.interface import route_to_vendor
            data = route_to_vendor('get_stock_data', symbol=ticker, start_date=start_date, end_date=end_date)
            if data is not None and len(data) > 0:
                self.results['stock_data'] = data
                return {'status': 'success', 'data': data}
            else:
                self.errors['stock_data'] = 'No data returned'
                return {'status': 'not_available', 'error': 'No data returned'}
        except Exception as e:
            self.errors['stock_data'] = str(e)
            return {'status': 'not_available', 'error': str(e)}

    def fetch_indicators(self, ticker: str, curr_date: str, look_back_days: int = 30) -> dict:
        """Fetch technical indicators"""
        try:
            from tradingagents.dataflows.interface import route_to_vendor
            indicators = ['close_50_sma', 'close_200_sma', 'macd', 'rsi', 'boll', 'atr']
            results = {}

            for indicator in indicators:
                try:
                    data = route_to_vendor('get_indicators',
                                          symbol=ticker,
                                          curr_date=curr_date,
                                          indicator=indicator,
                                          look_back_days=look_back_days)
                    if data:
                        results[indicator] = data
                except Exception as e:
                    results[indicator] = f"Error: {str(e)}"

            if results:
                self.results['indicators'] = results
                return {'status': 'success', 'data': results}
            else:
                self.errors['indicators'] = 'No indicators returned'
                return {'status': 'not_available', 'error': 'No indicators returned'}
        except Exception as e:
            self.errors['indicators'] = str(e)
            return {'status': 'not_available', 'error': str(e)}

    def fetch_news(self, ticker: str, start_date: str, end_date: str) -> dict:
        """Fetch news data"""
        try:
            from tradingagents.dataflows.interface import route_to_vendor
            news = route_to_vendor('get_news', ticker=ticker, start_date=start_date, end_date=end_date)
            if news:
                self.results['news'] = news
                return {'status': 'success', 'data': news}
            else:
                self.errors['news'] = 'No news returned'
                return {'status': 'not_available', 'error': 'No news returned'}
        except Exception as e:
            self.errors['news'] = str(e)
            return {'status': 'not_available', 'error': str(e)}

    def fetch_fundamentals(self, ticker: str, curr_date: str) -> dict:
        """Fetch fundamental data (balance sheet, income, cashflow)"""
        try:
            from tradingagents.dataflows.interface import route_to_vendor
            fundamentals = {}

            # Try each fundamental data type
            for data_type in ['get_balance_sheet', 'get_income_statement', 'get_cashflow']:
                try:
                    data = route_to_vendor(data_type, ticker=ticker, freq='quarterly', curr_date=curr_date)
                    if data:
                        fundamentals[data_type] = data
                except Exception as e:
                    fundamentals[data_type] = f"Error: {str(e)}"

            if fundamentals:
                self.results['fundamentals'] = fundamentals
                return {'status': 'success', 'data': fundamentals}
            else:
                self.errors['fundamentals'] = 'No fundamental data returned'
                return {'status': 'not_available', 'error': 'No fundamental data returned'}
        except Exception as e:
            self.errors['fundamentals'] = str(e)
            return {'status': 'not_available', 'error': str(e)}

    def fetch_insider_data(self, ticker: str, curr_date: str) -> dict:
        """Fetch insider transaction data"""
        try:
            from tradingagents.dataflows.interface import route_to_vendor
            data = route_to_vendor('get_insider_transactions', ticker=ticker, curr_date=curr_date)
            if data:
                self.results['insider'] = data
                return {'status': 'success', 'data': data}
            else:
                self.errors['insider'] = 'No insider data returned'
                return {'status': 'not_available', 'error': 'No insider data returned'}
        except Exception as e:
            self.errors['insider'] = str(e)
            return {'status': 'not_available', 'error': str(e)}

    def fetch_all_parallel(self, ticker: str, start_date: str, end_date: str) -> dict:
        """Fetch all data sources in parallel for faster execution"""
        data_results = {}

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.fetch_stock_data, ticker, start_date, end_date): 'stock_data',
                executor.submit(self.fetch_indicators, ticker, end_date): 'indicators',
                executor.submit(self.fetch_news, ticker, start_date, end_date): 'news',
                executor.submit(self.fetch_fundamentals, ticker, end_date): 'fundamentals',
                executor.submit(self.fetch_insider_data, ticker, end_date): 'insider',
            }

            for future in as_completed(futures):
                key = futures[future]
                try:
                    data_results[key] = future.result()
                except Exception as e:
                    data_results[key] = {'status': 'not_available', 'error': str(e)}

        return data_results


def quick_analyze_stock(ticker: str, end_date: str, lookback_days: int = 3) -> dict:
    """Quick analysis of a single stock - returns summary dict"""
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    fetcher = DataFetcher()
    data_results = fetcher.fetch_all_parallel(ticker, start_date, end_date)
    recommendation = generate_recommendation(fetcher, ticker)

    return {
        'ticker': ticker,
        'date': end_date,
        'action': recommendation['action'],
        'confidence': recommendation['confidence'],
        'bullish': recommendation.get('bullish_count', 0),
        'bearish': recommendation.get('bearish_count', 0),
        'reason': recommendation['reason'],
        'data_available': len(recommendation.get('data_sources', [])),
        'data_failed': len(recommendation.get('failed_sources', [])),
    }


def batch_analyze_stocks(tickers: list, end_date: str, progress_callback=None) -> list:
    """Analyze multiple stocks and return results"""
    results = []

    for i, ticker in enumerate(tickers):
        try:
            result = quick_analyze_stock(ticker, end_date)
            results.append(result)
        except Exception as e:
            results.append({
                'ticker': ticker,
                'date': end_date,
                'action': 'ERROR',
                'confidence': 0,
                'bullish': 0,
                'bearish': 0,
                'reason': str(e),
                'data_available': 0,
                'data_failed': 5,
            })

        if progress_callback:
            progress_callback((i + 1) / len(tickers))

    return results


def generate_recommendation(fetcher: DataFetcher, ticker: str) -> dict:
    """Generate a recommendation based on available data"""
    signals = []
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    confidence = 0

    # Analyze news sentiment if available
    if 'news' in fetcher.results:
        news_data = fetcher.results['news']
        try:
            if isinstance(news_data, str):
                news_data = json.loads(news_data)

            if isinstance(news_data, dict) and 'feed' in news_data:
                for article in news_data['feed']:
                    # Check ticker-specific sentiment
                    ticker_sentiments = article.get('ticker_sentiment', [])
                    for ts in ticker_sentiments:
                        if ts.get('ticker') == ticker:
                            score = float(ts.get('ticker_sentiment_score', 0))
                            if score > 0.15:
                                bullish_count += 1
                                signals.append(f"News: {article.get('title', 'Article')[:50]}... (Bullish)")
                            elif score < -0.15:
                                bearish_count += 1
                                signals.append(f"News: {article.get('title', 'Article')[:50]}... (Bearish)")
                            else:
                                neutral_count += 1
                            break
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # Analyze technical indicators if available
    if 'indicators' in fetcher.results:
        indicators = fetcher.results['indicators']

        # RSI analysis
        if 'rsi' in indicators and not str(indicators['rsi']).startswith('Error'):
            try:
                rsi_data = indicators['rsi']
                if isinstance(rsi_data, str) and 'rsi_14' in rsi_data.lower():
                    # Parse RSI value from string
                    import re
                    rsi_match = re.search(r'rsi[_\s]*14[:\s]*(\d+\.?\d*)', rsi_data.lower())
                    if rsi_match:
                        rsi_value = float(rsi_match.group(1))
                        if rsi_value < 30:
                            bullish_count += 2
                            signals.append(f"RSI ({rsi_value:.1f}): Oversold - Bullish signal")
                        elif rsi_value > 70:
                            bearish_count += 2
                            signals.append(f"RSI ({rsi_value:.1f}): Overbought - Bearish signal")
                        else:
                            neutral_count += 1
                            signals.append(f"RSI ({rsi_value:.1f}): Neutral")
            except:
                pass

        # Moving average analysis (50 vs 200 SMA)
        if 'close_50_sma' in indicators and 'close_200_sma' in indicators:
            try:
                sma50 = indicators['close_50_sma']
                sma200 = indicators['close_200_sma']
                if not str(sma50).startswith('Error') and not str(sma200).startswith('Error'):
                    signals.append("Moving Averages: Data available")
                    neutral_count += 1
            except:
                pass

    # Calculate recommendation
    total_signals = bullish_count + bearish_count + neutral_count

    if total_signals == 0:
        return {
            'action': 'HOLD',
            'confidence': 0,
            'reason': 'Insufficient data to make a recommendation',
            'signals': ['No data sources available for analysis'],
            'data_sources': list(fetcher.results.keys()),
            'failed_sources': list(fetcher.errors.keys())
        }

    confidence = abs(bullish_count - bearish_count) / total_signals * 100

    if bullish_count > bearish_count + 1:
        action = 'BUY'
        reason = f"Bullish signals ({bullish_count}) outweigh bearish ({bearish_count})"
    elif bearish_count > bullish_count + 1:
        action = 'SELL'
        reason = f"Bearish signals ({bearish_count}) outweigh bullish ({bullish_count})"
    else:
        action = 'HOLD'
        reason = f"Mixed signals - Bullish: {bullish_count}, Bearish: {bearish_count}, Neutral: {neutral_count}"

    return {
        'action': action,
        'confidence': min(confidence, 100),
        'reason': reason,
        'signals': signals if signals else ['Analysis based on available data'],
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
        'neutral_count': neutral_count,
        'data_sources': list(fetcher.results.keys()),
        'failed_sources': list(fetcher.errors.keys())
    }


def display_data_section(title: str, data: dict, icon: str = "📊"):
    """Display a data section with Not Available handling"""
    with st.expander(f"{icon} {title}", expanded=False):
        if data['status'] == 'success':
            content = data['data']
            if isinstance(content, dict):
                st.json(content)
            elif isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    st.json(parsed)
                except:
                    st.markdown(content)
            else:
                st.write(content)
        else:
            st.warning(f"**Not Available**")
            st.caption(f"Reason: {data.get('error', 'Unknown error')}")


def show():
    """Display enhanced stock analysis page"""
    st.markdown("<h1 class='main-header'>🔍 Stock Analysis</h1>", unsafe_allow_html=True)

    # Analysis Type Selector
    analysis_type = st.radio(
        "Analysis Type",
        ["📊 Single Stock", "📋 Batch Analysis (Multiple Stocks)"],
        horizontal=True
    )

    st.markdown("---")

    # Date configuration (shared)
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        analysis_date = st.date_input(
            "Analysis Date",
            value=datetime.now().date() - timedelta(days=1),
            max_value=datetime.now().date(),
            help="Date for analysis (use recent past date for best results)"
        )
    with col_date2:
        lookback_days = st.slider("Lookback Days", 1, 14, 3)

    end_date = analysis_date.strftime("%Y-%m-%d")
    start_date = (analysis_date - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    st.markdown("---")

    # ===== BATCH ANALYSIS MODE =====
    if analysis_type == "📋 Batch Analysis (Multiple Stocks)":
        st.markdown("## 📋 Batch Stock Analysis")
        st.markdown("Analyze multiple stocks at once and see a summary table")

        # Stock input methods
        input_method = st.radio(
            "Stock Selection",
            ["Use Default Watchlist", "Enter Custom List"],
            horizontal=True
        )

        if input_method == "Use Default Watchlist":
            selected_stocks = st.multiselect(
                "Select Stocks",
                DEFAULT_WATCHLIST,
                default=DEFAULT_WATCHLIST[:5]
            )
        else:
            custom_input = st.text_input(
                "Enter tickers (comma-separated)",
                value="NVDA, AAPL, MSFT, GOOGL, AMZN",
                help="Enter stock tickers separated by commas"
            )
            selected_stocks = [t.strip().upper() for t in custom_input.split(",") if t.strip()]

        st.markdown(f"**{len(selected_stocks)} stocks selected**")

        if st.button("🚀 Run Batch Analysis", type="primary", use_container_width=True):
            if not selected_stocks:
                st.error("Please select at least one stock")
                return

            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            results = []
            for i, ticker in enumerate(selected_stocks):
                status_text.text(f"Analyzing {ticker}... ({i+1}/{len(selected_stocks)})")
                try:
                    result = quick_analyze_stock(ticker, end_date, lookback_days)
                    results.append(result)
                except Exception as e:
                    results.append({
                        'ticker': ticker,
                        'action': 'ERROR',
                        'confidence': 0,
                        'bullish': 0,
                        'bearish': 0,
                        'reason': str(e)[:50],
                        'data_available': 0,
                        'data_failed': 5,
                    })
                progress_bar.progress((i + 1) / len(selected_stocks))

            status_text.text("Analysis complete!")

            # Display Results Table
            st.markdown("---")
            st.markdown("## 📊 Analysis Results")

            # Create summary dataframe
            df = pd.DataFrame(results)

            # Color coding function
            def color_action(val):
                if val == 'BUY':
                    return 'background-color: #d4edda; color: #155724'
                elif val == 'SELL':
                    return 'background-color: #f8d7da; color: #721c24'
                elif val == 'HOLD':
                    return 'background-color: #fff3cd; color: #856404'
                else:
                    return 'background-color: #e9ecef; color: #6c757d'

            # Display styled dataframe
            styled_df = df[['ticker', 'action', 'confidence', 'bullish', 'bearish', 'reason']].copy()
            styled_df.columns = ['Ticker', 'Action', 'Confidence %', 'Bullish', 'Bearish', 'Reason']

            st.dataframe(
                styled_df.style.applymap(color_action, subset=['Action']),
                use_container_width=True,
                hide_index=True
            )

            # Summary stats
            st.markdown("### 📈 Summary")
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

            buy_count = len([r for r in results if r['action'] == 'BUY'])
            sell_count = len([r for r in results if r['action'] == 'SELL'])
            hold_count = len([r for r in results if r['action'] == 'HOLD'])

            with summary_col1:
                st.metric("🟢 BUY", buy_count)
            with summary_col2:
                st.metric("🔴 SELL", sell_count)
            with summary_col3:
                st.metric("🟡 HOLD", hold_count)
            with summary_col4:
                avg_conf = sum(r['confidence'] for r in results) / len(results) if results else 0
                st.metric("Avg Confidence", f"{avg_conf:.0f}%")

            # Top picks
            buy_stocks = [r for r in results if r['action'] == 'BUY']
            if buy_stocks:
                buy_stocks.sort(key=lambda x: x['confidence'], reverse=True)
                st.markdown("### 🏆 Top BUY Picks")
                for stock in buy_stocks[:3]:
                    st.markdown(f"- **{stock['ticker']}** - Confidence: {stock['confidence']:.0f}%")

        return  # End batch analysis mode

    # ===== SINGLE STOCK ANALYSIS MODE =====
    st.markdown("## 📊 Single Stock Analysis")

    col1, col2 = st.columns(2)

    with col1:
        ticker = st.text_input(
            "Ticker Symbol",
            value="NVDA",
            help="Enter stock ticker (e.g., NVDA, AAPL, TSLA)"
        ).upper()

    with col2:
        analysis_mode = st.radio(
            "Analysis Mode",
            ["Quick (Parallel)", "Full Agent (LLM)"],
            help="Quick mode is faster with parallel data fetching"
        )

    # ===== TRADINGVIEW SECTION =====
    if ticker:
        st.markdown("---")
        st.markdown("## 📈 TradingView Analysis")

        # Create tabs for Chart and Technical Analysis
        tv_tab1, tv_tab2 = st.tabs(["📊 Live Chart", "🎯 Technical Ratings"])

        with tv_tab1:
            st.caption(f"Interactive TradingView chart for {ticker}")
            render_tradingview_chart(ticker, exchange="NASDAQ", height=500)

        with tv_tab2:
            # Get TradingView ratings
            with st.spinner("Fetching TradingView analysis..."):
                tv_analysis = get_tradingview_analysis(ticker)

            if tv_analysis['status'] == 'success':
                # Main recommendation display
                rec = tv_analysis['recommendation']
                rec_colors = {
                    'STRONG_BUY': ('#28a745', '#d4edda', '🟢'),
                    'BUY': ('#28a745', '#d4edda', '🟢'),
                    'NEUTRAL': ('#ffc107', '#fff3cd', '🟡'),
                    'SELL': ('#dc3545', '#f8d7da', '🔴'),
                    'STRONG_SELL': ('#dc3545', '#f8d7da', '🔴'),
                }
                color, bg_color, emoji = rec_colors.get(rec, ('#6c757d', '#e9ecef', '⚪'))

                st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border-left: 5px solid {color}; margin-bottom: 20px;">
                    <h2 style="color: {color}; margin: 0;">{emoji} TradingView: {rec.replace('_', ' ')}</h2>
                    <p style="color: #333; margin-top: 10px;">Exchange: {tv_analysis['exchange']} | Based on {tv_analysis['buy'] + tv_analysis['sell'] + tv_analysis['neutral']} indicators</p>
                </div>
                """, unsafe_allow_html=True)

                # Signal breakdown
                signal_col1, signal_col2, signal_col3 = st.columns(3)
                with signal_col1:
                    st.metric("🟢 Buy Signals", tv_analysis['buy'])
                with signal_col2:
                    st.metric("🟡 Neutral", tv_analysis['neutral'])
                with signal_col3:
                    st.metric("🔴 Sell Signals", tv_analysis['sell'])

                # Oscillators vs Moving Averages
                st.markdown("### Signal Breakdown")
                osc_col, ma_col = st.columns(2)

                with osc_col:
                    st.markdown("**Oscillators**")
                    osc = tv_analysis['oscillators']
                    st.markdown(f"- Recommendation: **{osc['recommendation'].replace('_', ' ')}**")
                    st.markdown(f"- Buy: {osc['buy']} | Neutral: {osc['neutral']} | Sell: {osc['sell']}")

                with ma_col:
                    st.markdown("**Moving Averages**")
                    ma = tv_analysis['moving_averages']
                    st.markdown(f"- Recommendation: **{ma['recommendation'].replace('_', ' ')}**")
                    st.markdown(f"- Buy: {ma['buy']} | Neutral: {ma['neutral']} | Sell: {ma['sell']}")

                # Key indicators
                with st.expander("📊 Key Indicator Values", expanded=False):
                    ind = tv_analysis['indicators']
                    ind_col1, ind_col2, ind_col3 = st.columns(3)

                    with ind_col1:
                        st.markdown("**Price**")
                        if ind.get('close'):
                            st.metric("Close", f"${ind['close']:.2f}")
                        if ind.get('high'):
                            st.metric("High", f"${ind['high']:.2f}")
                        if ind.get('low'):
                            st.metric("Low", f"${ind['low']:.2f}")

                    with ind_col2:
                        st.markdown("**Momentum**")
                        if ind.get('rsi'):
                            rsi_status = "Oversold" if ind['rsi'] < 30 else "Overbought" if ind['rsi'] > 70 else "Neutral"
                            st.metric("RSI", f"{ind['rsi']:.1f}", rsi_status)
                        if ind.get('macd'):
                            st.metric("MACD", f"{ind['macd']:.4f}")
                        if ind.get('adx'):
                            st.metric("ADX", f"{ind['adx']:.1f}")

                    with ind_col3:
                        st.markdown("**Moving Averages**")
                        if ind.get('sma20'):
                            st.metric("SMA 20", f"${ind['sma20']:.2f}")
                        if ind.get('sma50'):
                            st.metric("SMA 50", f"${ind['sma50']:.2f}")
                        if ind.get('sma200'):
                            st.metric("SMA 200", f"${ind['sma200']:.2f}")

                # Also render the visual widget
                st.markdown("### TradingView Technical Analysis Widget")
                render_tradingview_technical_analysis(ticker, exchange=tv_analysis['exchange'], height=400)

            else:
                st.warning(f"Could not fetch TradingView analysis: {tv_analysis.get('error', 'Unknown error')}")
                st.info("Showing chart only...")
                render_tradingview_technical_analysis(ticker, exchange="NASDAQ", height=400)

        st.markdown("---")

    # Run Analysis Button
    if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
        if not ticker:
            st.error("Please enter a ticker symbol")
            return

        fetcher = DataFetcher()

        # Progress tracking
        st.markdown("### 🔄 Fetching Data...")
        progress_bar = st.progress(0)
        status_container = st.empty()

        # Use parallel fetching for speed
        status_container.text("Fetching all data sources in parallel...")
        progress_bar.progress(20)

        data_results = fetcher.fetch_all_parallel(ticker, start_date, end_date)

        progress_bar.progress(100)
        status_container.text("✅ Data collection complete!")

        # Summary of data availability
        st.markdown("---")
        st.markdown("## 📊 Data Availability")

        col1, col2, col3, col4, col5 = st.columns(5)

        status_icons = {
            'success': '✅',
            'not_available': '❌'
        }

        with col1:
            icon = status_icons.get(data_results['stock_data']['status'], '❓')
            st.metric("Stock Data", icon)

        with col2:
            icon = status_icons.get(data_results['indicators']['status'], '❓')
            st.metric("Indicators", icon)

        with col3:
            icon = status_icons.get(data_results['news']['status'], '❓')
            st.metric("News", icon)

        with col4:
            icon = status_icons.get(data_results['fundamentals']['status'], '❓')
            st.metric("Fundamentals", icon)

        with col5:
            icon = status_icons.get(data_results['insider']['status'], '❓')
            st.metric("Insider Data", icon)

        # Generate rule-based recommendation
        recommendation = generate_recommendation(fetcher, ticker)

        # ===== RECOMMENDATION 1: ANALYST (Rule-Based) =====
        st.markdown("---")
        st.markdown("## 🔬 Analyst Recommendation (Rule-Based)")
        st.caption("Fast analysis based on technical indicators and news sentiment")

        # Main recommendation card with colors
        decision_colors = {
            'BUY': ('#28a745', '#d4edda', '🟢'),
            'SELL': ('#dc3545', '#f8d7da', '🔴'),
            'HOLD': ('#ffc107', '#fff3cd', '🟡')
        }
        color, bg_color, emoji = decision_colors.get(recommendation['action'], ('#6c757d', '#e9ecef', '⚪'))

        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border-left: 5px solid {color}; margin-bottom: 20px;">
            <h2 style="color: {color}; margin: 0;">{emoji} {recommendation['action']}</h2>
            <p style="color: #333; font-size: 1em; margin-top: 10px;">Confidence: {recommendation['confidence']:.0f}%</p>
        </div>
        """, unsafe_allow_html=True)

        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Action", recommendation['action'])
        with col2:
            st.metric("Confidence", f"{recommendation['confidence']:.0f}%")
        with col3:
            time_horizon = "Short Term" if recommendation.get('bullish_count', 0) > 2 else "Medium Term"
            st.metric("Time Horizon", time_horizon)
        with col4:
            risk = "High" if len(recommendation.get('failed_sources', [])) > 2 else "Medium"
            st.metric("Risk Level", risk)

        # Signal Summary
        with st.expander("📈 Signal Details", expanded=True):
            st.markdown(f"**Reason:** {recommendation['reason']}")

            signal_col1, signal_col2, signal_col3 = st.columns(3)
            with signal_col1:
                st.metric("Bullish Signals", recommendation.get('bullish_count', 0))
            with signal_col2:
                st.metric("Bearish Signals", recommendation.get('bearish_count', 0))
            with signal_col3:
                st.metric("Neutral Signals", recommendation.get('neutral_count', 0))

            if recommendation.get('signals'):
                st.markdown("**Key Signals:**")
                for signal in recommendation['signals'][:5]:
                    st.markdown(f"- {signal}")

        # ===== RECOMMENDATION 2: AI AGENT (LLM-Based) =====
        st.markdown("---")
        st.markdown("## 🤖 AI Agent Recommendation (LLM)")
        st.caption("Deep analysis using multi-agent AI system with debate and risk assessment")

        # Store data in session for LLM analysis
        st.session_state['current_ticker'] = ticker
        st.session_state['current_date'] = end_date
        st.session_state['analyst_recommendation'] = recommendation

        if st.button("🚀 Get AI Agent Recommendation", type="primary", use_container_width=True):
            try:
                from tradingagents.graph.trading_graph import TradingAgentsGraph

                config_manager = ConfigManager(db)
                config = config_manager.get_config_dict()

                # Progress display
                ai_progress = st.empty()
                ai_status = st.empty()

                ai_status.info("🔄 Initializing AI agents...")

                graph = TradingAgentsGraph(
                    selected_analysts=["market", "news", "fundamentals"],
                    debug=True,
                    config=config
                )

                # Stream execution with progress
                init_agent_state = graph.propagator.create_initial_state(ticker, end_date)
                args = graph.propagator.get_graph_args()

                trace = []
                seen_agents = set()
                progress_text = ""

                for chunk in graph.graph.stream(init_agent_state, **args):
                    messages = chunk.get("messages", [])
                    if messages and len(messages) > 0:
                        msg = messages[-1]
                        trace.append(chunk)

                        agent_name = getattr(msg, 'name', None) or type(msg).__name__
                        if agent_name and agent_name not in seen_agents and agent_name != 'HumanMessage':
                            seen_agents.add(agent_name)
                            progress_text += f"✅ {agent_name}\n"
                            ai_progress.markdown(progress_text + "⏳ Processing...")

                ai_progress.markdown(progress_text + "✅ **Complete!**")
                ai_status.empty()

                # Get final state
                if trace:
                    final_state = trace[-1]
                    ai_decision = graph.process_signal(final_state.get("final_trade_decision", "HOLD"))
                    ai_action = ai_decision.upper() if 'BUY' in ai_decision.upper() else ('SELL' if 'SELL' in ai_decision.upper() else 'HOLD')

                    # Display AI recommendation
                    ai_color, ai_bg, ai_emoji = decision_colors.get(ai_action, ('#6c757d', '#e9ecef', '⚪'))

                    st.markdown(f"""
                    <div style="background-color: {ai_bg}; padding: 20px; border-radius: 10px; border-left: 5px solid {ai_color}; margin: 20px 0;">
                        <h2 style="color: {ai_color}; margin: 0;">{ai_emoji} AI Recommendation: {ai_action}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    # AI Analysis Summary
                    st.markdown("### 🎯 AI Decision Summary")
                    if final_state.get('final_trade_decision'):
                        st.markdown(final_state['final_trade_decision'])

                    # Detailed AI reports
                    with st.expander("📋 Full AI Analysis Reports", expanded=False):
                        if final_state.get('market_report'):
                            st.markdown("#### Market Analysis")
                            st.markdown(final_state['market_report'])
                        if final_state.get('news_report'):
                            st.markdown("#### News Analysis")
                            st.markdown(final_state['news_report'])
                        if final_state.get('fundamentals_report'):
                            st.markdown("#### Fundamentals Analysis")
                            st.markdown(final_state['fundamentals_report'])
                        if final_state.get('investment_plan'):
                            st.markdown("#### Investment Plan")
                            st.markdown(final_state['investment_plan'])

                    # Compare recommendations
                    st.markdown("---")
                    st.markdown("### 📊 Recommendation Comparison")

                    compare_col1, compare_col2 = st.columns(2)
                    with compare_col1:
                        st.markdown(f"""
                        <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; text-align: center;">
                            <h4>🔬 Analyst</h4>
                            <h2 style="color: {color};">{emoji} {recommendation['action']}</h2>
                            <p>Confidence: {recommendation['confidence']:.0f}%</p>
                        </div>
                        """, unsafe_allow_html=True)

                    with compare_col2:
                        st.markdown(f"""
                        <div style="background-color: {ai_bg}; padding: 15px; border-radius: 8px; text-align: center;">
                            <h4>🤖 AI Agent</h4>
                            <h2 style="color: {ai_color};">{ai_emoji} {ai_action}</h2>
                            <p>Deep Analysis</p>
                        </div>
                        """, unsafe_allow_html=True)

                    # Agreement indicator
                    if recommendation['action'] == ai_action:
                        st.success("✅ **Both analysts AGREE** on the recommendation!")
                    else:
                        st.warning(f"⚠️ **Analysts DISAGREE** - Analyst: {recommendation['action']}, AI: {ai_action}")

            except Exception as e:
                st.error(f"AI analysis failed: {str(e)}")
                st.info("Make sure Ollama is running or configure API keys in Settings.")

        else:
            st.info("👆 Click above to get AI-powered recommendation (takes 1-2 minutes)")

        # Data availability (collapsed)
        with st.expander("📋 Data Sources", expanded=False):
            source_col1, source_col2 = st.columns(2)
            with source_col1:
                st.markdown("**Available:**")
                for source in recommendation.get('data_sources', []):
                    st.markdown(f"✅ {source}")
            with source_col2:
                if recommendation.get('failed_sources'):
                    st.markdown("**Not Available:**")
                    for source in recommendation['failed_sources']:
                        st.markdown(f"❌ {source}")

        # Raw data (collapsed)
        with st.expander("📋 View Raw Data", expanded=False):
            display_data_section("Stock Price Data", data_results['stock_data'], "📈")
            display_data_section("Technical Indicators", data_results['indicators'], "📊")
            display_data_section("News & Sentiment", data_results['news'], "📰")
            display_data_section("Fundamental Data", data_results['fundamentals'], "💰")
            display_data_section("Insider Transactions", data_results['insider'], "👤")

        # Save analysis
        st.markdown("---")
        st.markdown("## 💾 Save Analysis")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save to Database", use_container_width=True):
                analysis_data = {
                    'ticker': ticker,
                    'analysis_date': end_date,
                    'decision': recommendation['action'],
                    'market_report': json.dumps(data_results.get('stock_data', {})),
                    'news_report': json.dumps(data_results.get('news', {})),
                    'fundamentals_report': json.dumps(data_results.get('fundamentals', {})),
                    'final_decision': f"{recommendation['action']} - {recommendation['reason']}",
                    'status': 'pending'
                }

                try:
                    analysis_id = db.save_analysis(analysis_data)
                    st.success(f"Analysis saved! ID: {analysis_id}")
                except Exception as e:
                    st.error(f"Failed to save: {str(e)}")

        with col2:
            if st.button("📋 Add to Watchlist", use_container_width=True):
                try:
                    db.add_to_watchlist(ticker, f"Analysis on {end_date}: {recommendation['action']}")
                    st.success(f"Added {ticker} to watchlist!")
                except Exception as e:
                    st.error(f"Failed to add to watchlist: {str(e)}")
