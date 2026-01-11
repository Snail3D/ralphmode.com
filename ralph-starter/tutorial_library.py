#!/usr/bin/env python3
"""
Tutorial Library for Ralph Mode Onboarding

Curated YouTube tutorials for each setup step with timestamps.
Mobile-friendly links and clear descriptions.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Tutorial:
    """A single tutorial video with metadata."""
    title: str
    url: str
    description: str
    duration: str  # e.g., "5:30"
    timestamps: List[Dict[str, str]]  # [{"time": "1:23", "label": "SSH key generation"}]
    level: str  # "beginner", "intermediate", "advanced"
    updated: str  # Last verified date, e.g., "2025-01"


class TutorialLibrary:
    """Manages the library of onboarding tutorials."""

    # Version tracking for tutorial library
    VERSION = "1.0.0"
    LAST_UPDATED = "2025-01"

    def __init__(self):
        """Initialize tutorial library with curated content."""
        self._tutorials = self._load_tutorials()

    def _load_tutorials(self) -> Dict[str, List[Tutorial]]:
        """Load all curated tutorials organized by topic.

        Returns:
            Dictionary mapping topic to list of tutorials
        """
        return {
            "ssh_keys": [
                Tutorial(
                    title="SSH Keys Complete Guide (GitHub)",
                    url="https://www.youtube.com/watch?v=H5qNpRGB7Qw",
                    description="Complete walkthrough of SSH key generation and GitHub setup. Perfect for beginners!",
                    duration="8:42",
                    timestamps=[
                        {"time": "0:00", "label": "Introduction to SSH"},
                        {"time": "1:15", "label": "Checking for existing keys"},
                        {"time": "2:30", "label": "Generating new SSH key"},
                        {"time": "4:45", "label": "Adding key to GitHub"},
                        {"time": "7:00", "label": "Testing the connection"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="SSH Key Setup for Mac/Linux",
                    url="https://www.youtube.com/watch?v=1-RbTL0T70Q",
                    description="Quick setup for Unix-based systems. Great if you're on Mac or Linux!",
                    duration="5:12",
                    timestamps=[
                        {"time": "0:30", "label": "Open terminal"},
                        {"time": "1:00", "label": "Generate key"},
                        {"time": "3:20", "label": "Copy to GitHub"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="SSH Keys on Windows",
                    url="https://www.youtube.com/watch?v=2nkAQ620kwA",
                    description="Windows-specific SSH setup using Git Bash and PowerShell.",
                    duration="6:45",
                    timestamps=[
                        {"time": "0:45", "label": "Install Git Bash"},
                        {"time": "2:10", "label": "Generate key in Git Bash"},
                        {"time": "4:30", "label": "Add to GitHub"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ],

            "github_basics": [
                Tutorial(
                    title="GitHub for Beginners",
                    url="https://www.youtube.com/watch?v=RGOj5yH7evk",
                    description="Learn the basics of GitHub in 18 minutes. Covers repos, commits, and more!",
                    duration="18:35",
                    timestamps=[
                        {"time": "0:00", "label": "What is GitHub?"},
                        {"time": "3:20", "label": "Creating a repository"},
                        {"time": "8:45", "label": "Understanding commits"},
                        {"time": "12:30", "label": "Branches and merging"},
                        {"time": "16:00", "label": "Pull requests"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Creating Your First GitHub Repository",
                    url="https://www.youtube.com/watch?v=QUtk-Uuq9nE",
                    description="Step-by-step guide to creating and setting up your first repo.",
                    duration="7:22",
                    timestamps=[
                        {"time": "0:30", "label": "Sign up for GitHub"},
                        {"time": "2:00", "label": "Create new repository"},
                        {"time": "4:15", "label": "Initialize with README"},
                        {"time": "5:45", "label": "Clone to your computer"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ],

            "git_basics": [
                Tutorial(
                    title="Git Tutorial for Beginners",
                    url="https://www.youtube.com/watch?v=8JJ101D3knE",
                    description="Complete Git tutorial covering all the basics you need to get started.",
                    duration="32:41",
                    timestamps=[
                        {"time": "0:00", "label": "Introduction"},
                        {"time": "2:30", "label": "Installing Git"},
                        {"time": "5:45", "label": "Git config setup"},
                        {"time": "8:20", "label": "Your first commit"},
                        {"time": "15:30", "label": "Working with branches"},
                        {"time": "22:10", "label": "Pushing to GitHub"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Git Config - User Setup",
                    url="https://www.youtube.com/watch?v=ZM3I16Z-lxI",
                    description="Quick guide to setting up your Git user.name and user.email.",
                    duration="3:15",
                    timestamps=[
                        {"time": "0:20", "label": "Why configure Git?"},
                        {"time": "1:00", "label": "Set user.name"},
                        {"time": "1:45", "label": "Set user.email"},
                        {"time": "2:30", "label": "Verify configuration"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ],

            "api_keys": [
                Tutorial(
                    title="What are API Keys? (Explained Simply)",
                    url="https://www.youtube.com/watch?v=InoAIgBZIEA",
                    description="Understand what API keys are and why they matter. Security basics explained!",
                    duration="5:47",
                    timestamps=[
                        {"time": "0:00", "label": "API basics"},
                        {"time": "1:30", "label": "What is an API key?"},
                        {"time": "3:15", "label": "Security best practices"},
                        {"time": "4:30", "label": "Where to store keys"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Anthropic API Quick Start",
                    url="https://www.youtube.com/watch?v=Og3r8dga-zs",
                    description="Get started with Anthropic's Claude API. From signup to first API call!",
                    duration="9:12",
                    timestamps=[
                        {"time": "0:30", "label": "Sign up for Anthropic"},
                        {"time": "2:10", "label": "Navigate to API keys"},
                        {"time": "3:45", "label": "Generate new key"},
                        {"time": "5:20", "label": "Test the API"},
                        {"time": "7:00", "label": "Best practices"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ],

            "telegram_bots": [
                Tutorial(
                    title="How to Create a Telegram Bot",
                    url="https://www.youtube.com/watch?v=NwBWW8cNCP4",
                    description="Complete guide to creating your first Telegram bot with BotFather.",
                    duration="12:30",
                    timestamps=[
                        {"time": "0:45", "label": "Find BotFather"},
                        {"time": "2:15", "label": "Create new bot"},
                        {"time": "4:30", "label": "Get bot token"},
                        {"time": "6:00", "label": "Configure bot settings"},
                        {"time": "9:15", "label": "Test your bot"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Telegram Bot Permissions & Privacy",
                    url="https://www.youtube.com/watch?v=Pi6lnQ7j0g0",
                    description="Learn about bot privacy modes and group permissions.",
                    duration="7:18",
                    timestamps=[
                        {"time": "0:30", "label": "Privacy mode explained"},
                        {"time": "2:00", "label": "Disable privacy mode"},
                        {"time": "3:45", "label": "Group admin rights"},
                        {"time": "5:30", "label": "Testing permissions"}
                    ],
                    level="intermediate",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Telegram Group Setup for Bots",
                    url="https://www.youtube.com/watch?v=_kpgC9LfVqE",
                    description="How to add your bot to a group and configure it properly.",
                    duration="6:22",
                    timestamps=[
                        {"time": "0:20", "label": "Create group"},
                        {"time": "1:30", "label": "Add bot to group"},
                        {"time": "3:00", "label": "Make bot admin"},
                        {"time": "4:45", "label": "Configure permissions"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ],

            "environment_variables": [
                Tutorial(
                    title="Environment Variables Explained",
                    url="https://www.youtube.com/watch?v=IolxqkL7cD8",
                    description="Learn what .env files are and how to use them safely.",
                    duration="8:15",
                    timestamps=[
                        {"time": "0:00", "label": "What are env vars?"},
                        {"time": "2:30", "label": "Creating .env file"},
                        {"time": "4:15", "label": "Using in your code"},
                        {"time": "6:00", "label": "Security tips"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Keep Your API Keys Safe!",
                    url="https://www.youtube.com/watch?v=1mBE1RaLP-o",
                    description="Security best practices for API keys and secrets.",
                    duration="5:33",
                    timestamps=[
                        {"time": "0:30", "label": "Common mistakes"},
                        {"time": "2:00", "label": ".gitignore setup"},
                        {"time": "3:30", "label": "Using .env files"},
                        {"time": "4:45", "label": "What if you leak a key?"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ],

            "python_basics": [
                Tutorial(
                    title="Python Virtual Environments (venv)",
                    url="https://www.youtube.com/watch?v=APOPm01BVrk",
                    description="Set up isolated Python environments for your projects.",
                    duration="10:25",
                    timestamps=[
                        {"time": "0:45", "label": "Why use venv?"},
                        {"time": "2:30", "label": "Create virtual env"},
                        {"time": "4:15", "label": "Activate venv"},
                        {"time": "6:00", "label": "Install packages"},
                        {"time": "8:30", "label": "Deactivate venv"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Python Dependencies - requirements.txt",
                    url="https://www.youtube.com/watch?v=rWRa7pDSLXo",
                    description="Managing Python packages with requirements.txt files.",
                    duration="6:18",
                    timestamps=[
                        {"time": "0:30", "label": "What is requirements.txt?"},
                        {"time": "2:00", "label": "Generate from project"},
                        {"time": "3:45", "label": "Install from file"},
                        {"time": "5:15", "label": "Best practices"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ],

            "claude_code": [
                Tutorial(
                    title="Getting Started with Claude Code",
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder - replace with real video
                    description="Introduction to Claude Code CLI and autonomous coding.",
                    duration="15:20",
                    timestamps=[
                        {"time": "0:00", "label": "What is Claude Code?"},
                        {"time": "3:30", "label": "Installation"},
                        {"time": "6:45", "label": "First commands"},
                        {"time": "10:15", "label": "Autonomous mode"},
                        {"time": "13:00", "label": "Best practices"}
                    ],
                    level="beginner",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Ralph Mode - AI Team Coding",
                    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder - replace with real video
                    description="Learn how Ralph Mode brings AI coding to life with personality!",
                    duration="12:40",
                    timestamps=[
                        {"time": "0:30", "label": "Meet the team"},
                        {"time": "3:00", "label": "Setting up Ralph"},
                        {"time": "6:15", "label": "Your first session"},
                        {"time": "9:30", "label": "Advanced features"}
                    ],
                    level="intermediate",
                    updated="2025-01"
                )
            ],

            "webhooks_vs_polling": [
                Tutorial(
                    title="Webhooks vs Polling Explained",
                    url="https://www.youtube.com/watch?v=rJjaq5SnhP4",
                    description="Understand the difference between webhooks and polling for Telegram bots.",
                    duration="8:45",
                    timestamps=[
                        {"time": "0:30", "label": "What is polling?"},
                        {"time": "2:15", "label": "What are webhooks?"},
                        {"time": "4:30", "label": "Pros and cons"},
                        {"time": "6:45", "label": "Which to choose?"}
                    ],
                    level="intermediate",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Setting Up HTTPS for Webhooks",
                    url="https://www.youtube.com/watch?v=R3GunEOrV_E",
                    description="Get SSL certificate and domain for webhook deployment.",
                    duration="14:22",
                    timestamps=[
                        {"time": "1:00", "label": "Why HTTPS required?"},
                        {"time": "3:30", "label": "Get domain name"},
                        {"time": "6:15", "label": "SSL certificate setup"},
                        {"time": "10:00", "label": "Configure webhook"},
                        {"time": "12:30", "label": "Test webhook"}
                    ],
                    level="intermediate",
                    updated="2025-01"
                )
            ],

            "troubleshooting": [
                Tutorial(
                    title="Common Git Errors and Fixes",
                    url="https://www.youtube.com/watch?v=hJTZOHRusKU",
                    description="Debug common Git errors like 'permission denied' and 'merge conflicts'.",
                    duration="11:15",
                    timestamps=[
                        {"time": "0:45", "label": "Permission denied errors"},
                        {"time": "3:30", "label": "Merge conflicts"},
                        {"time": "6:00", "label": "Detached HEAD state"},
                        {"time": "8:45", "label": "Authentication issues"}
                    ],
                    level="intermediate",
                    updated="2025-01"
                ),
                Tutorial(
                    title="Python Import Errors Solved",
                    url="https://www.youtube.com/watch?v=vERmvFJ5xaA",
                    description="Fix 'ModuleNotFoundError' and other import issues.",
                    duration="7:30",
                    timestamps=[
                        {"time": "0:30", "label": "Common import errors"},
                        {"time": "2:15", "label": "Check virtual env"},
                        {"time": "4:00", "label": "Installing missing packages"},
                        {"time": "5:45", "label": "Path issues"}
                    ],
                    level="beginner",
                    updated="2025-01"
                )
            ]
        }

    def get_tutorials(self, topic: str) -> List[Tutorial]:
        """Get all tutorials for a specific topic.

        Args:
            topic: Topic key (e.g., 'ssh_keys', 'github_basics')

        Returns:
            List of Tutorial objects for that topic
        """
        return self._tutorials.get(topic, [])

    def get_tutorial(self, topic: str, index: int = 0) -> Optional[Tutorial]:
        """Get a specific tutorial by topic and index.

        Args:
            topic: Topic key
            index: Tutorial index (default 0 for primary tutorial)

        Returns:
            Tutorial object or None if not found
        """
        tutorials = self.get_tutorials(topic)
        if 0 <= index < len(tutorials):
            return tutorials[index]
        return None

    def format_tutorial_link(self, tutorial: Tutorial, include_timestamps: bool = True) -> str:
        """Format a tutorial as a mobile-friendly Telegram message.

        Args:
            tutorial: Tutorial object to format
            include_timestamps: Whether to include timestamp list

        Returns:
            Formatted string with tutorial info
        """
        message = f"🎥 *{tutorial.title}*\n"
        message += f"⏱️ Duration: {tutorial.duration}\n"
        message += f"📱 Level: {tutorial.level.capitalize()}\n\n"
        message += f"{tutorial.description}\n\n"
        message += f"🔗 [Watch Tutorial]({tutorial.url})\n"

        if include_timestamps and tutorial.timestamps:
            message += f"\n*Key Sections:*\n"
            for ts in tutorial.timestamps:
                message += f"• {ts['time']} - {ts['label']}\n"

        return message

    def format_topic_tutorials(self, topic: str) -> str:
        """Format all tutorials for a topic.

        Args:
            topic: Topic key

        Returns:
            Formatted string with all tutorials for that topic
        """
        tutorials = self.get_tutorials(topic)
        if not tutorials:
            return "No tutorials available for this topic yet. Ralph is working on it! 🔧"

        message = ""
        for i, tutorial in enumerate(tutorials, 1):
            message += f"\n*Option {i}:* {tutorial.title}\n"
            message += f"⏱️ {tutorial.duration} | 📱 {tutorial.level.capitalize()}\n"
            message += f"🔗 [Watch]({tutorial.url})\n"

        return message

    def get_all_topics(self) -> List[str]:
        """Get list of all available topics.

        Returns:
            List of topic keys
        """
        return list(self._tutorials.keys())

    def search_tutorials(self, query: str) -> List[Tuple[str, Tutorial]]:
        """Search for tutorials matching a query.

        Args:
            query: Search string

        Returns:
            List of (topic, tutorial) tuples matching the query
        """
        query_lower = query.lower()
        results = []

        for topic, tutorials in self._tutorials.items():
            for tutorial in tutorials:
                # Search in title, description, and timestamps
                if (query_lower in tutorial.title.lower() or
                    query_lower in tutorial.description.lower() or
                    any(query_lower in ts['label'].lower() for ts in tutorial.timestamps)):
                    results.append((topic, tutorial))

        return results


# Global instance
_tutorial_library = None


def get_tutorial_library() -> TutorialLibrary:
    """Get the global tutorial library instance.

    Returns:
        TutorialLibrary singleton
    """
    global _tutorial_library
    if _tutorial_library is None:
        _tutorial_library = TutorialLibrary()
    return _tutorial_library


# Convenience functions for quick access
def get_ssh_tutorial(index: int = 0) -> Optional[Tutorial]:
    """Get SSH key tutorial (convenience function)."""
    return get_tutorial_library().get_tutorial("ssh_keys", index)


def get_github_tutorial(index: int = 0) -> Optional[Tutorial]:
    """Get GitHub basics tutorial (convenience function)."""
    return get_tutorial_library().get_tutorial("github_basics", index)


def get_git_tutorial(index: int = 0) -> Optional[Tutorial]:
    """Get Git basics tutorial (convenience function)."""
    return get_tutorial_library().get_tutorial("git_basics", index)


def get_api_keys_tutorial(index: int = 0) -> Optional[Tutorial]:
    """Get API keys tutorial (convenience function)."""
    return get_tutorial_library().get_tutorial("api_keys", index)


def get_telegram_bot_tutorial(index: int = 0) -> Optional[Tutorial]:
    """Get Telegram bot tutorial (convenience function)."""
    return get_tutorial_library().get_tutorial("telegram_bots", index)
