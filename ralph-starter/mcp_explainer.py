#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Explainer

Provides simple explanations of MCP for Ralph Mode onboarding.
Makes the technical stuff accessible and fun!
"""

import logging
from typing import Dict, Any, Optional


class MCPExplainer:
    """Explains MCP concepts in simple, fun terms."""

    def __init__(self):
        """Initialize the MCP explainer."""
        self.logger = logging.getLogger(__name__)

    def get_mcp_explainer_message(self) -> str:
        """Get the main MCP explanation message.

        Returns:
            MCP explanation in Ralph's style
        """
        return """*What's MCP? (Model Context Protocol)* 🔌

Me Ralph! Me explain MCP to you!

**The Simple Version:**
MCP is like giving Claude Code superpowers! 🦸

Think of it like this:
→ Claude Code = smartphone 📱
→ MCP servers = apps you install 📲
→ Each app gives Claude new abilities! ✨

**Real-World Analogy:**
Remember browser extensions? MCP is like that!
→ Want Claude to read your GitHub repos? Install GitHub MCP server!
→ Want Claude to query databases? Install Postgres MCP server!
→ Want Claude to manage Slack? Install Slack MCP server!

**What MCP Enables:**

1. **Database Access** 🗄️
   → Claude can read/write to PostgreSQL, MySQL, SQLite
   → Query your production data safely
   → Generate reports and insights

2. **API Integrations** 🌐
   → GitHub: read repos, create PRs, manage issues
   → Slack: send messages, read channels
   → Discord: manage servers, send notifications
   → Notion: read/write pages and databases

3. **File System Tools** 📂
   → Read local files beyond the project
   → Access documentation folders
   → Search across multiple repos

4. **Custom Tools** 🛠️
   → Build your own MCP servers
   → Give Claude company-specific abilities
   → Integrate with internal tools

**Why It Matters:**

Without MCP:
❌ Claude is stuck in the project folder
❌ Can't access external systems
❌ Limited to basic file operations

With MCP:
✅ Claude can access your entire stack
✅ Automate complex workflows
✅ Build features that touch multiple systems
✅ Ralph can actually ship real features! 🚢

**Official Resources:**

📖 **MCP Docs:** https://modelcontextprotocol.io/
🎥 **Video Tutorial:** https://www.youtube.com/watch?v=8lik7EJBAH4
💻 **GitHub:** https://github.com/modelcontextprotocol
🔧 **Server Gallery:** https://github.com/modelcontextprotocol/servers

**Ralph's Take:**

"MCP make Claude Code go from toy car to race car! 🏎️
Me Ralph can do SO MUCH MORE with MCP servers!
Is like getting cheat codes for coding! Unpossible became possible!"

Ready to install some MCP servers and supercharge Ralph? 💪"""

    def get_mcp_quick_explainer(self) -> str:
        """Get a quick 2-sentence explanation.

        Returns:
            Quick MCP summary
        """
        return """*MCP in 2 Sentences:*

MCP (Model Context Protocol) lets Claude Code connect to external systems like GitHub, databases, and APIs. Think of it as installing apps on your phone - each MCP server gives Claude new superpowers! 🦸"""

    def get_mcp_server_categories(self) -> Dict[str, list]:
        """Get categorized list of popular MCP servers.

        Returns:
            Dictionary of categories and their servers
        """
        return {
            "Database": [
                {
                    "name": "PostgreSQL",
                    "description": "Connect to PostgreSQL databases",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres"
                },
                {
                    "name": "SQLite",
                    "description": "Query SQLite databases",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite"
                },
                {
                    "name": "MySQL",
                    "description": "Connect to MySQL databases",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/mysql"
                }
            ],
            "Development": [
                {
                    "name": "GitHub",
                    "description": "Manage repos, PRs, issues",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/github"
                },
                {
                    "name": "Git",
                    "description": "Advanced git operations",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/git"
                },
                {
                    "name": "Docker",
                    "description": "Manage containers",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/docker"
                }
            ],
            "Productivity": [
                {
                    "name": "Slack",
                    "description": "Send messages, read channels",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/slack"
                },
                {
                    "name": "Discord",
                    "description": "Manage Discord servers",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/discord"
                },
                {
                    "name": "Notion",
                    "description": "Read/write Notion pages",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/notion"
                }
            ],
            "File System": [
                {
                    "name": "File System",
                    "description": "Read/write files outside project",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem"
                },
                {
                    "name": "Grep",
                    "description": "Search across files",
                    "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/grep"
                }
            ]
        }

    def get_mcp_benefits_list(self) -> list:
        """Get list of key MCP benefits.

        Returns:
            List of benefit descriptions
        """
        return [
            "🔗 **Connect Anything**: GitHub, databases, APIs, file systems",
            "🤖 **Automate Workflows**: Let Claude handle multi-system tasks",
            "🏗️ **Build Real Features**: Not just toy demos, production-ready code",
            "🔧 **Customize Claude**: Add your own tools and integrations",
            "📦 **Pre-built Servers**: 40+ ready-to-use MCP servers available",
            "🔒 **Secure**: Full control over what Claude can access",
            "🚀 **Ship Faster**: Ralph can do more with less manual work"
        ]

    def get_mcp_use_cases(self) -> Dict[str, str]:
        """Get common MCP use cases with examples.

        Returns:
            Dictionary of use case titles and descriptions
        """
        return {
            "Database-Driven Features": """
Ralph can build features that read/write to your database:
→ User dashboards pulling real data
→ Admin panels with live stats
→ Report generators
→ Data migration scripts
""",
            "GitHub Automation": """
Ralph can manage your entire GitHub workflow:
→ Create PRs automatically
→ Label and assign issues
→ Update documentation
→ Close stale issues
""",
            "Multi-Service Features": """
Ralph can build features across multiple systems:
→ Slack notification when GitHub PR is merged
→ Database backup to cloud storage
→ Sync Notion docs with GitHub wiki
→ Discord alerts for production errors
""",
            "Company-Specific Tools": """
Build custom MCP servers for your company:
→ Internal API access
→ Custom deployment tools
→ Proprietary data sources
→ Company workflow automation
"""
        }


# Singleton instance
_mcp_explainer_instance = None


def get_mcp_explainer() -> MCPExplainer:
    """Get the singleton MCP explainer instance.

    Returns:
        MCPExplainer instance
    """
    global _mcp_explainer_instance
    if _mcp_explainer_instance is None:
        _mcp_explainer_instance = MCPExplainer()
    return _mcp_explainer_instance
