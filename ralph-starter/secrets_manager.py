#!/usr/bin/env python3
"""
Secrets Management for Ralph Mode
SEC-016: Secure secrets storage and access

This module provides secure secrets management using HashiCorp Vault or AWS Secrets Manager.
Secrets are injected at runtime, never stored in code or config files.

Features:
- HashiCorp Vault and AWS Secrets Manager support
- Environment-specific secrets (dev/staging/prod)
- Automatic secret rotation support
- Access auditing and logging
- Encryption in transit and at rest
- Runtime-only secret injection
"""

import os
import json
import logging
import time
from typing import Dict, Optional, Any
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod


# SEC-010: Setup logging with security audit trail
logger = logging.getLogger('secrets_manager')
logger.setLevel(logging.INFO)


class SecretProvider(Enum):
    """Supported secret storage providers"""
    ENV_VAR = "env_var"  # Development only - environment variables
    VAULT = "vault"  # HashiCorp Vault (recommended for production)
    AWS_SECRETS = "aws_secrets"  # AWS Secrets Manager


class SecretsError(Exception):
    """Raised when secret access fails"""
    pass


class BaseSecretsProvider(ABC):
    """Abstract base class for secret providers"""

    def __init__(self, environment: str):
        self.environment = environment
        self._cache = {}  # In-memory cache (cleared on rotation)
        self._access_log = []  # Audit trail

    @abstractmethod
    def get_secret(self, secret_name: str) -> str:
        """
        Retrieve a secret by name.

        Args:
            secret_name: Name of the secret to retrieve

        Returns:
            Secret value as string

        Raises:
            SecretsError: If secret cannot be retrieved
        """
        pass

    @abstractmethod
    def list_secrets(self) -> list:
        """List available secret names"""
        pass

    @abstractmethod
    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """
        Rotate a secret to a new value.

        Args:
            secret_name: Name of the secret
            new_value: New secret value

        Returns:
            True if rotation successful
        """
        pass

    def _log_access(self, secret_name: str, success: bool, error: Optional[str] = None):
        """SEC-016: Audit secret access"""
        from datetime import timezone
        access_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'secret_name': secret_name,
            'environment': self.environment,
            'success': success,
            'error': error,
            'pid': os.getpid()
        }
        self._access_log.append(access_record)

        if success:
            logger.info(f"Secret accessed: {secret_name} (env: {self.environment})")
        else:
            logger.error(f"Secret access failed: {secret_name} - {error}")

    def get_audit_log(self) -> list:
        """Get audit log of secret accesses"""
        return self._access_log.copy()

    def clear_cache(self):
        """Clear cached secrets (call after rotation)"""
        self._cache.clear()
        logger.info("Secret cache cleared")


