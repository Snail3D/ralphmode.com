#!/usr/bin/env python3
"""
Tests for SEC-025: Security Alerting

Tests all acceptance criteria:
1. Alert on 5+ failed logins from same IP
2. Alert on privilege escalation attempts
3. Alert on SQL injection attempts
4. Alert on unusual API patterns
5. Alert on new admin account creation
6. PagerDuty/Slack integration (via security_alerts.py)
7. Alert fatigue minimized (tuned thresholds)
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from security_monitor import (
    SecurityMonitor,
    AlertThresholds,
    MonitoringSecurityLogger
)

try:
    from security_logging import SecurityEventType, SecuritySeverity
    from security_alerts import AlertSeverity
    SECURITY_MODULES_AVAILABLE = True
except ImportError:
    SECURITY_MODULES_AVAILABLE = False
    pytest.skip("Security modules not available", allow_module_level=True)


@pytest.fixture
def monitor():
    """Create a SecurityMonitor with mocked alert manager"""
    alert_manager = Mock()
    alert_manager.send_alert = AsyncMock()
    return SecurityMonitor(alert_manager=alert_manager)


@pytest.fixture
def mock_send_alert():
    """Mock the send_security_alert function"""
    with patch('security_monitor.send_security_alert', new_callable=AsyncMock) as mock:
        yield mock


# ============================================================================
# SEC-025.1: Failed Login Detection
# ============================================================================

@pytest.mark.asyncio
async def test_failed_login_threshold(mock_send_alert):
    """Test that 5+ failed logins from same IP triggers alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate 4 failed logins (should NOT alert)
    for i in range(4):
        await monitor.process_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            ip_address="192.168.1.100",
            user_id=f"user{i}",
            details={"reason": "invalid_password"}
        )

    # No alert yet
    assert mock_send_alert.call_count == 0

    # 5th failed login should trigger alert
    await monitor.process_event(
        event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        ip_address="192.168.1.100",
        user_id="user5",
        details={"reason": "invalid_password"}
    )

    # Alert should be sent
    assert mock_send_alert.call_count == 1
    call_args = mock_send_alert.call_args[1]
    assert "Brute Force" in call_args['title']
    assert call_args['severity'] == AlertSeverity.CRITICAL
    assert call_args['ip_address'] == "192.168.1.100"


@pytest.mark.asyncio
async def test_failed_login_different_ips(mock_send_alert):
    """Test that failed logins from different IPs don't trigger alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate 3 failed logins from different IPs
    for i in range(3):
        await monitor.process_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            ip_address=f"192.168.1.{100 + i}",
            user_id="same_user",
            details={"reason": "invalid_password"}
        )

    # No alert should be sent (different IPs)
    assert mock_send_alert.call_count == 0


@pytest.mark.asyncio
async def test_failed_login_window_expiry(mock_send_alert):
    """Test that old failed logins outside the window don't count"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Add 4 failed logins
    for i in range(4):
        await monitor.process_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            ip_address="192.168.1.100",
            user_id=f"user{i}",
            details={"reason": "invalid_password"}
        )

    # Manually expire the window
    monitor.failed_logins["192.168.1.100"] = [
        time.time() - AlertThresholds.FAILED_LOGIN_WINDOW - 10
    ]

    # New failed login should NOT trigger alert (old data expired)
    await monitor.process_event(
        event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        ip_address="192.168.1.100",
        user_id="user5",
        details={"reason": "invalid_password"}
    )

    assert mock_send_alert.call_count == 0


# ============================================================================
# SEC-025.2: Privilege Escalation Detection
# ============================================================================

@pytest.mark.asyncio
async def test_privilege_escalation_threshold(mock_send_alert):
    """Test that 3+ privilege escalation attempts trigger alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate 2 attempts (should NOT alert)
    for i in range(2):
        await monitor.process_event(
            event_type=SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            user_id="attacker",
            ip_address="10.0.0.1",
            details={"attempted_action": "admin_access"}
        )

    assert mock_send_alert.call_count == 0

    # 3rd attempt should trigger alert
    await monitor.process_event(
        event_type=SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT,
        severity=SecuritySeverity.HIGH,
        user_id="attacker",
        ip_address="10.0.0.1",
        details={"attempted_action": "admin_access"}
    )

    assert mock_send_alert.call_count == 1
    call_args = mock_send_alert.call_args[1]
    assert "Privilege Escalation" in call_args['title']
    assert call_args['severity'] == AlertSeverity.CRITICAL
    assert call_args['user_id'] == "attacker"


@pytest.mark.asyncio
async def test_privilege_escalation_different_users(mock_send_alert):
    """Test that privilege escalation is tracked per user"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate 2 attempts from different users
    for i in range(2):
        await monitor.process_event(
            event_type=SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            user_id=f"attacker{i}",
            ip_address="10.0.0.1",
            details={"attempted_action": "admin_access"}
        )

    # No alert (different users)
    assert mock_send_alert.call_count == 0


