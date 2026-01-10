#!/usr/bin/env python3
"""
NT-002: Build Started Notification Service

This module handles notifications for build events, particularly when a build starts.
Sends Telegram messages to users to let them know their feedback is being worked on.
"""

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Get token from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# WB-003: Build dashboard URL (for live stream link)
BUILD_DASHBOARD_URL = os.getenv("BUILD_DASHBOARD_URL", "https://ralphmode.com/builds")


class NotificationService:
    """Service for sending notifications about build events."""

    def __init__(self):
        """Initialize the notification service with Telegram bot."""
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("NT-002: TELEGRAM_BOT_TOKEN not set, notifications disabled")
            self.bot = None
        else:
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)

    def _ralph_misspell(self, text: str) -> str:
        """
        Apply Ralph's signature misspellings to text.

        This makes notifications feel in-character from Ralph.
        Mirrors the ralph_misspell function from ralph_bot.py.
        """
        misspellings = {
            "important": "importent",
            "possible": "possibel",
            "definitely": "definately",
            "probably": "probly",
            "building": "bilding",
            "working": "werking",
            "started": "startid",
            "feedback": "feedbak",
            "priority": "priorite",
            "quality": "qualitee",
        }

        result = text
        for correct, wrong in misspellings.items():
            # Only replace if it's a whole word
            import re
            pattern = r'\b' + correct + r'\b'
            result = re.sub(pattern, wrong, result, flags=re.IGNORECASE)

        return result

    def _estimate_completion_time(self, feedback_type: str, priority_score: float) -> str:
        """
        Estimate when the build will be complete.

        Args:
            feedback_type: Type of feedback (bug, feature, etc.)
            priority_score: Priority score (0-10)

        Returns:
            Human-readable time estimate (e.g., "~30 minutes", "~2 hours")
        """
        # Base estimates by feedback type
        base_minutes = {
            "bug": 30,
            "feature": 60,
            "improvement": 45,
            "ui_ux": 40,
            "docs": 20,
        }

        # Get base estimate or default
        estimate = base_minutes.get(feedback_type, 45)

        # Higher priority = faster (we work harder on it)
        # But don't oversell - builds take time
        if priority_score > 8:
            estimate = int(estimate * 0.8)  # 20% faster for high priority
        elif priority_score < 5:
            estimate = int(estimate * 1.2)  # 20% slower for low priority

        # Format nicely
        if estimate < 60:
            return f"~{estimate} minutes"
        else:
            hours = estimate / 60
            if hours < 2:
                return f"~1-2 hours"
            else:
                return f"~{int(hours)} hours"

    async def send_build_started_notification(
        self,
        user_id: int,
        feedback_id: int,
        feedback_type: str,
        content_preview: str,
        priority_score: float,
        stream_url: Optional[str] = None
    ) -> bool:
        """
        NT-002: Send notification when a build starts.

        Args:
            user_id: Telegram user ID to notify
            feedback_id: Feedback item ID
            feedback_type: Type of feedback (bug, feature, etc.)
            content_preview: Short preview of the feedback content
            priority_score: Priority score (0-10)
            stream_url: Optional URL to watch live build stream (WB-002)

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.bot:
            logger.warning("NT-002: Bot not initialized, skipping notification")
            return False

        try:
            # Get completion time estimate
            eta = self._estimate_completion_time(feedback_type, priority_score)

            # Build in-character message from Ralph
            base_message = (
                f"🚧 *Build Startid!*\n\n"
                f"Hey Mr. Worms! Me and my team are werking on your feedbak #{feedback_id}!\n\n"
                f"📋 *What we're bilding:*\n"
                f"_{content_preview[:100]}{'...' if len(content_preview) > 100 else ''}_\n\n"
                f"⏱️ *Should be done in:* {eta}\n"
                f"⭐ *Priorite:* {priority_score:.1f}/10\n\n"
            )

            # Add stream link if available (WB-002)
            if stream_url:
                base_message += (
                    f"👀 *Watch us werk:* [Live Stream]({stream_url})\n\n"
                )
            else:
                # Fallback to general dashboard
                base_message += (
                    f"👀 *Check progress:* [Build Dashboard]({BUILD_DASHBOARD_URL})\n\n"
                )

            # Ralph's signature sign-off (vary it to feel fresh)
            sign_offs = [
                "I'm doing my best!",
                "This is gonna be great probly!",
                "My team knows what they're doing... I think!",
                "Let's make it happen!",
                "We're on it boss!",
            ]
            import random
            sign_off = random.choice(sign_offs)

            base_message += f"— Ralph 👷\n_{sign_off}_"

            # Apply Ralph's misspellings (but not to the preview or URLs)
            message = self._ralph_misspell(base_message)

            # Send the notification
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=False  # Show link preview for stream
            )

            logger.info(f"NT-002: Sent build started notification to user {user_id} for feedback {feedback_id}")
            return True

        except TelegramError as e:
            logger.error(f"NT-002: Failed to send notification to user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"NT-002: Unexpected error sending notification: {e}", exc_info=True)
            return False

    def send_build_started_sync(
        self,
        user_id: int,
        feedback_id: int,
        feedback_type: str,
        content_preview: str,
        priority_score: float,
        stream_url: Optional[str] = None
    ) -> bool:
        """
        Synchronous wrapper for send_build_started_notification.

        This is useful when calling from non-async contexts like build_orchestrator.
        """
        try:
            # Create new event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async function
            return loop.run_until_complete(
                self.send_build_started_notification(
                    user_id, feedback_id, feedback_type,
                    content_preview, priority_score, stream_url
                )
            )
        except Exception as e:
            logger.error(f"NT-002: Error in sync wrapper: {e}", exc_info=True)
            return False

    async def send_deployed_notification(
        self,
        user_id: int,
        feedback_id: int,
        version: str,
        changelog_url: Optional[str] = None
    ) -> bool:
        """
        NT-003: Send notification when a build is deployed to production.

        Args:
            user_id: Telegram user ID to notify
            feedback_id: Feedback item ID that was deployed
            version: Version number of the deployment (e.g., "0.4.0")
            changelog_url: Optional URL to the changelog

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.bot:
            logger.warning("NT-003: Bot not initialized, skipping notification")
            return False

        try:
            # Build in-character message from Ralph
            base_message = (
                f"🎉 *We Did It Mr. Worms!*\n\n"
                f"Your feedbak #{feedback_id} is now live in produkshun!\n\n"
                f"📦 *Version:* {version}\n"
            )

            # Add changelog link if available
            if changelog_url:
                base_message += f"📋 *Changelog:* [See what's new]({changelog_url})\n"
            else:
                # Fallback to generic changelog URL
                base_message += f"📋 *Changelog:* [See what's new](https://ralphmode.com/changelog)\n"

            base_message += (
                f"\n"
                f"Thank you for making Ralph Mode better! Your sugestion really helpt.\n\n"
                f"*How did we do?*\n"
                f"👍 Great! / 👎 Needs work\n\n"
            )

            # Ralph's signature sign-offs (vary for freshness)
            sign_offs = [
                "I'm super proud of this one!",
                "Me and my team worked real hard!",
                "This was a good idea Mr. Worms!",
                "I think you'll like it!",
                "We did our bestest!",
            ]
            import random
            sign_off = random.choice(sign_offs)

            base_message += f"— Ralph 👷\n_{sign_off}_"

            # Apply Ralph's misspellings
            message = self._ralph_misspell(base_message)

            # Send the notification
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=False  # Show link preview for changelog
            )

            logger.info(f"NT-003: Sent deployed notification to user {user_id} for feedback {feedback_id}, version {version}")
            return True

        except TelegramError as e:
            logger.error(f"NT-003: Failed to send deployed notification to user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"NT-003: Unexpected error sending deployed notification: {e}", exc_info=True)
            return False

    def send_deployed_sync(
        self,
        user_id: int,
        feedback_id: int,
        version: str,
        changelog_url: Optional[str] = None
    ) -> bool:
        """
        Synchronous wrapper for send_deployed_notification.

        This is useful when calling from non-async contexts like deploy_manager.
        """
        try:
            # Create new event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async function
            return loop.run_until_complete(
                self.send_deployed_notification(
                    user_id, feedback_id, version, changelog_url
                )
            )
        except Exception as e:
            logger.error(f"NT-003: Error in sync wrapper: {e}", exc_info=True)
            return False


# Global instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
