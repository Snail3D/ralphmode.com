# SEC-020: PII (Personally Identifiable Information) Handling Policy

## Overview

This document identifies all PII fields in the Ralph Mode system and describes how they are protected according to SEC-020 requirements.

## What is PII?

Personally Identifiable Information (PII) is any data that could potentially identify a specific individual. This includes names, IDs, contact information, and potentially sensitive project names.

## PII Fields in Ralph Mode

### User Table (database.py)

| Field | Type | Sensitivity | Protection |
|-------|------|-------------|------------|
| `telegram_id` | Integer | Semi-PII | Masked in logs |
| `username` | String | PII | Masked in logs |
| `first_name` | String | PII | **Encrypted at rest**, masked in logs |
| `last_name` | String | PII | **Encrypted at rest**, masked in logs |

### BotSession Table (database.py)

| Field | Type | Sensitivity | Protection |
|-------|------|-------------|------------|
| `project_name` | String | Potential PII | Masked in logs |

### Potential Future PII

| Field | Type | Sensitivity | Protection |
|-------|------|-------------|------------|
| `email` | String | PII | **Encrypted at rest**, masked in logs |
| `phone` | String | PII | **Encrypted at rest**, masked in logs |

## Security Measures

### 1. Encryption at Rest

**Status**: ✅ Implemented

PII fields marked for encryption are encrypted using Fernet (symmetric encryption) before storage in the database.

**Implementation**: `pii_handler.py::PIIEncryptor`

**Encrypted fields**:
- `first_name`
- `last_name`
- `email` (when added)
- `phone` (when added)

**Key Management**:
- Encryption key stored in `.pii_key` file (mode 0600, owner-only access)
- Can be overridden via `PII_ENCRYPTION_KEY` environment variable
- **Production requirement**: Use key management service (AWS KMS, Azure Key Vault)

**Usage**:
```python
from pii_handler import encrypt_pii, decrypt_pii

# Storing
user.first_name = encrypt_pii("John")

# Retrieving
decrypted_name = decrypt_pii(user.first_name)
# Or use helper methods:
user.set_encrypted_first_name("John")
name = user.get_decrypted_first_name()
```

### 2. Masking in Logs

**Status**: ✅ Implemented

All PII is masked when logged to prevent exposure in log files, error messages, or monitoring systems.

**Implementation**: `pii_handler.py::PIIMasker`

**Masking rules**:
- Strings: Show first 2 chars + asterisks (e.g., "JohnDoe" → "Jo*****")
- Telegram ID: Show first 2 and last 2 digits (e.g., "123456789" → "12*****89")
- Emails: Show first 2 chars + domain (e.g., "john@example.com" → "jo***@example.com")
- Phones: Show last 4 digits (e.g., "555-1234" → "***1234")

**Usage**:
```python
from pii_handler import mask_for_logs, PIIField

# Mask a single value
masked = mask_for_logs(username, PIIField.USERNAME)
logger.info(f"User {masked} logged in")

# Mask a dictionary
from pii_handler import PIIMasker
user_data = {"username": "johndoe", "first_name": "John"}
masked_dict = PIIMasker.mask_dict(user_data)
logger.debug(f"User data: {masked_dict}")

# Mask arbitrary text
text = "User john@example.com called from 555-1234"
safe_text = PIIMasker.mask_text(text)
logger.info(safe_text)
```

**Integration points**:
- `security_logging.py::SecurityEvent.to_dict()` - Automatically masks PII in security logs
- `database.py::User.__repr__()` - Masks username in object repr
- `ralph_bot.py` - Masks telegram_id in error logs

### 3. Access Control

**Status**: ✅ Implemented

All access to PII fields is logged for audit purposes. Explicit permission required for sensitive operations.

**Implementation**: `pii_handler.py::PIIAccessControl`

**Usage**:
```python
from pii_handler import require_pii_permission

@require_pii_permission("first_name")
def get_user_full_name(user_id):
    # Access is automatically logged
    user = db.query(User).filter(User.id == user_id).first()
    return f"{user.first_name} {user.last_name}"
```

**Audit log**:
```python
from pii_handler import PIIAccessControl

# Get recent PII access
log_entries = PIIAccessControl.get_access_log(limit=100)
# Returns: [{"timestamp": "...", "field": "first_name", "context": "module.function", "user_id": ...}]
```

### 4. Minimal Data Collection

**Status**: ✅ Implemented

We only collect PII that is **essential** for the service to function:

| Field | Justification | Required? |
|-------|---------------|-----------|
| `telegram_id` | Required to identify users in Telegram | ✅ Yes |
| `username` | Optional, used for display and mentions | ❌ No (optional) |
| `first_name` | Optional, from Telegram profile | ❌ No (optional) |
| `last_name` | Optional, from Telegram profile | ❌ No (optional) |
| `project_name` | Optional, user-provided | ❌ No (optional) |

