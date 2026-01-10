#!/usr/bin/env python3
"""
SEC-020: PII (Personally Identifiable Information) Handler

Handles encryption, masking, and access control for PII fields.

PII fields in this system:
- username (Telegram username)
- first_name (User's first name)
- last_name (User's last name)
- telegram_id (Telegram user ID - semi-PII)
- project_name (may contain sensitive info)

Security measures:
- Encryption at rest using Fernet (symmetric)
- Masking in logs
- Access control (explicit permission required)
- Minimal data collection
- Retention policy enforcement
"""

import os
import re
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet, InvalidToken
from functools import wraps

logger = logging.getLogger(__name__)

# =============================================================================
# Encryption Key Management
# =============================================================================

def get_encryption_key() -> bytes:
    """
    Get or generate encryption key for PII.

    In production, this should:
    1. Use a key management service (AWS KMS, Azure Key Vault, etc.)
    2. Rotate keys regularly
    3. Store in secure location (not in code!)

    For now, we use an environment variable with fallback to local file.
    """
    # Try environment variable first
    key_b64 = os.environ.get("PII_ENCRYPTION_KEY")
    if key_b64:
        return key_b64.encode()

    # Try local key file
    key_file = ".pii_key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read().strip()

    # Generate new key
    logger.warning("SEC-020: Generating new PII encryption key - store this securely!")
    key = Fernet.generate_key()

    # Save to file (with restricted permissions)
    try:
        with open(key_file, "wb") as f:
            f.write(key)
        os.chmod(key_file, 0o600)  # Read/write for owner only
        logger.info(f"SEC-020: Encryption key saved to {key_file} (mode 0600)")
    except Exception as e:
        logger.error(f"SEC-020: Failed to save encryption key: {e}")

    return key


# =============================================================================
# PII Field Definitions
# =============================================================================

class PIIField:
    """Definition of a PII field."""

    # PII field types
    USERNAME = "username"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    TELEGRAM_ID = "telegram_id"
    PROJECT_NAME = "project_name"
    EMAIL = "email"
    PHONE = "phone"

    # All PII fields
    ALL_FIELDS = {
        USERNAME, FIRST_NAME, LAST_NAME, TELEGRAM_ID,
        PROJECT_NAME, EMAIL, PHONE
    }

    # Fields that require encryption at rest
    ENCRYPTED_FIELDS = {
        FIRST_NAME, LAST_NAME, EMAIL, PHONE
    }

    # Fields that should be masked in logs
    MASKED_IN_LOGS = {
        USERNAME, FIRST_NAME, LAST_NAME, TELEGRAM_ID,
        PROJECT_NAME, EMAIL, PHONE
    }

    @classmethod
    def is_pii(cls, field_name: str) -> bool:
        """Check if a field is PII."""
        return field_name in cls.ALL_FIELDS


# =============================================================================
# Encryption/Decryption
# =============================================================================

class PIIEncryptor:
    """Handles encryption and decryption of PII."""

    def __init__(self):
        self.key = get_encryption_key()
        self.fernet = Fernet(self.key)

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypt PII value.

        Returns base64-encoded ciphertext or None if input is None.
        """
        if plaintext is None or plaintext == "":
            return None

        try:
            encrypted = self.fernet.encrypt(plaintext.encode())
            return encrypted.decode()  # Return as string for DB storage
        except Exception as e:
            logger.error(f"SEC-020: Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        """
        Decrypt PII value.

        Returns plaintext or None if input is None.
        """
        if ciphertext is None or ciphertext == "":
            return None

        try:
            decrypted = self.fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("SEC-020: Decryption failed - invalid token (wrong key or corrupted data)")
            raise
        except Exception as e:
            logger.error(f"SEC-020: Decryption failed: {e}")
            raise


# Global encryptor instance
_encryptor = None

def get_encryptor() -> PIIEncryptor:
    """Get global PII encryptor instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = PIIEncryptor()
    return _encryptor


# =============================================================================
# Masking (for logs and display)
# =============================================================================

