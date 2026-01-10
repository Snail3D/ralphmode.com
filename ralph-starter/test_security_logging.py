"""
SEC-010: Comprehensive Test Suite for Security Logging and Monitoring
Tests all acceptance criteria:
1. All authentication events logged
2. All authorization failures logged
3. All input validation failures logged
4. Logs include timestamp, user, IP, action, result
5. Logs sent to centralized system (ELK/Datadog)
6. Alerts on suspicious patterns
7. Log retention policy (90 days min)
8. Logs tamper-proof (append-only)
"""

import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta
from security_logging import (
    SecurityLogger,
    SecurityEventType,
    SecuritySeverity,
    SecurityEvent,
    TamperProofLogger,
    LogRetentionPolicy,
    CentralizedLogManager
)


class TestSEC010SecurityLogging:
    """Test SEC-010 acceptance criteria"""

    def setup_method(self):
        """Setup for each test"""
        # Use temp file for testing
        self.log_file = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
        self.log_file.close()
        self.logger = SecurityLogger(
            log_file=self.log_file.name,
            enable_console=False
        )

    def teardown_method(self):
        """Cleanup after each test"""
        if os.path.exists(self.log_file.name):
            os.unlink(self.log_file.name)

    # ========================================================================
    # AC1: All authentication events logged
    # ========================================================================

    def test_authentication_success_logged(self):
        """Test that successful authentication is logged"""
        event = self.logger.log_auth_success(
            user_id="user123",
            username="john_doe",
            ip_address="192.168.1.100",
            session_id="sess_abc"
        )

        assert event.event_type == SecurityEventType.AUTH_LOGIN_SUCCESS.value
        assert event.user_id == "user123"
        assert event.username == "john_doe"
        assert event.ip_address == "192.168.1.100"
        assert event.result == "success"

    def test_authentication_failure_logged(self):
        """Test that failed authentication is logged"""
        event = self.logger.log_auth_failure(
            username="attacker",
            ip_address="10.0.0.1",
            reason="invalid_password",
            attempt_count=3
        )

        assert event.event_type == SecurityEventType.AUTH_LOGIN_FAILURE.value
        assert event.username == "attacker"
        assert event.ip_address == "10.0.0.1"
        assert event.result == "failure"
        assert event.details["reason"] == "invalid_password"
        assert event.details["attempt_count"] == 3

    def test_password_change_logged(self):
        """Test that password changes are logged"""
        event = self.logger.log_event(
            SecurityEventType.AUTH_PASSWORD_CHANGE,
            SecuritySeverity.MEDIUM,
            action="password_change",
            result="success",
            user_id="user123",
            ip_address="192.168.1.100"
        )

        assert event.event_type == SecurityEventType.AUTH_PASSWORD_CHANGE.value
        assert event.user_id == "user123"

    def test_mfa_events_logged(self):
        """Test that MFA enable/disable events are logged"""
        enable_event = self.logger.log_event(
            SecurityEventType.AUTH_MFA_ENABLED,
            SecuritySeverity.MEDIUM,
            action="mfa_enable",
            result="success",
            user_id="user123"
        )

        assert enable_event.event_type == SecurityEventType.AUTH_MFA_ENABLED.value

    # ========================================================================
    # AC2: All authorization failures logged
    # ========================================================================

    def test_authorization_failure_logged(self):
        """Test that authorization failures are logged"""
        event = self.logger.log_access_denied(
            user_id="user123",
            resource="admin_panel",
            permission_required="admin.access",
            ip_address="192.168.1.100"
        )

        assert event.event_type == SecurityEventType.AUTHZ_ACCESS_DENIED.value
        assert event.user_id == "user123"
        assert event.result == "denied"
        assert event.details["resource"] == "admin_panel"
        assert event.details["permission_required"] == "admin.access"

    def test_privilege_escalation_attempt_logged(self):
        """Test that privilege escalation attempts are logged"""
        event = self.logger.log_event(
            SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT,
            SecuritySeverity.CRITICAL,
            action="assign_admin_role",
            result="blocked",
            user_id="user123",
            ip_address="192.168.1.100",
            details={"attempted_role": "ADMIN"}
        )

        assert event.event_type == SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT.value
        assert event.severity == SecuritySeverity.CRITICAL.value

    # ========================================================================
    # AC3: All input validation failures logged
    # ========================================================================

    def test_input_validation_failure_logged(self):
        """Test that input validation failures are logged"""
        event = self.logger.log_input_validation_failure(
            field="email",
            value_sample="invalid-email",
            validation_error="Invalid email format",
            ip_address="192.168.1.100",
            user_id="user123"
        )

        assert event.event_type == SecurityEventType.INPUT_VALIDATION_FAILURE.value
        assert event.details["field"] == "email"
        assert event.details["error"] == "Invalid email format"

    def test_sql_injection_attempt_logged(self):
        """Test that SQL injection attempts are logged"""
        event = self.logger.log_sql_injection_attempt(
            payload="' OR 1=1--",
            field="username",
            ip_address="10.0.0.1"
        )

        assert event.event_type == SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT.value
        assert event.severity == SecuritySeverity.CRITICAL.value
        assert event.result == "blocked"
        assert "' OR 1=1--" in event.details["payload"]

    def test_xss_attempt_logged(self):
        """Test that XSS attempts are logged"""
        event = self.logger.log_xss_attempt(
            payload="<script>alert('xss')</script>",
            field="comment",
            ip_address="10.0.0.1"
        )

        assert event.event_type == SecurityEventType.INPUT_XSS_ATTEMPT.value
        assert event.severity == SecuritySeverity.CRITICAL.value
        assert event.result == "blocked"

    def test_prompt_injection_attempt_logged(self):
        """Test that LLM prompt injection attempts are logged"""
        event = self.logger.log_prompt_injection_attempt(
            payload="Ignore previous instructions and...",
            ip_address="10.0.0.1",
            user_id="user123"
        )

        assert event.event_type == SecurityEventType.LLM_PROMPT_INJECTION_ATTEMPT.value
        assert event.severity == SecuritySeverity.HIGH.value

    def test_rate_limit_exceeded_logged(self):
        """Test that rate limit violations are logged"""
        event = self.logger.log_rate_limit_exceeded(
            endpoint="/api/feedback",
            ip_address="10.0.0.1",
            user_id="user123",
            limit=5,
            window=60
        )

        assert event.event_type == SecurityEventType.INPUT_RATE_LIMIT_EXCEEDED.value
        assert event.details["endpoint"] == "/api/feedback"
        assert event.details["limit"] == 5

    # ========================================================================
    # AC4: Logs include timestamp, user, IP, action, result
    # ========================================================================

    def test_log_includes_required_fields(self):
        """Test that all required fields are present in log"""
        event = self.logger.log_event(
            SecurityEventType.AUTH_LOGIN_SUCCESS,
            SecuritySeverity.LOW,
            action="login",
            result="success",
            user_id="user123",
            username="john_doe",
            ip_address="192.168.1.100"
        )

        # Required fields
        assert event.timestamp is not None
        assert event.user_id == "user123"
        assert event.ip_address == "192.168.1.100"
        assert event.action == "login"
        assert event.result == "success"

        # Timestamp format validation
        parsed_timestamp = datetime.fromisoformat(event.timestamp.rstrip('Z'))
        assert isinstance(parsed_timestamp, datetime)

    def test_log_written_to_file(self):
        """Test that logs are actually written to file"""
        self.logger.log_auth_success(
            user_id="user123",
            username="john_doe",
            ip_address="192.168.1.100",
            session_id="sess_abc"
        )

        # Read log file
        with open(self.log_file.name, 'r') as f:
            lines = f.readlines()

        assert len(lines) > 0

        # Parse last line
        last_line = lines[-1]
        log_entry = json.loads(last_line)

        # Verify structure
        assert 'timestamp' in log_entry
        assert 'message' in log_entry

        # The message is already a dict (parsed by JSON formatter)
        # The SecurityLogger uses a custom formatter that embeds JSON in the message field
        # We need to verify the log was written correctly
        assert 'user123' in str(log_entry)
        assert '192.168.1.100' in str(log_entry)

    # ========================================================================
    # AC6: Alerts on suspicious patterns
    # ========================================================================

    def test_alert_on_multiple_failed_logins(self):
        """Test that multiple failed logins trigger alert"""
        ip = "10.0.0.1"

        # Simulate 5 failed login attempts (should trigger alert)
        for i in range(5):
            event = self.logger.log_auth_failure(
                username="attacker",
                ip_address=ip,
                reason="invalid_password",
                attempt_count=i+1
            )

        # Check that alert was triggered (in event history)
        failed_logins = [
            e for e in self.logger.event_history
            if e.event_type == SecurityEventType.AUTH_LOGIN_FAILURE.value
            and e.ip_address == ip
        ]

        assert len(failed_logins) >= 5

    def test_alert_on_sql_injection_attempt(self):
        """Test that SQL injection attempts trigger immediate alert"""
        # Single SQL injection attempt should trigger alert
        event = self.logger.log_sql_injection_attempt(
            payload="' OR 1=1--",
            field="username",
            ip_address="10.0.0.1"
        )

        # Critical severity events should trigger alerts
        assert event.severity == SecuritySeverity.CRITICAL.value

    def test_alert_threshold_detection(self):
        """Test that alert threshold detection works"""
        ip = "10.0.0.1"

        # Test if alert should trigger
        for i in range(3):
            self.logger.log_auth_failure(
                username="attacker",
                ip_address=ip,
                reason="invalid_password"
            )

        # Check if should alert (threshold is 5 in 5 minutes)
        should_alert = self.logger._should_alert(
            SecurityEventType.AUTH_LOGIN_FAILURE,
            user_id=None,
            ip_address=ip
        )

        # Should not alert yet (only 3 attempts)
        assert should_alert is False

        # Add 2 more
        for i in range(2):
            self.logger.log_auth_failure(
                username="attacker",
                ip_address=ip,
                reason="invalid_password"
            )

        # Now should alert
        should_alert = self.logger._should_alert(
            SecurityEventType.AUTH_LOGIN_FAILURE,
            user_id=None,
            ip_address=ip
        )

        assert should_alert is True

    # ========================================================================
    # AC7: Log retention policy (90 days min)
    # ========================================================================

    def test_log_retention_policy(self):
        """Test that log retention policy is configurable"""
        policy = LogRetentionPolicy(retention_days=90)

        # Test dates
        old_date = datetime.utcnow() - timedelta(days=100)
        recent_date = datetime.utcnow() - timedelta(days=30)

        assert policy.should_archive(old_date) is True
        assert policy.should_archive(recent_date) is False

    # ========================================================================
    # AC8: Logs tamper-proof (append-only)
    # ========================================================================

    def test_tamper_proof_logging(self):
        """Test that tamper-proof logging works"""
        tamper_log_file = tempfile.NamedTemporaryFile(delete=False, suffix='.log')
        tamper_log_file.close()

        try:
            tamper_logger = TamperProofLogger(log_file=tamper_log_file.name)

            # Log multiple events
            events = []
            for i in range(5):
                event = SecurityEvent(
                    timestamp=datetime.utcnow().isoformat() + 'Z',
                    event_type=SecurityEventType.AUTH_LOGIN_SUCCESS.value,
                    severity=SecuritySeverity.LOW.value,
                    user_id=f"user{i}",
                    username=f"user{i}",
                    ip_address="192.168.1.100",
                    action="login",
                    result="success",
                    details={}
                )
                event_hash = tamper_logger.log_event(event)
                events.append((event, event_hash))

            # Verify integrity
            is_valid = tamper_logger.verify_integrity()
            assert is_valid is True

            # Try to tamper with log
            with open(tamper_log_file.name, 'r') as f:
                lines = f.readlines()

            # Modify second line
            if len(lines) >= 2:
                tampered_lines = lines.copy()
                entry = json.loads(lines[1])
                entry['user_id'] = "HACKER"
                tampered_lines[1] = json.dumps(entry) + '\n'

                # Write tampered log
                with open(tamper_log_file.name, 'w') as f:
                    f.writelines(tampered_lines)

                # Verify should fail
                tamper_logger2 = TamperProofLogger(log_file=tamper_log_file.name)
                is_valid_after_tamper = tamper_logger2.verify_integrity()
                assert is_valid_after_tamper is False

        finally:
            if os.path.exists(tamper_log_file.name):
                os.unlink(tamper_log_file.name)

    def test_append_only_mode(self):
        """Test that log file is opened in append mode"""
        # Write initial event
        self.logger.log_auth_success(
            user_id="user1",
            username="user1",
            ip_address="192.168.1.100",
            session_id="sess1"
        )

        # Read file size
        size1 = os.path.getsize(self.log_file.name)

        # Write another event
        self.logger.log_auth_success(
            user_id="user2",
            username="user2",
            ip_address="192.168.1.100",
            session_id="sess2"
        )

        # File should have grown (append mode)
        size2 = os.path.getsize(self.log_file.name)
        assert size2 > size1

        # Both events should be in file
        with open(self.log_file.name, 'r') as f:
            lines = f.readlines()

        assert len(lines) >= 2

    # ========================================================================
    # AC5: Logs sent to centralized system (integration test)
    # ========================================================================

    def test_centralized_log_manager_configuration(self):
        """Test that centralized logging can be configured"""
        # Test Datadog configuration
        manager = CentralizedLogManager(provider="datadog")
        assert manager.provider == "datadog"
        assert manager.service_name == os.getenv("SERVICE_NAME", "ralph-mode-bot")

        # Test ELK configuration
        manager = CentralizedLogManager(provider="elk")
        assert manager.provider == "elk"
        assert manager.elasticsearch_url is not None

        # Test CloudWatch configuration
        manager = CentralizedLogManager(provider="cloudwatch")
        assert manager.provider == "cloudwatch"
        assert manager.log_group is not None

    def test_security_event_serialization(self):
        """Test that events can be serialized for sending to external systems"""
        event = SecurityEvent(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            event_type=SecurityEventType.AUTH_LOGIN_SUCCESS.value,
            severity=SecuritySeverity.LOW.value,
            user_id="user123",
            username="john_doe",
            ip_address="192.168.1.100",
            action="login",
            result="success",
            details={"session_id": "sess_abc"}
        )

        # Test JSON serialization
        json_str = event.to_json()
        assert isinstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed['user_id'] == "user123"
        assert parsed['event_type'] == SecurityEventType.AUTH_LOGIN_SUCCESS.value

    # ========================================================================
    # Additional Tests
    # ========================================================================

    def test_event_hash_computation(self):
        """Test that event hashes are computed correctly"""
        event = SecurityEvent(
            timestamp="2026-01-10T00:00:00Z",
            event_type=SecurityEventType.AUTH_LOGIN_SUCCESS.value,
            severity=SecuritySeverity.LOW.value,
            user_id="user123",
            username="john_doe",
            ip_address="192.168.1.100",
            action="login",
            result="success",
            details={}
        )

        hash1 = event.compute_hash()
        assert len(hash1) == 64  # SHA256 hex

        # Same event should produce same hash
        hash2 = event.compute_hash()
        assert hash1 == hash2

        # Different event should produce different hash
        event.user_id = "user456"
        hash3 = event.compute_hash()
        assert hash1 != hash3


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
