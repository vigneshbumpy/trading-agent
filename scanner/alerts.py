"""
Alert System - Email + Desktop notifications
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import datetime

from .config import ScannerConfig
from .parallel_analyzer import AnalysisResult


class AlertManager:
    """Manages alerts via Email and Desktop notifications"""

    def __init__(self, config: ScannerConfig):
        self.config = config
        self.alerts = config.alerts

    def send_desktop_notification(self, title: str, message: str):
        """Send desktop notification (cross-platform)"""
        if not self.alerts.desktop_enabled:
            return

        try:
            # Try plyer first (cross-platform)
            from plyer import notification
            notification.notify(
                title=title,
                message=message[:256],  # Limit message length
                app_name="Stock Scanner",
                timeout=10
            )
        except ImportError:
            # Fallback to OS-specific
            try:
                import platform
                if platform.system() == "Darwin":  # macOS
                    os.system(f'''osascript -e 'display notification "{message[:100]}" with title "{title}"' ''')
                elif platform.system() == "Linux":
                    os.system(f'notify-send "{title}" "{message[:100]}"')
            except:
                pass

    def send_email(self, subject: str, body: str):
        """Send email notification"""
        if not self.alerts.email_enabled or not self.alerts.email_recipients:
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.alerts.email_sender
            msg['To'] = ', '.join(self.alerts.email_recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.alerts.email_smtp_server, self.alerts.email_smtp_port) as server:
                server.starttls()
                server.login(self.alerts.email_sender, self.alerts.email_password)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Email failed: {e}")
            return False

    def format_alert_message(self, results: List[AnalysisResult]) -> str:
        """Format results into alert message"""
        buys = [r for r in results if r.signal == 'BUY']

        if not buys:
            return ""

        msg = f"Stock Scanner Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        msg += f"Found {len(buys)} BUY signal(s):\n\n"

        for r in buys:
            msg += f"+ {r.symbol} ({r.confidence:.0f}% confidence)\n"
            msg += f"  {r.action_recommendation}\n"
            msg += f"  Value: {r.value_analysis}\n"
            msg += f"  News: {r.news_analysis}\n\n"

        return msg

    def send_alerts(self, results: List[AnalysisResult]):
        """Send all configured alerts"""
        buys = [r for r in results if r.signal == 'BUY']

        if not buys:
            print("No BUY signals to alert")
            return

        # Desktop notification
        if self.alerts.desktop_enabled:
            symbols = ", ".join([r.symbol for r in buys[:5]])
            title = f"BUY Signal: {len(buys)} stock(s)"
            message = f"Stocks: {symbols}"
            self.send_desktop_notification(title, message)
            print(f"Desktop notification sent")

        # Email
        if self.alerts.email_enabled:
            subject = f"Stock Scanner: {len(buys)} BUY Signal(s) - {datetime.now().strftime('%m/%d %H:%M')}"
            body = self.format_alert_message(results)
            if self.send_email(subject, body):
                print(f"Email sent to {len(self.alerts.email_recipients)} recipient(s)")

        print(f"Alerts sent for {len(buys)} BUY signals")
