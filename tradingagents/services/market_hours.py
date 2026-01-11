"""
Market hours service for Indian, US, and Crypto markets
"""

from datetime import datetime, time
from typing import Dict, Optional
import pytz
from dashboard.multiuser.brokers.unified_broker import Market


class MarketHoursService:
    """Service to check if markets are open"""

    # Market timezones
    IST = pytz.timezone('Asia/Kolkata')
    EST = pytz.timezone('US/Eastern')
    UTC = pytz.UTC

    # Market hours (local time)
    INDIA_MARKET_OPEN = time(9, 15)  # 9:15 AM IST
    INDIA_MARKET_CLOSE = time(15, 30)  # 3:30 PM IST

    US_MARKET_OPEN = time(9, 30)  # 9:30 AM EST
    US_MARKET_CLOSE = time(16, 0)  # 4:00 PM EST
    US_PRE_MARKET_OPEN = time(4, 0) # 4:00 AM EST

    # Weekends
    WEEKEND_DAYS = [5, 6]  # Saturday, Sunday

    @staticmethod
    def is_market_open(market: Market, check_time: Optional[datetime] = None) -> bool:
        """
        Check if market is currently open
        """
        if check_time is None:
            check_time = datetime.now(pytz.UTC)

        # Crypto markets are always open (24/7)
        if market == Market.CRYPTO:
            return True

        # Check if it's a weekend
        if check_time.weekday() in MarketHoursService.WEEKEND_DAYS:
            return False

        if market in [Market.INDIA_NSE, Market.INDIA_BSE]:
            return MarketHoursService._is_indian_market_open(check_time)
        elif market in [Market.US_NYSE, Market.US_NASDAQ, Market.US_AMEX]:
            return MarketHoursService._is_us_market_open(check_time)

        return False

    @staticmethod
    def is_pre_market(market: Market, check_time: Optional[datetime] = None) -> bool:
        """Check if it is pre-market hours"""
        if check_time is None:
            check_time = datetime.now(pytz.UTC)

        if check_time.weekday() in MarketHoursService.WEEKEND_DAYS:
            return False

        if market in [Market.US_NYSE, Market.US_NASDAQ, Market.US_AMEX]:
            est_time = check_time.astimezone(MarketHoursService.EST)
            current_time = est_time.time()
            return MarketHoursService.US_PRE_MARKET_OPEN <= current_time < MarketHoursService.US_MARKET_OPEN
        
        return False

    @staticmethod
    def _is_indian_market_open(check_time: datetime) -> bool:
        """Check if Indian market is open"""
        # Convert to IST
        ist_time = check_time.astimezone(MarketHoursService.IST)
        current_time = ist_time.time()

        # Check if within market hours
        return MarketHoursService.INDIA_MARKET_OPEN <= current_time <= MarketHoursService.INDIA_MARKET_CLOSE

    @staticmethod
    def _is_us_market_open(check_time: datetime) -> bool:
        """Check if US market is open"""
        # Convert to EST
        est_time = check_time.astimezone(MarketHoursService.EST)
        current_time = est_time.time()

        # Check if within market hours
        return MarketHoursService.US_MARKET_OPEN <= current_time <= MarketHoursService.US_MARKET_CLOSE

    @staticmethod
    def get_market_status(market: Market) -> Dict:
        """
        Get detailed market status

        Args:
            market: Market enum

        Returns:
            Dict with market status information
        """
        now = datetime.now(pytz.UTC)
        is_open = MarketHoursService.is_market_open(market, now)

        status = {
            "market": market.value,
            "is_open": is_open,
            "current_time": now.isoformat(),
            "timezone": "UTC"
        }

        if market == Market.CRYPTO:
            status.update({
                "hours": "24/7",
                "next_open": None,
                "next_close": None
            })
        elif market in [Market.INDIA_NSE, Market.INDIA_BSE]:
            ist_now = now.astimezone(MarketHoursService.IST)
            status.update({
                "hours": f"{MarketHoursService.INDIA_MARKET_OPEN.strftime('%H:%M')} - {MarketHoursService.INDIA_MARKET_CLOSE.strftime('%H:%M')} IST",
                "local_time": ist_now.isoformat(),
                "timezone": "IST"
            })
        elif market in [Market.US_NYSE, Market.US_NASDAQ, Market.US_AMEX]:
            est_now = now.astimezone(MarketHoursService.EST)
            status.update({
                "hours": f"{MarketHoursService.US_MARKET_OPEN.strftime('%H:%M')} - {MarketHoursService.US_MARKET_CLOSE.strftime('%H:%M')} EST",
                "local_time": est_now.isoformat(),
                "timezone": "EST"
            })

        return status

    @staticmethod
    def get_next_market_open(market: Market) -> Optional[datetime]:
        """
        Get next market open time

        Args:
            market: Market enum

        Returns:
            Next market open datetime (UTC) or None if crypto
        """
        if market == Market.CRYPTO:
            return None  # Always open

        now = datetime.now(pytz.UTC)

        if market in [Market.INDIA_NSE, Market.INDIA_BSE]:
            return MarketHoursService._get_next_indian_market_open(now)
        elif market in [Market.US_NYSE, Market.US_NASDAQ, Market.US_AMEX]:
            return MarketHoursService._get_next_us_market_open(now)

        return None

    @staticmethod
    def _get_next_indian_market_open(now: datetime) -> datetime:
        """Get next Indian market open time"""
        ist_now = now.astimezone(MarketHoursService.IST)
        today_open = datetime.combine(ist_now.date(), MarketHoursService.INDIA_MARKET_OPEN)
        today_open = MarketHoursService.IST.localize(today_open)

        # If market already closed today, get tomorrow
        if ist_now.time() > MarketHoursService.INDIA_MARKET_CLOSE:
            from datetime import timedelta
            tomorrow = ist_now.date() + timedelta(days=1)
            # Skip weekends
            while tomorrow.weekday() in MarketHoursService.WEEKEND_DAYS:
                tomorrow += timedelta(days=1)
            next_open = datetime.combine(tomorrow, MarketHoursService.INDIA_MARKET_OPEN)
            next_open = MarketHoursService.IST.localize(next_open)
        elif ist_now.time() < MarketHoursService.INDIA_MARKET_OPEN:
            # Market hasn't opened today yet
            next_open = today_open
        else:
            # Market is currently open, return today's open (already passed)
            next_open = today_open

        return next_open.astimezone(pytz.UTC)

    @staticmethod
    def _get_next_us_market_open(now: datetime) -> datetime:
        """Get next US market open time"""
        est_now = now.astimezone(MarketHoursService.EST)
        today_open = datetime.combine(est_now.date(), MarketHoursService.US_MARKET_OPEN)
        today_open = MarketHoursService.EST.localize(today_open)

        # If market already closed today, get tomorrow
        if est_now.time() > MarketHoursService.US_MARKET_CLOSE:
            from datetime import timedelta
            tomorrow = est_now.date() + timedelta(days=1)
            # Skip weekends
            while tomorrow.weekday() in MarketHoursService.WEEKEND_DAYS:
                tomorrow += timedelta(days=1)
            next_open = datetime.combine(tomorrow, MarketHoursService.US_MARKET_OPEN)
            next_open = MarketHoursService.EST.localize(next_open)
        elif est_now.time() < MarketHoursService.US_MARKET_OPEN:
            # Market hasn't opened today yet
            next_open = today_open
        else:
            # Market is currently open, return today's open (already passed)
            next_open = today_open

        return next_open.astimezone(pytz.UTC)

    @staticmethod
    def can_trade_now(market: Market) -> bool:
        """
        Quick check if trading is allowed now

        Args:
            market: Market enum

        Returns:
            True if can trade now
        """
        return MarketHoursService.is_market_open(market)


def is_market_open(market: Market) -> bool:
    """Convenience function to check if market is open"""
    return MarketHoursService.is_market_open(market)
