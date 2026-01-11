#!/usr/bin/env python3
"""
Setup Verification Suite for Ralph Mode

Checks that everything is configured correctly.
Provides visual status dashboard and fix suggestions.
"""

import os
import re
import subprocess
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class CheckStatus(Enum):
    """Status of a configuration check."""
    PASS = "✅"
    FAIL = "❌"
    WARNING = "⚠️"
    SKIP = "⏭️"
    INFO = "ℹ️"


@dataclass
class CheckResult:
    """Result of a configuration check."""
    name: str
    status: CheckStatus
    message: str
    fix_suggestion: Optional[str] = None
    details: Optional[str] = None
    category: str = "General"


class SetupVerifier:
    """Verifies all setup configurations for Ralph Mode."""

    def __init__(self):
        """Initialize the setup verifier."""
        self.logger = logging.getLogger(__name__)
        self.results: List[CheckResult] = []

    def verify_all(self, include_optional: bool = True) -> Dict[str, Any]:
        """Run all verification checks.

        Args:
            include_optional: Whether to check optional configurations

        Returns:
            Dictionary with verification results and summary
        """
        self.results = []

        # Required checks
        self._check_python_version()
        self._check_git_installed()
        self._check_git_configured()
        self._check_ssh_key()
        self._check_env_file()
        self._check_telegram_token()
        self._check_groq_api_key()
        self._check_telegram_admin_id()
        self._check_project_structure()

        # Optional checks
        if include_optional:
            self._check_anthropic_api_key()
            self._check_github_cli()
            self._check_docker()
            self._check_node_version()

        return self._generate_summary()

    def _check_python_version(self):
        """Check Python version is 3.10+."""
        try:
            import sys
            version = sys.version_info

            if version.major == 3 and version.minor >= 10:
                self.results.append(CheckResult(
                    name="Python Version",
                    status=CheckStatus.PASS,
                    message=f"Python {version.major}.{version.minor}.{version.micro}",
                    category="System"
                ))
            elif version.major == 3 and version.minor >= 8:
                self.results.append(CheckResult(
                    name="Python Version",
                    status=CheckStatus.WARNING,
                    message=f"Python {version.major}.{version.minor}.{version.micro} (recommended 3.10+)",
                    fix_suggestion="Consider upgrading to Python 3.10 or newer for best compatibility",
                    category="System"
                ))
            else:
                self.results.append(CheckResult(
                    name="Python Version",
                    status=CheckStatus.FAIL,
                    message=f"Python {version.major}.{version.minor}.{version.micro} is too old",
                    fix_suggestion="Install Python 3.10 or newer from python.org",
                    category="System"
                ))
        except Exception as e:
            self.results.append(CheckResult(
                name="Python Version",
                status=CheckStatus.FAIL,
                message="Could not check Python version",
                fix_suggestion=str(e),
                category="System"
            ))

    def _check_git_installed(self):
        """Check if Git is installed."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self.results.append(CheckResult(
                    name="Git Installation",
                    status=CheckStatus.PASS,
                    message=version,
                    category="System"
                ))
            else:
                self.results.append(CheckResult(
                    name="Git Installation",
                    status=CheckStatus.FAIL,
                    message="Git command failed",
                    fix_suggestion="Install Git from git-scm.com",
                    category="System"
                ))
        except FileNotFoundError:
            self.results.append(CheckResult(
                name="Git Installation",
                status=CheckStatus.FAIL,
                message="Git is not installed",
                fix_suggestion="Install Git from git-scm.com",
                category="System"
            ))
        except Exception as e:
            self.results.append(CheckResult(
                name="Git Installation",
                status=CheckStatus.FAIL,
                message="Could not check Git",
                fix_suggestion=str(e),
                category="System"
            ))

    def _check_git_configured(self):
        """Check if Git user name and email are configured."""
        try:
            # Check user.name
            result_name = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Check user.email
            result_email = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                timeout=5
            )

            name = result_name.stdout.strip()
            email = result_email.stdout.strip()

            if name and email:
                self.results.append(CheckResult(
                    name="Git Configuration",
                    status=CheckStatus.PASS,
                    message=f"{name} <{email}>",
                    category="Git"
                ))
            elif name:
                self.results.append(CheckResult(
                    name="Git Configuration",
                    status=CheckStatus.WARNING,
                    message="Email not configured",
                    fix_suggestion='Run: git config --global user.email "your@email.com"',
                    category="Git"
                ))
            elif email:
                self.results.append(CheckResult(
                    name="Git Configuration",
                    status=CheckStatus.WARNING,
                    message="Name not configured",
                    fix_suggestion='Run: git config --global user.name "Your Name"',
                    category="Git"
                ))
            else:
                self.results.append(CheckResult(
                    name="Git Configuration",
                    status=CheckStatus.FAIL,
                    message="Name and email not configured",
                    fix_suggestion='Run: git config --global user.name "Your Name" && git config --global user.email "your@email.com"',
                    category="Git"
                ))
        except Exception as e:
            self.results.append(CheckResult(
                name="Git Configuration",
                status=CheckStatus.FAIL,
                message="Could not check Git config",
                fix_suggestion=str(e),
                category="Git"
            ))

    def _check_ssh_key(self):
        """Check if SSH key exists and is added to GitHub."""
        ssh_dir = os.path.expanduser("~/.ssh")

        # Check for SSH keys
        key_files = []
        for key_type in ["id_ed25519", "id_rsa", "id_ecdsa"]:
            key_path = os.path.join(ssh_dir, key_type)
            if os.path.exists(key_path):
                key_files.append(key_type)

        if not key_files:
            self.results.append(CheckResult(
                name="SSH Key",
                status=CheckStatus.FAIL,
                message="No SSH key found",
                fix_suggestion='Generate SSH key: ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""',
                category="Git"
            ))
            return

        # Check if key is added to GitHub
        try:
            result = subprocess.run(
                ["ssh", "-T", "git@github.com"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # GitHub returns 1 even on successful auth
            if "successfully authenticated" in result.stderr.lower():
                self.results.append(CheckResult(
                    name="SSH Key",
                    status=CheckStatus.PASS,
                    message=f"Key exists and is configured on GitHub ({', '.join(key_files)})",
                    category="Git"
                ))
            else:
                self.results.append(CheckResult(
                    name="SSH Key",
                    status=CheckStatus.WARNING,
                    message=f"Key exists but may not be on GitHub ({', '.join(key_files)})",
                    fix_suggestion="Add your SSH key to GitHub: https://github.com/settings/keys",
                    details=result.stderr[:200],
                    category="Git"
                ))
        except subprocess.TimeoutExpired:
            self.results.append(CheckResult(
                name="SSH Key",
                status=CheckStatus.WARNING,
                message=f"Key exists but GitHub connection timed out ({', '.join(key_files)})",
                fix_suggestion="Check your internet connection and GitHub SSH settings",
                category="Git"
            ))
        except Exception as e:
            self.results.append(CheckResult(
                name="SSH Key",
                status=CheckStatus.WARNING,
                message=f"Key exists but could not verify GitHub connection ({', '.join(key_files)})",
                fix_suggestion=str(e),
                category="Git"
            ))

    def _check_env_file(self):
        """Check if .env file exists."""
        if os.path.exists(".env"):
            # Check file is not empty
            with open(".env", "r") as f:
                content = f.read().strip()

            if content:
                # Count configured variables (non-comment, non-empty lines)
                lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
                self.results.append(CheckResult(
                    name=".env File",
                    status=CheckStatus.PASS,
                    message=f"Exists with {len(lines)} configured variables",
                    category="Configuration"
                ))
            else:
                self.results.append(CheckResult(
                    name=".env File",
                    status=CheckStatus.WARNING,
                    message="File exists but is empty",
                    fix_suggestion="Copy .env.example to .env and fill in your values",
                    category="Configuration"
                ))
        else:
            self.results.append(CheckResult(
                name=".env File",
                status=CheckStatus.FAIL,
                message="File does not exist",
                fix_suggestion="Copy .env.example to .env: cp .env.example .env",
                category="Configuration"
            ))

    def _load_env(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}

        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()

        # Also check actual environment variables
        for key in ["TELEGRAM_BOT_TOKEN", "GROQ_API_KEY", "ANTHROPIC_API_KEY", "TELEGRAM_ADMIN_ID", "TELEGRAM_OWNER_ID"]:
            if key in os.environ:
                env_vars[key] = os.environ[key]

        return env_vars

    def _check_telegram_token(self):
        """Check if Telegram bot token is configured."""
        env_vars = self._load_env()

        token = env_vars.get("TELEGRAM_BOT_TOKEN", "")

        if not token or token == "your_telegram_bot_token_here":
            self.results.append(CheckResult(
                name="Telegram Bot Token",
                status=CheckStatus.FAIL,
                message="Not configured",
                fix_suggestion="Get token from @BotFather and add to .env: TELEGRAM_BOT_TOKEN=your_token",
                category="API Keys"
            ))
            return

        # Validate token format (should be like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
        if re.match(r'^\d+:[A-Za-z0-9_-]+$', token):
            self.results.append(CheckResult(
                name="Telegram Bot Token",
                status=CheckStatus.PASS,
                message=f"Configured ({token[:10]}...)",
                category="API Keys"
            ))
        else:
            self.results.append(CheckResult(
                name="Telegram Bot Token",
                status=CheckStatus.WARNING,
                message="Configured but format looks incorrect",
                fix_suggestion="Token should be like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
                details=f"Current value: {token[:20]}...",
                category="API Keys"
            ))

    def _check_groq_api_key(self):
        """Check if Groq API key is configured."""
        env_vars = self._load_env()

        key = env_vars.get("GROQ_API_KEY", "")

        if not key or key == "gsk_your_groq_api_key_here":
            self.results.append(CheckResult(
                name="Groq API Key",
                status=CheckStatus.FAIL,
                message="Not configured",
                fix_suggestion="Get free key from console.groq.com and add to .env: GROQ_API_KEY=gsk_...",
                category="API Keys"
            ))
            return

        # Validate key format (should start with gsk_)
        if key.startswith("gsk_"):
            self.results.append(CheckResult(
                name="Groq API Key",
                status=CheckStatus.PASS,
                message=f"Configured ({key[:10]}...)",
                category="API Keys"
            ))
        else:
            self.results.append(CheckResult(
                name="Groq API Key",
                status=CheckStatus.WARNING,
                message="Configured but doesn't start with 'gsk_'",
                fix_suggestion="Groq keys should start with 'gsk_'",
                details=f"Current value: {key[:20]}...",
                category="API Keys"
            ))

    def _check_anthropic_api_key(self):
        """Check if Anthropic API key is configured (optional)."""
        env_vars = self._load_env()

        key = env_vars.get("ANTHROPIC_API_KEY", "")

        if not key or key == "sk-ant-your_claude_key_here":
            self.results.append(CheckResult(
                name="Anthropic API Key (Optional)",
                status=CheckStatus.INFO,
                message="Not configured",
                fix_suggestion="Get key from console.anthropic.com for Claude-powered features",
                category="API Keys (Optional)"
            ))
            return

        # Validate key format (should start with sk-ant-)
        if key.startswith("sk-ant-"):
            self.results.append(CheckResult(
                name="Anthropic API Key (Optional)",
                status=CheckStatus.PASS,
                message=f"Configured ({key[:15]}...)",
                category="API Keys (Optional)"
            ))
        else:
            self.results.append(CheckResult(
                name="Anthropic API Key (Optional)",
                status=CheckStatus.WARNING,
                message="Configured but doesn't start with 'sk-ant-'",
                fix_suggestion="Anthropic keys should start with 'sk-ant-'",
                details=f"Current value: {key[:20]}...",
                category="API Keys (Optional)"
            ))

    def _check_telegram_admin_id(self):
        """Check if Telegram admin ID is configured."""
        env_vars = self._load_env()

        admin_id = env_vars.get("TELEGRAM_ADMIN_ID", "")
        owner_id = env_vars.get("TELEGRAM_OWNER_ID", "")

        if not admin_id or admin_id == "your_telegram_user_id_here":
            if owner_id and owner_id != "your_owner_telegram_id_here":
                self.results.append(CheckResult(
                    name="Telegram Admin ID",
                    status=CheckStatus.WARNING,
                    message="ADMIN_ID not set but OWNER_ID is configured",
                    fix_suggestion="Set TELEGRAM_ADMIN_ID in .env (get from @userinfobot)",
                    category="Configuration"
                ))
            else:
                self.results.append(CheckResult(
                    name="Telegram Admin ID",
                    status=CheckStatus.FAIL,
                    message="Not configured",
                    fix_suggestion="Get your ID from @userinfobot and add to .env: TELEGRAM_ADMIN_ID=your_id",
                    category="Configuration"
                ))
            return

        # Validate ID format (should be numeric)
        if admin_id.isdigit():
            self.results.append(CheckResult(
                name="Telegram Admin ID",
                status=CheckStatus.PASS,
                message=f"Configured (ID: {admin_id})",
                category="Configuration"
            ))
        else:
            self.results.append(CheckResult(
                name="Telegram Admin ID",
                status=CheckStatus.WARNING,
                message="Configured but doesn't look like a valid Telegram ID",
                fix_suggestion="ID should be numeric (like: 123456789)",
                details=f"Current value: {admin_id}",
                category="Configuration"
            ))

    def _check_project_structure(self):
        """Check if project structure is correct."""
        required_files = [
            "ralph_bot.py",
            "onboarding_wizard.py",
            "scripts/ralph/ralph.sh",
            "scripts/ralph/prd.json",
            ".env.example"
        ]

        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)

        if not missing_files:
            self.results.append(CheckResult(
                name="Project Structure",
                status=CheckStatus.PASS,
                message="All required files present",
                category="System"
            ))
        else:
            self.results.append(CheckResult(
                name="Project Structure",
                status=CheckStatus.FAIL,
                message=f"Missing {len(missing_files)} required files",
                fix_suggestion=f"Missing files: {', '.join(missing_files)}",
                category="System"
            ))

    def _check_github_cli(self):
        """Check if GitHub CLI is installed (optional)."""
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0]
                self.results.append(CheckResult(
                    name="GitHub CLI (Optional)",
                    status=CheckStatus.PASS,
                    message=version,
                    category="Optional Tools"
                ))
            else:
                self.results.append(CheckResult(
                    name="GitHub CLI (Optional)",
                    status=CheckStatus.INFO,
                    message="Not available",
                    fix_suggestion="Install gh CLI for easier GitHub operations: https://cli.github.com",
                    category="Optional Tools"
                ))
        except FileNotFoundError:
            self.results.append(CheckResult(
                name="GitHub CLI (Optional)",
                status=CheckStatus.INFO,
                message="Not installed",
                fix_suggestion="Install gh CLI for easier GitHub operations: https://cli.github.com",
                category="Optional Tools"
            ))
        except Exception:
            pass  # Optional check, don't show errors

    def _check_docker(self):
        """Check if Docker is installed (optional)."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self.results.append(CheckResult(
                    name="Docker (Optional)",
                    status=CheckStatus.PASS,
                    message=version,
                    category="Optional Tools"
                ))
            else:
                self.results.append(CheckResult(
                    name="Docker (Optional)",
                    status=CheckStatus.INFO,
                    message="Not available",
                    fix_suggestion="Install Docker for containerized deployments: https://docker.com",
                    category="Optional Tools"
                ))
        except FileNotFoundError:
            self.results.append(CheckResult(
                name="Docker (Optional)",
                status=CheckStatus.INFO,
                message="Not installed",
                fix_suggestion="Install Docker for containerized deployments: https://docker.com",
                category="Optional Tools"
            ))
        except Exception:
            pass  # Optional check, don't show errors

    def _check_node_version(self):
        """Check Node.js version (optional, for MCP servers)."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self.results.append(CheckResult(
                    name="Node.js (Optional)",
                    status=CheckStatus.PASS,
                    message=version,
                    category="Optional Tools"
                ))
            else:
                self.results.append(CheckResult(
                    name="Node.js (Optional)",
                    status=CheckStatus.INFO,
                    message="Not available",
                    fix_suggestion="Install Node.js for MCP server support: https://nodejs.org",
                    category="Optional Tools"
                ))
        except FileNotFoundError:
            self.results.append(CheckResult(
                name="Node.js (Optional)",
                status=CheckStatus.INFO,
                message="Not installed",
                fix_suggestion="Install Node.js for MCP server support: https://nodejs.org",
                category="Optional Tools"
            ))
        except Exception:
            pass  # Optional check, don't show errors

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of all checks.

        Returns:
            Dictionary with results summary
        """
        # Count by status
        counts = {
            "pass": len([r for r in self.results if r.status == CheckStatus.PASS]),
            "fail": len([r for r in self.results if r.status == CheckStatus.FAIL]),
            "warning": len([r for r in self.results if r.status == CheckStatus.WARNING]),
            "info": len([r for r in self.results if r.status == CheckStatus.INFO]),
            "total": len(self.results)
        }

        # Group by category
        by_category: Dict[str, List[CheckResult]] = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)

        # Determine overall status
        if counts["fail"] > 0:
            overall_status = "incomplete"
            overall_message = "Setup is incomplete - some required items are missing"
        elif counts["warning"] > 0:
            overall_status = "warnings"
            overall_message = "Setup is mostly complete but has some warnings"
        elif counts["pass"] > 0:
            overall_status = "complete"
            overall_message = "Setup is complete! All checks passed!"
        else:
            overall_status = "unknown"
            overall_message = "Could not verify setup status"

        return {
            "overall_status": overall_status,
            "overall_message": overall_message,
            "counts": counts,
            "results": self.results,
            "by_category": by_category
        }

    def get_dashboard_message(self) -> str:
        """Generate a visual status dashboard message.

        Returns:
            Formatted message with visual status dashboard
        """
        if not self.results:
            return "*No verification results available*\n\nRun verify_all() first!"

        summary = self._generate_summary()

        # Build the message
        lines = ["*🔍 Ralph's Setup Verification Dashboard*\n"]

        # Overall status
        if summary["overall_status"] == "complete":
            lines.append("*✅ SETUP COMPLETE!*")
            lines.append("Everything looks good! You ready to go!\n")
        elif summary["overall_status"] == "incomplete":
            lines.append("*❌ SETUP INCOMPLETE*")
            lines.append("Ralph found some problems! Let's fix them!\n")
        elif summary["overall_status"] == "warnings":
            lines.append("*⚠️ SETUP HAS WARNINGS*")
            lines.append("Mostly good but Ralph found some issues!\n")

        # Summary counts
        lines.append(f"*Summary:*")
        lines.append(f"• {summary['counts']['pass']} checks passed ✅")
        if summary['counts']['fail'] > 0:
            lines.append(f"• {summary['counts']['fail']} checks failed ❌")
        if summary['counts']['warning'] > 0:
            lines.append(f"• {summary['counts']['warning']} warnings ⚠️")
        if summary['counts']['info'] > 0:
            lines.append(f"• {summary['counts']['info']} info items ℹ️")
        lines.append("")

        # Results by category
        for category, results in summary["by_category"].items():
            lines.append(f"*{category}:*")

            for result in results:
                status_emoji = result.status.value
                lines.append(f"{status_emoji} {result.name}: {result.message}")

                if result.fix_suggestion and result.status in [CheckStatus.FAIL, CheckStatus.WARNING]:
                    lines.append(f"   → {result.fix_suggestion}")

            lines.append("")

        return "\n".join(lines)

    def export_report(self, filename: str = "setup_verification_report.txt") -> str:
        """Export verification results to a file.

        Args:
            filename: Name of the report file

        Returns:
            Path to the generated report
        """
        if not self.results:
            return ""

        summary = self._generate_summary()

        with open(filename, "w") as f:
            f.write("Ralph Mode - Setup Verification Report\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Overall Status: {summary['overall_status'].upper()}\n")
            f.write(f"{summary['overall_message']}\n\n")

            f.write("Summary:\n")
            f.write(f"  Total checks: {summary['counts']['total']}\n")
            f.write(f"  Passed: {summary['counts']['pass']}\n")
            f.write(f"  Failed: {summary['counts']['fail']}\n")
            f.write(f"  Warnings: {summary['counts']['warning']}\n")
            f.write(f"  Info: {summary['counts']['info']}\n\n")

            f.write("Detailed Results:\n")
            f.write("-" * 60 + "\n\n")

            for category, results in summary["by_category"].items():
                f.write(f"{category}:\n")

                for result in results:
                    f.write(f"  [{result.status.name}] {result.name}\n")
                    f.write(f"    Message: {result.message}\n")

                    if result.fix_suggestion:
                        f.write(f"    Fix: {result.fix_suggestion}\n")

                    if result.details:
                        f.write(f"    Details: {result.details}\n")

                    f.write("\n")

                f.write("\n")

        return os.path.abspath(filename)


def get_setup_verifier() -> SetupVerifier:
    """Get a setup verifier instance.

    Returns:
        SetupVerifier instance
    """
    return SetupVerifier()


# CLI usage
if __name__ == "__main__":
    verifier = SetupVerifier()
    results = verifier.verify_all(include_optional=True)

    print(verifier.get_dashboard_message())

    # Export report
    report_path = verifier.export_report()
    print(f"\nFull report exported to: {report_path}")
