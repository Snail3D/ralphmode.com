"""
SEC-010: Insufficient Logging and Monitoring
Comprehensive security logging with audit trails, alerting, and incident response.

OWASP Top 10 2021: A09 - Security Logging and Monitoring Failures
"""

import logging
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import os
from secure_deserializer import safe_json_loads, DeserializationError

# SEC-020: Import PII masking for log safety
try:
    from pii_handler import PIIMasker, PIIField
    PII_MASKING_AVAILABLE = True
except ImportError:
    PII_MASKING_AVAILABLE = False
    logging.warning("SEC-020: PII masking not available - logs may contain unmasked PII")


# ============================================================================
# Event Types and Severity Levels
# ============================================================================

class SecurityEventType(Enum):
    """Security event types for classification"""
    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_PASSWORD_CHANGE = "auth.password_change"
    AUTH_PASSWORD_RESET_REQUEST = "auth.password_reset.request"
    AUTH_PASSWORD_RESET_COMPLETE = "auth.password_reset.complete"
    AUTH_MFA_ENABLED = "auth.mfa.enabled"
    AUTH_MFA_DISABLED = "auth.mfa.disabled"
    AUTH_SESSION_EXPIRED = "auth.session.expired"
    AUTH_SESSION_HIJACK_ATTEMPT = "auth.session.hijack_attempt"

    # Authorization events
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    AUTHZ_PERMISSION_DENIED = "authz.permission.denied"
    AUTHZ_ROLE_CHANGED = "authz.role.changed"
    AUTHZ_PRIVILEGE_ESCALATION_ATTEMPT = "authz.privilege_escalation"

    # Input validation events
    INPUT_VALIDATION_FAILURE = "input.validation.failure"
    INPUT_SQL_INJECTION_ATTEMPT = "input.sqli.attempt"
    INPUT_XSS_ATTEMPT = "input.xss.attempt"
    INPUT_CSRF_FAILURE = "input.csrf.failure"
    INPUT_RATE_LIMIT_EXCEEDED = "input.rate_limit.exceeded"

    # Data access events
    DATA_ACCESS_SENSITIVE = "data.access.sensitive"
    DATA_EXPORT = "data.export"
    DATA_DELETION = "data.deletion"
    DATA_MODIFICATION = "data.modification"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_CONFIG_CHANGE = "system.config.change"
    SYSTEM_ADMIN_ACTION = "system.admin.action"

    # LLM-specific events
    LLM_PROMPT_INJECTION_ATTEMPT = "llm.prompt_injection.attempt"
    LLM_JAILBREAK_ATTEMPT = "llm.jailbreak.attempt"
    LLM_EXCESSIVE_TOKENS = "llm.excessive_tokens"

    # Telegram bot events
    TELEGRAM_BOT_MESSAGE_RECEIVED = "telegram.bot.message"
    TELEGRAM_CALLBACK_INVALID = "telegram.callback.invalid"
    TELEGRAM_UNAUTHORIZED_COMMAND = "telegram.unauthorized.command"


class SecuritySeverity(Enum):
    """Security event severity levels"""
    LOW = "low"           # Informational, expected behavior
    MEDIUM = "medium"     # Unusual but not necessarily malicious
    HIGH = "high"         # Likely attack, needs investigation
    CRITICAL = "critical" # Active attack, immediate response needed


# ============================================================================
# Security Event
# ============================================================================

