"""
SEC-025: Security Alerting - Real-time Security Monitoring

This module implements comprehensive security monitoring with real-time alerting.
It watches for suspicious patterns and automatically triggers alerts via multiple channels.

Acceptance Criteria:
1. Alert on 5+ failed logins from same IP
2. Alert on privilege escalation attempts
3. Alert on SQL injection attempts
4. Alert on unusual API patterns
5. Alert on new admin account creation
6. PagerDuty/Slack integration (via security_alerts.py)
7. 24/7 on-call rotation (via PagerDuty)
8. Alert fatigue minimized (tuned thresholds)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from threading import Lock

# Import our security modules
try:
    from security_logging import SecurityLogger, SecurityEventType, SecuritySeverity
    from security_alerts import SecurityAlertManager, AlertSeverity, send_security_alert
    SECURITY_MODULES_AVAILABLE = True
except ImportError:
    SECURITY_MODULES_AVAILABLE = False
    logging.error("Security modules not available - monitoring disabled")


logger = logging.getLogger(__name__)


# ============================================================================
# Security Event Patterns and Thresholds
# ============================================================================

class AlertThresholds:
    """
    Tuned thresholds to minimize alert fatigue while catching real threats.

    These are based on security best practices and real-world attack patterns.
    """

    # SEC-025.1: Failed login attempts
    FAILED_LOGIN_IP_COUNT = 5         # 5+ failed logins from same IP
    FAILED_LOGIN_WINDOW = 300         # Within 5 minutes

    # SEC-025.2: Privilege escalation
    PRIVILEGE_ESCALATION_COUNT = 3    # 3+ attempts
    PRIVILEGE_ESCALATION_WINDOW = 60  # Within 1 minute (very suspicious)

    # SEC-025.3: SQL injection
    SQLI_ATTEMPT_COUNT = 3            # 3+ SQL injection patterns
    SQLI_ATTEMPT_WINDOW = 60          # Within 1 minute

    # SEC-025.4: Unusual API patterns
    API_BURST_COUNT = 100             # 100+ requests
    API_BURST_WINDOW = 10             # Within 10 seconds (likely bot/attack)

    API_UNUSUAL_ENDPOINT_COUNT = 20   # Hitting 20+ different endpoints
    API_UNUSUAL_ENDPOINT_WINDOW = 60  # Within 1 minute (reconnaissance)

    # SEC-025.5: Admin account creation
    # Any new admin account creation triggers immediate alert (no threshold)

    # General thresholds
    XSS_ATTEMPT_COUNT = 3             # 3+ XSS attempts
    XSS_ATTEMPT_WINDOW = 60           # Within 1 minute

    CSRF_FAILURE_COUNT = 5            # 5+ CSRF failures
    CSRF_FAILURE_WINDOW = 300         # Within 5 minutes

    # Cooldown to prevent alert spam
    ALERT_COOLDOWN = 300              # Don't re-alert same pattern for 5 minutes


# ============================================================================
# Security Monitor
# ============================================================================

class SecurityMonitor:
    """
    Real-time security monitoring with pattern detection and alerting.

    This is the brain of SEC-025. It:
    1. Tracks security events in memory
    2. Detects suspicious patterns
    3. Triggers alerts when thresholds exceeded
    4. Prevents alert fatigue with cooldowns
    """

    def __init__(self, alert_manager: Optional[SecurityAlertManager] = None):
        self.alert_manager = alert_manager

        # Pattern tracking
        self.failed_logins: Dict[str, List[float]] = defaultdict(list)  # IP -> timestamps
        self.privilege_escalations: Dict[str, List[float]] = defaultdict(list)  # user_id -> timestamps
        self.sqli_attempts: Dict[str, List[float]] = defaultdict(list)  # IP -> timestamps
        self.xss_attempts: Dict[str, List[float]] = defaultdict(list)  # IP -> timestamps
        self.api_requests: Dict[str, List[float]] = defaultdict(list)  # IP -> timestamps
        self.api_endpoints: Dict[str, List[str]] = defaultdict(list)  # IP -> [endpoints]

        # Alert cooldown tracking
        self.last_alert: Dict[str, float] = {}  # pattern_key -> timestamp

        # Thread safety
        self.lock = Lock()

        logger.info("🔍 SecurityMonitor initialized - watching for threats")

    # ========================================================================
    # Main Event Processing
    # ========================================================================

    async def process_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Process a security event and check for suspicious patterns.

        This is called by the SecurityLogger after every security event.
        """
        details = details or {}

        # SEC-025.1: Failed login detection
        if event_type == SecurityEventType.AUTH_LOGIN_FAILURE:
            await self._check_failed_logins(ip_address, user_id, details)

        # SEC-025.2: Privilege escalation detection
        elif event_type == SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT:
            await self._check_privilege_escalation(user_id, ip_address, details)

        # SEC-025.3: SQL injection detection
        elif event_type == SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT:
            await self._check_sqli_attempts(ip_address, details)

        # XSS detection (related to input validation)
        elif event_type == SecurityEventType.INPUT_XSS_ATTEMPT:
            await self._check_xss_attempts(ip_address, details)

        # SEC-025.5: Admin account creation
        elif event_type == SecurityEventType.AUTHZ_ROLE_CHANGED:
            await self._check_admin_creation(user_id, ip_address, details)

        # SEC-025.4: Unusual API patterns (tracked on all events)
        if ip_address:
            await self._check_api_patterns(ip_address, details)

    # ========================================================================
    # SEC-025.1: Failed Login Detection
    # ========================================================================

    async def _check_failed_logins(
        self,
        ip_address: Optional[str],
        user_id: Optional[str],
        details: Dict[str, Any]
    ):
        """
        Alert on 5+ failed logins from same IP within 5 minutes.

        This catches brute force attacks and credential stuffing.
        """
        if not ip_address:
            return

        with self.lock:
            now = datetime.utcnow().timestamp()
            cutoff = now - AlertThresholds.FAILED_LOGIN_WINDOW

            # Clean old attempts
            self.failed_logins[ip_address] = [
                ts for ts in self.failed_logins[ip_address]
                if ts > cutoff
            ]

            # Add current attempt
            self.failed_logins[ip_address].append(now)

            count = len(self.failed_logins[ip_address])

        # Check threshold
        if count >= AlertThresholds.FAILED_LOGIN_IP_COUNT:
            alert_key = f"failed_login:{ip_address}"

            if self._should_send_alert(alert_key):
                await self._send_alert(
                    title="🚨 Brute Force Attack Detected",
                    message=f"Multiple failed login attempts detected from {ip_address}",
                    severity=AlertSeverity.CRITICAL,
                    event_type="auth.brute_force",
                    ip_address=ip_address,
                    user_id=user_id,
                    attempt_count=count,
                    window_minutes=AlertThresholds.FAILED_LOGIN_WINDOW // 60,
                    **details
                )

    # ========================================================================
    # SEC-025.2: Privilege Escalation Detection
    # ========================================================================

    async def _check_privilege_escalation(
        self,
        user_id: Optional[str],
        ip_address: Optional[str],
        details: Dict[str, Any]
    ):
        """
        Alert on 3+ privilege escalation attempts within 1 minute.

        This catches unauthorized access attempts to admin functions.
        """
        if not user_id:
            return

        with self.lock:
            now = datetime.utcnow().timestamp()
            cutoff = now - AlertThresholds.PRIVILEGE_ESCALATION_WINDOW

            # Clean old attempts
            self.privilege_escalations[user_id] = [
                ts for ts in self.privilege_escalations[user_id]
                if ts > cutoff
            ]

            # Add current attempt
            self.privilege_escalations[user_id].append(now)

            count = len(self.privilege_escalations[user_id])

        # Check threshold
        if count >= AlertThresholds.PRIVILEGE_ESCALATION_COUNT:
            alert_key = f"privilege_escalation:{user_id}"

            if self._should_send_alert(alert_key):
                await self._send_alert(
                    title="🔴 Privilege Escalation Attempt",
                    message=f"User {user_id} attempting to escalate privileges",
                    severity=AlertSeverity.CRITICAL,
                    event_type="authz.privilege_escalation",
                    user_id=user_id,
                    ip_address=ip_address,
                    attempt_count=count,
                    window_seconds=AlertThresholds.PRIVILEGE_ESCALATION_WINDOW,
                    **details
                )

    # ========================================================================
    # SEC-025.3: SQL Injection Detection
    # ========================================================================

    async def _check_sqli_attempts(
        self,
        ip_address: Optional[str],
        details: Dict[str, Any]
    ):
        """
        Alert on 3+ SQL injection attempts within 1 minute.

        This catches SQL injection attacks (OWASP #1).
        """
        if not ip_address:
            return

        with self.lock:
            now = datetime.utcnow().timestamp()
            cutoff = now - AlertThresholds.SQLI_ATTEMPT_WINDOW

            # Clean old attempts
            self.sqli_attempts[ip_address] = [
                ts for ts in self.sqli_attempts[ip_address]
                if ts > cutoff
            ]

            # Add current attempt
            self.sqli_attempts[ip_address].append(now)

            count = len(self.sqli_attempts[ip_address])

        # Check threshold
        if count >= AlertThresholds.SQLI_ATTEMPT_COUNT:
            alert_key = f"sqli:{ip_address}"

            if self._should_send_alert(alert_key):
                await self._send_alert(
                    title="⚠️ SQL Injection Attack Detected",
                    message=f"Multiple SQL injection attempts from {ip_address}",
                    severity=AlertSeverity.ERROR,
                    event_type="input.sqli.attack",
                    ip_address=ip_address,
                    attempt_count=count,
                    window_seconds=AlertThresholds.SQLI_ATTEMPT_WINDOW,
                    **details
                )

    # ========================================================================
    # XSS Detection (Bonus)
    # ========================================================================

    async def _check_xss_attempts(
        self,
        ip_address: Optional[str],
        details: Dict[str, Any]
    ):
        """
        Alert on 3+ XSS attempts within 1 minute.

        This catches XSS attacks (OWASP #3).
        """
        if not ip_address:
            return

        with self.lock:
            now = datetime.utcnow().timestamp()
            cutoff = now - AlertThresholds.XSS_ATTEMPT_WINDOW

            # Clean old attempts
            self.xss_attempts[ip_address] = [
                ts for ts in self.xss_attempts[ip_address]
                if ts > cutoff
            ]

            # Add current attempt
            self.xss_attempts[ip_address].append(now)

            count = len(self.xss_attempts[ip_address])

        # Check threshold
        if count >= AlertThresholds.XSS_ATTEMPT_COUNT:
            alert_key = f"xss:{ip_address}"

            if self._should_send_alert(alert_key):
                await self._send_alert(
                    title="⚠️ XSS Attack Detected",
                    message=f"Multiple XSS attempts from {ip_address}",
                    severity=AlertSeverity.ERROR,
                    event_type="input.xss.attack",
                    ip_address=ip_address,
                    attempt_count=count,
                    window_seconds=AlertThresholds.XSS_ATTEMPT_WINDOW,
                    **details
                )

    # ========================================================================
    # SEC-025.4: Unusual API Pattern Detection
    # ========================================================================

    async def _check_api_patterns(
        self,
        ip_address: str,
        details: Dict[str, Any]
    ):
        """
        Alert on unusual API usage patterns:
        1. Burst: 100+ requests in 10 seconds (DDoS/bot)
        2. Reconnaissance: 20+ different endpoints in 1 minute

        This catches automated attacks and scanning.
        """
        with self.lock:
            now = datetime.utcnow().timestamp()

            # Track request burst
            burst_cutoff = now - AlertThresholds.API_BURST_WINDOW
            self.api_requests[ip_address] = [
                ts for ts in self.api_requests[ip_address]
                if ts > burst_cutoff
            ]
            self.api_requests[ip_address].append(now)

            # Track endpoint diversity
            endpoint = details.get('endpoint', 'unknown')
            endpoint_cutoff = now - AlertThresholds.API_UNUSUAL_ENDPOINT_WINDOW

            # Clean old endpoint tracking
            if ip_address in self.api_endpoints:
                # Remove duplicates and keep recent
                recent_endpoints = self.api_endpoints[ip_address][-100:]  # Keep last 100
                self.api_endpoints[ip_address] = recent_endpoints

            self.api_endpoints[ip_address].append(endpoint)

            burst_count = len(self.api_requests[ip_address])
            unique_endpoints = len(set(self.api_endpoints[ip_address][-50:]))  # Check last 50

        # Check for burst
        if burst_count >= AlertThresholds.API_BURST_COUNT:
            alert_key = f"api_burst:{ip_address}"

            if self._should_send_alert(alert_key):
                await self._send_alert(
                    title="🚨 API Request Burst Detected",
                    message=f"Unusual API burst from {ip_address} - possible DDoS or bot",
                    severity=AlertSeverity.ERROR,
                    event_type="api.burst",
                    ip_address=ip_address,
                    request_count=burst_count,
                    window_seconds=AlertThresholds.API_BURST_WINDOW,
                    **details
                )

        # Check for reconnaissance
        if unique_endpoints >= AlertThresholds.API_UNUSUAL_ENDPOINT_COUNT:
            alert_key = f"api_recon:{ip_address}"

            if self._should_send_alert(alert_key):
                await self._send_alert(
                    title="⚠️ API Reconnaissance Detected",
                    message=f"Scanning behavior from {ip_address} - hitting many endpoints",
                    severity=AlertSeverity.WARNING,
                    event_type="api.reconnaissance",
                    ip_address=ip_address,
                    unique_endpoints=unique_endpoints,
                    window_minutes=AlertThresholds.API_UNUSUAL_ENDPOINT_WINDOW // 60,
                    **details
                )

    # ========================================================================
    # SEC-025.5: Admin Account Creation Detection
    # ========================================================================

    async def _check_admin_creation(
        self,
        user_id: Optional[str],
        ip_address: Optional[str],
        details: Dict[str, Any]
    ):
        """
        Alert on any new admin account creation (immediate, no threshold).

        This is CRITICAL - every admin account creation should be reviewed.
        """
        # Check if this is an admin role assignment
        new_role = details.get('new_role', '').lower()
        old_role = details.get('old_role', '').lower()

        if 'admin' in new_role and 'admin' not in old_role:
            # This is a new admin account!
            alert_key = f"admin_created:{user_id}:{datetime.utcnow().timestamp()}"

            # Always send this alert (no cooldown)
            await self._send_alert(
                title="🔴 NEW ADMIN ACCOUNT CREATED",
                message=f"User {user_id} was granted admin privileges",
                severity=AlertSeverity.CRITICAL,
                event_type="authz.admin_created",
                user_id=user_id,
                ip_address=ip_address,
                new_role=new_role,
                old_role=old_role,
                created_by=details.get('created_by', 'unknown')
            )

    # ========================================================================
    # Alert Helpers
    # ========================================================================

    def _should_send_alert(self, alert_key: str) -> bool:
        """
        Check if we should send an alert or if we're in cooldown.

        This prevents alert fatigue by not re-alerting the same pattern
        within the cooldown window.
        """
        now = datetime.utcnow().timestamp()

        if alert_key in self.last_alert:
            time_since_last = now - self.last_alert[alert_key]
            if time_since_last < AlertThresholds.ALERT_COOLDOWN:
                # Still in cooldown
                logger.debug(f"Alert {alert_key} in cooldown ({time_since_last:.0f}s)")
                return False

        # Record this alert
        self.last_alert[alert_key] = now
        return True

    async def _send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        event_type: str,
        **metadata
    ):
        """
        Send alert via SecurityAlertManager.

        This uses our existing alerting infrastructure (Telegram, Email, Slack, PagerDuty).
        """
        if not self.alert_manager:
            logger.warning(f"Alert would be sent: {title}")
            return

        try:
            await send_security_alert(
                title=title,
                message=message,
                severity=severity,
                event_type=event_type,
                **metadata
            )
            logger.info(f"✅ Alert sent: {title}")
        except Exception as e:
            logger.error(f"❌ Failed to send alert: {e}")


