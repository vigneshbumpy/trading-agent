"""
Continuous monitoring automation service for automated trading
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.services.execution_service import TradeExecutionService
from tradingagents.services.position_sizing import PositionSizingCalculator, create_position_sizer
from tradingagents.services.risk_limits import RiskLimits, create_risk_limits
from tradingagents.services.market_hours import MarketHoursService
from tradingagents.utils.market_detector import MarketDetector
from dashboard.multiuser.brokers.unified_broker import Market

logger = logging.getLogger(__name__)


class AutomationService:
    """Continuous monitoring and automated trading service"""

    def __init__(
        self,
        trading_graph: TradingAgentsGraph,
        execution_service: TradeExecutionService,
        watchlist: List[str],
        config: Dict = None
    ):
        """
        Initialize automation service

        Args:
            trading_graph: TradingAgentsGraph instance
            execution_service: TradeExecutionService instance
            watchlist: List of symbols to monitor
            config: Configuration dict
        """
        self.trading_graph = trading_graph
        self.execution_service = execution_service
        self.watchlist = watchlist
        self.config = config or {}

        # Service state
        self.is_running = False
        self.is_paused = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Configuration
        self.analysis_interval = self.config.get("analysis_interval", 300)  # 5 minutes default
        self.auto_execute = self.config.get("auto_execute", True)
        self.position_sizer = create_position_sizer(self.config.get("position_sizing", {}))
        self.risk_limits = create_risk_limits(self.config.get("risk_limits", {}))

        # Safety: Log paper trading mode
        if self.execution_service.paper_trading:
            logger.info("Automation service initialized in PAPER TRADING mode")
        else:
            logger.warning("Automation service initialized in LIVE TRADING mode")

        # Tracking
        self.last_analysis: Dict[str, datetime] = {}
        self.analysis_count = 0
        self.execution_count = 0
        self.errors: List[Dict] = []

    def start(self):
        """Start the automation service"""
        if self.is_running:
            logger.warning("Automation service is already running")
            return

        self.is_running = True
        self.is_paused = False
        self.stop_event.clear()

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        logger.info(f"Automation service started with watchlist: {self.watchlist}")

    def stop(self):
        """Stop the automation service"""
        if not self.is_running:
            return

        self.is_running = False
        self.stop_event.set()

        if self.thread:
            self.thread.join(timeout=10)

        logger.info("Automation service stopped")

    def pause(self):
        """Pause the automation service"""
        self.is_paused = True
        logger.info("Automation service paused")

    def resume(self):
        """Resume the automation service"""
        self.is_paused = False
        logger.info("Automation service resumed")

        self.last_morning_brief_date = None
        
    def _run_loop(self):
        """Main automation loop"""
        logger.info("Starting automation loop")

        while self.is_running and not self.stop_event.is_set():
            try:
                if self.is_paused:
                    time.sleep(1)
                    continue

                # Pre-market Morning Brief (US Market)
                if MarketHoursService.is_pre_market(Market.US_NASDAQ):
                    today = datetime.now().date()
                    if self.last_morning_brief_date != today:
                        try:
                            from tradingagents.services.morning_brief import morning_brief_service
                            morning_brief_service.generate_brief(self.watchlist)
                            self.last_morning_brief_date = today
                            logger.info("✅ Morning Brief generated successfully")
                        except Exception as e:
                            logger.error(f"Failed to generate morning brief: {e}")

                # Process watchlist in parallel (Batch Analysis)
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                max_workers = self.config.get("batch_size", 3) # Default 3 parallel agents
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._process_symbol, symbol): symbol 
                        for symbol in self.watchlist 
                        if not self.stop_event.is_set()
                    }
                    
                    for future in as_completed(futures):
                        symbol = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
                            self.errors.append({
                                "timestamp": datetime.now().isoformat(),
                                "symbol": symbol,
                                "error": str(e)
                            })
                            
                        if self.stop_event.is_set():
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

                # Wait before next cycle
                if not self.stop_event.is_set():
                    time.sleep(self.analysis_interval)
                if not self.stop_event.is_set():
                    time.sleep(self.analysis_interval)

            except Exception as e:
                logger.error(f"Error in automation loop: {e}", exc_info=True)
                self.errors.append({
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                })
                time.sleep(60)  # Wait a minute before retrying

        logger.info("Automation loop ended")

    def _process_symbol(self, symbol: str):
        """Process a single symbol"""
        # Check if enough time has passed since last analysis
        last_analysis_time = self.last_analysis.get(symbol)
        if last_analysis_time:
            time_since = (datetime.now() - last_analysis_time).total_seconds()
            if time_since < self.analysis_interval:
                return  # Skip if too soon

        # Detect market
        market = MarketDetector.detect_market(symbol)

        # Check if market is open
        if not MarketHoursService.is_market_open(market):
            logger.debug(f"Market {market.value} is closed for {symbol}, skipping")
            return

        # Phase 2: Momentum Filter
        from tradingagents.services.market_filter import market_filter
        pass_momentum, reason = market_filter.check_momentum(symbol)
        
        if not pass_momentum:
            logger.info(f"Skipping {symbol} (Momentum Filter): {reason}")
            # Update last analysis so we don't retry immediately
            self.last_analysis[symbol] = datetime.now() 
            return

        logger.info(f"Analyzing {symbol} (market: {market.value})")

        try:
            # Run trading analysis
            trade_date = datetime.now().strftime("%Y-%m-%d")
            final_state, decision = self.trading_graph.propagate(symbol, trade_date)

            self.analysis_count += 1
            self.last_analysis[symbol] = datetime.now()

            # Parse decision
            parsed_decision = self.execution_service.parse_decision(decision)

            if parsed_decision["action"] == "HOLD":
                logger.info(f"Decision for {symbol}: HOLD - no action")
                return

            # Get current price
            broker = self.execution_service.get_broker(market)
            exchange = MarketDetector.get_exchange_for_market(market)
            normalized_symbol = MarketDetector.normalize_symbol(symbol, market, None)

            quote = broker.get_quote(normalized_symbol, exchange)
            if "error" in quote:
                logger.error(f"Could not get quote for {symbol}: {quote['error']}")
                return

            current_price = quote.get("last_price", 0)
            if current_price == 0:
                logger.error(f"Invalid price for {symbol}")
                return

            # Get portfolio value
            account_info = broker.get_account_info()
            portfolio_value = account_info.get("portfolio_value", account_info.get("buying_power", 0))

            # Calculate position size
            position_info = self.position_sizer.calculate_position_size(
                portfolio_value=portfolio_value,
                price=current_price
            )

            quantity = position_info["quantity"]

            # Check risk limits
            risk_check = self.risk_limits.can_trade(
                symbol=symbol,
                action=parsed_decision["action"],
                quantity=quantity,
                price=current_price,
                portfolio_value=portfolio_value,
                market=market.value
            )

            if not risk_check["allowed"]:
                logger.warning(f"Trade blocked for {symbol}: {risk_check['reason']}")
                return

            # Execute trade if auto-execute is enabled
            if self.auto_execute:
                logger.info(f"Executing {parsed_decision['action']} {quantity} {symbol} @ {current_price}")

                result = self.execution_service.execute_trade(
                    symbol=symbol,
                    action=parsed_decision["action"],
                    quantity=quantity,
                    order_type="MARKET",
                    market=market
                )

                if result.get("status") == "success":
                    self.execution_count += 1
                    # Record trade in risk limits
                    self.risk_limits.record_trade(
                        symbol=symbol,
                        action=parsed_decision["action"],
                        quantity=quantity,
                        price=current_price,
                        market=market.value
                    )
                    logger.info(f"Trade executed successfully: {result.get('order_id')}")
                else:
                    logger.error(f"Trade execution failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            raise

    def get_status(self) -> Dict:
        """Get service status"""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "watchlist": self.watchlist,
            "analysis_count": self.analysis_count,
            "execution_count": self.execution_count,
            "last_analysis": {k: v.isoformat() for k, v in self.last_analysis.items()},
            "error_count": len(self.errors),
            "recent_errors": self.errors[-5:]  # Last 5 errors
        }

    def update_watchlist(self, watchlist: List[str]):
        """Update watchlist"""
        self.watchlist = watchlist
        logger.info(f"Watchlist updated: {watchlist}")

    def add_symbol(self, symbol: str):
        """Add symbol to watchlist"""
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            logger.info(f"Added {symbol} to watchlist")

    def remove_symbol(self, symbol: str):
        """Remove symbol from watchlist"""
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            logger.info(f"Removed {symbol} from watchlist")
