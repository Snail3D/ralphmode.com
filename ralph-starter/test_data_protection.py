#!/usr/bin/env python3
"""
Test Suite for SEC-005: Sensitive Data Exposure Prevention

Tests:
- Secret management
- Data encryption at rest (AES-256-GCM)
- PII protection
- Secure logging
- HTTPS enforcement
"""

import os
import sys
import unittest
import base64
from datetime import timedelta

# Import the module
from data_protection import (
    SecretManager,
    DataEncryption,
    PIIProtection,
    SecureLogger,
    add_security_headers,
)


class TestSecretManager(unittest.TestCase):
    """Test SecretManager class"""

    def test_is_secret_key(self):
        """Test secret key detection"""
        self.assertTrue(SecretManager.is_secret_key("API_KEY"))
        self.assertTrue(SecretManager.is_secret_key("password"))
        self.assertTrue(SecretManager.is_secret_key("auth_token"))
        self.assertTrue(SecretManager.is_secret_key("SECRET_KEY"))
        self.assertFalse(SecretManager.is_secret_key("username"))
        self.assertFalse(SecretManager.is_secret_key("email"))

    def test_sanitize_string(self):
        """Test string sanitization"""
        text = "API_KEY=sk_live_abc123xyz456"
        sanitized = SecretManager.sanitize_for_logging(text)
        self.assertNotIn("sk_live_abc123xyz456", sanitized)
        self.assertIn("***REDACTED***", sanitized)

    def test_sanitize_dict(self):
        """Test dictionary sanitization"""
        data = {
            "username": "john",
            "password": "super_secret",
            "email": "john@example.com"
        }
        sanitized = SecretManager.sanitize_for_logging(data)
        self.assertEqual(sanitized["username"], "john")
        self.assertEqual(sanitized["password"], "***REDACTED***")
        self.assertEqual(sanitized["email"], "john@example.com")


