"""
Fully Autonomous Trading Service
- Auto-discovers trending stocks from news
- Fast analysis (no slow multi-agent)
- Automatic paper trading execution
- No manual watchlist needed
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from tradingagents.services.news_discovery import NewsDiscoveryService, create_news_discovery
from tradingagents.services.fast_analyzer import FastAnalyzer, create_fast_analyzer
from tradingagents.services.execution_service import TradeExecutionService
from tradingagents.services.market_hours import MarketHoursService
from tradingagents.utils.market_detector import MarketDetector

logger = logging.getLogger(__name__)


class AutonomousTrader:
    """
    Fully autonomous trading bot
    - Discovers stocks automatically from news
    - Analyzes quickly using technical indicators
    - Executes paper trades automatically
    """
    
    def __init__(
        self,
        execution_service: TradeExecutionService = None,
        config: Dict = None,
        on_trade: Callable = None,
        on_analysis: Callable = None
    ):
        """
        Initialize autonomous trader
        
        Args:
            execution_service: Trade execution service (paper trading by default)
            config: Configuration dict
            on_trade: Callback when trade is executed
            on_analysis: Callback when analysis is complete
        """
        self.config = config or {}
        
        # Services
        self.news_discovery = create_news_discovery(self.config.get('news', {}))
        self.analyzer = FastAnalyzer(self.config.get('analyzer', {}))
        self.execution_service = execution_service or TradeExecutionService(
            paper_trading=True,
            live_trading_approved=False
        )
        
        # Callbacks
        self.on_trade = on_trade
        self.on_analysis = on_analysis
        
        # Configuration
        self.scan_interval = self.config.get('scan_interval', 60)  # 1 minute
        self.min_confidence = self.config.get('min_confidence', 0.65)
        self.max_positions = self.config.get('max_positions', 5)
        self.position_size_pct = self.config.get('position_size_pct', 0.02)  # 2% per trade
        self.include_crypto = self.config.get('include_crypto', True)
        self.include_indian = self.config.get('include_indian', True)
        
        # State
        self.is_running = False
        self.is_paused = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Tracking
        self.positions: Dict[str, Dict] = {}  # Current positions
        self.trades_today: List[Dict] = []
        self.analyses_today: List[Dict] = []
        self.errors: List[Dict] = []
        self.last_scan_time: Optional[datetime] = None
        
        # Stats
        self.stats = {
            'total_analyses': 0,
            'total_trades': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0
        }
        
        logger.info("Autonomous Trader initialized")
        logger.info(f"  - Paper Trading: {self.execution_service.paper_trading}")
        logger.info(f"  - Min Confidence: {self.min_confidence}")
        logger.info(f"  - Scan Interval: {self.scan_interval}s")
    
    def start(self):
        """Start autonomous trading"""
        if self.is_running:
            logger.warning("Autonomous trader already running")
            return
        
        self.is_running = True
        self.is_paused = False
        self.stop_event.clear()
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        mode = "📝 PAPER" if self.execution_service.paper_trading else "🔴 LIVE"
        logger.info(f"🚀 Autonomous Trader STARTED in {mode} mode")
    
    def stop(self):
        """Stop autonomous trading"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info("🛑 Autonomous Trader STOPPED")
    
    def pause(self):
        """Pause trading"""
        self.is_paused = True
        logger.info("⏸️ Autonomous Trader PAUSED")
    
    def resume(self):
        """Resume trading"""
        self.is_paused = False
        logger.info("▶️ Autonomous Trader RESUMED")
    
    def _run_loop(self):
        """Main trading loop"""
        logger.info("Starting autonomous trading loop...")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                if self.is_paused:
                    time.sleep(1)
                    continue
                
                # Run trading cycle
                self._trading_cycle()
                
                # Wait before next scan
                self.stop_event.wait(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                self.errors.append({
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                })
                time.sleep(30)  # Wait before retry
        
        logger.info("Trading loop ended")
    
    def _trading_cycle(self):
        """Single trading cycle: discover -> analyze -> trade"""
        cycle_start = datetime.now()
        logger.info(f"📊 Starting trading cycle at {cycle_start.strftime('%H:%M:%S')}")
        
        try:
            # Step 1: Discover trending stocks
            trending = self.news_discovery.discover_trending_stocks()
            logger.info(f"📰 Found {len(trending)} trending stocks")
            
            if not trending:
                logger.info("No trending stocks found, skipping cycle")
                return
            
            # Step 2: Quick analysis of top trending
            actionable = []
            
            for stock in trending[:10]:  # Analyze top 10
                ticker = stock['ticker']
                
                # Check market hours
                market = MarketDetector.detect_market(ticker)
                if not MarketHoursService.is_market_open(market):
                    logger.debug(f"Market closed for {ticker}, skipping")
                    continue
                
                # Fast analysis
                analysis = self.analyzer.analyze(ticker)
                self.stats['total_analyses'] += 1
                
                # Combine news sentiment with technical analysis
                news_sentiment = stock.get('sentiment', 0.5)
                technical_action = analysis.get('action', 'HOLD')
                technical_confidence = analysis.get('confidence', 0.5)
                
                # Combined confidence
                combined_confidence = (news_sentiment * 0.4 + technical_confidence * 0.6)
                
                # Determine final action
                if stock['action'] == technical_action:
                    # News and technical agree - high confidence
                    final_action = technical_action
                    final_confidence = min(0.95, combined_confidence * 1.2)
                elif technical_action == 'HOLD':
                    # Technical says hold, use news signal with lower confidence
                    final_action = stock['action']
                    final_confidence = combined_confidence * 0.7
                else:
                    # Conflicting signals - be cautious
                    final_action = 'HOLD'
                    final_confidence = 0.4
                
                result = {
                    'ticker': ticker,
                    'market': market.value,
                    'action': final_action,
                    'confidence': final_confidence,
                    'news_sentiment': news_sentiment,
                    'technical': technical_action,
                    'reasons': analysis.get('reasons', []) + [f"News: {stock.get('headlines', [''])[0][:50]}"],
                    'timestamp': datetime.now().isoformat()
                }
                
                self.analyses_today.append(result)
                
                # Callback
                if self.on_analysis:
                    self.on_analysis(result)
                
                # Check if actionable
                if final_action != 'HOLD' and final_confidence >= self.min_confidence:
                    actionable.append(result)
                    logger.info(f"✅ {ticker}: {final_action} (confidence: {final_confidence:.0%})")
                else:
                    logger.debug(f"⏸️ {ticker}: {final_action} (confidence: {final_confidence:.0%}) - below threshold")
            
            # Step 3: Execute trades
            if actionable:
                logger.info(f"🎯 {len(actionable)} actionable trades found")
                self._execute_trades(actionable)
            else:
                logger.info("No actionable trades this cycle")
            
            self.last_scan_time = datetime.now()
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            logger.info(f"✨ Cycle complete in {cycle_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            self.errors.append({
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'type': 'cycle_error'
            })
    
    def _execute_trades(self, actionable: List[Dict]):
        """Execute trades for actionable signals"""
        
        for signal in actionable:
            ticker = signal['ticker']
            action = signal['action']
            confidence = signal['confidence']
            
            try:
                # Check if we already have a position
                if ticker in self.positions:
                    existing = self.positions[ticker]
                    if existing['action'] == action:
                        logger.info(f"Already have {action} position in {ticker}, skipping")
                        continue
                
                # Check max positions
                if len(self.positions) >= self.max_positions and action == 'BUY':
                    logger.warning(f"Max positions ({self.max_positions}) reached, skipping {ticker}")
                    continue
                
                # Calculate quantity (simplified - would use position sizer in production)
                market = MarketDetector.detect_market(ticker)
                quantity = self._calculate_quantity(ticker, market)
                
                if quantity <= 0:
                    logger.warning(f"Cannot calculate quantity for {ticker}")
                    continue
                
                # Execute trade
                logger.info(f"🔄 Executing: {action} {quantity} {ticker}")
                
                result = self.execution_service.execute_trade(
                    symbol=ticker,
                    action=action,
                    quantity=quantity,
                    order_type='MARKET',
                    market=market
                )
                
                trade_record = {
                    'ticker': ticker,
                    'action': action,
                    'quantity': quantity,
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat(),
                    'result': result,
                    'paper_trading': self.execution_service.paper_trading
                }
                
                self.trades_today.append(trade_record)
                self.stats['total_trades'] += 1
                
                if result.get('status') == 'success':
                    self.stats['successful_trades'] += 1
                    
                    # Track position
                    if action == 'BUY':
                        self.positions[ticker] = {
                            'action': action,
                            'quantity': quantity,
                            'entry_time': datetime.now().isoformat(),
                            'order_id': result.get('order_id')
                        }
                    elif action == 'SELL' and ticker in self.positions:
                        del self.positions[ticker]
                    
                    logger.info(f"✅ Trade executed: {action} {quantity} {ticker}")
                else:
                    logger.error(f"❌ Trade failed: {result.get('error')}")
                
                # Callback
                if self.on_trade:
                    self.on_trade(trade_record)
                
            except Exception as e:
                logger.error(f"Error executing trade for {ticker}: {e}")
                self.errors.append({
                    'timestamp': datetime.now().isoformat(),
                    'ticker': ticker,
                    'error': str(e)
                })
    
    def _calculate_quantity(self, ticker: str, market) -> float:
        """Calculate position size"""
        try:
            # Get current price
            import yfinance as yf
            
            # Normalize for yfinance
            if market.value == 'CRYPTO':
                yf_ticker = f"{ticker.replace('-USD', '')}-USD"
            else:
                yf_ticker = ticker
            
            stock = yf.Ticker(yf_ticker)
            hist = stock.history(period='1d')
            
            if hist.empty:
                return 0
            
            current_price = hist['Close'].iloc[-1]
            
            # Simple position sizing: 2% of $100,000 paper portfolio
            portfolio_value = 100000  # Paper trading default
            position_value = portfolio_value * self.position_size_pct
            
            quantity = position_value / current_price
            
            # Round appropriately
            if market.value == 'CRYPTO':
                return round(quantity, 4)  # Crypto can have decimals
            else:
                return int(quantity)  # Stocks need whole shares
                
        except Exception as e:
            logger.error(f"Error calculating quantity for {ticker}: {e}")
            return 0
    
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'paper_trading': self.execution_service.paper_trading,
            'last_scan': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'positions': len(self.positions),
            'trades_today': len(self.trades_today),
            'analyses_today': len(self.analyses_today),
            'stats': self.stats,
            'errors': len(self.errors),
            'config': {
                'scan_interval': self.scan_interval,
                'min_confidence': self.min_confidence,
                'max_positions': self.max_positions,
                'position_size_pct': self.position_size_pct
            }
        }
    
    def get_recent_trades(self, limit: int = 20) -> List[Dict]:
        """Get recent trades"""
        return self.trades_today[-limit:]
    
    def get_recent_analyses(self, limit: int = 50) -> List[Dict]:
        """Get recent analyses"""
        return self.analyses_today[-limit:]
    
    def get_positions(self) -> Dict:
        """Get current positions"""
        return self.positions.copy()


def create_autonomous_trader(
    paper_trading: bool = True,
    config: Dict = None,
    on_trade: Callable = None,
    on_analysis: Callable = None
) -> AutonomousTrader:
    """
    Factory function to create autonomous trader
    
    Args:
        paper_trading: Enable paper trading (default True)
        config: Configuration dict
        on_trade: Callback when trade executes
        on_analysis: Callback when analysis completes
    """
    execution_service = TradeExecutionService(
        paper_trading=paper_trading,
        live_trading_approved=not paper_trading
    )
    
    return AutonomousTrader(
        execution_service=execution_service,
        config=config,
        on_trade=on_trade,
        on_analysis=on_analysis
    )
