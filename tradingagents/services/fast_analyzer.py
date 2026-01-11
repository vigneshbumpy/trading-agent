"""
Fast stock analyzer - Quick technical + sentiment analysis
Replaces slow multi-agent system for rapid trading decisions
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

logger = logging.getLogger(__name__)


class FastAnalyzer:
    """
    Fast stock analyzer using technical indicators and sentiment
    Much faster than the full multi-agent system
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.cache = {}
        self.cache_duration = timedelta(minutes=5)
    
    def analyze(self, symbol: str) -> Dict:
        """
        Quick analysis of a stock
        
        Args:
            symbol: Stock ticker
            
        Returns:
            Analysis result with action and confidence
        """
        # Check cache
        cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # Run analyses in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(self._get_technical_signals, symbol): 'technical',
                    executor.submit(self._get_price_momentum, symbol): 'momentum',
                    executor.submit(self._get_volume_analysis, symbol): 'volume'
                }
                
                results = {}
                for future in as_completed(futures):
                    analysis_type = futures[future]
                    try:
                        results[analysis_type] = future.result()
                    except Exception as e:
                        logger.error(f"Error in {analysis_type} analysis: {e}")
                        results[analysis_type] = {'signal': 'HOLD', 'confidence': 0.5}
            
            # Combine signals
            final_result = self._combine_signals(symbol, results)
            
            # Cache result
            self.cache[cache_key] = final_result
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return {
                'symbol': symbol,
                'action': 'HOLD',
                'confidence': 0.3,
                'reason': f'Analysis error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_technical_signals(self, symbol: str) -> Dict:
        """Get technical analysis signals"""
        try:
            import yfinance as yf
            
            # Get recent data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d', interval='1h')
            
            if hist.empty:
                return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'No data'}
            
            # Calculate simple indicators
            close = hist['Close']
            
            # Moving averages
            sma_5 = close.rolling(5).mean().iloc[-1]
            sma_20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else sma_5
            current_price = close.iloc[-1]
            
            # RSI (simplified)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            
            # Determine signal
            signals = []
            
            # Price vs MA
            if current_price > sma_5 > sma_20:
                signals.append(('BUY', 0.7))
            elif current_price < sma_5 < sma_20:
                signals.append(('SELL', 0.7))
            else:
                signals.append(('HOLD', 0.5))
            
            # RSI
            if current_rsi < 30:
                signals.append(('BUY', 0.8))  # Oversold
            elif current_rsi > 70:
                signals.append(('SELL', 0.8))  # Overbought
            else:
                signals.append(('HOLD', 0.5))
            
            # Aggregate
            buy_score = sum(c for s, c in signals if s == 'BUY')
            sell_score = sum(c for s, c in signals if s == 'SELL')
            
            if buy_score > sell_score and buy_score > 0.6:
                return {'signal': 'BUY', 'confidence': min(0.9, buy_score / 2), 
                       'reason': f'RSI={current_rsi:.0f}, Price>MA'}
            elif sell_score > buy_score and sell_score > 0.6:
                return {'signal': 'SELL', 'confidence': min(0.9, sell_score / 2),
                       'reason': f'RSI={current_rsi:.0f}, Price<MA'}
            else:
                return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'No clear signal'}
                
        except Exception as e:
            logger.error(f"Technical analysis error for {symbol}: {e}")
            return {'signal': 'HOLD', 'confidence': 0.5, 'reason': str(e)}
    
    def _get_price_momentum(self, symbol: str) -> Dict:
        """Analyze price momentum"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='5d')
            
            if hist.empty or len(hist) < 2:
                return {'signal': 'HOLD', 'confidence': 0.5}
            
            # Calculate momentum
            returns = hist['Close'].pct_change()
            
            # Recent momentum (last 3 periods)
            recent_return = returns.iloc[-3:].sum() if len(returns) >= 3 else returns.iloc[-1]
            
            # Determine signal
            if recent_return > 0.02:  # >2% gain
                return {'signal': 'BUY', 'confidence': min(0.8, 0.5 + recent_return * 5),
                       'reason': f'+{recent_return*100:.1f}% momentum'}
            elif recent_return < -0.02:  # >2% loss
                return {'signal': 'SELL', 'confidence': min(0.8, 0.5 + abs(recent_return) * 5),
                       'reason': f'{recent_return*100:.1f}% momentum'}
            else:
                return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'Neutral momentum'}
                
        except Exception as e:
            logger.error(f"Momentum analysis error for {symbol}: {e}")
            return {'signal': 'HOLD', 'confidence': 0.5}
    
    def _get_volume_analysis(self, symbol: str) -> Dict:
        """Analyze trading volume"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='10d')
            
            if hist.empty or len(hist) < 5:
                return {'signal': 'HOLD', 'confidence': 0.5}
            
            # Volume analysis
            avg_volume = hist['Volume'].rolling(5).mean().iloc[-1]
            current_volume = hist['Volume'].iloc[-1]
            price_change = hist['Close'].pct_change().iloc[-1]
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # High volume + price up = bullish
            # High volume + price down = bearish
            if volume_ratio > 1.5:
                if price_change > 0:
                    return {'signal': 'BUY', 'confidence': 0.7,
                           'reason': f'High volume ({volume_ratio:.1f}x) + price up'}
                else:
                    return {'signal': 'SELL', 'confidence': 0.7,
                           'reason': f'High volume ({volume_ratio:.1f}x) + price down'}
            
            return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'Normal volume'}
            
        except Exception as e:
            logger.error(f"Volume analysis error for {symbol}: {e}")
            return {'signal': 'HOLD', 'confidence': 0.5}
    
    def _combine_signals(self, symbol: str, results: Dict) -> Dict:
        """Combine all signals into final decision"""
        
        buy_confidence = 0
        sell_confidence = 0
        hold_confidence = 0
        reasons = []
        
        weights = {'technical': 0.4, 'momentum': 0.35, 'volume': 0.25}
        
        for analysis_type, result in results.items():
            weight = weights.get(analysis_type, 0.33)
            signal = result.get('signal', 'HOLD')
            confidence = result.get('confidence', 0.5)
            reason = result.get('reason', '')
            
            if signal == 'BUY':
                buy_confidence += confidence * weight
                if reason:
                    reasons.append(f"📈 {reason}")
            elif signal == 'SELL':
                sell_confidence += confidence * weight
                if reason:
                    reasons.append(f"📉 {reason}")
            else:
                hold_confidence += confidence * weight
        
        # Determine final action
        if buy_confidence > sell_confidence and buy_confidence > 0.5:
            action = 'BUY'
            confidence = min(0.95, buy_confidence)
        elif sell_confidence > buy_confidence and sell_confidence > 0.5:
            action = 'SELL'
            confidence = min(0.95, sell_confidence)
        else:
            action = 'HOLD'
            confidence = max(hold_confidence, 0.5)
        
        return {
            'symbol': symbol,
            'action': action,
            'confidence': confidence,
            'buy_score': buy_confidence,
            'sell_score': sell_confidence,
            'reasons': reasons,
            'details': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def quick_scan(self, symbols: List[str]) -> List[Dict]:
        """
        Quick scan multiple symbols in parallel
        
        Args:
            symbols: List of stock tickers
            
        Returns:
            List of analysis results sorted by confidence
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.analyze, symbol): symbol for symbol in symbols}
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
        
        # Sort by confidence (actionable items first)
        results.sort(key=lambda x: (
            0 if x['action'] == 'HOLD' else 1,  # HOLD last
            x['confidence']
        ), reverse=True)
        
        return results


class FastCryptoAnalyzer(FastAnalyzer):
    """Fast analyzer optimized for crypto (24/7 market)"""
    
    def _get_technical_signals(self, symbol: str) -> Dict:
        """Get technical signals for crypto"""
        try:
            import yfinance as yf
            
            # Normalize symbol for yfinance
            if not symbol.endswith('-USD'):
                yf_symbol = f"{symbol}-USD"
            else:
                yf_symbol = symbol
            
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period='2d', interval='15m')
            
            if hist.empty:
                return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'No data'}
            
            close = hist['Close']
            current_price = close.iloc[-1]
            
            # Short-term MAs for crypto
            sma_10 = close.rolling(10).mean().iloc[-1]
            sma_30 = close.rolling(30).mean().iloc[-1] if len(close) >= 30 else sma_10
            
            # Price change
            pct_change = (current_price - close.iloc[0]) / close.iloc[0] * 100
            
            if current_price > sma_10 > sma_30 and pct_change > 1:
                return {'signal': 'BUY', 'confidence': 0.75, 
                       'reason': f'Uptrend +{pct_change:.1f}%'}
            elif current_price < sma_10 < sma_30 and pct_change < -1:
                return {'signal': 'SELL', 'confidence': 0.75,
                       'reason': f'Downtrend {pct_change:.1f}%'}
            else:
                return {'signal': 'HOLD', 'confidence': 0.5, 'reason': 'Sideways'}
                
        except Exception as e:
            logger.error(f"Crypto technical analysis error: {e}")
            return {'signal': 'HOLD', 'confidence': 0.5}


def create_fast_analyzer(symbol: str = None) -> FastAnalyzer:
    """Factory to create appropriate analyzer"""
    crypto_symbols = {'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'AVAX', 'MATIC', 'LINK'}
    
    if symbol:
        symbol_base = symbol.replace('-USD', '').replace('.NS', '').upper()
        if symbol_base in crypto_symbols:
            return FastCryptoAnalyzer()
    
    return FastAnalyzer()
