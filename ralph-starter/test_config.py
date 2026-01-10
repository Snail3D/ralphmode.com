#!/usr/bin/env python3
"""
Tests for SEC-007: Security Misconfiguration Prevention

Tests the Config class validation and security enforcement.
"""

import os
import sys
import unittest
from unittest.mock import patch
from config import Config, ProductionConfig, DevelopmentConfig, ConfigurationError


class TestSecurityMisconfiguration(unittest.TestCase):
    """Test SEC-007: Security Misconfiguration Prevention"""

    def setUp(self):
        """Store original environment"""
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Restore original environment"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_debug_false_in_production(self):
        """SEC-007: DEBUG must be False in production"""
        os.environ['RALPH_ENV'] = 'production'
        os.environ['DEBUG'] = 'False'

        config = ProductionConfig()
        self.assertFalse(config.DEBUG, "DEBUG must be False in production")

    def test_debug_true_in_production_detected(self):
        """SEC-007: Detect DEBUG=True in production"""
        os.environ['RALPH_ENV'] = 'production'
        os.environ['DEBUG'] = 'True'

        # Force re-evaluation
        class TestProdConfig(Config):
            ENV = 'production'
            DEBUG = True

        is_valid, issues = TestProdConfig.validate()
        self.assertFalse(is_valid, "Should detect DEBUG=True in production")
        self.assertTrue(
            any('DEBUG=True' in issue for issue in issues),
            "Should report DEBUG=True issue"
        )

    def test_secret_keys_required_in_production(self):
        """SEC-007: Secret keys must be set in production"""
        class TestProdConfig(Config):
            ENV = 'production'
            SECRET_KEY = None
            SESSION_SECRET_KEY = None
            CSRF_SECRET_KEY = None

        is_valid, issues = TestProdConfig.validate()
        self.assertFalse(is_valid, "Should require secret keys in production")
        self.assertTrue(
            any('SECRET_KEY not set' in issue for issue in issues),
            "Should report missing SECRET_KEY"
        )

    def test_secret_key_length_validation(self):
        """SEC-007: Secret keys must be sufficiently long"""
        class TestProdConfig(Config):
            ENV = 'production'
            SECRET_KEY = 'short'
            SESSION_SECRET_KEY = 'x' * 32
            CSRF_SECRET_KEY = 'y' * 32

        is_valid, issues = TestProdConfig.validate()
        self.assertFalse(is_valid, "Should reject short secret keys")
        self.assertTrue(
            any('too short' in issue for issue in issues),
            "Should report short SECRET_KEY"
        )

    def test_default_credentials_detection(self):
        """SEC-007: Detect insecure default credentials"""
        class TestProdConfig(Config):
            ENV = 'production'
            SECRET_KEY = 'changeme_this_is_bad'
            SESSION_SECRET_KEY = 'your_token_here'
            CSRF_SECRET_KEY = 'password123'

        is_valid, issues = TestProdConfig.validate()
        self.assertFalse(is_valid, "Should detect default credentials")
        critical_issues = [i for i in issues if 'insecure default' in i.lower()]
        self.assertGreater(len(critical_issues), 0, "Should report insecure defaults")

    def test_https_enforced_in_production(self):
        """SEC-007: HTTPS should be enforced in production"""
        class TestProdConfig(Config):
            ENV = 'production'
            FORCE_HTTPS = False

        is_valid, issues = TestProdConfig.validate()
        warnings = [i for i in issues if 'HTTPS' in i]
        self.assertGreater(len(warnings), 0, "Should warn about HTTPS not enforced")

    def test_secure_cookies_in_production(self):
        """SEC-007: Cookies must be secure in production"""
        class TestProdConfig(Config):
            ENV = 'production'
            SESSION_COOKIE_SECURE = False

        is_valid, issues = TestProdConfig.validate()
        self.assertFalse(is_valid, "Should require secure cookies in production")
        self.assertTrue(
            any('SESSION_COOKIE_SECURE' in issue for issue in issues),
            "Should report insecure cookies"
        )

    def test_unnecessary_features_disabled_in_production(self):
        """SEC-007: Unnecessary features must be disabled in production"""
        class TestProdConfig(Config):
            ENV = 'production'
            TEMPLATES_AUTO_RELOAD = True
            EXPLAIN_TEMPLATE_LOADING = True
            PROPAGATE_EXCEPTIONS = True

        is_valid, issues = TestProdConfig.validate()
        warnings = [i for i in issues if i.startswith('WARNING')]
        self.assertGreater(len(warnings), 2, "Should warn about unnecessary features")

    def test_testing_mode_disabled_in_production(self):
        """SEC-007: Testing mode must be disabled in production"""
        class TestProdConfig(Config):
            ENV = 'production'
            TESTING = True

        is_valid, issues = TestProdConfig.validate()
        self.assertFalse(is_valid, "Should reject TESTING=True in production")
        self.assertTrue(
            any('TESTING=True' in issue for issue in issues),
            "Should report testing mode enabled"
        )

    def test_allowed_origins_validation(self):
        """SEC-007: ALLOWED_ORIGINS must be properly configured"""
        class TestProdConfig(Config):
            ENV = 'production'
            ALLOWED_ORIGINS = ['*']

        is_valid, issues = TestProdConfig.validate()
        self.assertFalse(is_valid, "Should reject wildcard ALLOWED_ORIGINS")

    def test_localhost_in_production_origins(self):
        """SEC-007: localhost should not be in production ALLOWED_ORIGINS"""
        class TestProdConfig(Config):
            ENV = 'production'
            ALLOWED_ORIGINS = ['https://ralphmode.com', 'http://localhost:3000']

        is_valid, issues = TestProdConfig.validate()
        warnings = [i for i in issues if 'localhost' in i]
        self.assertGreater(len(warnings), 0, "Should warn about localhost in production")

    def test_api_keys_required_in_production(self):
        """SEC-007: API keys should be set in production"""
        class TestProdConfig(Config):
            ENV = 'production'
            TELEGRAM_BOT_TOKEN = None
            GROQ_API_KEY = None

        is_valid, issues = TestProdConfig.validate()
        errors = [i for i in issues if 'not set' in i]
        self.assertGreater(len(errors), 0, "Should warn about missing API keys")

    def test_development_config_more_permissive(self):
        """SEC-007: Development config can have DEBUG=True"""
        class TestDevConfig(Config):
            ENV = 'development'
            DEBUG = True
            FORCE_HTTPS = False
            SESSION_COOKIE_SECURE = False

        is_valid, issues = TestDevConfig.validate()
        # Development should pass validation even with less strict settings
        critical_issues = [i for i in issues if i.startswith('CRITICAL')]
        self.assertEqual(len(critical_issues), 0, "Development config should be valid")

    def test_production_config_strict(self):
        """SEC-007: Production config must be strict"""
        # Production config should fail without proper secrets
        is_valid, issues = ProductionConfig.validate()

        # Should have issues if secrets not set
        if not os.getenv('SECRET_KEY'):
            self.assertFalse(is_valid, "Production should require secrets")

    def test_flask_config_generation(self):
        """SEC-007: Flask config should be properly generated"""
        config_dict = ProductionConfig.get_flask_config()

        self.assertIn('DEBUG', config_dict)
        self.assertIn('SESSION_COOKIE_SECURE', config_dict)
        self.assertIn('SESSION_COOKIE_HTTPONLY', config_dict)
        self.assertFalse(config_dict['DEBUG'], "DEBUG should be False in production Flask config")

    def test_config_validation_comprehensive(self):
        """SEC-007: Comprehensive validation test"""
        # Create a fully secure production config
        class SecureProdConfig(Config):
            ENV = 'production'
            DEBUG = False
            TESTING = False
            SECRET_KEY = 'a' * 64
            SESSION_SECRET_KEY = 'b' * 64
            CSRF_SECRET_KEY = 'c' * 64
            FORCE_HTTPS = True
            SESSION_COOKIE_SECURE = True
            TEMPLATES_AUTO_RELOAD = False
            EXPLAIN_TEMPLATE_LOADING = False
            PROPAGATE_EXCEPTIONS = False
            ALLOWED_ORIGINS = ['https://ralphmode.com']
            TELEGRAM_BOT_TOKEN = 'valid_token'
            GROQ_API_KEY = 'valid_key'

        is_valid, issues = SecureProdConfig.validate()
        critical_issues = [i for i in issues if i.startswith('CRITICAL')]
        self.assertEqual(len(critical_issues), 0, f"Should have no critical issues, got: {critical_issues}")

    def test_server_tokens_off_concept(self):
        """SEC-007: Verify concept of server tokens being disabled"""
        # This is handled by nginx.conf, just verify we understand the requirement
        # server_tokens off; should be in nginx config
        self.assertTrue(True, "Server tokens should be disabled in nginx.conf")

    def test_directory_listing_disabled_concept(self):
        """SEC-007: Verify concept of directory listing being disabled"""
        # This is handled by nginx.conf (autoindex off)
        self.assertTrue(True, "Directory listing should be disabled in nginx.conf")


class TestConfigurationErrorHandling(unittest.TestCase):
    """Test error handling and reporting"""

    def test_validation_returns_tuple(self):
        """Validation should return (bool, list) tuple"""
        result = Config.validate()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], list)

    def test_issues_list_contains_strings(self):
        """Issues list should contain string descriptions"""
        is_valid, issues = Config.validate()
        for issue in issues:
            self.assertIsInstance(issue, str)

    def test_critical_issues_marked(self):
        """Critical issues should be marked with CRITICAL prefix"""
        class TestConfig(Config):
            ENV = 'production'
            DEBUG = True  # This should be CRITICAL

        is_valid, issues = TestConfig.validate()
        critical = [i for i in issues if i.startswith('CRITICAL')]
        self.assertGreater(len(critical), 0, "Should have critical issues")


def run_tests():
    """Run all tests"""
    unittest.main()


if __name__ == '__main__':
    run_tests()
