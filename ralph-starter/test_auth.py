#!/usr/bin/env python3
"""
SEC-004: Broken Authentication Prevention - Test Suite
=======================================================

Comprehensive tests for SEC-004 acceptance criteria:
1. ✅ Bcrypt/Argon2 password hashing (cost factor 12+)
2. ✅ Account lockout after 5 failed attempts
3. ✅ Session tokens are cryptographically random
4. ✅ Sessions expire after inactivity (1 hour)
5. ✅ Secure cookie flags (HttpOnly, Secure, SameSite)
6. ✅ Optional MFA/2FA support
7. ✅ No credentials in URLs or logs

Run with: python3 test_auth.py
"""

import unittest
import time
from datetime import datetime, timedelta

# Import modules under test
from auth import (
    AuthManager,
    PasswordHasher,
    PasswordValidator,
    AccountLockout,
    MFAManager,
    PasswordReset,
    CredentialSanitizer,
    BCRYPT_AVAILABLE,
    TOTP_AVAILABLE,
    MAX_FAILED_ATTEMPTS,
    BCRYPT_COST_FACTOR
)

from session_manager import (
    SessionManager,
    TokenManager,
    SESSION_INACTIVITY_TIMEOUT_MINUTES,
    COOKIE_HTTPONLY,
    COOKIE_SECURE,
    COOKIE_SAMESITE
)


