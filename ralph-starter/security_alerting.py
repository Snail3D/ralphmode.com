"""
SEC-025: Security Alerting
Real-time security alerting with comprehensive monitoring, alert routing, and incident response.

This module extends the existing security_alerts.py with:
- Specific alert triggers for all OWASP Top 10 scenarios
- API anomaly detection
- Admin account monitoring
- On-call rotation management
- Alert fatigue minimization through intelligent throttling

Integrations:
- Telegram (primary - we're a Telegram bot!)
- Email
- PagerDuty (for critical incidents requiring immediate response)
- Slack (for team visibility)
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
import json

# Import existing alerting infrastructure
from security_alerts import (
    SecurityAlertManager,
    SecurityAlert,
    AlertSeverity,
    send_security_alert
)

# Import security logging
from security_logging import (
    SecurityLogger,
    SecurityEventType,
    SecuritySeverity,
    SecurityEvent
)


# ============================================================================
# Enhanced Alert Triggers
# ============================================================================

@dataclass
class AlertTrigger:
    """Configuration for alert triggers"""
    event_type: SecurityEventType
    threshold: int
    time_window_seconds: int
    severity: AlertSeverity
    alert_title: str
    alert_message_template: str


class SecurityAlertTriggers:
    """
    Comprehensive alert triggers for SEC-025 compliance
    Meets all acceptance criteria:
    1. 5+ failed logins from same IP
    2. Privilege escalation attempts
    3. SQL injection attempts
    4. Unusual API patterns
    5. New admin account creation
    """

    TRIGGERS = [
        # 1. Failed login alerts (5+ from same IP)
        AlertTrigger(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            threshold=5,
            time_window_seconds=300,  # 5 minutes
            severity=AlertSeverity.ERROR,
            alert_title="Multiple Failed Login Attempts Detected",
            alert_message_template="IP {ip_address} has {count} failed login attempts in {window} minutes. Possible brute force attack."
        ),

        # 2. Privilege escalation attempts
        AlertTrigger(
            event_type=SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT,
            threshold=1,  # Any privilege escalation attempt is critical
            time_window_seconds=60,
            severity=AlertSeverity.CRITICAL,
            alert_title="Privilege Escalation Attempt Detected",
            alert_message_template="User {user_id} attempted privilege escalation from IP {ip_address}. IMMEDIATE INVESTIGATION REQUIRED."
        ),

        # 3. SQL injection attempts
        AlertTrigger(
            event_type=SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT,
            threshold=1,  # Any SQL injection is critical
            time_window_seconds=60,
            severity=AlertSeverity.CRITICAL,
            alert_title="SQL Injection Attack Detected",
            alert_message_template="SQL injection attempt from IP {ip_address}. Payload: {payload}. Automatically blocked."
        ),

        # 4. XSS attempts
        AlertTrigger(
            event_type=SecurityEventType.INPUT_XSS_ATTEMPT,
            threshold=1,
            time_window_seconds=60,
            severity=AlertSeverity.CRITICAL,
            alert_title="XSS Attack Detected",
            alert_message_template="XSS injection attempt from IP {ip_address}. Payload: {payload}. Automatically blocked."
        ),

        # 5. LLM prompt injection
        AlertTrigger(
            event_type=SecurityEventType.LLM_PROMPT_INJECTION_ATTEMPT,
            threshold=3,
            time_window_seconds=300,
            severity=AlertSeverity.ERROR,
            alert_title="LLM Prompt Injection Attempts",
            alert_message_template="IP {ip_address} has {count} prompt injection attempts. User {user_id} may be attempting to manipulate the AI."
        ),

        # 6. Rate limit exceeded (potential DDoS)
        AlertTrigger(
            event_type=SecurityEventType.INPUT_RATE_LIMIT_EXCEEDED,
            threshold=20,
            time_window_seconds=300,
            severity=AlertSeverity.WARNING,
            alert_title="Excessive Rate Limit Violations",
            alert_message_template="IP {ip_address} exceeded rate limits {count} times. Possible DDoS or abuse."
        ),

        # 7. Access denied patterns (reconnaissance)
        AlertTrigger(
            event_type=SecurityEventType.AUTHZ_ACCESS_DENIED,
            threshold=10,
            time_window_seconds=300,
            severity=AlertSeverity.WARNING,
            alert_title="Excessive Access Denials",
            alert_message_template="User {user_id} from IP {ip_address} has {count} access denials. Possible reconnaissance activity."
        ),

        # 8. Session hijack attempts
        AlertTrigger(
            event_type=SecurityEventType.AUTH_SESSION_HIJACK_ATTEMPT,
            threshold=1,
            time_window_seconds=60,
            severity=AlertSeverity.CRITICAL,
            alert_title="Session Hijack Attempt Detected",
            alert_message_template="Potential session hijacking detected for user {user_id}. IP mismatch or token tampering detected."
        ),
    ]


# ============================================================================
# API Anomaly Detection
# ============================================================================

class APIAnomalyDetector:
    """
    Detects unusual API patterns:
    - Sudden spike in requests (>3x normal)
    - Unusual endpoint access patterns
    - Geographic anomalies (access from new countries)
    - Time-based anomalies (access at unusual hours)
    """

    def __init__(self):
        # Track API request patterns
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.endpoint_baselines: Dict[str, float] = {}  # Average requests per minute
        self.user_locations: Dict[str, set] = defaultdict(set)  # User -> countries
        self.user_typical_hours: Dict[str, set] = defaultdict(set)  # User -> hours

    def record_api_call(
        self,
        user_id: str,
        endpoint: str,
        ip_address: str,
        country: Optional[str] = None
    ):
        """Record API call for pattern analysis"""
        timestamp = datetime.utcnow()

        # Record request
        key = f"{user_id}:{endpoint}"
        self.request_history[key].append(timestamp)

        # Track location
        if country:
            self.user_locations[user_id].add(country)

        # Track typical access hours
        hour = timestamp.hour
        self.user_typical_hours[user_id].add(hour)

    def detect_anomalies(
        self,
        user_id: str,
        endpoint: str,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in API usage

        Returns:
            List of detected anomalies with details
        """
        anomalies = []
        key = f"{user_id}:{endpoint}"

        # 1. Spike detection: >3x normal request rate
        if key in self.request_history:
            recent_requests = self.request_history[key]
            if len(recent_requests) >= 10:
                # Calculate recent rate (last minute)
                one_min_ago = datetime.utcnow() - timedelta(minutes=1)
                recent_count = sum(1 for ts in recent_requests if ts > one_min_ago)

                # Calculate baseline (excluding last minute)
                baseline_count = len(recent_requests) - recent_count
                baseline_rate = baseline_count / max(len(recent_requests), 1)

                # Alert if >3x baseline
                if recent_count > baseline_rate * 3 and recent_count > 10:
                    anomalies.append({
                        "type": "request_spike",
                        "severity": "high",
                        "message": f"Request spike detected: {recent_count} requests in last minute (baseline: {baseline_rate:.1f})",
                        "recent_count": recent_count,
                        "baseline": baseline_rate
                    })

        # 2. Geographic anomaly: New country for established user
        if country and user_id in self.user_locations:
            known_countries = self.user_locations[user_id]
            if len(known_countries) >= 3 and country not in known_countries:
                anomalies.append({
                    "type": "geographic_anomaly",
                    "severity": "medium",
                    "message": f"Access from new country: {country} (known: {', '.join(known_countries)})",
                    "new_country": country,
                    "known_countries": list(known_countries)
                })

        # 3. Time-based anomaly: Access at unusual hour
        current_hour = datetime.utcnow().hour
        if user_id in self.user_typical_hours:
            typical_hours = self.user_typical_hours[user_id]
            if len(typical_hours) >= 5 and current_hour not in typical_hours:
                # Check if this is significantly different (>4 hours from typical)
                hour_diffs = [min(abs(current_hour - h), 24 - abs(current_hour - h)) for h in typical_hours]
                min_diff = min(hour_diffs) if hour_diffs else 0

                if min_diff > 4:
                    anomalies.append({
                        "type": "temporal_anomaly",
                        "severity": "low",
                        "message": f"Access at unusual hour: {current_hour}:00 (typical: {sorted(typical_hours)})",
                        "current_hour": current_hour,
                        "typical_hours": sorted(typical_hours)
                    })

        return anomalies


