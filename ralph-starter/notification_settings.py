#!/usr/bin/env python3
"""
Notification Settings Manager for Ralph Mode

Handles user preferences for when and how Ralph notifies them.
Supports build completion, errors, milestones, and more.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import time
from pathlib import Path


class NotificationSettings:
    """Manages notification preferences for users."""

    # Notification types
    NOTIF_BUILD_COMPLETE = "build_complete"
    NOTIF_ERRORS = "errors"
    NOTIF_MILESTONES = "milestones"
    NOTIF_IDLE_CHATTER = "idle_chatter"
    NOTIF_RALPH_MOMENTS = "ralph_moments"

    # Notification modes
    MODE_INSTANT = "instant"
    MODE_SUMMARY = "summary"
    MODE_NONE = "none"

    DEFAULT_SETTINGS = {
        NOTIF_BUILD_COMPLETE: MODE_INSTANT,
        NOTIF_ERRORS: MODE_INSTANT,
        NOTIF_MILESTONES: MODE_INSTANT,
        NOTIF_IDLE_CHATTER: MODE_INSTANT,
        NOTIF_RALPH_MOMENTS: MODE_INSTANT,
        "quiet_hours_enabled": False,
        "quiet_hours_start": "22:00",  # 10 PM
        "quiet_hours_end": "08:00",    # 8 AM
    }

    def __init__(self, storage_dir: Optional[str] = None):
        """Initialize notification settings manager.

        Args:
            storage_dir: Directory to store user preferences (defaults to ./user_data)
        """
        self.logger = logging.getLogger(__name__)
        self.storage_dir = Path(storage_dir) if storage_dir else Path("./user_data")
        self.storage_dir.mkdir(exist_ok=True)

    def _get_user_file(self, user_id: int) -> Path:
        """Get the path to a user's settings file."""
        return self.storage_dir / f"notif_settings_{user_id}.json"

    def get_settings(self, user_id: int) -> Dict[str, Any]:
        """Get notification settings for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary of notification settings
        """
        user_file = self._get_user_file(user_id)

        if not user_file.exists():
            return self.DEFAULT_SETTINGS.copy()

        try:
            with open(user_file, 'r') as f:
                settings = json.load(f)
                # Merge with defaults to handle new settings
                merged = self.DEFAULT_SETTINGS.copy()
                merged.update(settings)
                return merged
        except Exception as e:
            self.logger.error(f"Error loading settings for user {user_id}: {e}")
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """Save notification settings for a user.

        Args:
            user_id: Telegram user ID
            settings: Dictionary of notification settings

        Returns:
            True if successful, False otherwise
        """
        user_file = self._get_user_file(user_id)

        try:
            with open(user_file, 'w') as f:
                json.dump(settings, f, indent=2)
            self.logger.info(f"Saved notification settings for user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving settings for user {user_id}: {e}")
            return False

    def update_setting(self, user_id: int, setting_key: str, value: Any) -> bool:
        """Update a single notification setting.

        Args:
            user_id: Telegram user ID
            setting_key: Key to update
            value: New value

        Returns:
            True if successful, False otherwise
        """
        settings = self.get_settings(user_id)
        settings[setting_key] = value
        return self.save_settings(user_id, settings)

    def is_quiet_hours(self, user_id: int) -> bool:
        """Check if current time is within user's quiet hours.

        Args:
            user_id: Telegram user ID

        Returns:
            True if in quiet hours, False otherwise
        """
        settings = self.get_settings(user_id)

        if not settings.get("quiet_hours_enabled", False):
            return False

        from datetime import datetime
        now = datetime.now().time()

        try:
            start_str = settings.get("quiet_hours_start", "22:00")
            end_str = settings.get("quiet_hours_end", "08:00")

            start_time = time(*map(int, start_str.split(":")))
            end_time = time(*map(int, end_str.split(":")))

            # Handle overnight quiet hours (e.g., 10 PM - 8 AM)
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                return now >= start_time or now <= end_time
        except Exception as e:
            self.logger.error(f"Error checking quiet hours: {e}")
            return False

    def should_send_notification(self, user_id: int, notif_type: str) -> bool:
        """Check if a notification should be sent.

        Args:
            user_id: Telegram user ID
            notif_type: Type of notification

        Returns:
            True if notification should be sent, False otherwise
        """
        settings = self.get_settings(user_id)

        # Check if notification type is enabled
        mode = settings.get(notif_type, self.MODE_INSTANT)
        if mode == self.MODE_NONE:
            return False

        # Check quiet hours
        if self.is_quiet_hours(user_id):
            # During quiet hours, only send errors
            if notif_type == self.NOTIF_ERRORS:
                return True
            return False

        return True

    def get_notification_mode(self, user_id: int, notif_type: str) -> str:
        """Get the notification mode for a specific type.

        Args:
            user_id: Telegram user ID
            notif_type: Type of notification

        Returns:
            Notification mode (instant/summary/none)
        """
        settings = self.get_settings(user_id)
        return settings.get(notif_type, self.MODE_INSTANT)


# Singleton instance
_notification_settings_instance = None


def get_notification_settings(storage_dir: Optional[str] = None) -> NotificationSettings:
    """Get the singleton instance of NotificationSettings.

    Args:
        storage_dir: Directory to store user preferences (only used on first call)

    Returns:
        NotificationSettings instance
    """
    global _notification_settings_instance
    if _notification_settings_instance is None:
        _notification_settings_instance = NotificationSettings(storage_dir)
    return _notification_settings_instance