**We do NOT collect**:
- Email addresses (unless user explicitly provides)
- Phone numbers
- Physical addresses
- Payment card data (handled by Stripe, never stored)
- IP addresses (hashed for rate limiting only)

### 5. Data Retention Policy

**Status**: ✅ Implemented

PII is automatically deleted after retention periods expire.

**Implementation**: `pii_handler.py::PIIRetentionPolicy`

**Retention periods**:
- Inactive users: 365 days (1 year)
- Deleted users: 30 days (recovery window)
- Session data: 90 days

**Usage**:
```python
from pii_handler import PIIRetentionPolicy
from datetime import datetime

# Check if should delete
should_delete = PIIRetentionPolicy.should_delete(
    entity_type="inactive_user",
    last_activity=user.updated_at
)

if should_delete:
    db.delete(user)
```

### 6. Transmission Security

**Status**: ✅ Implemented

All PII is transmitted only over encrypted channels:

- **Telegram API**: HTTPS only (enforced by python-telegram-bot)
- **Groq API**: HTTPS only
- **Database connections**: TLS when using remote databases (PostgreSQL, MySQL)

**Environment variables** for production:
```bash
# Use TLS for database
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### 7. Access Logging

**Status**: ✅ Implemented

All PII access is logged via `PIIAccessControl.log_access()`.

**Logged events**:
- Which PII field was accessed
- When (timestamp)
- Where (function/module context)
- By whom (user_id if available)

**Audit trail location**: In-memory (last 1000 entries)

**Future enhancement**: Persist to append-only audit log file.

## Testing PII Protection

Run the PII handler self-test:

```bash
python3 pii_handler.py
```

**Expected output**:
```
============================================================
SEC-020: PII Handler Tests
============================================================

[1] Encryption Test
   Original: John Doe
   Encrypted: gAAAAABl...
   Decrypted: John Doe
   ✅ PASS

[2] Masking Test
   'JohnDoe'            -> Jo*****        ✅
   'Alice'              -> Al***          ✅
   'A'                  -> *              ✅
   ''                   -> [empty]        ✅
   None                 -> [none]         ✅
   ✅ PASS

[3] Telegram ID Masking
   Original: 123456789
   Masked: 12*****89
   ✅ PASS

[4] Dictionary Masking
   Original: {'telegram_id': 123456789, 'username': 'johndoe', ...}
   Masked: {'telegram_id': '12*****89', 'username': 'jo*****', ...}
   ✅ PASS

[5] Access Control
   Function result: accessed
   Access logged: True
   ✅ PASS

[6] Retention Policy
   Old user (400 days): should_delete=True
   Recent user (10 days): should_delete=False
   ✅ PASS

============================================================
SEC-020: All tests completed
============================================================
```

## Compliance Checklist

### SEC-020 Acceptance Criteria

- [x] **PII fields identified and documented** - This file
- [x] **Minimal PII collected (only what's needed)** - See "Minimal Data Collection" section
- [x] **PII encrypted at rest** - `first_name`, `last_name` via `pii_handler.py`
- [x] **PII masked in logs** - All logs via `PIIMasker`
- [x] **PII access requires explicit permission** - `@require_pii_permission` decorator
- [x] **PII retention policy enforced** - `PIIRetentionPolicy` (365 days for inactive users)
- [x] **PII transmitted only over encrypted channels** - HTTPS enforced

## Production Deployment Checklist

Before deploying to production:

- [ ] **Generate and secure encryption key**
  ```bash
  # Generate key
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

  # Set in environment
  export PII_ENCRYPTION_KEY="<generated_key>"
  ```

- [ ] **Use key management service** (AWS KMS, Azure Key Vault, etc.)
- [ ] **Enable database TLS** (set `?sslmode=require` in DATABASE_URL)
- [ ] **Set up log rotation** for security_audit.log
- [ ] **Configure PII access monitoring** (alerts on unusual access patterns)
- [ ] **Schedule automated cleanup** for expired PII (cron job)
- [ ] **Review and adjust retention periods** per legal requirements

## GDPR Compliance

This PII handling policy supports GDPR compliance:

- **Right to be informed**: This document + user-facing privacy policy
- **Right of access**: `/mystatus` command (SEC-019)
- **Right to rectification**: User can update profile in Telegram
- **Right to erasure**: `/deletemydata` command (SEC-019)
- **Right to restrict processing**: Subscription tier controls
- **Right to data portability**: `/exportmydata` command (SEC-019)
- **Right to object**: Opt-out via subscription settings

## Support

For questions about PII handling:

1. Read this document
2. Review `pii_handler.py` source code
3. Run self-tests: `python3 pii_handler.py`
4. Check security logs: `tail -f security_audit.log`

---

**Last updated**: 2026-01-10
**Maintained by**: Ralph Mode Security Team
**Related**: SEC-020, SEC-019 (GDPR), SEC-010 (Logging)
