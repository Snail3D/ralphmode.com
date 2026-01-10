#!/usr/bin/env python3
"""
SANITIZER - Broadcast-Safe Output Filter for Ralph Mode

This module strips sensitive information from messages BEFORE they reach Groq
or get sent to Telegram. Groq can't leak what it never sees.

BC-001: Sanitization layer between Claude and Groq
BC-002: Output filter before Telegram send
BC-003: Regex patterns for common secrets
BC-004: .env key name detection
"""

import re
import os
import logging
from typing import List, Tuple, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# BC-003: REGEX PATTERNS FOR COMMON SECRETS
# =============================================================================

SECRET_PATTERNS = [
    # API Keys
    (r'sk-[a-zA-Z0-9]{20,}', '[OPENAI_KEY]'),  # OpenAI
    (r'sk-ant-[a-zA-Z0-9\-]{20,}', '[ANTHROPIC_KEY]'),  # Anthropic
    (r'ghp_[a-zA-Z0-9]{36,}', '[GITHUB_TOKEN]'),  # GitHub Personal Access Token
    (r'gho_[a-zA-Z0-9]{36,}', '[GITHUB_OAUTH]'),  # GitHub OAuth
    (r'github_pat_[a-zA-Z0-9_]{22,}', '[GITHUB_PAT]'),  # GitHub Fine-grained PAT
    (r'glpat-[a-zA-Z0-9\-]{20,}', '[GITLAB_TOKEN]'),  # GitLab
    (r'AKIA[A-Z0-9]{16}', '[AWS_ACCESS_KEY]'),  # AWS Access Key
    (r'gsk_[a-zA-Z0-9]{20,}', '[GROQ_KEY]'),  # Groq
    (r'xox[baprs]-[a-zA-Z0-9\-]{10,}', '[SLACK_TOKEN]'),  # Slack
    (r'[a-zA-Z0-9]{32}:AAF[a-zA-Z0-9_-]{33}', '[TELEGRAM_TOKEN]'),  # Telegram Bot Token

    # IP Addresses
    (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_ADDRESS]'),  # IPv4
    (r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b', '[IPv6_ADDRESS]'),  # IPv6

    # Connection Strings
    (r'postgres(?:ql)?://[^\s]+', '[DATABASE_URL]'),  # PostgreSQL
    (r'mysql://[^\s]+', '[DATABASE_URL]'),  # MySQL
    (r'mongodb(?:\+srv)?://[^\s]+', '[DATABASE_URL]'),  # MongoDB
    (r'redis://[^\s]+', '[REDIS_URL]'),  # Redis
    (r'amqp://[^\s]+', '[AMQP_URL]'),  # RabbitMQ

    # JWT Tokens (base64.base64.signature format)
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[JWT_TOKEN]'),

    # Private Keys
    (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', '[PRIVATE_KEY_START]'),
    (r'-----BEGIN PGP PRIVATE KEY BLOCK-----', '[PGP_PRIVATE_KEY]'),

    # Common Secret Patterns
    (r'(?i)password\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', '[PASSWORD_REDACTED]'),
    (r'(?i)secret\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', '[SECRET_REDACTED]'),
    (r'(?i)api[_-]?key\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', '[API_KEY_REDACTED]'),
    (r'(?i)auth[_-]?token\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', '[AUTH_TOKEN_REDACTED]'),
    (r'(?i)access[_-]?token\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', '[ACCESS_TOKEN_REDACTED]'),

    # Email addresses (optional - may want to keep for context)
    # (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),

    # Long random strings (likely tokens) - 32+ alphanumeric chars
    (r'\b[a-zA-Z0-9]{40,}\b', '[LONG_TOKEN]'),

    # SSH key fingerprints
    (r'SHA256:[a-zA-Z0-9+/]{43}', '[SSH_FINGERPRINT]'),

    # Bearer tokens
    (r'(?i)bearer\s+[a-zA-Z0-9\-._~+/]+=*', '[BEARER_TOKEN]'),
]

# Compile patterns for efficiency
COMPILED_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(pattern), replacement)
    for pattern, replacement in SECRET_PATTERNS
]


