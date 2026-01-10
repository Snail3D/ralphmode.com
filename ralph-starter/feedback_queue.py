#!/usr/bin/env python3
"""
FQ-001, FQ-002, FQ-003: Feedback Queue Management for Ralph Mode Bot

FQ-001: Database layer for feedback queue
- Uses existing Feedback model from database.py
- Tracks feedback status from submission to deployment
- Provides queue management and prioritization

FQ-002: Status state machine
- pending: Just submitted
- screening: Being checked for spam/quality
- scored: Quality and priority calculated
- queued: Ready for Ralph to pick up
- in_progress: Ralph is working on it
- testing: Implementation complete, testing
- deployed: Successfully deployed
- rejected: Spam, duplicate, or won't fix

FQ-003: User status tracking
- /mystatus command shows user's feedback status
- Track feedback through full lifecycle
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import Session

from database import get_db, Feedback, User, InputValidator
from feedback_scorer import (
    get_feedback_scorer,
    calculate_priority_with_tier,
    normalize_quality_score,
    estimate_complexity_from_feedback
)

logger = logging.getLogger(__name__)


# FQ-002: Valid status transitions
STATUS_TRANSITIONS = {
    "pending": ["screening", "rejected"],
    "screening": ["scored", "rejected"],
    "scored": ["queued", "rejected"],
    "queued": ["in_progress", "rejected"],
    "in_progress": ["testing", "rejected"],
    "testing": ["deployed", "in_progress"],  # Can go back to in_progress if tests fail
    "deployed": [],  # Terminal state
    "rejected": []   # Terminal state
}


class FeedbackQueue:
    """
    FQ-001: Feedback queue management system.

    Provides methods to:
    - Add feedback to queue
    - Update feedback status
    - Get next item for Ralph to work on
    - Query queue by status, priority, user
    - Track feedback lifecycle
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize feedback queue.

        Args:
            db: Optional database session (if None, uses get_db())
        """
        self.db = db
        self._owns_db = db is None

    def __enter__(self):
        """Context manager entry."""
        if self._owns_db:
            self.db = get_db().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._owns_db and self.db:
            self.db.__exit__(exc_type, exc_val, exc_tb)

    def add_feedback(
        self,
        user_id: int,
        feedback_type: str,
        content: str,
        ip_hash: Optional[str] = None
    ) -> Optional[Feedback]:
        """
        Add new feedback to queue.

        Args:
            user_id: Database user ID
            feedback_type: Type (bug, feature, improvement, praise)
            content: Feedback content
            ip_hash: Hashed IP for rate limiting

        Returns:
            Feedback object if created, None if validation fails
        """
        # Validate inputs
        try:
            user_id = int(user_id)
            if user_id <= 0:
                logger.error(f"Invalid user_id: {user_id}")
                return None
        except (TypeError, ValueError):
            logger.error(f"Invalid user_id type: {user_id}")
            return None

        if feedback_type not in ["bug", "feature", "improvement", "praise"]:
            logger.error(f"Invalid feedback_type: {feedback_type}")
            return None

        if not InputValidator.is_safe_string(content, max_length=10000):
            logger.error("Invalid feedback content")
            return None

        try:
            feedback = Feedback(
                user_id=user_id,
                feedback_type=feedback_type,
                content=content,
                status="pending",
                ip_hash=ip_hash,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)

            logger.info(f"Added feedback {feedback.id} to queue (type={feedback_type}, user={user_id})")
            return feedback

        except Exception as e:
            logger.error(f"Failed to add feedback to queue: {e}")
            self.db.rollback()
            return None

    def update_status(
        self,
        feedback_id: int,
        new_status: str,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """
        Update feedback status with validation.

        Args:
            feedback_id: Feedback ID
            new_status: New status
            rejection_reason: Reason if rejecting

        Returns:
            True if updated, False if validation fails
        """
        try:
            feedback_id = int(feedback_id)
            if feedback_id <= 0:
                logger.error(f"Invalid feedback_id: {feedback_id}")
                return False
        except (TypeError, ValueError):
            logger.error(f"Invalid feedback_id type: {feedback_id}")
            return False

        try:
            feedback = self.db.query(Feedback).filter(Feedback.id == feedback_id).first()

            if not feedback:
                logger.error(f"Feedback {feedback_id} not found")
                return False

            # Validate status transition
            current_status = feedback.status
            if new_status not in STATUS_TRANSITIONS.get(current_status, []):
                # Allow transitions to terminal states from any state
                if new_status not in ["rejected", "deployed"]:
                    logger.error(
                        f"Invalid status transition: {current_status} -> {new_status}"
                    )
                    return False

            # Update status
            feedback.status = new_status
            feedback.updated_at = datetime.utcnow()

            # Handle rejection
            if new_status == "rejected":
                feedback.rejected_at = datetime.utcnow()
                if rejection_reason:
                    feedback.rejection_reason = rejection_reason

            self.db.commit()
            logger.info(f"Updated feedback {feedback_id}: {current_status} -> {new_status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update feedback status: {e}")
            self.db.rollback()
            return False

    def score_feedback(self, feedback_id: int) -> Optional[Dict[str, Any]]:
        """
        Calculate quality and priority scores for feedback.

        This automatically:
        1. Calculates quality score (QS-001)
        2. Estimates complexity
        3. Calculates priority score (PR-001)
        4. Categorizes into tier (PR-002)
        5. Updates status to 'scored'

        Args:
            feedback_id: Feedback ID

        Returns:
            Dict with scores or None if failed
        """
        try:
            feedback = self.db.query(Feedback).filter(Feedback.id == feedback_id).first()

            if not feedback:
                logger.error(f"Feedback {feedback_id} not found")
                return None

            # Calculate quality score
            scorer = get_feedback_scorer()
            quality_scores = scorer.calculate_quality_score(feedback.content)
            quality_score = quality_scores['total']

            # Normalize quality for priority calculation
            normalized_quality = normalize_quality_score(quality_score)

            # Estimate complexity
            complexity = estimate_complexity_from_feedback(
                feedback.content,
                feedback.feedback_type
            )

            # Get user tier weight (default to Builder tier = 1.0)
            user = self.db.query(User).filter(User.id == feedback.user_id).first()
            user_tier = user.subscription_tier if user else "builder"
            user_weight = 2.0 if user_tier == "priority" else 1.0

            # For now, use heuristic estimates for impact, frequency, urgency
            # TODO: These should come from LLM analysis or user input
            impact = 5.0  # Medium impact by default
            frequency = 5.0  # Medium frequency
            urgency = 5.0  # Medium urgency

            # Calculate priority with tier
            priority_result = calculate_priority_with_tier(
                impact, frequency, urgency, normalized_quality, user_weight, complexity
            )

            # Update feedback record
            feedback.quality_score = quality_score
            feedback.priority_score = priority_result['priority_score']
            feedback.status = "scored"
            feedback.updated_at = datetime.utcnow()

            self.db.commit()

            logger.info(
                f"Scored feedback {feedback_id}: "
                f"quality={quality_score:.2f}, "
                f"priority={priority_result['priority_score']:.2f}, "
                f"tier={priority_result['tier']}"
            )

            return {
                'quality_score': quality_score,
                'priority_score': priority_result['priority_score'],
                'priority_tier': priority_result['tier'],
                'complexity': complexity
            }

        except Exception as e:
            logger.error(f"Failed to score feedback {feedback_id}: {e}")
            self.db.rollback()
            return None

    def get_next_high_priority(self) -> Optional[Feedback]:
        """
        Get next HIGH priority item for Ralph to work on.

        Returns items in 'queued' status, ordered by priority score descending.

        Returns:
            Feedback object or None
        """
        try:
            feedback = self.db.query(Feedback).filter(
                Feedback.status == "queued",
                Feedback.priority_score > 7  # HIGH tier threshold
            ).order_by(
                desc(Feedback.priority_score)
            ).first()

            return feedback

        except Exception as e:
            logger.error(f"Failed to get next high priority item: {e}")
            return None

    def get_queue_by_status(self, status: str, limit: int = 100) -> List[Feedback]:
        """
        Get all feedback items with a specific status.

        Args:
            status: Status to filter by
            limit: Maximum number of items to return

        Returns:
            List of Feedback objects
        """
        try:
            items = self.db.query(Feedback).filter(
                Feedback.status == status
            ).order_by(
                desc(Feedback.priority_score)
            ).limit(limit).all()

            return items

        except Exception as e:
            logger.error(f"Failed to get queue by status {status}: {e}")
            return []

    def get_user_feedback(self, user_id: int) -> List[Feedback]:
        """
        Get all feedback submitted by a user.

        Args:
            user_id: Database user ID

        Returns:
            List of Feedback objects
        """
        try:
            feedback_items = self.db.query(Feedback).filter(
                Feedback.user_id == user_id
            ).order_by(
                desc(Feedback.created_at)
            ).all()

            return feedback_items

        except Exception as e:
            logger.error(f"Failed to get user feedback for user {user_id}: {e}")
            return []

    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics by status.

        Returns:
            Dict with status counts:
            {
                'pending': 5,
                'screening': 2,
                'scored': 10,
                'queued': 8,
                'in_progress': 3,
                'testing': 1,
                'deployed': 50,
                'rejected': 12,
                'total': 91
            }
        """
        try:
            stats = {}

            for status in ["pending", "screening", "scored", "queued",
                          "in_progress", "testing", "deployed", "rejected"]:
                count = self.db.query(Feedback).filter(
                    Feedback.status == status
                ).count()
                stats[status] = count

            stats['total'] = self.db.query(Feedback).count()

            return stats

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}


def get_feedback_queue(db: Optional[Session] = None) -> FeedbackQueue:
    """
    Get a feedback queue instance.

    Args:
        db: Optional database session

    Returns:
        FeedbackQueue instance
    """
    return FeedbackQueue(db)
