#!/usr/bin/env python3
"""
Theme Manager for Ralph Mode
OB-040: Visual Theme Selector

Manages visual themes for Ralph interactions. Allows users to customize
the appearance of messages with different color schemes and styles.
"""

import logging
from typing import Dict, Optional, Any
from enum import Enum


logger = logging.getLogger(__name__)


class ThemeStyle(Enum):
    """Available visual themes."""
    LIGHT = "light"
    DARK = "dark"
    COLORFUL = "colorful"
    MINIMAL = "minimal"
    CUSTOM = "custom"


# Theme definitions with Telegram-compatible formatting
THEMES = {
    ThemeStyle.LIGHT: {
        "name": "Light Mode",
        "description": "Clean and bright, easy on the eyes in daytime",
        "character_prefix": "•",  # Simple bullet point
        "separator": "─" * 30,
        "header_style": lambda text: f"*{text}*",  # Bold only
        "code_block": lambda text: f"`{text}`",
        "emphasis": lambda text: f"_{text}_",  # Italic
        "preview": """• Ralph: Let's get this party started!
─────────────────────────────────
*Status:* Working on authentication
`Code complete`""",
    },
    ThemeStyle.DARK: {
        "name": "Dark Mode",
        "description": "Sleek and sophisticated, perfect for late-night coding",
        "character_prefix": "▸",  # Arrow
        "separator": "━" * 30,
        "header_style": lambda text: f"*{text.upper()}*",  # Bold + uppercase
        "code_block": lambda text: f"`{text}`",
        "emphasis": lambda text: f"_{text}_",
        "preview": """▸ Ralph: Let's get this party started!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*STATUS:* Working on authentication
`Code complete`""",
    },
    ThemeStyle.COLORFUL: {
        "name": "Colorful",
        "description": "Full emoji indicators, vibrant and expressive",
        "character_prefix": "emoji",  # Use character-specific emoji
        "separator": "─" * 30,
        "header_style": lambda text: f"*✨ {text} ✨*",
        "code_block": lambda text: f"```{text}```",
        "emphasis": lambda text: f"**{text}**",  # Bold emphasis
        "preview": """🔴 Ralph: Let's get this party started!
─────────────────────────────────
*✨ Status ✨* Working on authentication
```Code complete```""",
    },
    ThemeStyle.MINIMAL: {
        "name": "Minimal",
        "description": "No frills, just the content that matters",
        "character_prefix": "",  # No prefix
        "separator": "",  # No separator
        "header_style": lambda text: text,  # Plain text
        "code_block": lambda text: text,  # Plain text
        "emphasis": lambda text: text,  # Plain text
        "preview": """Ralph: Let's get this party started!

Status: Working on authentication
Code complete""",
    },
}

# Character emoji mapping for colorful theme
CHARACTER_EMOJIS = {
    "Ralph": "🔴",      # Red for the boss
    "Stool": "🟢",      # Green for chill frontend dev
    "Gomer": "🟡",      # Yellow for lovable backend
    "Mona": "🔵",       # Blue for smart tech lead
    "Gus": "🟤",        # Brown for grizzled senior
    "Frinky": "🟣",     # Purple for design specialist
    "册子": "🟠",       # Orange for API specialist
    "Willie": "🟫",     # Dark brown for DevOps
    "Doc": "⚪",        # White for debugging specialist
    "Slithery Sam": "🟢",      # Green snake
    "Scripter Sid": "🟣",      # Purple villain
    "Token Tina": "💎",        # Diamond thief
}


