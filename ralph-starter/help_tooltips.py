#!/usr/bin/env python3
"""
Help Tooltips - OB-015: Inline Help Tooltips

Kid-friendly explanations for technical terms (8th grade reading level).
Used throughout the onboarding wizard to help users understand concepts.
"""

from typing import Dict, Optional

# All tooltips written at 8th grade reading level
# Simple language, concrete examples, links to learn more
TOOLTIPS: Dict[str, Dict[str, str]] = {
    # Git & GitHub Terms
    "ssh_key": {
        "text": "An SSH key is like a special password that lets your computer talk to GitHub securely. Instead of typing your password every time, your computer shows GitHub this special key to prove it's really you. It's super safe because the key never leaves your computer!",
        "example": "Think of it like a keycard to get into a building - you tap it once, and the door opens automatically.",
        "learn_more": "https://docs.github.com/en/authentication/connecting-to-github-with-ssh/about-ssh"
    },

    "repository": {
        "text": "A repository (or 'repo') is a folder where your project lives. It stores all your code files, images, and the complete history of every change you've ever made. GitHub keeps a copy online so your code is backed up and your team can access it.",
        "example": "Like a Google Drive folder, but specifically designed for code with superpowers for tracking changes.",
        "learn_more": "https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories"
    },

    "commit": {
        "text": "A commit is like saving your work, but better! When you commit, you save a snapshot of your code with a description of what you changed. This creates a history so you can always go back to any previous version if something breaks.",
        "example": "Like saving a video game - you can always load an earlier save if you mess up.",
        "learn_more": "https://github.com/git-guides/git-commit"
    },

    "push": {
        "text": "Pushing means sending your saved work (commits) from your computer to GitHub. It's like uploading your changes to the cloud so others can see them and your work is backed up.",
        "example": "Like hitting 'sync' on Google Drive - your local changes go up to the cloud.",
        "learn_more": "https://github.com/git-guides/git-push"
    },

    "pull": {
        "text": "Pulling is the opposite of pushing - it downloads the latest changes from GitHub to your computer. This keeps your local copy up to date with what's on GitHub.",
        "example": "Like hitting 'refresh' to get the latest version of a shared document.",
        "learn_more": "https://github.com/git-guides/git-pull"
    },

    "clone": {
        "text": "Cloning means making a complete copy of a GitHub repository onto your computer. You get all the code, all the history, everything. Then you can work on it locally.",
        "example": "Like downloading an entire Google Drive folder to your computer so you can work on it offline.",
        "learn_more": "https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository"
    },

    "branch": {
        "text": "A branch is like a separate copy of your code where you can experiment without messing up the main version. When you're happy with your changes, you can merge them back into the main branch.",
        "example": "Like making a copy of a Word document so you can try new edits without ruining the original.",
        "learn_more": "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches"
    },

    # API & Authentication Terms
    "api_key": {
        "text": "An API key is like a password that lets your program talk to another service (like Anthropic or Groq). It proves you have permission to use that service. Keep it secret! Anyone with your API key can use it and you'll get charged.",
        "example": "Like a credit card number - very powerful, must be kept secret!",
        "learn_more": "https://docs.anthropic.com/en/api/getting-started"
    },

    "env_file": {
        "text": "A .env file is where you store secret information (like API keys and passwords) so they don't go into your code. This file stays on your computer and never gets uploaded to GitHub. It keeps your secrets safe!",
        "example": "Like a locked drawer where you keep your passwords - stays at home, doesn't travel.",
        "learn_more": "https://www.freecodecamp.org/news/how-to-use-environment-variables/"
    },

    "webhook": {
        "text": "A webhook is like a doorbell for your app. When something happens on GitHub (like a new commit), GitHub 'rings the doorbell' by sending a message to your app. Your app can then do something automatically, like start a build.",
        "example": "Like getting a text notification when your package is delivered - automatic updates!",
        "learn_more": "https://docs.github.com/en/webhooks-and-events/webhooks/about-webhooks"
    },

    # Python Terms
    "virtual_environment": {
        "text": "A virtual environment (venv) is a separate space for your Python project. It keeps your project's packages separate from other projects, so they don't conflict. Each project gets its own clean room!",
        "example": "Like having separate toolboxes for different projects - the tools in one don't mix with another.",
        "learn_more": "https://realpython.com/python-virtual-environments-a-primer/"
    },

    "requirements_txt": {
        "text": "A requirements.txt file lists all the Python packages your project needs. It's like a shopping list - anyone can read it and install exactly the right versions of everything.",
        "example": "Like a recipe that lists all the ingredients you need to buy.",
        "learn_more": "https://pip.pypa.io/en/stable/user_guide/#requirements-files"
    },

    "pip": {
        "text": "pip is Python's package installer. It downloads and installs libraries (pre-written code) from the internet so you don't have to write everything from scratch. It's the standard way to add features to your Python projects.",
        "example": "Like an app store for Python code - you type what you want and it installs it.",
        "learn_more": "https://pip.pypa.io/en/stable/"
    },

    # Node.js Terms
    "nodejs": {
        "text": "Node.js lets you run JavaScript outside of a web browser. It's what powers many modern development tools and servers. You need it to run Claude Code CLI.",
        "example": "Like a runtime for JavaScript - it runs JS code on your computer, not just in Chrome/Firefox.",
        "learn_more": "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs"
    },

    "npm": {
        "text": "npm is Node's package manager, like pip for Python. It installs JavaScript libraries and tools. It comes bundled with Node.js.",
        "example": "Like an app store for JavaScript tools and libraries.",
        "learn_more": "https://docs.npmjs.com/about-npm"
    },

    "package_json": {
        "text": "A package.json file lists all the JavaScript packages your project needs, plus info about your project. It's like a recipe file for your Node.js app.",
        "example": "Like a label on a food package - tells you what's inside and what ingredients it needs.",
        "learn_more": "https://docs.npmjs.com/cli/v10/configuring-npm/package-json"
    },

    # MCP Terms
    "mcp_server": {
        "text": "MCP (Model Context Protocol) servers give Claude superpowers! Each server connects Claude to a tool or service (like GitHub, Slack, or your database). Claude can then use those services to help you get work done.",
        "example": "Like plugins for a video game - each one adds new abilities and features.",
        "learn_more": "https://modelcontextprotocol.io/"
    },

    # Claude Code Terms
    "claude_code": {
        "text": "Claude Code is a command-line tool where Claude (the AI) helps you write and edit code. You can have conversations with Claude, and it can read, write, and run code on your computer to help you build things.",
        "example": "Like having a super smart coding buddy in your terminal who can actually write code for you.",
        "learn_more": "https://docs.anthropic.com/claude-code"
    },

    "prd": {
        "text": "PRD means Product Requirements Document. It's a big list of features you want to build. Ralph reads this list and works through each task one by one, implementing them automatically while you sleep!",
        "example": "Like a to-do list for your AI team - they work through it item by item.",
        "learn_more": None  # Internal concept
    },

    # Ralph Mode Specific
    "ralph_mode": {
        "text": "Ralph Mode is an autonomous coding system. You give Ralph a list of tasks (a PRD) and he manages a team of AI workers who implement features automatically. Wake up to completed work! It's like having a development team working overnight.",
        "example": "Set it up before bed, wake up with your features built, tested, and committed.",
        "learn_more": "https://ralphmode.com"
    },

    # General Development Terms
    "localhost": {
        "text": "Localhost is your own computer when it's running like a server. When you visit localhost in your browser, you're looking at a website running on your machine, not the internet. Great for testing!",
        "example": "Like a private rehearsal stage - you can test your website before showing it to the world.",
        "learn_more": "https://developer.mozilla.org/en-US/docs/Learn/Common_questions/Tools_and_setup/What_is_a_web_server"
    },

    "cli": {
        "text": "CLI means Command Line Interface - it's a way to control your computer by typing commands instead of clicking buttons. Looks scary at first, but it's super powerful once you learn it!",
        "example": "Like texting commands to your computer instead of tapping icons.",
        "learn_more": "https://www.freecodecamp.org/news/command-line-for-beginners/"
    },

    "path_environment_variable": {
        "text": "Your PATH is a list of folders where your computer looks for programs. When you type a command like 'node' or 'git', your computer searches these folders to find the program. If it's not in PATH, your computer won't find it!",
        "example": "Like your computer's speed dial - it knows where to look for common programs.",
        "learn_more": "https://www.freecodecamp.org/news/how-to-set-an-environment-variable-in-linux/"
    },
}


