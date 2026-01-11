#!/usr/bin/env python3
"""
Telegram Utilities - Copy Button Component (OB-012)

Reusable copy-to-clipboard buttons for Telegram.
One tap copies command/key to clipboard with mobile-friendly UX.
"""

import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Global storage for copy button data (keyed by hash for security)
# In production, this should be Redis or similar
_COPY_DATA_STORE: Dict[str, str] = {}

def create_copy_button(
    text_to_copy: str,
    button_label: str = "📋 Copy",
    show_preview: bool = False,
    max_preview_length: int = 30
) -> InlineKeyboardButton:
    """
    Create a copy-to-clipboard button for Telegram.

    Args:
        text_to_copy: The text that will be copied when button is clicked
        button_label: The label displayed on the button
        show_preview: If True, shows a preview of the text in the button label
        max_preview_length: Maximum length of preview text

    Returns:
        InlineKeyboardButton configured for copy action

    Example:
        >>> button = create_copy_button("ssh-keygen -t ed25519", "📋 Copy Command")
        >>> keyboard = InlineKeyboardMarkup([[button]])
    """
    # Generate a unique hash for this copy action
    copy_id = hashlib.md5(text_to_copy.encode()).hexdigest()[:16]

    # Store the text to copy (keyed by hash)
    _COPY_DATA_STORE[copy_id] = text_to_copy

    # Add preview if requested
    if show_preview:
        preview = text_to_copy[:max_preview_length]
        if len(text_to_copy) > max_preview_length:
            preview += "..."
        button_label = f"{button_label}: {preview}"

    # Create callback data (format: copy_<hash>)
    callback_data = f"copy_{copy_id}"

    return InlineKeyboardButton(button_label, callback_data=callback_data)


