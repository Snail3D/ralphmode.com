"""
Tests for SEC-025: Security Monitoring and Alerting
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from monitoring import (
    SecurityMonitor,
    ThreatPattern,
    SecurityEvent,
    SecurityMonitoringMiddleware,
    get_security_monitor,
)
from security_alerts import AlertSeverity


# ============================================================================
# Test SecurityMonitor
# ============================================================================

@pytest.fixture
def mock_alert_manager():
    """Create mock alert manager"""
    manager = Mock()
    manager.send_alert = AsyncMock()
    return manager


@pytest.fixture
def security_monitor(mock_alert_manager):
    """Create SecurityMonitor instance with mock alert manager"""
    return SecurityMonitor(alert_manager=mock_alert_manager)


# ============================================================================
# Failed Login Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_failed_login_threshold(security_monitor, mock_alert_manager):
    """Test that 5+ failed logins trigger an alert"""
    ip_address = "10.0.0.1"

    # Simulate 5 failed logins
    for i in range(5):
        await security_monitor.track_failed_login(
            user_id=None,
            ip_address=ip_address,
            username="admin",
            reason="invalid_password"
        )

    # Should have triggered alert
    assert mock_alert_manager.send_alert.called
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert "Failed Login" in call_args.title or "Brute Force" in call_args.title
    assert call_args.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]


@pytest.mark.asyncio
async def test_failed_login_no_alert_below_threshold(security_monitor, mock_alert_manager):
    """Test that < 5 failed logins don't trigger alert"""
    ip_address = "10.0.0.2"

    # Simulate 4 failed logins (below threshold)
    for i in range(4):
        await security_monitor.track_failed_login(
            user_id=None,
            ip_address=ip_address,
            username="user",
            reason="invalid_password"
        )

    # Should NOT have triggered alert
    assert not mock_alert_manager.send_alert.called


@pytest.mark.asyncio
async def test_brute_force_detection(security_monitor, mock_alert_manager):
    """Test that 10+ failed logins trigger CRITICAL brute force alert"""
    ip_address = "10.0.0.3"

    # Simulate 10 failed logins (brute force threshold)
    for i in range(10):
        await security_monitor.track_failed_login(
            user_id=None,
            ip_address=ip_address,
            username="admin"
        )

    # Should have triggered CRITICAL alert
    assert mock_alert_manager.send_alert.called
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert call_args.severity == AlertSeverity.CRITICAL
    assert "Brute Force" in call_args.title


# ============================================================================
# SQL Injection Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_sql_injection_detection(security_monitor, mock_alert_manager):
    """Test SQL injection attempt triggers immediate alert"""
    ip_address = "10.0.0.4"
    payload = "' OR 1=1--"

    await security_monitor.track_sql_injection(
        user_id="attacker",
        ip_address=ip_address,
        payload=payload,
        field="username"
    )

    # Should trigger alert immediately (zero tolerance)
    assert mock_alert_manager.send_alert.called
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert "SQL Injection" in call_args.title
    assert call_args.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]


@pytest.mark.asyncio
async def test_sql_injection_threshold(security_monitor, mock_alert_manager):
    """Test that 3+ SQL injection attempts escalate to CRITICAL"""
    ip_address = "10.0.0.5"

    # Simulate 3 SQL injection attempts
    for i in range(3):
        await security_monitor.track_sql_injection(
            user_id="attacker",
            ip_address=ip_address,
            payload="' UNION SELECT *--",
            field="search"
        )

    # Last alert should be CRITICAL
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert call_args.severity == AlertSeverity.CRITICAL
    assert call_args.metadata.get("coordinated_attack") == True


# ============================================================================
# Privilege Escalation Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_privilege_escalation_alert(security_monitor, mock_alert_manager):
    """Test privilege escalation attempt triggers alert"""
    await security_monitor.track_privilege_escalation(
        user_id="user123",
        ip_address="10.0.0.6",
        attempted_action="delete_all_users",
        current_role="user",
        required_role="admin"
    )

    # Should trigger alert immediately
    assert mock_alert_manager.send_alert.called
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert "Privilege Escalation" in call_args.title
    assert call_args.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]


@pytest.mark.asyncio
async def test_privilege_escalation_repeated(security_monitor, mock_alert_manager):
    """Test repeated privilege escalation escalates severity"""
    user_id = "user456"
    ip_address = "10.0.0.7"

    # First attempt
    await security_monitor.track_privilege_escalation(
        user_id=user_id,
        ip_address=ip_address,
        attempted_action="view_admin_panel",
        current_role="user",
        required_role="admin"
    )

    # Second attempt
    await security_monitor.track_privilege_escalation(
        user_id=user_id,
        ip_address=ip_address,
        attempted_action="view_admin_panel",
        current_role="user",
        required_role="admin"
    )

    # Second alert should be CRITICAL
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert call_args.severity == AlertSeverity.CRITICAL


# ============================================================================
# Unusual API Pattern Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_api_rate_threshold(security_monitor, mock_alert_manager):
    """Test that 100+ API requests trigger rate limit alert"""
    ip_address = "10.0.0.8"
    user_id = "user789"

    # Simulate 100 API requests
    for i in range(100):
        await security_monitor.track_api_request(
            user_id=user_id,
            ip_address=ip_address,
            endpoint="/api/data",
            method="GET",
            status_code=200
        )

    # Should trigger alert
    assert mock_alert_manager.send_alert.called
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert "Unusual API" in call_args.title or "API Activity" in call_args.title


