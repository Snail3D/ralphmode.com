#!/usr/bin/env python3
"""
Claude Code CLI Installation Helper - OB-026

Guides users through installing Claude Code CLI.
Checks installation status, provides commands, and troubleshoots issues.
"""

import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClaudeCodeStatus:
    """Status of Claude Code CLI installation."""
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None
    error: Optional[str] = None


class ClaudeCodeSetup:
    """Handles Claude Code CLI installation and verification."""

    INSTALL_COMMAND = "npm install -g @anthropic-ai/claude-code"
    DOCS_URL = "https://docs.anthropic.com/claude-code"

    # Common issues and solutions
    TROUBLESHOOTING = {
        "command_not_found": {
            "issue": "claude command not found",
            "solutions": [
                "Make sure npm is installed: `npm --version`",
                "Check your PATH includes npm global bin directory",
                "Try running: `npm config get prefix` to find npm global location",
                "On Mac/Linux, you may need to add npm bin to PATH in ~/.bashrc or ~/.zshrc"
            ]
        },
        "permission_denied": {
            "issue": "Permission denied during installation",
            "solutions": [
                "Don't use sudo with npm global installs",
                "Configure npm to install globally without sudo:",
                "  mkdir ~/.npm-global",
                "  npm config set prefix '~/.npm-global'",
                "  Add to ~/.bashrc: export PATH=~/.npm-global/bin:$PATH",
                "  source ~/.bashrc"
            ]
        },
        "npm_not_installed": {
            "issue": "npm is not installed",
            "solutions": [
                "Install Node.js (includes npm): https://nodejs.org",
                "Or use nvm (Node Version Manager): https://github.com/nvm-sh/nvm",
                "Verify installation with: `node --version && npm --version`"
            ]
        },
        "old_version": {
            "issue": "Claude Code CLI is outdated",
            "solutions": [
                "Update to latest version:",
                f"  {INSTALL_COMMAND}",
                "Or update all global packages:",
                "  npm update -g"
            ]
        }
    }

    def __init__(self):
        """Initialize Claude Code setup helper."""
        self.logger = logging.getLogger(__name__)

    async def check_claude_installed(self) -> ClaudeCodeStatus:
        """
        Check if Claude Code CLI is installed and working.

        Returns:
            ClaudeCodeStatus with installation details
        """
        try:
            # Check if claude command exists
            result = await self._run_command("which claude")
            if result.returncode != 0:
                return ClaudeCodeStatus(
                    installed=False,
                    error="claude command not found in PATH"
                )

            claude_path = result.stdout.strip()

            # Get version
            version_result = await self._run_command("claude --version")
            if version_result.returncode != 0:
                return ClaudeCodeStatus(
                    installed=True,
                    path=claude_path,
                    error="claude command found but --version failed"
                )

            version = version_result.stdout.strip()

            return ClaudeCodeStatus(
                installed=True,
                version=version,
                path=claude_path
            )

        except Exception as e:
            self.logger.error(f"Error checking Claude Code installation: {e}")
            return ClaudeCodeStatus(
                installed=False,
                error=str(e)
            )

    async def check_npm_installed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if npm is installed.

        Returns:
            Tuple of (is_installed, version)
        """
        try:
            result = await self._run_command("npm --version")
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, None
        except Exception as e:
            self.logger.error(f"Error checking npm: {e}")
            return False, None

    async def verify_installation(self) -> Dict[str, Any]:
        """
        Verify Claude Code CLI installation with comprehensive checks.

        Returns:
            Dict with verification results
        """
        results = {
            "success": False,
            "checks": {}
        }

        # Check npm
        npm_installed, npm_version = await self.check_npm_installed()
        results["checks"]["npm"] = {
            "installed": npm_installed,
            "version": npm_version
        }

        if not npm_installed:
            results["error"] = "npm_not_installed"
            return results

        # Check Claude Code
        status = await self.check_claude_installed()
        results["checks"]["claude"] = {
            "installed": status.installed,
            "version": status.version,
            "path": status.path,
            "error": status.error
        }

        results["success"] = status.installed

        if not status.installed:
            if "not found" in (status.error or ""):
                results["error"] = "command_not_found"
            else:
                results["error"] = "unknown_error"

        return results

    def get_install_command(self) -> str:
        """Get the npm install command for Claude Code CLI."""
        return self.INSTALL_COMMAND

    def get_troubleshooting_for_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Get troubleshooting steps for a specific issue.

        Args:
            issue_key: Key identifying the issue (e.g., 'command_not_found')

        Returns:
            Dict with issue and solutions, or None if issue not found
        """
        return self.TROUBLESHOOTING.get(issue_key)

    def get_all_troubleshooting(self) -> Dict[str, Dict[str, Any]]:
        """Get all troubleshooting information."""
        return self.TROUBLESHOOTING

    def get_docs_url(self) -> str:
        """Get Claude Code documentation URL."""
        return self.DOCS_URL

    async def _run_command(self, command: str) -> subprocess.CompletedProcess:
        """
        Run a shell command asynchronously.

        Args:
            command: Command to run

        Returns:
            CompletedProcess with result
        """
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        return subprocess.CompletedProcess(
            args=command,
            returncode=process.returncode,
            stdout=stdout.decode().strip() if stdout else "",
            stderr=stderr.decode().strip() if stderr else ""
        )


# Singleton instance
_claude_code_setup: Optional[ClaudeCodeSetup] = None


def get_claude_code_setup() -> ClaudeCodeSetup:
    """Get singleton instance of ClaudeCodeSetup."""
    global _claude_code_setup
    if _claude_code_setup is None:
        _claude_code_setup = ClaudeCodeSetup()
    return _claude_code_setup