class TestDataEncryption(unittest.TestCase):
    """Test DataEncryption class"""

    def setUp(self):
        """Create encryptor with known key"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        self.master_key = AESGCM.generate_key(bit_length=256)
        self.encryptor = DataEncryption(master_key=self.master_key)

    def test_encrypt_decrypt(self):
        """Test basic encryption/decryption"""
        plaintext = "Sensitive data: Credit card 4532-1234-5678-9010"
        encrypted = self.encryptor.encrypt(plaintext)

        # Encrypted should be different from plaintext
        self.assertNotEqual(encrypted, plaintext)

        # Decryption should recover original
        decrypted = self.encryptor.decrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_with_context(self):
        """Test encryption with context (different keys for different fields)"""
        plaintext = "user@example.com"

        # Same plaintext, different contexts = different ciphertexts
        encrypted1 = self.encryptor.encrypt(plaintext, context="email")
        encrypted2 = self.encryptor.encrypt(plaintext, context="username")

        self.assertNotEqual(encrypted1, encrypted2)

        # Decrypt with correct context
        self.assertEqual(self.encryptor.decrypt(encrypted1, context="email"), plaintext)
        self.assertEqual(self.encryptor.decrypt(encrypted2, context="username"), plaintext)

    def test_encrypt_decrypt_dict(self):
        """Test dictionary encryption"""
        data = {
            "username": "john_doe",
            "email": "john@example.com",
            "phone": "+1-234-567-8900",
            "public_info": "This is public"
        }

        # Encrypt sensitive fields
        encrypted = self.encryptor.encrypt_dict(data, ["email", "phone"])

        # Sensitive fields should be encrypted
        self.assertNotEqual(encrypted["email"], data["email"])
        self.assertNotEqual(encrypted["phone"], data["phone"])

        # Public fields unchanged
        self.assertEqual(encrypted["username"], data["username"])
        self.assertEqual(encrypted["public_info"], data["public_info"])

        # Decrypt
        decrypted = self.encryptor.decrypt_dict(encrypted, ["email", "phone"])
        self.assertEqual(decrypted, data)

    def test_encrypted_format(self):
        """Test that encrypted data is base64-encoded"""
        plaintext = "test data"
        encrypted = self.encryptor.encrypt(plaintext)

        # Should be valid base64
        try:
            base64.b64decode(encrypted)
            valid_b64 = True
        except Exception:
            valid_b64 = False

        self.assertTrue(valid_b64)


class TestPIIProtection(unittest.TestCase):
    """Test PIIProtection class"""

    def test_mask_email(self):
        """Test email masking"""
        self.assertEqual(
            PIIProtection.mask_email("john.doe@example.com"),
            "j***e@example.com"
        )
        self.assertEqual(
            PIIProtection.mask_email("a@test.com"),
            "a***@test.com"
        )

    def test_mask_phone(self):
        """Test phone masking"""
        masked = PIIProtection.mask_phone("+1-234-567-8900")
        self.assertIn("***", masked)
        self.assertIn("8900", masked)
        self.assertNotIn("234", masked)

    def test_mask_credit_card(self):
        """Test credit card masking"""
        masked = PIIProtection.mask_credit_card("4532-1234-5678-9010")
        self.assertIn("****", masked)
        self.assertIn("9010", masked)
        self.assertNotIn("4532", masked)

    def test_detect_and_mask_pii(self):
        """Test PII detection and masking"""
        text = "Email me at john.doe@example.com or call +1-234-567-8900"
        masked = PIIProtection.detect_and_mask_pii(text)

        # Should mask email
        self.assertNotIn("john.doe@example.com", masked)
        self.assertIn("@example.com", masked)

        # Should mask phone
        self.assertNotIn("234-567", masked)
        self.assertIn("***", masked)

    def test_retention_periods(self):
        """Test GDPR retention periods"""
        # User profile: 2 years
        profile_period = PIIProtection.get_pii_retention_period("user_profile")
        self.assertEqual(profile_period, timedelta(days=365 * 2))

        # Logs: 30 days
        log_period = PIIProtection.get_pii_retention_period("logs")
        self.assertEqual(log_period, timedelta(days=30))

        # Default: 1 year
        default_period = PIIProtection.get_pii_retention_period("unknown_type")
        self.assertEqual(default_period, timedelta(days=365))


class TestSecureLogger(unittest.TestCase):
    """Test SecureLogger class"""

    def test_logger_sanitizes_secrets(self):
        """Test that logger sanitizes secrets"""
        import logging
        from io import StringIO

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)

        logger = SecureLogger(__name__)
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.INFO)

        # Log a secret
        logger.info("User logged in with API_KEY=sk_live_abc123xyz")

        # Check log output doesn't contain secret
        log_output = log_stream.getvalue()
        self.assertNotIn("sk_live_abc123xyz", log_output)


class TestSecurityHeaders(unittest.TestCase):
    """Test security headers function"""

    def test_add_security_headers(self):
        """Test that security headers are added"""
        from flask import Flask, jsonify

        app = Flask(__name__)

        @app.route('/test')
        def test_route():
            return jsonify({'status': 'ok'})

        with app.test_client() as client:
            # Mock response
            response = client.get('/test')

            # Add security headers
            response = add_security_headers(response)

            # Check HSTS (SEC-005)
            self.assertIn('Strict-Transport-Security', response.headers)
            hsts = response.headers['Strict-Transport-Security']
            self.assertIn('max-age=31536000', hsts)
            self.assertIn('includeSubDomains', hsts)

            # Check other security headers
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(response.headers['X-Frame-Options'], 'DENY')


def run_tests():
    """Run all tests"""
    print("=" * 70)
    print("SEC-005: Sensitive Data Exposure Prevention - Test Suite")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSecretManager))
    suite.addTests(loader.loadTestsFromTestCase(TestDataEncryption))
    suite.addTests(loader.loadTestsFromTestCase(TestPIIProtection))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureLogger))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityHeaders))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        print("=" * 70)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