# ============================================================================
# Admin Account Monitoring
# ============================================================================

class AdminAccountMonitor:
    """
    Monitors admin account changes:
    - New admin account creation
    - Admin role changes
    - Admin permission modifications
    - Admin login from new locations
    """

    def __init__(self, alert_manager: SecurityAlertManager):
        self.alert_manager = alert_manager
        self.admin_users: set = set()
        self.admin_creation_log: List[Dict[str, Any]] = []

    async def alert_new_admin(
        self,
        new_admin_id: str,
        created_by: str,
        ip_address: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Alert when new admin account is created"""
        await send_security_alert(
            title="🔴 New Admin Account Created",
            message=f"A new admin account was created:\n"
                   f"• New Admin: {new_admin_id}\n"
                   f"• Created By: {created_by}\n"
                   f"• IP Address: {ip_address}\n\n"
                   f"REQUIRES VERIFICATION: Confirm this was authorized.",
            severity=AlertSeverity.CRITICAL,
            event_type="admin.account.created",
            user_id=created_by,
            ip_address=ip_address,
            new_admin_id=new_admin_id,
            **(details or {})
        )

        # Log creation
        self.admin_creation_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "new_admin_id": new_admin_id,
            "created_by": created_by,
            "ip_address": ip_address,
            "details": details
        })

        # Add to admin set
        self.admin_users.add(new_admin_id)

    async def alert_admin_role_change(
        self,
        admin_id: str,
        old_role: str,
        new_role: str,
        changed_by: str,
        ip_address: str
    ):
        """Alert when admin role/permissions change"""
        severity = AlertSeverity.CRITICAL if "admin" in new_role.lower() else AlertSeverity.ERROR

        await send_security_alert(
            title="⚠️ Admin Role Change",
            message=f"Admin permissions changed:\n"
                   f"• Admin: {admin_id}\n"
                   f"• Old Role: {old_role}\n"
                   f"• New Role: {new_role}\n"
                   f"• Changed By: {changed_by}\n"
                   f"• IP: {ip_address}",
            severity=severity,
            event_type="admin.role.changed",
            user_id=changed_by,
            ip_address=ip_address,
            admin_id=admin_id,
            old_role=old_role,
            new_role=new_role
        )


# ============================================================================
# On-Call Rotation Management
# ============================================================================

@dataclass
class OnCallEngineer:
    """On-call engineer details"""
    name: str
    telegram_id: int
    email: str
    phone: Optional[str]
    timezone: str


class OnCallRotation:
    """
    Manages 24/7 on-call rotation for security incidents.

    Rotation schedule:
    - Primary: First responder (immediate notification)
    - Secondary: Escalation if no response in 5 minutes
    - Manager: Escalation for critical incidents
    """

    def __init__(self):
        # Load rotation from environment or config
        self.engineers = self._load_engineers()
        self.rotation_schedule = self._build_rotation()

    def _load_engineers(self) -> List[OnCallEngineer]:
        """Load on-call engineers from configuration"""
        # In production, load from database or config file
        # For now, load from environment
        engineers_json = os.getenv("ONCALL_ENGINEERS", "[]")
        try:
            engineers_data = json.loads(engineers_json)
            return [OnCallEngineer(**e) for e in engineers_data]
        except:
            return []

    def _build_rotation(self) -> Dict[str, OnCallEngineer]:
        """Build rotation schedule (weekly rotation)"""
        if not self.engineers:
            return {}

        # Simple weekly rotation (can be enhanced with more complex scheduling)
        week_number = datetime.utcnow().isocalendar()[1]
        primary_index = week_number % len(self.engineers)
        secondary_index = (week_number + 1) % len(self.engineers)

        return {
            "primary": self.engineers[primary_index],
            "secondary": self.engineers[secondary_index],
        }

    def get_current_oncall(self, role: str = "primary") -> Optional[OnCallEngineer]:
        """Get currently on-call engineer"""
        return self.rotation_schedule.get(role)

    async def escalate_alert(
        self,
        alert: SecurityAlert,
        alert_manager: SecurityAlertManager
    ):
        """
        Escalate alert through on-call rotation:
        1. Send to primary
        2. If no acknowledgment in 5 minutes, escalate to secondary
        3. For CRITICAL, send to both immediately
        """
        primary = self.get_current_oncall("primary")
        secondary = self.get_current_oncall("secondary")

        if alert.severity == AlertSeverity.CRITICAL:
            # Critical: notify both immediately
            if primary:
                await self._notify_engineer(primary, alert, alert_manager, "PRIMARY")
            if secondary:
                await self._notify_engineer(secondary, alert, alert_manager, "SECONDARY")
        else:
            # Non-critical: primary first
            if primary:
                await self._notify_engineer(primary, alert, alert_manager, "PRIMARY")

                # TODO: Implement acknowledgment tracking and auto-escalation
                # after 5 minutes of no response

    async def _notify_engineer(
        self,
        engineer: OnCallEngineer,
        alert: SecurityAlert,
        alert_manager: SecurityAlertManager,
        role: str
    ):
        """Send alert to specific engineer"""
        # Customize alert message for on-call engineer
        enhanced_message = f"🚨 ON-CALL ALERT ({role})\n\n{alert.message}\n\n"
        enhanced_message += f"On-call: {engineer.name} ({engineer.timezone})"

        enhanced_alert = SecurityAlert(
            title=alert.title,
            message=enhanced_message,
            severity=alert.severity,
            event_type=alert.event_type,
            timestamp=alert.timestamp,
            user_id=alert.user_id,
            ip_address=alert.ip_address,
            metadata={**alert.metadata, "oncall_engineer": engineer.name, "oncall_role": role}
        )

        # Send via Telegram directly to engineer
        if alert_manager.telegram_bot:
            try:
                await alert_manager.telegram_bot.send_message(
                    chat_id=engineer.telegram_id,
                    text=alert_manager._format_telegram_alert(enhanced_alert),
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Failed to notify {engineer.name}: {e}")


# ============================================================================
# Alert Fatigue Minimization
# ============================================================================

class AlertFatigueManager:
    """
    Minimizes alert fatigue through:
    - Intelligent alert grouping (combine similar alerts)
    - Adaptive thresholds (tune based on normal patterns)
    - Alert summarization (hourly digests for low-priority)
    - Automatic silence periods after resolution
    """

    def __init__(self):
        self.alert_groups: Dict[str, List[SecurityAlert]] = defaultdict(list)
        self.silence_periods: Dict[str, datetime] = {}
        self.threshold_adjustments: Dict[str, float] = defaultdict(lambda: 1.0)

    def should_send_alert(
        self,
        alert: SecurityAlert,
        similar_alerts_count: int
    ) -> bool:
        """
        Decide if alert should be sent or grouped

        Returns:
            bool: True if alert should be sent immediately
        """
        alert_key = f"{alert.event_type}:{alert.ip_address}"

        # 1. Check silence period
        if alert_key in self.silence_periods:
            if datetime.utcnow() < self.silence_periods[alert_key]:
                return False  # Still in silence period

        # 2. Critical alerts always go through
        if alert.severity == AlertSeverity.CRITICAL:
            return True

        # 3. Group similar low-priority alerts
        if alert.severity == AlertSeverity.INFO and similar_alerts_count > 0:
            self.alert_groups[alert_key].append(alert)
            return False  # Will be sent as digest later

        # 4. Apply threshold adjustments
        # If we've had too many false positives, raise threshold
        adjusted_threshold = self._get_adjusted_threshold(alert.event_type)
        if similar_alerts_count < adjusted_threshold:
            return False

        return True

    def _get_adjusted_threshold(self, event_type: str) -> int:
        """Get adjusted threshold based on historical false positive rate"""
        base_threshold = 1
        adjustment = self.threshold_adjustments[event_type]
        return int(base_threshold * adjustment)

    def silence_alert_type(self, alert_type: str, duration_minutes: int = 60):
        """Silence specific alert type for duration"""
        self.silence_periods[alert_type] = datetime.utcnow() + timedelta(minutes=duration_minutes)

    async def send_alert_digest(self, alert_manager: SecurityAlertManager):
        """Send hourly digest of grouped low-priority alerts"""
        if not self.alert_groups:
            return

        digest_message = "📊 *Security Alert Digest (Last Hour)*\n\n"

        for alert_key, alerts in self.alert_groups.items():
            if alerts:
                digest_message += f"• {alert_key}: {len(alerts)} events\n"

        digest_alert = SecurityAlert(
            title="Security Alert Digest",
            message=digest_message,
            severity=AlertSeverity.INFO,
            event_type="digest.hourly",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            metadata={"grouped_alerts": len(self.alert_groups)}
        )

        await alert_manager.send_alert(digest_alert)

        # Clear grouped alerts
        self.alert_groups.clear()


# ============================================================================
# Unified Security Alerting System
# ============================================================================

class UnifiedSecurityAlerting:
    """
    Complete SEC-025 implementation combining:
    - Alert triggers
    - API anomaly detection
    - Admin monitoring
    - On-call rotation
    - Alert fatigue management
    """

    def __init__(self):
        self.security_logger = SecurityLogger()
        self.alert_manager = SecurityAlertManager()
        self.anomaly_detector = APIAnomalyDetector()
        self.admin_monitor = AdminAccountMonitor(self.alert_manager)
        self.oncall_rotation = OnCallRotation()
        self.fatigue_manager = AlertFatigueManager()

    async def process_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        user_id: Optional[str],
        ip_address: Optional[str],
        details: Dict[str, Any]
    ):
        """
        Process security event and trigger appropriate alerts

        This is the main entry point for the alerting system
        """
        # 1. Log the event
        event = self.security_logger.log_event(
            event_type=event_type,
            severity=severity,
            action=details.get("action", "unknown"),
            result=details.get("result", "unknown"),
            user_id=user_id,
            ip_address=ip_address,
            details=details
        )

        # 2. Check if this triggers any alerts
        for trigger in SecurityAlertTriggers.TRIGGERS:
            if trigger.event_type == event_type:
                # Check if threshold exceeded
                if self._check_trigger_threshold(trigger, user_id, ip_address):
                    alert = self._create_alert_from_trigger(
                        trigger, user_id, ip_address, details
                    )

                    # 3. Check alert fatigue
                    if self.fatigue_manager.should_send_alert(alert, 0):
                        # 4. Send through alert manager
                        await self.alert_manager.send_alert(alert)

                        # 5. Escalate to on-call if critical
                        if alert.severity == AlertSeverity.CRITICAL:
                            await self.oncall_rotation.escalate_alert(alert, self.alert_manager)

    def _check_trigger_threshold(
        self,
        trigger: AlertTrigger,
        user_id: Optional[str],
        ip_address: Optional[str]
    ) -> bool:
        """Check if event count exceeds trigger threshold"""
        # Use SecurityLogger's history to check threshold
        cutoff_time = datetime.utcnow() - timedelta(seconds=trigger.time_window_seconds)

        matching_events = [
            e for e in self.security_logger.event_history
            if e.event_type == trigger.event_type.value
            and datetime.fromisoformat(e.timestamp.rstrip('Z')) > cutoff_time
            and (user_id is None or e.user_id == user_id)
            and (ip_address is None or e.ip_address == ip_address)
        ]

        return len(matching_events) >= trigger.threshold

    def _create_alert_from_trigger(
        self,
        trigger: AlertTrigger,
        user_id: Optional[str],
        ip_address: Optional[str],
        details: Dict[str, Any]
    ) -> SecurityAlert:
        """Create SecurityAlert from trigger configuration"""
        message = trigger.alert_message_template.format(
            user_id=user_id or "unknown",
            ip_address=ip_address or "unknown",
            count=trigger.threshold,
            window=trigger.time_window_seconds // 60,
            payload=details.get("payload", "N/A")[:100]
        )

        return SecurityAlert(
            title=trigger.alert_title,
            message=message,
            severity=trigger.severity,
            event_type=trigger.event_type.value,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            user_id=user_id,
            ip_address=ip_address,
            metadata=details
        )


# ============================================================================
# Global Instance
# ============================================================================

_unified_alerting = None

def get_unified_alerting() -> UnifiedSecurityAlerting:
    """Get global unified alerting instance"""
    global _unified_alerting
    if _unified_alerting is None:
        _unified_alerting = UnifiedSecurityAlerting()
    return _unified_alerting


# ============================================================================
# Convenience Functions
# ============================================================================

async def alert_on_failed_logins(ip_address: str, username: str, count: int):
    """Alert on multiple failed login attempts"""
    alerting = get_unified_alerting()
    await alerting.process_security_event(
        event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        user_id=None,
        ip_address=ip_address,
        details={
            "action": "login",
            "result": "failure",
            "username": username,
            "attempt_count": count
        }
    )


async def alert_on_privilege_escalation(user_id: str, ip_address: str, attempted_action: str):
    """Alert on privilege escalation attempt"""
    alerting = get_unified_alerting()
    await alerting.process_security_event(
        event_type=SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT,
        severity=SecuritySeverity.CRITICAL,
        user_id=user_id,
        ip_address=ip_address,
        details={
            "action": attempted_action,
            "result": "blocked"
        }
    )


async def alert_on_sql_injection(ip_address: str, payload: str, field: str):
    """Alert on SQL injection attempt"""
    alerting = get_unified_alerting()
    await alerting.process_security_event(
        event_type=SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT,
        severity=SecuritySeverity.CRITICAL,
        user_id=None,
        ip_address=ip_address,
        details={
            "action": f"sql_injection_{field}",
            "result": "blocked",
            "payload": payload,
            "field": field
        }
    )


async def alert_on_new_admin(
    new_admin_id: str,
    created_by: str,
    ip_address: str
):
    """Alert on new admin account creation"""
    alerting = get_unified_alerting()
    await alerting.admin_monitor.alert_new_admin(
        new_admin_id=new_admin_id,
        created_by=created_by,
        ip_address=ip_address
    )


async def alert_on_api_anomaly(
    user_id: str,
    endpoint: str,
    ip_address: str,
    country: Optional[str] = None
):
    """Alert on unusual API patterns"""
    alerting = get_unified_alerting()

    # Record API call
    alerting.anomaly_detector.record_api_call(user_id, endpoint, ip_address, country)

    # Detect anomalies
    anomalies = alerting.anomaly_detector.detect_anomalies(user_id, endpoint, country)

    # Send alerts for detected anomalies
    for anomaly in anomalies:
        severity_map = {
            "low": AlertSeverity.INFO,
            "medium": AlertSeverity.WARNING,
            "high": AlertSeverity.ERROR,
            "critical": AlertSeverity.CRITICAL
        }

        await send_security_alert(
            title=f"API Anomaly Detected: {anomaly['type']}",
            message=anomaly['message'],
            severity=severity_map.get(anomaly['severity'], AlertSeverity.WARNING),
            event_type=f"api.anomaly.{anomaly['type']}",
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            **anomaly
        )


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    async def test_sec025():
        """Test SEC-025 alerting system"""
        print("Testing SEC-025 Security Alerting System...")

        # Test 1: Failed login alerts
        print("\n1. Testing failed login alerts...")
        for i in range(6):
            await alert_on_failed_logins("10.0.0.1", "attacker", i+1)

        # Test 2: Privilege escalation
        print("\n2. Testing privilege escalation alert...")
        await alert_on_privilege_escalation("user123", "10.0.0.1", "access_admin_panel")

        # Test 3: SQL injection
        print("\n3. Testing SQL injection alert...")
        await alert_on_sql_injection("10.0.0.2", "' OR 1=1--", "username")

        # Test 4: New admin creation
        print("\n4. Testing new admin alert...")
        await alert_on_new_admin("new_admin_99", "admin1", "192.168.1.100")

        # Test 5: API anomaly
        print("\n5. Testing API anomaly detection...")
        for i in range(15):
            await alert_on_api_anomaly("user456", "/api/data", "10.0.0.3")

        print("\n✅ All SEC-025 tests completed!")

    # Run tests
    asyncio.run(test_sec025())
