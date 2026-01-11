#!/usr/bin/env python3
"""
MCP Server Manager

Provides browsing, searching, and installation helpers for MCP servers.
Builds on mcp_explainer.py to add interactive features.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from mcp_explainer import get_mcp_explainer

# Import GitHub MCP setup helper (OB-018)
try:
    from github_mcp_setup import get_github_mcp_setup
    GITHUB_MCP_AVAILABLE = True
except ImportError:
    GITHUB_MCP_AVAILABLE = False
    logging.warning("GitHub MCP setup helper not available")


class MCPManager:
    """Manages MCP server browsing and installation."""

    def __init__(self):
        """Initialize the MCP manager."""
        self.logger = logging.getLogger(__name__)
        self.explainer = get_mcp_explainer()

        # Extended server catalog with install commands
        self.server_catalog = self._build_server_catalog()

        # Initialize GitHub MCP setup helper (OB-018)
        if GITHUB_MCP_AVAILABLE:
            self.github_setup = get_github_mcp_setup()
        else:
            self.github_setup = None

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