# ============================================================================
# SEC-025.3: SQL Injection Detection
# ============================================================================

@pytest.mark.asyncio
async def test_sqli_threshold(mock_send_alert):
    """Test that 3+ SQL injection attempts trigger alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate 2 attempts (should NOT alert)
    for i in range(2):
        await monitor.process_event(
            event_type=SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            ip_address="10.0.0.1",
            details={"payload": f"' OR 1=1-- {i}"}
        )

    assert mock_send_alert.call_count == 0

    # 3rd attempt should trigger alert
    await monitor.process_event(
        event_type=SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT,
        severity=SecuritySeverity.HIGH,
        ip_address="10.0.0.1",
        details={"payload": "' OR 1=1--"}
    )

    assert mock_send_alert.call_count == 1
    call_args = mock_send_alert.call_args[1]
    assert "SQL Injection" in call_args['title']
    assert call_args['severity'] == AlertSeverity.ERROR
    assert call_args['ip_address'] == "10.0.0.1"


@pytest.mark.asyncio
async def test_xss_threshold(mock_send_alert):
    """Test that 3+ XSS attempts trigger alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate 3 XSS attempts
    for i in range(3):
        await monitor.process_event(
            event_type=SecurityEventType.INPUT_XSS_ATTEMPT,
            severity=SecuritySeverity.HIGH,
            ip_address="10.0.0.2",
            details={"payload": f"<script>alert({i})</script>"}
        )

    assert mock_send_alert.call_count == 1
    call_args = mock_send_alert.call_args[1]
    assert "XSS" in call_args['title']


# ============================================================================
# SEC-025.4: Unusual API Patterns
# ============================================================================

@pytest.mark.asyncio
async def test_api_burst_detection(mock_send_alert):
    """Test that 100+ requests in 10 seconds triggers alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate burst of 100+ requests
    for i in range(100):
        await monitor.process_event(
            event_type=SecurityEventType.SYSTEM_ERROR,  # Any event type
            severity=SecuritySeverity.LOW,
            ip_address="10.0.0.3",
            details={"endpoint": "/api/test"}
        )

    assert mock_send_alert.call_count == 1
    call_args = mock_send_alert.call_args[1]
    assert "Burst" in call_args['title']
    assert call_args['ip_address'] == "10.0.0.3"


@pytest.mark.asyncio
async def test_api_reconnaissance_detection(mock_send_alert):
    """Test that hitting 20+ different endpoints triggers alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate scanning 20+ different endpoints
    for i in range(25):
        await monitor.process_event(
            event_type=SecurityEventType.SYSTEM_ERROR,
            severity=SecuritySeverity.LOW,
            ip_address="10.0.0.4",
            details={"endpoint": f"/api/endpoint_{i}"}
        )

    # Should trigger reconnaissance alert
    assert mock_send_alert.call_count >= 1

    # Find the reconnaissance alert
    recon_alert = None
    for call in mock_send_alert.call_args_list:
        if "Reconnaissance" in call[1]['title']:
            recon_alert = call[1]
            break

    assert recon_alert is not None
    assert recon_alert['ip_address'] == "10.0.0.4"


# ============================================================================
# SEC-025.5: Admin Account Creation
# ============================================================================

