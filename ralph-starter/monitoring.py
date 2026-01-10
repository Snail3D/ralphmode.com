"""
SEC-025: Security Monitoring System
Real-time threat detection and pattern analysis for security events.

Monitors:
- Failed login attempts (5+ from same IP = alert)
- Privilege escalation attempts
- SQL injection attempts
- Unusual API patterns
- New admin account creation
- Brute force attacks
- Rate limiting violations
- Suspicious user behavior

Integrates with SecurityAlertManager for multi-channel alerting.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

# Import alerting system
from security_alerts import (
    SecurityAlertManager,
    AlertSeverity,
    send_security_alert,
    get_alert_manager
)


# ============================================================================
# Threat Detection Patterns
# ============================================================================

class ThreatPattern(Enum):
    """Types of security threats we monitor"""
    FAILED_LOGIN = "auth.failed_login"
    BRUTE_FORCE = "auth.brute_force"
    PRIVILEGE_ESCALATION = "access.privilege_escalation"
    SQL_INJECTION = "input.sqli_attempt"
    XSS_ATTEMPT = "input.xss_attempt"
    UNUSUAL_API_PATTERN = "api.unusual_pattern"
    ADMIN_ACCOUNT_CREATED = "admin.account_created"
    RATE_LIMIT_EXCEEDED = "api.rate_limit_exceeded"
    SUSPICIOUS_BEHAVIOR = "user.suspicious_behavior"
    UNAUTHORIZED_ACCESS = "access.unauthorized"


@dataclass
class SecurityEvent:
    """Security event for analysis"""
    event_type: ThreatPattern
    user_id: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    severity: AlertSeverity = AlertSeverity.WARNING


# ============================================================================
# Security Monitor
# ============================================================================

class SecurityMonitor:
    """
    Real-time security monitoring and threat detection.
    Analyzes patterns and triggers alerts based on tuned thresholds.
    """

    def __init__(self, alert_manager: Optional[SecurityAlertManager] = None):
        self.alert_manager = alert_manager or get_alert_manager()

        # Event tracking for pattern detection
        self.failed_logins: Dict[str, List[datetime]] = defaultdict(list)
        self.api_requests: Dict[str, List[datetime]] = defaultdict(list)
        self.privilege_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.sql_injection_attempts: Dict[str, List[datetime]] = defaultdict(list)

        # Thresholds (tuned to minimize false positives)
        self.FAILED_LOGIN_THRESHOLD = 5  # 5+ failed logins = alert
        self.FAILED_LOGIN_WINDOW = 300  # 5 minutes

        self.BRUTE_FORCE_THRESHOLD = 10  # 10+ attempts = brute force
        self.BRUTE_FORCE_WINDOW = 600  # 10 minutes

        self.API_RATE_THRESHOLD = 100  # 100 requests
        self.API_RATE_WINDOW = 60  # per minute

        self.SQLI_THRESHOLD = 3  # 3+ attempts = definite attack
        self.SQLI_WINDOW = 300  # 5 minutes

        # Admin user IDs (loaded from config)
        self.admin_user_ids = self._load_admin_ids()

        # On-call rotation (for 24/7 coverage)
        self.on_call_schedule = self._load_on_call_schedule()

    def _load_admin_ids(self) -> List[str]:
        """Load admin user IDs from environment"""
        admin_ids = os.getenv("ADMIN_USER_IDS", "")
        if admin_ids:
            return [id.strip() for id in admin_ids.split(",")]
        return []

    def _load_on_call_schedule(self) -> Dict[str, Any]:
        """
        Load 24/7 on-call rotation schedule.
        In production, this would integrate with PagerDuty's schedule API.
        """
        return {
            "enabled": os.getenv("ON_CALL_ROTATION_ENABLED", "true").lower() == "true",
            "primary": os.getenv("ON_CALL_PRIMARY", "security-team"),
            "escalation_timeout": int(os.getenv("ESCALATION_TIMEOUT_MINUTES", "15"))
        }

    # ========================================================================
    # Failed Login Detection
    # ========================================================================

    async def track_failed_login(
        self,
        user_id: Optional[str],
        ip_address: str,
        username: Optional[str] = None,
        reason: str = "invalid_credentials"
    ):
        """
        Track failed login attempt and alert on threshold breach.

        Threshold: 5+ failed logins from same IP in 5 minutes
        """
        now = datetime.utcnow()

        # Track by IP address (more reliable for brute force detection)
        self.failed_logins[ip_address].append(now)

        # Clean old attempts
        self._cleanup_old_events(
            self.failed_logins[ip_address],
            now,
            self.FAILED_LOGIN_WINDOW
        )

        attempt_count = len(self.failed_logins[ip_address])

        # Alert on threshold breach
        if attempt_count >= self.FAILED_LOGIN_THRESHOLD:
            severity = (
                AlertSeverity.CRITICAL if attempt_count >= self.BRUTE_FORCE_THRESHOLD
                else AlertSeverity.ERROR
            )

            attack_type = "Brute Force Attack" if attempt_count >= self.BRUTE_FORCE_THRESHOLD else "Multiple Failed Logins"

            await send_security_alert(
                title=f"{attack_type} Detected",
                message=f"{attempt_count} failed login attempts from {ip_address} in {self.FAILED_LOGIN_WINDOW // 60} minutes",
                severity=severity,
                event_type=ThreatPattern.BRUTE_FORCE.value if attempt_count >= self.BRUTE_FORCE_THRESHOLD else ThreatPattern.FAILED_LOGIN.value,
                ip_address=ip_address,
                user_id=user_id,
                username=username,
                attempt_count=attempt_count,
                reason=reason,
                window_minutes=self.FAILED_LOGIN_WINDOW // 60
            )

    # ========================================================================
    # Privilege Escalation Detection
    # ========================================================================

    async def track_privilege_escalation(
        self,
        user_id: str,
        ip_address: str,
        attempted_action: str,
        current_role: str,
        required_role: str,
        resource: Optional[str] = None
    ):
        """
        Detect and alert on privilege escalation attempts.

        Triggers: Any attempt to perform admin action without admin privileges
        """
        now = datetime.utcnow()

        event_key = f"{user_id}:{attempted_action}"
        self.privilege_attempts[event_key].append(now)

        # Clean old attempts
        self._cleanup_old_events(
            self.privilege_attempts[event_key],
            now,
            300  # 5 minute window
        )

        attempt_count = len(self.privilege_attempts[event_key])

        # Always alert on privilege escalation (high severity threat)
        severity = AlertSeverity.CRITICAL if attempt_count > 1 else AlertSeverity.ERROR

        await send_security_alert(
            title="Privilege Escalation Attempt",
            message=f"User {user_id} attempted to perform admin action '{attempted_action}' without proper privileges",
            severity=severity,
            event_type=ThreatPattern.PRIVILEGE_ESCALATION.value,
            user_id=user_id,
            ip_address=ip_address,
            attempted_action=attempted_action,
            current_role=current_role,
            required_role=required_role,
            resource=resource,
            attempt_count=attempt_count
        )

    # ========================================================================
    # SQL Injection Detection
    # ========================================================================

    async def track_sql_injection(
        self,
        user_id: Optional[str],
        ip_address: str,
        payload: str,
        field: str,
        endpoint: Optional[str] = None
    ):
        """
        Detect and alert on SQL injection attempts.

        Threshold: 3+ attempts from same IP = coordinated attack
        """
        now = datetime.utcnow()

        self.sql_injection_attempts[ip_address].append(now)

        # Clean old attempts
        self._cleanup_old_events(
            self.sql_injection_attempts[ip_address],
            now,
            self.SQLI_WINDOW
        )

        attempt_count = len(self.sql_injection_attempts[ip_address])

        # Alert on ANY SQL injection attempt (zero tolerance)
        severity = AlertSeverity.CRITICAL if attempt_count >= self.SQLI_THRESHOLD else AlertSeverity.ERROR

        await send_security_alert(
            title="SQL Injection Attempt Detected",
            message=f"SQL injection payload detected from {ip_address} in field '{field}'",
            severity=severity,
            event_type=ThreatPattern.SQL_INJECTION.value,
            user_id=user_id,
            ip_address=ip_address,
            payload=payload[:200],  # Truncate for safety
            field=field,
            endpoint=endpoint,
            attempt_count=attempt_count,
            coordinated_attack=attempt_count >= self.SQLI_THRESHOLD
        )

    # ========================================================================
    # Unusual API Pattern Detection
    # ========================================================================

    async def track_api_request(
        self,
        user_id: Optional[str],
        ip_address: str,
        endpoint: str,
        method: str,
        status_code: int
    ):
        """
        Track API requests and detect unusual patterns.

        Patterns detected:
        - Excessive request rate (100+ req/min from single IP)
        - Systematic endpoint scanning (many 404s)
        - Error farming (many 500s)
        """
        now = datetime.utcnow()

        request_key = f"{ip_address}:{user_id}"
        self.api_requests[request_key].append(now)

        # Clean old requests
        self._cleanup_old_events(
            self.api_requests[request_key],
            now,
            self.API_RATE_WINDOW
        )

        request_count = len(self.api_requests[request_key])

        # Alert on excessive rate
        if request_count >= self.API_RATE_THRESHOLD:
            await send_security_alert(
                title="Unusual API Activity Detected",
                message=f"{request_count} API requests from {ip_address} in {self.API_RATE_WINDOW} seconds",
                severity=AlertSeverity.WARNING,
                event_type=ThreatPattern.UNUSUAL_API_PATTERN.value,
                user_id=user_id,
                ip_address=ip_address,
                request_count=request_count,
                endpoint=endpoint,
                method=method,
                window_seconds=self.API_RATE_WINDOW
            )

    # ========================================================================
    # Admin Account Creation
    # ========================================================================

    async def track_admin_creation(
        self,
        creator_user_id: str,
        new_admin_user_id: str,
        new_admin_username: str,
        creator_ip: str
    ):
        """
        Alert on new admin account creation (always alert - critical event).

        This is a high-risk event that should always be monitored.
        """
        await send_security_alert(
            title="New Admin Account Created",
            message=f"Admin account '{new_admin_username}' (ID: {new_admin_user_id}) created by {creator_user_id}",
            severity=AlertSeverity.CRITICAL,
            event_type=ThreatPattern.ADMIN_ACCOUNT_CREATED.value,
            user_id=creator_user_id,
            ip_address=creator_ip,
            new_admin_user_id=new_admin_user_id,
            new_admin_username=new_admin_username,
            action="admin_account_created"
        )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _cleanup_old_events(
        self,
        event_list: List[datetime],
        now: datetime,
        window_seconds: int
    ):
        """Remove events older than the time window"""
        cutoff = now - timedelta(seconds=window_seconds)
        # Remove old events in-place
        while event_list and event_list[0] < cutoff:
            event_list.pop(0)

    # ========================================================================
    # Batch Event Analysis
    # ========================================================================

    async def analyze_security_events(
        self,
        events: List[SecurityEvent]
    ) -> Dict[str, Any]:
        """
        Analyze batch of security events for patterns.
        Returns summary with threat levels and recommendations.
        """
        analysis = {
            "total_events": len(events),
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "high_risk_ips": set(),
            "high_risk_users": set(),
            "recommendations": []
        }

        for event in events:
            # Count by type
            analysis["by_type"][event.event_type.value] += 1

            # Count by severity
            analysis["by_severity"][event.severity.value] += 1

            # Track high-risk actors
            if event.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
                if event.ip_address:
                    analysis["high_risk_ips"].add(event.ip_address)
                if event.user_id:
                    analysis["high_risk_users"].add(event.user_id)

        # Generate recommendations
        if analysis["by_type"][ThreatPattern.FAILED_LOGIN.value] > 10:
            analysis["recommendations"].append(
                "High volume of failed logins detected. Consider implementing CAPTCHA or temporary IP blocks."
            )

        if analysis["by_type"][ThreatPattern.SQL_INJECTION.value] > 0:
            analysis["recommendations"].append(
                "SQL injection attempts detected. Ensure all inputs use parameterized queries."
            )

        if len(analysis["high_risk_ips"]) > 5:
            analysis["recommendations"].append(
                f"Multiple high-risk IPs detected ({len(analysis['high_risk_ips'])}). Consider implementing IP blocklist."
            )

        # Convert sets to lists for JSON serialization
        analysis["high_risk_ips"] = list(analysis["high_risk_ips"])
        analysis["high_risk_users"] = list(analysis["high_risk_users"])

        return dict(analysis)


# ============================================================================
# Integrated Security Monitoring Middleware
# ============================================================================

class SecurityMonitoringMiddleware:
    """
    Middleware that integrates SecurityMonitor with application.
    Automatically tracks and analyzes security events.
    """

    def __init__(self, monitor: Optional[SecurityMonitor] = None):
        self.monitor = monitor or SecurityMonitor()

    async def track_login_attempt(
        self,
        success: bool,
        user_id: Optional[str],
        username: Optional[str],
        ip_address: str,
        reason: Optional[str] = None
    ):
        """Track login attempt (failed or successful)"""
        if not success:
            await self.monitor.track_failed_login(
                user_id=user_id,
                ip_address=ip_address,
                username=username,
                reason=reason or "invalid_credentials"
            )

    async def check_privilege_escalation(
        self,
        user_id: str,
        user_role: str,
        required_role: str,
        action: str,
        ip_address: str,
        resource: Optional[str] = None
    ) -> bool:
        """
        Check if user has required privilege.
        Alert if escalation attempt detected.
        """
        has_privilege = user_role == required_role or user_role == "admin"

        if not has_privilege:
            await self.monitor.track_privilege_escalation(
                user_id=user_id,
                ip_address=ip_address,
                attempted_action=action,
                current_role=user_role,
                required_role=required_role,
                resource=resource
            )

        return has_privilege


# ============================================================================
# Global Monitor Instance
# ============================================================================

_security_monitor = None


def get_security_monitor() -> SecurityMonitor:
    """Get or create global security monitor"""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor


# ============================================================================
# Convenience Functions
# ============================================================================

async def track_failed_login(user_id: Optional[str], ip_address: str, username: Optional[str] = None):
    """Convenience function for tracking failed logins"""
    monitor = get_security_monitor()
    await monitor.track_failed_login(user_id, ip_address, username)


async def track_privilege_escalation(user_id: str, ip_address: str, action: str, current_role: str, required_role: str):
    """Convenience function for tracking privilege escalation"""
    monitor = get_security_monitor()
    await monitor.track_privilege_escalation(user_id, ip_address, action, current_role, required_role)


async def track_sql_injection(user_id: Optional[str], ip_address: str, payload: str, field: str):
    """Convenience function for tracking SQL injection"""
    monitor = get_security_monitor()
    await monitor.track_sql_injection(user_id, ip_address, payload, field)


async def track_api_request(user_id: Optional[str], ip_address: str, endpoint: str, method: str, status_code: int):
    """Convenience function for tracking API requests"""
    monitor = get_security_monitor()
    await monitor.track_api_request(user_id, ip_address, endpoint, method, status_code)


async def track_admin_creation(creator_id: str, new_admin_id: str, new_admin_username: str, creator_ip: str):
    """Convenience function for tracking admin creation"""
    monitor = get_security_monitor()
    await monitor.track_admin_creation(creator_id, new_admin_id, new_admin_username, creator_ip)


# ============================================================================
# SF-002: Health Monitoring System
# ============================================================================
# Continuous health monitoring for:
# - API latency
# - Error rates
# - Queue depth
# - Build success rate
# - Anomaly detection and alerting
# ============================================================================

class HealthStatus(Enum):
    """Overall system health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthMetrics:
    """Current health metrics snapshot"""
    timestamp: datetime
    api_latency_ms: float
    error_rate_percent: float
    queue_depth: int
    build_success_rate_percent: float
    status: HealthStatus
    alerts: List[str] = field(default_factory=list)


