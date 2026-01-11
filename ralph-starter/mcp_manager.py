#!/usr/bin/env python3
"""
MCP Server Manager

Provides browsing, searching, and installation helpers for MCP servers.
Builds on mcp_explainer.py to add interactive features.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from mcp_explainer import get_mcp_explainer

# Import MCP Health Checker (OB-021)
try:
    from health_check import get_health_checker
    HEALTH_CHECK_AVAILABLE = True
except ImportError:
    HEALTH_CHECK_AVAILABLE = False
    logging.warning("MCP health check system not available")

# Import GitHub MCP setup helper (OB-018)
try:
    from github_mcp_setup import get_github_mcp_setup
    GITHUB_MCP_AVAILABLE = True
except ImportError:
    GITHUB_MCP_AVAILABLE = False
    logging.warning("GitHub MCP setup helper not available")

# Import Slack MCP setup helper (OB-043)
try:
    from slack_mcp_setup import get_slack_mcp_setup
    SLACK_MCP_AVAILABLE = True
except ImportError:
    SLACK_MCP_AVAILABLE = False
    logging.warning("Slack MCP setup helper not available")

# Import Discord MCP setup helper (OB-044)
try:
    from discord_mcp_setup import get_discord_mcp_setup
    DISCORD_MCP_AVAILABLE = True
except ImportError:
    DISCORD_MCP_AVAILABLE = False
    logging.warning("Discord MCP setup helper not available")

# Import Notion MCP setup helper (OB-045)
try:
    from notion_mcp_setup import get_notion_mcp_setup
    NOTION_MCP_AVAILABLE = True
except ImportError:
    NOTION_MCP_AVAILABLE = False
    logging.warning("Notion MCP setup helper not available")

# Import Database MCP setup helper (OB-019)
try:
    from database_mcp_setup import get_database_mcp_setup
    DATABASE_MCP_AVAILABLE = True
except ImportError:
    DATABASE_MCP_AVAILABLE = False
    logging.warning("Database MCP setup helper not available")


class MCPManager:
    """Manages MCP server browsing and installation."""

    def __init__(self):
        """Initialize the MCP manager."""
        self.logger = logging.getLogger(__name__)
        self.explainer = get_mcp_explainer()

        # Extended server catalog with install commands
        self.server_catalog = self._build_server_catalog()

        # Initialize MCP Health Checker (OB-021)
        if HEALTH_CHECK_AVAILABLE:
            self.health_checker = get_health_checker()
        else:
            self.health_checker = None

        # Initialize GitHub MCP setup helper (OB-018)
        if GITHUB_MCP_AVAILABLE:
            self.github_setup = get_github_mcp_setup()
        else:
            self.github_setup = None

        # Initialize Slack MCP setup helper (OB-043)
        if SLACK_MCP_AVAILABLE:
            self.slack_setup = get_slack_mcp_setup()
        else:
            self.slack_setup = None

        # Initialize Discord MCP setup helper (OB-044)
        if DISCORD_MCP_AVAILABLE:
            self.discord_setup = get_discord_mcp_setup()
        else:
            self.discord_setup = None

        # Initialize Notion MCP setup helper (OB-045)
        if NOTION_MCP_AVAILABLE:
            self.notion_setup = get_notion_mcp_setup()
        else:
            self.notion_setup = None

        # Initialize Database MCP setup helper (OB-019)
        if DATABASE_MCP_AVAILABLE:
            self.database_setup = get_database_mcp_setup()
        else:
            self.database_setup = None

    def _build_server_catalog(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build comprehensive server catalog with installation info.

        Returns:
            Dictionary of categories with server details
        """
        # Get base catalog from explainer
        base_catalog = self.explainer.get_mcp_server_categories()

        # Enhance with installation commands and additional metadata
        enhanced_catalog = {}

        for category, servers in base_catalog.items():
            enhanced_servers = []
            for server in servers:
                enhanced_server = {
                    **server,
                    "install_cmd": self._get_install_command(server["name"]),
                    "setup_required": self._requires_setup(server["name"]),
                    "difficulty": self._get_difficulty(server["name"]),
                    "tags": self._get_tags(server["name"])
                }
                enhanced_servers.append(enhanced_server)
            enhanced_catalog[category] = enhanced_servers

        return enhanced_catalog

    def _get_install_command(self, server_name: str) -> str:
        """Get installation command for a server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Installation command
        """
        # Simplified install commands (actual commands may vary)
        install_map = {
            "PostgreSQL": "npx -y @modelcontextprotocol/server-postgres",
            "SQLite": "npx -y @modelcontextprotocol/server-sqlite",
            "MySQL": "npx -y @modelcontextprotocol/server-mysql",
            "GitHub": "npx -y @modelcontextprotocol/server-github",
            "Git": "npx -y @modelcontextprotocol/server-git",
            "Docker": "npx -y @modelcontextprotocol/server-docker",
            "Slack": "npx -y @modelcontextprotocol/server-slack",
            "Discord": "npx -y @modelcontextprotocol/server-discord",
            "Notion": "npx -y @modelcontextprotocol/server-notion",
            "File System": "npx -y @modelcontextprotocol/server-filesystem",
            "Grep": "npx -y @modelcontextprotocol/server-grep"
        }
        return install_map.get(server_name, f"# See docs for {server_name}")

    def _requires_setup(self, server_name: str) -> bool:
        """Check if server requires additional setup/credentials.

        Args:
            server_name: Name of the MCP server

        Returns:
            True if setup required
        """
        # Servers that need API keys or credentials
        needs_setup = {"GitHub", "Slack", "Discord", "Notion", "PostgreSQL", "MySQL"}
        return server_name in needs_setup

    def _get_difficulty(self, server_name: str) -> str:
        """Get difficulty level for server setup.

        Args:
            server_name: Name of the MCP server

        Returns:
            Difficulty level: "Easy", "Medium", "Advanced"
        """
        easy = {"File System", "Grep", "SQLite", "Git"}
        advanced = {"Docker", "PostgreSQL", "MySQL"}

        if server_name in easy:
            return "Easy"
        elif server_name in advanced:
            return "Advanced"
        else:
            return "Medium"

    def _get_tags(self, server_name: str) -> List[str]:
        """Get tags for a server.

        Args:
            server_name: Name of the MCP server

        Returns:
            List of tags
        """
        tag_map = {
            "PostgreSQL": ["database", "sql", "production"],
            "SQLite": ["database", "sql", "beginner-friendly"],
            "MySQL": ["database", "sql", "production"],
            "GitHub": ["git", "api", "popular", "requires-token"],
            "Git": ["git", "beginner-friendly"],
            "Docker": ["containers", "devops"],
            "Slack": ["communication", "api", "requires-token"],
            "Discord": ["communication", "api", "requires-token"],
            "Notion": ["productivity", "api", "requires-token"],
            "File System": ["files", "beginner-friendly"],
            "Grep": ["search", "beginner-friendly"]
        }
        return tag_map.get(server_name, [])

    def get_all_servers(self) -> List[Dict[str, Any]]:
        """Get flat list of all servers across categories.

        Returns:
            List of all server dictionaries
        """
        all_servers = []
        for servers in self.server_catalog.values():
            all_servers.extend(servers)
        return all_servers

    def search_servers(self, query: str) -> List[Dict[str, Any]]:
        """Search servers by name, description, or tags.

        Args:
            query: Search query string

        Returns:
            List of matching servers
        """
        query_lower = query.lower()
        results = []

        for server in self.get_all_servers():
            # Search in name
            if query_lower in server["name"].lower():
                results.append(server)
                continue

            # Search in description
            if query_lower in server["description"].lower():
                results.append(server)
                continue

            # Search in tags
            if any(query_lower in tag for tag in server.get("tags", [])):
                results.append(server)
                continue

        return results

    def filter_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        """Filter servers by difficulty level.

        Args:
            difficulty: "Easy", "Medium", or "Advanced"

        Returns:
            List of servers matching difficulty
        """
        return [
            server for server in self.get_all_servers()
            if server.get("difficulty") == difficulty
        ]

    def filter_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get servers in a specific category.

        Args:
            category: Category name (Database, Development, Productivity, File System)

        Returns:
            List of servers in category
        """
        return self.server_catalog.get(category, [])

    def get_beginner_friendly_servers(self) -> List[Dict[str, Any]]:
        """Get list of beginner-friendly servers.

        Returns:
            List of easy-to-setup servers
        """
        return [
            server for server in self.get_all_servers()
            if "beginner-friendly" in server.get("tags", [])
        ]

    def get_server_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get server details by name.

        Args:
            name: Server name

        Returns:
            Server dictionary or None if not found
        """
        for server in self.get_all_servers():
            if server["name"].lower() == name.lower():
                return server
        return None

    def format_server_card(self, server: Dict[str, Any]) -> str:
        """Format a server as a display card.

        Args:
            server: Server dictionary

        Returns:
            Formatted string for display
        """
        setup_badge = "🔑 Setup Required" if server.get("setup_required") else "✅ Ready to Use"
        difficulty = server.get("difficulty", "Medium")
        difficulty_emoji = {"Easy": "🟢", "Medium": "🟡", "Advanced": "🔴"}.get(difficulty, "⚪")

        tags = " ".join([f"`{tag}`" for tag in server.get("tags", [])[:3]])

        card = f"""**{server['name']}**
{server['description']}

{difficulty_emoji} {difficulty} | {setup_badge}
{tags}

📦 Install: `{server.get('install_cmd', 'See docs')}`
🔗 [Docs]({server['url']})"""

        return card

    def format_category_overview(self, category: str) -> str:
        """Format all servers in a category.

        Args:
            category: Category name

        Returns:
            Formatted category overview
        """
        servers = self.filter_by_category(category)

        if not servers:
            return f"No servers found in {category}"

        overview = f"**{category} MCP Servers** ({len(servers)} available)\n\n"

        for i, server in enumerate(servers, 1):
            difficulty_emoji = {"Easy": "🟢", "Medium": "🟡", "Advanced": "🔴"}.get(
                server.get("difficulty", "Medium"), "⚪"
            )
            setup_icon = "🔑" if server.get("setup_required") else "✅"

            overview += f"{i}. {difficulty_emoji} {setup_icon} **{server['name']}**\n"
            overview += f"   _{server['description']}_\n\n"

        return overview

    def get_popular_servers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get list of most popular/recommended servers.

        Args:
            limit: Maximum number of servers to return

        Returns:
            List of popular servers
        """
        # Manually curated list of popular servers
        popular_names = ["GitHub", "PostgreSQL", "Slack", "File System", "Git"]

        popular = []
        for name in popular_names[:limit]:
            server = self.get_server_by_name(name)
            if server:
                popular.append(server)

        return popular

    def get_quick_start_recommendations(self) -> Dict[str, str]:
        """Get recommended servers for quick start.

        Returns:
            Dictionary with use case -> server recommendations
        """
        return {
            "First Timer": "Start with **Git** and **File System** - super easy, no setup needed!",
            "GitHub User": "Install **GitHub** server to let Claude manage your repos and PRs",
            "Database Developer": "Try **SQLite** first (easy), then **PostgreSQL** (production-ready)",
            "Team Collaboration": "Add **Slack** or **Discord** for team notifications",
            "Power User": "Go wild with **GitHub + PostgreSQL + Slack** for the full stack"
        }

    # OB-018: GitHub MCP Server Setup Methods

    def setup_github_mcp(self) -> Dict[str, Any]:
        """Guide through GitHub MCP server setup.

        Returns:
            Dictionary with setup status and instructions
        """
        if not self.github_setup:
            return {
                "success": False,
                "error": "GitHub MCP setup helper not available"
            }

        # Check all prerequisites
        cli_ok, cli_msg = self.github_setup.check_gh_cli_installed()
        auth_ok, username = self.github_setup.check_gh_auth_status()
        server_ok, server_msg = self.github_setup.check_mcp_server_installed()

        return {
            "github_cli": {
                "installed": cli_ok,
                "message": cli_msg
            },
            "authentication": {
                "authenticated": auth_ok,
                "username": username,
                "instructions": self.github_setup.get_auth_instructions() if not auth_ok else None
            },
            "mcp_server": {
                "ready": server_ok,
                "message": server_msg,
                "install_instructions": self.github_setup.get_install_instructions() if not server_ok else None
            },
            "all_ready": cli_ok and auth_ok and server_ok,
            "setup_guide": self.github_setup.format_setup_guide()
        }

    def verify_github_connection(self) -> Tuple[bool, str]:
        """Verify GitHub MCP server is ready to use.

        Returns:
            Tuple of (success, message)
        """
        if not self.github_setup:
            return False, "GitHub MCP setup helper not available"

        return self.github_setup.verify_connection()

    def get_github_capabilities(self) -> Dict[str, list]:
        """Get list of GitHub MCP server capabilities.

        Returns:
            Dictionary with categorized capabilities
        """
        if not self.github_setup:
            return {}

        return self.github_setup.get_available_actions()

    def format_github_setup_guide(self) -> str:
        """Get formatted GitHub setup guide for display.

        Returns:
            Formatted markdown guide
        """
        if not self.github_setup:
            return "GitHub MCP setup helper not available"

        return self.github_setup.format_setup_guide()

    # OB-043: Slack MCP Server Setup Methods

    def setup_slack_mcp(self) -> Dict[str, Any]:
        """Guide through Slack MCP server setup.

        Returns:
            Dictionary with setup status and instructions
        """
        if not self.slack_setup:
            return {
                "success": False,
                "error": "Slack MCP setup helper not available"
            }

        # Check all prerequisites
        node_ok, node_msg = self.slack_setup.check_node_installed()
        server_ok, server_msg = self.slack_setup.check_mcp_server_installed()

        return {
            "node_js": {
                "installed": node_ok,
                "message": node_msg
            },
            "mcp_server": {
                "ready": server_ok,
                "message": server_msg,
                "install_instructions": self.slack_setup.get_install_instructions() if not server_ok else None
            },
            "slack_app": {
                "creation_guide": self.slack_setup.get_slack_app_creation_guide(),
                "oauth_guide": self.slack_setup.get_oauth_setup_guide(),
                "channel_guide": self.slack_setup.get_channel_setup_guide(),
                "workspace_id_guide": self.slack_setup.get_workspace_id_instructions()
            },
            "all_ready": node_ok and server_ok,
            "setup_guide": self.slack_setup.format_setup_guide(),
            "test_info": self.slack_setup.get_test_command()
        }

    def verify_slack_connection(self) -> Tuple[bool, str]:
        """Verify Slack MCP server is ready to use.

        Returns:
            Tuple of (success, message)
        """
        if not self.slack_setup:
            return False, "Slack MCP setup helper not available"

        return self.slack_setup.verify_connection()

    def get_slack_capabilities(self) -> Dict[str, list]:
        """Get list of Slack MCP server capabilities.

        Returns:
            Dictionary with categorized capabilities
        """
        if not self.slack_setup:
            return {}

        return self.slack_setup.get_available_actions()

    def format_slack_setup_guide(self) -> str:
        """Get formatted Slack setup guide for display.

        Returns:
            Formatted markdown guide
        """
        if not self.slack_setup:
            return "Slack MCP setup helper not available"

        return self.slack_setup.format_setup_guide()

    # OB-044: Discord MCP Server Setup Methods

    def setup_discord_mcp(self) -> Dict[str, Any]:
        """Guide through Discord MCP server setup.

        Returns:
            Dictionary with setup status and instructions
        """
        if not self.discord_setup:
            return {
                "success": False,
                "error": "Discord MCP setup helper not available"
            }

        # Check all prerequisites
        token_ok, token_msg = self.discord_setup.check_discord_token_configured()
        server_ok, server_msg = self.discord_setup.check_mcp_server_installed()

        return {
            "discord_token": {
                "configured": token_ok,
                "message": token_msg
            },
            "mcp_server": {
                "ready": server_ok,
                "message": server_msg,
                "install_instructions": self.discord_setup.get_install_instructions() if not server_ok else None
            },
            "bot_creation": {
                "creation_guide": self.discord_setup.get_bot_creation_instructions(),
                "token_guide": self.discord_setup.get_token_setup_guide()
            },
            "all_ready": token_ok and server_ok,
            "setup_guide": self.discord_setup.get_setup_summary()
        }

    def test_discord_connection(self, token: str, channel_id: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """Test Discord bot connection.

        Args:
            token: Discord bot token
            channel_id: Channel ID to test with

        Returns:
            Tuple of (success, message, response_data)
        """
        if not self.discord_setup:
            return False, "Discord MCP setup helper not available", None

        return self.discord_setup.test_discord_connection(token, channel_id)

    def list_discord_channels(self, token: str, guild_id: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List Discord channels in a guild.

        Args:
            token: Discord bot token
            guild_id: Discord server (guild) ID

        Returns:
            Tuple of (success, channels_list, error_message)
        """
        if not self.discord_setup:
            return False, [], "Discord MCP setup helper not available"

        return self.discord_setup.list_channels(token, guild_id)

    def configure_discord_channel(self, channel_name: str, channel_id: str) -> Dict[str, Any]:
        """Configure default Discord channel for notifications.

        Args:
            channel_name: Channel name
            channel_id: Channel ID

        Returns:
            Configuration dictionary
        """
        if not self.discord_setup:
            return {"error": "Discord MCP setup helper not available"}

        return self.discord_setup.configure_default_channel(channel_name, channel_id)

    def get_discord_bot_creation_guide(self) -> Dict[str, Any]:
        """Get Discord bot creation instructions.

        Returns:
            Dictionary with bot creation steps
        """
        if not self.discord_setup:
            return {"error": "Discord MCP setup helper not available"}

        return self.discord_setup.get_bot_creation_instructions()

    def format_discord_setup_guide(self) -> str:
        """Get formatted Discord setup guide for display.

        Returns:
            Formatted markdown guide
        """
        if not self.discord_setup:
            return "Discord MCP setup helper not available"

        summary = self.discord_setup.get_setup_summary()
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

    # OB-045: Notion MCP Server Setup Methods

    def setup_notion_mcp(self) -> Dict[str, Any]:
        """Guide through Notion MCP server setup.

        Returns:
            Dictionary with setup status and instructions
        """
        if not self.notion_setup:
            return {
                "success": False,
                "error": "Notion MCP setup helper not available"
            }

        # Check all prerequisites
        token_ok, token_msg = self.notion_setup.check_notion_token_configured()
        server_ok, server_msg = self.notion_setup.check_mcp_server_installed()

        return {
            "notion_token": {
                "configured": token_ok,
                "message": token_msg
            },
            "mcp_server": {
                "ready": server_ok,
                "message": server_msg,
                "install_instructions": self.notion_setup.get_install_instructions() if not server_ok else None
            },
            "integration_creation": {
                "creation_guide": self.notion_setup.get_integration_creation_instructions(),
                "page_sharing_guide": self.notion_setup.get_page_sharing_guide()
            },
            "all_ready": token_ok and server_ok,
            "setup_guide": self.notion_setup.get_setup_summary(),
            "example_queries": self.notion_setup.get_example_queries()
        }

    def test_notion_connection(self, token: str) -> Tuple[bool, str, Optional[Dict]]:
        """Test Notion integration connection.

        Args:
            token: Notion integration token

        Returns:
            Tuple of (success, message, response_data)
        """
        if not self.notion_setup:
            return False, "Notion MCP setup helper not available", None

        return self.notion_setup.test_notion_connection(token)

    def list_notion_databases(self, token: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List Notion databases accessible to integration.

        Args:
            token: Notion integration token

        Returns:
            Tuple of (success, databases_list, error_message)
        """
        if not self.notion_setup:
            return False, [], "Notion MCP setup helper not available"

        return self.notion_setup.list_databases(token)

    def list_notion_pages(self, token: str, limit: int = 10) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List Notion pages accessible to integration.

        Args:
            token: Notion integration token
            limit: Maximum number of pages to return

        Returns:
            Tuple of (success, pages_list, error_message)
        """
        if not self.notion_setup:
            return False, [], "Notion MCP setup helper not available"

        return self.notion_setup.list_pages(token, limit)

    def configure_notion_database(self, database_name: str, database_id: str) -> Dict[str, Any]:
        """Configure default Notion database for logging.

        Args:
            database_name: Database name
            database_id: Database ID (UUID)

        Returns:
            Configuration dictionary
        """
        if not self.notion_setup:
            return {"error": "Notion MCP setup helper not available"}

        return self.notion_setup.configure_default_database(database_name, database_id)

    def get_notion_integration_guide(self) -> Dict[str, Any]:
        """Get Notion integration creation instructions.

        Returns:
            Dictionary with integration creation steps
        """
        if not self.notion_setup:
            return {"error": "Notion MCP setup helper not available"}

        return self.notion_setup.get_integration_creation_instructions()

    def verify_notion_connection(self) -> Tuple[bool, str]:
        """Verify Notion MCP server is ready to use.

        Returns:
            Tuple of (success, message)
        """
        if not self.notion_setup:
            return False, "Notion MCP setup helper not available"

        return self.notion_setup.verify_connection()

    def get_notion_capabilities(self) -> Dict[str, list]:
        """Get list of Notion MCP server capabilities.

        Returns:
            Dictionary with categorized capabilities
        """
        if not self.notion_setup:
            return {}

        return self.notion_setup.get_available_actions()

    def format_notion_setup_guide(self) -> str:
        """Get formatted Notion setup guide for display.

        Returns:
            Formatted markdown guide
        """
        if not self.notion_setup:
            return "Notion MCP setup helper not available"

        return self.notion_setup.format_setup_guide()

    # OB-021: MCP Health Check System Methods

    async def check_all_mcp_servers(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all configured MCP servers.

        Returns:
            Dictionary with server health status
        """
        if not self.health_checker:
            return {
                "error": "Health check system not available"
            }

        return await self.health_checker.check_all_servers()

    async def check_mcp_server(self, server_name: str) -> Dict[str, Any]:
        """Check health of a specific MCP server.

        Args:
            server_name: Name of the server to check

        Returns:
            Dictionary with server health status
        """
        if not self.health_checker:
            return {
                "error": "Health check system not available"
            }

        return await self.health_checker.check_server(server_name)

    async def reconnect_mcp_server(self, server_name: str) -> Tuple[bool, str]:
        """Attempt to reconnect a failed MCP server.

        Args:
            server_name: Name of the server to reconnect

        Returns:
            Tuple of (success, message)
        """
        if not self.health_checker:
            return False, "Health check system not available"

        return await self.health_checker.reconnect_server(server_name)

    def get_mcp_health_summary(self) -> Dict[str, Any]:
        """Get summary of current MCP health status.

        Returns:
            Dictionary with health summary
        """
        if not self.health_checker:
            return {
                "error": "Health check system not available"
            }

        return self.health_checker.get_health_summary()

    def get_mcp_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent MCP health check history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of health check records
        """
        if not self.health_checker:
            return []

        return self.health_checker.get_health_history(limit)

    def format_mcp_health_report(self, results: Dict[str, Dict[str, Any]]) -> str:
        """Format MCP health check results as readable report.

        Args:
            results: Health check results

        Returns:
            Formatted report string
        """
        if not self.health_checker:
            return "Health check system not available"

        return self.health_checker.format_health_report(results)

    def register_mcp_health_alert(self, callback: callable):
        """Register a callback for MCP connection loss alerts.

        Args:
            callback: Function to call when connection is lost
                     Should accept (server_name, status, message)
        """
        if not self.health_checker:
            self.logger.warning("Health check system not available, cannot register alert")
            return

        self.health_checker.register_alert_callback(callback)


# Singleton instance
_mcp_manager_instance = None


def get_mcp_manager() -> MCPManager:
    """Get the singleton MCP manager instance.

    Returns:
        MCPManager instance
    """
    global _mcp_manager_instance
    if _mcp_manager_instance is None:
        _mcp_manager_instance = MCPManager()
    return _mcp_manager_instance
