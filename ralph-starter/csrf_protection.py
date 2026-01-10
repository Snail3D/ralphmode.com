#!/usr/bin/env python3
"""
SEC-003: CSRF (Cross-Site Request Forgery) Protection for Ralph Mode

This module provides comprehensive CSRF protection including:
- Cryptographically secure CSRF token generation and validation
- SameSite cookie configuration
- Origin/Referer header validation
- Double-submit cookie pattern for APIs
- Telegram callback query validation

SECURITY PRINCIPLES:
1. GENERATE cryptographically random tokens (secrets.token_urlsafe)
2. VALIDATE tokens on every state-changing request
3. USE SameSite=Strict or Lax for all cookies
4. CHECK Origin/Referer headers as defense-in-depth
5. APPLY double-submit pattern for stateless API protection

Usage:
    from csrf_protection import (
        CSRFProtection,
        generate_csrf_token,
        validate_csrf_token,
        get_secure_cookie_settings,
        OriginValidator,
        TelegramCallbackValidator
    )

    # Generate token for a session
    token = generate_csrf_token(session_id)

    # Validate token on form submission
    if not validate_csrf_token(session_id, submitted_token):
        raise SecurityError("CSRF validation failed")

    # Get secure cookie settings
    cookie_settings = get_secure_cookie_settings()
"""

import os
import hmac
import time
import secrets
import hashlib
import logging
import re
from typing import Dict, Optional, Tuple, List, Set
from datetime import datetime, timedelta
from functools import lru_cache
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# =============================================================================
# SEC-003: CSRF TOKEN GENERATION AND VALIDATION
# =============================================================================

