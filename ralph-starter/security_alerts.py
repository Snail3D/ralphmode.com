"""
SEC-010: Security Alerting System
Real-time alerts for suspicious patterns and critical security events.

Integrations:
- Telegram notifications (primary - we're a Telegram bot!)
- Email alerts
- PagerDuty (for critical incidents)
- Slack webhooks
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

# For Telegram notifications
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# For email notifications
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ============================================================================
# Alert Severity and Channels
# ============================================================================

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"
    SLACK = "slack"
    WEBHOOK = "webhook"


@dataclass
class SecurityAlert:
    """Security alert data structure"""
    title: str
    message: str
    severity: AlertSeverity
    event_type: str
    timestamp: str
    metadata: Dict[str, Any]
    user_id: Optional[str] = None
    ip_address: Optional[str] = None


# ============================================================================
# Alert Manager
# ============================================================================

class SecurityAlertManager:
    """
    Manages security alerts across multiple channels.
    Implements alert routing, throttling, and escalation.
    """

    def __init__(self):
        # Alert configuration
        self.admin_telegram_ids = self._load_admin_ids()
        self.alert_email = os.getenv("SECURITY_ALERT_EMAIL")
        self.pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

        # Telegram bot for alerts
        self.telegram_bot = None
        if TELEGRAM_AVAILABLE:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if token:
                self.telegram_bot = Bot(token=token)

        # Alert throttling (prevent spam)
        self.alert_history: Dict[str, List[float]] = {}
        self.throttle_window = 300  # 5 minutes
        self.max_alerts_per_window = 5

        # Channel routing based on severity
        self.severity_routing = {
            AlertSeverity.INFO: [AlertChannel.TELEGRAM],
            AlertSeverity.WARNING: [AlertChannel.TELEGRAM, AlertChannel.EMAIL],
            AlertSeverity.ERROR: [AlertChannel.TELEGRAM, AlertChannel.EMAIL, AlertChannel.SLACK],
            AlertSeverity.CRITICAL: [AlertChannel.TELEGRAM, AlertChannel.EMAIL,
                                    AlertChannel.SLACK, AlertChannel.PAGERDUTY],
        }

    def _load_admin_ids(self) -> List[int]:
        """Load admin Telegram IDs from environment"""
        admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
        if admin_ids_str:
            return [int(id.strip()) for id in admin_ids_str.split(",")]
        return []

    async def send_alert(self, alert: SecurityAlert):
        """
        Send security alert to appropriate channels based on severity

        Args:
            alert: SecurityAlert object
        """
        # Check throttling
        if self._should_throttle(alert):
            print(f"Alert throttled: {alert.title}")
            return

        # Get channels for this severity
        channels = self.severity_routing.get(alert.severity, [AlertChannel.TELEGRAM])

        # Send to each channel
        tasks = []
        for channel in channels:
            if channel == AlertChannel.TELEGRAM:
                tasks.append(self._send_telegram_alert(alert))
            elif channel == AlertChannel.EMAIL:
                tasks.append(self._send_email_alert(alert))
            elif channel == AlertChannel.SLACK:
                tasks.append(self._send_slack_alert(alert))
            elif channel == AlertChannel.PAGERDUTY:
                tasks.append(self._send_pagerduty_alert(alert))

        # Send all alerts concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _should_throttle(self, alert: SecurityAlert) -> bool:
        """Check if alert should be throttled to prevent spam"""
        alert_key = f"{alert.event_type}:{alert.user_id}:{alert.ip_address}"
        now = datetime.utcnow().timestamp()

        # Clean up old timestamps
        if alert_key in self.alert_history:
            self.alert_history[alert_key] = [
                ts for ts in self.alert_history[alert_key]
                if now - ts < self.throttle_window
            ]
        else:
            self.alert_history[alert_key] = []

        # Check if over threshold
        if len(self.alert_history[alert_key]) >= self.max_alerts_per_window:
            return True

        # Record this alert
        self.alert_history[alert_key].append(now)
        return False

    # ========================================================================
    # Telegram Alerts (Primary channel for Ralph Mode)
    # ========================================================================

    async def _send_telegram_alert(self, alert: SecurityAlert):
        """Send alert to admin Telegram accounts"""
        if not self.telegram_bot or not self.admin_telegram_ids:
            return

        # Format alert message
        message = self._format_telegram_alert(alert)

        # Send to all admins
        for admin_id in self.admin_telegram_ids:
            try:
                await self.telegram_bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except TelegramError as e:
                print(f"Failed to send Telegram alert to {admin_id}: {e}")

    def _format_telegram_alert(self, alert: SecurityAlert) -> str:
        """Format alert for Telegram with emoji and markdown"""
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "🚨",
            AlertSeverity.CRITICAL: "🔴",
        }

        emoji = severity_emoji.get(alert.severity, "🔔")

        msg = f"{emoji} *SECURITY ALERT*\n\n"
        msg += f"*{alert.title}*\n"
        msg += f"Severity: `{alert.severity.value.upper()}`\n"
        msg += f"Event: `{alert.event_type}`\n"
        msg += f"Time: `{alert.timestamp}`\n\n"
        msg += f"{alert.message}\n\n"

        if alert.user_id:
            msg += f"User: `{alert.user_id}`\n"
        if alert.ip_address:
            msg += f"IP: `{alert.ip_address}`\n"

        if alert.metadata:
            msg += f"\n*Details:*\n"
            for key, value in alert.metadata.items():
                msg += f"• {key}: `{value}`\n"

        return msg

    # ========================================================================
    # Email Alerts
    # ========================================================================

    async def _send_email_alert(self, alert: SecurityAlert):
        """Send alert via email"""
        if not self.alert_email:
            return

        try:
            # SMTP configuration
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASSWORD")

            if not smtp_user or not smtp_pass:
                print("SMTP credentials not configured")
                return

            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = self.alert_email
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"

            # HTML body
            html_body = self._format_email_alert(alert)
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()

        except Exception as e:
            print(f"Failed to send email alert: {e}")

    def _format_email_alert(self, alert: SecurityAlert) -> str:
        """Format alert as HTML email"""
        severity_colors = {
            AlertSeverity.INFO: "#3498db",
            AlertSeverity.WARNING: "#f39c12",
            AlertSeverity.ERROR: "#e74c3c",
            AlertSeverity.CRITICAL: "#c0392b",
        }

        color = severity_colors.get(alert.severity, "#95a5a6")

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert-box {{
                    border-left: 4px solid {color};
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .severity {{
                    color: {color};
                    font-weight: bold;
                    font-size: 18px;
                }}
                .metadata {{
                    background-color: #f0f0f0;
                    padding: 10px;
                    margin-top: 10px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="alert-box">
                <h2>{alert.title}</h2>
                <p class="severity">Severity: {alert.severity.value.upper()}</p>
                <p><strong>Event Type:</strong> {alert.event_type}</p>
                <p><strong>Timestamp:</strong> {alert.timestamp}</p>
                <p>{alert.message}</p>

                {f'<p><strong>User ID:</strong> {alert.user_id}</p>' if alert.user_id else ''}
                {f'<p><strong>IP Address:</strong> {alert.ip_address}</p>' if alert.ip_address else ''}

                <div class="metadata">
                    <strong>Additional Details:</strong>
                    <ul>
        """

        for key, value in alert.metadata.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"

        html += """
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    # ========================================================================
    # Slack Alerts
    # ========================================================================

    async def _send_slack_alert(self, alert: SecurityAlert):
        """Send alert to Slack via webhook"""
        if not self.slack_webhook:
            return

        try:
            import aiohttp

            severity_colors = {
                AlertSeverity.INFO: "#3498db",
                AlertSeverity.WARNING: "#f39c12",
                AlertSeverity.ERROR: "#e74c3c",
                AlertSeverity.CRITICAL: "#c0392b",
            }

            payload = {
                "attachments": [
                    {
                        "color": severity_colors.get(alert.severity, "#95a5a6"),
                        "title": alert.title,
                        "text": alert.message,
                        "fields": [
                            {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                            {"title": "Event Type", "value": alert.event_type, "short": True},
                            {"title": "Timestamp", "value": alert.timestamp, "short": False},
                        ],
                        "footer": "Ralph Mode Security",
                        "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                    }
                ]
            }

            # Add user/IP fields if available
            if alert.user_id:
                payload["attachments"][0]["fields"].append(
                    {"title": "User ID", "value": alert.user_id, "short": True}
                )
            if alert.ip_address:
                payload["attachments"][0]["fields"].append(
                    {"title": "IP Address", "value": alert.ip_address, "short": True}
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook, json=payload) as response:
                    if response.status != 200:
                        print(f"Failed to send Slack alert: {response.status}")

        except Exception as e:
            print(f"Failed to send Slack alert: {e}")

    # ========================================================================
    # PagerDuty Alerts (for critical incidents)
    # ========================================================================

    async def _send_pagerduty_alert(self, alert: SecurityAlert):
        """Send critical alert to PagerDuty"""
        if not self.pagerduty_key:
            return

        try:
            import aiohttp

            payload = {
                "routing_key": self.pagerduty_key,
                "event_action": "trigger",
                "payload": {
                    "summary": alert.title,
                    "severity": alert.severity.value,
                    "source": "ralph-mode-security",
                    "timestamp": alert.timestamp,
                    "custom_details": {
                        "message": alert.message,
                        "event_type": alert.event_type,
                        "user_id": alert.user_id,
                        "ip_address": alert.ip_address,
                        **alert.metadata
                    }
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload
                ) as response:
                    if response.status != 202:
                        print(f"Failed to send PagerDuty alert: {response.status}")

        except Exception as e:
            print(f"Failed to send PagerDuty alert: {e}")


# ============================================================================
# Convenience Functions
# ============================================================================

# Global alert manager instance
_alert_manager = None


def get_alert_manager() -> SecurityAlertManager:
    """Get or create global alert manager"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = SecurityAlertManager()
    return _alert_manager


