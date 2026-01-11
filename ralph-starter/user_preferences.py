#!/usr/bin/env python3
"""
User Preferences Module for Ralph Mode

Stores and manages user preferences including:
- Character avatar selection (guide character)
- Theme preferences
- Notification settings
- Other user-specific settings
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class UserPreferences:
    """Manages user preferences and settings."""

    # Available characters that can be selected as guides
    AVAILABLE_CHARACTERS = {
        "Ralph": {
            "title": "Boss (The Classic)",
            "description": "Ralph Wiggum - your lovable, unpredictable boss. Says 'unpossible', picks his nose, creates chaos but somehow delivers results.",
            "personality_preview": "Me fail English? That's unpossible! Let's make good codes!",
            "style": "chaotic_wholesome"
        },
        "Stool": {
            "title": "Frontend Dev (The Chill One)",
            "description": "Millennial frontend developer who's lowkey passionate about UX. Coffee in hand, vibes on point.",
            "personality_preview": "Yo, so like, let's build something that actually slaps, you know?",
            "style": "casual"
        },
        "Gomer": {
            "title": "Backend Dev (The Lovable Oaf)",
            "description": "Seems confused but knows backend architecture inside-out. Loves donuts and naps but delivers solid code.",
            "personality_preview": "D'oh! I mean... yeah, I can totally optimize that database query. *munches donut*",
            "style": "lovable_oaf"
        },
        "Mona": {
            "title": "Tech Lead (The Overachiever)",
            "description": "Smartest person in the room. Actually... everything she says is correct. Plays saxophone, thinks architecturally.",
            "personality_preview": "Actually, if we approach this logically, the optimal solution is quite clear.",
            "style": "overachiever"
        },
        "Gus": {
            "title": "Senior Dev (The Veteran)",
            "description": "25 years in. Seen every bug, survived every framework war. Cynical but wise.",
            "personality_preview": "*sips coffee* I've seen this exact problem in '09. Here's what you do...",
            "style": "veteran"
        }
    }

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize user preferences manager.

        Args:
            storage_path: Path to store preferences. Defaults to ./data/user_preferences.json
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path(__file__).parent / "data" / "user_preferences.json"

        # Ensure data directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing preferences or initialize empty
        self.preferences: Dict[str, Dict[str, Any]] = self._load_preferences()

    def _load_preferences(self) -> Dict[str, Dict[str, Any]]:
        """Load preferences from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load preferences: {e}")
                return {}
        return {}

    def _save_preferences(self) -> bool:
        """Save preferences to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.preferences, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get all preferences for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dict of user preferences
        """
        return self.preferences.get(str(user_id), {
            "guide_character": "Ralph",  # Default guide
            "theme": "default",
            "notifications_enabled": True,
            "onboarding_complete": False
        })

    def set_guide_character(self, user_id: str, character: str) -> bool:
        """
        Set the guide character for a user.

        Args:
            user_id: Telegram user ID
            character: Character name (Ralph, Stool, Gomer, Mona, or Gus)

        Returns:
            True if successful, False otherwise
        """
        if character not in self.AVAILABLE_CHARACTERS:
            logger.error(f"Invalid character: {character}")
            return False

        user_id_str = str(user_id)
        if user_id_str not in self.preferences:
            self.preferences[user_id_str] = self.get_user_preferences(user_id)

        self.preferences[user_id_str]["guide_character"] = character
        return self._save_preferences()

    def get_guide_character(self, user_id: str) -> str:
        """
        Get the guide character for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Character name
        """
        prefs = self.get_user_preferences(user_id)
        return prefs.get("guide_character", "Ralph")

    def set_theme(self, user_id: str, theme: str) -> bool:
        """
        Set the theme preference for a user.

        Args:
            user_id: Telegram user ID
            theme: Theme name

        Returns:
            True if successful, False otherwise
        """
        user_id_str = str(user_id)
        if user_id_str not in self.preferences:
            self.preferences[user_id_str] = self.get_user_preferences(user_id)

        self.preferences[user_id_str]["theme"] = theme
        return self._save_preferences()

    def mark_onboarding_complete(self, user_id: str) -> bool:
        """
        Mark onboarding as complete for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        user_id_str = str(user_id)
        if user_id_str not in self.preferences:
            self.preferences[user_id_str] = self.get_user_preferences(user_id)

        self.preferences[user_id_str]["onboarding_complete"] = True
        return self._save_preferences()

    def is_onboarding_complete(self, user_id: str) -> bool:
        """
        Check if user has completed onboarding.

        Args:
            user_id: Telegram user ID

        Returns:
            True if onboarding is complete, False otherwise
        """
        prefs = self.get_user_preferences(user_id)
        return prefs.get("onboarding_complete", False)

    def set_preference(self, user_id: str, key: str, value: Any) -> bool:
        """
        Set a generic preference for a user.

        Args:
            user_id: Telegram user ID
            key: Preference key
            value: Preference value

        Returns:
            True if successful, False otherwise
        """
        user_id_str = str(user_id)
        if user_id_str not in self.preferences:
            self.preferences[user_id_str] = self.get_user_preferences(user_id)

        self.preferences[user_id_str][key] = value
        return self._save_preferences()

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        Get a generic preference for a user.

        Args:
            user_id: Telegram user ID
            key: Preference key
            default: Default value if key not found

        Returns:
            Preference value or default
        """
        prefs = self.get_user_preferences(user_id)
        return prefs.get(key, default)


# Global singleton instance
_user_preferences_instance: Optional[UserPreferences] = None


def get_user_preferences() -> UserPreferences:
    """Get the global user preferences instance."""
    global _user_preferences_instance
    if _user_preferences_instance is None:
        _user_preferences_instance = UserPreferences()
    return _user_preferences_instance


def init_user_preferences(storage_path: Optional[str] = None) -> UserPreferences:
    """
    Initialize the user preferences system with a custom storage path.

    Args:
        storage_path: Custom storage path for preferences

    Returns:
        UserPreferences instance
    """
    global _user_preferences_instance
    _user_preferences_instance = UserPreferences(storage_path)
    return _user_preferences_instance
