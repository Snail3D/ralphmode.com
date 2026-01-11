#!/usr/bin/env python3
"""
Slack MCP Server Setup (OB-043)

Guides users through connecting Slack workspace for notifications and interaction.
Enables Ralph to send updates and interact via Slack.
"""

import subprocess
import logging
import os
import json
from typing import Dict, Any, Optional, Tuple, List
from telegram_utils import create_copy_button, create_copy_message


class SlackMCPSetup:
    """Handles Slack MCP server setup and configuration."""

    def __init__(self):
        """Initialize the Slack MCP setup handler."""
        self.logger = logging.getLogger(__name__)

    def check_slack_token_configured(self) -> Tuple[bool, str]:
        """Check if Slack token is configured in environment.

        Returns:
            Tuple of (is_configured, status_message)
        """
        slack_token = os.environ.get('SLACK_BOT_TOKEN')
        slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')

        if slack_token:
            # Mask the token for security
            masked = f"{slack_token[:10]}...{slack_token[-4:]}" if len(slack_token) > 14 else "***"
            return True, f"Slack token configured: {masked}"
        elif slack_webhook:
            return True, "Slack webhook URL configured"
        else:
            return False, "No Slack credentials configured"

    def get_app_creation_instructions(self) -> Dict[str, Any]:
        """Get instructions for creating a Slack app.

        Returns:
            Dictionary with app creation steps and links
        """
        return {
            "title": "Create a Slack App",
            "url": "https://api.slack.com/apps/new",
            "steps": [
                {
                    "step": 1,
                    "title": "Go to Slack API",
                    "description": "Visit api.slack.com/apps and click 'Create New App'",
                    "url": "https://api.slack.com/apps/new"
                },
                {
                    "step": 2,
                    "title": "Choose 'From scratch'",
                    "description": "Give your app a name (e.g., 'Ralph Mode Bot')"
                },
                {
                    "step": 3,
                    "title": "Select your workspace",
                    "description": "Choose the workspace where Ralph will send messages"
                },
                {
                    "step": 4,
                    "title": "Configure OAuth & Permissions",
                    "description": "Add these bot token scopes:",
                    "scopes": [
                        "chat:write - Send messages",
                        "chat:write.public - Send to any channel",
                        "channels:read - List channels",
                        "groups:read - List private channels"
                    ]
                },
                {
                    "step": 5,
                    "title": "Install to Workspace",
                    "description": "Click 'Install to Workspace' and authorize"
                },
                {
                    "step": 6,
                    "title": "Copy Bot Token",
                    "description": "Copy the 'Bot User OAuth Token' (starts with xoxb-)"
                }
            ],
            "video_tutorial": "https://www.youtube.com/results?search_query=slack+bot+token+tutorial",
            "ralph_tip": "I made a Slack thingy once! It was fun. Just follow the clicky things!"
        }

    def get_oauth_setup_guide(self) -> Dict[str, Any]:
        """Get OAuth setup guidance for Slack.

        Returns:
            Dictionary with OAuth configuration details
        """
        return {
            "title": "Configure OAuth & Permissions",
            "url": "https://api.slack.com/authentication/oauth-v2",
            "required_scopes": {
                "bot": [
                    {"scope": "chat:write", "reason": "Send messages to channels"},
                    {"scope": "chat:write.public", "reason": "Send to public channels without joining"},
                    {"scope": "channels:read", "reason": "List available channels"},
                    {"scope": "groups:read", "reason": "List private channels"},
                    {"scope": "im:write", "reason": "Send direct messages"},
                    {"scope": "users:read", "reason": "Get user information"}
                ],
                "user": []  # No user scopes needed for basic bot functionality
            },
            "redirect_url": "https://ralphmode.com/slack/oauth/callback",  # Placeholder
            "install_url_template": "https://slack.com/oauth/v2/authorize?client_id={client_id}&scope={scopes}",
            "ralph_tip": "Ralph doesn't understand OAuth but the smart workers say it's important!"
        }

    def check_mcp_server_installed(self) -> Tuple[bool, str]:
        """Check if Slack MCP server is available.

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

            # Check if Slack MCP server package is available
            result = subprocess.run(
                ["npm", "view", "@modelcontextprotocol/server-slack", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"Slack MCP server available (v{version})"
            return False, "Slack MCP server package not found"
        except FileNotFoundError:
            return False, "npm/npx not found - Node.js installation required"
        except subprocess.TimeoutExpired:
            return False, "Package check timed out"
        except Exception as e:
            self.logger.error(f"Error checking MCP server: {e}")
            return False, f"Check failed: {str(e)}"

    def get_install_instructions(self) -> Dict[str, Any]:
        """Get Slack MCP server installation instructions.

        Returns:
            Dictionary with installation steps and commands
        """
        return {
            "install_command": "npx -y @modelcontextprotocol/server-slack",
            "description": "Install Slack MCP server via npx (no permanent installation needed)",
            "requirements": [
                "Node.js 18+ installed",
                "Slack Bot Token (xoxb-...)",
                "Workspace access"
            ],
            "config_example": {
                "mcpServers": {
                    "slack": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-slack"],
                        "env": {
                            "SLACK_BOT_TOKEN": "xoxb-your-token-here"
                        }
                    }
                }
            },
            "config_location": "~/.config/claude/config.json",
            "ralph_tip": "Just paste the token thingy into the config file! Easy peasy!"
        }

    def test_slack_connection(self, token: str, channel: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Test Slack connection by sending a test message.

        Args:
            token: Slack bot token
            channel: Channel ID or name (defaults to general)

        Returns:
            Tuple of (success, message, response_data)
        """
        try:
            import requests

            # Use Slack API to post a test message
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "channel": channel or "#general",
                "text": "🎉 Ralph Mode connected! I can send messages now!",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Ralph Mode is connected!* 🎉\n\nI can send you updates about:\n• Build progress\n• Task completions\n• Code reviews\n• Worker conversations"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Sent from Ralph Mode - ralphmode.com"
                            }
                        ]
                    }
                ]
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if data.get("ok"):
                return True, "✅ Test message sent successfully!", data
            else:
                error = data.get("error", "Unknown error")
                return False, f"❌ Failed to send message: {error}", data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error testing Slack: {e}")
            return False, f"❌ Network error: {str(e)}", None
        except Exception as e:
            self.logger.error(f"Error testing Slack connection: {e}")
            return False, f"❌ Error: {str(e)}", None

    def list_channels(self, token: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List available Slack channels.

        Args:
            token: Slack bot token

        Returns:
            Tuple of (success, channels_list, error_message)
        """
        try:
            import requests

            url = "https://slack.com/api/conversations.list"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            params = {
                "types": "public_channel,private_channel",
                "limit": 100
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()

            if data.get("ok"):
                channels = data.get("channels", [])
                formatted_channels = [
                    {
                        "id": ch["id"],
                        "name": ch["name"],
                        "is_private": ch.get("is_private", False),
                        "is_member": ch.get("is_member", False)
                    }
                    for ch in channels
                ]
                return True, formatted_channels, ""
            else:
                error = data.get("error", "Unknown error")
                return False, [], f"Failed to list channels: {error}"
        except Exception as e:
            self.logger.error(f"Error listing Slack channels: {e}")
            return False, [], f"Error: {str(e)}"

    def configure_default_channel(self, channel_name: str, channel_id: str) -> Dict[str, Any]:
        """Configure default channel for Ralph notifications.

        Args:
            channel_name: Channel name (e.g., "general")
            channel_id: Channel ID (e.g., "C01234ABC")

        Returns:
            Configuration dictionary
        """
        config = {
            "default_channel": {
                "name": channel_name,
                "id": channel_id
            },
            "notification_preferences": {
                "build_started": True,
                "build_completed": True,
                "task_completed": True,
                "blocker_escalated": True,
                "session_ended": True
            },
            "message_format": "rich",  # "rich" or "simple"
            "mention_on_blocker": False,  # Don't @channel by default
            "ralph_tip": f"Ralph will send messages to #{channel_name}!"
        }
        return config

    def get_setup_summary(self) -> Dict[str, Any]:
        """Get complete setup summary and checklist.

        Returns:
            Dictionary with setup checklist and status
        """
        return {
            "title": "Slack MCP Setup Checklist",
            "steps": [
                {
                    "id": "create_app",
                    "title": "Create Slack App",
                    "status": "pending",
                    "action": "Visit api.slack.com/apps"
                },
                {
                    "id": "configure_oauth",
                    "title": "Configure OAuth Scopes",
                    "status": "pending",
                    "action": "Add required bot scopes"
                },
                {
                    "id": "install_app",
                    "title": "Install App to Workspace",
                    "status": "pending",
                    "action": "Authorize app installation"
                },
                {
                    "id": "copy_token",
                    "title": "Copy Bot Token",
                    "status": "pending",
                    "action": "Save xoxb- token securely"
                },
                {
                    "id": "install_mcp",
                    "title": "Install Slack MCP Server",
                    "status": "pending",
                    "action": "Run npx command"
                },
                {
                    "id": "test_connection",
                    "title": "Test Connection",
                    "status": "pending",
                    "action": "Send test message"
                },
                {
                    "id": "configure_channel",
                    "title": "Set Default Channel",
                    "status": "pending",
                    "action": "Choose notification channel"
                }
            ],
            "estimated_time": "10-15 minutes",
            "difficulty": "Medium",
            "ralph_encouragement": "You got this boss! Just follow the steps and I'll be chatting on Slack in no time!"
        }


def get_slack_mcp_setup() -> SlackMCPSetup:
    """Factory function to get SlackMCPSetup instance.

    Returns:
        SlackMCPSetup instance
    """
    return SlackMCPSetup()