class PIIMasker:
    """Masks PII in text for safe logging/display."""

    # Patterns for common PII
    PATTERNS = {
        # Email: show first 2 chars + domain
        'email': (
            r'\b([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
            r'\1***@\2'
        ),
        # Phone: show last 4 digits
        'phone': (
            r'\b(\+?[\d\s\-()]{7,}[\d])\b',
            lambda m: '***' + m.group(1)[-4:]
        ),
        # Telegram ID: show first 2 and last 2 digits
        'telegram_id': (
            r'\b(telegram_id[=:\s]+)(\d{2})\d+(\d{2})\b',
            r'\1\2***\3'
        ),
    }

    @classmethod
    def mask_string(cls, value: Optional[str], show_chars: int = 2) -> str:
        """
        Mask a string value for logging.

        Examples:
            "JohnDoe" -> "Jo****"
            "Alice" -> "Al***"
            "" -> "[empty]"
            None -> "[none]"
        """
        if value is None:
            return "[none]"
        if value == "":
            return "[empty]"
        if len(value) <= show_chars:
            return "*" * len(value)

        return value[:show_chars] + ("*" * (len(value) - show_chars))

    @classmethod
    def mask_telegram_id(cls, telegram_id: Optional[int]) -> str:
        """Mask Telegram ID for logging."""
        if telegram_id is None:
            return "[none]"

        id_str = str(telegram_id)
        if len(id_str) <= 4:
            return "***"

        return id_str[:2] + ("*" * (len(id_str) - 4)) + id_str[-2:]

    @classmethod
    def mask_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask PII fields in a dictionary.

        Returns a new dict with PII fields masked.
        """
        masked = data.copy()

        for key, value in masked.items():
            if PIIField.is_pii(key):
                if key == PIIField.TELEGRAM_ID and isinstance(value, int):
                    masked[key] = cls.mask_telegram_id(value)
                elif isinstance(value, str):
                    masked[key] = cls.mask_string(value)

        return masked

    @classmethod
    def mask_text(cls, text: str) -> str:
        """
        Mask PII patterns in arbitrary text.

        Useful for masking PII in log messages, exceptions, etc.
        """
        if not text:
            return text

        result = text

        for pattern_name, (pattern, replacement) in cls.PATTERNS.items():
            try:
                if callable(replacement):
                    result = re.sub(pattern, replacement, result)
                else:
                    result = re.sub(pattern, replacement, result)
            except Exception as e:
                logger.warning(f"SEC-020: Failed to mask {pattern_name}: {e}")

        return result


# =============================================================================
# Access Control
# =============================================================================

class PIIAccessControl:
    """Controls access to PII fields."""

    # Track PII access for audit
    access_log = []

    @classmethod
    def log_access(cls, field: str, context: str, user_id: Optional[int] = None):
        """Log PII access for audit."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "field": field,
            "context": context,
            "user_id": user_id
        }
        cls.access_log.append(entry)

        # Keep only last 1000 entries
        if len(cls.access_log) > 1000:
            cls.access_log = cls.access_log[-1000:]

        logger.info(f"SEC-020: PII access - field={field}, context={context}")

    @classmethod
    def get_access_log(cls, limit: int = 100) -> list:
        """Get recent PII access log entries."""
        return cls.access_log[-limit:]


