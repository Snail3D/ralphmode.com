#!/usr/bin/env python3
"""
API Key Manager for Ralph Mode

Handles secure storage and validation of API keys.
Keys are stored in .env file (never committed to git).
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Tuple


class APIKeyManager:
    """Manages API keys securely."""

    def __init__(self, env_file: str = ".env"):
        """Initialize the API key manager.

        Args:
            env_file: Path to the .env file (default: .env)
        """
        self.logger = logging.getLogger(__name__)
        self.env_file = Path(env_file)

        # Create .env file if it doesn't exist
        if not self.env_file.exists():
            self.env_file.touch(mode=0o600)  # Create with restricted permissions
            self.logger.info(f"Created new .env file at {self.env_file}")

    def validate_anthropic_key(self, key: str) -> Tuple[bool, Optional[str]]:
        """Validate Anthropic API key format.

        Args:
            key: The API key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not key:
            return False, "API key is empty"

        key = key.strip()

        # Check prefix
        if not key.startswith("sk-ant-"):
            return False, "Anthropic API keys must start with 'sk-ant-'"

        # Check minimum length (Anthropic keys are ~100+ characters)
        if len(key) < 50:
            return False, f"API key is too short ({len(key)} chars). Real keys are 100+ characters"

        # Check for valid characters only
        if not re.match(r'^sk-ant-[a-zA-Z0-9_-]+$', key):
            return False, "API key contains invalid characters"

        return True, None

    def validate_telegram_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """Validate Telegram bot token format.

        Args:
            token: The bot token to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token:
            return False, "Bot token is empty"

        token = token.strip()

        # Telegram tokens are in format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
        if not re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
            return False, "Invalid Telegram bot token format"

        # Check minimum length
        if len(token) < 30:
            return False, "Bot token is too short"

        return True, None

    def validate_groq_key(self, key: str) -> Tuple[bool, Optional[str]]:
        """Validate Groq API key format.

        Args:
            key: The API key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not key:
            return False, "API key is empty"

        key = key.strip()

        # Groq keys start with gsk_
        if not key.startswith("gsk_"):
            return False, "Groq API keys must start with 'gsk_'"

        # Check minimum length
        if len(key) < 40:
            return False, f"API key is too short ({len(key)} chars)"

        return True, None

    def save_key_to_env(self, key_name: str, key_value: str) -> bool:
        """Save or update an API key in the .env file.

        Args:
            key_name: The environment variable name (e.g., ANTHROPIC_API_KEY)
            key_value: The API key value

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read existing .env content
            if self.env_file.exists():
                with open(self.env_file, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []

            # Check if key already exists
            key_exists = False
            updated_lines = []

            for line in lines:
                # Skip comments and empty lines
                if line.strip().startswith('#') or not line.strip():
                    updated_lines.append(line)
                    continue

                # Check if this is the key we're updating
                if '=' in line:
                    env_key = line.split('=')[0].strip()
                    if env_key == key_name:
                        # Update existing key
                        updated_lines.append(f"{key_name}={key_value}\n")
                        key_exists = True
                        self.logger.info(f"Updated existing key: {key_name}")
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)

            # If key doesn't exist, add it
            if not key_exists:
                updated_lines.append(f"\n# Added by Ralph Mode\n")
                updated_lines.append(f"{key_name}={key_value}\n")
                self.logger.info(f"Added new key: {key_name}")

            # Write back to .env with secure permissions
            with open(self.env_file, 'w') as f:
                f.writelines(updated_lines)

            # Ensure file has restricted permissions (user read/write only)
            os.chmod(self.env_file, 0o600)

            return True

        except Exception as e:
            self.logger.error(f"Error saving key to .env: {e}")
            return False

    def get_key_from_env(self, key_name: str) -> Optional[str]:
        """Get an API key from the .env file.

        Args:
            key_name: The environment variable name

        Returns:
            The key value if found, None otherwise
        """
        try:
            if not self.env_file.exists():
                return None

            with open(self.env_file, 'r') as f:
                for line in f:
                    # Skip comments and empty lines
                    if line.strip().startswith('#') or not line.strip():
                        continue

                    if '=' in line:
                        env_key, env_value = line.split('=', 1)
                        if env_key.strip() == key_name:
                            return env_value.strip()

            return None

        except Exception as e:
            self.logger.error(f"Error reading key from .env: {e}")
            return None

    def check_env_in_gitignore(self) -> bool:
        """Check if .env is in .gitignore.

        Returns:
            True if .env is ignored, False otherwise
        """
        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():
            return False

        try:
            with open(gitignore_path, 'r') as f:
                content = f.read()
                # Check for .env in gitignore (as a line or pattern)
                return bool(re.search(r'(^|\n)\.env($|\n|\s)', content))

        except Exception as e:
            self.logger.error(f"Error reading .gitignore: {e}")
            return False

    def ensure_env_in_gitignore(self) -> bool:
        """Ensure .env is in .gitignore.

        Returns:
            True if .env is already ignored or was successfully added
        """
        gitignore_path = Path(".gitignore")

        # Check if already in gitignore
        if self.check_env_in_gitignore():
            self.logger.info(".env is already in .gitignore")
            return True

        try:
            # Create .gitignore if it doesn't exist
            if not gitignore_path.exists():
                with open(gitignore_path, 'w') as f:
                    f.write("# Environment variables\n.env\n")
                self.logger.info("Created .gitignore with .env entry")
                return True

            # Add .env to existing .gitignore
            with open(gitignore_path, 'a') as f:
                f.write("\n# Environment variables (added by Ralph Mode)\n.env\n")
            self.logger.info("Added .env to .gitignore")
            return True

        except Exception as e:
            self.logger.error(f"Error updating .gitignore: {e}")
            return False

    def test_anthropic_key(self, api_key: str) -> Tuple[bool, str]:
        """Test if an Anthropic API key works.

        Args:
            api_key: The API key to test

        Returns:
            Tuple of (success, message)
        """
        try:
            import anthropic

            # Create client
            client = anthropic.Anthropic(api_key=api_key)

            # Make a minimal test request
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",  # Use the cheapest model
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Say 'test'"}
                ]
            )

            if message.content:
                return True, "API key is valid and working!"
            else:
                return False, "API key accepted but no response received"

        except anthropic.AuthenticationError:
            return False, "Authentication failed. API key is invalid or expired."
        except anthropic.PermissionDeniedError:
            return False, "Permission denied. Check your API key permissions."
        except anthropic.RateLimitError:
            return False, "Rate limit exceeded. Your key works but you're being throttled."
        except Exception as e:
            return False, f"Test failed: {str(e)}"

    def get_anthropic_key_info(self) -> str:
        """Get information about the saved Anthropic API key.

        Returns:
            Info message about the key status
        """
        key = self.get_key_from_env("ANTHROPIC_API_KEY")

        if not key:
            return "❌ No Anthropic API key found in .env"

        # Mask the key for display (show only first 7 and last 4 chars)
        if len(key) > 15:
            masked_key = f"{key[:11]}...{key[-4:]}"
        else:
            masked_key = "sk-ant-***"

        return f"✅ Anthropic API key found: {masked_key}"


def get_api_key_manager() -> APIKeyManager:
    """Get the API key manager instance.

    Returns:
        APIKeyManager instance
    """
    return APIKeyManager()