# ============================================================================
# Admin Account Creation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_admin_creation_alert(security_monitor, mock_alert_manager):
    """Test that admin account creation always triggers CRITICAL alert"""
    await security_monitor.track_admin_creation(
        creator_user_id="admin1",
        new_admin_user_id="admin2",
        new_admin_username="newadmin",
        creator_ip="10.0.0.9"
    )

    # Should trigger CRITICAL alert immediately
    assert mock_alert_manager.send_alert.called
    call_args = mock_alert_manager.send_alert.call_args[0][0]
    assert "Admin" in call_args.title
    assert call_args.severity == AlertSeverity.CRITICAL


# ============================================================================
# Event Cleanup Tests
# ============================================================================

def test_event_cleanup(security_monitor):
    """Test that old events are cleaned up properly"""
    ip_address = "10.0.0.10"

    # Add some old events
    now = datetime.utcnow()
    old_time = now - timedelta(seconds=400)

    # Manually add old events
    security_monitor.failed_logins[ip_address] = [old_time, old_time, now]

    # Cleanup should remove old events
    security_monitor._cleanup_old_events(
        security_monitor.failed_logins[ip_address],
        now,
        300  # 5 minute window
    )

    # Should only have 1 event left (the recent one)
    assert len(security_monitor.failed_logins[ip_address]) == 1


# ============================================================================
# Security Analysis Tests
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_security_events(security_monitor):
    """Test batch event analysis"""
    events = [
        SecurityEvent(
            event_type=ThreatPattern.FAILED_LOGIN,
            user_id=None,
            ip_address="10.0.0.1",
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.WARNING
        ),
        SecurityEvent(
            event_type=ThreatPattern.SQL_INJECTION,
            user_id="attacker",
            ip_address="10.0.0.2",
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.CRITICAL
        ),
    ]

    analysis = await security_monitor.analyze_security_events(events)

    assert analysis["total_events"] == 2
    assert len(analysis["by_type"]) > 0
    assert len(analysis["high_risk_ips"]) > 0


# ============================================================================
# Middleware Tests
# ============================================================================

@pytest.mark.asyncio
async def test_middleware_login_tracking():
    """Test middleware login tracking"""
    mock_monitor = Mock()
    mock_monitor.track_failed_login = AsyncMock()

    middleware = SecurityMonitoringMiddleware(monitor=mock_monitor)

    # Track failed login
    await middleware.track_login_attempt(
        success=False,
        user_id=None,
        username="admin",
        ip_address="10.0.0.11",
        reason="invalid_password"
    )

    # Should have called monitor
    assert mock_monitor.track_failed_login.called


@pytest.mark.asyncio
async def test_middleware_privilege_check():
    """Test middleware privilege escalation check"""
    mock_monitor = Mock()
    mock_monitor.track_privilege_escalation = AsyncMock()

    middleware = SecurityMonitoringMiddleware(monitor=mock_monitor)

    # Check privilege (user trying to access admin action)
    has_privilege = await middleware.check_privilege_escalation(
        user_id="user123",
        user_role="user",
        required_role="admin",
        action="delete_users",
        ip_address="10.0.0.12"
    )

    # Should return False (no privilege)
    assert has_privilege == False

    # Should have tracked escalation attempt
    assert mock_monitor.track_privilege_escalation.called


# ============================================================================
# Configuration Tests
# ============================================================================

def test_monitoring_thresholds(security_monitor):
    """Test that thresholds are properly configured"""
    assert security_monitor.FAILED_LOGIN_THRESHOLD == 5
    assert security_monitor.FAILED_LOGIN_WINDOW == 300
    assert security_monitor.BRUTE_FORCE_THRESHOLD == 10
    assert security_monitor.API_RATE_THRESHOLD == 100
    assert security_monitor.SQLI_THRESHOLD == 3


def test_on_call_schedule_loading(security_monitor):
    """Test on-call schedule configuration"""
    schedule = security_monitor.on_call_schedule

    assert "enabled" in schedule
    assert "primary" in schedule
    assert "escalation_timeout" in schedule


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_attack_scenario(security_monitor, mock_alert_manager):
    """
    Test complete attack scenario:
    1. Multiple failed logins
    2. SQL injection attempts
    3. Privilege escalation
    """
    attacker_ip = "10.0.0.99"

    # Phase 1: Brute force attack
    for i in range(5):
        await security_monitor.track_failed_login(
            user_id=None,
            ip_address=attacker_ip,
            username="admin"
        )

    # Phase 2: SQL injection
    await security_monitor.track_sql_injection(
        user_id="attacker",
        ip_address=attacker_ip,
        payload="' OR '1'='1",
        field="username"
    )

    # Phase 3: Privilege escalation
    await security_monitor.track_privilege_escalation(
        user_id="attacker",
        ip_address=attacker_ip,
        attempted_action="access_admin_panel",
        current_role="user",
        required_role="admin"
    )

    # Should have triggered multiple alerts
    assert mock_alert_manager.send_alert.call_count >= 3


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
