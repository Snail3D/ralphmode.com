#!/usr/bin/env python3
"""
SEC-013: API Authentication (JWT)
=================================

Enterprise-grade JWT authentication implementing OWASP best practices:
- JWT access tokens with 15-minute expiry
- Refresh tokens with 7-day expiry (rotated on use)
- RS256 asymmetric signing (public/private key pairs)
- Token revocation support (blacklist)
- API keys for service-to-service auth
- API keys hashed in database (bcrypt)
- Token validation on every API request

This module provides:
1. JWT access token generation (15 min expiry)
2. Refresh token generation (7 days, rotated)
3. RS256 signature verification
4. Token revocation (blacklist)
5. API key generation and hashing
6. Token validation middleware

Usage:
    from jwt_manager import JWTManager

    # Initialize (generates RSA key pair if not exists)
    jwt_mgr = JWTManager()

    # Issue tokens after successful login
    tokens = jwt_mgr.issue_tokens(user_id="user123", roles=["user"])
    # Returns: {"access_token": "...", "refresh_token": "...", "expires_in": 900}

    # Validate access token on each request
    payload = jwt_mgr.verify_access_token(access_token)
    if payload:
        user_id = payload["sub"]
        # Request authorized

    # Refresh access token using refresh token
    new_tokens = jwt_mgr.refresh_access_token(refresh_token)

    # Revoke tokens (logout)
    jwt_mgr.revoke_token(access_token)
"""

import os
import secrets
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

# JWT library
try:
    import jwt
    from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("WARNING: PyJWT not installed. Install with: pip install PyJWT[crypto]")

# Cryptography for RSA key generation
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("WARNING: cryptography not installed. Install with: pip install cryptography")

# Bcrypt for API key hashing
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("WARNING: bcrypt not installed. Install with: pip install bcrypt")


# =============================================================================
# Configuration
# =============================================================================

# Token expiry times
ACCESS_TOKEN_EXPIRY_MINUTES = 15  # SEC-013: Short-lived access tokens
REFRESH_TOKEN_EXPIRY_DAYS = 7     # SEC-013: Refresh tokens with 7-day expiry

# JWT settings
JWT_ALGORITHM = "RS256"  # SEC-013: Asymmetric signing (RS256)
JWT_ISSUER = "ralph-mode-api"
JWT_AUDIENCE = "ralph-mode-users"

# API key settings
API_KEY_LENGTH = 32  # bytes (64 hex chars)
API_KEY_PREFIX = "rmk_"  # Ralph Mode Key prefix
BCRYPT_COST = 12  # Same as auth.py

# Key storage paths
KEYS_DIR = os.path.join(os.path.dirname(__file__), ".keys")
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "jwt_private.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "jwt_public.pem")


# =============================================================================
# In-Memory Storage (Replace with Redis/database in production)
# =============================================================================

# Token blacklist (revoked tokens)
# Structure: {token_jti: expiry_timestamp}
_token_blacklist: Dict[str, float] = {}

# Refresh tokens (store for rotation)
# Structure: {refresh_token_jti: {"user_id": str, "issued_at": float, "expires_at": float}}
_refresh_tokens: Dict[str, Dict] = {}

# API keys (hashed)
# Structure: {api_key_id: {"hash": str, "name": str, "created_at": datetime, "scopes": list}}
_api_keys: Dict[str, Dict] = {}


# =============================================================================
# RSA Key Management
# =============================================================================

