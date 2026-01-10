#!/usr/bin/env python3
"""
QS-003: User Quality Score Tracking Module for Ralph Mode Bot

Tracks quality score per user over time. Users with consistently high-quality
feedback get boosted priority.

Quality Score Tiers:
- avg > 85: +50% priority boost (excellent feedback providers)
- avg > 70: +20% priority boost (good feedback providers)
- avg < 40: flagged for review (low quality feedback)

Integration:
- Updates user quality score when feedback is scored
- Calculates average from all user feedback
- Provides priority boost multiplier for PR-001
- Shown on /mystatus command
"""

import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
from sqlalchemy import func

from database import get_db, User, Feedback

logger = logging.getLogger(__name__)


class UserQualityTracker:
    """
    Tracks and updates user quality scores based on feedback quality.

    The quality score is a rolling average of all feedback quality scores
    from that user. It's used to boost priority for high-quality contributors
    and flag low-quality submitters for review.
    """

    def update_user_quality_score(self, user_id: int) -> Optional[float]:
        """
        Calculate and update the average quality score for a user.

        Calculates the average quality_score from all of the user's feedback
        items and updates the user.quality_score field.

        Args:
            user_id: Internal database user ID

        Returns:
            Updated quality score (0-100) or None if update failed
        """
        try:
            with get_db() as db:
                # Get user
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return None

                # Calculate average quality score from all user feedback
                avg_score = db.query(
                    func.avg(Feedback.quality_score)
                ).filter(
                    Feedback.user_id == user_id,
                    Feedback.quality_score.isnot(None)
                ).scalar()

                if avg_score is not None:
                    # Round to 2 decimal places
                    avg_score = round(float(avg_score), 2)

                    # Update user quality score
                    user.quality_score = avg_score
                    user.updated_at = datetime.utcnow()
                    db.commit()

                    logger.info(f"Updated user {user_id} quality score to {avg_score}")

                    # Flag for review if below threshold
                    if avg_score < 40:
                        logger.warning(
                            f"User {user_id} flagged for review: "
                            f"quality score {avg_score} below threshold (40)"
                        )

                    return avg_score
                else:
                    # No scored feedback yet, keep default
                    logger.info(f"User {user_id} has no scored feedback yet")
                    return user.quality_score

        except Exception as e:
            logger.error(f"Failed to update user quality score for user {user_id}: {e}")
            return None

    def get_priority_boost(self, user_id: int) -> float:
        """
        Get the priority boost multiplier based on user quality score.

        Priority boosts:
        - avg > 85: 1.5x (50% boost)
        - avg > 70: 1.2x (20% boost)
        - avg < 40: 1.0x (no boost, flagged for review)
        - default: 1.0x (no boost)

        Args:
            user_id: Internal database user ID

        Returns:
            Priority boost multiplier (1.0, 1.2, or 1.5)
        """
        try:
            with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return 1.0

                quality_score = user.quality_score or 50.0  # Default to middle

                if quality_score > 85:
                    return 1.5  # 50% boost
                elif quality_score > 70:
                    return 1.2  # 20% boost
                else:
                    return 1.0  # No boost

        except Exception as e:
            logger.error(f"Failed to get priority boost for user {user_id}: {e}")
            return 1.0

    def get_user_quality_stats(self, user_id: int) -> Optional[Dict]:
        """
        Get detailed quality statistics for a user.

        Returns stats for /mystatus display:
        - Current quality score
        - Total feedback count
        - Priority boost multiplier
        - Quality tier description

        Args:
            user_id: Internal database user ID

        Returns:
            Dict with quality stats or None if user not found
        """
        try:
            with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return None

                # Count total feedback items
                total_feedback = db.query(func.count(Feedback.id)).filter(
                    Feedback.user_id == user_id
                ).scalar() or 0

                # Count scored feedback items
                scored_feedback = db.query(func.count(Feedback.id)).filter(
                    Feedback.user_id == user_id,
                    Feedback.quality_score.isnot(None)
                ).scalar() or 0

                quality_score = user.quality_score or 50.0
                boost = self.get_priority_boost(user_id)

                # Determine quality tier
                if quality_score > 85:
                    tier = "Excellent"
                    tier_emoji = "⭐"
                    description = "Top contributor! Your feedback gets 50% priority boost."
                elif quality_score > 70:
                    tier = "Good"
                    tier_emoji = "✨"
                    description = "Great feedback! You get 20% priority boost."
                elif quality_score < 40:
                    tier = "Needs Improvement"
                    tier_emoji = "⚠️"
                    description = "Low quality score. Try to be more specific and actionable."
                else:
                    tier = "Average"
                    tier_emoji = "👍"
                    description = "Keep providing quality feedback to earn priority boosts!"

                return {
                    'quality_score': quality_score,
                    'total_feedback': total_feedback,
                    'scored_feedback': scored_feedback,
                    'priority_boost': boost,
                    'boost_percentage': int((boost - 1.0) * 100),
                    'tier': tier,
                    'tier_emoji': tier_emoji,
                    'description': description,
                    'flagged': quality_score < 40
                }

        except Exception as e:
            logger.error(f"Failed to get quality stats for user {user_id}: {e}")
            return None

    def is_user_flagged(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if user is flagged for review due to low quality score.

        Args:
            user_id: Internal database user ID

        Returns:
            Tuple of (is_flagged, reason)
        """
        try:
            with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return (False, None)

                quality_score = user.quality_score or 50.0

                if quality_score < 40:
                    # Count feedback to determine reason
                    feedback_count = db.query(func.count(Feedback.id)).filter(
                        Feedback.user_id == user_id,
                        Feedback.quality_score.isnot(None)
                    ).scalar() or 0

                    reason = (
                        f"Quality score {quality_score:.1f} below threshold (40.0). "
                        f"Based on {feedback_count} feedback items."
                    )
                    return (True, reason)

                return (False, None)

        except Exception as e:
            logger.error(f"Failed to check if user {user_id} is flagged: {e}")
            return (False, None)


# Singleton instance
_user_quality_tracker = None


def get_user_quality_tracker() -> UserQualityTracker:
    """
    Get the global user quality tracker instance.

    Returns:
        UserQualityTracker instance
    """
    global _user_quality_tracker
    if _user_quality_tracker is None:
        _user_quality_tracker = UserQualityTracker()
    return _user_quality_tracker


def update_user_quality_score(user_id: int) -> Optional[float]:
    """
    Convenience function to update user quality score.

    Args:
        user_id: Internal database user ID

    Returns:
        Updated quality score or None
    """
    tracker = get_user_quality_tracker()
    return tracker.update_user_quality_score(user_id)


def get_priority_boost(user_id: int) -> float:
    """
    Convenience function to get priority boost multiplier.

    Args:
        user_id: Internal database user ID

    Returns:
        Priority boost multiplier
    """
    tracker = get_user_quality_tracker()
    return tracker.get_priority_boost(user_id)
