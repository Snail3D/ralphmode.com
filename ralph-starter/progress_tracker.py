#!/usr/bin/env python3
"""
Progress Tracker UI for Ralph Mode Onboarding

Displays a visual checklist showing setup progress with:
- Status icons (✅ completed, 🔄 in progress, ⬜ pending)
- Percentage complete
- Current step highlighting
- Persistent across sessions
"""

import logging
from typing import Dict, Any, List, Tuple


logger = logging.getLogger(__name__)


class ProgressTracker:
    """Manages and displays onboarding progress UI."""

    # Define all setup steps in order
    SETUP_STEPS = [
        {
            "id": "ssh_key_generated",
            "label": "Generate SSH Key",
            "description": "Create SSH key for GitHub authentication"
        },
        {
            "id": "ssh_key_added_to_github",
            "label": "Add SSH Key to GitHub",
            "description": "Upload your public key to GitHub"
        },
        {
            "id": "repo_created",
            "label": "Create Repository",
            "description": "Set up your GitHub repository"
        },
        {
            "id": "git_configured",
            "label": "Configure Git",
            "description": "Set up Git username and email"
        },
        {
            "id": "first_commit",
            "label": "Make First Commit",
            "description": "Commit your initial code"
        },
        {
            "id": "environment_setup",
            "label": "Set Up Environment",
            "description": "Configure .env file with tokens"
        }
    ]

    def __init__(self):
        """Initialize the progress tracker."""
        self.logger = logging.getLogger(__name__)

    def get_progress_message(
        self,
        state: Dict[str, Any],
        current_step: str = None
    ) -> str:
        """Generate a visual progress message.

        Args:
            state: Setup state dictionary with completion flags
            current_step: ID of the current step being worked on (optional)

        Returns:
            Formatted progress message with visual indicators
        """
        completed_count = 0
        total_steps = len(self.SETUP_STEPS)
        lines = ["*🛠 Setup Progress*\n"]

        for step in self.SETUP_STEPS:
            step_id = step["id"]
            label = step["label"]
            is_completed = state.get(step_id, False)
            is_current = step_id == current_step

            # Determine icon
            if is_completed:
                icon = "✅"
                completed_count += 1
            elif is_current:
                icon = "🔄"
            else:
                icon = "⬜"

            # Format line with highlighting for current step
            if is_current:
                lines.append(f"▶️ {icon} *{label}*")
            else:
                lines.append(f"   {icon} {label}")

        # Calculate percentage
        percentage = int((completed_count / total_steps) * 100) if total_steps > 0 else 0

        # Add progress bar
        progress_bar = self._generate_progress_bar(percentage)
        lines.append(f"\n{progress_bar} {percentage}%")
        lines.append(f"({completed_count}/{total_steps} steps complete)")

        return "\n".join(lines)

    def get_compact_progress(self, state: Dict[str, Any]) -> str:
        """Generate a compact one-line progress indicator.

        Args:
            state: Setup state dictionary

        Returns:
            Compact progress string (e.g., "✅✅🔄⬜⬜⬜ 33%")
        """
        icons = []
        completed_count = 0
        total_steps = len(self.SETUP_STEPS)

        for step in self.SETUP_STEPS:
            step_id = step["id"]
            is_completed = state.get(step_id, False)

            if is_completed:
                icons.append("✅")
                completed_count += 1
            else:
                icons.append("⬜")

        percentage = int((completed_count / total_steps) * 100) if total_steps > 0 else 0

        return "".join(icons) + f" {percentage}%"

    def _generate_progress_bar(self, percentage: int, width: int = 10) -> str:
        """Generate a visual progress bar.

        Args:
            percentage: Progress percentage (0-100)
            width: Width of the progress bar in characters

        Returns:
            Progress bar string (e.g., "████░░░░░░")
        """
        filled = int((percentage / 100) * width)
        empty = width - filled

        return "█" * filled + "░" * empty

    def get_next_step(self, state: Dict[str, Any]) -> Tuple[str, str]:
        """Get the next incomplete step.

        Args:
            state: Setup state dictionary

        Returns:
            Tuple of (step_id, step_label) for the next step, or (None, None) if all complete
        """
        for step in self.SETUP_STEPS:
            step_id = step["id"]
            if not state.get(step_id, False):
                return step_id, step["label"]

        return None, None

    def is_setup_complete(self, state: Dict[str, Any]) -> bool:
        """Check if all setup steps are complete.

        Args:
            state: Setup state dictionary

        Returns:
            True if all steps complete, False otherwise
        """
        for step in self.SETUP_STEPS:
            if not state.get(step["id"], False):
                return False

        return True

    def get_step_details(self, step_id: str) -> Dict[str, str]:
        """Get details for a specific step.

        Args:
            step_id: Step identifier

        Returns:
            Dictionary with step details (label, description) or None if not found
        """
        for step in self.SETUP_STEPS:
            if step["id"] == step_id:
                return {
                    "label": step["label"],
                    "description": step["description"]
                }

        return None

    def get_celebration_message(self, state: Dict[str, Any]) -> str:
        """Generate a celebration message when setup is complete.

        Args:
            state: Setup state dictionary

        Returns:
            Celebration message with completed checklist
        """
        if not self.is_setup_complete(state):
            return ""

        lines = [
            "*🎉 SETUP COMPLETE! 🎉*\n",
            "You did it! Ralph is super proud of you! Here's what you accomplished:\n"
        ]

        for step in self.SETUP_STEPS:
            lines.append(f"✅ {step['label']}")

        lines.append("\n*You're all set to start building!*")

        return "\n".join(lines)

    def add_progress_footer(self, message: str, state: Dict[str, Any]) -> str:
        """Add a compact progress footer to any message.

        Args:
            message: Original message
            state: Setup state dictionary

        Returns:
            Message with progress footer appended
        """
        compact_progress = self.get_compact_progress(state)

        return f"{message}\n\n_Progress: {compact_progress}_"


def get_progress_tracker() -> ProgressTracker:
    """Get the progress tracker instance.

    Returns:
        ProgressTracker instance
    """
    return ProgressTracker()