class HealthMonitor:
    """
    SF-002: Continuous health monitoring system.

    Monitors:
    - API response times (latency tracking)
    - Error rates (5xx errors, exceptions)
    - Queue depth (pending feedback items)
    - Build success rate (deployment health)

    Alerts on anomalies based on tuned thresholds.
    """

    def __init__(self):
        # API latency tracking
        self.api_response_times: List[float] = []
        self.api_latency_window = 100  # Track last 100 requests

        # Error rate tracking
        self.total_requests = 0
        self.error_count = 0
        self.error_window_start = datetime.utcnow()
        self.error_window_duration = 300  # 5 minutes

        # Queue depth tracking
        self.current_queue_depth = 0
        self.queue_depth_history: List[int] = []

        # Build success tracking
        self.build_attempts = 0
        self.build_successes = 0
        self.build_history: List[bool] = []  # True = success, False = failure
        self.build_history_window = 50  # Track last 50 builds

        # Thresholds for alerting
        self.LATENCY_WARNING_MS = 1000  # 1 second
        self.LATENCY_CRITICAL_MS = 3000  # 3 seconds

        self.ERROR_RATE_WARNING = 5.0  # 5% error rate
        self.ERROR_RATE_CRITICAL = 10.0  # 10% error rate

        self.QUEUE_DEPTH_WARNING = 50
        self.QUEUE_DEPTH_CRITICAL = 100

        self.BUILD_SUCCESS_WARNING = 80.0  # Below 80% success
        self.BUILD_SUCCESS_CRITICAL = 60.0  # Below 60% success

    # ========================================================================
    # API Latency Monitoring
    # ========================================================================

    def track_api_response_time(self, latency_ms: float):
        """
        Track API response time.

        Args:
            latency_ms: Response time in milliseconds
        """
        self.api_response_times.append(latency_ms)

        # Keep only recent measurements
        if len(self.api_response_times) > self.api_latency_window:
            self.api_response_times.pop(0)

    def get_avg_latency(self) -> float:
        """Get average API latency in milliseconds"""
        if not self.api_response_times:
            return 0.0
        return sum(self.api_response_times) / len(self.api_response_times)

    def get_p95_latency(self) -> float:
        """Get 95th percentile API latency"""
        if not self.api_response_times:
            return 0.0
        sorted_times = sorted(self.api_response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]

    # ========================================================================
    # Error Rate Monitoring
    # ========================================================================

    def track_request(self, is_error: bool = False):
        """
        Track API request success/failure.

        Args:
            is_error: True if request resulted in error (5xx, exception)
        """
        now = datetime.utcnow()

        # Reset window if expired
        if (now - self.error_window_start).total_seconds() > self.error_window_duration:
            self.error_window_start = now
            self.total_requests = 0
            self.error_count = 0

        self.total_requests += 1
        if is_error:
            self.error_count += 1

    def get_error_rate(self) -> float:
        """Get current error rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests) * 100

    # ========================================================================
    # Queue Depth Monitoring
    # ========================================================================

    def update_queue_depth(self, depth: int):
        """
        Update current queue depth.

        Args:
            depth: Number of items in queue
        """
        self.current_queue_depth = depth
        self.queue_depth_history.append(depth)

        # Keep last 1000 measurements
        if len(self.queue_depth_history) > 1000:
            self.queue_depth_history.pop(0)

    def get_avg_queue_depth(self) -> float:
        """Get average queue depth"""
        if not self.queue_depth_history:
            return 0.0
        return sum(self.queue_depth_history) / len(self.queue_depth_history)

    # ========================================================================
    # Build Success Rate Monitoring
    # ========================================================================

    def track_build(self, success: bool):
        """
        Track build attempt result.

        Args:
            success: True if build succeeded, False if failed
        """
        self.build_attempts += 1
        if success:
            self.build_successes += 1

        self.build_history.append(success)

        # Keep only recent history
        if len(self.build_history) > self.build_history_window:
            self.build_history.pop(0)

    def get_build_success_rate(self) -> float:
        """Get build success rate as percentage"""
        if not self.build_history:
            return 100.0  # Assume healthy if no data
        successes = sum(1 for success in self.build_history if success)
        return (successes / len(self.build_history)) * 100

    def get_recent_build_failures(self) -> int:
        """Get count of recent consecutive failures"""
        if not self.build_history:
            return 0

        consecutive_failures = 0
        for success in reversed(self.build_history):
            if success:
                break
            consecutive_failures += 1

        return consecutive_failures

    # ========================================================================
    # Anomaly Detection & Alerting
    # ========================================================================

    def check_health(self) -> HealthMetrics:
        """
        Check overall system health and generate alerts.

        Returns:
            HealthMetrics with current status and alerts
        """
        alerts = []
        status = HealthStatus.HEALTHY

        # Check API latency
        avg_latency = self.get_avg_latency()
        p95_latency = self.get_p95_latency()

        if p95_latency >= self.LATENCY_CRITICAL_MS:
            alerts.append(f"CRITICAL: API p95 latency is {p95_latency:.0f}ms (threshold: {self.LATENCY_CRITICAL_MS}ms)")
            status = HealthStatus.CRITICAL
        elif p95_latency >= self.LATENCY_WARNING_MS:
            alerts.append(f"WARNING: API p95 latency is {p95_latency:.0f}ms (threshold: {self.LATENCY_WARNING_MS}ms)")
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED

        # Check error rate
        error_rate = self.get_error_rate()

        if error_rate >= self.ERROR_RATE_CRITICAL:
            alerts.append(f"CRITICAL: Error rate is {error_rate:.1f}% (threshold: {self.ERROR_RATE_CRITICAL}%)")
            status = HealthStatus.CRITICAL
        elif error_rate >= self.ERROR_RATE_WARNING:
            alerts.append(f"WARNING: Error rate is {error_rate:.1f}% (threshold: {self.ERROR_RATE_WARNING}%)")
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED

        # Check queue depth
        if self.current_queue_depth >= self.QUEUE_DEPTH_CRITICAL:
            alerts.append(f"CRITICAL: Queue depth is {self.current_queue_depth} (threshold: {self.QUEUE_DEPTH_CRITICAL})")
            status = HealthStatus.CRITICAL
        elif self.current_queue_depth >= self.QUEUE_DEPTH_WARNING:
            alerts.append(f"WARNING: Queue depth is {self.current_queue_depth} (threshold: {self.QUEUE_DEPTH_WARNING})")
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED

        # Check build success rate
        build_success_rate = self.get_build_success_rate()
        recent_failures = self.get_recent_build_failures()

        if build_success_rate <= self.BUILD_SUCCESS_CRITICAL:
            alerts.append(f"CRITICAL: Build success rate is {build_success_rate:.1f}% (threshold: {self.BUILD_SUCCESS_CRITICAL}%)")
            status = HealthStatus.CRITICAL
        elif build_success_rate <= self.BUILD_SUCCESS_WARNING:
            alerts.append(f"WARNING: Build success rate is {build_success_rate:.1f}% (threshold: {self.BUILD_SUCCESS_WARNING}%)")
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED

        # Alert on consecutive failures (circuit breaker related)
        if recent_failures >= 5:
            alerts.append(f"CRITICAL: {recent_failures} consecutive build failures detected")
            status = HealthStatus.CRITICAL

        return HealthMetrics(
            timestamp=datetime.utcnow(),
            api_latency_ms=avg_latency,
            error_rate_percent=error_rate,
            queue_depth=self.current_queue_depth,
            build_success_rate_percent=build_success_rate,
            status=status,
            alerts=alerts
        )

    # ========================================================================
    # Dashboard Metrics
    # ========================================================================

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for dashboard display.

        Returns:
            Dictionary with all key metrics
        """
        health = self.check_health()

        return {
            "timestamp": health.timestamp.isoformat(),
            "status": health.status.value,
            "alerts": health.alerts,
            "metrics": {
                "api_latency": {
                    "avg_ms": round(self.get_avg_latency(), 2),
                    "p95_ms": round(self.get_p95_latency(), 2),
                    "samples": len(self.api_response_times),
                    "threshold_warning_ms": self.LATENCY_WARNING_MS,
                    "threshold_critical_ms": self.LATENCY_CRITICAL_MS
                },
                "error_rate": {
                    "current_percent": round(health.error_rate_percent, 2),
                    "total_requests": self.total_requests,
                    "error_count": self.error_count,
                    "window_seconds": self.error_window_duration,
                    "threshold_warning": self.ERROR_RATE_WARNING,
                    "threshold_critical": self.ERROR_RATE_CRITICAL
                },
                "queue": {
                    "current_depth": self.current_queue_depth,
                    "avg_depth": round(self.get_avg_queue_depth(), 2),
                    "threshold_warning": self.QUEUE_DEPTH_WARNING,
                    "threshold_critical": self.QUEUE_DEPTH_CRITICAL
                },
                "builds": {
                    "success_rate_percent": round(health.build_success_rate_percent, 2),
                    "total_attempts": self.build_attempts,
                    "total_successes": self.build_successes,
                    "recent_failures": self.get_recent_build_failures(),
                    "history_size": len(self.build_history),
                    "threshold_warning": self.BUILD_SUCCESS_WARNING,
                    "threshold_critical": self.BUILD_SUCCESS_CRITICAL
                }
            }
        }


