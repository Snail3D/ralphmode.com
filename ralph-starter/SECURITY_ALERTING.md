# Security Alerting System - SEC-025

## Overview

Ralph Mode Bot implements comprehensive real-time security monitoring and alerting. The system detects suspicious patterns, tracks security events, and sends multi-channel alerts to ensure 24/7 security coverage.

## Architecture

### Components

1. **SecurityAlertManager** (`security_alerts.py`)
   - Multi-channel alert delivery
   - Alert routing based on severity
   - Alert throttling to prevent spam
   - Integrations: Telegram, Email, Slack, PagerDuty

2. **SecurityMonitor** (`monitoring.py`)
   - Real-time threat detection
   - Pattern analysis
   - Threshold-based alerting
   - Event tracking and correlation

3. **SecurityMonitoringMiddleware** (`monitoring.py`)
   - Application integration layer
   - Automatic event tracking
   - Access control enforcement

## Monitored Threats

### 1. Failed Login Attempts

**Threshold**: 5+ failed logins from same IP within 5 minutes

**Detection Logic**:
```python
# Tracks by IP address
if failed_attempts >= 5:
    severity = ERROR
    alert("Multiple Failed Logins Detected")

if failed_attempts >= 10:
    severity = CRITICAL
    alert("Brute Force Attack Detected")
```

**Alert Severity**:
- 5-9 attempts: ERROR
- 10+ attempts: CRITICAL (Brute Force)

**Integration**:
```python
from monitoring import track_failed_login

await track_failed_login(
    user_id=None,
    ip_address="10.0.0.1",
    username="admin",
    reason="invalid_password"
)
```

### 2. SQL Injection Attempts

**Threshold**: ANY attempt triggers alert (zero tolerance)

**Detection Logic**:
```python
# Immediate alert on detection
if sqli_detected:
    severity = ERROR

# Escalate to CRITICAL after 3+ attempts
if sqli_attempts >= 3:
    severity = CRITICAL
    metadata["coordinated_attack"] = True
```

**Alert Severity**:
- 1-2 attempts: ERROR
- 3+ attempts: CRITICAL (Coordinated Attack)

**Integration**:
```python
from monitoring import track_sql_injection

await track_sql_injection(
    user_id="attacker",
    ip_address="10.0.0.1",
    payload="' OR 1=1--",
    field="username"
)
```

### 3. Privilege Escalation

**Threshold**: ANY attempt triggers alert

**Detection Logic**:
```python
# Always alert when user attempts unauthorized action
if user_role != required_role:
    severity = ERROR

# Escalate to CRITICAL on repeated attempts
if attempts > 1:
    severity = CRITICAL
```

**Alert Severity**:
- First attempt: ERROR
- Repeated attempts: CRITICAL

**Integration**:
```python
from monitoring import track_privilege_escalation

await track_privilege_escalation(
    user_id="user123",
    ip_address="10.0.0.1",
    attempted_action="delete_users",
    current_role="user",
    required_role="admin"
)
```

### 4. Unusual API Patterns

**Threshold**: 100+ requests per minute from single IP

**Detection Logic**:
```python
# Track API calls by IP + User ID
if api_calls_per_minute >= 100:
    severity = WARNING
    alert("Unusual API Activity Detected")
```

**Alert Severity**:
- WARNING (rate limiting should handle, but we monitor)

**Integration**:
```python
from monitoring import track_api_request

await track_api_request(
    user_id="user123",
    ip_address="10.0.0.1",
    endpoint="/api/data",
    method="GET",
    status_code=200
)
```

### 5. Admin Account Creation

**Threshold**: ALWAYS alert (zero tolerance)

**Detection Logic**:
```python
# Always CRITICAL - admin creation is high-risk event
on_admin_creation:
    severity = CRITICAL
    alert("New Admin Account Created")
```

**Alert Severity**:
- Always: CRITICAL

**Integration**:
```python
from monitoring import track_admin_creation

await track_admin_creation(
    creator_user_id="admin1",
    new_admin_user_id="admin2",
    new_admin_username="newadmin",
    creator_ip="10.0.0.1"
)
```

## Alert Channels

### Primary: Telegram

