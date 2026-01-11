"""
Health monitoring service for broker connectivity, execution tracking, and auto-recovery

Features:
- Broker health checks
- Execution statistics tracking
- Watchdog thread for continuous monitoring
- Alert callbacks for failures
- Auto-pause/resume on issues
"""

import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from dashboard.multiuser.brokers.unified_broker import UnifiedBrokerInterface, BrokerType

logger = logging.getLogger(__name__)


class AlertLevel:
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthMonitor:
    """Monitor broker health, execution performance, and system health with auto-recovery"""

    def __init__(
        self,
        check_interval: int = 60,
        auto_start: bool = False,
        on_alert: Optional[Callable] = None,
        on_broker_down: Optional[Callable] = None,
        on_broker_recovered: Optional[Callable] = None
    ):
        """
        Initialize health monitor

        Args:
            check_interval: Health check interval in seconds
            auto_start: Start monitoring thread automatically
            on_alert: Callback for alerts (level, message, details)
            on_broker_down: Callback when broker goes down
            on_broker_recovered: Callback when broker recovers
        """
        self.check_interval = check_interval
        self.brokers: Dict[BrokerType, UnifiedBrokerInterface] = {}
        self.broker_status: Dict[BrokerType, Dict] = {}
        self.execution_stats: Dict[str, List] = defaultdict(list)
        self.api_rate_limits: Dict[BrokerType, Dict] = {}
        self.last_check: Dict[BrokerType, datetime] = {}
        
        # Callbacks
        self.on_alert = on_alert
        self.on_broker_down = on_broker_down
        self.on_broker_recovered = on_broker_recovered
        
        # Watchdog thread
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False
        
        # Circuit breaker
        self._circuit_breaker: Dict[BrokerType, Dict] = {}
        self._max_consecutive_failures = 5
        self._recovery_timeout = 300  # 5 minutes
        
        # System metrics
        self.start_time = datetime.now()
        self.total_health_checks = 0
        self.total_alerts = 0
        self.alert_history: List[Dict] = []
        
        if auto_start:
            self.start_monitoring()

    def register_broker(self, broker_type: BrokerType, broker: UnifiedBrokerInterface):
        """Register a broker for monitoring"""
        self.brokers[broker_type] = broker
        self.broker_status[broker_type] = {
            "status": "unknown",
            "last_check": None,
            "response_time": None,
            "error_count": 0,
            "consecutive_failures": 0,
            "last_error": None,
            "last_success": None
        }
        self._circuit_breaker[broker_type] = {
            "open": False,
            "failures": 0,
            "last_failure": None,
            "open_until": None
        }
        logger.info(f"Registered broker {broker_type.value} for health monitoring")

    def check_broker_health(self, broker_type: BrokerType) -> Dict:
        """
        Check health of a specific broker

        Args:
            broker_type: Broker type to check

        Returns:
            Health status dict
        """
        if broker_type not in self.brokers:
            return {
                "status": "error",
                "error": f"Broker {broker_type.value} not registered"
            }
        
        # Check circuit breaker
        cb = self._circuit_breaker.get(broker_type, {})
        if cb.get("open") and cb.get("open_until"):
            if datetime.now() < cb["open_until"]:
                return {
                    "status": "circuit_open",
                    "error": "Circuit breaker open, broker temporarily disabled",
                    "recovery_at": cb["open_until"].isoformat()
                }
            else:
                # Try to recover
                self._circuit_breaker[broker_type]["open"] = False
                logger.info(f"Circuit breaker closed for {broker_type.value}, attempting recovery")

        broker = self.brokers[broker_type]
        start_time = time.time()
        self.total_health_checks += 1

        try:
            # Try to get account info as health check
            account_info = broker.get_account_info()

            response_time = time.time() - start_time
            
            was_down = self.broker_status[broker_type]["status"] == "error"

            if "error" in account_info:
                self._handle_broker_failure(broker_type, account_info.get("error"))
            else:
                self.broker_status[broker_type]["status"] = "healthy"
                self.broker_status[broker_type]["consecutive_failures"] = 0
                self.broker_status[broker_type]["last_error"] = None
                self.broker_status[broker_type]["last_success"] = datetime.now()
                self._circuit_breaker[broker_type]["failures"] = 0
                
                # Notify recovery
                if was_down and self.on_broker_recovered:
                    self.on_broker_recovered(broker_type)
                    self._send_alert(
                        AlertLevel.INFO,
                        f"Broker {broker_type.value} recovered",
                        {"broker": broker_type.value}
                    )

            self.broker_status[broker_type]["last_check"] = datetime.now()
            self.broker_status[broker_type]["response_time"] = response_time

            return {
                "status": self.broker_status[broker_type]["status"],
                "response_time": response_time,
                "account_info": account_info if "error" not in account_info else None
            }

        except Exception as e:
            response_time = time.time() - start_time
            self._handle_broker_failure(broker_type, str(e))
            self.broker_status[broker_type]["last_check"] = datetime.now()
            self.broker_status[broker_type]["response_time"] = response_time

            logger.error(f"Health check failed for {broker_type.value}: {e}")

            return {
                "status": "error",
                "error": str(e),
                "response_time": response_time
            }
    
    def _handle_broker_failure(self, broker_type: BrokerType, error: str):
        """Handle broker failure with circuit breaker logic"""
        self.broker_status[broker_type]["error_count"] += 1
        self.broker_status[broker_type]["consecutive_failures"] += 1
        self.broker_status[broker_type]["last_error"] = error
        self.broker_status[broker_type]["status"] = "error"
        
        # Update circuit breaker
        cb = self._circuit_breaker[broker_type]
        cb["failures"] += 1
        cb["last_failure"] = datetime.now()
        
        # Check if circuit should open
        if cb["failures"] >= self._max_consecutive_failures:
            cb["open"] = True
            cb["open_until"] = datetime.now() + timedelta(seconds=self._recovery_timeout)
            
            self._send_alert(
                AlertLevel.CRITICAL,
                f"Circuit breaker opened for {broker_type.value}",
                {
                    "broker": broker_type.value,
                    "failures": cb["failures"],
                    "recovery_at": cb["open_until"].isoformat()
                }
            )
            
        # Notify broker down
        if self.broker_status[broker_type]["consecutive_failures"] == 1:
            if self.on_broker_down:
                self.on_broker_down(broker_type, error)
            self._send_alert(
                AlertLevel.ERROR,
                f"Broker {broker_type.value} is down: {error}",
                {"broker": broker_type.value, "error": error}
            )
    
    def _send_alert(self, level: str, message: str, details: Dict = None):
        """Send alert and store in history"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "details": details or {}
        }
        
        self.alert_history.append(alert)
        self.total_alerts += 1
        
        # Keep only last 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        if self.on_alert:
            self.on_alert(level, message, details)
        
        logger.log(
            logging.CRITICAL if level == AlertLevel.CRITICAL else
            logging.ERROR if level == AlertLevel.ERROR else
            logging.WARNING if level == AlertLevel.WARNING else
            logging.INFO,
            f"[{level.upper()}] {message}"
        )

    def check_all_brokers(self) -> Dict:
        """Check health of all registered brokers"""
        results = {}

        for broker_type in self.brokers.keys():
            results[broker_type.value] = self.check_broker_health(broker_type)

        return results

    def record_execution(
        self,
        broker_type: BrokerType,
        symbol: str,
        success: bool,
        execution_time: float,
        error: Optional[str] = None
    ):
        """Record execution statistics"""
        execution_record = {
            "timestamp": datetime.now(),
            "broker": broker_type.value,
            "symbol": symbol,
            "success": success,
            "execution_time": execution_time,
            "error": error
        }

        self.execution_stats[broker_type.value].append(execution_record)

        # Keep only last 1000 records per broker
        if len(self.execution_stats[broker_type.value]) > 1000:
            self.execution_stats[broker_type.value] = self.execution_stats[broker_type.value][-1000:]
        
        # Alert on execution failure
        if not success:
            self._send_alert(
                AlertLevel.WARNING,
                f"Trade execution failed for {symbol}",
                {"broker": broker_type.value, "symbol": symbol, "error": error}
            )

    def get_execution_stats(
        self,
        broker_type: Optional[BrokerType] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict:
        """
        Get execution statistics

        Args:
            broker_type: Filter by broker type (None for all)
            time_window: Time window to analyze (None for all time)

        Returns:
            Statistics dict
        """
        brokers_to_check = [broker_type] if broker_type else list(self.brokers.keys())

        stats = {}

        for bt in brokers_to_check:
            records = self.execution_stats[bt.value]

            if time_window:
                cutoff = datetime.now() - time_window
                records = [r for r in records if r["timestamp"] >= cutoff]

            if not records:
                stats[bt.value] = {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "success_rate": 0,
                    "avg_execution_time": 0
                }
                continue

            total = len(records)
            success = sum(1 for r in records if r["success"])
            failed = total - success
            avg_time = sum(r["execution_time"] for r in records) / total

            stats[bt.value] = {
                "total": total,
                "success": success,
                "failed": failed,
                "success_rate": (success / total * 100) if total > 0 else 0,
                "avg_execution_time": avg_time,
                "min_execution_time": min(r["execution_time"] for r in records),
                "max_execution_time": max(r["execution_time"] for r in records)
            }

        return stats

    def get_health_summary(self) -> Dict:
        """Get overall health summary"""
        summary = {
            "brokers": {},
            "overall_status": "healthy",
            "total_brokers": len(self.brokers),
            "healthy_brokers": 0,
            "unhealthy_brokers": 0,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_health_checks": self.total_health_checks,
            "total_alerts": self.total_alerts
        }

        for broker_type, status in self.broker_status.items():
            broker_summary = {
                "status": status["status"],
                "last_check": status["last_check"].isoformat() if status["last_check"] else None,
                "response_time": status["response_time"],
                "error_count": status["error_count"],
                "consecutive_failures": status["consecutive_failures"],
                "last_error": status["last_error"],
                "circuit_breaker_open": self._circuit_breaker.get(broker_type, {}).get("open", False)
            }

            summary["brokers"][broker_type.value] = broker_summary

            if status["status"] == "healthy":
                summary["healthy_brokers"] += 1
            else:
                summary["unhealthy_brokers"] += 1

        if summary["unhealthy_brokers"] > 0:
            summary["overall_status"] = "degraded"
        if summary["unhealthy_brokers"] == summary["total_brokers"] and summary["total_brokers"] > 0:
            summary["overall_status"] = "unhealthy"

        # Add execution stats
        summary["execution_stats"] = self.get_execution_stats(
            time_window=timedelta(hours=24)
        )

        return summary
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent alerts"""
        return self.alert_history[-limit:]

    def check_rate_limits(self, broker_type: BrokerType) -> Dict:
        """
        Check API rate limit status (if available)

        Args:
            broker_type: Broker type

        Returns:
            Rate limit status
        """
        # This is a placeholder - actual implementation depends on broker API
        # Most brokers don't expose rate limit info directly
        return {
            "status": "unknown",
            "message": "Rate limit checking not implemented for this broker"
        }

    def should_pause_trading(self, broker_type: BrokerType) -> bool:
        """
        Determine if trading should be paused due to health issues

        Args:
            broker_type: Broker type

        Returns:
            True if trading should be paused
        """
        if broker_type not in self.broker_status:
            return True
        
        # Check circuit breaker
        cb = self._circuit_breaker.get(broker_type, {})
        if cb.get("open"):
            return True

        status = self.broker_status[broker_type]

        # Pause if broker is unhealthy
        if status["status"] == "error":
            return True

        # Pause if too many consecutive failures
        if status["consecutive_failures"] >= 3:
            return True

        # Pause if response time is too high
        if status["response_time"] and status["response_time"] > 10.0:
            return True

        return False
    
    # ==================== WATCHDOG THREAD ====================
    
    def start_monitoring(self):
        """Start the watchdog monitoring thread"""
        if self._is_running:
            return
        
        self._is_running = True
        self._stop_event.clear()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()
        logger.info("Health monitoring watchdog started")
    
    def stop_monitoring(self):
        """Stop the watchdog monitoring thread"""
        self._is_running = False
        self._stop_event.set()
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=10)
        logger.info("Health monitoring watchdog stopped")
    
    def _watchdog_loop(self):
        """Main watchdog loop"""
        while self._is_running and not self._stop_event.is_set():
            try:
                # Check all brokers
                self.check_all_brokers()
                
            except Exception as e:
                logger.error(f"Error in watchdog loop: {e}")
                self._send_alert(
                    AlertLevel.ERROR,
                    f"Watchdog error: {e}",
                    {"error": str(e)}
                )
            
            # Wait for next check
            self._stop_event.wait(self.check_interval)
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        return self._is_running


def create_health_monitor(
    check_interval: int = 60,
    auto_start: bool = False,
    on_alert: Callable = None
) -> HealthMonitor:
    """Create health monitor instance"""
    return HealthMonitor(
        check_interval=check_interval,
        auto_start=auto_start,
        on_alert=on_alert
    )