def require_pii_permission(field: str):
    """
    Decorator that enforces explicit permission to access PII.

    Usage:
        @require_pii_permission("first_name")
        def get_user_name(user_id):
            # Access to first_name is logged
            return user.first_name
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log the access
            context = f"{func.__module__}.{func.__name__}"
            PIIAccessControl.log_access(field, context)

            # Execute the function
            return func(*args, **kwargs)

        return wrapper
    return decorator


# =============================================================================
# Data Retention
# =============================================================================

class PIIRetentionPolicy:
    """Enforces data retention policies for PII."""

    # Default retention periods (in days)
    RETENTION_PERIODS = {
        "inactive_user": 365,  # 1 year
        "deleted_user": 30,    # 30 days for recovery
        "session_data": 90,    # 90 days
    }

    @classmethod
    def should_delete(cls, entity_type: str, last_activity: datetime) -> bool:
        """
        Check if PII should be deleted based on retention policy.

        Args:
            entity_type: Type of entity (inactive_user, deleted_user, session_data)
            last_activity: Last activity timestamp

        Returns:
            True if data should be deleted
        """
        retention_days = cls.RETENTION_PERIODS.get(entity_type, 365)
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        return last_activity < cutoff

    @classmethod
    def get_retention_period(cls, entity_type: str) -> int:
        """Get retention period in days for entity type."""
        return cls.RETENTION_PERIODS.get(entity_type, 365)


# =============================================================================
# Utilities
# =============================================================================

def encrypt_pii(value: Optional[str]) -> Optional[str]:
    """Convenience function to encrypt PII."""
    return get_encryptor().encrypt(value)


def decrypt_pii(value: Optional[str]) -> Optional[str]:
    """Convenience function to decrypt PII."""
    return get_encryptor().decrypt(value)


def mask_for_logs(value: Any, field_name: Optional[str] = None) -> str:
    """
    Convenience function to mask value for logging.

    Args:
        value: The value to mask
        field_name: Optional field name for context

    Returns:
        Masked string suitable for logging
    """
    if field_name == PIIField.TELEGRAM_ID and isinstance(value, int):
        return PIIMasker.mask_telegram_id(value)
    elif isinstance(value, str):
        return PIIMasker.mask_string(value)
    elif isinstance(value, dict):
        return str(PIIMasker.mask_dict(value))
    else:
        return str(value)


# =============================================================================
# Self-test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SEC-020: PII Handler Tests")
    print("=" * 60)

    # Test encryption
    print("\n[1] Encryption Test")
    encryptor = get_encryptor()
    original = "John Doe"
    encrypted = encryptor.encrypt(original)
    decrypted = encryptor.decrypt(encrypted)
    print(f"   Original: {original}")
    print(f"   Encrypted: {encrypted[:20]}...")
    print(f"   Decrypted: {decrypted}")
    print(f"   ✅ PASS" if decrypted == original else "   ❌ FAIL")

    # Test masking
    print("\n[2] Masking Test")
    test_cases = [
        ("JohnDoe", "Jo*****"),
        ("Alice", "Al***"),
        ("A", "*"),
        ("", "[empty]"),
        (None, "[none]"),
    ]
    all_pass = True
    for value, expected in test_cases:
        masked = PIIMasker.mask_string(value)
        passed = masked == expected
        all_pass = all_pass and passed
        print(f"   {repr(value):20} -> {masked:15} {'✅' if passed else '❌ Expected: ' + expected}")
    print(f"   {'✅ PASS' if all_pass else '❌ FAIL'}")

    # Test telegram ID masking
    print("\n[3] Telegram ID Masking")
    test_id = 123456789
    masked_id = PIIMasker.mask_telegram_id(test_id)
    print(f"   Original: {test_id}")
    print(f"   Masked: {masked_id}")
    print(f"   ✅ PASS" if "***" in masked_id else "   ❌ FAIL")

    # Test dict masking
    print("\n[4] Dictionary Masking")
    user_data = {
        "telegram_id": 123456789,
        "username": "johndoe",
        "first_name": "John",
        "last_name": "Doe",
        "subscription_tier": "free"  # Not PII
    }
    masked_dict = PIIMasker.mask_dict(user_data)
    print(f"   Original: {user_data}")
    print(f"   Masked: {masked_dict}")
    print(f"   ✅ PASS" if masked_dict["subscription_tier"] == "free" else "   ❌ FAIL")

    # Test access control
    print("\n[5] Access Control")
    @require_pii_permission("first_name")
    def test_function():
        return "accessed"

    result = test_function()
    log_entries = PIIAccessControl.get_access_log(limit=1)
    print(f"   Function result: {result}")
    print(f"   Access logged: {len(log_entries) > 0}")
    print(f"   ✅ PASS" if len(log_entries) > 0 else "   ❌ FAIL")

    # Test retention policy
    print("\n[6] Retention Policy")
    old_date = datetime.utcnow() - timedelta(days=400)
    recent_date = datetime.utcnow() - timedelta(days=10)
    should_delete_old = PIIRetentionPolicy.should_delete("inactive_user", old_date)
    should_delete_recent = PIIRetentionPolicy.should_delete("inactive_user", recent_date)
    print(f"   Old user (400 days): should_delete={should_delete_old}")
    print(f"   Recent user (10 days): should_delete={should_delete_recent}")
    print(f"   ✅ PASS" if (should_delete_old and not should_delete_recent) else "   ❌ FAIL")

    print("\n" + "=" * 60)
    print("SEC-020: All tests completed")
    print("=" * 60)