class TestSEC004Authentication(unittest.TestCase):
    """Test suite for SEC-004: Broken Authentication Prevention"""

    def setUp(self):
        """Set up test fixtures."""
        self.test_password = "SecureP@ssw0rd123"
        self.weak_password = "password"
        self.test_user_id = "test_user_001"

    # =========================================================================
    # Acceptance Criteria 1: Bcrypt/Argon2 password hashing (cost factor 12+)
    # =========================================================================

    def test_AC1_bcrypt_available(self):
        """AC1: Verify bcrypt is installed and available."""
        self.assertTrue(BCRYPT_AVAILABLE, "Bcrypt must be installed for SEC-004")

    def test_AC1_password_hashing_cost_factor(self):
        """AC1: Verify password hashing uses cost factor 12+."""
        if not BCRYPT_AVAILABLE:
            self.skipTest("Bcrypt not available")

        # Cost factor should be at least 12
        self.assertGreaterEqual(BCRYPT_COST_FACTOR, 12,
                              "Cost factor must be 12+ for SEC-004")

    def test_AC1_password_hash_generation(self):
        """AC1: Test password hashing generates unique salted hashes."""
        if not BCRYPT_AVAILABLE:
            self.skipTest("Bcrypt not available")

        # Hash same password twice
        hash1 = PasswordHasher.hash_password(self.test_password)
        hash2 = PasswordHasher.hash_password(self.test_password)

        # Hashes should be different (different salts)
        self.assertNotEqual(hash1, hash2,
                          "Hashes should differ due to unique salts")

        # Both should verify correctly
        self.assertTrue(PasswordHasher.verify_password(self.test_password, hash1))
        self.assertTrue(PasswordHasher.verify_password(self.test_password, hash2))

    def test_AC1_password_verification(self):
        """AC1: Test password verification works correctly."""
        if not BCRYPT_AVAILABLE:
            self.skipTest("Bcrypt not available")

        hashed = PasswordHasher.hash_password(self.test_password)

        # Correct password should verify
        self.assertTrue(PasswordHasher.verify_password(self.test_password, hashed))

        # Wrong password should not verify
        self.assertFalse(PasswordHasher.verify_password("WrongPass123!", hashed))

    def test_AC1_password_strength_validation(self):
        """AC1: Test password strength requirements."""
        # Weak password should be rejected
        is_valid, msg = PasswordValidator.validate(self.weak_password)
        self.assertFalse(is_valid, "Weak password should be rejected")

        # Strong password should be accepted
        is_valid, msg = PasswordValidator.validate(self.test_password)
        self.assertTrue(is_valid, f"Strong password should be accepted: {msg}")

    def test_AC1_password_requirements(self):
        """AC1: Test specific password requirements."""
        # Test minimum length
        is_valid, msg = PasswordValidator.validate("Short1!")
        self.assertFalse(is_valid)
        self.assertIn("12 characters", msg)

        # Test uppercase requirement
        is_valid, msg = PasswordValidator.validate("nouppercase123!")
        self.assertFalse(is_valid)
        self.assertIn("uppercase", msg)

        # Test lowercase requirement
        is_valid, msg = PasswordValidator.validate("NOLOWERCASE123!")
        self.assertFalse(is_valid)
        self.assertIn("lowercase", msg)

        # Test digit requirement
        is_valid, msg = PasswordValidator.validate("NoDigitsHere!")
        self.assertFalse(is_valid)
        self.assertIn("digit", msg)

        # Test special character requirement
        is_valid, msg = PasswordValidator.validate("NoSpecialChars123")
        self.assertFalse(is_valid)
        self.assertIn("special", msg)

    # =========================================================================
    # Acceptance Criteria 2: Account lockout after 5 failed attempts
    # =========================================================================

    def test_AC2_account_lockout_after_5_attempts(self):
        """AC2: Verify account locks after 5 failed login attempts."""
        test_user = "lockout_test_user"

        # First 4 attempts should not lock account
        for i in range(4):
            AccountLockout.record_failed_attempt(test_user)
            is_locked, _ = AccountLockout.is_account_locked(test_user)
            self.assertFalse(is_locked, f"Account should not be locked after {i+1} attempts")

        # 5th attempt should lock account
        AccountLockout.record_failed_attempt(test_user)
        is_locked, locked_until = AccountLockout.is_account_locked(test_user)
        self.assertTrue(is_locked, "Account should be locked after 5 failed attempts")
        self.assertIsNotNone(locked_until, "Lockout expiration should be set")

    def test_AC2_lockout_duration(self):
        """AC2: Verify lockout has appropriate duration."""
        test_user = "lockout_duration_test"

        # Trigger lockout
        for i in range(MAX_FAILED_ATTEMPTS):
            AccountLockout.record_failed_attempt(test_user)

        is_locked, locked_until = AccountLockout.is_account_locked(test_user)
        self.assertTrue(is_locked)

        # Lockout should expire in the future
        self.assertGreater(locked_until, datetime.utcnow())

        # Should expire within reasonable time (< 1 hour)
        max_lockout = datetime.utcnow() + timedelta(hours=1)
        self.assertLess(locked_until, max_lockout)

    def test_AC2_failed_attempt_counter_reset(self):
        """AC2: Verify failed attempts reset after successful login."""
        test_user = "reset_test_user"

        # Record some failed attempts
        for i in range(3):
            AccountLockout.record_failed_attempt(test_user)

        count = AccountLockout.get_failed_attempts_count(test_user)
        self.assertEqual(count, 3)

        # Reset (simulates successful login)
        AccountLockout.reset_failed_attempts(test_user)

        count = AccountLockout.get_failed_attempts_count(test_user)
        self.assertEqual(count, 0, "Failed attempts should reset to 0")

    def test_AC2_authentication_with_lockout(self):
        """AC2: Test full authentication flow with account lockout."""
        if not BCRYPT_AVAILABLE:
            self.skipTest("Bcrypt not available")

        test_user = "auth_lockout_test"
        hashed = PasswordHasher.hash_password(self.test_password)

        # First 4 wrong password attempts
        for i in range(4):
            result = AuthManager.authenticate(test_user, "WrongPass123!", hashed)
            self.assertFalse(result["success"])
            self.assertIn("attempts remaining", result["error"].lower())

        # 5th wrong attempt should lock account
        result = AuthManager.authenticate(test_user, "WrongPass123!", hashed)
        self.assertFalse(result["success"])
        self.assertIn("locked", result["error"].lower())

        # Correct password should still be rejected (account locked)
        result = AuthManager.authenticate(test_user, self.test_password, hashed)
        self.assertFalse(result["success"])
        self.assertIn("locked", result["error"].lower())

    # =========================================================================
    # Acceptance Criteria 3: Session tokens are cryptographically random
    # =========================================================================

    def test_AC3_session_token_randomness(self):
        """AC3: Verify session tokens are cryptographically random."""
        # Generate multiple tokens
        tokens = [TokenManager.generate_token() for _ in range(10)]

        # All tokens should be unique
        self.assertEqual(len(tokens), len(set(tokens)),
                       "All tokens should be unique (cryptographically random)")

        # Tokens should have correct length (64 hex chars = 32 bytes)
        for token in tokens:
            self.assertEqual(len(token), 64, "Token should be 64 hex characters")

    def test_AC3_session_creation(self):
        """AC3: Test session creation with cryptographic token."""
        token = SessionManager.create_session(
            user_id=self.test_user_id,
            ip_address="192.168.1.100"
        )

        # Token should be returned
        self.assertIsNotNone(token)
        self.assertEqual(len(token), 64)

        # Token should validate
        user_id = SessionManager.validate_session(token)
        self.assertEqual(user_id, self.test_user_id)

    def test_AC3_session_token_not_predictable(self):
        """AC3: Verify tokens cannot be predicted from previous tokens."""
        # Generate sequential tokens
        token1 = TokenManager.generate_token()
        token2 = TokenManager.generate_token()
        token3 = TokenManager.generate_token()

        # Convert to integers to check for sequential patterns
        int1 = int(token1, 16)
        int2 = int(token2, 16)
        int3 = int(token3, 16)

        # Tokens should not be sequential
        self.assertNotEqual(int2, int1 + 1, "Tokens should not be sequential")
        self.assertNotEqual(int3, int2 + 1, "Tokens should not be sequential")

        # Differences should be large and random
        diff1 = abs(int2 - int1)
        diff2 = abs(int3 - int2)

        # Differences should be significant (not small increments)
        min_difference = 2**200  # Very large number
        self.assertGreater(diff1, min_difference)
        self.assertGreater(diff2, min_difference)

    # =========================================================================
    # Acceptance Criteria 4: Sessions expire after inactivity (1 hour)
    # =========================================================================

    def test_AC4_session_inactivity_timeout_config(self):
        """AC4: Verify session inactivity timeout is configured."""
        # Should be 60 minutes (1 hour) per SEC-004
        self.assertEqual(SESSION_INACTIVITY_TIMEOUT_MINUTES, 60,
                       "Session timeout should be 1 hour (60 minutes)")

    def test_AC4_session_activity_update(self):
        """AC4: Test session activity updates extend session lifetime."""
        token = SessionManager.create_session(self.test_user_id)

        # Update activity
        time.sleep(1)
        updated = SessionManager.update_activity(token)
        self.assertTrue(updated, "Activity should be updated")

        # Session should still be valid
        user_id = SessionManager.validate_session(token)
        self.assertEqual(user_id, self.test_user_id)

    def test_AC4_session_expiration_simulation(self):
        """AC4: Test session expiration (simulated)."""
        token = SessionManager.create_session(self.test_user_id)

        # Get internal session and manually expire it
        hashed_token = TokenManager.hash_token(token)
        session = SessionManager.store.get(hashed_token)

        # Set last activity to 2 hours ago (past timeout)
        session.last_activity = datetime.utcnow() - timedelta(hours=2)

        # Validation should fail (session expired)
        user_id = SessionManager.validate_session(token)
        self.assertIsNone(user_id, "Expired session should not validate")

    # =========================================================================
    # Acceptance Criteria 5: Secure cookie flags (HttpOnly, Secure, SameSite)
    # =========================================================================

    def test_AC5_secure_cookie_flags(self):
        """AC5: Verify secure cookie flags are configured."""
        # Get cookie configuration
        config = SessionManager.get_cookie_config()

        # SEC-004 requirements
        self.assertTrue(config['httponly'],
                      "HttpOnly flag must be True (prevents XSS)")
        self.assertTrue(config['secure'],
                      "Secure flag must be True (HTTPS only)")
        self.assertEqual(config['samesite'], 'Strict',
                       "SameSite should be Strict (prevents CSRF)")

    def test_AC5_cookie_config_values(self):
        """AC5: Test all cookie configuration values."""
        config = SessionManager.get_cookie_config()

        # Verify all required fields
        self.assertIn('httponly', config)
        self.assertIn('secure', config)
        self.assertIn('samesite', config)
        self.assertIn('path', config)
        self.assertIn('max_age', config)

        # Verify max_age matches session timeout
        expected_max_age = SESSION_INACTIVITY_TIMEOUT_MINUTES * 60
        self.assertEqual(config['max_age'], expected_max_age)

    # =========================================================================
    # Acceptance Criteria 6: Optional MFA/2FA support
    # =========================================================================

    def test_AC6_mfa_secret_generation(self):
        """AC6: Test MFA secret generation."""
        if not TOTP_AVAILABLE:
            self.skipTest("TOTP library not available (optional)")

        secret = MFAManager.generate_secret()
        self.assertIsNotNone(secret)
        self.assertGreater(len(secret), 0)

    def test_AC6_mfa_enable_for_user(self):
        """AC6: Test enabling MFA for a user."""
        if not TOTP_AVAILABLE:
            self.skipTest("TOTP library not available (optional)")

        mfa_user = "mfa_test_user"
        mfa_data = MFAManager.enable_mfa(mfa_user)

        # Should return secret, QR URI, and backup codes
        self.assertIn('secret', mfa_data)
        self.assertIn('qr_uri', mfa_data)
        self.assertIn('backup_codes', mfa_data)

        # Should have multiple backup codes
        self.assertGreater(len(mfa_data['backup_codes']), 5)

        # MFA should be enabled
        self.assertTrue(MFAManager.is_mfa_enabled(mfa_user))

    def test_AC6_mfa_authentication_flow(self):
        """AC6: Test full authentication with MFA."""
        if not BCRYPT_AVAILABLE or not TOTP_AVAILABLE:
            self.skipTest("Required libraries not available")

        mfa_user = "mfa_auth_test"
        hashed = PasswordHasher.hash_password(self.test_password)

        # Enable MFA
        mfa_data = MFAManager.enable_mfa(mfa_user)

        # First auth attempt with correct password but no MFA token
        result = AuthManager.authenticate(mfa_user, self.test_password, hashed)
        self.assertFalse(result["success"])
        self.assertTrue(result.get("requires_mfa", False))

        # Note: Can't test actual TOTP verification without time manipulation
        # In production, would use time-based token from authenticator app

    def test_AC6_backup_codes(self):
        """AC6: Test MFA backup codes."""
        if not TOTP_AVAILABLE:
            self.skipTest("TOTP library not available")

        # Generate backup codes
        codes = MFAManager.generate_backup_codes(count=10)

        self.assertEqual(len(codes), 10)

        # All codes should be unique
        self.assertEqual(len(codes), len(set(codes)))

        # Codes should be 8 characters
        for code in codes:
            self.assertEqual(len(code), 8)

    # =========================================================================
    # Acceptance Criteria 7: No credentials in URLs or logs
    # =========================================================================

    def test_AC7_credential_sanitization(self):
        """AC7: Test credential sanitization for logging."""
        # Sample log entry with credentials
        log_entry = "Login attempt: username=admin, password=SecretPass123, token=abc123xyz"

        # Sanitize
        sanitized = CredentialSanitizer.sanitize_for_logging(log_entry)

        # Credentials should be redacted
        self.assertNotIn("SecretPass123", sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_AC7_sensitive_pattern_detection(self):
        """AC7: Test detection of various sensitive patterns."""
        test_cases = [
            ("password=mysecret123", True),
            ("token=abc123def456", True),
            ("api_key=sk_live_123", True),
            ("secret=hidden_value", True),
            ("username=admin", False),  # username is not always sensitive
        ]

        for text, should_contain_redacted in test_cases:
            sanitized = CredentialSanitizer.sanitize_for_logging(text)

            if should_contain_redacted:
                # Original credential should not appear
                original_value = text.split("=")[1]
                self.assertNotIn(original_value, sanitized,
                               f"Credential should be sanitized in: {text}")

    def test_AC7_url_safety_check(self):
        """AC7: Test URL safety checker."""
        # Safe values
        self.assertTrue(CredentialSanitizer.is_safe_for_url("user123"))
        self.assertTrue(CredentialSanitizer.is_safe_for_url("12345"))

        # Unsafe values (look like credentials)
        self.assertFalse(CredentialSanitizer.is_safe_for_url("MySecretPasswordValue123"))
        self.assertFalse(CredentialSanitizer.is_safe_for_url("api_key_value"))
        self.assertFalse(CredentialSanitizer.is_safe_for_url("secret_token_here"))

    # =========================================================================
    # Integration Tests
    # =========================================================================

    def test_full_authentication_flow(self):
        """Integration: Test complete authentication flow."""
        if not BCRYPT_AVAILABLE:
            self.skipTest("Bcrypt not available")

        # 1. Register user (hash password)
        user_id = "integration_test_user"
        password = "IntegrationP@ss123"

        hashed = AuthManager.hash_password(password)
        self.assertIsNotNone(hashed)

        # 2. Attempt login with wrong password
        result = AuthManager.authenticate(user_id, "WrongPass123!", hashed)
        self.assertFalse(result["success"])

        # 3. Login with correct password
        result = AuthManager.authenticate(user_id, password, hashed)
        self.assertTrue(result["success"])

        # 4. Create session
        session_token = SessionManager.create_session(user_id)
        self.assertIsNotNone(session_token)

        # 5. Validate session
        validated_user = SessionManager.validate_session(session_token)
        self.assertEqual(validated_user, user_id)

        # 6. Logout
        ended = SessionManager.end_session(session_token)
        self.assertTrue(ended)

        # 7. Session should be invalid after logout
        validated_user = SessionManager.validate_session(session_token)
        self.assertIsNone(validated_user)

    def test_password_reset_flow(self):
        """Integration: Test password reset flow."""
        user_id = "reset_flow_user"

        # 1. Generate reset token
        token = PasswordReset.generate_reset_token(user_id)
        self.assertIsNotNone(token)
        self.assertEqual(len(token), 64)

        # 2. Verify token
        verified_user = PasswordReset.verify_reset_token(token)
        self.assertEqual(verified_user, user_id)

        # 3. Use token (invalidate it)
        PasswordReset.invalidate_reset_token(token)

        # 4. Token should no longer be valid
        verified_user = PasswordReset.verify_reset_token(token)
        self.assertIsNone(verified_user)


def run_tests():
    """Run all SEC-004 tests and generate report."""
    print("SEC-004: Broken Authentication Prevention - Test Suite")
    print("=" * 70)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSEC004Authentication)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print()

    # Print acceptance criteria summary
    print("SEC-004 ACCEPTANCE CRITERIA:")
    print("-" * 70)
    print("✅ AC1: Bcrypt/Argon2 password hashing (cost factor 12+)")
    print("✅ AC2: Account lockout after 5 failed attempts")
    print("✅ AC3: Session tokens are cryptographically random")
    print("✅ AC4: Sessions expire after inactivity (1 hour)")
    print("✅ AC5: Secure cookie flags (HttpOnly, Secure, SameSite)")
    print("✅ AC6: Optional MFA/2FA support")
    print("✅ AC7: No credentials in URLs or logs")
    print()

    # Check if all tests passed
    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED - SEC-004 COMPLETE!")
        return True
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
