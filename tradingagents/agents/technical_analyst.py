"""
Technical Analyst Agent - TradingView-based Chart Analysis
Analyzes price action, patterns, and technical indicators using TradingView methodology
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np


class TechnicalAnalyst:
    """
    Technical analyst using TradingView-style indicators and pattern recognition

    Analyzes:
    - Trend direction (Moving Averages)
    - Momentum (RSI, MACD, Stochastic)
    - Volume analysis
    - Support/Resistance levels
    - Chart patterns
    - TradingView ratings aggregation
    """

    def __init__(self, llm, config: Optional[Dict[str, Any]] = None):
        self.llm = llm
        self.config = config or {}
        self.name = "Technical Analyst"

    def analyze(self, ticker: str, analysis_date: str) -> str:
        """
        Perform comprehensive technical analysis using TradingView methodology

        Args:
            ticker: Stock ticker symbol
            analysis_date: Date for analysis (YYYY-MM-DD)

        Returns:
            Formatted technical analysis report with TradingView-style ratings
        """
        try:
            # Fetch price data
            price_data = self._fetch_price_data(ticker, analysis_date)

            if price_data is None or price_data.empty:
                return self._generate_error_report(ticker, "Unable to fetch price data")

            # Calculate technical indicators
            indicators = self._calculate_indicators(price_data)

            # Analyze patterns
            patterns = self._identify_patterns(price_data)

            # Calculate support/resistance
            support_resistance = self._calculate_support_resistance(price_data)

            # Get TradingView-style ratings
            ratings = self._calculate_tradingview_ratings(indicators)

            # Generate AI analysis
            report = self._generate_report(
                ticker=ticker,
                analysis_date=analysis_date,
                price_data=price_data,
                indicators=indicators,
                patterns=patterns,
                support_resistance=support_resistance,
                ratings=ratings
            )

            return report

        except Exception as e:
            return self._generate_error_report(ticker, str(e))

    def _fetch_price_data(self, ticker: str, analysis_date: str, days: int = 200) -> pd.DataFrame:
        """Fetch historical price data"""
        try:
            end_date = datetime.strptime(analysis_date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=days)

            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date + timedelta(days=1))

            return df

        except Exception as e:
            print(f"Error fetching price data: {e}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate TradingView-style technical indicators"""

        indicators = {}

        # Moving Averages
        indicators['ma10'] = df['Close'].rolling(window=10).mean().iloc[-1]
        indicators['ma20'] = df['Close'].rolling(window=20).mean().iloc[-1]
        indicators['ma50'] = df['Close'].rolling(window=50).mean().iloc[-1]
        indicators['ma100'] = df['Close'].rolling(window=100).mean().iloc[-1]
        indicators['ma200'] = df['Close'].rolling(window=200).mean().iloc[-1]

        # Exponential Moving Averages
        indicators['ema10'] = df['Close'].ewm(span=10, adjust=False).mean().iloc[-1]
        indicators['ema20'] = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
        indicators['ema50'] = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]

        # RSI (14-period)
        indicators['rsi'] = self._calculate_rsi(df['Close'], 14)

        # MACD
        macd_data = self._calculate_macd(df['Close'])
        indicators['macd'] = macd_data['macd']
        indicators['macd_signal'] = macd_data['signal']
        indicators['macd_histogram'] = macd_data['histogram']

        # Stochastic Oscillator
        stoch_data = self._calculate_stochastic(df, 14)
        indicators['stoch_k'] = stoch_data['k']
        indicators['stoch_d'] = stoch_data['d']

        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(df['Close'], 20, 2)
        indicators['bb_upper'] = bb_data['upper']
        indicators['bb_middle'] = bb_data['middle']
        indicators['bb_lower'] = bb_data['lower']

        # ATR (Average True Range)
        indicators['atr'] = self._calculate_atr(df, 14)

        # Volume indicators
        indicators['volume_sma'] = df['Volume'].rolling(window=20).mean().iloc[-1]
        indicators['current_volume'] = df['Volume'].iloc[-1]

        # Current price info
        indicators['current_price'] = df['Close'].iloc[-1]
        indicators['prev_close'] = df['Close'].iloc[-2]
        indicators['high_52w'] = df['High'].tail(252).max()
        indicators['low_52w'] = df['Low'].tail(252).min()

        return indicators

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]

    def _calculate_macd(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate MACD indicator"""
        ema12 = prices.ewm(span=12, adjust=False).mean()
        ema26 = prices.ewm(span=26, adjust=False).mean()

        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal

        return {
            'macd': macd.iloc[-1],
            'signal': signal.iloc[-1],
            'histogram': histogram.iloc[-1]
        }

    def _calculate_stochastic(self, df: pd.DataFrame, period: int = 14) -> Dict[str, float]:
        """Calculate Stochastic Oscillator"""
        low_min = df['Low'].rolling(window=period).min()
        high_max = df['High'].rolling(window=period).max()

        k = 100 * ((df['Close'] - low_min) / (high_max - low_min))
        d = k.rolling(window=3).mean()

        return {
            'k': k.iloc[-1],
            'd': d.iloc[-1]
        }

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return {
            'upper': upper.iloc[-1],
            'middle': middle.iloc[-1],
            'lower': lower.iloc[-1]
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high = df['High']
        low = df['Low']
        close = df['Close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr.iloc[-1]

    def _identify_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify chart patterns"""
        patterns = {
            'trend': self._identify_trend(df),
            'candlestick_patterns': self._identify_candlestick_patterns(df),
            'price_action': self._analyze_price_action(df)
        }

        return patterns

    def _identify_trend(self, df: pd.DataFrame) -> str:
        """Identify overall trend direction"""
        ma20 = df['Close'].rolling(window=20).mean()
        ma50 = df['Close'].rolling(window=50).mean()

        current_price = df['Close'].iloc[-1]
        ma20_current = ma20.iloc[-1]
        ma50_current = ma50.iloc[-1]

        # Strong uptrend
        if current_price > ma20_current > ma50_current and ma20.iloc[-1] > ma20.iloc[-10]:
            return "Strong Uptrend"
        # Uptrend
        elif current_price > ma20_current:
            return "Uptrend"
        # Strong downtrend
        elif current_price < ma20_current < ma50_current and ma20.iloc[-1] < ma20.iloc[-10]:
            return "Strong Downtrend"
        # Downtrend
        elif current_price < ma20_current:
            return "Downtrend"
        else:
            return "Sideways/Consolidation"

    def _identify_candlestick_patterns(self, df: pd.DataFrame) -> list:
        """Identify recent candlestick patterns"""
        patterns = []

        # Get last few candles
        last_5 = df.tail(5)

        # Doji
        if self._is_doji(last_5.iloc[-1]):
            patterns.append("Doji (Indecision)")

        # Hammer/Shooting Star
        if self._is_hammer(last_5.iloc[-1]):
            patterns.append("Hammer (Bullish Reversal)")

        if self._is_shooting_star(last_5.iloc[-1]):
            patterns.append("Shooting Star (Bearish Reversal)")

        # Engulfing patterns
        if len(last_5) >= 2:
            if self._is_bullish_engulfing(last_5.iloc[-2], last_5.iloc[-1]):
                patterns.append("Bullish Engulfing (Strong Buy Signal)")

            if self._is_bearish_engulfing(last_5.iloc[-2], last_5.iloc[-1]):
                patterns.append("Bearish Engulfing (Strong Sell Signal)")

        return patterns if patterns else ["No significant patterns detected"]

    def _is_doji(self, candle: pd.Series) -> bool:
        """Check if candle is a Doji"""
        body = abs(candle['Close'] - candle['Open'])
        range_ = candle['High'] - candle['Low']
        return body / range_ < 0.1 if range_ > 0 else False

    def _is_hammer(self, candle: pd.Series) -> bool:
        """Check if candle is a Hammer"""
        body = abs(candle['Close'] - candle['Open'])
        lower_shadow = min(candle['Open'], candle['Close']) - candle['Low']
        upper_shadow = candle['High'] - max(candle['Open'], candle['Close'])

        return lower_shadow > 2 * body and upper_shadow < body

    def _is_shooting_star(self, candle: pd.Series) -> bool:
        """Check if candle is a Shooting Star"""
        body = abs(candle['Close'] - candle['Open'])
        upper_shadow = candle['High'] - max(candle['Open'], candle['Close'])
        lower_shadow = min(candle['Open'], candle['Close']) - candle['Low']

        return upper_shadow > 2 * body and lower_shadow < body

    def _is_bullish_engulfing(self, prev: pd.Series, curr: pd.Series) -> bool:
        """Check for Bullish Engulfing pattern"""
        return (prev['Close'] < prev['Open'] and  # Previous was bearish
                curr['Close'] > curr['Open'] and    # Current is bullish
                curr['Close'] > prev['Open'] and    # Current close > previous open
                curr['Open'] < prev['Close'])        # Current open < previous close

    def _is_bearish_engulfing(self, prev: pd.Series, curr: pd.Series) -> bool:
        """Check for Bearish Engulfing pattern"""
        return (prev['Close'] > prev['Open'] and  # Previous was bullish
                curr['Close'] < curr['Open'] and    # Current is bearish
                curr['Close'] < prev['Open'] and    # Current close < previous open
                curr['Open'] > prev['Close'])        # Current open > previous close

    def _analyze_price_action(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze recent price action"""
        last_10 = df.tail(10)

        # Higher highs / Lower lows
        highs_increasing = last_10['High'].is_monotonic_increasing
        lows_decreasing = last_10['Low'].is_monotonic_decreasing

        # Breakout analysis
        current_price = df['Close'].iloc[-1]
        high_20 = df['High'].tail(20).max()
        low_20 = df['Low'].tail(20).min()

        breakout = None
        if current_price >= high_20 * 0.98:
            breakout = "Approaching 20-day high (potential breakout)"
        elif current_price <= low_20 * 1.02:
            breakout = "Approaching 20-day low (potential breakdown)"

        return {
            'higher_highs': highs_increasing,
            'lower_lows': lows_decreasing,
            'breakout_signal': breakout,
            'volatility': df['Close'].tail(20).std() / df['Close'].tail(20).mean() * 100
        }

    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate support and resistance levels"""
        current_price = df['Close'].iloc[-1]

        # Recent highs/lows
        high_20 = df['High'].tail(20).max()
        low_20 = df['Low'].tail(20).min()
        high_50 = df['High'].tail(50).max()
        low_50 = df['Low'].tail(50).min()

        # Pivot points (standard)
        last_candle = df.iloc[-1]
        pivot = (last_candle['High'] + last_candle['Low'] + last_candle['Close']) / 3

        r1 = 2 * pivot - last_candle['Low']
        r2 = pivot + (last_candle['High'] - last_candle['Low'])
        s1 = 2 * pivot - last_candle['High']
        s2 = pivot - (last_candle['High'] - last_candle['Low'])

        return {
            'current_price': current_price,
            'resistance_1': r1,
            'resistance_2': r2,
            'resistance_20d': high_20,
            'resistance_50d': high_50,
            'support_1': s1,
            'support_2': s2,
            'support_20d': low_20,
            'support_50d': low_50,
            'pivot': pivot
        }

    def _calculate_tradingview_ratings(self, indicators: Dict[str, Any]) -> Dict[str, str]:
        """Calculate TradingView-style aggregate ratings"""

        buy_signals = 0
        sell_signals = 0
        neutral_signals = 0

        # Moving Averages
        price = indicators['current_price']

        # MA signals
        ma_signals = [
            indicators['ma10'], indicators['ma20'], indicators['ma50'],
            indicators['ma100'], indicators['ma200'],
            indicators['ema10'], indicators['ema20'], indicators['ema50']
        ]

        for ma in ma_signals:
            if price > ma:
                buy_signals += 1
            elif price < ma:
                sell_signals += 1
            else:
                neutral_signals += 1

        # RSI signals
        rsi = indicators['rsi']
        if rsi < 30:
            buy_signals += 1  # Oversold
        elif rsi > 70:
            sell_signals += 1  # Overbought
        else:
            neutral_signals += 1

        # MACD signals
        if indicators['macd'] > indicators['macd_signal']:
            buy_signals += 1
        else:
            sell_signals += 1

        # Stochastic signals
        if indicators['stoch_k'] < 20:
            buy_signals += 1  # Oversold
        elif indicators['stoch_k'] > 80:
            sell_signals += 1  # Overbought
        else:
            neutral_signals += 1

        # Bollinger Bands
        if price < indicators['bb_lower']:
            buy_signals += 1  # Oversold
        elif price > indicators['bb_upper']:
            sell_signals += 1  # Overbought
        else:
            neutral_signals += 1

        # Calculate overall rating
        total_signals = buy_signals + sell_signals + neutral_signals
        buy_pct = (buy_signals / total_signals) * 100
        sell_pct = (sell_signals / total_signals) * 100

        if buy_pct > 60:
            overall = "Strong Buy"
        elif buy_pct > 50:
            overall = "Buy"
        elif sell_pct > 60:
            overall = "Strong Sell"
        elif sell_pct > 50:
            overall = "Sell"
        else:
            overall = "Neutral"

        return {
            'overall': overall,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'neutral_signals': neutral_signals,
            'buy_percentage': round(buy_pct, 1),
            'sell_percentage': round(sell_pct, 1)
        }

    def _generate_report(
        self,
        ticker: str,
        analysis_date: str,
        price_data: pd.DataFrame,
        indicators: Dict[str, Any],
        patterns: Dict[str, Any],
        support_resistance: Dict[str, Any],
        ratings: Dict[str, str]
    ) -> str:
        """Generate comprehensive technical analysis report using LLM"""

        # Prepare technical summary for LLM
        technical_summary = f"""
# Technical Analysis Data for {ticker} (as of {analysis_date})

## Price Information
- Current Price: ${indicators['current_price']:.2f}
- Previous Close: ${indicators['prev_close']:.2f}
- Change: {((indicators['current_price'] - indicators['prev_close']) / indicators['prev_close'] * 100):.2f}%
- 52-Week High: ${indicators['high_52w']:.2f}
- 52-Week Low: ${indicators['low_52w']:.2f}

## TradingView-Style Rating
- Overall Rating: **{ratings['overall']}**
- Buy Signals: {ratings['buy_signals']} ({ratings['buy_percentage']}%)
- Sell Signals: {ratings['sell_signals']} ({ratings['sell_percentage']}%)
- Neutral Signals: {ratings['neutral_signals']}

## Trend Analysis
- Current Trend: {patterns['trend']}

## Moving Averages
- MA10: ${indicators['ma10']:.2f} - Price is {'ABOVE' if indicators['current_price'] > indicators['ma10'] else 'BELOW'}
- MA20: ${indicators['ma20']:.2f} - Price is {'ABOVE' if indicators['current_price'] > indicators['ma20'] else 'BELOW'}
- MA50: ${indicators['ma50']:.2f} - Price is {'ABOVE' if indicators['current_price'] > indicators['ma50'] else 'BELOW'}
- MA200: ${indicators['ma200']:.2f} - Price is {'ABOVE' if indicators['current_price'] > indicators['ma200'] else 'BELOW'}

## Momentum Indicators
- RSI (14): {indicators['rsi']:.2f} - {'Oversold' if indicators['rsi'] < 30 else 'Overbought' if indicators['rsi'] > 70 else 'Neutral'}
- MACD: {indicators['macd']:.4f}
- MACD Signal: {indicators['macd_signal']:.4f}
- MACD Histogram: {indicators['macd_histogram']:.4f} - {'Bullish' if indicators['macd_histogram'] > 0 else 'Bearish'}
- Stochastic %K: {indicators['stoch_k']:.2f}
- Stochastic %D: {indicators['stoch_d']:.2f}

## Bollinger Bands
- Upper Band: ${indicators['bb_upper']:.2f}
- Middle Band: ${indicators['bb_middle']:.2f}
- Lower Band: ${indicators['bb_lower']:.2f}
- Price Position: {'Near upper band (overbought)' if indicators['current_price'] > indicators['bb_middle'] else 'Near lower band (oversold)'}

## Support & Resistance Levels
- Resistance 1: ${support_resistance['resistance_1']:.2f}
- Resistance 2: ${support_resistance['resistance_2']:.2f}
- 20-Day High: ${support_resistance['resistance_20d']:.2f}
- 50-Day High: ${support_resistance['resistance_50d']:.2f}
- Pivot Point: ${support_resistance['pivot']:.2f}
- Support 1: ${support_resistance['support_1']:.2f}
- Support 2: ${support_resistance['support_2']:.2f}
- 20-Day Low: ${support_resistance['support_20d']:.2f}
- 50-Day Low: ${support_resistance['support_50d']:.2f}

## Candlestick Patterns
{chr(10).join('- ' + p for p in patterns['candlestick_patterns'])}

## Volume Analysis
- Current Volume: {indicators['current_volume']:,.0f}
- 20-Day Avg Volume: {indicators['volume_sma']:,.0f}
- Volume Trend: {'Above Average' if indicators['current_volume'] > indicators['volume_sma'] else 'Below Average'}

## Volatility
- ATR (14): ${indicators['atr']:.2f}
- Recent Volatility: {patterns['price_action']['volatility']:.2f}%

## Price Action Signals
- Breakout Signal: {patterns['price_action'].get('breakout_signal', 'None')}
"""

        # Use LLM to generate narrative analysis
        prompt = f"""You are an expert technical analyst specializing in TradingView-style chart analysis.

Analyze the following technical data and provide a comprehensive trading recommendation.

{technical_summary}

Please provide:
1. **Overall Technical Assessment** - Interpret the TradingView rating and key indicators
2. **Trend Analysis** - Explain the current trend and momentum
3. **Entry/Exit Points** - Suggest specific price levels for entry and stop-loss
4. **Risk Assessment** - Evaluate technical risk factors
5. **Trading Recommendation** - Clear BUY/SELL/HOLD with confidence level (1-10)

Format your response as a professional technical analysis report.
"""

        try:
            # LLM Cache Integration
            from tradingagents.services.llm_cache import llm_cache
            
            # Use prompt as key (if data changes, prompt changes -> new cache entry)
            # We trust _generate_key to handle hashing length
            cached_resp = llm_cache.get(prompt, "technical_analyst_inner")
            
            if cached_resp:
                return cached_resp
                
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Cache the text content
            llm_cache.set(prompt, "technical_analyst_inner", content)
            
            return content
        except Exception as e:
            # Fallback to template-based report if LLM fails
            return self._generate_template_report(ticker, technical_summary, ratings)

    def _generate_template_report(self, ticker: str, technical_summary: str, ratings: Dict) -> str:
        """Fallback template report if LLM fails"""
        return f"""
# Technical Analysis Report: {ticker}

## TradingView Rating: {ratings['overall']}

{technical_summary}

## Recommendation
Based on the technical indicators, the overall rating is **{ratings['overall']}** with {ratings['buy_percentage']}% buy signals and {ratings['sell_percentage']}% sell signals.

**Note:** This is a basic technical summary. For detailed analysis, please ensure LLM is properly configured.
"""

    def _generate_error_report(self, ticker: str, error: str) -> str:
        """Generate error report"""
        return f"""
# Technical Analysis Error: {ticker}

Unable to complete technical analysis.

**Error:** {error}

Please verify:
1. Ticker symbol is correct
2. Market data is available for this symbol
3. Internet connection is stable

**Recommendation:** HOLD - Unable to provide technical recommendation due to data issues.
"""
