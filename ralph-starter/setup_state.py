#!/usr/bin/env python3
"""
Setup State Manager for Ralph Mode Onboarding

Manages persistent state for the onboarding wizard, allowing users
to resume interrupted setup sessions.

Features:
- Saves progress to database
- Detects incomplete setups
- Offers resume or restart options
- Handles expired/stale setups
- Shows what's already completed
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# Database imports
try:
    from database import get_db, User, BotSession
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logging.warning("Database not available - setup state will not persist")


logger = logging.getLogger(__name__)


class SetupStateManager:
    """Manages onboarding setup state with database persistence."""

    # Setup expiration time (48 hours)
    SETUP_EXPIRATION_HOURS = 48

    # Minimum steps for a setup to be considered "in progress"
    MIN_STEPS_FOR_RESUME = 1

    def __init__(self):
        """Initialize the setup state manager."""
        self.logger = logging.getLogger(__name__)

    def save_setup_state(
        self,
        user_id: int,
        telegram_id: int,
        state: Dict[str, Any]
    ) -> bool:
        """Save the current setup state to the database.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID
            state: Current onboarding state dictionary

        Returns:
            True if saved successfully, False otherwise
        """
        if not DATABASE_AVAILABLE:
            self.logger.warning("Database not available, cannot save setup state")
            return False

        try:
            with get_db() as db:
                # Find or create onboarding session
                session = (
                    db.query(BotSession)
                    .filter(
                        BotSession.user_id == user_id,
                        BotSession.status == "onboarding"
                    )
                    .first()
                )

                if not session:
                    # Create new onboarding session
                    session = BotSession(
                        user_id=user_id,
                        chat_id=telegram_id,  # For 1-on-1 chats, chat_id == telegram_id
                        status="onboarding",
                        project_name="Ralph Mode Setup",
                        session_data=json.dumps(state)
                    )
                    db.add(session)
                else:
                    # Update existing session
                    session.session_data = json.dumps(state)
                    session.updated_at = datetime.utcnow()

                db.commit()
                self.logger.info(f"Saved setup state for user {telegram_id}")
                return True

        except Exception as e:
            self.logger.error(f"Error saving setup state: {e}")
            return False

    def load_setup_state(
        self,
        user_id: int,
        telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        """Load the setup state from the database.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            Setup state dictionary if found, None otherwise
        """
        if not DATABASE_AVAILABLE:
            return None

        try:
            with get_db() as db:
                # Find onboarding session
                session = (
                    db.query(BotSession)
                    .filter(
                        BotSession.user_id == user_id,
                        BotSession.status == "onboarding"
                    )
                    .first()
                )

                if session and session.session_data:
                    state = json.loads(session.session_data)
                    self.logger.info(f"Loaded setup state for user {telegram_id}")
                    return state

                return None

        except Exception as e:
            self.logger.error(f"Error loading setup state: {e}")
            return None

    def has_incomplete_setup(
        self,
        user_id: int,
        telegram_id: int
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if user has an incomplete setup session.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            Tuple of (has_incomplete_setup, state_dict)
        """
        state = self.load_setup_state(user_id, telegram_id)

        if not state:
            return False, None

        # Check if setup is completed
        if state.get("step") == "complete":
            return False, None

        # Check if setup has any progress
        progress_count = sum([
            state.get("ssh_key_generated", False),
            state.get("ssh_key_added_to_github", False),
            state.get("repo_created", False),
            state.get("git_configured", False),
        ])

        if progress_count < self.MIN_STEPS_FOR_RESUME:
            # Not enough progress to resume
            return False, None

        # Check if setup is stale
        if self.is_setup_stale(state):
            return False, None

        return True, state

    def is_setup_stale(self, state: Dict[str, Any]) -> bool:
        """Check if a setup session is stale (too old).

        Args:
            state: Setup state dictionary

        Returns:
            True if stale, False otherwise
        """
        started_at = state.get("started_at")

        if not started_at:
            # No start time, consider it stale
            return True

        try:
            # Parse the start time
            if isinstance(started_at, str):
                start_time = datetime.fromisoformat(started_at)
            else:
                start_time = started_at

            # Check if it's older than expiration threshold
            expiration_time = start_time + timedelta(hours=self.SETUP_EXPIRATION_HOURS)

            return datetime.utcnow() > expiration_time

        except (TypeError, ValueError) as e:
            self.logger.error(f"Error parsing setup start time: {e}")
            return True

    def get_setup_age_message(self, state: Dict[str, Any]) -> str:
        """Get a human-readable message about setup age.

        Args:
            state: Setup state dictionary

        Returns:
            Age description string
        """
        started_at = state.get("started_at")

        if not started_at:
            return "Unknown"

        try:
            if isinstance(started_at, str):
                start_time = datetime.fromisoformat(started_at)
            else:
                start_time = started_at

            age = datetime.utcnow() - start_time

            # Format based on age
            if age.days > 0:
                return f"{age.days} day{'s' if age.days != 1 else ''} ago"
            elif age.seconds >= 3600:
                hours = age.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif age.seconds >= 60:
                minutes = age.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "Just now"

        except (TypeError, ValueError):
            return "Unknown"

    def clear_setup_state(self, user_id: int, telegram_id: int) -> bool:
        """Clear/delete the setup state for a user.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            True if cleared successfully, False otherwise
        """
        if not DATABASE_AVAILABLE:
            return False

        try:
            with get_db() as db:
                # Find and delete onboarding session
                session = (
                    db.query(BotSession)
                    .filter(
                        BotSession.user_id == user_id,
                        BotSession.status == "onboarding"
                    )
                    .first()
                )

                if session:
                    db.delete(session)
                    db.commit()
                    self.logger.info(f"Cleared setup state for user {telegram_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error clearing setup state: {e}")
            return False

    def mark_setup_complete(self, user_id: int, telegram_id: int) -> bool:
        """Mark the setup as completed.

        Args:
            user_id: Database user ID
            telegram_id: Telegram user ID

        Returns:
            True if marked successfully, False otherwise
        """
        if not DATABASE_AVAILABLE:
            return False

        try:
            with get_db() as db:
                # Find onboarding session
                session = (
                    db.query(BotSession)
                    .filter(
                        BotSession.user_id == user_id,
                        BotSession.status == "onboarding"
                    )
                    .first()
                )

                if session:
                    # Update status to completed
                    session.status = "completed"
                    session.ended_at = datetime.utcnow()
                    db.commit()
                    self.logger.info(f"Marked setup complete for user {telegram_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error marking setup complete: {e}")
            return False

    def get_resume_message(self, state: Dict[str, Any]) -> str:
        """Generate a message showing resumable progress.

        Args:
            state: Setup state dictionary

        Returns:
            Progress message with what's already done
        """
        age = self.get_setup_age_message(state)

        completed = []
        pending = []

        # Check what's done
        if state.get("ssh_key_generated"):
            completed.append("SSH key generated")
        else:
            pending.append("Generate SSH key")

        if state.get("ssh_key_added_to_github"):
            completed.append("SSH key added to GitHub")
        else:
            pending.append("Add SSH key to GitHub")

        if state.get("repo_created"):
            completed.append("Repository created")
        else:
            pending.append("Create repository")

        if state.get("git_configured"):
            completed.append("Git configured")
        else:
            pending.append("Configure Git")

        completed_text = "\n".join([f"✅ {item}" for item in completed]) if completed else "Nothing yet"
        pending_text = "\n".join([f"⬜ {item}" for item in pending]) if pending else "All done!"

        return f"""*Ralph found your unfinished setup!* 🔧

You started setting up {age}!

*What you already did:*
{completed_text}

*What's left to do:*
{pending_text}

*Wanna pick up where you left off?*
"""

    def save_config_history(self, user_id: int, history: list) -> bool:
        """Save configuration change history for a user - OB-049.

        Args:
            user_id: Telegram user ID
            history: List of configuration change records

        Returns:
            True if saved successfully
        """
        if not DATABASE_AVAILABLE:
            self.logger.warning("Database not available, cannot save config history")
            return False

        try:
            with get_db() as db:
                # Find or create user
                user = db.query(User).filter(User.telegram_id == user_id).first()

                if not user:
                    self.logger.error(f"User {user_id} not found in database")
                    return False

                # Store in a BotSession with special status
                session = (
                    db.query(BotSession)
                    .filter(
                        BotSession.user_id == user.id,
                        BotSession.status == "config_history"
                    )
                    .first()
                )

                if not session:
                    # Create new config history session
                    session = BotSession(
                        user_id=user.id,
                        chat_id=user_id,
                        status="config_history",
                        project_name="Configuration History",
                        session_data=json.dumps({"history": history})
                    )
                    db.add(session)
                else:
                    # Update existing
                    session.session_data = json.dumps({"history": history})
                    session.updated_at = datetime.utcnow()

                db.commit()
                self.logger.info(f"OB-049: Saved config history for user {user_id}")
                return True

        except Exception as e:
            self.logger.error(f"OB-049: Error saving config history: {e}")
            return False

    def get_config_history(self, user_id: int) -> list:
        """Get configuration change history for a user - OB-049.

        Args:
            user_id: Telegram user ID

        Returns:
            List of configuration change records
        """
        if not DATABASE_AVAILABLE:
            return []

        try:
            with get_db() as db:
                # Find user
                user = db.query(User).filter(User.telegram_id == user_id).first()

                if not user:
                    return []

                # Find config history session
                session = (
                    db.query(BotSession)
                    .filter(
                        BotSession.user_id == user.id,
                        BotSession.status == "config_history"
                    )
                    .first()
                )

                if session and session.session_data:
                    data = json.loads(session.session_data)
                    history = data.get("history", [])
                    self.logger.info(f"OB-049: Loaded config history for user {user_id}")
                    return history

                return []

        except Exception as e:
            self.logger.error(f"OB-049: Error loading config history: {e}")
            return []


def get_setup_state_manager() -> SetupStateManager:
    """Get the setup state manager instance.

    Returns:
        SetupStateManager instance
    """
    return SetupStateManager()
