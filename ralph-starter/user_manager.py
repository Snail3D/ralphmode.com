#!/usr/bin/env python3
"""
MU-001: User Tier System for Ralph Mode Bot

Implements tiered user access:
- Tier 1: Mr. Worms/Owner - Full control, admin powers, directs the build
- Tier 2: Power Users - Can control bot actions, authenticated via /password
- Tier 3: Chatters - Can chat with Ralph, but input doesn't affect build
- Tier 4: Viewers - View only, no interaction

Tiers persist across sessions via database storage.
"""

import os
import logging
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

# Import database for persistence
try:
    from database import get_db, User, InputValidator
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logging.warning("MU-001: Database not available - tier system will use in-memory storage only")

logger = logging.getLogger(__name__)


class UserTier(Enum):
    """User access tiers for the Ralph Mode system."""

    TIER_1_OWNER = 1      # Mr. Worms - Full control
    TIER_2_POWER = 2      # Power Users - Can control bot
    TIER_3_CHATTER = 3    # Chatters - Can chat only
    TIER_4_VIEWER = 4     # Viewers - Read-only

    @property
    def display_name(self) -> str:
        """Get a human-readable name for this tier."""
        return {
            UserTier.TIER_1_OWNER: "Mr. Worms (Owner)",
            UserTier.TIER_2_POWER: "Power User",
            UserTier.TIER_3_CHATTER: "Chatter",
            UserTier.TIER_4_VIEWER: "Viewer",
        }[self]

    @property
    def can_control_build(self) -> bool:
        """Can this tier control bot actions and direct the build?"""
        return self in [UserTier.TIER_1_OWNER, UserTier.TIER_2_POWER]

    @property
    def can_chat(self) -> bool:
        """Can this tier chat with Ralph?"""
        return self in [UserTier.TIER_1_OWNER, UserTier.TIER_2_POWER, UserTier.TIER_3_CHATTER]

    @property
    def can_view(self) -> bool:
        """Can this tier view the session?"""
        return True  # All tiers can view

    @property
    def has_admin_powers(self) -> bool:
        """Does this tier have admin powers?"""
        return self == UserTier.TIER_1_OWNER