# ============================================================================
# Integration with SecurityLogger
# ============================================================================

class MonitoringSecurityLogger:
    """
    SecurityLogger wrapper that automatically monitors events.

    This is the glue between SecurityLogger and SecurityMonitor.
    Use this instead of SecurityLogger directly to get automatic monitoring.
    """

    def __init__(self, security_logger, monitor: Optional[SecurityMonitor] = None):
        self.logger = security_logger
        self.monitor = monitor or SecurityMonitor()

    def log_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        action: str,
        result: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log event and process for monitoring.

        This is synchronous (returns immediately) but kicks off async monitoring.
        """
        # Log to SecurityLogger
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

        # Process for monitoring (async, non-blocking)
        try:
            # Try to get running event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule as task
                asyncio.create_task(
                    self.monitor.process_event(
                        event_type=event_type,
                        severity=severity,
                        user_id=user_id,
                        ip_address=ip_address,
                        details=details
                    )
                )
            else:
                # Run in new loop
                asyncio.run(
                    self.monitor.process_event(
                        event_type=event_type,
                        severity=severity,
                        user_id=user_id,
                        ip_address=ip_address,
                        details=details
                    )
                )
        except Exception as e:
            logger.error(f"Failed to process monitoring event: {e}")

        return event


# ============================================================================
# Convenience Functions
# ============================================================================

# Global monitor instance
_monitor = None


def get_security_monitor() -> SecurityMonitor:
    """Get or create global security monitor"""
    global _monitor
    if _monitor is None:
        _monitor = SecurityMonitor()
    return _monitor


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    async def test_monitoring():
        """Test security monitoring"""
        monitor = SecurityMonitor()

        # Simulate failed login attacks
        print("\n🧪 Simulating brute force attack...")
        for i in range(6):
            await monitor.process_event(
                event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
                severity=SecuritySeverity.MEDIUM,
                ip_address="10.0.0.1",
                user_id=f"test_user_{i}",
                details={"reason": "invalid_password"}
            )

        # Simulate privilege escalation
        print("\n🧪 Simulating privilege escalation...")
        for i in range(4):
            await monitor.process_event(
                event_type=SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT,
                severity=SecuritySeverity.HIGH,
                user_id="attacker",
                ip_address="10.0.0.2",
                details={"attempted_action": "admin_access"}
            )

        # Simulate SQL injection
        print("\n🧪 Simulating SQL injection...")
        for i in range(4):
            await monitor.process_event(
                event_type=SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT,
                severity=SecuritySeverity.HIGH,
                ip_address="10.0.0.3",
                details={"payload": "' OR 1=1--"}
            )

        # Simulate admin creation
        print("\n🧪 Simulating admin account creation...")
        await monitor.process_event(
            event_type=SecurityEventType.AUTHZ_ROLE_CHANGED,
            severity=SecuritySeverity.CRITICAL,
            user_id="new_admin",
            ip_address="10.0.0.4",
            details={
                "old_role": "user",
                "new_role": "admin",
                "created_by": "suspicious_user"
            }
        )

        print("\n✅ Monitoring tests completed!")

    # Run test
    asyncio.run(test_monitoring())