def get_tooltip(term: str) -> Optional[str]:
    """
    Get the tooltip text for a technical term.

    Args:
        term: The technical term to look up (case-insensitive)

    Returns:
        The tooltip text, or None if not found

    Example:
        >>> text = get_tooltip("ssh_key")
        >>> print(text)
        "An SSH key is like a special password..."
    """
    term_lower = term.lower().replace(" ", "_").replace("-", "_")
    tooltip_data = TOOLTIPS.get(term_lower)

    if not tooltip_data:
        return None

    # Build the full tooltip text
    text = tooltip_data["text"]

    if tooltip_data.get("example"):
        text += f"\n\n💡 {tooltip_data['example']}"

    if tooltip_data.get("learn_more"):
        text += f"\n\n📚 Learn more: {tooltip_data['learn_more']}"

    return text


def get_tooltip_short(term: str) -> Optional[str]:
    """
    Get just the main explanation without examples or links.

    Args:
        term: The technical term to look up

    Returns:
        Short tooltip text, or None if not found
    """
    term_lower = term.lower().replace(" ", "_").replace("-", "_")
    tooltip_data = TOOLTIPS.get(term_lower)

    if not tooltip_data:
        return None

    return tooltip_data["text"]


def get_all_terms() -> list[str]:
    """
    Get a list of all terms that have tooltips defined.

    Returns:
        List of term keys
    """
    return list(TOOLTIPS.keys())


