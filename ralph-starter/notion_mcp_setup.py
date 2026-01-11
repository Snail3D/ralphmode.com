#!/usr/bin/env python3
"""
Notion MCP Server Setup (OB-045)

Guides users through connecting Notion for documentation and planning integration.
Enables Ralph to read and write to Notion databases and pages.
"""

import subprocess
import logging
import os
import json
from typing import Dict, Any, Optional, Tuple, List


class NotionMCPSetup:
    """Handles Notion MCP server setup and configuration."""

    def __init__(self):
        """Initialize the Notion MCP setup handler."""
        self.logger = logging.getLogger(__name__)

    def check_notion_token_configured(self) -> Tuple[bool, str]:
        """Check if Notion token is configured in environment.

        Returns:
            Tuple of (is_configured, status_message)
        """
        notion_token = os.environ.get('NOTION_API_KEY')
        notion_integration = os.environ.get('NOTION_INTEGRATION_TOKEN')

        token = notion_token or notion_integration
        if token:
            # Mask the token for security
            masked = f"{token[:10]}...{token[-4:]}" if len(token) > 14 else "***"
            return True, f"Notion token configured: {masked}"
        else:
            return False, "No Notion API key configured"

    def get_integration_creation_instructions(self) -> Dict[str, Any]:
        """Get instructions for creating a Notion integration.

        Returns:
            Dictionary with integration creation steps and links
        """
        return {
            "title": "Create a Notion Integration",
            "url": "https://www.notion.so/my-integrations",
            "steps": [
                {
                    "step": 1,
                    "title": "Go to Notion Integrations",
                    "description": "Visit notion.so/my-integrations",
                    "url": "https://www.notion.so/my-integrations"
                },
                {
                    "step": 2,
                    "title": "Create New Integration",
                    "description": "Click '+ New integration' button"
                },
                {
                    "step": 3,
                    "title": "Name Your Integration",
                    "description": "Give it a name (e.g., 'Ralph Mode Bot')"
                },
                {
                    "step": 4,
                    "title": "Select Associated Workspace",
                    "description": "Choose the workspace where Ralph can access pages"
                },
                {
                    "step": 5,
                    "title": "Configure Capabilities",
                    "description": "Enable these capabilities:",
                    "capabilities": [
                        "Read content - View pages and databases",
                        "Update content - Edit pages and databases",
                        "Insert content - Create new pages"
                    ]
                },
                {
                    "step": 6,
                    "title": "Copy Integration Token",
                    "description": "Copy the 'Internal Integration Token' (starts with secret_)"
                },
                {
                    "step": 7,
                    "title": "Share Pages with Integration",
                    "description": "In Notion, click Share on any page → Add your integration"
                }
            ],
            "video_tutorial": "https://www.youtube.com/results?search_query=notion+api+integration+setup",
            "ralph_tip": "Notion is like a smart notebook! Ralph can write stuff there now!"
        }

    def get_page_sharing_guide(self) -> Dict[str, Any]:
        """Get guidance on sharing Notion pages with integration.

        Returns:
            Dictionary with page sharing details
        """
        return {
            "title": "Share Pages with Ralph",
            "description": "Your integration needs explicit access to pages",
            "steps": [
                "Open the Notion page or database you want Ralph to access",
                "Click the '...' menu in the top-right",
                "Select 'Add connections'",
                "Search for and select your integration (e.g., 'Ralph Mode Bot')",
                "Click 'Confirm' to grant access"
            ],
            "important_note": "You must share EACH page/database individually. Parent page access doesn't grant child access automatically.",
            "ralph_tip": "Don't forget to share the pages! Ralph can't see them otherwise!"
        }

    def check_mcp_server_installed(self) -> Tuple[bool, str]:
        """Check if Notion MCP server is available.

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

            # Check if Notion MCP server package is available
            result = subprocess.run(
                ["npm", "view", "@modelcontextprotocol/server-notion", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"Notion MCP server available (v{version})"
            return False, "Notion MCP server package not found"
        except FileNotFoundError:
            return False, "npm/npx not found - Node.js installation required"
        except subprocess.TimeoutExpired:
            return False, "Package check timed out"
        except Exception as e:
            self.logger.error(f"Error checking MCP server: {e}")
            return False, f"Check failed: {str(e)}"

    def get_install_instructions(self) -> Dict[str, Any]:
        """Get Notion MCP server installation instructions.

        Returns:
            Dictionary with installation steps and commands
        """
        return {
            "install_command": "npx -y @modelcontextprotocol/server-notion",
            "description": "Install Notion MCP server via npx (no permanent installation needed)",
            "requirements": [
                "Node.js 18+ installed",
                "Notion Integration Token (secret_...)",
                "Pages shared with integration"
            ],
            "config_example": {
                "mcpServers": {
                    "notion": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-notion"],
                        "env": {
                            "NOTION_API_KEY": "secret_your_token_here"
                        }
                    }
                }
            },
            "config_location": "~/.config/claude/config.json",
            "ralph_tip": "Just paste the secret token into the config! Then Ralph can read your notes!"
        }

    def test_notion_connection(self, token: str) -> Tuple[bool, str, Optional[Dict]]:
        """Test Notion connection by fetching user info.

        Args:
            token: Notion integration token

        Returns:
            Tuple of (success, message, response_data)
        """
        try:
            import requests

            # Use Notion API to get bot/user info
            url = "https://api.notion.com/v1/users/me"
            headers = {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            if response.status_code == 200:
                bot_name = data.get("name", "Unknown")
                workspace = data.get("workspace_name", "Unknown workspace")
                return True, f"✅ Connected as: {bot_name} in {workspace}", data
            else:
                error = data.get("message", "Unknown error")
                return False, f"❌ Failed to connect: {error}", data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error testing Notion: {e}")
            return False, f"❌ Network error: {str(e)}", None
        except Exception as e:
            self.logger.error(f"Error testing Notion connection: {e}")
            return False, f"❌ Error: {str(e)}", None

    def list_databases(self, token: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List accessible Notion databases.

        Args:
            token: Notion integration token

        Returns:
            Tuple of (success, databases_list, error_message)
        """
        try:
            import requests

            url = "https://api.notion.com/v1/search"
            headers = {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            payload = {
                "filter": {
                    "value": "database",
                    "property": "object"
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if response.status_code == 200:
                databases = data.get("results", [])
                formatted_databases = [
                    {
                        "id": db["id"],
                        "title": db.get("title", [{}])[0].get("plain_text", "Untitled"),
                        "url": db.get("url", ""),
                        "created_time": db.get("created_time", ""),
                        "last_edited_time": db.get("last_edited_time", "")
                    }
                    for db in databases
                ]
                return True, formatted_databases, ""
            else:
                error = data.get("message", "Unknown error")
                return False, [], f"Failed to list databases: {error}"
        except Exception as e:
            self.logger.error(f"Error listing Notion databases: {e}")
            return False, [], f"Error: {str(e)}"

    def list_pages(self, token: str, limit: int = 10) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List accessible Notion pages.

        Args:
            token: Notion integration token
            limit: Maximum number of pages to return

        Returns:
            Tuple of (success, pages_list, error_message)
        """
        try:
            import requests

            url = "https://api.notion.com/v1/search"
            headers = {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            payload = {
                "filter": {
                    "value": "page",
                    "property": "object"
                },
                "page_size": limit
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if response.status_code == 200:
                pages = data.get("results", [])
                formatted_pages = [
                    {
                        "id": page["id"],
                        "title": page.get("properties", {}).get("title", {}).get("title", [{}])[0].get("plain_text", "Untitled"),
                        "url": page.get("url", ""),
                        "created_time": page.get("created_time", ""),
                        "last_edited_time": page.get("last_edited_time", "")
                    }
                    for page in pages
                ]
                return True, formatted_pages, ""
            else:
                error = data.get("message", "Unknown error")
                return False, [], f"Failed to list pages: {error}"
        except Exception as e:
            self.logger.error(f"Error listing Notion pages: {e}")
            return False, [], f"Error: {str(e)}"

    def get_example_queries(self) -> List[Dict[str, str]]:
        """Get example queries users can try with Notion.

        Returns:
            List of example query dictionaries
        """
        return [
            {
                "query": "List all my databases",
                "description": "Shows all databases the integration can access"
            },
            {
                "query": "Find pages about [topic]",
                "description": "Search for pages containing specific keywords"
            },
            {
                "query": "Create a new page in [database]",
                "description": "Add a new entry to a database"
            },
            {
                "query": "Update page titled [name]",
                "description": "Edit an existing page's content"
            },
            {
                "query": "Show recent changes",
                "description": "List recently edited pages and databases"
            }
        ]

    def configure_default_database(self, database_name: str, database_id: str) -> Dict[str, Any]:
        """Configure default database for Ralph operations.

        Args:
            database_name: Database name (e.g., "Tasks")
            database_id: Database ID (UUID)

        Returns:
            Configuration dictionary
        """
        config = {
            "default_database": {
                "name": database_name,
                "id": database_id
            },
            "auto_logging": {
                "build_started": True,
                "build_completed": True,
                "task_completed": True,
                "blocker_logged": True
            },
            "page_template": {
                "properties": {
                    "Name": {"title": [{"text": {"content": ""}}]},
                    "Status": {"select": {"name": "In Progress"}},
                    "Created": {"date": {"start": ""}}
                }
            },
            "ralph_tip": f"Ralph will log work to '{database_name}' database!"
        }
        return config

    def get_setup_summary(self) -> Dict[str, Any]:
        """Get complete setup summary and checklist.

        Returns:
            Dictionary with setup checklist and status
        """
        return {
            "title": "Notion MCP Setup Checklist",
            "steps": [
                {
                    "id": "create_integration",
                    "title": "Create Notion Integration",
                    "status": "pending",
                    "action": "Visit notion.so/my-integrations"
                },
                {
                    "id": "configure_capabilities",
                    "title": "Enable Required Capabilities",
                    "status": "pending",
                    "action": "Turn on Read, Update, and Insert content"
                },
                {
                    "id": "copy_token",
                    "title": "Copy Integration Token",
                    "status": "pending",
                    "action": "Save secret_ token securely"
                },
                {
                    "id": "share_pages",
                    "title": "Share Pages with Integration",
                    "status": "pending",
                    "action": "Add integration to pages/databases"
                },
                {
                    "id": "install_mcp",
                    "title": "Install Notion MCP Server",
                    "status": "pending",
                    "action": "Run npx command"
                },
                {
                    "id": "test_connection",
                    "title": "Test Connection",
                    "status": "pending",
                    "action": "Verify API access"
                },
                {
                    "id": "configure_database",
                    "title": "Set Default Database (Optional)",
                    "status": "pending",
                    "action": "Choose database for auto-logging"
                }
            ],
            "estimated_time": "10-15 minutes",
            "difficulty": "Medium",
            "ralph_encouragement": "Notion is super cool! Ralph can write down all the smart things the workers do!"
        }

    def verify_connection(self) -> Tuple[bool, str]:
        """Verify Notion MCP server is ready to use.

        Returns:
            Tuple of (success, message)
        """
        token_ok, token_msg = self.check_notion_token_configured()
        server_ok, server_msg = self.check_mcp_server_installed()

        if not token_ok:
            return False, f"Token not configured: {token_msg}"
        if not server_ok:
            return False, f"Server not ready: {server_msg}"

        return True, "✅ Notion MCP server is ready!"

    def get_available_actions(self) -> Dict[str, list]:
        """Get list of available actions with Notion MCP.

        Returns:
            Dictionary with categorized actions
        """
        return {
            "Reading": [
                "List databases",
                "List pages",
                "Read page content",
                "Search pages and databases",
                "Get database schema"
            ],
            "Writing": [
                "Create new pages",
                "Update page content",
                "Add database entries",
                "Update database properties",
                "Archive pages"
            ],
            "Organization": [
                "Create databases",
                "Configure page templates",
                "Set up auto-logging",
                "Organize by tags/properties"
            ]
        }

    def format_setup_guide(self) -> str:
        """Get formatted setup guide for display.

        Returns:
            Formatted markdown guide
        """
        summary = self.get_setup_summary()
        guide = f"**{summary['title']}**\n\n"
        guide += f"⏱️ Estimated time: {summary['estimated_time']}\n"
        guide += f"🎯 Difficulty: {summary['difficulty']}\n\n"
        guide += f"💡 {summary['ralph_encouragement']}\n\n"
        guide += "**Steps:**\n"
        for step in summary['steps']:
            status_icon = "⬜" if step['status'] == "pending" else "✅"
            guide += f"{status_icon} {step['title']}\n"
            guide += f"   → {step['action']}\n\n"

        return guide


def get_notion_mcp_setup() -> NotionMCPSetup:
    """Factory function to get NotionMCPSetup instance.

    Returns:
        NotionMCPSetup instance
    """
    return NotionMCPSetup()
