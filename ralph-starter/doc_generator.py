#!/usr/bin/env python3
"""
Documentation Generator for Ralph Mode Onboarding - OB-050

Generates customized README.md and documentation based on user's setup configuration.
Includes configured services, custom commands, getting started instructions,
and troubleshooting specific to their config.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class DocGenerator:
    """Generates customized documentation based on user's setup configuration."""

    def __init__(self):
        """Initialize the documentation generator."""
        self.logger = logging.getLogger(__name__)

    def generate_readme(self, state: Dict[str, Any], project_name: str = "Ralph Mode Project") -> str:
        """Generate a customized README.md based on setup state.

        Args:
            state: Onboarding state dictionary with user's configuration
            project_name: Name of the user's project

        Returns:
            Generated README.md content as string
        """
        sections = []

        # Header
        sections.append(self._generate_header(project_name, state))

        # Quick Start (based on their config)
        sections.append(self._generate_quick_start(state))

        # Configuration Summary
        sections.append(self._generate_config_summary(state))

        # Custom Commands
        sections.append(self._generate_custom_commands(state))

        # Troubleshooting
        sections.append(self._generate_troubleshooting(state))

        # Additional Resources
        sections.append(self._generate_resources())

        # Footer
        sections.append(self._generate_footer())

        return "\n\n".join(sections)

    def _generate_header(self, project_name: str, state: Dict[str, Any]) -> str:
        """Generate README header section."""
        repo_url = state.get("repo_url", "")
        repo_name = self._extract_repo_name(repo_url)

        header = f"# {project_name}\n\n"
        header += "**Your AI Dev Team, Live on Stage**\n\n"
        header += "This project uses Ralph Mode - a Telegram bot that turns AI development into an immersive theatrical experience.\n\n"

        if repo_url:
            header += f"**Repository**: [{repo_name}]({repo_url})\n"

        setup_type = state.get("setup_type", "guided")
        header += f"**Setup Type**: {setup_type.capitalize()}\n"

        setup_date = state.get("completed_at") or state.get("started_at")
        if setup_date:
            if isinstance(setup_date, str):
                try:
                    date_obj = datetime.fromisoformat(setup_date)
                    header += f"**Setup Date**: {date_obj.strftime('%B %d, %Y')}\n"
                except:
                    pass

        return header

    def _generate_quick_start(self, state: Dict[str, Any]) -> str:
        """Generate Quick Start section based on user's configuration."""
        section = "## Quick Start\n\n"

        # Environment setup
        section += "### 1. Environment Setup\n\n"
        section += "Your environment file (`.env`) should contain:\n\n"
        section += "```bash\n"

        env_vars = []
        env_vars.append("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        env_vars.append("GROQ_API_KEY=your_groq_api_key_here")
        env_vars.append("OWNER_TELEGRAM_ID=your_telegram_id_here")

        # Add optional services if configured
        if state.get("groq_configured"):
            env_vars.append("# Groq API configured for AI responses")
        if state.get("openweather_configured"):
            env_vars.append("OPENWEATHER_API_KEY=your_openweather_key_here")
            env_vars.append("# Optional: Weather integration for scene setting")

        section += "\n".join(env_vars)
        section += "\n```\n\n"

        # Git configuration
        if state.get("git_configured"):
            git_name = state.get("git_name", "Your Name")
            git_email = state.get("git_email", "your.email@example.com")
            section += "### 2. Git Configuration\n\n"
            section += "Your git is configured with:\n\n"
            section += f"- **Name**: {git_name}\n"
            section += f"- **Email**: {git_email}\n\n"

        # SSH setup
        if state.get("ssh_key_generated"):
            section += "### 3. SSH Key\n\n"
            if state.get("ssh_key_added_to_github"):
                section += "✅ SSH key generated and added to GitHub\n\n"
                section += "You can verify with:\n\n"
                section += "```bash\n"
                section += "ssh -T git@github.com\n"
                section += "```\n\n"
            else:
                section += "⚠️ SSH key generated but not yet added to GitHub\n\n"

        # Repository
        if state.get("repo_created"):
            repo_url = state.get("repo_url")
            section += "### 4. Repository\n\n"
            section += f"Your repository is set up at:\n\n"
            section += f"```\n{repo_url}\n```\n\n"

        # Running the bot
        section += "### 5. Run the Bot\n\n"
        section += "```bash\n"
        section += "# Create virtual environment (if not already done)\n"
        section += "python3 -m venv venv\n"
        section += "source venv/bin/activate  # On Windows: venv\\Scripts\\activate\n\n"
        section += "# Install dependencies\n"
        section += "pip install -r requirements.txt\n\n"
        section += "# Run the bot\n"
        section += "python ralph_bot.py\n"
        section += "```\n"

        return section

    def _generate_config_summary(self, state: Dict[str, Any]) -> str:
        """Generate configuration summary section."""
        section = "## Your Configuration\n\n"

        configured_items = []
        pending_items = []

        # Check each configuration item
        configs = [
            ("ssh_key_generated", "✅ SSH Key Generated", "⬜ SSH Key Not Generated"),
            ("ssh_key_added_to_github", "✅ SSH Key Added to GitHub", "⬜ SSH Key Not Added to GitHub"),
            ("repo_created", "✅ Repository Created", "⬜ Repository Not Created"),
            ("git_configured", "✅ Git Configured", "⬜ Git Not Configured"),
            ("environment_setup", "✅ Environment Variables Set", "⬜ Environment Variables Pending"),
            ("first_commit", "✅ First Commit Made", "⬜ First Commit Pending"),
        ]

        for key, done_msg, pending_msg in configs:
            if state.get(key):
                configured_items.append(done_msg)
            else:
                pending_items.append(pending_msg)

        if configured_items:
            section += "### Configured Services\n\n"
            section += "\n".join(configured_items) + "\n\n"

        if pending_items:
            section += "### Pending Setup\n\n"
            section += "\n".join(pending_items) + "\n\n"

        return section

    def _generate_custom_commands(self, state: Dict[str, Any]) -> str:
        """Generate custom commands section based on user's setup."""
        section = "## Commands & Usage\n\n"

        # Basic commands
        section += "### Basic Commands\n\n"
        section += "| Command | Description |\n"
        section += "|---------|-------------|\n"
        section += "| `/start` | Start a new session with Ralph |\n"
        section += "| `/setup` | Run the onboarding wizard |\n"
        section += "| `/help` | Show help and available commands |\n"
        section += "| `/status` | Check bot status and configuration |\n\n"

        # Voice-only mode
        section += "### Voice-Only Mode\n\n"
        section += "Ralph Mode uses **voice-only input** for full immersion:\n\n"
        section += "1. Record a voice message in Telegram\n"
        section += "2. Send it to the bot\n"
        section += "3. Your speech becomes theatrical dialogue\n"
        section += "4. Watch the team respond in character\n\n"

        # Git workflow commands (if configured)
        if state.get("git_configured") and state.get("repo_created"):
            section += "### Git Workflow\n\n"
            section += "```bash\n"
            section += "# Check status\n"
            section += "git status\n\n"
            section += "# Pull latest changes\n"
            section += "git pull origin main\n\n"
            section += "# Push your changes\n"
            section += "git add .\n"
            section += "git commit -m \"Your message\"\n"
            section += "git push origin main\n"
            section += "```\n\n"

        # Advanced commands
        section += "### Advanced Commands\n\n"
        section += "| Command | Description |\n"
        section += "|---------|-------------|\n"
        section += "| `/reorganize` | Re-cluster PRD tasks for optimal order |\n"
        section += "| `/feedback` | Submit feedback to improve Ralph |\n"
        section += "| `Admin commands` | Speak \"admin command: [action]\" for hidden admin actions |\n\n"

        return section

    def _generate_troubleshooting(self, state: Dict[str, Any]) -> str:
        """Generate troubleshooting section specific to user's configuration."""
        section = "## Troubleshooting\n\n"

        # SSH-specific troubleshooting
        if state.get("ssh_key_generated"):
            section += "### SSH Connection Issues\n\n"
            section += "If you get SSH permission denied:\n\n"
            section += "```bash\n"
            section += "# Test SSH connection\n"
            section += "ssh -T git@github.com\n\n"
            section += "# Check if SSH key is loaded\n"
            section += "ssh-add -l\n\n"
            section += "# Add your SSH key to the agent\n"
            section += "ssh-add ~/.ssh/id_ed25519\n"
            section += "```\n\n"

        # Git-specific troubleshooting
        if state.get("git_configured"):
            section += "### Git Issues\n\n"
            section += "**Problem**: Git asks for username/password\n\n"
            section += "**Solution**: Make sure you're using SSH URL, not HTTPS:\n\n"
            section += "```bash\n"
            section += "# Check current remote\n"
            section += "git remote -v\n\n"
            section += "# Change to SSH if needed\n"
            git_name = state.get("git_name", "Your Name")
            git_email = state.get("git_email", "your.email@example.com")
            section += f"# Your configured git: {git_name} <{git_email}>\n"
            section += "```\n\n"

        # Repository-specific troubleshooting
        if state.get("repo_created"):
            repo_url = state.get("repo_url", "")
            section += "### Repository Issues\n\n"
            section += "**Problem**: Can't push to repository\n\n"
            section += "**Solution**: Verify repository permissions\n\n"
            section += "```bash\n"
            section += f"# Your repository: {repo_url}\n\n"
            section += "# Check remote configuration\n"
            section += "git remote -v\n\n"
            section += "# Verify you have write access\n"
            section += "# Make sure you're logged into GitHub with the right account\n"
            section += "```\n\n"

        # Bot-specific troubleshooting
        section += "### Bot Not Responding\n\n"
        section += "1. **Check bot is running**: `ps aux | grep ralph_bot`\n"
        section += "2. **Check logs**: Look for errors in console output\n"
        section += "3. **Verify API keys**: Make sure `.env` file has correct tokens\n"
        section += "4. **Restart bot**: Stop and restart `python ralph_bot.py`\n\n"

        # Environment-specific troubleshooting
        section += "### Environment Variables\n\n"
        section += "**Problem**: Bot can't find API keys\n\n"
        section += "**Solution**: \n\n"
        section += "```bash\n"
        section += "# Check .env file exists\n"
        section += "ls -la .env\n\n"
        section += "# Verify it has the required variables\n"
        section += "cat .env\n\n"
        section += "# Make sure you're in the right directory\n"
        section += "pwd\n"
        section += "```\n\n"

        # General troubleshooting
        section += "### General Tips\n\n"
        section += "- **Check Python version**: Ralph Mode requires Python 3.8+\n"
        section += "- **Virtual environment**: Always activate venv before running\n"
        section += "- **Dependencies**: Run `pip install -r requirements.txt` if you get import errors\n"
        section += "- **Permissions**: Make sure you have write permissions in the project directory\n\n"

        return section

    def _generate_resources(self) -> str:
        """Generate additional resources section."""
        section = "## Additional Resources\n\n"
        section += "### Documentation\n\n"
        section += "- [Ralph Mode GitHub](https://github.com/Snail3D/ralphmode.com)\n"
        section += "- [Ralph Pattern Original](https://github.com/snarktank/ralph)\n"
        section += "- [Claude Code Docs](https://docs.anthropic.com/claude-code)\n"
        section += "- [Groq API Docs](https://console.groq.com/docs)\n\n"

        section += "### Community & Support\n\n"
        section += "- **Questions**: Create an issue on GitHub\n"
        section += "- **Feature Requests**: Submit via `/feedback` in the bot\n"
        section += "- **Contributing**: See CONTRIBUTING.md\n\n"

        section += "### Credits\n\n"
        section += "- Ralph Pattern by [Geoffrey Huntley](https://ghuntley.com)\n"
        section += "- Popularized by [Ryan Carson](https://x.com/ryancarson)\n"
        section += "- Built with [Claude Code](https://claude.com/claude-code)\n"
        section += "- Powered by [Groq](https://groq.com)\n\n"

        return section

    def _generate_footer(self) -> str:
        """Generate README footer."""
        footer = "---\n\n"
        footer += "*Your AI dev team, live on stage.*\n\n"
        footer += f"*Generated by Ralph Mode on {datetime.now().strftime('%B %d, %Y')}*\n"
        return footer

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Repository name (e.g., 'user/repo')
        """
        if not repo_url:
            return ""

        # Handle different URL formats
        # git@github.com:user/repo.git
        # https://github.com/user/repo.git
        # https://github.com/user/repo

        if "github.com" in repo_url:
            parts = repo_url.split("github.com")[-1]
            parts = parts.strip("/:").rstrip(".git")
            return parts

        return repo_url

    def save_readme(self, content: str, file_path: str = "README.md") -> bool:
        """Save generated README to file.

        Args:
            content: README content to save
            file_path: Path where to save the README

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            self.logger.info(f"OB-050: Saved README to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"OB-050: Error saving README: {e}")
            return False

    def generate_getting_started_guide(self, state: Dict[str, Any]) -> str:
        """Generate a separate getting started guide for new users.

        Args:
            state: Onboarding state dictionary

        Returns:
            Getting started guide content
        """
        guide = "# Getting Started with Ralph Mode\n\n"
        guide += "Welcome! Here's everything you need to get up and running.\n\n"

        # Step-by-step based on what's configured
        guide += "## Setup Checklist\n\n"

        steps = []

        if state.get("ssh_key_generated"):
            steps.append("✅ SSH key generated")
        else:
            steps.append("⬜ Generate SSH key")

        if state.get("ssh_key_added_to_github"):
            steps.append("✅ SSH key added to GitHub")
        else:
            steps.append("⬜ Add SSH key to GitHub")

        if state.get("repo_created"):
            steps.append("✅ Repository created")
        else:
            steps.append("⬜ Create repository")

        if state.get("git_configured"):
            steps.append("✅ Git configured")
        else:
            steps.append("⬜ Configure Git")

        if state.get("environment_setup"):
            steps.append("✅ Environment variables set")
        else:
            steps.append("⬜ Set environment variables")

        guide += "\n".join(steps) + "\n\n"

        # Next steps
        guide += "## Next Steps\n\n"

        if not state.get("first_commit"):
            guide += "### Make Your First Commit\n\n"
            guide += "```bash\n"
            guide += "# Create a test file\n"
            guide += "echo 'Hello Ralph!' > test.txt\n\n"
            guide += "# Commit it\n"
            guide += "git add test.txt\n"
            guide += "git commit -m 'First commit with Ralph'\n"
            guide += "git push origin main\n"
            guide += "```\n\n"

        guide += "### Start Using Ralph\n\n"
        guide += "1. Open Telegram and find your bot\n"
        guide += "2. Send `/start`\n"
        guide += "3. Send a voice message with your instructions\n"
        guide += "4. Watch the magic happen!\n\n"

        return guide


def get_doc_generator() -> DocGenerator:
    """Get the documentation generator instance.

    Returns:
        DocGenerator instance
    """
    return DocGenerator()