class Sanitizer:
    """
    Sanitizes text to remove sensitive information before it reaches
    external AI services or is displayed publicly.
    """

    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize sanitizer with optional .env path for project-specific filtering.

        Args:
            env_path: Path to .env file for additional secret detection
        """
        self.env_values: Set[str] = set()
        self.env_keys: Set[str] = set()
        self.audit_log: List[dict] = []
        self.broadcast_safe_mode = os.environ.get('BROADCAST_SAFE', 'false').lower() == 'true'

        # BC-004: Load .env values if path provided
        if env_path and os.path.exists(env_path):
            self._load_env_secrets(env_path)
        else:
            # Try default location
            default_env = os.path.join(os.path.dirname(__file__), '.env')
            if os.path.exists(default_env):
                self._load_env_secrets(default_env)

    def _load_env_secrets(self, env_path: str) -> None:
        """
        Load secrets from .env file for project-specific filtering.

        Args:
            env_path: Path to .env file
        """
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")

                        # Store both key names and values
                        if len(value) >= 8:  # Only store substantial values
                            self.env_values.add(value)
                            self.env_keys.add(key)

            logger.info(f"Loaded {len(self.env_values)} secret values from .env")
        except Exception as e:
            logger.warning(f"Could not load .env secrets: {e}")

    def sanitize(self, text: str, context: str = "unknown") -> str:
        """
        Sanitize text by removing all detected secrets.

        Args:
            text: The text to sanitize
            context: Description of where this text came from (for audit log)

        Returns:
            Sanitized text with secrets replaced
        """
        if not text:
            return text

        original = text
        replacements = []

        # BC-003: Apply regex patterns
        for pattern, replacement in COMPILED_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                if len(match) > 6:  # Don't replace very short matches
                    replacements.append({
                        'pattern': pattern.pattern[:50],
                        'replacement': replacement,
                        'matched_length': len(match)
                    })
            text = pattern.sub(replacement, text)

        # BC-004: Replace known .env values
        for value in self.env_values:
            if value in text:
                replacements.append({
                    'pattern': '.env value',
                    'replacement': '[ENV_SECRET]',
                    'matched_length': len(value)
                })
                text = text.replace(value, '[ENV_SECRET]')

        # Log what was filtered (BC-005: Audit logging)
        if replacements:
            self._log_sanitization(context, len(replacements), replacements)

        return text

    def sanitize_for_groq(self, text: str) -> str:
        """
        Sanitize text before sending to Groq for AI processing.
        This is the PRIMARY protection layer.

        Args:
            text: Text to sanitize before Groq sees it

        Returns:
            Sanitized text safe for Groq
        """
        return self.sanitize(text, context="groq_input")

    def sanitize_for_telegram(self, text: str) -> str:
        """
        Final sanitization pass before sending to Telegram.
        Belt-and-suspenders - catches anything that slipped through.

        Args:
            text: Text to sanitize before Telegram display

        Returns:
            Sanitized text safe for public display
        """
        sanitized = self.sanitize(text, context="telegram_output")

        # Extra check in broadcast-safe mode
        if self.broadcast_safe_mode:
            # More aggressive filtering - replace any long alphanumeric strings
            sanitized = re.sub(r'\b[a-zA-Z0-9]{20,}\b', '[REDACTED]', sanitized)

        return sanitized

    def is_safe(self, text: str) -> bool:
        """
        Check if text is safe (contains no detected secrets).

        Args:
            text: Text to check

        Returns:
            True if no secrets detected, False otherwise
        """
        # Check regex patterns
        for pattern, _ in COMPILED_PATTERNS:
            if pattern.search(text):
                return False

        # Check .env values
        for value in self.env_values:
            if value in text:
                return False

        return True

    def _log_sanitization(self, context: str, count: int, details: List[dict]) -> None:
        """
        Log what was sanitized for debugging/auditing.

        Args:
            context: Where the sanitization occurred
            count: Number of replacements made
            details: List of replacement details
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'replacements_count': count,
            'patterns_matched': [d['replacement'] for d in details]
        }

        self.audit_log.append(log_entry)

        # Keep log from growing too large
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-500:]

        logger.info(f"Sanitized {count} secrets from {context}: {[d['replacement'] for d in details]}")

    def get_audit_summary(self, limit: int = 20) -> List[dict]:
        """
        Get recent audit log entries.

        Args:
            limit: Maximum entries to return

        Returns:
            Recent audit log entries
        """
        return self.audit_log[-limit:]

    def add_secret(self, secret: str) -> None:
        """
        Add a new secret to filter (runtime addition).

        Args:
            secret: The secret value to filter
        """
        if len(secret) >= 8:
            self.env_values.add(secret)
            logger.info(f"Added new secret to filter (length: {len(secret)})")


# Global sanitizer instance
_sanitizer: Optional[Sanitizer] = None


def get_sanitizer() -> Sanitizer:
    """Get or create the global sanitizer instance."""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = Sanitizer()
    return _sanitizer


def sanitize(text: str) -> str:
    """Convenience function to sanitize text."""
    return get_sanitizer().sanitize(text)


def sanitize_for_groq(text: str) -> str:
    """Convenience function to sanitize text for Groq."""
    return get_sanitizer().sanitize_for_groq(text)


def sanitize_for_telegram(text: str) -> str:
    """Convenience function to sanitize text for Telegram."""
    return get_sanitizer().sanitize_for_telegram(text)


def is_safe(text: str) -> bool:
    """Convenience function to check if text is safe."""
    return get_sanitizer().is_safe(text)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test the sanitizer
    test_strings = [
        "My API key is sk-1234567890abcdefghijklmnop",
        "Connect to postgres://user:password123@localhost:5432/db",
        "Server IP is 192.168.1.100 and password=supersecret123",
        "GitHub token: ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "This text has no secrets in it.",
        "AWS key AKIAIOSFODNN7EXAMPLE is exposed!",
    ]

    s = Sanitizer()

    print("=" * 60)
    print("SANITIZER TEST")
    print("=" * 60)

    for test in test_strings:
        print(f"\nOriginal: {test[:60]}...")
        sanitized = s.sanitize(test)
        print(f"Sanitized: {sanitized}")
        print(f"Is safe: {s.is_safe(test)} -> {s.is_safe(sanitized)}")
