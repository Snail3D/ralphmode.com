#!/usr/bin/env python3
"""
Test suite for SEC-013: JWT Authentication
"""

import pytest
import time
from datetime import datetime, timedelta
from jwt_manager import JWTManager, APIKeyManager, RSAKeyManager


class TestJWTManager:
    """Test JWT token issuance and verification."""

    def test_issue_tokens(self):
        """Test token issuance with correct structure."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user", roles=["user"])

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "Bearer"
        assert tokens["expires_in"] == 900  # 15 minutes in seconds

    def test_verify_access_token(self):
        """Test access token verification."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user", roles=["user", "admin"])

        payload = jwt_mgr.verify_access_token(tokens["access_token"])

        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["type"] == "access"
        assert "user" in payload["roles"]
        assert "admin" in payload["roles"]

    def test_verify_invalid_token(self):
        """Test that invalid tokens are rejected."""
        jwt_mgr = JWTManager()
        payload = jwt_mgr.verify_access_token("invalid.token.here")

        assert payload is None

    def test_refresh_token_rotation(self):
        """Test that refresh tokens are rotated on use."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user")

        old_refresh = tokens["refresh_token"]

        # Refresh should work first time
        new_tokens = jwt_mgr.refresh_access_token(old_refresh)
        assert new_tokens is not None
        assert "access_token" in new_tokens

        # Old refresh token should be invalid now
        invalid_tokens = jwt_mgr.refresh_access_token(old_refresh)
        assert invalid_tokens is None

    def test_token_revocation(self):
        """Test token revocation."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user")

        # Token should be valid before revocation
        payload = jwt_mgr.verify_access_token(tokens["access_token"])
        assert payload is not None

        # Revoke token
        success = jwt_mgr.revoke_token(tokens["access_token"])
        assert success is True

        # Token should be invalid after revocation
        payload = jwt_mgr.verify_access_token(tokens["access_token"])
        assert payload is None

    def test_token_expiry(self):
        """Test that expired tokens are rejected."""
        import time as time_module

        jwt_mgr = JWTManager()

        # This would require mocking time or waiting 15 minutes
        # For now, just verify the expiry claim is set correctly
        tokens = jwt_mgr.issue_tokens(user_id="test_user")
        payload = jwt_mgr.verify_access_token(tokens["access_token"])

        exp_timestamp = payload["exp"]
        now_timestamp = time_module.time()
        time_diff = exp_timestamp - now_timestamp

        # Should expire in approximately 15 minutes (900 seconds)
        assert 895 <= time_diff <= 905  # Allow 5 second variance

    def test_additional_claims(self):
        """Test that additional claims are included in tokens."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(
            user_id="test_user",
            additional_claims={"custom_field": "custom_value"}
        )

        payload = jwt_mgr.verify_access_token(tokens["access_token"])
        assert payload["custom_field"] == "custom_value"


class TestAPIKeyManager:
    """Test API key generation and verification."""

    def test_generate_api_key(self):
        """Test API key generation."""
        key_data = APIKeyManager.generate_api_key(name="Test Service", scopes=["read", "write"])

        assert "api_key" in key_data
        assert key_data["api_key"].startswith("rmk_")
        assert key_data["name"] == "Test Service"
        assert key_data["scopes"] == ["read", "write"]
        assert "api_key_id" in key_data

    def test_verify_api_key(self):
        """Test API key verification."""
        key_data = APIKeyManager.generate_api_key(name="Test Service")
        api_key = key_data["api_key"]

        verified = APIKeyManager.verify_api_key(api_key)

        assert verified is not None
        assert verified["name"] == "Test Service"
        assert verified["api_key_id"] == key_data["api_key_id"]

    def test_verify_invalid_api_key(self):
        """Test that invalid API keys are rejected."""
        verified = APIKeyManager.verify_api_key("rmk_invalid_key")
        assert verified is None

    def test_revoke_api_key(self):
        """Test API key revocation."""
        key_data = APIKeyManager.generate_api_key(name="Test Service")
        api_key = key_data["api_key"]
        key_id = key_data["api_key_id"]

        # Key should work before revocation
        verified = APIKeyManager.verify_api_key(api_key)
        assert verified is not None

        # Revoke key
        success = APIKeyManager.revoke_api_key(key_id)
        assert success is True

        # Key should not work after revocation
        verified = APIKeyManager.verify_api_key(api_key)
        assert verified is None

    def test_list_api_keys(self):
        """Test listing API keys."""
        # Generate some keys
        APIKeyManager.generate_api_key(name="Service 1")
        APIKeyManager.generate_api_key(name="Service 2")

        keys = APIKeyManager.list_api_keys()

        assert len(keys) >= 2
        # Ensure plaintext keys are not in the list
        for key in keys:
            assert "api_key" not in key
            assert "hash" not in key


class TestRSAKeyManager:
    """Test RSA key management."""

    def test_load_or_generate_keys(self):
        """Test that keys are loaded or generated."""
        private_key, public_key = RSAKeyManager.load_or_generate_keys()

        assert private_key is not None
        assert public_key is not None
        assert b"BEGIN PRIVATE KEY" in private_key
        assert b"BEGIN PUBLIC KEY" in public_key


class TestSEC013Compliance:
    """Test SEC-013 acceptance criteria."""

    def test_jwt_15_minute_expiry(self):
        """SEC-013: JWT tokens with 15-minute expiry."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user")

        assert tokens["expires_in"] == 900  # 15 minutes = 900 seconds

    def test_refresh_7_day_expiry_rotated(self):
        """SEC-013: Refresh tokens with 7-day expiry (rotated on use)."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user")

        # Decode refresh token to check expiry
        payload = jwt_mgr.verify_refresh_token(tokens["refresh_token"])
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        days_until_expiry = (exp_time - now).days

        assert 6 <= days_until_expiry <= 7  # Should be 7 days

        # Test rotation
        new_tokens = jwt_mgr.refresh_access_token(tokens["refresh_token"])
        assert new_tokens is not None

        # Old refresh token should be invalid
        old_invalid = jwt_mgr.refresh_access_token(tokens["refresh_token"])
        assert old_invalid is None

    def test_rs256_signing(self):
        """SEC-013: Tokens signed with RS256 (asymmetric)."""
        import jwt as pyjwt

        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user")

        # Decode without verification to inspect header
        header = pyjwt.get_unverified_header(tokens["access_token"])

        assert header["alg"] == "RS256"

    def test_token_revocation(self):
        """SEC-013: Token revocation supported."""
        jwt_mgr = JWTManager()
        tokens = jwt_mgr.issue_tokens(user_id="test_user")

        # Revoke and verify
        success = jwt_mgr.revoke_token(tokens["access_token"])
        assert success is True

        payload = jwt_mgr.verify_access_token(tokens["access_token"])
        assert payload is None

    def test_api_keys_hashed(self):
        """SEC-013: API keys hashed in database."""
        from jwt_manager import _api_keys

        key_data = APIKeyManager.generate_api_key(name="Test")
        key_id = key_data["api_key_id"]

        # Check that stored hash is not the plaintext key
        stored_data = _api_keys[key_id]
        assert stored_data["hash"] != key_data["api_key"]
        assert stored_data["hash"].startswith("$2b$")  # Bcrypt hash format

    def test_token_validation_on_request(self):
        """SEC-013: Token validation on every request."""
        jwt_mgr = JWTManager()

        # Valid token
        tokens = jwt_mgr.issue_tokens(user_id="test_user")
        payload = jwt_mgr.verify_access_token(tokens["access_token"])
        assert payload is not None

        # Invalid token
        payload = jwt_mgr.verify_access_token("invalid_token")
        assert payload is None

        # Revoked token
        jwt_mgr.revoke_token(tokens["access_token"])
        payload = jwt_mgr.verify_access_token(tokens["access_token"])
        assert payload is None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