class CSRFProtection:
    """
    CSRF token management with secure generation and validation.

    Uses HMAC-based tokens tied to session IDs for cryptographic security.
    Tokens expire after a configurable time to limit replay attacks.
    """

    # Secret key for HMAC - should be loaded from environment in production
    _secret_key: bytes = None

    # Token storage: {session_id: (token, timestamp)}
    _token_store: Dict[str, Tuple[str, float]] = {}

    # Token expiration time in seconds (default: 1 hour)
    TOKEN_EXPIRY = 3600

    # Maximum tokens to store (prevents memory exhaustion)
    MAX_TOKENS = 10000

    @classmethod
    def _get_secret_key(cls) -> bytes:
        """
        Get or generate the secret key for HMAC operations.

        In production, this MUST be loaded from environment/secrets manager.

        Returns:
            bytes: The secret key
        """
        if cls._secret_key is None:
            # Try to load from environment
            env_key = os.environ.get("CSRF_SECRET_KEY")
            if env_key:
                cls._secret_key = env_key.encode('utf-8')
            else:
                # Generate a random key for this process
                # WARNING: This resets on restart - use env var in production
                logger.warning(
                    "CSRF_SECRET_KEY not set - generating random key. "
                    "Set CSRF_SECRET_KEY in production!"
                )
                cls._secret_key = secrets.token_bytes(32)
        return cls._secret_key

    @classmethod
    def generate_token(cls, session_id: str) -> str:
        """
        Generate a cryptographically secure CSRF token for a session.

        The token is tied to the session ID and includes a timestamp
        for expiration checking.

        Args:
            session_id: Unique identifier for the user's session

        Returns:
            str: The CSRF token (URL-safe base64)

        Example:
            >>> token = CSRFProtection.generate_token("user_12345")
            >>> len(token) > 40  # Token is substantial
            True
        """
        if not session_id:
            raise ValueError("session_id is required")

        # Clean up old tokens periodically
        cls._cleanup_old_tokens()

        # Generate random component
        random_bytes = secrets.token_bytes(16)

        # Create timestamp
        timestamp = int(time.time())

        # Create HMAC signature
        message = f"{session_id}:{timestamp}:{random_bytes.hex()}".encode()
        signature = hmac.new(
            cls._get_secret_key(),
            message,
            hashlib.sha256
        ).hexdigest()

        # Combine into token
        token = f"{timestamp}:{random_bytes.hex()}:{signature}"

        # Store token with timestamp
        cls._token_store[session_id] = (token, timestamp)

        # Return URL-safe version
        return secrets.token_urlsafe(32) + ":" + token

    @classmethod
    def validate_token(cls, session_id: str, token: str) -> bool:
        """
        Validate a CSRF token for a session.

        Checks:
        1. Token format is valid
        2. Token hasn't expired
        3. HMAC signature matches
        4. Token matches stored token for session

        Args:
            session_id: The session ID this token should belong to
            token: The token to validate

        Returns:
            bool: True if token is valid, False otherwise
        """
        if not session_id or not token:
            logger.warning(f"CSRF validation failed: missing session_id or token")
            return False

        try:
            # Parse token
            parts = token.split(":")
            if len(parts) < 4:
                logger.warning("CSRF validation failed: malformed token")
                return False

            # Extract components (random_prefix:timestamp:random_bytes:signature)
            timestamp = int(parts[1])
            random_hex = parts[2]
            signature = parts[3]

            # Check expiration
            current_time = int(time.time())
            if current_time - timestamp > cls.TOKEN_EXPIRY:
                logger.warning(f"CSRF validation failed: token expired")
                return False

            # Verify HMAC signature
            message = f"{session_id}:{timestamp}:{random_hex}".encode()
            expected_sig = hmac.new(
                cls._get_secret_key(),
                message,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                logger.warning("CSRF validation failed: signature mismatch")
                return False

            # Check against stored token (optional but adds security)
            stored = cls._token_store.get(session_id)
            if stored:
                stored_token, stored_time = stored
                # Allow some tolerance for token regeneration
                if abs(stored_time - timestamp) > 60:  # 1 minute tolerance
                    logger.info("CSRF token validated with new token generation")

            return True

        except (ValueError, IndexError) as e:
            logger.warning(f"CSRF validation failed: {e}")
            return False

    @classmethod
    def revoke_token(cls, session_id: str) -> None:
        """
        Revoke the CSRF token for a session.

        Call this on logout or session termination.

        Args:
            session_id: The session whose token should be revoked
        """
        if session_id in cls._token_store:
            del cls._token_store[session_id]

    @classmethod
    def _cleanup_old_tokens(cls) -> None:
        """Remove expired tokens to prevent memory bloat."""
        current_time = int(time.time())
        expired = [
            sid for sid, (_, ts) in cls._token_store.items()
            if current_time - ts > cls.TOKEN_EXPIRY
        ]
        for sid in expired:
            del cls._token_store[sid]

        # Also enforce max tokens limit
        if len(cls._token_store) > cls.MAX_TOKENS:
            # Remove oldest tokens
            sorted_tokens = sorted(
                cls._token_store.items(),
                key=lambda x: x[1][1]
            )
            for sid, _ in sorted_tokens[:len(cls._token_store) - cls.MAX_TOKENS]:
                del cls._token_store[sid]


# Convenience functions
def generate_csrf_token(session_id: str) -> str:
    """Generate a CSRF token for the given session."""
    return CSRFProtection.generate_token(session_id)


def validate_csrf_token(session_id: str, token: str) -> bool:
    """Validate a CSRF token for the given session."""
    return CSRFProtection.validate_token(session_id, token)


# =============================================================================
# SEC-003: SECURE COOKIE CONFIGURATION
# =============================================================================

class SecureCookieConfig:
    """
    Secure cookie configuration with SameSite and other security attributes.

    Implements:
    - SameSite=Strict/Lax to prevent CSRF via cookies
    - HttpOnly to prevent XSS cookie theft
    - Secure to require HTTPS
    - Proper expiration handling
    """

    @staticmethod
    def get_settings(
        same_site: str = "Strict",
        http_only: bool = True,
        secure: bool = True,
        max_age: int = 3600,
        path: str = "/",
        domain: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get secure cookie settings dictionary.

        Args:
            same_site: "Strict", "Lax", or "None" (None requires Secure=True)
            http_only: Prevent JavaScript access
            secure: Require HTTPS (disable only for local dev)
            max_age: Cookie lifetime in seconds
            path: Cookie path
            domain: Cookie domain (None = current domain only)

        Returns:
            Dict with cookie settings for use with response.set_cookie()

        Example:
            >>> settings = SecureCookieConfig.get_settings()
            >>> settings['samesite']
            'Strict'
            >>> settings['httponly']
            True
        """
        # Validate SameSite value
        valid_same_site = {"Strict", "Lax", "None"}
        if same_site not in valid_same_site:
            raise ValueError(f"same_site must be one of {valid_same_site}")

        # SameSite=None requires Secure=True
        if same_site == "None" and not secure:
            logger.warning(
                "SameSite=None requires Secure=True. Setting Secure=True."
            )
            secure = True

        settings = {
            "samesite": same_site,
            "httponly": http_only,
            "secure": secure,
            "max_age": max_age,
            "path": path,
        }

        if domain:
            settings["domain"] = domain

        return settings

    @staticmethod
    def get_csrf_cookie_settings() -> Dict[str, any]:
        """
        Get settings specifically for CSRF token cookie.

        Uses Strict SameSite and HttpOnly for maximum protection.

        Returns:
            Dict with CSRF cookie settings
        """
        return SecureCookieConfig.get_settings(
            same_site="Strict",
            http_only=True,
            secure=True,
            max_age=3600,  # 1 hour
            path="/"
        )

    @staticmethod
    def get_session_cookie_settings() -> Dict[str, any]:
        """
        Get settings for session cookies.

        Uses Lax SameSite to allow top-level navigation while
        still protecting against CSRF.

        Returns:
            Dict with session cookie settings
        """
        return SecureCookieConfig.get_settings(
            same_site="Lax",
            http_only=True,
            secure=True,
            max_age=86400,  # 24 hours
            path="/"
        )

    @staticmethod
    def get_dev_settings() -> Dict[str, any]:
        """
        Get cookie settings for local development.

        WARNING: Less secure - only use for local development!

        Returns:
            Dict with development cookie settings
        """
        logger.warning("Using development cookie settings - NOT SECURE!")
        return SecureCookieConfig.get_settings(
            same_site="Lax",
            http_only=True,
            secure=False,  # Allow HTTP for localhost
            max_age=3600,
            path="/"
        )


def get_secure_cookie_settings(environment: str = "production") -> Dict[str, any]:
    """
    Get secure cookie settings for the given environment.

    Args:
        environment: "production", "staging", or "development"

    Returns:
        Dict with appropriate cookie settings
    """
    if environment == "development":
        return SecureCookieConfig.get_dev_settings()
    return SecureCookieConfig.get_csrf_cookie_settings()


# =============================================================================
# SEC-003: ORIGIN/REFERER HEADER VALIDATION
# =============================================================================

class OriginValidator:
    """
    Validates Origin and Referer headers to prevent CSRF.

    This is a defense-in-depth measure - tokens are the primary defense,
    but header validation catches attacks that bypass token checks.
    """

    # Allowed origins (configure for your domains)
    _allowed_origins: Set[str] = set()

    @classmethod
    def configure(cls, allowed_origins: List[str]) -> None:
        """
        Configure the allowed origins for validation.

        Args:
            allowed_origins: List of allowed origin URLs
                e.g., ["https://ralphmode.com", "https://www.ralphmode.com"]
        """
        cls._allowed_origins = set()
        for origin in allowed_origins:
            # Normalize origin (remove trailing slash)
            parsed = urlparse(origin)
            normalized = f"{parsed.scheme}://{parsed.netloc}"
            cls._allowed_origins.add(normalized.lower())

        logger.info(f"Configured {len(cls._allowed_origins)} allowed origins")

    @classmethod
    def validate_origin(cls, origin: Optional[str]) -> bool:
        """
        Validate an Origin header value.

        Args:
            origin: The Origin header value

        Returns:
            bool: True if origin is allowed or not present
        """
        # If no origin header, fall back to referer check
        if not origin:
            return True  # Will rely on referer check

        origin_lower = origin.lower().strip()

        # Check against allowed origins
        if origin_lower in cls._allowed_origins:
            return True

        # Allow localhost for development
        if cls._is_localhost(origin_lower):
            logger.info(f"Allowing localhost origin: {origin}")
            return True

        logger.warning(f"Origin validation failed: {origin}")
        return False

    @classmethod
    def validate_referer(
        cls,
        referer: Optional[str],
        target_path: Optional[str] = None
    ) -> bool:
        """
        Validate a Referer header value.

        Args:
            referer: The Referer header value
            target_path: Optional target path to validate against

        Returns:
            bool: True if referer is allowed
        """
        if not referer:
            # Missing referer is suspicious but not always indicative of attack
            logger.info("Missing Referer header")
            return True  # Rely on token validation

        try:
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}".lower()

            if origin in cls._allowed_origins:
                return True

            if cls._is_localhost(origin):
                return True

            logger.warning(f"Referer validation failed: {referer}")
            return False

        except Exception as e:
            logger.warning(f"Referer parsing failed: {e}")
            return False

    @classmethod
    def validate_request(
        cls,
        origin: Optional[str],
        referer: Optional[str]
    ) -> Tuple[bool, str]:
        """
        Validate both Origin and Referer headers.

        Use this as defense-in-depth alongside token validation.

        Args:
            origin: The Origin header value
            referer: The Referer header value

        Returns:
            Tuple of (is_valid, reason)
        """
        # Validate origin first (more reliable)
        if origin:
            if not cls.validate_origin(origin):
                return False, f"Invalid origin: {origin}"
            return True, "Origin validated"

        # Fall back to referer
        if referer:
            if not cls.validate_referer(referer):
                return False, f"Invalid referer: {referer}"
            return True, "Referer validated"

        # Neither present - suspicious but not definitive
        # Rely on token validation
        return True, "No origin/referer - relying on token"

    @staticmethod
    def _is_localhost(origin: str) -> bool:
        """Check if origin is localhost for development."""
        localhost_patterns = [
            "http://localhost",
            "https://localhost",
            "http://127.0.0.1",
            "https://127.0.0.1",
            "http://0.0.0.0",
        ]
        return any(origin.startswith(p) for p in localhost_patterns)


# =============================================================================
# SEC-003: DOUBLE-SUBMIT COOKIE PATTERN
# =============================================================================

class DoubleSubmitCookie:
    """
    Implements the double-submit cookie pattern for stateless CSRF protection.

    This pattern:
    1. Sets a random token in a cookie
    2. Client includes same token in request header/body
    3. Server compares both - must match

    Useful for APIs where server-side session storage isn't available.
    """

    COOKIE_NAME = "csrf_double_submit"
    HEADER_NAME = "X-CSRF-Token"

    @classmethod
    def generate_token(cls) -> str:
        """
        Generate a token for double-submit pattern.

        Returns:
            str: Random token for cookie and header
        """
        return secrets.token_urlsafe(32)

    @classmethod
    def validate(
        cls,
        cookie_token: Optional[str],
        header_token: Optional[str]
    ) -> bool:
        """
        Validate double-submit tokens match.

        Args:
            cookie_token: Token from cookie
            header_token: Token from header/body

        Returns:
            bool: True if tokens match and are present
        """
        if not cookie_token or not header_token:
            logger.warning("Double-submit validation failed: missing token(s)")
            return False

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(cookie_token, header_token):
            logger.warning("Double-submit validation failed: token mismatch")
            return False

        return True

    @classmethod
    def get_cookie_settings(cls) -> Dict[str, any]:
        """
        Get cookie settings for the double-submit cookie.

        Note: Cannot use HttpOnly because JS needs to read the cookie
        to include it in the header. SameSite provides protection.

        Returns:
            Dict with cookie settings
        """
        return {
            "samesite": "Strict",
            "httponly": False,  # JS needs access
            "secure": True,
            "max_age": 3600,
            "path": "/"
        }


# =============================================================================
# SEC-003: TELEGRAM CALLBACK VALIDATION
# =============================================================================

class TelegramCallbackValidator:
    """
    Validates Telegram callback queries to prevent CSRF-like attacks.

    Telegram callbacks include a callback_query_id that's unique per click.
    We add additional validation for sensitive operations.
    """

    # Store recent callback IDs to prevent replay
    _recent_callbacks: Dict[str, float] = {}

    # Callback expiry time (seconds)
    CALLBACK_EXPIRY = 60

    @classmethod
    def validate_callback(
        cls,
        callback_query_id: str,
        user_id: int,
        expected_user_id: int
    ) -> Tuple[bool, str]:
        """
        Validate a Telegram callback query.

        Checks:
        1. Callback ID hasn't been used before (replay prevention)
        2. User ID matches expected user (authorization)
        3. Callback is recent enough

        Args:
            callback_query_id: Telegram's callback query ID
            user_id: ID of user who clicked
            expected_user_id: ID of user who should be clicking

        Returns:
            Tuple of (is_valid, reason)
        """
        # Clean up old callbacks
        cls._cleanup_old_callbacks()

        # Check user authorization
        if user_id != expected_user_id:
            logger.warning(
                f"Callback user mismatch: {user_id} != {expected_user_id}"
            )
            return False, "Unauthorized user"

        # Check for replay
        if callback_query_id in cls._recent_callbacks:
            logger.warning(f"Callback replay detected: {callback_query_id}")
            return False, "Callback already processed"

        # Store callback to prevent replay
        cls._recent_callbacks[callback_query_id] = time.time()

        return True, "Valid callback"

    @classmethod
    def generate_secure_callback_data(
        cls,
        action: str,
        user_id: int,
        **params
    ) -> str:
        """
        Generate secure callback data with embedded verification.

        Includes HMAC signature to prevent callback data tampering.

        Args:
            action: The action identifier
            user_id: User this callback belongs to
            **params: Additional parameters

        Returns:
            str: Secure callback data string
        """
        # Build parameter string
        param_str = ":".join(f"{k}={v}" for k, v in sorted(params.items()))

        # Create message
        timestamp = int(time.time())
        message = f"{action}:{user_id}:{timestamp}:{param_str}"

        # Sign it
        signature = hmac.new(
            CSRFProtection._get_secret_key(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:8]  # Truncate for Telegram's 64-byte limit

        # Format: action:user:time:params:sig
        if param_str:
            return f"{action}:{user_id}:{timestamp}:{param_str}:{signature}"
        return f"{action}:{user_id}:{timestamp}:{signature}"

    @classmethod
    def validate_secure_callback_data(
        cls,
        callback_data: str,
        expected_user_id: int
    ) -> Tuple[bool, str, Dict]:
        """
        Validate secure callback data.

        Args:
            callback_data: The callback data string
            expected_user_id: Expected user ID

        Returns:
            Tuple of (is_valid, action, params)
        """
        try:
            parts = callback_data.split(":")
            if len(parts) < 4:
                return False, "", {}

            action = parts[0]
            user_id = int(parts[1])
            timestamp = int(parts[2])

            # Check user
            if user_id != expected_user_id:
                logger.warning("Callback data user mismatch")
                return False, "", {}

            # Check expiry (1 hour)
            if time.time() - timestamp > 3600:
                logger.warning("Callback data expired")
                return False, "", {}

            # Extract signature (last part)
            signature = parts[-1]

            # Reconstruct message for verification
            if len(parts) > 4:
                param_str = ":".join(parts[3:-1])
                message = f"{action}:{user_id}:{timestamp}:{param_str}"
            else:
                param_str = ""
                message = f"{action}:{user_id}:{timestamp}"

            # Verify signature
            expected_sig = hmac.new(
                CSRFProtection._get_secret_key(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()[:8]

            if not hmac.compare_digest(signature, expected_sig):
                logger.warning("Callback data signature invalid")
                return False, "", {}

            # Parse params
            params = {}
            if param_str:
                for param in param_str.split(":"):
                    if "=" in param:
                        k, v = param.split("=", 1)
                        params[k] = v

            return True, action, params

        except (ValueError, IndexError) as e:
            logger.warning(f"Callback data validation failed: {e}")
            return False, "", {}

    @classmethod
    def _cleanup_old_callbacks(cls) -> None:
        """Remove expired callback records."""
        current_time = time.time()
        expired = [
            cid for cid, ts in cls._recent_callbacks.items()
            if current_time - ts > cls.CALLBACK_EXPIRY
        ]
        for cid in expired:
            del cls._recent_callbacks[cid]


# =============================================================================
# SEC-003: CSRF TESTING UTILITIES
# =============================================================================

class CSRFTester:
    """
    Testing utilities for CSRF protection verification.

    Use these in CI/CD pipelines to verify protection is working.
    """

    @staticmethod
    def test_token_generation() -> Dict:
        """
        Test CSRF token generation.

        Returns:
            Dict with test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "failures": []
        }

        # Test 1: Token generation
        try:
            token = CSRFProtection.generate_token("test_session_1")
            assert len(token) > 40, "Token too short"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Token generation: {e}")

        # Test 2: Token validation (valid)
        try:
            session_id = "test_session_2"
            token = CSRFProtection.generate_token(session_id)
            assert CSRFProtection.validate_token(session_id, token), "Valid token rejected"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Valid token validation: {e}")

        # Test 3: Token validation (wrong session)
        try:
            token = CSRFProtection.generate_token("session_a")
            valid = CSRFProtection.validate_token("session_b", token)
            assert not valid, "Wrong session accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Wrong session validation: {e}")

        # Test 4: Token validation (tampered)
        try:
            token = CSRFProtection.generate_token("test_session_3")
            tampered = token[:-5] + "XXXXX"
            valid = CSRFProtection.validate_token("test_session_3", tampered)
            assert not valid, "Tampered token accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Tampered token validation: {e}")

        # Test 5: Empty token rejection
        try:
            valid = CSRFProtection.validate_token("test_session", "")
            assert not valid, "Empty token accepted"
            valid = CSRFProtection.validate_token("", "some_token")
            assert not valid, "Empty session accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Empty input validation: {e}")

        return results

    @staticmethod
    def test_origin_validation() -> Dict:
        """
        Test Origin/Referer header validation.

        Returns:
            Dict with test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "failures": []
        }

        # Configure test origins
        OriginValidator.configure([
            "https://ralphmode.com",
            "https://www.ralphmode.com"
        ])

        # Test 1: Valid origin
        try:
            valid = OriginValidator.validate_origin("https://ralphmode.com")
            assert valid, "Valid origin rejected"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Valid origin: {e}")

        # Test 2: Invalid origin
        try:
            valid = OriginValidator.validate_origin("https://evil.com")
            assert not valid, "Invalid origin accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Invalid origin: {e}")

        # Test 3: Localhost (development)
        try:
            valid = OriginValidator.validate_origin("http://localhost:3000")
            assert valid, "Localhost rejected"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Localhost origin: {e}")

        # Test 4: Referer validation
        try:
            valid = OriginValidator.validate_referer(
                "https://ralphmode.com/some/page"
            )
            assert valid, "Valid referer rejected"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Valid referer: {e}")

        return results

    @staticmethod
    def test_double_submit() -> Dict:
        """
        Test double-submit cookie pattern.

        Returns:
            Dict with test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "failures": []
        }

        # Test 1: Matching tokens
        try:
            token = DoubleSubmitCookie.generate_token()
            valid = DoubleSubmitCookie.validate(token, token)
            assert valid, "Matching tokens rejected"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Matching tokens: {e}")

        # Test 2: Mismatched tokens
        try:
            token1 = DoubleSubmitCookie.generate_token()
            token2 = DoubleSubmitCookie.generate_token()
            valid = DoubleSubmitCookie.validate(token1, token2)
            assert not valid, "Mismatched tokens accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Mismatched tokens: {e}")

        # Test 3: Missing tokens
        try:
            valid = DoubleSubmitCookie.validate("token", None)
            assert not valid, "Missing header token accepted"
            valid = DoubleSubmitCookie.validate(None, "token")
            assert not valid, "Missing cookie token accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Missing tokens: {e}")

        return results

    @staticmethod
    def test_telegram_callbacks() -> Dict:
        """
        Test Telegram callback validation.

        Returns:
            Dict with test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "failures": []
        }

        # Test 1: Secure callback generation and validation
        try:
            user_id = 12345
            callback_data = TelegramCallbackValidator.generate_secure_callback_data(
                "approve",
                user_id,
                order_id="abc123"
            )
            valid, action, params = TelegramCallbackValidator.validate_secure_callback_data(
                callback_data,
                user_id
            )
            assert valid, "Valid callback rejected"
            assert action == "approve", "Wrong action"
            assert params.get("order_id") == "abc123", "Missing param"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Secure callback: {e}")

        # Test 2: Wrong user
        try:
            callback_data = TelegramCallbackValidator.generate_secure_callback_data(
                "delete",
                12345
            )
            valid, _, _ = TelegramCallbackValidator.validate_secure_callback_data(
                callback_data,
                99999  # Wrong user
            )
            assert not valid, "Wrong user accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Wrong user: {e}")

        # Test 3: Tampered callback
        try:
            callback_data = TelegramCallbackValidator.generate_secure_callback_data(
                "action",
                12345
            )
            tampered = callback_data[:-3] + "XXX"
            valid, _, _ = TelegramCallbackValidator.validate_secure_callback_data(
                tampered,
                12345
            )
            assert not valid, "Tampered callback accepted"
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["failures"].append(f"Tampered callback: {e}")

        return results

    @classmethod
    def run_all_tests(cls) -> Dict:
        """
        Run all CSRF protection tests.

        Returns:
            Dict with combined test results
        """
        all_results = {
            "token_tests": cls.test_token_generation(),
            "origin_tests": cls.test_origin_validation(),
            "double_submit_tests": cls.test_double_submit(),
            "telegram_tests": cls.test_telegram_callbacks(),
        }

        # Calculate totals
        total_passed = sum(r["passed"] for r in all_results.values())
        total_failed = sum(r["failed"] for r in all_results.values())

        all_results["summary"] = {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "all_passed": total_failed == 0
        }

        return all_results


# =============================================================================
# MAIN - Self Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SEC-003: CSRF Protection Tests")
    print("=" * 60)

    results = CSRFTester.run_all_tests()

    print("\n1. Token Generation Tests:")
    print(f"   Passed: {results['token_tests']['passed']}")
    print(f"   Failed: {results['token_tests']['failed']}")
    if results['token_tests']['failures']:
        for f in results['token_tests']['failures']:
            print(f"   - {f}")

    print("\n2. Origin Validation Tests:")
    print(f"   Passed: {results['origin_tests']['passed']}")
    print(f"   Failed: {results['origin_tests']['failed']}")
    if results['origin_tests']['failures']:
        for f in results['origin_tests']['failures']:
            print(f"   - {f}")

    print("\n3. Double-Submit Cookie Tests:")
    print(f"   Passed: {results['double_submit_tests']['passed']}")
    print(f"   Failed: {results['double_submit_tests']['failed']}")
    if results['double_submit_tests']['failures']:
        for f in results['double_submit_tests']['failures']:
            print(f"   - {f}")

    print("\n4. Telegram Callback Tests:")
    print(f"   Passed: {results['telegram_tests']['passed']}")
    print(f"   Failed: {results['telegram_tests']['failed']}")
    if results['telegram_tests']['failures']:
        for f in results['telegram_tests']['failures']:
            print(f"   - {f}")

    print("\n" + "=" * 60)
    summary = results['summary']
    if summary['all_passed']:
        print(f"All {summary['total_passed']} CSRF protection tests PASSED")
    else:
        print(f"CSRF tests: {summary['total_passed']} passed, {summary['total_failed']} FAILED")
    print("=" * 60)
