#!/usr/bin/env python3
"""
FB-002: Subscription Gate for Feedback

This module manages subscription tiers and access control for the feedback system.

Subscription Tiers:
- free: No feedback access (viewer tier)
- builder: $10/mo - Can submit feedback with weight 1.0
- priority: $20/mo - Can submit feedback with weight 2.0
- enterprise: Custom pricing - Premium features

Weight determines how much the feedback influences the RLHF loop.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from database import get_db, User

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Manages subscription tiers and access control."""

    # Subscription tier definitions
    TIERS = {
        "free": {
            "name": "Viewer",
            "can_feedback": False,
            "feedback_weight": 0.0,
            "monthly_price": 0
        },
        "builder": {
            "name": "Builder",
            "can_feedback": True,
            "feedback_weight": 1.0,
            "monthly_price": 10
        },
        "priority": {
            "name": "Priority",
            "can_feedback": True,
            "feedback_weight": 2.0,
            "monthly_price": 20
        },
        "enterprise": {
            "name": "Enterprise",
            "can_feedback": True,
            "feedback_weight": 3.0,
            "monthly_price": None  # Custom pricing
        }
    }

    def __init__(self):
        """Initialize the subscription manager."""
        pass

    def get_user_tier(self, telegram_id: int) -> str:
        """
        Get the subscription tier for a user.

        Args:
            telegram_id: The user's Telegram ID

        Returns:
            Subscription tier string (free, builder, priority, enterprise)
        """
        with get_db() as db:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                return user.subscription_tier or "free"
            return "free"

    def can_submit_feedback(self, telegram_id: int) -> Tuple[bool, Optional[str], float]:
        """
        Check if a user can submit feedback based on their subscription tier.

        Args:
            telegram_id: The user's Telegram ID

        Returns:
            Tuple of (can_submit: bool, tier_name: str, weight: float)
        """
        tier = self.get_user_tier(telegram_id)
        tier_info = self.TIERS.get(tier, self.TIERS["free"])

        return (
            tier_info["can_feedback"],
            tier_info["name"],
            tier_info["feedback_weight"]
        )

    def get_feedback_weight(self, telegram_id: int) -> float:
        """
        Get the feedback weight multiplier for a user.

        Higher tier = higher weight = more influence on RLHF loop.

        Args:
            telegram_id: The user's Telegram ID

        Returns:
            Weight multiplier (0.0 to 3.0)
        """
        tier = self.get_user_tier(telegram_id)
        tier_info = self.TIERS.get(tier, self.TIERS["free"])
        return tier_info["feedback_weight"]

    def get_upgrade_message(self, current_tier: str = "free") -> str:
        """
        Get an upgrade message showing available tiers.

        Args:
            current_tier: The user's current tier

        Returns:
            Formatted upgrade message
        """
        if current_tier == "free":
            return (
                "🎭 **Want to shape Ralph Mode's future?**\n\n"
                "Your feedback helps us build what YOU want! Choose your tier:\n\n"
                "🔨 **Builder** - $10/mo\n"
                "   • Submit feature requests & bug reports\n"
                "   • Influence the roadmap\n"
                "   • Standard priority in the queue\n\n"
                "⚡ **Priority** - $20/mo\n"
                "   • Everything in Builder\n"
                "   • 2x feedback weight (jump the queue!)\n"
                "   • Early access to new features\n\n"
                "Use `/subscribe` to upgrade and start influencing Ralph's team!"
            )
        elif current_tier == "builder":
            return (
                "⚡ **Upgrade to Priority** - $20/mo\n\n"
                "Get 2x feedback weight and jump the queue!\n"
                "Your ideas get built faster.\n\n"
                "Use `/subscribe` to upgrade!"
            )
        else:
            return "You're already on a premium tier! Thank you for your support! 🎉"

    def update_user_tier(self, telegram_id: int, new_tier: str) -> bool:
        """
        Update a user's subscription tier.

        Args:
            telegram_id: The user's Telegram ID
            new_tier: The new tier (free, builder, priority, enterprise)

        Returns:
            True if successful, False otherwise
        """
        if new_tier not in self.TIERS:
            logger.error(f"Invalid tier: {new_tier}")
            return False

        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    user.subscription_tier = new_tier
                    user.updated_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"Updated user {telegram_id} to tier {new_tier}")
                    return True
                else:
                    logger.warning(f"User {telegram_id} not found")
                    return False
        except Exception as e:
            logger.error(f"Failed to update user tier: {e}")
            return False

    def get_tier_info(self, tier: str) -> dict:
        """
        Get information about a subscription tier.

        Args:
            tier: The tier name

        Returns:
            Dict with tier information
        """
        return self.TIERS.get(tier, self.TIERS["free"])


# Singleton instance
_subscription_manager = None

def get_subscription_manager() -> SubscriptionManager:
    """Get the global subscription manager instance."""
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = SubscriptionManager()
    return _subscription_manager


if __name__ == "__main__":
    # Test the subscription manager
    print("=" * 60)
    print("FB-002: Subscription Manager Tests")
    print("=" * 60)

    manager = get_subscription_manager()

    print("\nTier definitions:")
    for tier_name, tier_info in manager.TIERS.items():
        print(f"  {tier_name}: {tier_info['name']} - "
              f"Can feedback: {tier_info['can_feedback']}, "
              f"Weight: {tier_info['feedback_weight']}")

    print("\nUpgrade message (free tier):")
    print(manager.get_upgrade_message("free"))

    print("\n" + "=" * 60)
    print("✅ Subscription manager initialized successfully")
    print("=" * 60)
