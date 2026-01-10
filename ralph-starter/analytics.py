#!/usr/bin/env python3
"""
AN-001: User Satisfaction Tracking and Analytics

This module provides analytics for user satisfaction ratings on deployed fixes.
Used for RLHF improvement and quality metrics.
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy import func, Integer

from database import get_db, User, Feedback, UserSatisfaction

logger = logging.getLogger(__name__)


class SatisfactionAnalytics:
    """Analytics for user satisfaction tracking."""

    @staticmethod
    def get_satisfaction_rate_for_feedback(feedback_id: int) -> Optional[float]:
        """
        Get satisfaction rate for a specific feedback item.

        Args:
            feedback_id: Feedback item ID

        Returns:
            Satisfaction rate (0.0 to 1.0), or None if no ratings
        """
        try:
            with get_db() as db:
                total = db.query(UserSatisfaction).filter(
                    UserSatisfaction.feedback_id == feedback_id
                ).count()

                if total == 0:
                    return None

                satisfied = db.query(UserSatisfaction).filter(
                    UserSatisfaction.feedback_id == feedback_id,
                    UserSatisfaction.satisfied == True
                ).count()

                return satisfied / total

        except Exception as e:
            logger.error(f"AN-001: Error getting satisfaction rate for feedback {feedback_id}: {e}")
            return None

    @staticmethod
    def get_user_satisfaction_stats(user_id: int) -> Dict:
        """
        Get satisfaction statistics for a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dict with satisfaction stats
        """
        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if not user:
                    return {
                        "total_ratings": 0,
                        "satisfied_count": 0,
                        "unsatisfied_count": 0,
                        "satisfaction_rate": None
                    }

                # Get all satisfaction entries for this user
                total = db.query(UserSatisfaction).filter(
                    UserSatisfaction.user_id == user.id
                ).count()

                satisfied = db.query(UserSatisfaction).filter(
                    UserSatisfaction.user_id == user.id,
                    UserSatisfaction.satisfied == True
                ).count()

                unsatisfied = total - satisfied

                return {
                    "total_ratings": total,
                    "satisfied_count": satisfied,
                    "unsatisfied_count": unsatisfied,
                    "satisfaction_rate": satisfied / total if total > 0 else None
                }

        except Exception as e:
            logger.error(f"AN-001: Error getting user satisfaction stats for user {user_id}: {e}")
            return {
                "total_ratings": 0,
                "satisfied_count": 0,
                "unsatisfied_count": 0,
                "satisfaction_rate": None
            }

    @staticmethod
    def get_overall_satisfaction_rate(days: Optional[int] = None) -> Dict:
        """
        Get overall satisfaction rate across all feedback.

        Args:
            days: Optional number of days to look back (None for all time)

        Returns:
            Dict with overall satisfaction metrics
        """
        try:
            with get_db() as db:
                query = db.query(UserSatisfaction)

                # Filter by date if specified
                if days:
                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    query = query.filter(UserSatisfaction.created_at >= cutoff_date)

                total = query.count()

                if total == 0:
                    return {
                        "total_ratings": 0,
                        "satisfied_count": 0,
                        "unsatisfied_count": 0,
                        "satisfaction_rate": None,
                        "period_days": days
                    }

                satisfied = query.filter(UserSatisfaction.satisfied == True).count()
                unsatisfied = total - satisfied

                return {
                    "total_ratings": total,
                    "satisfied_count": satisfied,
                    "unsatisfied_count": unsatisfied,
                    "satisfaction_rate": satisfied / total,
                    "period_days": days
                }

        except Exception as e:
            logger.error(f"AN-001: Error getting overall satisfaction rate: {e}")
            return {
                "total_ratings": 0,
                "satisfied_count": 0,
                "unsatisfied_count": 0,
                "satisfaction_rate": None,
                "period_days": days
            }

    @staticmethod
    def get_low_satisfaction_feedback(threshold: float = 0.5, min_ratings: int = 3) -> List[Dict]:
        """
        Get feedback items with low satisfaction ratings for RLHF.

        Args:
            threshold: Satisfaction rate threshold (default 0.5 = 50%)
            min_ratings: Minimum number of ratings required

        Returns:
            List of feedback items with low satisfaction
        """
        try:
            with get_db() as db:
                # Get feedback items with satisfaction counts
                results = db.query(
                    Feedback.id,
                    Feedback.feedback_type,
                    Feedback.content,
                    Feedback.status,
                    func.count(UserSatisfaction.id).label('rating_count'),
                    func.sum(func.cast(UserSatisfaction.satisfied, Integer)).label('satisfied_count')
                ).join(
                    UserSatisfaction,
                    Feedback.id == UserSatisfaction.feedback_id
                ).group_by(
                    Feedback.id
                ).having(
                    func.count(UserSatisfaction.id) >= min_ratings
                ).all()

                # Filter by satisfaction rate
                low_satisfaction = []
                for result in results:
                    rating_count = result.rating_count
                    satisfied_count = result.satisfied_count or 0
                    satisfaction_rate = satisfied_count / rating_count if rating_count > 0 else 0

                    if satisfaction_rate < threshold:
                        low_satisfaction.append({
                            "feedback_id": result.id,
                            "feedback_type": result.feedback_type,
                            "content_preview": result.content[:100] if result.content else "",
                            "status": result.status,
                            "rating_count": rating_count,
                            "satisfied_count": satisfied_count,
                            "satisfaction_rate": satisfaction_rate
                        })

                # Sort by satisfaction rate (lowest first)
                low_satisfaction.sort(key=lambda x: x["satisfaction_rate"])

                return low_satisfaction

        except Exception as e:
            logger.error(f"AN-001: Error getting low satisfaction feedback: {e}")
            return []

    @staticmethod
    def get_satisfaction_trend(days: int = 30) -> List[Dict]:
        """
        Get satisfaction trend over time for visualization.

        Args:
            days: Number of days to look back

        Returns:
            List of daily satisfaction rates
        """
        try:
            with get_db() as db:
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                # Get ratings grouped by date
                results = db.query(
                    func.date(UserSatisfaction.created_at).label('date'),
                    func.count(UserSatisfaction.id).label('total'),
                    func.sum(func.cast(UserSatisfaction.satisfied, Integer)).label('satisfied')
                ).filter(
                    UserSatisfaction.created_at >= cutoff_date
                ).group_by(
                    func.date(UserSatisfaction.created_at)
                ).order_by(
                    func.date(UserSatisfaction.created_at)
                ).all()

                trend = []
                for result in results:
                    total = result.total
                    satisfied = result.satisfied or 0
                    trend.append({
                        "date": result.date.isoformat() if result.date else None,
                        "total_ratings": total,
                        "satisfied_count": satisfied,
                        "satisfaction_rate": satisfied / total if total > 0 else 0
                    })

                return trend

        except Exception as e:
            logger.error(f"AN-001: Error getting satisfaction trend: {e}")
            return []


# Global instance
_satisfaction_analytics: Optional[SatisfactionAnalytics] = None


def get_satisfaction_analytics() -> SatisfactionAnalytics:
    """Get or create the global satisfaction analytics instance."""
    global _satisfaction_analytics
    if _satisfaction_analytics is None:
        _satisfaction_analytics = SatisfactionAnalytics()
    return _satisfaction_analytics


if __name__ == "__main__":
    # Test the analytics
    print("=" * 60)
    print("AN-001: User Satisfaction Analytics Tests")
    print("=" * 60)

    analytics = get_satisfaction_analytics()

    print("\n1. Overall Satisfaction Rate (All Time):")
    overall = analytics.get_overall_satisfaction_rate()
    print(f"   Total Ratings: {overall['total_ratings']}")
    print(f"   Satisfied: {overall['satisfied_count']}")
    print(f"   Unsatisfied: {overall['unsatisfied_count']}")
    if overall['satisfaction_rate'] is not None:
        print(f"   Satisfaction Rate: {overall['satisfaction_rate']:.1%}")
    else:
        print("   Satisfaction Rate: N/A (no ratings yet)")

    print("\n2. Overall Satisfaction Rate (Last 7 Days):")
    recent = analytics.get_overall_satisfaction_rate(days=7)
    print(f"   Total Ratings: {recent['total_ratings']}")
    if recent['satisfaction_rate'] is not None:
        print(f"   Satisfaction Rate: {recent['satisfaction_rate']:.1%}")
    else:
        print("   Satisfaction Rate: N/A (no ratings yet)")

    print("\n3. Low Satisfaction Feedback (needs attention):")
    low_sat = analytics.get_low_satisfaction_feedback(threshold=0.6, min_ratings=2)
    if low_sat:
        for item in low_sat[:5]:
            print(f"   Feedback #{item['feedback_id']}: {item['satisfaction_rate']:.1%} satisfied")
            print(f"      {item['content_preview']}")
    else:
        print("   No low satisfaction items found (good!)")

    print("\n" + "=" * 60)