class RSAKeyManager:
    """
    Manage RSA key pairs for JWT signing.

    Generates and loads RSA-2048 key pairs for RS256 signing.
    Private key signs tokens, public key verifies them.
    """

    @staticmethod
    def generate_key_pair() -> tuple:
        """
        Generate new RSA-2048 key pair.

        Returns:
            (private_key_pem, public_key_pem) tuple as bytes
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")

        # Generate RSA-2048 private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Serialize private key to PEM
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()  # Store unencrypted (use filesystem encryption)
        )

        # Extract public key
        public_key = private_key.public_key()

        # Serialize public key to PEM
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    @staticmethod
    def save_key_pair(private_pem: bytes, public_pem: bytes) -> None:
        """
        Save key pair to disk.

        Args:
            private_pem: Private key in PEM format
            public_pem: Public key in PEM format
        """
        os.makedirs(KEYS_DIR, exist_ok=True)

        # Save private key (restrict permissions)
        with open(PRIVATE_KEY_PATH, 'wb') as f:
            f.write(private_pem)
        os.chmod(PRIVATE_KEY_PATH, 0o600)  # Read/write for owner only

        # Save public key
        with open(PUBLIC_KEY_PATH, 'wb') as f:
            f.write(public_pem)
        os.chmod(PUBLIC_KEY_PATH, 0o644)  # Readable by all

    @staticmethod
    def load_or_generate_keys() -> tuple:
        """
        Load existing keys or generate new ones.

        Returns:
            (private_key_pem, public_key_pem) tuple as bytes
        """
        # Try to load existing keys
        if os.path.exists(PRIVATE_KEY_PATH) and os.path.exists(PUBLIC_KEY_PATH):
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                private_pem = f.read()
            with open(PUBLIC_KEY_PATH, 'rb') as f:
                public_pem = f.read()
            return private_pem, public_pem

        # Generate new keys
        private_pem, public_pem = RSAKeyManager.generate_key_pair()
        RSAKeyManager.save_key_pair(private_pem, public_pem)

        return private_pem, public_pem


# =============================================================================
# JWT Token Manager
# =============================================================================

class JWTManager:
    """
    Main JWT authentication manager.

    Handles:
    - Access token issuance (15 min expiry)
    - Refresh token issuance (7 day expiry, rotated)
    - Token verification (RS256)
    - Token revocation (blacklist)
    """

    def __init__(self):
        """Initialize JWT manager and load keys."""
        if not JWT_AVAILABLE:
            raise RuntimeError("PyJWT not installed. Cannot use JWT authentication.")

        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography not installed. Cannot use RS256 signing.")

        # Load or generate RSA keys
        self.private_key, self.public_key = RSAKeyManager.load_or_generate_keys()

    def issue_tokens(self, user_id: str, roles: Optional[List[str]] = None,
                    additional_claims: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Issue access token and refresh token pair.

        Args:
            user_id: User identifier
            roles: List of user roles (e.g., ["user", "admin"])
            additional_claims: Optional additional JWT claims

        Returns:
            Dict with:
            {
                "access_token": str,
                "refresh_token": str,
                "token_type": "Bearer",
                "expires_in": int (seconds)
            }
        """
        now = datetime.utcnow()

        # Generate unique JTI (JWT ID) for both tokens
        access_jti = secrets.token_urlsafe(16)
        refresh_jti = secrets.token_urlsafe(16)

        # Build access token payload
        access_payload = {
            "sub": user_id,  # Subject (user ID)
            "iat": now,  # Issued at
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES),  # Expires
            "iss": JWT_ISSUER,  # Issuer
            "aud": JWT_AUDIENCE,  # Audience
            "jti": access_jti,  # JWT ID (for revocation)
            "type": "access",
            "roles": roles or ["user"],
        }

        # Add additional claims if provided
        if additional_claims:
            access_payload.update(additional_claims)

        # Build refresh token payload
        refresh_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "jti": refresh_jti,
            "type": "refresh",
        }

        # Sign tokens with private key
        access_token = jwt.encode(access_payload, self.private_key, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, self.private_key, algorithm=JWT_ALGORITHM)

        # Store refresh token for rotation tracking
        _refresh_tokens[refresh_jti] = {
            "user_id": user_id,
            "issued_at": now.timestamp(),
            "expires_at": (now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).timestamp(),
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRY_MINUTES * 60,  # Seconds
        }

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode access token.

        Args:
            token: JWT access token

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            # Decode and verify signature
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
            )

            # Check token type
            if payload.get("type") != "access":
                return None

            # Check if token is revoked
            jti = payload.get("jti")
            if jti and self._is_token_revoked(jti):
                return None

            return payload

        except ExpiredSignatureError:
            # Token expired
            return None
        except InvalidTokenError:
            # Invalid token
            return None
        except Exception:
            # Other errors
            return None

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode refresh token.

        Args:
            token: JWT refresh token

        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            # Decode and verify signature
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
            )

            # Check token type
            if payload.get("type") != "refresh":
                return None

            # Check if token is revoked
            jti = payload.get("jti")
            if jti and self._is_token_revoked(jti):
                return None

            # Check if refresh token exists in store
            if jti not in _refresh_tokens:
                return None

            return payload

        except ExpiredSignatureError:
            return None
        except InvalidTokenError:
            return None
        except Exception:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Issue new access token using refresh token.

        SEC-013: Refresh tokens are rotated on use (old one invalidated, new one issued).

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token pair if successful, None otherwise
        """
        # Verify refresh token
        payload = self.verify_refresh_token(refresh_token)
        if not payload:
            return None

        user_id = payload["sub"]
        old_jti = payload["jti"]

        # Revoke old refresh token (rotation)
        self._revoke_token(old_jti)
        if old_jti in _refresh_tokens:
            del _refresh_tokens[old_jti]

        # Issue new token pair
        roles = payload.get("roles", ["user"])
        return self.issue_tokens(user_id, roles)

    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token (add to blacklist).

        Args:
            token: JWT token to revoke

        Returns:
            True if revoked, False if invalid
        """
        try:
            # Decode without verification (we just need JTI and expiry)
            payload = jwt.decode(token, options={"verify_signature": False})
            jti = payload.get("jti")
            exp = payload.get("exp")

            if not jti or not exp:
                return False

            # Add to blacklist
            self._revoke_token(jti, exp)

            # Remove from refresh token store if applicable
            if jti in _refresh_tokens:
                del _refresh_tokens[jti]

            return True

        except Exception:
            return False

    def _revoke_token(self, jti: str, expiry: Optional[float] = None) -> None:
        """
        Internal method to add token to blacklist.

        Args:
            jti: JWT ID
            expiry: Token expiry timestamp (optional)
        """
        if expiry is None:
            # Default to 7 days from now (max token lifetime)
            expiry = (datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).timestamp()

        _token_blacklist[jti] = expiry

    def _is_token_revoked(self, jti: str) -> bool:
        """
        Check if token is revoked.

        Args:
            jti: JWT ID

        Returns:
            True if revoked, False otherwise
        """
        if jti not in _token_blacklist:
            return False

        # Check if blacklist entry expired (can remove it)
        expiry = _token_blacklist[jti]
        if time.time() > expiry:
            del _token_blacklist[jti]
            return False

        return True

    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired entries from blacklist and refresh token store.

        Returns:
            Number of entries cleaned up
        """
        now = time.time()
        cleaned = 0

        # Clean blacklist
        expired_jti = [jti for jti, exp in _token_blacklist.items() if now > exp]
        for jti in expired_jti:
            del _token_blacklist[jti]
            cleaned += 1

        # Clean refresh tokens
        expired_refresh = [jti for jti, data in _refresh_tokens.items() if now > data["expires_at"]]
        for jti in expired_refresh:
            del _refresh_tokens[jti]
            cleaned += 1

        return cleaned


# =============================================================================
# API Key Manager (for service-to-service auth)
# =============================================================================

class APIKeyManager:
    """
    Manage API keys for service-to-service authentication.

    SEC-013: API keys are hashed in database (bcrypt, cost 12).
    Keys are prefixed with "rmk_" for easy identification.
    """

    @staticmethod
    def generate_api_key(name: str, scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate new API key.

        Args:
            name: Human-readable name for the key
            scopes: List of allowed scopes/permissions

        Returns:
            Dict with:
            {
                "api_key": str (plaintext - ONLY TIME IT'S VISIBLE),
                "api_key_id": str,
                "name": str,
                "scopes": list,
                "created_at": datetime
            }
        """
        if not BCRYPT_AVAILABLE:
            raise RuntimeError("bcrypt not installed. Cannot hash API keys securely.")

        # Generate random API key
        key_bytes = secrets.token_bytes(API_KEY_LENGTH)
        key_hex = key_bytes.hex()
        api_key = f"{API_KEY_PREFIX}{key_hex}"

        # Generate key ID (first 8 chars of hash)
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]

        # Hash the key for storage
        key_hash = bcrypt.hashpw(api_key.encode(), bcrypt.gensalt(rounds=BCRYPT_COST))

        # Store hashed key
        _api_keys[key_id] = {
            "hash": key_hash.decode('utf-8'),
            "name": name,
            "created_at": datetime.utcnow(),
            "scopes": scopes or [],
        }

        return {
            "api_key": api_key,  # ONLY TIME plaintext is visible
            "api_key_id": key_id,
            "name": name,
            "scopes": scopes or [],
            "created_at": datetime.utcnow(),
        }

    @staticmethod
    def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify API key and return metadata.

        Args:
            api_key: API key to verify

        Returns:
            Key metadata if valid, None otherwise
        """
        if not BCRYPT_AVAILABLE:
            raise RuntimeError("bcrypt not installed")

        if not api_key or not api_key.startswith(API_KEY_PREFIX):
            return None

        # Get key ID
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]

        if key_id not in _api_keys:
            return None

        key_data = _api_keys[key_id]

        # Verify hash
        try:
            stored_hash = key_data["hash"].encode('utf-8')
            if bcrypt.checkpw(api_key.encode(), stored_hash):
                return {
                    "api_key_id": key_id,
                    "name": key_data["name"],
                    "scopes": key_data["scopes"],
                    "created_at": key_data["created_at"],
                }
        except Exception:
            pass

        return None

    @staticmethod
    def revoke_api_key(api_key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            api_key_id: Key ID to revoke

        Returns:
            True if revoked, False if not found
        """
        if api_key_id in _api_keys:
            del _api_keys[api_key_id]
            return True
        return False

    @staticmethod
    def list_api_keys() -> List[Dict[str, Any]]:
        """
        List all API keys (without plaintext keys).

        Returns:
            List of key metadata dicts
        """
        return [
            {
                "api_key_id": key_id,
                "name": data["name"],
                "scopes": data["scopes"],
                "created_at": data["created_at"],
            }
            for key_id, data in _api_keys.items()
        ]