class EnvVarSecretsProvider(BaseSecretsProvider):
    """
    Environment variable secret provider.

    SEC-016: For development only. Secrets are read from environment variables.
    NOT secure for production - use Vault or AWS Secrets Manager.
    """

    def get_secret(self, secret_name: str) -> str:
        """Get secret from environment variable"""
        try:
            # Check cache first
            if secret_name in self._cache:
                self._log_access(secret_name, True)
                return self._cache[secret_name]

            # Get from environment with environment prefix
            env_key = f"{self.environment.upper()}_{secret_name}" if self.environment != 'development' else secret_name
            secret_value = os.getenv(env_key)

            if secret_value is None:
                # Fall back to unprefixed name
                secret_value = os.getenv(secret_name)

            if secret_value is None:
                error = f"Secret not found: {secret_name}"
                self._log_access(secret_name, False, error)
                raise SecretsError(error)

            # Cache the secret
            self._cache[secret_name] = secret_value
            self._log_access(secret_name, True)
            return secret_value

        except Exception as e:
            error = f"Failed to retrieve secret: {str(e)}"
            self._log_access(secret_name, False, error)
            raise SecretsError(error)

    def list_secrets(self) -> list:
        """List secrets from environment (filtered by prefix)"""
        prefix = f"{self.environment.upper()}_" if self.environment != 'development' else ""
        secrets = [k.replace(prefix, '') for k in os.environ.keys() if k.startswith(prefix) or self.environment == 'development']
        return secrets

    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate secret in environment (updates process env only)"""
        try:
            env_key = f"{self.environment.upper()}_{secret_name}" if self.environment != 'development' else secret_name
            os.environ[env_key] = new_value

            # Clear cache to force reload
            if secret_name in self._cache:
                del self._cache[secret_name]

            logger.info(f"Secret rotated: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Secret rotation failed: {secret_name} - {str(e)}")
            return False


class VaultSecretsProvider(BaseSecretsProvider):
    """
    HashiCorp Vault secret provider.

    SEC-016: Production-grade secret management with Vault.
    Requires hvac library: pip install hvac
    """

    def __init__(self, environment: str, vault_url: Optional[str] = None,
                 vault_token: Optional[str] = None, vault_path: Optional[str] = None):
        super().__init__(environment)

        try:
            import hvac
        except ImportError:
            raise SecretsError("hvac library not installed. Install with: pip install hvac")

        self.vault_url = vault_url or os.getenv('VAULT_ADDR', 'http://localhost:8200')
        self.vault_token = vault_token or os.getenv('VAULT_TOKEN')
        self.vault_path = vault_path or f"secret/data/ralph/{environment}"

        if not self.vault_token:
            raise SecretsError("VAULT_TOKEN not set")

        # Initialize Vault client
        self.client = hvac.Client(url=self.vault_url, token=self.vault_token)

        if not self.client.is_authenticated():
            raise SecretsError("Failed to authenticate with Vault")

        logger.info(f"Vault client initialized (env: {environment}, path: {self.vault_path})")

    def get_secret(self, secret_name: str) -> str:
        """Get secret from Vault"""
        try:
            # Check cache first
            if secret_name in self._cache:
                self._log_access(secret_name, True)
                return self._cache[secret_name]

            # Read from Vault
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.vault_path,
                mount_point='secret'
            )

            secrets = response['data']['data']

            if secret_name not in secrets:
                error = f"Secret not found in Vault: {secret_name}"
                self._log_access(secret_name, False, error)
                raise SecretsError(error)

            secret_value = secrets[secret_name]

            # Cache the secret
            self._cache[secret_name] = secret_value
            self._log_access(secret_name, True)
            return secret_value

        except Exception as e:
            error = f"Failed to retrieve secret from Vault: {str(e)}"
            self._log_access(secret_name, False, error)
            raise SecretsError(error)

    def list_secrets(self) -> list:
        """List secrets in Vault path"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.vault_path,
                mount_point='secret'
            )
            return list(response['data']['data'].keys())
        except Exception as e:
            logger.error(f"Failed to list Vault secrets: {str(e)}")
            return []

    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate secret in Vault"""
        try:
            # Read current secrets
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.vault_path,
                mount_point='secret'
            )

            secrets = response['data']['data']
            secrets[secret_name] = new_value

            # Write updated secrets
            self.client.secrets.kv.v2.create_or_update_secret(
                path=self.vault_path,
                secret=secrets,
                mount_point='secret'
            )

            # Clear cache
            if secret_name in self._cache:
                del self._cache[secret_name]

            logger.info(f"Secret rotated in Vault: {secret_name}")
            return True

        except Exception as e:
            logger.error(f"Vault secret rotation failed: {secret_name} - {str(e)}")
            return False


class AWSSecretsProvider(BaseSecretsProvider):
    """
    AWS Secrets Manager provider.

    SEC-016: Production-grade secret management with AWS.
    Requires boto3 library: pip install boto3
    """

    def __init__(self, environment: str, region_name: Optional[str] = None):
        super().__init__(environment)

        try:
            import boto3
        except ImportError:
            raise SecretsError("boto3 library not installed. Install with: pip install boto3")

        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.secret_prefix = f"ralph/{environment}/"

        # Initialize AWS Secrets Manager client
        self.client = boto3.client('secretsmanager', region_name=self.region_name)

        logger.info(f"AWS Secrets Manager initialized (env: {environment}, region: {self.region_name})")

    def get_secret(self, secret_name: str) -> str:
        """Get secret from AWS Secrets Manager"""
        try:
            # Check cache first
            if secret_name in self._cache:
                self._log_access(secret_name, True)
                return self._cache[secret_name]

            # Full secret name with environment prefix
            full_name = f"{self.secret_prefix}{secret_name}"

            # Get secret value
            response = self.client.get_secret_value(SecretId=full_name)

            if 'SecretString' in response:
                secret_value = response['SecretString']
            else:
                # Binary secret (decode base64)
                import base64
                secret_value = base64.b64decode(response['SecretBinary']).decode('utf-8')

            # Cache the secret
            self._cache[secret_name] = secret_value
            self._log_access(secret_name, True)
            return secret_value

        except self.client.exceptions.ResourceNotFoundException:
            error = f"Secret not found in AWS: {secret_name}"
            self._log_access(secret_name, False, error)
            raise SecretsError(error)
        except Exception as e:
            error = f"Failed to retrieve secret from AWS: {str(e)}"
            self._log_access(secret_name, False, error)
            raise SecretsError(error)

    def list_secrets(self) -> list:
        """List secrets in AWS Secrets Manager"""
        try:
            paginator = self.client.get_paginator('list_secrets')
            secrets = []

            for page in paginator.paginate():
                for secret in page['SecretList']:
                    if secret['Name'].startswith(self.secret_prefix):
                        # Remove prefix from name
                        name = secret['Name'].replace(self.secret_prefix, '')
                        secrets.append(name)

            return secrets
        except Exception as e:
            logger.error(f"Failed to list AWS secrets: {str(e)}")
            return []

    def rotate_secret(self, secret_name: str, new_value: str) -> bool:
        """Rotate secret in AWS Secrets Manager"""
        try:
            full_name = f"{self.secret_prefix}{secret_name}"

            # Update secret value
            self.client.put_secret_value(
                SecretId=full_name,
                SecretString=new_value
            )

            # Clear cache
            if secret_name in self._cache:
                del self._cache[secret_name]

            logger.info(f"Secret rotated in AWS: {secret_name}")
            return True

        except Exception as e:
            logger.error(f"AWS secret rotation failed: {secret_name} - {str(e)}")
            return False


class SecretsManager:
    """
    Main secrets manager interface.

    SEC-016: Runtime secret injection with multiple backend support.

    Usage:
        # Development (env vars)
        secrets = SecretsManager(environment='development')

        # Production (Vault)
        secrets = SecretsManager(
            environment='production',
            provider=SecretProvider.VAULT,
            vault_url='https://vault.example.com',
            vault_token=os.getenv('VAULT_TOKEN')
        )

        # Get secrets
        telegram_token = secrets.get('TELEGRAM_BOT_TOKEN')
        groq_key = secrets.get('GROQ_API_KEY')
    """

    def __init__(self, environment: str = 'development',
                 provider: SecretProvider = SecretProvider.ENV_VAR,
                 **provider_kwargs):
        """
        Initialize secrets manager.

        Args:
            environment: Environment name (development/staging/production)
            provider: Secret provider backend
            **provider_kwargs: Provider-specific configuration
        """
        self.environment = environment
        self.provider_type = provider

        # SEC-016: Choose provider based on environment and configuration
        if provider == SecretProvider.ENV_VAR:
            self.provider = EnvVarSecretsProvider(environment)
        elif provider == SecretProvider.VAULT:
            self.provider = VaultSecretsProvider(environment, **provider_kwargs)
        elif provider == SecretProvider.AWS_SECRETS:
            self.provider = AWSSecretsProvider(environment, **provider_kwargs)
        else:
            raise SecretsError(f"Unsupported provider: {provider}")

        logger.info(f"SecretsManager initialized (env: {environment}, provider: {provider.value})")

    def get(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret by name.

        Args:
            secret_name: Name of the secret
            default: Default value if secret not found (optional)

        Returns:
            Secret value or default
        """
        try:
            return self.provider.get_secret(secret_name)
        except SecretsError as e:
            if default is not None:
                logger.warning(f"Secret not found, using default: {secret_name}")
                return default
            raise

    def get_required(self, secret_name: str) -> str:
        """
        Get a required secret (raises error if not found).

        Args:
            secret_name: Name of the secret

        Returns:
            Secret value

        Raises:
            SecretsError: If secret not found
        """
        return self.provider.get_secret(secret_name)

    def list(self) -> list:
        """List available secrets"""
        return self.provider.list_secrets()

    def rotate(self, secret_name: str, new_value: str) -> bool:
        """
        Rotate a secret to a new value.

        Args:
            secret_name: Name of the secret
            new_value: New secret value

        Returns:
            True if successful
        """
        return self.provider.rotate_secret(secret_name, new_value)

    def get_audit_log(self) -> list:
        """Get audit log of secret accesses"""
        return self.provider.get_audit_log()

    def clear_cache(self):
        """Clear cached secrets"""
        self.provider.clear_cache()