@dataclass
class SecurityEvent:
    """Structured security event for logging"""
    timestamp: str
    event_type: str
    severity: str
    user_id: Optional[str]
    username: Optional[str]
    ip_address: Optional[str]
    action: str
    result: str
    details: Dict[str, Any]
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self, mask_pii: bool = True) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Args:
            mask_pii: If True, mask PII fields for safe logging (default: True)
        """
        data = asdict(self)

        # SEC-020: Mask PII in logs
        if mask_pii and PII_MASKING_AVAILABLE:
            # Mask username
            if data.get("username"):
                data["username"] = PIIMasker.mask_string(data["username"])

            # Mask user_id if it looks like a telegram_id
            if data.get("user_id") and data["user_id"].isdigit():
                data["user_id"] = PIIMasker.mask_telegram_id(int(data["user_id"]))

            # Mask PII in details dict
            if isinstance(data.get("details"), dict):
                data["details"] = PIIMasker.mask_dict(data["details"])

        return data

    def to_json(self, mask_pii: bool = True) -> str:
        """
        Convert to JSON string.

        Args:
            mask_pii: If True, mask PII fields for safe logging (default: True)
        """
        return json.dumps(self.to_dict(mask_pii=mask_pii))

    def compute_hash(self) -> str:
        """Compute tamper-proof hash of event (for append-only verification)"""
        data = self.to_json()
        return hashlib.sha256(data.encode()).hexdigest()


# ============================================================================
# Security Logger
# ============================================================================

class SecurityLogger:
    """
    Enterprise-grade security logging with:
    - Structured JSON logging
    - Tamper-proof audit trail
    - Centralized logging support
    - Automatic alerting on suspicious patterns
    """

    def __init__(
        self,
        log_file: str = "security_audit.log",
        log_level: int = logging.INFO,
        enable_console: bool = True
    ):
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(log_level)

        # JSON formatter for structured logs
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","message":%(message)s}'
        )

        # File handler (append-only for tamper-proof logs)
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler (optional, for development)
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Event history for pattern detection (in-memory, last 1000 events)
        self.event_history: List[SecurityEvent] = []
        self.max_history = 1000

        # Alert thresholds
        self.alert_thresholds = {
            SecurityEventType.AUTH_LOGIN_FAILURE: (5, 300),  # 5 failures in 5 min
            SecurityEventType.AUTHZ_ACCESS_DENIED: (10, 300),  # 10 denials in 5 min
            SecurityEventType.INPUT_VALIDATION_FAILURE: (20, 300),  # 20 in 5 min
            SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT: (1, 60),  # 1 attempt = alert
            SecurityEventType.INPUT_XSS_ATTEMPT: (1, 60),  # 1 attempt = alert
            SecurityEventType.LLM_PROMPT_INJECTION_ATTEMPT: (3, 300),  # 3 in 5 min
        }

    def log_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        action: str,
        result: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> SecurityEvent:
        """
        Log a security event with full context

        Args:
            event_type: Type of security event
            severity: Severity level
            action: What action was attempted
            result: Outcome (success, failure, blocked, etc.)
            user_id: User ID if applicable
            username: Username if applicable
            ip_address: Source IP address
            details: Additional context (dict)
            session_id: Session identifier
            request_id: Request identifier for correlation

        Returns:
            SecurityEvent: The logged event
        """
        event = SecurityEvent(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            event_type=event_type.value,
            severity=severity.value,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            action=action,
            result=result,
            details=details or {},
            session_id=session_id,
            request_id=request_id
        )

        # Log to file
        log_method = self._get_log_method(severity)
        log_method(event.to_json())

        # Add to history for pattern detection
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Check for suspicious patterns
        if self._should_alert(event_type, user_id, ip_address):
            self._trigger_alert(event_type, user_id, ip_address)

        return event

    def _get_log_method(self, severity: SecuritySeverity):
        """Get appropriate logging method based on severity"""
        severity_map = {
            SecuritySeverity.LOW: self.logger.info,
            SecuritySeverity.MEDIUM: self.logger.warning,
            SecuritySeverity.HIGH: self.logger.error,
            SecuritySeverity.CRITICAL: self.logger.critical,
        }
        return severity_map.get(severity, self.logger.info)

    def _should_alert(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str],
        ip_address: Optional[str]
    ) -> bool:
        """Check if event pattern triggers alert threshold"""
        if event_type not in self.alert_thresholds:
            return False

        count_threshold, time_window = self.alert_thresholds[event_type]
        cutoff_time = datetime.utcnow() - timedelta(seconds=time_window)

        # Count matching events in time window
        matching_events = [
            e for e in self.event_history
            if e.event_type == event_type.value
            and datetime.fromisoformat(e.timestamp.rstrip('Z')) > cutoff_time
            and (user_id is None or e.user_id == user_id)
            and (ip_address is None or e.ip_address == ip_address)
        ]

        return len(matching_events) >= count_threshold

    def _trigger_alert(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str],
        ip_address: Optional[str]
    ):
        """Trigger security alert (can integrate with Datadog, PagerDuty, etc.)"""
        alert_msg = {
            "alert": "SECURITY_THRESHOLD_EXCEEDED",
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "action_required": "INVESTIGATE_IMMEDIATELY"
        }
        self.logger.critical(json.dumps(alert_msg))

        # TODO: Integrate with alerting service (PagerDuty, Datadog, etc.)
        # self._send_to_pagerduty(alert_msg)
        # self._send_to_datadog(alert_msg)

    # ========================================================================
    # Convenience methods for common events
    # ========================================================================

    def log_auth_success(self, user_id: str, username: str, ip_address: str, session_id: str):
        """Log successful authentication"""
        return self.log_event(
            SecurityEventType.AUTH_LOGIN_SUCCESS,
            SecuritySeverity.LOW,
            action="login",
            result="success",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            session_id=session_id
        )

    def log_auth_failure(
        self,
        username: str,
        ip_address: str,
        reason: str,
        attempt_count: int = 1
    ):
        """Log failed authentication attempt"""
        return self.log_event(
            SecurityEventType.AUTH_LOGIN_FAILURE,
            SecuritySeverity.MEDIUM,
            action="login",
            result="failure",
            username=username,
            ip_address=ip_address,
            details={"reason": reason, "attempt_count": attempt_count}
        )

    def log_access_denied(
        self,
        user_id: str,
        resource: str,
        permission_required: str,
        ip_address: str
    ):
        """Log authorization failure"""
        return self.log_event(
            SecurityEventType.AUTHZ_ACCESS_DENIED,
            SecuritySeverity.MEDIUM,
            action=f"access_{resource}",
            result="denied",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "resource": resource,
                "permission_required": permission_required
            }
        )

    def log_input_validation_failure(
        self,
        field: str,
        value_sample: str,
        validation_error: str,
        ip_address: str,
        user_id: Optional[str] = None
    ):
        """Log input validation failure"""
        return self.log_event(
            SecurityEventType.INPUT_VALIDATION_FAILURE,
            SecuritySeverity.MEDIUM,
            action=f"validate_{field}",
            result="failure",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "field": field,
                "value_sample": value_sample[:50],  # First 50 chars only
                "error": validation_error
            }
        )

    def log_sql_injection_attempt(
        self,
        payload: str,
        field: str,
        ip_address: str,
        user_id: Optional[str] = None
    ):
        """Log SQL injection attempt"""
        return self.log_event(
            SecurityEventType.INPUT_SQL_INJECTION_ATTEMPT,
            SecuritySeverity.CRITICAL,
            action=f"sql_inject_{field}",
            result="blocked",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "payload": payload[:100],  # First 100 chars
                "field": field,
                "attack_type": "sql_injection"
            }
        )

    def log_xss_attempt(
        self,
        payload: str,
        field: str,
        ip_address: str,
        user_id: Optional[str] = None
    ):
        """Log XSS attempt"""
        return self.log_event(
            SecurityEventType.INPUT_XSS_ATTEMPT,
            SecuritySeverity.CRITICAL,
            action=f"xss_inject_{field}",
            result="blocked",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "payload": payload[:100],
                "field": field,
                "attack_type": "xss"
            }
        )

    def log_prompt_injection_attempt(
        self,
        payload: str,
        ip_address: str,
        user_id: Optional[str] = None
    ):
        """Log LLM prompt injection attempt"""
        return self.log_event(
            SecurityEventType.LLM_PROMPT_INJECTION_ATTEMPT,
            SecuritySeverity.HIGH,
            action="llm_prompt_inject",
            result="blocked",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "payload": payload[:100],
                "attack_type": "prompt_injection"
            }
        )

    def log_rate_limit_exceeded(
        self,
        endpoint: str,
        ip_address: str,
        user_id: Optional[str] = None,
        limit: int = 0,
        window: int = 0
    ):
        """Log rate limit exceeded"""
        return self.log_event(
            SecurityEventType.INPUT_RATE_LIMIT_EXCEEDED,
            SecuritySeverity.MEDIUM,
            action=f"rate_limit_{endpoint}",
            result="blocked",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "endpoint": endpoint,
                "limit": limit,
                "window_seconds": window
            }
        )


# ============================================================================
# Centralized Logging Integration
# ============================================================================

class CentralizedLogManager:
    """
    Integration with centralized logging systems:
    - ELK Stack (Elasticsearch, Logstash, Kibana)
    - Datadog
    - Splunk
    - AWS CloudWatch
    """

    def __init__(self, provider: str = "datadog"):
        self.provider = provider
        self._configure_provider()

    def _configure_provider(self):
        """Configure provider-specific settings"""
        if self.provider == "datadog":
            # Datadog configuration
            self.api_key = os.getenv("DATADOG_API_KEY")
            self.app_key = os.getenv("DATADOG_APP_KEY")
            self.service_name = os.getenv("SERVICE_NAME", "ralph-mode-bot")

        elif self.provider == "elk":
            # ELK Stack configuration
            self.elasticsearch_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            self.index_name = os.getenv("ELK_INDEX", "security-logs")

        elif self.provider == "cloudwatch":
            # AWS CloudWatch configuration
            self.log_group = os.getenv("CLOUDWATCH_LOG_GROUP", "/aws/ralph-mode/security")
            self.log_stream = os.getenv("CLOUDWATCH_LOG_STREAM", "security-audit")

    def send_event(self, event: SecurityEvent):
        """Send event to centralized logging system"""
        if self.provider == "datadog":
            self._send_to_datadog(event)
        elif self.provider == "elk":
            self._send_to_elasticsearch(event)
        elif self.provider == "cloudwatch":
            self._send_to_cloudwatch(event)

    def _send_to_datadog(self, event: SecurityEvent):
        """Send to Datadog (via HTTP API or agent)"""
        # TODO: Implement Datadog integration
        # Example: use datadog.api.Event.create()
        pass

    def _send_to_elasticsearch(self, event: SecurityEvent):
        """Send to Elasticsearch"""
        # TODO: Implement Elasticsearch integration
        # Example: use elasticsearch-py client
        pass

    def _send_to_cloudwatch(self, event: SecurityEvent):
        """Send to AWS CloudWatch"""
        # TODO: Implement CloudWatch integration
        # Example: use boto3.client('logs').put_log_events()
        pass


# ============================================================================
# Log Retention Policy
# ============================================================================

class LogRetentionPolicy:
    """
    Manage log retention:
    - Minimum 90 days for security logs (compliance requirement)
    - Compression of old logs
    - Archival to cold storage
    """

    def __init__(self, retention_days: int = 90):
        self.retention_days = retention_days

    def should_archive(self, log_date: datetime) -> bool:
        """Check if log should be archived"""
        age_days = (datetime.utcnow() - log_date).days
        return age_days > self.retention_days

    def compress_old_logs(self, log_dir: str = "."):
        """Compress logs older than retention period"""
        # TODO: Implement log compression
        # Example: gzip logs older than 90 days
        pass

    def archive_to_s3(self, log_file: str):
        """Archive logs to S3 for long-term storage"""
        # TODO: Implement S3 archival
        # Example: use boto3.client('s3').upload_file()
        pass


# ============================================================================
# Tamper-Proof Logging
# ============================================================================

class TamperProofLogger:
    """
    Append-only logging with cryptographic verification.
    Each log entry includes hash of previous entry (blockchain-like).
    """

    def __init__(self, log_file: str = "tamper_proof_audit.log"):
        self.log_file = log_file
        self.previous_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        """Get hash of last log entry"""
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    # SEC-008: Use secure deserialization
                    last_line = safe_json_loads(lines[-1].strip())
                    return last_line.get('hash', '0' * 64)
        except (FileNotFoundError, DeserializationError):
            pass
        return '0' * 64  # Genesis hash

    def log_event(self, event: SecurityEvent) -> str:
        """
        Log event with tamper-proof chain

        Returns:
            str: Hash of logged event
        """
        # Compute hash including previous hash (blockchain-like)
        event_data = event.to_dict()
        event_data['previous_hash'] = self.previous_hash

        event_json = json.dumps(event_data)
        current_hash = hashlib.sha256(event_json.encode()).hexdigest()
        event_data['hash'] = current_hash

        # Append to log file (append-only mode)
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event_data) + '\n')

        self.previous_hash = current_hash
        return current_hash

    def verify_integrity(self) -> bool:
        """Verify log integrity by checking hash chain"""
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()

            previous_hash = '0' * 64
            for i, line in enumerate(lines):
                # SEC-008: Use secure deserialization
                entry = safe_json_loads(line.strip())

                # Check if previous_hash matches
                if entry.get('previous_hash') != previous_hash:
                    print(f"Integrity violation at line {i+1}: previous_hash mismatch")
                    return False

                # Recompute hash
                stored_hash = entry.pop('hash')
                recomputed = hashlib.sha256(json.dumps(entry).encode()).hexdigest()

                if stored_hash != recomputed:
                    print(f"Integrity violation at line {i+1}: hash mismatch")
                    return False

                previous_hash = stored_hash

            return True
        except Exception as e:
            print(f"Error verifying integrity: {e}")
            return False


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Create logger
    logger = SecurityLogger(log_file="security_audit.log", enable_console=True)

    # Log various events
    logger.log_auth_success(
        user_id="user123",
        username="john_doe",
        ip_address="192.168.1.100",
        session_id="sess_abc123"
    )

    logger.log_auth_failure(
        username="attacker",
        ip_address="10.0.0.1",
        reason="invalid_password",
        attempt_count=3
    )

    logger.log_sql_injection_attempt(
        payload="' OR 1=1--",
        field="username",
        ip_address="10.0.0.1"
    )

    # Tamper-proof logging
    tamper_proof = TamperProofLogger()
    event = SecurityEvent(
        timestamp=datetime.utcnow().isoformat() + 'Z',
        event_type=SecurityEventType.AUTH_LOGIN_SUCCESS.value,
        severity=SecuritySeverity.LOW.value,
        user_id="user123",
        username="john_doe",
        ip_address="192.168.1.100",
        action="login",
        result="success",
        details={}
    )
    event_hash = tamper_proof.log_event(event)
    print(f"Event logged with hash: {event_hash}")

    # Verify integrity
    is_valid = tamper_proof.verify_integrity()
    print(f"Log integrity: {'VALID' if is_valid else 'COMPROMISED'}")
