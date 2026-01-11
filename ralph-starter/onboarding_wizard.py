#!/usr/bin/env python3
"""
Onboarding Wizard for Ralph Mode

Guides users through setup with Ralph's personality.
Makes the technical stuff fun and accessible.
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class OnboardingWizard:
    """Handles the onboarding flow for new users."""

    # Onboarding steps
    STEP_WELCOME = "welcome"
    STEP_SETUP_TYPE = "setup_type"
    STEP_SSH_KEY = "ssh_key"
    STEP_GITHUB = "github"
    STEP_REPO = "repo"
    STEP_COMPLETE = "complete"

    # Setup types
    SETUP_GUIDED = "guided"
    SETUP_QUICK = "quick"

    def __init__(self):
        """Initialize the onboarding wizard."""
        self.logger = logging.getLogger(__name__)

    def get_welcome_message(self) -> str:
        """Get Ralph's welcoming onboarding message.

        Returns:
            Welcome message with Ralph's personality
        """
        return """*Welcome to Ralph Mode Setup!* 🍩

Me Ralph! Me help you set up AI team!

*What we gonna do:*
• Get your computer talking to GitHub (that's where code lives!)
• Make a special house for your code (called "repository")
• Connect Ralph's brain to your computer
• Make sure everything works good!

Don't worry! Ralph make it super easy! Like eating paste... but PRODUCTIVE!

*Two ways to do this:*

🎯 *Guided Setup* - Ralph walks you through every step
   Perfect if this is your first time!
   Ralph explains EVERYTHING!

⚡ *Quick Setup* - For smarty-pants who did this before
   Just the important stuff!

*Which one you want?*
"""

    def get_welcome_keyboard(self) -> InlineKeyboardMarkup:
        """Get the welcome screen keyboard with setup type options.

        Returns:
            Keyboard markup with Guided/Quick setup buttons
        """
        keyboard = [
            [
                InlineKeyboardButton("🎯 Guided Setup (Recommended)", callback_data="setup_guided"),
            ],
            [
                InlineKeyboardButton("⚡ Quick Setup", callback_data="setup_quick"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_setup_overview(self, setup_type: str) -> str:
        """Get the setup overview based on chosen type.

        Args:
            setup_type: Either 'guided' or 'quick'

        Returns:
            Overview message for the selected setup type
        """
        if setup_type == self.SETUP_GUIDED:
            return """*Okay! Ralph do Guided Setup!* 👍

Me gonna help you with:

**Step 1:** Make special key for GitHub 🔑
   (Like a super secret password but fancier!)

**Step 2:** Tell GitHub about your key 🎫
   (So GitHub knows it's really you!)

**Step 3:** Make a code house (repository) 🏠
   (Where your code lives!)

**Step 4:** Connect Ralph to everything 🔌
   (The magic part!)

Ralph take it slow! No rush! We do together!

*Ready to start?*
"""
        else:  # Quick setup
            return """*Quick Setup Mode Activated!* ⚡

Ralph assume you know the drill!

**Quick checklist:**
✅ SSH key for GitHub
✅ GitHub repository created
✅ Repository URL configured
✅ Claude Code installed

Ralph help you check each one super fast!

*Let's go!*
"""

    def get_overview_keyboard(self) -> InlineKeyboardMarkup:
        """Get the keyboard for the overview screen.

        Returns:
            Keyboard markup with Continue button
        """
        keyboard = [
            [InlineKeyboardButton("▶️ Let's Go!", callback_data="setup_continue")],
            [InlineKeyboardButton("◀️ Back", callback_data="setup_back_welcome")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def init_onboarding_state(self, user_id: int) -> Dict[str, Any]:
        """Initialize onboarding state for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Initial onboarding state dictionary
        """
        return {
            "step": self.STEP_WELCOME,
            "setup_type": None,
            "ssh_key_generated": False,
            "ssh_key_added_to_github": False,
            "repo_created": False,
            "repo_url": None,
            "started_at": None,
            "completed_at": None,
        }

    def update_step(self, state: Dict[str, Any], new_step: str) -> Dict[str, Any]:
        """Update the current step in onboarding state.

        Args:
            state: Current onboarding state
            new_step: New step to move to

        Returns:
            Updated state dictionary
        """
        state["step"] = new_step
        return state

    def set_setup_type(self, state: Dict[str, Any], setup_type: str) -> Dict[str, Any]:
        """Set the setup type in onboarding state.

        Args:
            state: Current onboarding state
            setup_type: Either 'guided' or 'quick'

        Returns:
            Updated state dictionary
        """
        state["setup_type"] = setup_type
        return state

    def is_onboarding_complete(self, state: Dict[str, Any]) -> bool:
        """Check if onboarding is complete.

        Args:
            state: Current onboarding state

        Returns:
            True if onboarding is complete, False otherwise
        """
        return (
            state.get("ssh_key_generated", False) and
            state.get("ssh_key_added_to_github", False) and
            state.get("repo_created", False) and
            state.get("repo_url") is not None
        )

    def get_progress_message(self, state: Dict[str, Any]) -> str:
        """Get a progress message showing what's been completed.

        Args:
            state: Current onboarding state

        Returns:
            Progress message string
        """
        progress = []

        if state.get("ssh_key_generated"):
            progress.append("✅ SSH key generated")
        else:
            progress.append("⬜ SSH key not generated yet")

        if state.get("ssh_key_added_to_github"):
            progress.append("✅ SSH key added to GitHub")
        else:
            progress.append("⬜ SSH key not added to GitHub yet")

        if state.get("repo_created"):
            progress.append("✅ Repository created")
        else:
            progress.append("⬜ Repository not created yet")

        if state.get("repo_url"):
            progress.append(f"✅ Repository URL: {state['repo_url']}")
        else:
            progress.append("⬜ Repository URL not configured")

        return "*Your Progress:*\n\n" + "\n".join(progress)


def get_onboarding_wizard() -> OnboardingWizard:
    """Get the onboarding wizard instance.

    Returns:
        OnboardingWizard instance
    """
    return OnboardingWizard()