Best for Ralph Mode Bot (we're a Telegram bot!):

```python
# Alerts sent to admin Telegram IDs
ADMIN_TELEGRAM_IDS=123456789,987654321
```

**Format**:
```
🔴 SECURITY ALERT

SQL Injection Attempt Detected
Severity: CRITICAL
Event: input.sqli_attempt
Time: 2026-01-10T12:34:56Z

SQL injection payload detected from 10.0.0.1 in field 'username'

User: attacker
IP: 10.0.0.1

Details:
• payload: ' OR 1=1--
• field: username
• attempt_count: 3
• coordinated_attack: true
```

### Secondary: Email

For audit trails and permanent records:

```python
SECURITY_ALERT_EMAIL=security@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your_password
```

**Format**: HTML email with severity color-coding

### Tertiary: Slack

For team collaboration:

```python
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Format**: Slack attachment with color-coded severity

### Critical Escalation: PagerDuty

For CRITICAL alerts requiring immediate response:

```python
PAGERDUTY_INTEGRATION_KEY=your_integration_key
```

**Severity Routing**:
- INFO → Telegram only
- WARNING → Telegram + Email
- ERROR → Telegram + Email + Slack
- CRITICAL → All channels including PagerDuty

## Alert Fatigue Prevention

### 1. Throttling

Prevents spam from repeated alerts:

```python
# Default: Max 5 alerts per 5 minutes per IP/event type
throttle_window = 300  # 5 minutes
max_alerts_per_window = 5
```

**Logic**:
```python
alert_key = f"{event_type}:{ip_address}"
if alerts_in_window(alert_key) >= 5:
    suppress_alert()
else:
    send_alert()
```

### 2. Tuned Thresholds

Carefully calibrated to minimize false positives:

| Threat | Threshold | Rationale |
|--------|-----------|-----------|
| Failed Logins | 5 | Normal users rarely fail 5x |
| Brute Force | 10 | Clear attack pattern |
| SQL Injection | 1 | Zero tolerance |
| API Rate | 100/min | Well above normal usage |
| Privilege Escalation | 1 | Immediate concern |
| Admin Creation | 1 | Always audit |

### 3. Cooldown Periods

Built into SecurityMonitor:

```python
alert_cooldown = 600  # 10 minutes

# Won't re-alert for same IP/threat within 10 minutes
if last_alert_time < now - cooldown:
    send_alert()
```

### 4. Event Aggregation

Batch analysis reduces noise:

```python
# Analyze patterns across events
analysis = await monitor.analyze_security_events(events)

# Recommendations based on patterns, not individual events
if analysis["by_type"]["failed_login"] > 10:
    recommend("Implement CAPTCHA or temporary IP blocks")
```

## 24/7 On-Call Rotation

### Configuration

```python
# Environment variables
ON_CALL_ROTATION_ENABLED=true
ON_CALL_PRIMARY=security-team
ESCALATION_TIMEOUT_MINUTES=15
```

### PagerDuty Integration

For production 24/7 coverage:

1. **Create PagerDuty Service**
   - Go to PagerDuty → Services → New Service
   - Integration: Events API v2
   - Copy integration key

2. **Configure Integration**
   ```bash
   export PAGERDUTY_INTEGRATION_KEY=your_key
   ```

3. **Set Up Schedule**
   - Create on-call schedule in PagerDuty
   - Define escalation policies
   - Configure notification rules

4. **Alert Routing**
   - CRITICAL alerts → Immediate page
   - ERROR alerts → Email to on-call
   - WARNING alerts → Logged only

### Escalation Flow

```
CRITICAL Alert Detected
       ↓
Sent to PagerDuty
       ↓
Page On-Call Engineer (Primary)
       ↓
No Response in 15 min?
       ↓
Escalate to Secondary
       ↓
No Response in 15 min?
       ↓
Escalate to Manager
```

## Usage Examples

### Basic Integration

```python
from monitoring import (
    track_failed_login,
    track_sql_injection,
    track_privilege_escalation,
    track_api_request,
    track_admin_creation
)

# In your authentication handler
async def handle_login(username, password, ip_address):
    user = authenticate(username, password)

    if not user:
        # Track failed login
        await track_failed_login(
            user_id=None,
            ip_address=ip_address,
            username=username
        )
        raise AuthenticationError()

    return user
```

### Middleware Integration

```python
from monitoring import SecurityMonitoringMiddleware

middleware = SecurityMonitoringMiddleware()

# Automatic privilege checking
async def delete_users(current_user, ip_address):
    has_privilege = await middleware.check_privilege_escalation(
        user_id=current_user.id,
        user_role=current_user.role,
        required_role="admin",
        action="delete_users",
        ip_address=ip_address,
        resource="users"
    )

    if not has_privilege:
        raise PermissionDenied()

    # Perform action...
```

### Input Validation

```python
from monitoring import track_sql_injection
from monitoring import PatternDetector

async def search(query, user_id, ip_address):
    # Check for SQL injection
    if PatternDetector.contains_sqli(query):
        await track_sql_injection(
            user_id=user_id,
            ip_address=ip_address,
            payload=query,
            field="search_query"
        )
        raise ValidationError("Invalid input")

    # Safe to proceed...
    return perform_search(query)
```

## Testing

Run comprehensive test suite:

```bash
# Run all monitoring tests
pytest test_monitoring.py -v

# Run specific test
pytest test_monitoring.py::test_failed_login_threshold -v

# Run with coverage
pytest test_monitoring.py --cov=monitoring --cov-report=html
```

## Monitoring Dashboard

For production monitoring, integrate with your observability platform:

### Metrics to Track

1. **Alert Volume**
   - Alerts per hour/day
   - By severity
   - By threat type

2. **Response Times**
   - Time to acknowledge
   - Time to resolve
   - Escalation rate

3. **False Positive Rate**
   - Dismissed alerts
   - Alert accuracy
   - Threshold effectiveness

4. **Threat Patterns**
   - Top attacking IPs
   - Most targeted resources
   - Attack trends over time

### Example: Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

# Alert metrics
alerts_total = Counter(
    'security_alerts_total',
    'Total security alerts sent',
    ['severity', 'threat_type']
)

alert_response_time = Histogram(
    'alert_response_seconds',
    'Time to respond to alerts',
    ['severity']
)
```

## Troubleshooting

### No Alerts Being Sent

**Check**:
1. Alert manager configuration
2. Channel credentials (Telegram token, SMTP password, etc.)
3. Admin IDs/emails configured
4. Network connectivity

**Debug**:
```python
# Test alert system
from security_alerts import SecurityAlertManager
import asyncio

async def test():
    manager = SecurityAlertManager()
    # Check configuration
    print(f"Telegram bot: {manager.telegram_bot is not None}")
    print(f"Admin IDs: {manager.admin_telegram_ids}")
    print(f"Alert email: {manager.alert_email}")

asyncio.run(test())
```

### Too Many Alerts (False Positives)

**Solutions**:
1. Increase thresholds
2. Extend time windows
3. Add IP whitelisting
4. Implement machine learning for pattern detection

**Adjust thresholds**:
```python
monitor = SecurityMonitor()
monitor.FAILED_LOGIN_THRESHOLD = 10  # Increase from 5
monitor.API_RATE_THRESHOLD = 200  # Increase from 100
```

### Alerts Not Reaching PagerDuty

**Check**:
1. Integration key is correct
2. PagerDuty service is active
3. Network can reach events.pagerduty.com
4. Alert severity is CRITICAL

## Best Practices

### 1. Regular Threshold Review

Quarterly review of:
- Alert volume
- False positive rate
- Missed attacks
- Response times

Adjust thresholds accordingly.

### 2. Alert Correlation

Don't alert on individual events in isolation:

```python
# Good: Correlate related events
if failed_logins > 5 AND sql_injection_attempts > 0:
    escalate_to_critical()

# Bad: Alert on every failed login
if failed_login:
    send_alert()
```

### 3. Actionable Alerts

Every alert should have:
- Clear description of the threat
- Recommended response actions
- Context (user, IP, timestamp, etc.)
- Severity appropriate to the threat

### 4. Alert Hygiene

- **Acknowledge** all alerts
- **Investigate** before dismissing
- **Document** false positives
- **Update** detection logic based on learnings

### 5. Security Team Training

Ensure on-call engineers know:
- How to access alert details
- Investigation procedures
- Escalation protocols
- Incident response playbooks

## Compliance

This alerting system helps meet:

- **SOC 2**: Real-time security monitoring
- **PCI-DSS**: Alert on security events
- **GDPR**: Data breach detection
- **ISO 27001**: Security incident management

## Future Enhancements

### Planned

1. **Machine Learning**
   - Anomaly detection
   - Behavioral analysis
   - Automated threat classification

2. **Advanced Correlation**
   - Cross-event pattern detection
   - Attack chain analysis
   - Threat intelligence integration

3. **Automated Response**
   - Auto-block malicious IPs
   - Rate limit escalation
   - Session termination

4. **Enhanced Reporting**
   - Daily/weekly security digests
   - Trend analysis
   - Executive dashboards

---

**Last Updated**: 2026-01-10
**Owner**: Security Team
**Review Cycle**: Quarterly
