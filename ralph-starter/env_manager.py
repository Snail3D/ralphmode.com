"""Environment File Manager for Ralph Mode Onboarding.

This module handles creating and managing the .env file during onboarding.
Ensures secure storage of API keys and configuration values.

Created for OB-008: Environment File Creator
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class EnvManager:
    """Manages .env file creation and updates during onboarding."""

    # Required environment variables for basic functionality
    REQUIRED_VARS = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_OWNER_ID",
        "GROQ_API_KEY",
    ]

    # Optional but recommended variables
    OPTIONAL_VARS = [
        "ANTHROPIC_API_KEY",
        "TELEGRAM_ADMIN_ID",
        "POWER_USER_PASSWORD",
        "SECRET_KEY",
        "SESSION_SECRET_KEY",
        "CSRF_SECRET_KEY",
    ]

    # Variable descriptions for user guidance
    VAR_DESCRIPTIONS = {
        "TELEGRAM_BOT_TOKEN": "Your Telegram bot token from @BotFather",
        "TELEGRAM_OWNER_ID": "Your Telegram user ID (Tier 1 - full control)",
        "TELEGRAM_ADMIN_ID": "Admin Telegram user ID (if different from owner)",
        "GROQ_API_KEY": "Groq API key for fast AI inference (free at console.groq.com)",
        "ANTHROPIC_API_KEY": "Claude API key for code changes (optional)",
        "POWER_USER_PASSWORD": "Password for Tier 2 power users",
        "SECRET_KEY": "Secret key for session encryption (auto-generated)",
        "SESSION_SECRET_KEY": "Secret key for session management (auto-generated)",
        "CSRF_SECRET_KEY": "Secret key for CSRF protection (auto-generated)",
    }

    def __init__(self, project_root: Optional[str] = None):
        """Initialize the environment manager.

        Args:
            project_root: Path to project root (defaults to current directory)
        """
        self.project_root = Path(project_root or os.getcwd())
        self.env_file = self.project_root / ".env"
        self.env_example_file = self.project_root / ".env.example"
        self.gitignore_file = self.project_root / ".gitignore"

    def env_exists(self) -> bool:
        """Check if .env file already exists.

        Returns:
            True if .env exists
        """
        return self.env_file.exists()

    def env_example_exists(self) -> bool:
        """Check if .env.example file exists.

        Returns:
            True if .env.example exists
        """
        return self.env_example_file.exists()

    def create_env_file(self) -> bool:
        """Create a new .env file if it doesn't exist.

        Returns:
            True if created, False if already exists
        """
        if self.env_exists():
            return False

        # Create basic .env file with comments
        content = self._generate_env_template()
        self.env_file.write_text(content)
        return True

    def _generate_env_template(self) -> str:
        """Generate .env file template with comments.

        Returns:
            .env file content
        """
        lines = [
            "# Ralph Mode Configuration",
            "# NEVER commit this file to GitHub!",
            "# This file is in .gitignore - it stays LOCAL only!",
            "",
            "# Environment",
            "RALPH_ENV=development",
            "",
            "# Required: Telegram Bot Configuration",
            "TELEGRAM_BOT_TOKEN=",
            "TELEGRAM_OWNER_ID=",
            "",
            "# Required: Groq API (FREE - get at console.groq.com)",
            "GROQ_API_KEY=",
            "",
            "# Optional: Claude API (for actual code changes)",
            "ANTHROPIC_API_KEY=",
            "",
            "# Optional: Additional Configuration",
            "TELEGRAM_ADMIN_ID=",
            "POWER_USER_PASSWORD=",
            "",
            "# Server Configuration",
            "HOST=0.0.0.0",
            "PORT=5000",
            "LOG_LEVEL=INFO",
            "",
        ]
        return "\n".join(lines)

    def get_variable(self, var_name: str) -> Optional[str]:
        """Get a variable value from .env file.

        Args:
            var_name: Variable name to get

        Returns:
            Variable value or None if not found
        """
        if not self.env_exists():
            return None

        content = self.env_file.read_text()
        pattern = rf'^{re.escape(var_name)}\s*=\s*(.*)$'
        match = re.search(pattern, content, re.MULTILINE)
        return match.group(1).strip() if match else None

    def set_variable(self, var_name: str, value: str) -> bool:
        """Set or update a variable in .env file.

        Args:
            var_name: Variable name
            value: Variable value

        Returns:
            True if successful
        """
        # Create .env if it doesn't exist
        if not self.env_exists():
            self.create_env_file()

        content = self.env_file.read_text()
        pattern = rf'^{re.escape(var_name)}\s*=.*$'
        replacement = f'{var_name}={value}'

        # Check if variable exists
        if re.search(pattern, content, re.MULTILINE):
            # Update existing variable
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            # Append new variable
            if not content.endswith('\n'):
                content += '\n'
            new_content = content + f'{replacement}\n'

        self.env_file.write_text(new_content)
        return True

    def get_all_variables(self) -> Dict[str, str]:
        """Get all variables from .env file.

        Returns:
            Dictionary of variable name to value
        """
        if not self.env_exists():
            return {}

        variables = {}
        content = self.env_file.read_text()

        for line in content.split('\n'):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse variable
            if '=' in line:
                key, value = line.split('=', 1)
                variables[key.strip()] = value.strip()

        return variables

    def check_missing_required(self) -> List[str]:
        """Check which required variables are missing or empty.

        Returns:
            List of missing variable names
        """
        all_vars = self.get_all_variables()
        missing = []

        for var in self.REQUIRED_VARS:
            if var not in all_vars or not all_vars[var]:
                missing.append(var)

        return missing

    def check_missing_optional(self) -> List[str]:
        """Check which optional variables are missing or empty.

        Returns:
            List of missing optional variable names
        """
        all_vars = self.get_all_variables()
        missing = []

        for var in self.OPTIONAL_VARS:
            if var not in all_vars or not all_vars[var]:
                missing.append(var)

        return missing

    def verify_gitignore(self) -> Tuple[bool, str]:
        """Verify that .env is in .gitignore.

        Returns:
            Tuple of (is_safe, message)
        """
        if not self.gitignore_file.exists():
            return False, ".gitignore file not found!"

        content = self.gitignore_file.read_text()

        # Check if .env is ignored
        if re.search(r'^\s*\.env\s*$', content, re.MULTILINE):
            return True, ".env is safely in .gitignore!"

        # Check if commented out (bad!)
        if re.search(r'^\s*#.*\.env', content, re.MULTILINE):
            return False, ".env is commented out in .gitignore!"

        return False, ".env is NOT in .gitignore - SECURITY RISK!"

    def add_to_gitignore(self) -> bool:
        """Add .env to .gitignore if not present.

        Returns:
            True if added, False if already present
        """
        is_safe, _ = self.verify_gitignore()
        if is_safe:
            return False  # Already present

        # Create .gitignore if it doesn't exist
        if not self.gitignore_file.exists():
            content = "# Environment variables - NEVER commit these!\n.env\n"
            self.gitignore_file.write_text(content)
            return True

        # Append to existing .gitignore
        content = self.gitignore_file.read_text()
        if not content.endswith('\n'):
            content += '\n'
        content += "\n# Environment variables - NEVER commit these!\n.env\n"
        self.gitignore_file.write_text(content)
        return True

    def generate_secret_key(self) -> str:
        """Generate a secure random secret key.

        Returns:
            64-character hex secret key
        """
        import secrets
        return secrets.token_hex(32)

    def auto_generate_secrets(self) -> Dict[str, str]:
        """Auto-generate secret keys if not already set.

        Returns:
            Dictionary of generated secrets
        """
        generated = {}
        secret_vars = ["SECRET_KEY", "SESSION_SECRET_KEY", "CSRF_SECRET_KEY"]

        for var in secret_vars:
            current_value = self.get_variable(var)
            # Only generate if empty or placeholder
            if not current_value or "your_" in current_value or "_here" in current_value:
                new_secret = self.generate_secret_key()
                self.set_variable(var, new_secret)
                generated[var] = new_secret

        return generated

    def get_variable_description(self, var_name: str) -> str:
        """Get user-friendly description of a variable.

        Args:
            var_name: Variable name

        Returns:
            Description string
        """
        return self.VAR_DESCRIPTIONS.get(var_name, f"Configuration variable: {var_name}")

    def validate_setup(self) -> Tuple[bool, List[str]]:
        """Validate that .env is properly set up.

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        # Check .env exists
        if not self.env_exists():
            issues.append(".env file does not exist!")
            return False, issues

        # Check .gitignore
        is_safe, msg = self.verify_gitignore()
        if not is_safe:
            issues.append(msg)

        # Check required variables
        missing_required = self.check_missing_required()
        if missing_required:
            issues.append(f"Missing required variables: {', '.join(missing_required)}")

        return len(issues) == 0, issues

    def get_setup_summary(self) -> str:
        """Get a summary of current .env setup status.

        Returns:
            Human-readable summary string
        """
        lines = []

        # Check if .env exists
        if not self.env_exists():
            lines.append("❌ .env file does not exist")
            return "\n".join(lines)

        lines.append("✅ .env file exists")

        # Check .gitignore
        is_safe, msg = self.verify_gitignore()
        lines.append(f"{'✅' if is_safe else '❌'} {msg}")

        # Check required variables
        missing_required = self.check_missing_required()
        if missing_required:
            lines.append(f"❌ Missing required: {', '.join(missing_required)}")
        else:
            lines.append(f"✅ All required variables set ({len(self.REQUIRED_VARS)} total)")

        # Check optional variables
        missing_optional = self.check_missing_optional()
        configured_optional = len(self.OPTIONAL_VARS) - len(missing_optional)
        lines.append(f"ℹ️  Optional variables: {configured_optional}/{len(self.OPTIONAL_VARS)} configured")

        return "\n".join(lines)