# ============================================================================
# Global Health Monitor Instance
# ============================================================================

_health_monitor = None


def get_health_monitor() -> HealthMonitor:
    """Get or create global health monitor"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


# ============================================================================
# Convenience Functions for Health Monitoring
# ============================================================================

def track_api_latency(latency_ms: float):
    """Track API response time"""
    monitor = get_health_monitor()
    monitor.track_api_response_time(latency_ms)


def track_api_request(is_error: bool = False):
    """Track API request"""
    monitor = get_health_monitor()
    monitor.track_request(is_error)


def update_queue_depth(depth: int):
    """Update queue depth"""
    monitor = get_health_monitor()
    monitor.update_queue_depth(depth)


def track_build_result(success: bool):
    """Track build result"""
    monitor = get_health_monitor()
    monitor.track_build(success)


def get_system_health() -> HealthMetrics:
    """Get current system health"""
    monitor = get_health_monitor()
    return monitor.check_health()


def get_health_dashboard() -> Dict[str, Any]:
    """Get dashboard metrics"""
    monitor = get_health_monitor()
    return monitor.get_dashboard_metrics()


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    async def test_security_monitoring():
        """Test security monitoring"""
        monitor = SecurityMonitor()

        # Simulate brute force attack
        print("=== Security Monitoring Tests ===")
        print("\nSimulating brute force attack...")
        for i in range(7):
            await monitor.track_failed_login(
                user_id=None,
                ip_address="10.0.0.1",
                username="admin",
                reason="invalid_password"
            )
            await asyncio.sleep(0.1)

        # Simulate SQL injection
        print("\nSimulating SQL injection...")
        await monitor.track_sql_injection(
            user_id="user123",
            ip_address="10.0.0.2",
            payload="' OR 1=1--",
            field="username"
        )

        # Simulate privilege escalation
        print("\nSimulating privilege escalation...")
        await monitor.track_privilege_escalation(
            user_id="user456",
            ip_address="10.0.0.3",
            attempted_action="delete_all_users",
            current_role="user",
            required_role="admin"
        )

        # Simulate admin creation
        print("\nSimulating admin account creation...")
        await monitor.track_admin_creation(
            creator_user_id="admin1",
            new_admin_user_id="admin2",
            new_admin_username="newadmin",
            creator_ip="10.0.0.4"
        )

        print("\nSecurity monitoring tests completed!")

    def test_health_monitoring():
        """Test health monitoring (SF-002)"""
        print("\n\n=== Health Monitoring Tests (SF-002) ===")
        health_monitor = get_health_monitor()

        # Test API latency tracking
        print("\nTesting API latency monitoring...")
        for latency in [100, 150, 200, 500, 1200, 2500]:
            health_monitor.track_api_response_time(latency)
            print(f"  Tracked latency: {latency}ms")

        print(f"  Average latency: {health_monitor.get_avg_latency():.2f}ms")
        print(f"  P95 latency: {health_monitor.get_p95_latency():.2f}ms")

        # Test error rate tracking
        print("\nTesting error rate monitoring...")
        for i in range(20):
            is_error = i % 10 == 0  # 10% error rate
            health_monitor.track_request(is_error)
        print(f"  Error rate: {health_monitor.get_error_rate():.2f}%")

        # Test queue depth tracking
        print("\nTesting queue depth monitoring...")
        for depth in [10, 25, 45, 75, 105]:
            health_monitor.update_queue_depth(depth)
            print(f"  Queue depth: {depth}")
        print(f"  Average queue depth: {health_monitor.get_avg_queue_depth():.2f}")

        # Test build success rate tracking
        print("\nTesting build success rate monitoring...")
        build_results = [True, True, False, True, True, False, False, True]
        for success in build_results:
            health_monitor.track_build(success)
            status = "SUCCESS" if success else "FAILURE"
            print(f"  Build: {status}")
        print(f"  Build success rate: {health_monitor.get_build_success_rate():.2f}%")
        print(f"  Recent consecutive failures: {health_monitor.get_recent_build_failures()}")

        # Test health check with alerts
        print("\nChecking overall system health...")
        health = health_monitor.check_health()
        print(f"  Status: {health.status.value.upper()}")
        print(f"  API Latency: {health.api_latency_ms:.2f}ms")
        print(f"  Error Rate: {health.error_rate_percent:.2f}%")
        print(f"  Queue Depth: {health.queue_depth}")
        print(f"  Build Success Rate: {health.build_success_rate_percent:.2f}%")

        if health.alerts:
            print(f"\n  Alerts ({len(health.alerts)}):")
            for alert in health.alerts:
                print(f"    - {alert}")
        else:
            print("\n  No alerts")

        # Test dashboard metrics
        print("\nGetting dashboard metrics...")
        dashboard = health_monitor.get_dashboard_metrics()
        import json
        print(json.dumps(dashboard, indent=2))

        print("\n✅ Health monitoring tests completed!")

    # Run tests
    print("Starting monitoring system tests...\n")
    asyncio.run(test_security_monitoring())
    test_health_monitoring()
    print("\n🎉 All tests passed!")