def create_copy_message(
    text_to_copy: str,
    description: str = "",
    button_label: str = "📋 Copy",
    show_text: bool = True,
    code_block: bool = False
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Create a formatted message with a copy button.

    Args:
        text_to_copy: The text that will be copied
        description: Optional description shown above the text
        button_label: Label for the copy button
        show_text: If True, displays the text in the message
        code_block: If True, wraps text in code block formatting

    Returns:
        Tuple of (message_text, keyboard_markup)

    Example:
        >>> text, keyboard = create_copy_message(
        ...     "git config --global user.name 'John Doe'",
        ...     description="Run this command:",
        ...     code_block=True
        ... )
    """
    # Build the message text
    message_parts = []

    if description:
        message_parts.append(description)

    if show_text:
        if code_block:
            message_parts.append(f"```\n{text_to_copy}\n```")
        else:
            message_parts.append(text_to_copy)

    message_text = "\n\n".join(message_parts) if message_parts else "Ready to copy!"

    # Create the copy button
    button = create_copy_button(text_to_copy, button_label)
    keyboard = InlineKeyboardMarkup([[button]])

    return message_text, keyboard


def create_multi_copy_buttons(
    items: List[tuple[str, str, str]],
    columns: int = 1
) -> InlineKeyboardMarkup:
    """
    Create multiple copy buttons arranged in a grid.

    Args:
        items: List of (text_to_copy, button_label, description) tuples
        columns: Number of buttons per row

    Returns:
        InlineKeyboardMarkup with multiple copy buttons

    Example:
        >>> items = [
        ...     ("secret_key_123", "📋 API Key", "Anthropic API Key"),
        ...     ("bot_token_456", "📋 Bot Token", "Telegram Bot Token")
        ... ]
        >>> keyboard = create_multi_copy_buttons(items, columns=2)
    """
    buttons = []
    current_row = []

    for text_to_copy, button_label, _ in items:
        button = create_copy_button(text_to_copy, button_label)
        current_row.append(button)

        if len(current_row) >= columns:
            buttons.append(current_row)
            current_row = []

    # Add remaining buttons
    if current_row:
        buttons.append(current_row)

    return InlineKeyboardMarkup(buttons)


def get_copy_text(copy_id: str) -> Optional[str]:
    """
    Retrieve the text associated with a copy button ID.

    Args:
        copy_id: The hash ID from the copy button callback

    Returns:
        The text to copy, or None if not found

    Example:
        >>> text = get_copy_text("abc123def456")
    """
    return _COPY_DATA_STORE.get(copy_id)


def handle_copy_callback(callback_data: str) -> tuple[bool, Optional[str], str]:
    """
    Process a copy button callback.

    Args:
        callback_data: The callback_data from the button press

    Returns:
        Tuple of (success, text_to_copy, response_message)

    Example:
        >>> success, text, message = handle_copy_callback("copy_abc123")
        >>> if success:
        ...     # Show text to user for manual copy
        ...     await query.answer(message, show_alert=True)
    """
    # Parse callback data
    if not callback_data.startswith("copy_"):
        return False, None, "Invalid copy action"

    copy_id = callback_data[5:]  # Remove "copy_" prefix

    # Retrieve the text
    text_to_copy = get_copy_text(copy_id)

    if not text_to_copy:
        logging.warning(f"Copy text not found for ID: {copy_id}")
        return False, None, "❌ Copy data expired. Please try again."

    # Success! Return the text so the bot can display it
    # Telegram doesn't support true clipboard copying, so we show it in an alert
    return True, text_to_copy, "✅ Copied! Text shown below - tap and hold to copy manually."


def cleanup_old_copy_data(max_entries: int = 1000):
    """
    Clean up old copy data to prevent memory bloat.
    This should be called periodically or when store gets too large.

    Args:
        max_entries: Maximum number of entries to keep
    """
    global _COPY_DATA_STORE

    if len(_COPY_DATA_STORE) > max_entries:
        # Keep only the most recent entries
        # In a real implementation, use timestamps
        keys = list(_COPY_DATA_STORE.keys())
        to_remove = keys[:-max_entries]
        for key in to_remove:
            del _COPY_DATA_STORE[key]

        logging.info(f"Cleaned up {len(to_remove)} old copy data entries")


# OB-015 Support: Tooltip/Help Button Component
def create_help_button(
    tooltip_text: str,
    button_label: str = "❓"
) -> InlineKeyboardButton:
    """
    Create a help/tooltip button that shows explanation on tap.

    Args:
        tooltip_text: The explanation to show
        button_label: The label for the button (default: ?)

    Returns:
        InlineKeyboardButton configured for help tooltip

    Example:
        >>> button = create_help_button("SSH keys are like digital passwords")
    """
    # Generate unique ID for this tooltip
    tooltip_id = hashlib.md5(tooltip_text.encode()).hexdigest()[:16]

    # Store the tooltip text
    _COPY_DATA_STORE[f"help_{tooltip_id}"] = tooltip_text

    return InlineKeyboardButton(button_label, callback_data=f"help_{tooltip_id}")


def handle_help_callback(callback_data: str) -> tuple[bool, str]:
    """
    Process a help button callback.

    Args:
        callback_data: The callback_data from the button press

    Returns:
        Tuple of (success, tooltip_text)
    """
    if not callback_data.startswith("help_"):
        return False, "Invalid help action"

    tooltip_text = get_copy_text(callback_data)

    if not tooltip_text:
        return False, "❌ Help text not found"

    return True, tooltip_text


def create_button_row_with_help(
    main_button: InlineKeyboardButton,
    help_text: str
) -> List[InlineKeyboardButton]:
    """
    Create a row with a main button and a help button.

    Args:
        main_button: The primary action button
        help_text: The help/tooltip text

    Returns:
        List of buttons for a keyboard row

    Example:
        >>> copy_btn = create_copy_button("ssh-keygen -t ed25519", "Copy Command")
        >>> row = create_button_row_with_help(
        ...     copy_btn,
        ...     "This generates a new SSH key pair for GitHub authentication"
        ... )
    """
    help_button = create_help_button(help_text)
    return [main_button, help_button]


# Utility for Ralph-themed copy confirmations
RALPH_COPY_MESSAGES = [
    "✅ I copied it boss! Well, I showed it to you. You gotta tap it yourself!",
    "✅ Here's the thingy! Tap and hold to copy it to your clipboard!",
    "✅ Got it! Now you gotta do the pressy-holdy thing to copy it!",
    "✅ Here you go Mr. Worms! Just tap-hold-copy like normal!",
    "✅ I putted it here for you! Your phone knows what to do next!",
]

def get_ralph_copy_message() -> str:
    """Get a random Ralph-themed copy confirmation message."""
    import random
    return random.choice(RALPH_COPY_MESSAGES)
