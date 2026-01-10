"""
Tests for SEC-025: Security Alerting and Monitoring
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from monitoring import (
    SecurityMonitor,
    ThreatPattern,
    SecurityEvent,
    SecurityMonitoringMiddleware,
    get_security_monitor
)

from security_alerts import (
    SecurityAlert,
    AlertSeverity,
    AlertChannel,
    SecurityAlertManager
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_alert_manager():
    """Mock alert manager for testing"""
    manager = Mock(spec=SecurityAlertManager)
    manager.send_alert = AsyncMock()
    return manager


@pytest.fixture
def security_monitor(mock_alert_manager):
    """Create SecurityMonitor with mocked alert manager"""
    return SecurityMonitor(alert_manager=mock_alert_manager)


@pytest.fixture
def monitoring_middleware(security_monitor):
    """Create SecurityMonitoringMiddleware with test monitor"""
    return SecurityMonitoringMiddleware(monitor=security_monitor)


# ============================================================================
# Failed Login Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_single_failed_login_no_alert(security_monitor, mock_alert_manager):
    """Single failed login should not trigger alert"""
    await security_monitor.track_failed_login(
        user_id="user123",
        ip_address="10.0.0.1",
        username="testuser"
    )

    # Should not send alert for single failure
    mock_alert_manager.send_alert.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_failed_logins_alert(security_monitor, mock_alert_manager):
    """5+ failed logins from same IP should trigger alert"""
    ip = "10.0.0.1"

    # Simulate 6 failed logins
    for i in range(6):
        await security_monitor.track_failed_login(
            user_id=f"user{i}",
            ip_address=ip,
            username=f"user{i}"
        )

    # Should send alert after threshold
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        await security_monitor.track_failed_login(
            user_id="user7",
            ip_address=ip,
            username="user7"
        )

        # Verify alert was sent
        assert mock_send.called
        call_args = mock_send.call_args[1]
        assert "Failed Login" in call_args["title"] or "Brute Force" in call_args["title"]
        assert call_args["ip_address"] == ip


@pytest.mark.asyncio
async def test_brute_force_detection(security_monitor):
    """10+ failed logins should be classified as brute force"""
    ip = "10.0.0.1"

    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        # Simulate 11 failed logins
        for i in range(11):
            await security_monitor.track_failed_login(
                user_id=None,
                ip_address=ip,
                username="admin"
            )

        # Verify brute force alert
        assert mock_send.called
        call_args = mock_send.call_args[1]
        assert call_args["event_type"] == ThreatPattern.BRUTE_FORCE.value
        assert call_args["severity"] == AlertSeverity.CRITICAL


# ============================================================================
# Privilege Escalation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_privilege_escalation_alert(security_monitor):
    """Privilege escalation attempt should always trigger alert"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        await security_monitor.track_privilege_escalation(
            user_id="user123",
            ip_address="10.0.0.2",
            attempted_action="delete_all_users",
            current_role="user",
            required_role="admin"
        )

        # Verify alert sent
        assert mock_send.called
        call_args = mock_send.call_args[1]
        assert call_args["title"] == "Privilege Escalation Attempt"
        assert call_args["event_type"] == ThreatPattern.PRIVILEGE_ESCALATION.value
        assert call_args["severity"] in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]


@pytest.mark.asyncio
async def test_repeated_privilege_escalation(security_monitor):
    """Repeated privilege escalation attempts should escalate severity"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        # First attempt
        await security_monitor.track_privilege_escalation(
            user_id="user123",
            ip_address="10.0.0.2",
            attempted_action="view_admin_panel",
            current_role="user",
            required_role="admin"
        )

        # Second attempt with SAME action - should be CRITICAL
        await security_monitor.track_privilege_escalation(
            user_id="user123",
            ip_address="10.0.0.2",
            attempted_action="view_admin_panel",  # Same action = repeated attempt
            current_role="user",
            required_role="admin"
        )

        # Check that second call used CRITICAL severity
        call_args = mock_send.call_args[1]
        assert call_args["severity"] == AlertSeverity.CRITICAL


# ============================================================================
# SQL Injection Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_sql_injection_alert(security_monitor):
    """SQL injection attempt should trigger immediate alert"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        await security_monitor.track_sql_injection(
            user_id="user123",
            ip_address="10.0.0.3",
            payload="' OR 1=1--",
            field="username"
        )

        # Verify alert sent immediately
        assert mock_send.called
        call_args = mock_send.call_args[1]
        assert call_args["title"] == "SQL Injection Attempt Detected"
        assert call_args["event_type"] == ThreatPattern.SQL_INJECTION.value
        assert "' OR 1=1--" in call_args["payload"]


@pytest.mark.asyncio
async def test_coordinated_sql_injection(security_monitor):
    """Multiple SQL injection attempts = coordinated attack"""
    ip = "10.0.0.3"

    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        # Simulate 3 attempts (meets threshold)
        payloads = ["' OR 1=1--", "'; DROP TABLE users--", "' UNION SELECT * FROM passwords--"]
        for payload in payloads:
            await security_monitor.track_sql_injection(
                user_id="user123",
                ip_address=ip,
                payload=payload,
                field="username"
            )

        # Last call should indicate coordinated attack
        call_args = mock_send.call_args[1]
        assert call_args["coordinated_attack"] is True
        assert call_args["severity"] == AlertSeverity.CRITICAL


# ============================================================================
# API Pattern Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_unusual_api_pattern(security_monitor):
    """Excessive API requests should trigger unusual pattern alert"""
    ip = "10.0.0.4"
    user_id = "user123"

    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        # Simulate 101 requests (over threshold of 100)
        for i in range(101):
            await security_monitor.track_api_request(
                user_id=user_id,
                ip_address=ip,
                endpoint="/api/data",
                method="GET",
                status_code=200
            )

        # Verify alert sent
        assert mock_send.called
        call_args = mock_send.call_args[1]
        assert call_args["event_type"] == ThreatPattern.UNUSUAL_API_PATTERN.value
        assert call_args["request_count"] >= 100


