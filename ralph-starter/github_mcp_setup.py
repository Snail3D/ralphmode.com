#!/usr/bin/env python3
"""
GitHub MCP Server Setup

Guides users through connecting GitHub MCP server with Ralph's personality.
Enables repo management from Ralph Mode.
"""

import subprocess
import logging
import os
from typing import Dict, Any, Optional, Tuple


class GitHubMCPSetup:
    """Handles GitHub MCP server setup and configuration."""

    def __init__(self):
        """Initialize the GitHub MCP setup handler."""
        self.logger = logging.getLogger(__name__)

    def check_gh_cli_installed(self) -> Tuple[bool, str]:
        """Check if GitHub CLI is installed.

        Returns:
            Tuple of (is_installed, version_or_error_message)
        """
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                return True, version
            return False, "GitHub CLI not responding correctly"
        except FileNotFoundError:
            return False, "GitHub CLI not found - needs installation"
        except subprocess.TimeoutExpired:
            return False, "GitHub CLI check timed out"
        except Exception as e:
            self.logger.error(f"Error checking gh CLI: {e}")
            return False, f"Error: {str(e)}"

    def check_gh_auth_status(self) -> Tuple[bool, Optional[str]]:
        """Check if user is authenticated with GitHub CLI.

        Returns:
            Tuple of (is_authenticated, username_or_error)
        """
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # gh auth status returns 0 if logged in
            if result.returncode == 0:
                # Parse username from output
                for line in result.stdout.split('\n'):
                    if 'Logged in to github.com as' in line:
                        username = line.split('as')[-1].strip().split()[0]
                        return True, username
                return True, "unknown user"
            else:
                return False, None
        except FileNotFoundError:
            return False, None
        except subprocess.TimeoutExpired:
            self.logger.warning("GitHub auth status check timed out")
            return False, None
        except Exception as e:
            self.logger.error(f"Error checking GitHub auth: {e}")
            return False, None

    def get_auth_instructions(self) -> Dict[str, Any]:
        """Get instructions for GitHub authentication.

        Returns:
            Dictionary with auth instructions and commands
        """
        return {
            "method": "device_flow",
            "command": "gh auth login",
            "steps": [
                "Run the command: `gh auth login`",
                "Choose 'GitHub.com' when prompted",
                "Choose 'HTTPS' for preferred protocol",
                "Choose 'Login with a web browser'",
                "Copy the one-time code shown",
                "Press Enter to open github.com in browser",
                "Paste the code and authorize",
                "You're authenticated! 🎉"
            ],
            "install_gh_cli": {
                "mac": "brew install gh",
                "linux": "See: https://github.com/cli/cli/blob/trunk/docs/install_linux.md",
                "windows": "winget install --id GitHub.cli"
            }
        }

    def check_mcp_server_installed(self) -> Tuple[bool, str]:
        """Check if GitHub MCP server is available.

        Returns:
            Tuple of (is_installed, status_message)
        """
        try:
            # Check if npx is available
            result = subprocess.run(
                ["npx", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, "npx not found - Node.js required"

            # Try to get server info (doesn't actually run it)
            # Just check if the package resolves
            result = subprocess.run(
                ["npm", "view", "@modelcontextprotocol/server-github", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"GitHub MCP server available (v{version})"
            return False, "GitHub MCP server package not found"
        except FileNotFoundError:
            return False, "npm/npx not found - Node.js installation required"
        except subprocess.TimeoutExpired:
            return False, "Package check timed out"
        except Exception as e:
            self.logger.error(f"Error checking MCP server: {e}")
            return False, f"Check failed: {str(e)}"

    def get_install_instructions(self) -> Dict[str, Any]:
        """Get GitHub MCP server installation instructions.

        Returns:
            Dictionary with installation steps and commands
        """
        return {
            "install_command": "npx -y @modelcontextprotocol/server-github",
            "config_location": "~/.config/claude/claude_desktop_config.json",
            "config_example": {
                "mcpServers": {
                    "github": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "@modelcontextprotocol/server-github"
                        ],
                        "env": {
                            "GITHUB_TOKEN": "<your-github-token>"
                        }
                    }
                }
            },
            "steps": [
                "1. Make sure Node.js is installed (npx required)",
                "2. Authenticate with GitHub CLI: `gh auth login`",
                "3. Add GitHub MCP server to Claude config",
                "4. Restart Claude Code to load the server",
                "5. Test with a GitHub operation!"
            ],
            "token_info": {
                "how_to_create": "Settings → Developer settings → Personal access tokens → Generate new token",
                "required_scopes": ["repo", "read:org", "read:user"],
                "token_url": "https://github.com/settings/tokens"
            }
        }

    def verify_connection(self) -> Tuple[bool, str]:
        """Verify GitHub MCP server connection works.

        Returns:
            Tuple of (success, message)
        """
        # Check both gh CLI auth and server availability
        cli_installed, cli_msg = self.check_gh_cli_installed()
        if not cli_installed:
            return False, f"GitHub CLI not installed: {cli_msg}"

        is_authed, username = self.check_gh_auth_status()
        if not is_authed:
            return False, "Not authenticated with GitHub - run 'gh auth login'"

        server_ok, server_msg = self.check_mcp_server_installed()
        if not server_ok:
            return False, f"GitHub MCP server not ready: {server_msg}"

        return True, f"✅ Connected as @{username} - GitHub MCP ready!"

    def get_available_actions(self) -> Dict[str, list]:
        """Get list of actions available with GitHub MCP server.

        Returns:
            Dictionary with categorized actions
        """
        return {
            "Repository Management": [
                "📂 Create new repositories",
                "🔍 Search your repos",
                "⭐ Star/unstar repos",
                "👁️ Watch/unwatch repos",
                "📊 Get repo stats"
            ],
            "Issues & PRs": [
                "🐛 Create and manage issues",
                "✅ Create pull requests",
                "💬 Comment on issues/PRs",
                "🏷️ Add/remove labels",
                "👤 Assign issues"
            ],
            "Code Operations": [
                "📝 Read file contents from any repo",
                "🌿 List branches",
                "📋 Get commit history",
                "🔀 Compare branches",
                "📦 Create releases"
            ],
            "Collaboration": [
                "👥 Manage collaborators",
                "🔐 Check repo permissions",
                "📢 Create discussions",
                "⚙️ Update repo settings",
                "🪝 Configure webhooks"
            ]
        }

    def format_setup_guide(self) -> str:
        """Format complete setup guide for display.

        Returns:
            Formatted markdown guide
        """
        cli_ok, cli_msg = self.check_gh_cli_installed()
        auth_ok, username = self.check_gh_auth_status()
        server_ok, server_msg = self.check_mcp_server_installed()

        guide = "**GitHub MCP Server Setup Guide** 🐙\n\n"

        # Step 1: GitHub CLI
        guide += "**1️⃣ GitHub CLI**\n"
        if cli_ok:
            guide += f"   ✅ {cli_msg}\n\n"
        else:
            guide += f"   ❌ {cli_msg}\n"
            guide += "   Install: `brew install gh` (Mac) or see [docs](https://cli.github.com)\n\n"

        # Step 2: Authentication
        guide += "**2️⃣ GitHub Authentication**\n"
        if auth_ok:
            guide += f"   ✅ Logged in as @{username}\n\n"
        else:
            guide += "   ❌ Not authenticated\n"
            guide += "   Run: `gh auth login`\n"
            guide += "   Then follow the prompts to authenticate\n\n"

        # Step 3: MCP Server
        guide += "**3️⃣ GitHub MCP Server**\n"
        if server_ok:
            guide += f"   ✅ {server_msg}\n\n"
        else:
            guide += f"   ⚠️ {server_msg}\n"
            guide += "   Install Node.js if missing: https://nodejs.org\n\n"

        # What's possible
        guide += "**🎯 What You Can Do:**\n"
        actions = self.get_available_actions()
        for category, action_list in actions.items():
            guide += f"\n_{category}_:\n"
            for action in action_list[:3]:  # Show first 3 of each
                guide += f"  • {action}\n"

        guide += "\n💡 Once setup is complete, Ralph and the team can manage your repos directly!"

        return guide

    def get_quick_test_command(self) -> Dict[str, str]:
        """Get a quick command to test GitHub MCP is working.

        Returns:
            Dictionary with test command info
        """
        return {
            "command": "gh repo list --limit 5",
            "description": "List your first 5 repositories",
            "expected": "Should show your GitHub repos",
            "troubleshooting": [
                "If this fails, check: gh auth status",
                "Make sure you're logged in: gh auth login",
                "Verify token has 'repo' scope"
            ]
        }


# Singleton instance
_github_mcp_setup_instance = None


def get_github_mcp_setup() -> GitHubMCPSetup:
    """Get the singleton GitHub MCP setup instance.

    Returns:
        GitHubMCPSetup instance
    """
    global _github_mcp_setup_instance
    if _github_mcp_setup_instance is None:
        _github_mcp_setup_instance = GitHubMCPSetup()
    return _github_mcp_setup_instance
