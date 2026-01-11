#!/usr/bin/env python3
"""
Discord MCP Server Setup (OB-044)

Guides users through connecting Discord server for community features.
Enables Ralph to send updates and interact via Discord.
"""

import subprocess
import logging
import os
import json
from typing import Dict, Any, Optional, Tuple, List


class DiscordMCPSetup:
    """Handles Discord MCP server setup and configuration."""

    def __init__(self):
        """Initialize the Discord MCP setup handler."""
        self.logger = logging.getLogger(__name__)

    def check_discord_token_configured(self) -> Tuple[bool, str]:
        """Check if Discord token is configured in environment.

        Returns:
            Tuple of (is_configured, status_message)
        """
        discord_token = os.environ.get('DISCORD_BOT_TOKEN')

        if discord_token:
            # Mask the token for security
            masked = f"{discord_token[:10]}...{discord_token[-4:]}" if len(discord_token) > 14 else "***"
            return True, f"Discord token configured: {masked}"
        else:
            return False, "No Discord bot token configured"

    def get_bot_creation_instructions(self) -> Dict[str, Any]:
        """Get instructions for creating a Discord bot.

        Returns:
            Dictionary with bot creation steps and links
        """
        return {
            "title": "Create a Discord Bot",
            "url": "https://discord.com/developers/applications",
            "steps": [
                {
                    "step": 1,
                    "title": "Go to Discord Developer Portal",
                    "description": "Visit discord.com/developers/applications",
                    "url": "https://discord.com/developers/applications"
                },
                {
                    "step": 2,
                    "title": "Create New Application",
                    "description": "Click 'New Application' and name it (e.g., 'Ralph Mode Bot')"
                },
                {
                    "step": 3,
                    "title": "Create a Bot",
                    "description": "Go to 'Bot' tab and click 'Add Bot'"
                },
                {
                    "step": 4,
                    "title": "Configure Bot Permissions",
                    "description": "Enable these Privileged Gateway Intents:",
                    "intents": [
                        "Presence Intent (optional)",
                        "Server Members Intent",
                        "Message Content Intent"
                    ]
                },
                {
                    "step": 5,
                    "title": "Copy Bot Token",
                    "description": "Under 'Token', click 'Copy' to get your bot token"
                },
                {
                    "step": 6,
                    "title": "Invite Bot to Server",
                    "description": "Go to 'OAuth2' → 'URL Generator', select 'bot' scope and permissions"
                },
                {
                    "step": 7,
                    "title": "Generate Invite Link",
                    "description": "Copy the generated URL and paste in browser to invite bot"
                }
            ],
            "required_permissions": [
                "Send Messages",
                "Read Message History",
                "View Channels",
                "Embed Links",
                "Attach Files"
            ],
            "video_tutorial": "https://www.youtube.com/results?search_query=discord+bot+setup+tutorial",
            "ralph_tip": "Discord bots are like Telegram bots but for gamers! Just click the buttons and copy the token!"
        }

    def get_token_setup_guide(self) -> Dict[str, Any]:
        """Get Discord bot token setup guidance.

        Returns:
            Dictionary with token configuration details
        """
        return {
            "title": "Configure Discord Bot Token",
            "security_warning": "Never share your bot token! It's like a password.",
            "environment_variable": "DISCORD_BOT_TOKEN",
            "token_format": "Starts with 'MTE' or similar base64-encoded string",
            "storage_locations": {
                ".env": "DISCORD_BOT_TOKEN=your_token_here",
                "config.json": {
                    "mcpServers": {
                        "discord": {
                            "env": {
                                "DISCORD_BOT_TOKEN": "your_token_here"
                            }
                        }
                    }
                }
            },
            "ralph_tip": "Keep this secret! Don't push it to GitHub or Ralph will be sad!"
        }

    def check_mcp_server_installed(self) -> Tuple[bool, str]:
        """Check if Discord MCP server is available.

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

            # Check if Discord MCP server package is available
            result = subprocess.run(
                ["npm", "view", "@modelcontextprotocol/server-discord", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"Discord MCP server available (v{version})"
            return False, "Discord MCP server package not found"
        except FileNotFoundError:
            return False, "npm/npx not found - Node.js installation required"
        except subprocess.TimeoutExpired:
            return False, "Package check timed out"
        except Exception as e:
            self.logger.error(f"Error checking MCP server: {e}")
            return False, f"Check failed: {str(e)}"

    def get_install_instructions(self) -> Dict[str, Any]:
        """Get Discord MCP server installation instructions.

        Returns:
            Dictionary with installation steps and commands
        """
        return {
            "install_command": "npx -y @modelcontextprotocol/server-discord",
            "description": "Install Discord MCP server via npx (no permanent installation needed)",
            "requirements": [
                "Node.js 18+ installed",
                "Discord Bot Token",
                "Bot invited to your server"
            ],
            "config_example": {
                "mcpServers": {
                    "discord": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-discord"],
                        "env": {
                            "DISCORD_BOT_TOKEN": "your_token_here"
                        }
                    }
                }
            },
            "config_location": "~/.config/claude/config.json",
            "ralph_tip": "Just copy-paste the command and Ralph will be on Discord!"
        }

    def test_discord_connection(self, token: str, channel_id: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Test Discord connection by sending a test message.

        Args:
            token: Discord bot token
            channel_id: Channel ID (numeric string)

        Returns:
            Tuple of (success, message, response_data)
        """
        try:
            import requests

            if not channel_id:
                return False, "❌ Channel ID required for Discord", None

            # Use Discord API to post a test message
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json"
            }
            payload = {
                "content": "🎉 Ralph Mode connected to Discord!",
                "embeds": [
                    {
                        "title": "Ralph Mode is Online! 🚀",
                        "description": "I can send you updates about:\n• Build progress\n• Task completions\n• Code reviews\n• Worker conversations",
                        "color": 3447003,  # Blue
                        "footer": {
                            "text": "Sent from Ralph Mode - ralphmode.com"
                        }
                    }
                ]
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if response.status_code == 200:
                return True, "✅ Test message sent successfully!", data
            else:
                error = data.get("message", "Unknown error")
                return False, f"❌ Failed to send message: {error}", data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error testing Discord: {e}")
            return False, f"❌ Network error: {str(e)}", None
        except Exception as e:
            self.logger.error(f"Error testing Discord connection: {e}")
            return False, f"❌ Error: {str(e)}", None

    def list_channels(self, token: str, guild_id: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List available Discord channels in a guild.

        Args:
            token: Discord bot token
            guild_id: Discord server (guild) ID

        Returns:
            Tuple of (success, channels_list, error_message)
        """
        try:
            import requests

            url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
            headers = {
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                channels = response.json()
                formatted_channels = [
                    {
                        "id": ch["id"],
                        "name": ch["name"],
                        "type": ch["type"],  # 0=text, 2=voice, 4=category, etc.
                        "position": ch.get("position", 0)
                    }
                    for ch in channels
                    if ch["type"] == 0  # Only text channels
                ]
                # Sort by position
                formatted_channels.sort(key=lambda x: x["position"])
                return True, formatted_channels, ""
            else:
                error = response.json().get("message", "Unknown error")
                return False, [], f"Failed to list channels: {error}"
        except Exception as e:
            self.logger.error(f"Error listing Discord channels: {e}")
            return False, [], f"Error: {str(e)}"

    def configure_default_channel(self, channel_name: str, channel_id: str) -> Dict[str, Any]:
        """Configure default channel for Ralph notifications.

        Args:
            channel_name: Channel name (e.g., "general")
            channel_id: Channel ID (numeric string)

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
            "message_format": "rich",  # "rich" (embeds) or "simple" (plain text)
            "mention_on_blocker": False,  # Don't @everyone by default
            "use_embeds": True,  # Use Discord embeds for rich formatting
            "ralph_tip": f"Ralph will send messages to #{channel_name}!"
        }
        return config

    def get_setup_summary(self) -> Dict[str, Any]:
        """Get complete setup summary and checklist.

        Returns:
            Dictionary with setup checklist and status
        """
        return {
            "title": "Discord MCP Setup Checklist",
            "steps": [
                {
                    "id": "create_bot",
                    "title": "Create Discord Bot",
                    "status": "pending",
                    "action": "Visit discord.com/developers/applications"
                },
                {
                    "id": "enable_intents",
                    "title": "Enable Required Intents",
                    "status": "pending",
                    "action": "Turn on Message Content Intent"
                },
                {
                    "id": "copy_token",
                    "title": "Copy Bot Token",
                    "status": "pending",
                    "action": "Save token securely"
                },
                {
                    "id": "invite_bot",
                    "title": "Invite Bot to Server",
                    "status": "pending",
                    "action": "Generate and use invite link"
                },
                {
                    "id": "install_mcp",
                    "title": "Install Discord MCP Server",
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
            "ralph_encouragement": "Discord is fun! Follow the steps and we'll be gaming... I mean working together!"
        }


def get_discord_mcp_setup() -> DiscordMCPSetup:
    """Factory function to get DiscordMCPSetup instance.

    Returns:
        DiscordMCPSetup instance
    """
    return DiscordMCPSetup()