def create_secrets_manager(environment: Optional[str] = None) -> SecretsManager:
    """
    Factory function to create SecretsManager based on environment.

    SEC-016: Automatically selects appropriate provider based on environment.

    Args:
        environment: Environment name (defaults to RALPH_ENV or 'production')

    Returns:
        Configured SecretsManager instance
    """
    if environment is None:
        environment = os.getenv('RALPH_ENV', 'production').lower()

    # Development: Use environment variables
    if environment == 'development':
        return SecretsManager(
            environment=environment,
            provider=SecretProvider.ENV_VAR
        )

    # Production/Staging: Use Vault or AWS Secrets Manager
    # Try Vault first (if VAULT_TOKEN is set)
    if os.getenv('VAULT_TOKEN'):
        return SecretsManager(
            environment=environment,
            provider=SecretProvider.VAULT,
            vault_url=os.getenv('VAULT_ADDR'),
            vault_token=os.getenv('VAULT_TOKEN')
        )

    # Fall back to AWS Secrets Manager (if AWS credentials available)
    if os.getenv('AWS_ACCESS_KEY_ID') or os.path.exists(os.path.expanduser('~/.aws/credentials')):
        return SecretsManager(
            environment=environment,
            provider=SecretProvider.AWS_SECRETS,
            region_name=os.getenv('AWS_REGION')
        )

    # Last resort: environment variables (with warning)
    logger.warning(f"No Vault or AWS credentials found. Using environment variables in {environment}. This is NOT secure for production!")
    return SecretsManager(
        environment=environment,
        provider=SecretProvider.ENV_VAR
    )