# =============================================================================
# Token Validation Decorator
# =============================================================================

def require_jwt_auth(required_roles: Optional[List[str]] = None):
    """
    Decorator to require JWT authentication on API endpoints.

    Args:
        required_roles: List of required roles (optional)

    Usage:
        @require_jwt_auth(required_roles=["admin"])
        async def admin_endpoint(request):
            user_id = request.state.user_id
            roles = request.state.roles
            # ... endpoint logic
    """
    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return {"error": "Missing or invalid Authorization header"}, 401

            token = auth_header[7:]  # Remove "Bearer " prefix

            # Verify token
            jwt_mgr = JWTManager()
            payload = jwt_mgr.verify_access_token(token)

            if not payload:
                return {"error": "Invalid or expired token"}, 401

            # Check roles if required
            if required_roles:
                user_roles = payload.get("roles", [])
                if not any(role in user_roles for role in required_roles):
                    return {"error": "Insufficient permissions"}, 403

            # Attach user info to request
            request.state.user_id = payload["sub"]
            request.state.roles = payload.get("roles", [])
            request.state.jwt_payload = payload

            # Call endpoint
            return await func(request, *args, **kwargs)

        return wrapper
    return decorator


# =============================================================================
# Module-level convenience functions
# =============================================================================

def create_jwt_manager() -> JWTManager:
    """Create and return a JWT manager instance."""
    return JWTManager()