class UserManager:
    """
    Manages user tiers, authentication, and permissions.

    Features:
    - Persistent tier storage via database
    - Default tier configuration
    - Tier-based permission checking
    - Power user authentication via password
    """

    def __init__(self, default_tier: UserTier = UserTier.TIER_4_VIEWER):
        """
        Initialize the user manager.

        Args:
            default_tier: Default tier for new users
        """
        self.default_tier = default_tier
        self._in_memory_tiers: Dict[int, UserTier] = {}

        # Load power user password from environment
        self.power_user_password = os.environ.get("POWER_USER_PASSWORD", "")
        if not self.power_user_password:
            logger.warning("MU-001: POWER_USER_PASSWORD not set - power user authentication disabled")

        # Load owner ID from environment
        self.owner_id = self._load_owner_id()
        if self.owner_id:
            logger.info(f"MU-001: Owner ID configured: {self.owner_id}")
        else:
            logger.warning("MU-001: TELEGRAM_OWNER_ID not set - no owner configured")

    def _load_owner_id(self) -> Optional[int]:
        """Load the owner's Telegram ID from environment."""
        owner_id_str = os.environ.get("TELEGRAM_OWNER_ID", "")
        if owner_id_str:
            try:
                return int(owner_id_str)
            except ValueError:
                logger.error(f"Invalid TELEGRAM_OWNER_ID: {owner_id_str}")
        return None

    def get_user_tier(self, telegram_id: int) -> UserTier:
        """
        Get the tier for a user.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User's tier (or default tier for new users)
        """
        # Validate input
        if not InputValidator.validate_telegram_id(telegram_id):
            logger.warning(f"Invalid telegram_id: {telegram_id}")
            return self.default_tier

        # Check if user is the configured owner
        if self.owner_id and telegram_id == self.owner_id:
            return UserTier.TIER_1_OWNER

        # Try database first
        if DATABASE_AVAILABLE:
            try:
                with get_db() as db:
                    user = db.query(User).filter(User.telegram_id == telegram_id).first()
                    if user and hasattr(user, 'access_tier'):
                        tier_value = getattr(user, 'access_tier')
                        try:
                            return UserTier(tier_value)
                        except ValueError:
                            logger.warning(f"Invalid tier value in database: {tier_value}")
            except Exception as e:
                logger.error(f"Error fetching user tier from database: {e}")

        # Fall back to in-memory storage
        if telegram_id in self._in_memory_tiers:
            return self._in_memory_tiers[telegram_id]

        # Return default tier for new users
        return self.default_tier

    def set_user_tier(self, telegram_id: int, tier: UserTier) -> bool:
        """
        Set the tier for a user.

        Args:
            telegram_id: Telegram user ID
            tier: New tier to assign

        Returns:
            True if successful, False otherwise
        """
        # Validate input
        if not InputValidator.validate_telegram_id(telegram_id):
            logger.warning(f"Invalid telegram_id: {telegram_id}")
            return False

        # Store in in-memory cache
        self._in_memory_tiers[telegram_id] = tier

        # Try to persist to database
        if DATABASE_AVAILABLE:
            try:
                with get_db() as db:
                    user = db.query(User).filter(User.telegram_id == telegram_id).first()
                    if user:
                        # Update existing user
                        if not hasattr(User, 'access_tier'):
                            logger.warning("User model doesn't have access_tier column - will add in next migration")
                        else:
                            setattr(user, 'access_tier', tier.value)
                            db.commit()
                            logger.info(f"Updated tier for user {telegram_id}: {tier.display_name}")
                    else:
                        # Create new user
                        logger.warning(f"User {telegram_id} not in database - tier stored in memory only")
                return True
            except Exception as e:
                logger.error(f"Error setting user tier in database: {e}")
                # Continue with in-memory storage

        logger.info(f"Set tier for user {telegram_id}: {tier.display_name} (in-memory)")
        return True

    def authenticate_power_user(self, telegram_id: int, password: str) -> bool:
        """
        Authenticate a user as a power user.

        Args:
            telegram_id: Telegram user ID
            password: Password to verify

        Returns:
            True if authentication successful and tier upgraded
        """
        if not self.power_user_password:
            logger.warning("Power user authentication attempted but no password configured")
            return False

        if password == self.power_user_password:
            # Upgrade to Tier 2
            success = self.set_user_tier(telegram_id, UserTier.TIER_2_POWER)
            if success:
                logger.info(f"User {telegram_id} authenticated as power user")
            return success
        else:
            logger.warning(f"Failed power user authentication for user {telegram_id}")
            return False

    def can_control_build(self, telegram_id: int) -> bool:
        """Check if user can control bot actions and direct the build."""
        tier = self.get_user_tier(telegram_id)
        return tier.can_control_build

    def can_chat(self, telegram_id: int) -> bool:
        """Check if user can chat with Ralph."""
        tier = self.get_user_tier(telegram_id)
        return tier.can_chat

    def can_view(self, telegram_id: int) -> bool:
        """Check if user can view the session."""
        tier = self.get_user_tier(telegram_id)
        return tier.can_view

    def has_admin_powers(self, telegram_id: int) -> bool:
        """Check if user has admin powers."""
        tier = self.get_user_tier(telegram_id)
        return tier.has_admin_powers

    def get_user_info(self, telegram_id: int) -> Dict[str, Any]:
        """
        Get comprehensive information about a user.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Dictionary with user tier and permissions
        """
        tier = self.get_user_tier(telegram_id)
        return {
            "telegram_id": telegram_id,
            "tier": tier.value,
            "tier_name": tier.display_name,
            "can_control_build": tier.can_control_build,
            "can_chat": tier.can_chat,
            "can_view": tier.can_view,
            "has_admin_powers": tier.has_admin_powers,
            "is_owner": telegram_id == self.owner_id if self.owner_id else False,
        }


# Global instance
_user_manager: Optional[UserManager] = None


def get_user_manager(default_tier: UserTier = UserTier.TIER_4_VIEWER) -> UserManager:
    """
    Get the global UserManager instance (singleton pattern).

    Args:
        default_tier: Default tier for new users (only used on first call)

    Returns:
        UserManager instance
    """
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager(default_tier=default_tier)
    return _user_manager


# Migration helper: Add access_tier column to User model
def add_tier_column_to_user():
    """
    Helper function to add the access_tier column to the User model.
    This should be called during database initialization.
    """
    if not DATABASE_AVAILABLE:
        return

    try:
        from sqlalchemy import Column, Integer

        # Check if column already exists
        if hasattr(User, 'access_tier'):
            logger.info("access_tier column already exists in User model")
            return

        # This is a simple migration - in production, use Alembic
        logger.warning("access_tier column needs to be added to User model")
        logger.warning("Please add: access_tier = Column(Integer, default=4)  # Default to Tier 4 (Viewer)")

    except Exception as e:
        logger.error(f"Error checking for access_tier column: {e}")