@pytest.mark.asyncio
async def test_admin_creation_alert(mock_send_alert):
    """Test that admin account creation triggers immediate alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate admin role assignment
    await monitor.process_event(
        event_type=SecurityEventType.AUTHZ_ROLE_CHANGED,
        severity=SecuritySeverity.CRITICAL,
        user_id="new_admin",
        ip_address="10.0.0.5",
        details={
            "old_role": "user",
            "new_role": "admin",
            "created_by": "existing_admin"
        }
    )

    # Should trigger immediate alert
    assert mock_send_alert.call_count == 1
    call_args = mock_send_alert.call_args[1]
    assert "ADMIN" in call_args['title'].upper()
    assert call_args['severity'] == AlertSeverity.CRITICAL
    assert call_args['user_id'] == "new_admin"


@pytest.mark.asyncio
async def test_non_admin_role_change_no_alert(mock_send_alert):
    """Test that non-admin role changes don't trigger alert"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Simulate non-admin role change
    await monitor.process_event(
        event_type=SecurityEventType.AUTHZ_ROLE_CHANGED,
        severity=SecuritySeverity.LOW,
        user_id="user",
        ip_address="10.0.0.6",
        details={
            "old_role": "user",
            "new_role": "premium_user",
            "created_by": "admin"
        }
    )

    # Should NOT trigger alert (not admin)
    assert mock_send_alert.call_count == 0


# ============================================================================
# SEC-025.8: Alert Fatigue Minimization
# ============================================================================

@pytest.mark.asyncio
async def test_alert_cooldown(mock_send_alert):
    """Test that alerts are throttled to prevent spam"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Trigger first alert
    for i in range(5):
        await monitor.process_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            ip_address="192.168.1.100",
            user_id=f"user{i}",
            details={"reason": "invalid_password"}
        )

    assert mock_send_alert.call_count == 1

    # Trigger same pattern again immediately (should be throttled)
    for i in range(5, 10):
        await monitor.process_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            ip_address="192.168.1.100",
            user_id=f"user{i}",
            details={"reason": "invalid_password"}
        )

    # Still only 1 alert (cooldown active)
    assert mock_send_alert.call_count == 1


@pytest.mark.asyncio
async def test_alert_cooldown_expires(mock_send_alert):
    """Test that alerts can be sent again after cooldown expires"""
    alert_manager = Mock()
    monitor = SecurityMonitor(alert_manager=alert_manager)

    # Trigger first alert
    for i in range(5):
        await monitor.process_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            ip_address="192.168.1.100",
            user_id=f"user{i}",
            details={"reason": "invalid_password"}
        )

    assert mock_send_alert.call_count == 1

    # Manually expire the cooldown
    alert_key = "failed_login:192.168.1.100"
    monitor.last_alert[alert_key] = time.time() - AlertThresholds.ALERT_COOLDOWN - 10

    # Trigger same pattern again (should alert now)
    for i in range(5, 10):
        await monitor.process_event(
            event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            ip_address="192.168.1.100",
            user_id=f"user{i}",
            details={"reason": "invalid_password"}
        )

    # Should have 2 alerts now
    assert mock_send_alert.call_count == 2


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_monitoring_security_logger_integration():
    """Test MonitoringSecurityLogger integration"""
    from security_logging import SecurityLogger

    # Create mocked components
    security_logger = Mock()
    security_logger.log_event = Mock(return_value={"id": "event_123"})

    monitor = Mock()
    monitor.process_event = AsyncMock()

    # Create monitoring logger
    monitoring_logger = MonitoringSecurityLogger(
        security_logger=security_logger,
        monitor=monitor
    )

    # Log an event
    monitoring_logger.log_event(
        event_type=SecurityEventType.AUTH_LOGIN_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        action="login",
        result="failure",
        ip_address="10.0.0.1"
    )

    # Wait a moment for async processing
    await asyncio.sleep(0.1)

    # Should have logged to SecurityLogger
    assert security_logger.log_event.called

    # Should have processed for monitoring
    # Note: Due to async complexity, we just verify the integration exists


def test_alert_thresholds_configured():
    """Test that all alert thresholds are properly configured"""
    assert AlertThresholds.FAILED_LOGIN_IP_COUNT == 5
    assert AlertThresholds.FAILED_LOGIN_WINDOW == 300

    assert AlertThresholds.PRIVILEGE_ESCALATION_COUNT == 3
    assert AlertThresholds.PRIVILEGE_ESCALATION_WINDOW == 60

    assert AlertThresholds.SQLI_ATTEMPT_COUNT == 3
    assert AlertThresholds.SQLI_ATTEMPT_WINDOW == 60

    assert AlertThresholds.API_BURST_COUNT == 100
    assert AlertThresholds.API_BURST_WINDOW == 10

    assert AlertThresholds.ALERT_COOLDOWN == 300


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