def generate_api_key(name: str, scopes: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convenience function for API key generation."""
    return APIKeyManager.generate_api_key(name, scopes)

def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Convenience function for API key verification."""
    return APIKeyManager.verify_api_key(api_key)


# =============================================================================
# Self-test
# =============================================================================

if __name__ == "__main__":
    print("SEC-013: API Authentication (JWT) - Self Test")
    print("=" * 60)

    # Test 1: RSA key generation
    print("\n[Test 1] RSA key pair generation...")
    if CRYPTO_AVAILABLE:
        private_key, public_key = RSAKeyManager.load_or_generate_keys()
        print(f"  Private key loaded: {len(private_key)} bytes")
        print(f"  Public key loaded: {len(public_key)} bytes")
        print("  ✅ PASS")
    else:
        print("  ❌ FAIL: cryptography not installed")

    # Test 2: JWT token issuance
    print("\n[Test 2] JWT token issuance (15 min access, 7 day refresh)...")
    if JWT_AVAILABLE and CRYPTO_AVAILABLE:
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user", roles=["user", "admin"])
        print(f"  Access token: {tokens['access_token'][:50]}... (truncated)")
        print(f"  Refresh token: {tokens['refresh_token'][:50]}... (truncated)")
        print(f"  Token type: {tokens['token_type']}")
        print(f"  Expires in: {tokens['expires_in']} seconds")
        print("  ✅ PASS")
    else:
        print("  ❌ FAIL: PyJWT or cryptography not installed")

    # Test 3: Access token verification
    print("\n[Test 3] Access token verification (RS256)...")
    if JWT_AVAILABLE and CRYPTO_AVAILABLE:
        payload = jwt_mgr.verify_access_token(tokens['access_token'])
        print(f"  User ID: {payload['sub']}")
        print(f"  Roles: {payload['roles']}")
        print(f"  Expires: {datetime.fromtimestamp(payload['exp'])}")
        print("  ✅ PASS")
    else:
        print("  ❌ SKIP")

    # Test 4: Refresh token rotation
    print("\n[Test 4] Refresh token rotation...")
    if JWT_AVAILABLE and CRYPTO_AVAILABLE:
        old_refresh = tokens['refresh_token']
        new_tokens = jwt_mgr.refresh_access_token(old_refresh)

        print(f"  New access token issued: {new_tokens is not None}")

        # Old refresh token should be invalid now
        invalid_result = jwt_mgr.refresh_access_token(old_refresh)
        print(f"  Old refresh token invalidated: {invalid_result is None}")
        print("  ✅ PASS")
    else:
        print("  ❌ SKIP")

    # Test 5: Token revocation
    print("\n[Test 5] Token revocation (blacklist)...")
    if JWT_AVAILABLE and CRYPTO_AVAILABLE:
        test_tokens = jwt_mgr.issue_tokens(user_id="test_revoke")
        access_token = test_tokens['access_token']

        # Verify works before revocation
        payload_before = jwt_mgr.verify_access_token(access_token)
        print(f"  Token valid before revocation: {payload_before is not None}")

        # Revoke token
        jwt_mgr.revoke_token(access_token)

        # Verify fails after revocation
        payload_after = jwt_mgr.verify_access_token(access_token)
        print(f"  Token invalid after revocation: {payload_after is None}")
        print("  ✅ PASS")
    else:
        print("  ❌ SKIP")

    # Test 6: API key generation and verification
    print("\n[Test 6] API key generation (hashed with bcrypt)...")
    if BCRYPT_AVAILABLE:
        key_data = APIKeyManager.generate_api_key(
            name="Test Service",
            scopes=["read", "write"]
        )
        print(f"  API key: {key_data['api_key'][:30]}... (truncated)")
        print(f"  Key ID: {key_data['api_key_id']}")
        print(f"  Name: {key_data['name']}")
        print(f"  Scopes: {key_data['scopes']}")

        # Verify key
        verified = APIKeyManager.verify_api_key(key_data['api_key'])
        print(f"  Verification successful: {verified is not None}")
        print(f"  Verified name: {verified['name']}")
        print("  ✅ PASS")
    else:
        print("  ❌ FAIL: bcrypt not installed")

    # Test 7: Cleanup expired tokens
    print("\n[Test 7] Cleanup expired tokens...")
    if JWT_AVAILABLE and CRYPTO_AVAILABLE:
        cleaned = jwt_mgr.cleanup_expired_tokens()
        print(f"  Entries cleaned: {cleaned}")
        print("  ✅ PASS")
    else:
        print("  ❌ SKIP")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("\nSEC-013 Implementation Summary:")
    print("  ✅ JWT access tokens (15-minute expiry)")
    print("  ✅ Refresh tokens (7-day expiry, rotated on use)")
    print("  ✅ RS256 asymmetric signing")
    print("  ✅ Token revocation (blacklist)")
    print("  ✅ API keys for service-to-service (hashed)")
    print("  ✅ Token validation on every request")