class ThemeManager:
    """Manages theme preferences and formatting for users."""

    def __init__(self):
        """Initialize the theme manager."""
        self.logger = logging.getLogger(__name__)
        self.custom_themes: Dict[int, Dict[str, Any]] = {}

    def get_theme(self, theme_style: str) -> Optional[Dict[str, Any]]:
        """Get theme configuration by style name.

        Args:
            theme_style: Theme style string (e.g., "light", "dark")

        Returns:
            Theme configuration dict or None if not found
        """
        try:
            style = ThemeStyle(theme_style.lower())
            return THEMES.get(style)
        except (ValueError, KeyError):
            self.logger.warning(f"Unknown theme style: {theme_style}")
            return None

    def get_default_theme(self) -> Dict[str, Any]:
        """Get the default theme (colorful).

        Returns:
            Default theme configuration
        """
        return THEMES[ThemeStyle.COLORFUL]

    def format_character_name(
        self,
        character: str,
        theme_style: str = "colorful"
    ) -> str:
        """Format a character name based on theme.

        Args:
            character: Character name
            theme_style: Theme style to apply

        Returns:
            Formatted character name with theme styling
        """
        theme = self.get_theme(theme_style) or self.get_default_theme()
        prefix_type = theme.get("character_prefix", "")

        if prefix_type == "emoji":
            # Use colorful emoji prefix
            emoji = CHARACTER_EMOJIS.get(character, "👤")
            return f"{emoji} {character}"
        elif prefix_type:
            # Use simple prefix
            return f"{prefix_type} {character}"
        else:
            # Minimal - no prefix
            return character

    def format_message(
        self,
        character: str,
        message: str,
        theme_style: str = "colorful"
    ) -> str:
        """Format a complete message with character name and theme styling.

        Args:
            character: Character name
            message: Message content
            theme_style: Theme style to apply

        Returns:
            Fully formatted message
        """
        formatted_name = self.format_character_name(character, theme_style)
        return f"{formatted_name}: {message}"

    def format_header(
        self,
        text: str,
        theme_style: str = "colorful"
    ) -> str:
        """Format a header/title based on theme.

        Args:
            text: Header text
            theme_style: Theme style to apply

        Returns:
            Formatted header
        """
        theme = self.get_theme(theme_style) or self.get_default_theme()
        header_formatter = theme.get("header_style", lambda t: t)
        return header_formatter(text)

    def format_separator(self, theme_style: str = "colorful") -> str:
        """Get a separator line for the theme.

        Args:
            theme_style: Theme style to apply

        Returns:
            Separator string (may be empty for minimal theme)
        """
        theme = self.get_theme(theme_style) or self.get_default_theme()
        return theme.get("separator", "")

    def format_code(
        self,
        code: str,
        theme_style: str = "colorful"
    ) -> str:
        """Format code/technical text based on theme.

        Args:
            code: Code or technical content
            theme_style: Theme style to apply

        Returns:
            Formatted code
        """
        theme = self.get_theme(theme_style) or self.get_default_theme()
        code_formatter = theme.get("code_block", lambda t: t)
        return code_formatter(code)

    def format_emphasis(
        self,
        text: str,
        theme_style: str = "colorful"
    ) -> str:
        """Format emphasized text based on theme.

        Args:
            text: Text to emphasize
            theme_style: Theme style to apply

        Returns:
            Formatted emphasis
        """
        theme = self.get_theme(theme_style) or self.get_default_theme()
        emphasis_formatter = theme.get("emphasis", lambda t: t)
        return emphasis_formatter(text)

    def get_theme_preview(self, theme_style: str) -> str:
        """Get a preview of what the theme looks like.

        Args:
            theme_style: Theme style to preview

        Returns:
            Preview text showing theme in action
        """
        theme = self.get_theme(theme_style) or self.get_default_theme()
        return theme.get("preview", "No preview available")

    def get_available_themes(self) -> list:
        """Get list of available themes with metadata.

        Returns:
            List of theme info dicts
        """
        themes = []
        for style, theme_data in THEMES.items():
            themes.append({
                "id": style.value,
                "name": theme_data["name"],
                "description": theme_data["description"],
                "preview": theme_data["preview"]
            })
        return themes

    def set_custom_theme(
        self,
        user_id: int,
        theme_config: Dict[str, Any]
    ) -> bool:
        """Set a custom theme for a user.

        Args:
            user_id: User's Telegram ID
            theme_config: Custom theme configuration

        Returns:
            True if set successfully
        """
        try:
            # Validate required fields
            required = ["character_prefix", "separator", "header_style"]
            if not all(key in theme_config for key in required):
                self.logger.error("Custom theme missing required fields")
                return False

            self.custom_themes[user_id] = theme_config
            self.logger.info(f"Set custom theme for user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error setting custom theme: {e}")
            return False

    def get_custom_theme(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get custom theme for a user.

        Args:
            user_id: User's Telegram ID

        Returns:
            Custom theme config or None
        """
        return self.custom_themes.get(user_id)


# Global theme manager instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance.

    Returns:
        ThemeManager instance
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
