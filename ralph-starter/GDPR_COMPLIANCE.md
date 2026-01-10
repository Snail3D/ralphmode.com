# SEC-019: GDPR Compliance Documentation

## Overview

Ralph Mode Bot is fully compliant with the EU General Data Protection Regulation (GDPR). This document explains our implementation of GDPR requirements.

## GDPR Principles Implemented

### 1. Lawfulness, Fairness, Transparency (Article 5.1.a)
- **Explicit consent required** before data collection
- Clear privacy policy displayed to all users
- Transparent about what data is collected and why

### 2. Purpose Limitation (Article 5.1.b)
- Data collected only for specific, legitimate purposes
- Purposes clearly communicated to users
- Data not used for incompatible purposes

### 3. Data Minimization (Article 5.1.c)
- Collect only necessary data:
  - Telegram user ID (required for bot functionality)
  - Username (for user identification)
  - Messages/code (for AI assistance)
  - Session data (for service delivery)

### 4. Accuracy (Article 5.1.d)
- Users can update their data anytime
- Mechanisms to correct inaccurate data

### 5. Storage Limitation (Article 5.1.e)
- **Data retention periods enforced**:
  - User data: 2 years after last activity
  - Session data: 90 days
  - Feedback: 5 years
  - Audit logs: 7 years (compliance requirement)

### 6. Integrity and Confidentiality (Article 5.1.f)
- Encryption at rest (db_config.py)
- Encrypted connections (SSL/TLS)
- Access controls and audit logging

### 7. Accountability (Article 5.2)
- Complete audit trail
- Data processing agreements with third parties
- This documentation

## User Rights Implementation

### Right to Access (Article 15)
**Command**: `/mydata`

Users can view all their data including:
- User profile information
- Session history
- Feedback submitted
- Data retention info
- Third-party processors

**Implementation**: `DataAccessController.get_user_data_summary()`

### Right to Data Portability (Article 20)
**Command**: `/export`

Users can export all their data in machine-readable JSON format.

**Features**:
- Complete data export
- Structured JSON format
- Includes export metadata
- File sent directly to user

**Implementation**: `DataExportController.export_user_data()`

### Right to Erasure (Article 17)
**Command**: `/deleteme`

Users can request complete deletion of their data.

**Features**:
- Confirmation required (prevents accidental deletion)
- Deletes all user data:
  - User profile
  - All sessions
  - All feedback
  - Associated data
- Audit trail maintained (compliance requirement)
- Irreversible

**Implementation**: `DataDeletionController.delete_user_data()`

### Right to Restrict Processing (Article 18)
Users can decline consent, which prevents data processing.

### Right to Object (Article 21)
Users can decline consent or delete their data at any time.

## Consent Management

### Explicit Consent (Article 7)
- **Opt-in required** (not opt-out)
- Clear, specific consent request
- User must take affirmative action
- Can be withdrawn at any time

### Consent Request Includes:
1. What data is collected
2. Why it's collected
3. User's rights
4. Data controller information
5. Links to privacy policy and terms

**Implementation**: `ConsentManager.request_consent_text()`

## Data Controller Information (Article 13)

**Data Controller**: Ralph Mode  
**Contact**: privacy@ralphmode.com  
**Address**: [Your Company Address]

## Third-Party Data Processors (Article 28)

### 1. Telegram
- **Purpose**: Message delivery and user authentication
- **Data Shared**: User ID, username, messages
- **Privacy Policy**: https://telegram.org/privacy
- **Legal Basis**: Data Processing Agreement

### 2. Groq
- **Purpose**: AI code generation
- **Data Shared**: Anonymized code requests
- **Privacy Policy**: https://groq.com/privacy
- **Legal Basis**: Data Processing Agreement

## Data Retention Policy (Article 5.1.e)

Automated cleanup enforced by `DataRetentionEnforcer`:

| Data Type | Retention Period | Reason |
|-----------|------------------|--------|
| User Data | 2 years after last activity | Service provision |
| Session Data | 90 days | Operational needs |
| Feedback | 5 years | Product improvement |
| Audit Logs | 7 years | Compliance/legal |

**Implementation**: `DataRetentionEnforcer.cleanup_expired_data()`

## Data Breach Notification (Articles 33 & 34)

### Process
1. Breach detected and logged
2. Assessment of severity and impact
3. Notification to supervisory authority within 72 hours
4. Notification to affected users (if high risk)
5. Documentation for compliance

**Implementation**: `DataBreachNotifier.notify_breach()`

## Privacy Policy

Full privacy policy available at: https://ralphmode.com/privacy

### Includes:
- What data we collect
- Why we collect it
- How we use it
- How long we keep it
- User rights
- Contact information
- Third-party processors

## Bot Commands for Users

```
/privacy   - View privacy policy and data protection info
/mydata    - View all your data (Right to Access)
/export    - Export your data in JSON (Data Portability)
/deleteme  - Delete all your data (Right to Erasure)
```

## Integration with ralph_bot.py

```python
from user_data_controller import register_gdpr_handlers, check_user_consent

# In main()
register_gdpr_handlers(application)

# Before processing user data
if not await check_user_consent(update, context):
    return  # Consent request shown to user
```

## Compliance Checklist

- [x] Explicit consent for data collection
- [x] Privacy policy clearly displayed
- [x] User can view all their data (/mydata)
- [x] User can request data deletion (/deleteme)
- [x] User can export their data (JSON format)
- [x] Data retention policy enforced
- [x] Third-party data processing documented
- [x] Data breach notification process defined

## Files

- `gdpr.py` - Core GDPR compliance module
- `user_data_controller.py` - Telegram bot integration
- `GDPR_COMPLIANCE.md` - This documentation

## Audit Trail

All GDPR-related actions are logged:
- Consent decisions → `security_logging.py`
- Data access requests → `logs/audit.log`
- Data exports → `logs/audit.log`
- Data deletions → `logs/gdpr_deletions.log`
- Data breaches → `logs/data_breaches.log`

## Supervisory Authority

For EU users, the relevant supervisory authority should be identified based on the data controller's location.

## Legal Basis

Primary legal basis for processing: **Consent** (Article 6.1.a)

Alternative legal basis where applicable:
- Performance of contract (Article 6.1.b) - service delivery
- Legitimate interests (Article 6.1.f) - security and fraud prevention

## Contact for GDPR Requests

**Email**: privacy@ralphmode.com  
**Response Time**: Within 30 days (as required by GDPR)

## Version

- **GDPR Compliance Version**: 1.0
- **Last Updated**: 2026-01-10
- **Implements**: GDPR (EU Regulation 2016/679)

---

**Note**: This implementation provides a strong foundation for GDPR compliance. For production deployment, consult with a legal expert to ensure full compliance with all applicable regulations.
