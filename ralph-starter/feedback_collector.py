#!/usr/bin/env python3
"""
FB-001: Feedback Collection Module for Ralph Mode Bot

Handles user feedback collection from Telegram:
- Text descriptions of bugs/features
- Voice messages (transcribed)
- Screenshots with context
- Stores feedback with user_id, tier, timestamp

This module is part of the RLHF Self-Building System where users help
build the bot by providing feedback that gets queued, prioritized, and
automatically implemented.
"""

import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from io import BytesIO

from telegram import Update, File
from telegram.ext import ContextTypes

from database import get_db, Feedback, User, InputValidator
from rate_limiter import check_feedback_rate_limits

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collects and stores user feedback from various sources.

    Supports:
    - Text feedback
    - Voice messages (with transcription)
    - Screenshots (with context extraction)
    """

    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize feedback collector.

        Args:
            groq_api_key: Optional Groq API key for voice transcription
        """
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")

    def _get_user_ip(self, update: Update) -> str:
        """
        RL-001: Extract user IP address from Telegram update.

        Note: Telegram doesn't directly expose user IPs in their API.
        For Telegram bots, we use the user_id as a proxy for IP-based limiting.
        This prevents abuse while respecting Telegram's privacy model.

        Args:
            update: Telegram update object

        Returns:
            User identifier (telegram_id as string for IP limiting purposes)
        """
        if update and update.effective_user:
            # Use telegram user_id as proxy for IP-based rate limiting
            return f"telegram_{update.effective_user.id}"
        return "unknown"

    def _is_priority_user(self, user) -> bool:
        """
        RL-001: Check if user has priority tier (gets 2x rate limits).

        Args:
            user: User database object

        Returns:
            True if user has Builder+ or Priority tier
        """
        if not user:
            return False

        priority_tiers = ["builder", "builder+", "priority", "enterprise"]
        return user.subscription_tier.lower() in priority_tiers

    async def collect_text_feedback(
        self,
        user_id: int,
        telegram_id: int,
        content: str,
        feedback_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
        update: Optional[Update] = None
    ) -> Optional[int]:
        """
        Collect text-based feedback.

        Args:
            user_id: Internal database user ID
            telegram_id: Telegram user ID (for validation)
            content: Feedback text content
            feedback_type: Type of feedback (bug, feature, improvement, praise)
            metadata: Optional metadata (source, context, etc.)
            weight: FB-002 subscription weight (0.0=free, 1.0=builder, 2.0=priority, 3.0=enterprise)
            update: Optional Telegram update (for IP-based rate limiting)

        Returns:
            Feedback ID if successful, None otherwise
            Returns -1 if rate limited (use this to show friendly message)
        """
        # Validate input
        validated_telegram_id = InputValidator.validate_telegram_id(telegram_id)
        if not validated_telegram_id:
            logger.warning(f"Invalid telegram_id: {telegram_id}")
            return None

        if not InputValidator.is_safe_string(content, max_length=10000):
            logger.warning(f"Invalid feedback content from user {telegram_id}")
            return None

        if feedback_type not in ["bug", "feature", "improvement", "praise", "general"]:
            feedback_type = "general"

        try:
            with get_db() as db:
                # Get or create user
                user = db.query(User).filter(User.telegram_id == validated_telegram_id).first()
                if not user:
                    # Create user record
                    user = User(
                        telegram_id=validated_telegram_id,
                        subscription_tier="free"  # Default tier
                    )
                    db.add(user)
                    db.flush()

                # RL-001: Check IP-based rate limits
                if update:
                    user_ip = self._get_user_ip(update)
                    is_priority = self._is_priority_user(user)

                    allowed, error_metadata = check_feedback_rate_limits(
                        ip_address=user_ip,
                        is_priority=is_priority
                    )

                    if not allowed:
                        logger.warning(
                            f"Rate limit exceeded for user {telegram_id} "
                            f"({error_metadata['limit_type']} limit: {error_metadata['limit']})"
                        )
                        # Store error metadata for caller to use in friendly message
                        if metadata is None:
                            metadata = {}
                        metadata['rate_limit_error'] = error_metadata
                        return -1  # Signal rate limit exceeded

                # Create feedback entry
                # FB-002: Use subscription weight as base priority_score
                # This will be further refined by PR-001 algorithm later
                feedback = Feedback(
                    user_id=user.id,
                    feedback_type=feedback_type,
                    content=content,
                    status="pending",
                    priority_score=weight,  # FB-002: Subscription tier weight
                    created_at=datetime.utcnow()
                )

                db.add(feedback)
                db.flush()

                logger.info(f"Collected text feedback from user {telegram_id}: {feedback.id}")
                return feedback.id

        except Exception as e:
            logger.error(f"Failed to collect text feedback: {e}")
            return None

    async def collect_voice_feedback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        telegram_id: int
    ) -> Optional[int]:
        """
        Collect voice message feedback (with transcription).

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: Internal database user ID
            telegram_id: Telegram user ID

        Returns:
            Feedback ID if successful, None otherwise
        """
        try:
            voice = update.message.voice
            if not voice:
                return None

            # Download voice file
            voice_file: File = await context.bot.get_file(voice.file_id)
            voice_bytes = BytesIO()
            await voice_file.download_to_memory(voice_bytes)
            voice_bytes.seek(0)

            # Transcribe using Groq Whisper (placeholder - needs implementation)
            # For now, store a placeholder message
            transcription = await self._transcribe_voice(voice_bytes)

            if not transcription:
                transcription = "[Voice message - transcription unavailable]"

            # Store as text feedback with voice metadata
            metadata = {
                "source": "voice",
                "file_id": voice.file_id,
                "duration": voice.duration
            }

            feedback_id = await self.collect_text_feedback(
                user_id=user_id,
                telegram_id=telegram_id,
                content=transcription,
                feedback_type="general",
                metadata=metadata,
                update=update  # RL-001: Pass update for rate limiting
            )

            logger.info(f"Collected voice feedback from user {telegram_id}: {feedback_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Failed to collect voice feedback: {e}")
            return None

    async def collect_screenshot_feedback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        telegram_id: int,
        caption: Optional[str] = None
    ) -> Optional[int]:
        """
        Collect screenshot feedback with context.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: Internal database user ID
            telegram_id: Telegram user ID
            caption: Optional caption text

        Returns:
            Feedback ID if successful, None otherwise
        """
        try:
            photo = update.message.photo[-1] if update.message.photo else None
            if not photo:
                return None

            # Download photo
            photo_file: File = await context.bot.get_file(photo.file_id)

            # Store feedback with photo reference
            content = caption or "[Screenshot feedback - see attached image]"

            metadata = {
                "source": "screenshot",
                "file_id": photo.file_id,
                "caption": caption
            }

            feedback_id = await self.collect_text_feedback(
                user_id=user_id,
                telegram_id=telegram_id,
                content=content,
                feedback_type="bug" if "bug" in content.lower() else "general",
                metadata=metadata,
                update=update  # RL-001: Pass update for rate limiting
            )

            logger.info(f"Collected screenshot feedback from user {telegram_id}: {feedback_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Failed to collect screenshot feedback: {e}")
            return None

    async def _transcribe_voice(self, audio_bytes: BytesIO) -> Optional[str]:
        """
        Transcribe voice message using Groq Whisper.

        NOTE: This is a placeholder. Full implementation would use:
        - Groq Whisper API for transcription
        - Proper audio format handling

        Args:
            audio_bytes: Audio file bytes

        Returns:
            Transcribed text or None
        """
        # TODO: Implement Groq Whisper transcription
        # For now, return placeholder
        logger.warning("Voice transcription not yet implemented - using placeholder")
        return None

    def get_rate_limit_message(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        RL-001: Get friendly rate limit error message from metadata.

        Args:
            metadata: Metadata dict that may contain rate_limit_error

        Returns:
            Friendly error message or None
        """
        if not metadata or 'rate_limit_error' not in metadata:
            return None

        error = metadata['rate_limit_error']
        return error.get('message', 'Rate limit exceeded. Please try again later.')

    def classify_feedback_type(self, content: str) -> str:
        """
        Classify feedback type based on content.

        Args:
            content: Feedback text

        Returns:
            Feedback type (bug, feature, improvement, praise)
        """
        content_lower = content.lower()

        # Bug indicators
        bug_keywords = ["bug", "error", "crash", "broken", "not working", "issue", "problem"]
        if any(keyword in content_lower for keyword in bug_keywords):
            return "bug"

        # Feature request indicators
        feature_keywords = ["feature", "add", "could you", "would be nice", "suggestion", "want"]
        if any(keyword in content_lower for keyword in feature_keywords):
            return "feature"

        # Improvement indicators
        improvement_keywords = ["improve", "better", "enhance", "optimize", "should"]
        if any(keyword in content_lower for keyword in improvement_keywords):
            return "improvement"

        # Praise indicators
        praise_keywords = ["great", "awesome", "love", "thank", "excellent", "perfect"]
        if any(keyword in content_lower for keyword in praise_keywords):
            return "praise"

        return "general"

    def get_user_feedback_count(self, telegram_id: int) -> Dict[str, int]:
        """
        Get feedback statistics for a user.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Dict with feedback counts by status
        """
        validated_id = InputValidator.validate_telegram_id(telegram_id)
        if not validated_id:
            return {}

        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == validated_id).first()
                if not user:
                    return {}

                # Count feedback by status
                feedback_list = db.query(Feedback).filter(Feedback.user_id == user.id).all()

                counts = {
                    "total": len(feedback_list),
                    "pending": 0,
                    "reviewing": 0,
                    "building": 0,
                    "deployed": 0,
                    "rejected": 0
                }

                for fb in feedback_list:
                    if fb.status in counts:
                        counts[fb.status] += 1

                return counts

        except Exception as e:
            logger.error(f"Failed to get feedback count: {e}")
            return {}


# Singleton instance
_feedback_collector = None

def get_feedback_collector(groq_api_key: Optional[str] = None) -> FeedbackCollector:
    """
    Get the global feedback collector instance.

    Args:
        groq_api_key: Optional Groq API key

    Returns:
        FeedbackCollector instance
    """
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector(groq_api_key)
    return _feedback_collector