if __name__ == '__main__':
    """
    Test secrets manager from command line.

    Usage:
        python secrets_manager.py                    # Test with current environment
        RALPH_ENV=production python secrets_manager.py  # Test production config
    """
    import sys

    print("Testing SecretsManager...\n")

    try:
        # Create secrets manager
        secrets = create_secrets_manager()

        print(f"Environment: {secrets.environment}")
        print(f"Provider: {secrets.provider_type.value}")
        print()

        # Try to get some common secrets
        test_secrets = [
            'TELEGRAM_BOT_TOKEN',
            'GROQ_API_KEY',
            'SECRET_KEY'
        ]

        print("Testing secret retrieval:")
        for secret_name in test_secrets:
            try:
                value = secrets.get(secret_name)
                # Mask the value for security
                masked = value[:8] + '...' + value[-4:] if value and len(value) > 12 else '[REDACTED]'
                print(f"  ✅ {secret_name}: {masked}")
            except SecretsError as e:
                print(f"  ❌ {secret_name}: Not found")

        print()
        print("Audit log:")
        for entry in secrets.get_audit_log():
            status = "✅" if entry['success'] else "❌"
            print(f"  {status} {entry['timestamp']} - {entry['secret_name']}")

        print("\n✅ SecretsManager test complete!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