def search_tooltips(query: str) -> Dict[str, str]:
    """
    Search for tooltips containing a query string.

    Args:
        query: Search string (case-insensitive)

    Returns:
        Dict of matching terms and their texts
    """
    query_lower = query.lower()
    matches = {}

    for term, data in TOOLTIPS.items():
        if query_lower in term.lower() or query_lower in data["text"].lower():
            matches[term] = data["text"]

    return matches


# Ralph-themed help responses for when tooltips aren't found
RALPH_NO_TOOLTIP_MESSAGES = [
    "I don't know what that is! But I can still help you do it!",
    "That one's not in my brain yet. But we can figure it out together!",
    "Never heard of it! Wanna teach me?",
    "My helper book doesn't have that word. But that's okay!",
]


def get_ralph_no_tooltip_message() -> str:
    """Get a random Ralph-themed message for when a tooltip isn't found."""
    import random
    return random.choice(RALPH_NO_TOOLTIP_MESSAGES)


# Testing
if __name__ == "__main__":
    print("=== Help Tooltips Test ===\n")

    # Test getting a tooltip
    print("1. SSH Key Tooltip:")
    print(get_tooltip("ssh_key"))
    print("\n" + "="*50 + "\n")

    # Test short version
    print("2. API Key Tooltip (short):")
    print(get_tooltip_short("api_key"))
    print("\n" + "="*50 + "\n")

    # Test all terms
    print("3. All available terms:")
    print(", ".join(get_all_terms()))
    print("\n" + "="*50 + "\n")

    # Test search
    print("4. Search for 'GitHub':")
    results = search_tooltips("GitHub")
    for term in results:
        print(f"  - {term}")
    print("\n" + "="*50 + "\n")

    # Test not found
    print("5. Not found message:")
    print(get_ralph_no_tooltip_message())