async def send_security_alert(
    title: str,
    message: str,
    severity: AlertSeverity,
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **metadata
):
    """
    Convenience function to send a security alert

    Example:
        await send_security_alert(
            title="SQL Injection Attempt Detected",
            message="Multiple SQL injection attempts from same IP",
            severity=AlertSeverity.CRITICAL,
            event_type="input.sqli.attempt",
            ip_address="10.0.0.1",
            payload="' OR 1=1--",
            field="username"
        )
    """
    alert = SecurityAlert(
        title=title,
        message=message,
        severity=severity,
        event_type=event_type,
        timestamp=datetime.utcnow().isoformat() + 'Z',
        user_id=user_id,
        ip_address=ip_address,
        metadata=metadata
    )

    manager = get_alert_manager()
    await manager.send_alert(alert)


# ============================================================================
# Integration with SecurityLogger
# ============================================================================

class AlertingSecurityLogger:
    """
    SecurityLogger with integrated alerting.
    Automatically sends alerts when suspicious patterns detected.
    """

    def __init__(self, security_logger, alert_manager: Optional[SecurityAlertManager] = None):
        self.logger = security_logger
        self.alert_manager = alert_manager or get_alert_manager()

    async def log_and_alert_if_needed(
        self,
        event_type,
        severity,
        action: str,
        result: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log event and send alert if critical/high severity

        This bridges the SecurityLogger with SecurityAlertManager
        """
        # Log the event
        event = self.logger.log_event(
            event_type=event_type,
            severity=severity,
            action=action,
            result=result,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            details=details
        )

        # Send alert for high/critical events
        if severity.value in ['high', 'critical']:
            alert_severity = AlertSeverity.CRITICAL if severity.value == 'critical' else AlertSeverity.ERROR

            await send_security_alert(
                title=f"Security Event: {event_type.value}",
                message=f"Action '{action}' resulted in '{result}'",
                severity=alert_severity,
                event_type=event_type.value,
                user_id=user_id,
                ip_address=ip_address,
                **(details or {})
            )


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    async def test_alerts():
        """Test alert system"""
        manager = SecurityAlertManager()

        # Test different severity levels
        test_alerts = [
            SecurityAlert(
                title="Test Info Alert",
                message="This is a test info alert",
                severity=AlertSeverity.INFO,
                event_type="test.info",
                timestamp=datetime.utcnow().isoformat() + 'Z',
                metadata={"test": "data"}
            ),
            SecurityAlert(
                title="SQL Injection Detected",
                message="Multiple SQL injection attempts detected from single IP",
                severity=AlertSeverity.CRITICAL,
                event_type="input.sqli.attempt",
                timestamp=datetime.utcnow().isoformat() + 'Z',
                user_id="attacker123",
                ip_address="10.0.0.1",
                metadata={"payload": "' OR 1=1--", "attempts": 5}
            ),
        ]

        for alert in test_alerts:
            print(f"Sending {alert.severity.value} alert...")
            await manager.send_alert(alert)

        print("All test alerts sent!")

    # Run test
    asyncio.run(test_alerts())
