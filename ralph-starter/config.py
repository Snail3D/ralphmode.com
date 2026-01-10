#!/usr/bin/env python3
"""
Configuration Management for Ralph Mode
SEC-007: Security Misconfiguration Prevention
SEC-016: Secrets Management

This module enforces secure configuration defaults and prevents
common security misconfigurations in production.

SEC-016: Secrets are loaded from SecretsManager (Vault/AWS) at runtime,
never from code or config files.
"""

import os
import sys
import warnings
from typing import Dict, List, Tuple, Optional
from enum import Enum


class Environment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigurationError(Exception):
    """Raised when insecure configuration is detected"""
    pass


class Config:
    """
    Secure configuration with environment-specific settings.

    SEC-007: Enforces secure defaults and prevents misconfigurations.
    SEC-016: Secrets loaded from SecretsManager at runtime.
    """

    # Detect environment (default to production for safety)
    ENV = os.getenv('RALPH_ENV', 'production').lower()

    # SEC-007: Debug mode MUST be False in production
    DEBUG = False if ENV == 'production' else os.getenv('DEBUG', 'False').lower() == 'true'

    # SEC-007: Testing mode (disable in production)
    TESTING = False if ENV == 'production' else os.getenv('TESTING', 'False').lower() == 'true'

    # SEC-016: Initialize SecretsManager (lazy loading)
    _secrets_manager = None

    @classmethod
    def _get_secrets_manager(cls):
        """Lazy-load secrets manager"""
        if cls._secrets_manager is None:
            try:
                from secrets_manager import create_secrets_manager
                cls._secrets_manager = create_secrets_manager(cls.ENV)
            except Exception as e:
                # Fall back to environment variables if SecretsManager unavailable
                warnings.warn(f"SecretsManager unavailable, falling back to env vars: {e}")
                cls._secrets_manager = False  # Marker to prevent retrying
        return cls._secrets_manager

    @classmethod
    def _get_secret(cls, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        SEC-016: Get secret from SecretsManager or fall back to env var.

        Args:
            secret_name: Name of the secret
            default: Default value if not found

        Returns:
            Secret value or default
        """
        secrets_manager = cls._get_secrets_manager()

        # If SecretsManager available, use it
        if secrets_manager and secrets_manager is not False:
            try:
                return secrets_manager.get(secret_name, default)
            except Exception:
                pass  # Fall through to env var

        # Fall back to environment variable
        return os.getenv(secret_name, default)

    # Flask secret keys (SEC-016: loaded at runtime from SecretsManager)
    @property
    def SECRET_KEY(self):
        return self._get_secret('SECRET_KEY')

    @property
    def SESSION_SECRET_KEY(self):
        return self._get_secret('SESSION_SECRET_KEY')

    @property
    def CSRF_SECRET_KEY(self):
        return self._get_secret('CSRF_SECRET_KEY')

    # Database configuration
    @property
    def DATABASE_URL(self):
        return self._get_secret('DATABASE_URL')

    # API Keys (SEC-016: never hardcoded, loaded at runtime)
    @property
    def TELEGRAM_BOT_TOKEN(self):
        return self._get_secret('TELEGRAM_BOT_TOKEN')

    @property
    def GROQ_API_KEY(self):
        return self._get_secret('GROQ_API_KEY')

    @property
    def ANTHROPIC_API_KEY(self):
        return self._get_secret('ANTHROPIC_API_KEY')

    # Server configuration (non-sensitive, can remain as class vars)
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))

    # SEC-007: Force HTTPS in production
    FORCE_HTTPS = True if ENV == 'production' else os.getenv('FORCE_HTTPS', 'False').lower() == 'true'

    # SEC-005: Session security
    SESSION_COOKIE_SECURE = True if ENV == 'production' else False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_NAME = '__Host-session' if ENV == 'production' else 'session'

    # SEC-007: Disable unnecessary features in production
    TEMPLATES_AUTO_RELOAD = False if ENV == 'production' else True
    EXPLAIN_TEMPLATE_LOADING = False
    SEND_FILE_MAX_AGE_DEFAULT = 31536000 if ENV == 'production' else 0  # 1 year cache in prod

    # SEC-010: Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO' if ENV == 'production' else 'DEBUG')
    LOG_TO_STDOUT = os.getenv('LOG_TO_STDOUT', 'True').lower() == 'true'

    # SEC-007: Prevent server information leakage
    SERVER_NAME = None  # Don't expose server hostname
    PROPAGATE_EXCEPTIONS = False if ENV == 'production' else True

    # CORS settings
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'https://ralphmode.com').split(',')

    # BC-006: Broadcast-Safe Mode (extra-strict filtering for live streams)
    BROADCAST_SAFE = os.getenv('BROADCAST_SAFE', 'False').lower() == 'true'
    BROADCAST_SAFE_DELAY = float(os.getenv('BROADCAST_SAFE_DELAY', '5.0'))  # Review delay in seconds

    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """
        Validate configuration for security issues.

        SEC-007: Automated configuration scanning
        SEC-016: Validates secrets loaded from SecretsManager

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check 1: DEBUG must be False in production
        if cls.ENV == 'production' and cls.DEBUG:
            issues.append("CRITICAL: DEBUG=True in production environment")

        # Check 2: Secret keys must be set in production
        # SEC-016: Access via properties to load from SecretsManager
        if cls.ENV == 'production':
            secret_key = cls._get_secret('SECRET_KEY')
            if not secret_key:
                issues.append("CRITICAL: SECRET_KEY not set in production")
            elif len(secret_key) < 32:
                issues.append("CRITICAL: SECRET_KEY too short (min 32 characters)")

            if not cls._get_secret('SESSION_SECRET_KEY'):
                issues.append("CRITICAL: SESSION_SECRET_KEY not set in production")

            if not cls._get_secret('CSRF_SECRET_KEY'):
                issues.append("CRITICAL: CSRF_SECRET_KEY not set in production")

        # Check 3: Default credentials check
        # SEC-016: Check secrets from SecretsManager
        insecure_defaults = [
            'changeme', 'password', 'admin', 'secret', 'default',
            'your_token_here', 'your_key_here', 'your_password_here',
            'test', 'demo', '12345', 'password123'
        ]

        for key_name in ['SECRET_KEY', 'SESSION_SECRET_KEY', 'CSRF_SECRET_KEY']:
            key_value = cls._get_secret(key_name, '')
            if key_value:
                if any(default in key_value.lower() for default in insecure_defaults):
                    issues.append(f"CRITICAL: {key_name} contains insecure default value")

        # Check 4: HTTPS enforcement in production
        if cls.ENV == 'production' and not cls.FORCE_HTTPS:
            issues.append("WARNING: HTTPS not enforced in production")

        # Check 5: Secure cookies in production
        if cls.ENV == 'production' and not cls.SESSION_COOKIE_SECURE:
            issues.append("CRITICAL: SESSION_COOKIE_SECURE=False in production")

        # Check 6: Unnecessary features disabled in production
        if cls.ENV == 'production':
            if cls.TEMPLATES_AUTO_RELOAD:
                issues.append("WARNING: TEMPLATES_AUTO_RELOAD=True in production")
            if cls.EXPLAIN_TEMPLATE_LOADING:
                issues.append("WARNING: EXPLAIN_TEMPLATE_LOADING=True in production")
            if cls.PROPAGATE_EXCEPTIONS:
                issues.append("WARNING: PROPAGATE_EXCEPTIONS=True in production")

        # Check 7: Validate API keys are set
        # SEC-016: Load from SecretsManager
        if cls.ENV == 'production':
            if not cls._get_secret('TELEGRAM_BOT_TOKEN'):
                issues.append("ERROR: TELEGRAM_BOT_TOKEN not set")
            if not cls._get_secret('GROQ_API_KEY'):
                issues.append("ERROR: GROQ_API_KEY not set")

        # Check 8: Check for test/development artifacts
        if cls.ENV == 'production':
            if cls.TESTING:
                issues.append("CRITICAL: TESTING=True in production")
            if cls.HOST == '0.0.0.0' and cls.DEBUG:
                issues.append("CRITICAL: Running on 0.0.0.0 with DEBUG=True")

        # Check 9: Validate ALLOWED_ORIGINS
        if cls.ENV == 'production':
            if not cls.ALLOWED_ORIGINS or cls.ALLOWED_ORIGINS == ['*']:
                issues.append("CRITICAL: ALLOWED_ORIGINS not properly configured")
            if any('localhost' in origin for origin in cls.ALLOWED_ORIGINS):
                issues.append("WARNING: localhost in ALLOWED_ORIGINS in production")

        is_valid = len([i for i in issues if i.startswith('CRITICAL')]) == 0
        return is_valid, issues

    @classmethod
    def enforce_security(cls):
        """
        Enforce security configuration and fail-fast if issues found.

        SEC-007: Prevents server from starting with insecure configuration.
        """
        is_valid, issues = cls.validate()

        if not is_valid:
            print("\n🚨 SECURITY CONFIGURATION ERRORS DETECTED 🚨\n", file=sys.stderr)
            for issue in issues:
                print(f"  ❌ {issue}", file=sys.stderr)
            print("\n❌ Server cannot start with insecure configuration", file=sys.stderr)
            print("   Fix the above issues and try again.\n", file=sys.stderr)
            sys.exit(1)

        # Warnings (non-blocking)
        warnings_only = [i for i in issues if i.startswith('WARNING')]
        if warnings_only:
            print("\n⚠️  SECURITY CONFIGURATION WARNINGS ⚠️\n", file=sys.stderr)
            for warning in warnings_only:
                print(f"  ⚠️  {warning}", file=sys.stderr)
            print()

    @classmethod
    def get_flask_config(cls) -> Dict[str, any]:
        """
        Get Flask-compatible configuration dictionary.

        Returns:
            Dictionary of Flask configuration options
        """
        return {
            'DEBUG': cls.DEBUG,
            'TESTING': cls.TESTING,
            'SECRET_KEY': cls.SECRET_KEY,
            'SESSION_COOKIE_SECURE': cls.SESSION_COOKIE_SECURE,
            'SESSION_COOKIE_HTTPONLY': cls.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_SAMESITE': cls.SESSION_COOKIE_SAMESITE,
            'SESSION_COOKIE_NAME': cls.SESSION_COOKIE_NAME,
            'TEMPLATES_AUTO_RELOAD': cls.TEMPLATES_AUTO_RELOAD,
            'EXPLAIN_TEMPLATE_LOADING': cls.EXPLAIN_TEMPLATE_LOADING,
            'SEND_FILE_MAX_AGE_DEFAULT': cls.SEND_FILE_MAX_AGE_DEFAULT,
            'SERVER_NAME': cls.SERVER_NAME,
            'PROPAGATE_EXCEPTIONS': cls.PROPAGATE_EXCEPTIONS,
        }

    @classmethod
    def print_config_summary(cls):
        """
        Print configuration summary (without sensitive data).

        SEC-016: Shows whether secrets are loaded from SecretsManager.
        """
        secrets_manager = cls._get_secrets_manager()
        provider = "None (env vars)" if not secrets_manager or secrets_manager is False else secrets_manager.provider_type.value

        print(f"\n{'='*60}")
        print(f"  Ralph Mode - Configuration Summary")
        print(f"{'='*60}")
        print(f"  Environment:        {cls.ENV}")
        print(f"  Secrets Provider:   {provider}")
        print(f"  Debug Mode:         {cls.DEBUG}")
        print(f"  Testing Mode:       {cls.TESTING}")
        print(f"  Force HTTPS:        {cls.FORCE_HTTPS}")
        print(f"  Secure Cookies:     {cls.SESSION_COOKIE_SECURE}")
        print(f"  Log Level:          {cls.LOG_LEVEL}")
        print(f"  Host:Port:          {cls.HOST}:{cls.PORT}")
        print(f"  Allowed Origins:    {len(cls.ALLOWED_ORIGINS)} origin(s)")
        print(f"  Secret Key Set:     {'Yes' if cls._get_secret('SECRET_KEY') else 'No'}")
        print(f"  Session Key Set:    {'Yes' if cls._get_secret('SESSION_SECRET_KEY') else 'No'}")
        print(f"  CSRF Key Set:       {'Yes' if cls._get_secret('CSRF_SECRET_KEY') else 'No'}")
        print(f"  Telegram Token Set: {'Yes' if cls._get_secret('TELEGRAM_BOT_TOKEN') else 'No'}")
        print(f"  Groq API Key Set:   {'Yes' if cls._get_secret('GROQ_API_KEY') else 'No'}")
        print(f"  Broadcast Safe:     {cls.BROADCAST_SAFE}")
        if cls.BROADCAST_SAFE:
            print(f"  Review Delay:       {cls.BROADCAST_SAFE_DELAY}s")
        print(f"{'='*60}\n")


class ProductionConfig(Config):
    """Production-specific configuration (most secure)"""
    ENV = 'production'
    DEBUG = False
    TESTING = False
    FORCE_HTTPS = True
    SESSION_COOKIE_SECURE = True


class StagingConfig(Config):
    """Staging configuration (production-like but more permissive)"""
    ENV = 'staging'
    DEBUG = False
    TESTING = False
    FORCE_HTTPS = True
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    """Development configuration (permissive for local dev)"""
    ENV = 'development'
    # DEBUG can be enabled in development
    # HTTPS not required locally


# Select configuration based on environment
config_map = {
    'production': ProductionConfig,
    'staging': StagingConfig,
    'development': DevelopmentConfig,
}

# Get current environment
current_env = os.getenv('RALPH_ENV', 'production').lower()
AppConfig = config_map.get(current_env, ProductionConfig)


if __name__ == '__main__':
    """
    Run configuration validation from command line.

    Usage:
        python config.py              # Validate current environment
        RALPH_ENV=production python config.py  # Validate production config
    """
    print("Running configuration validation...")
    AppConfig.print_config_summary()

    is_valid, issues = AppConfig.validate()

    if is_valid:
        print("✅ Configuration is valid!\n")
    else:
        print("❌ Configuration has issues:\n")
        for issue in issues:
            print(f"  - {issue}")
        print()
        sys.exit(1)