# ============================================================================
# Admin Account Creation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_admin_creation_alert(security_monitor):
    """Admin account creation should always trigger CRITICAL alert"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        await security_monitor.track_admin_creation(
            creator_user_id="admin1",
            new_admin_user_id="admin2",
            new_admin_username="newadmin",
            creator_ip="10.0.0.5"
        )

        # Verify CRITICAL alert sent
        assert mock_send.called
        call_args = mock_send.call_args[1]
        assert call_args["title"] == "New Admin Account Created"
        assert call_args["severity"] == AlertSeverity.CRITICAL
        assert call_args["event_type"] == ThreatPattern.ADMIN_ACCOUNT_CREATED.value


# ============================================================================
# Middleware Tests
# ============================================================================

@pytest.mark.asyncio
async def test_middleware_login_tracking(monitoring_middleware):
    """Middleware should track failed login attempts"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock):
        # Track failed login
        await monitoring_middleware.track_login_attempt(
            success=False,
            user_id="user123",
            username="testuser",
            ip_address="10.0.0.6",
            reason="invalid_password"
        )

        # Verify tracking occurred (no exception)
        assert True


@pytest.mark.asyncio
async def test_middleware_privilege_check(monitoring_middleware):
    """Middleware should detect and alert on privilege escalation"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        # User without admin privilege attempts admin action
        has_privilege = await monitoring_middleware.check_privilege_escalation(
            user_id="user123",
            user_role="user",
            required_role="admin",
            action="delete_user",
            ip_address="10.0.0.7"
        )

        # Should return False (no privilege)
        assert has_privilege is False

        # Should send alert
        assert mock_send.called


@pytest.mark.asyncio
async def test_middleware_admin_privilege_check(monitoring_middleware):
    """Middleware should allow admin actions for admin users"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        # Admin user performs admin action
        has_privilege = await monitoring_middleware.check_privilege_escalation(
            user_id="admin1",
            user_role="admin",
            required_role="admin",
            action="delete_user",
            ip_address="10.0.0.8"
        )

        # Should return True (has privilege)
        assert has_privilege is True

        # Should NOT send alert
        mock_send.assert_not_called()


# ============================================================================
# Event Analysis Tests
# ============================================================================

@pytest.mark.asyncio
async def test_batch_event_analysis(security_monitor):
    """Analyze batch of events for patterns"""
    events = [
        SecurityEvent(
            event_type=ThreatPattern.FAILED_LOGIN,
            user_id="user1",
            ip_address="10.0.0.1",
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.WARNING
        ),
        SecurityEvent(
            event_type=ThreatPattern.SQL_INJECTION,
            user_id="user2",
            ip_address="10.0.0.2",
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.CRITICAL
        ),
        SecurityEvent(
            event_type=ThreatPattern.FAILED_LOGIN,
            user_id="user1",
            ip_address="10.0.0.1",
            timestamp=datetime.utcnow(),
            severity=AlertSeverity.WARNING
        ),
    ]

    analysis = await security_monitor.analyze_security_events(events)

    # Verify analysis
    assert analysis["total_events"] == 3
    assert analysis["by_type"][ThreatPattern.FAILED_LOGIN.value] == 2
    assert analysis["by_type"][ThreatPattern.SQL_INJECTION.value] == 1
    assert "10.0.0.2" in analysis["high_risk_ips"]  # SQL injection IP
    assert len(analysis["recommendations"]) > 0


# ============================================================================
# Alert Manager Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_alert_severity_routing():
    """Test that different severities route to correct channels"""
    manager = SecurityAlertManager()

    # Check routing configuration
    assert AlertChannel.TELEGRAM in manager.severity_routing[AlertSeverity.INFO]
    assert AlertChannel.PAGERDUTY in manager.severity_routing[AlertSeverity.CRITICAL]
    assert AlertChannel.SLACK in manager.severity_routing[AlertSeverity.ERROR]


def test_alert_throttling():
    """Test alert throttling to prevent spam"""
    manager = SecurityAlertManager()

    alert = SecurityAlert(
        title="Test Alert",
        message="Test message",
        severity=AlertSeverity.WARNING,
        event_type="test.event",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        user_id="user123",
        ip_address="10.0.0.1",
        metadata={}
    )

    # First alert should not be throttled
    assert not manager._should_throttle(alert)

    # Record alert
    manager._should_throttle(alert)

    # Simulate rapid alerts (within same window)
    for _ in range(5):
        manager._should_throttle(alert)

    # Should now be throttled
    assert manager._should_throttle(alert)


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_full_monitoring_flow():
    """Test complete monitoring and alerting flow"""
    with patch('monitoring.send_security_alert', new_callable=AsyncMock) as mock_send:
        monitor = SecurityMonitor()

        # Simulate attack sequence
        ip = "10.0.0.99"

        # 1. Failed logins (brute force)
        for i in range(6):
            await monitor.track_failed_login(
                user_id=None,
                ip_address=ip,
                username="admin"
            )

        # 2. SQL injection
        await monitor.track_sql_injection(
            user_id="attacker",
            ip_address=ip,
            payload="' OR 1=1--",
            field="username"
        )

        # 3. Privilege escalation
        await monitor.track_privilege_escalation(
            user_id="attacker",
            ip_address=ip,
            attempted_action="access_admin_panel",
            current_role="user",
            required_role="admin"
        )

        # Verify multiple alerts sent
        assert mock_send.call_count >= 3


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
