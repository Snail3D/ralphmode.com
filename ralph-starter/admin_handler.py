#!/usr/bin/env python3
"""
SF-003: Admin Override Controls for Ralph Mode Bot

This module provides admin commands to control the build orchestrator:
- /admin pause - Stop build loop
- /admin resume - Restart build loop
- /admin deploy FB-XXX - Force deploy a specific feedback item
- /admin rollback - Revert to previous version
- /admin prioritize FB-XXX - Boost priority of a feedback item
- /admin reject FB-XXX - Remove feedback item from queue

Admin commands are restricted to users with TELEGRAM_ADMIN_ID.

Usage:
    from admin_handler import AdminHandler

    admin = AdminHandler(bot_instance)
    await admin.handle_pause(update, context)
    await admin.handle_resume(update, context)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from database import get_db, Feedback
from feedback_queue import get_feedback_queue
from circuit_breaker import get_circuit_breaker
from deploy_manager import DeployManager, DeploymentResult

logger = logging.getLogger(__name__)

# Admin user ID from environment
ADMIN_USER_ID = os.getenv('TELEGRAM_ADMIN_ID')

# Pause flag file (used by build orchestrator)
PAUSE_FLAG_FILE = Path('/tmp/ralph_build_paused.flag')

# AC-003: User cooldown storage (user_id -> cooldown_seconds)
# Format: {user_id: {'cooldown_seconds': int, 'last_message_time': timestamp}}
USER_COOLDOWNS: Dict[int, Dict[str, any]] = {}


class AdminHandler:
    """
    SF-003: Admin Override Controls

    Provides privileged commands for controlling the build orchestrator.
    """

    def __init__(self, bot_instance=None):
        """
        Initialize the admin handler.

        Args:
            bot_instance: Reference to RalphBot instance (optional, for future features)
        """
        self.bot = bot_instance
        self.deploy_manager = DeployManager()
        self.circuit_breaker = get_circuit_breaker()

    def is_admin(self, user_id: int) -> bool:
        """
        Check if user is an admin.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user is admin, False otherwise
        """
        if not ADMIN_USER_ID:
            logger.warning("TELEGRAM_ADMIN_ID not set in environment")
            return False

        try:
            admin_id = int(ADMIN_USER_ID)
            return user_id == admin_id
        except ValueError:
            logger.error(f"Invalid TELEGRAM_ADMIN_ID: {ADMIN_USER_ID}")
            return False

    async def handle_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Main handler for /admin commands. Routes to appropriate subcommand.

        Usage:
            /admin pause
            /admin resume
            /admin deploy FB-123
            /admin rollback
            /admin prioritize FB-123
            /admin reject FB-123

        Args:
            update: Telegram update
            context: Callback context
        """
        user_id = update.effective_user.id

        # Check admin permissions
        if not self.is_admin(user_id):
            await update.message.reply_text(
                "❌ Unauthorized. Admin commands require special permissions."
            )
            logger.warning(f"Unauthorized admin command attempt by user {user_id}")
            return

        # Parse subcommand
        if not context.args:
            await self._show_admin_help(update)
            return

        subcommand = context.args[0].lower()

        # Route to appropriate handler
        handlers = {
            'pause': self.handle_pause,
            'resume': self.handle_resume,
            'deploy': self.handle_deploy,
            'rollback': self.handle_rollback,
            'prioritize': self.handle_prioritize,
            'reject': self.handle_reject,
            'cooldown': self.handle_set_cooldown,  # AC-003
        }

        handler = handlers.get(subcommand)
        if handler:
            await handler(update, context)
        else:
            await update.message.reply_text(
                f"❌ Unknown admin command: {subcommand}\n\n"
                "Use /admin to see available commands."
            )

    async def _show_admin_help(self, update: Update):
        """Show admin command help."""
        help_text = """🔧 **Admin Commands**

Available commands:

`/admin pause` - Stop build loop
Pauses the build orchestrator. No new builds will start.

`/admin resume` - Restart build loop
Resumes the build orchestrator after a pause.

`/admin deploy FB-XXX` - Force deploy
Force deploy a specific feedback item, bypassing normal queue.

`/admin rollback` - Revert to previous
Rollback to the previous deployed version.

`/admin prioritize FB-XXX` - Boost priority
Increase priority score of a feedback item to move it to front of queue.

`/admin reject FB-XXX` - Remove from queue
Reject a feedback item and remove it from the queue.

`/admin cooldown <user_id> <duration> <unit>` - Set message cooldown
Limit how often a user can message. Units: seconds, minutes, hours.
Use `/admin cooldown <user_id> 0` to remove cooldown.

Examples:
`/admin pause`
`/admin deploy FB-42`
`/admin prioritize FB-123`
`/admin cooldown 123456789 5 minutes`
`/admin cooldown 987654321 30 seconds`
`/admin cooldown 123456789 0` (remove)
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /admin pause - Stop build loop

        Creates a pause flag file that the orchestrator checks.
        """
        try:
            # Create pause flag
            pause_data = {
                'paused_at': datetime.utcnow().isoformat(),
                'paused_by': update.effective_user.id,
                'paused_by_username': update.effective_user.username or 'Unknown',
                'reason': 'Manual admin pause'
            }

            with open(PAUSE_FLAG_FILE, 'w') as f:
                json.dump(pause_data, f, indent=2)

            logger.info(f"Build loop PAUSED by admin {update.effective_user.id}")

            await update.message.reply_text(
                "⏸️ **Build Loop Paused**\n\n"
                "The build orchestrator will stop processing new items.\n"
                "Current build (if any) will complete.\n\n"
                "Use `/admin resume` to restart.",
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Error pausing build loop: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error pausing build loop: {str(e)}"
            )

    async def handle_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /admin resume - Restart build loop

        Removes the pause flag and resets the circuit breaker if needed.
        """
        try:
            # Remove pause flag
            if PAUSE_FLAG_FILE.exists():
                PAUSE_FLAG_FILE.unlink()
                logger.info(f"Build loop RESUMED by admin {update.effective_user.id}")
                message = "▶️ **Build Loop Resumed**\n\n" \
                         "The build orchestrator will start processing items again."
            else:
                message = "ℹ️ Build loop was not paused."

            # Reset circuit breaker if tripped
            if self.circuit_breaker.is_tripped():
                self.circuit_breaker.reset()
                message += "\n\n🔄 Circuit breaker has been reset."
                logger.info("Circuit breaker RESET by admin")

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error resuming build loop: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error resuming build loop: {str(e)}"
            )

    async def handle_deploy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /admin deploy FB-XXX - Force deploy

        Force deploy a specific feedback item, bypassing the normal queue.
        """
        try:
            # Parse feedback ID
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Usage: `/admin deploy FB-123`",
                    parse_mode='Markdown'
                )
                return

            fb_arg = context.args[1].upper()
            if not fb_arg.startswith('FB-'):
                await update.message.reply_text(
                    "❌ Invalid format. Use: `/admin deploy FB-123`",
                    parse_mode='Markdown'
                )
                return

            try:
                feedback_id = int(fb_arg.replace('FB-', ''))
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid feedback ID. Use: `/admin deploy FB-123`",
                    parse_mode='Markdown'
                )
                return

            # Check if feedback exists
            with get_db() as db:
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

                if not feedback:
                    await update.message.reply_text(
                        f"❌ Feedback item FB-{feedback_id} not found."
                    )
                    return

                await update.message.reply_text(
                    f"🚀 **Force Deploying FB-{feedback_id}**\n\n"
                    f"Type: {feedback.feedback_type}\n"
                    f"Content: {feedback.content[:100]}...\n\n"
                    f"Starting deployment...",
                    parse_mode='Markdown'
                )

                # Force deploy to staging
                result = self.deploy_manager.deploy_to_staging(feedback_id)

                if result.success:
                    # Update feedback status
                    queue = get_feedback_queue(db)
                    queue.update_status(feedback_id, "deployed_staging")

                    await update.message.reply_text(
                        f"✅ **Deploy Successful**\n\n"
                        f"FB-{feedback_id} deployed to staging:\n"
                        f"{result.staging_url}\n\n"
                        f"Branch: {result.branch_name}\n"
                        f"Commit: `{result.commit_hash[:8]}`",
                        parse_mode='Markdown'
                    )

                    logger.info(f"Admin force deploy SUCCESS: FB-{feedback_id}")
                else:
                    await update.message.reply_text(
                        f"❌ **Deploy Failed**\n\n"
                        f"Error: {result.error_message}",
                        parse_mode='Markdown'
                    )

                    logger.error(f"Admin force deploy FAILED: FB-{feedback_id} - {result.error_message}")

        except Exception as e:
            logger.error(f"Error in force deploy: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error deploying: {str(e)}"
            )

    async def handle_rollback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /admin rollback - Revert to previous version

        Rollback to the last stable deployment.
        """
        try:
            await update.message.reply_text(
                "🔄 **Rolling back to previous version...**",
                parse_mode='Markdown'
            )

            # Perform rollback
            result = self.deploy_manager.rollback()

            if result.success:
                await update.message.reply_text(
                    f"✅ **Rollback Successful**\n\n"
                    f"Reverted to previous version:\n"
                    f"Commit: `{result.commit_hash[:8] if result.commit_hash else 'unknown'}`\n"
                    f"URL: {result.staging_url or 'N/A'}",
                    parse_mode='Markdown'
                )

                logger.info(f"Admin rollback SUCCESS by user {update.effective_user.id}")
            else:
                await update.message.reply_text(
                    f"❌ **Rollback Failed**\n\n"
                    f"Error: {result.error_message}",
                    parse_mode='Markdown'
                )

                logger.error(f"Admin rollback FAILED: {result.error_message}")

        except Exception as e:
            logger.error(f"Error in rollback: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error rolling back: {str(e)}"
            )

    async def handle_prioritize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /admin prioritize FB-XXX - Boost priority

        Increase priority score of a feedback item to 9.5 (high priority).
        """
        try:
            # Parse feedback ID
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Usage: `/admin prioritize FB-123`",
                    parse_mode='Markdown'
                )
                return

            fb_arg = context.args[1].upper()
            if not fb_arg.startswith('FB-'):
                await update.message.reply_text(
                    "❌ Invalid format. Use: `/admin prioritize FB-123`",
                    parse_mode='Markdown'
                )
                return

            try:
                feedback_id = int(fb_arg.replace('FB-', ''))
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid feedback ID. Use: `/admin prioritize FB-123`",
                    parse_mode='Markdown'
                )
                return

            # Update priority
            with get_db() as db:
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

                if not feedback:
                    await update.message.reply_text(
                        f"❌ Feedback item FB-{feedback_id} not found."
                    )
                    return

                old_priority = feedback.priority_score or 0.0
                feedback.priority_score = 9.5  # High priority
                feedback.updated_at = datetime.utcnow()
                db.commit()

                await update.message.reply_text(
                    f"⬆️ **Priority Boosted**\n\n"
                    f"FB-{feedback_id}\n"
                    f"Priority: {old_priority:.2f} → 9.5\n\n"
                    f"This item will be processed next.",
                    parse_mode='Markdown'
                )

                logger.info(
                    f"Admin prioritize: FB-{feedback_id} priority {old_priority:.2f} -> 9.5 "
                    f"by user {update.effective_user.id}"
                )

        except Exception as e:
            logger.error(f"Error prioritizing feedback: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error prioritizing feedback: {str(e)}"
            )

    async def handle_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /admin reject FB-XXX - Remove from queue

        Reject a feedback item and remove it from the queue.
        """
        try:
            # Parse feedback ID
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Usage: `/admin reject FB-123`",
                    parse_mode='Markdown'
                )
                return

            fb_arg = context.args[1].upper()
            if not fb_arg.startswith('FB-'):
                await update.message.reply_text(
                    "❌ Invalid format. Use: `/admin reject FB-123`",
                    parse_mode='Markdown'
                )
                return

            try:
                feedback_id = int(fb_arg.replace('FB-', ''))
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid feedback ID. Use: `/admin reject FB-123`",
                    parse_mode='Markdown'
                )
                return

            # Reject feedback
            with get_db() as db:
                queue = get_feedback_queue(db)
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

                if not feedback:
                    await update.message.reply_text(
                        f"❌ Feedback item FB-{feedback_id} not found."
                    )
                    return

                # Update status to rejected
                queue.update_status(
                    feedback_id,
                    "rejected",
                    "Rejected by admin"
                )

                await update.message.reply_text(
                    f"🚫 **Feedback Rejected**\n\n"
                    f"FB-{feedback_id} has been removed from the queue.\n\n"
                    f"Type: {feedback.feedback_type}\n"
                    f"Content: {feedback.content[:100]}...",
                    parse_mode='Markdown'
                )

                logger.info(
                    f"Admin reject: FB-{feedback_id} rejected by user {update.effective_user.id}"
                )

        except Exception as e:
            logger.error(f"Error rejecting feedback: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error rejecting feedback: {str(e)}"
            )

    async def handle_set_cooldown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        AC-003: /admin cooldown <user_id> <duration> <unit>

        Set cooldown period for a user. User can only message once per cooldown period.

        Examples:
            /admin cooldown 123456789 5 minutes
            /admin cooldown 123456789 30 seconds
            /admin cooldown 123456789 0  (remove cooldown)

        Args:
            update: Telegram update
            context: Callback context with args [user_id, duration, unit]
        """
        try:
            # Parse arguments
            if len(context.args) < 3:
                await update.message.reply_text(
                    "❌ Usage: `/admin cooldown <user_id> <duration> <unit>`\n\n"
                    "Examples:\n"
                    "`/admin cooldown 123456789 5 minutes`\n"
                    "`/admin cooldown 123456789 30 seconds`\n"
                    "`/admin cooldown 123456789 0` (remove cooldown)",
                    parse_mode='Markdown'
                )
                return

            # Extract user_id
            try:
                target_user_id = int(context.args[1])
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid user ID. Must be a number.",
                    parse_mode='Markdown'
                )
                return

            # Extract duration
            try:
                duration = int(context.args[2])
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid duration. Must be a number.",
                    parse_mode='Markdown'
                )
                return

            # If duration is 0, remove cooldown
            if duration == 0:
                if target_user_id in USER_COOLDOWNS:
                    del USER_COOLDOWNS[target_user_id]
                    await update.message.reply_text(
                        f"✅ **Cooldown Removed**\n\n"
                        f"User `{target_user_id}` can now message without restriction.",
                        parse_mode='Markdown'
                    )
                    logger.info(f"AC-003: Cooldown removed for user {target_user_id} by admin {update.effective_user.id}")
                else:
                    await update.message.reply_text(
                        f"ℹ️ User `{target_user_id}` has no active cooldown.",
                        parse_mode='Markdown'
                    )
                return

            # Extract unit (minutes or seconds)
            if len(context.args) >= 4:
                unit = context.args[3].lower()
            else:
                unit = 'seconds'  # Default to seconds if not specified

            # Convert to seconds
            if unit.startswith('minute'):
                cooldown_seconds = duration * 60
                unit_display = 'minutes'
            elif unit.startswith('second'):
                cooldown_seconds = duration
                unit_display = 'seconds'
            elif unit.startswith('hour'):
                cooldown_seconds = duration * 3600
                unit_display = 'hours'
            else:
                await update.message.reply_text(
                    "❌ Invalid time unit. Use 'seconds', 'minutes', or 'hours'.",
                    parse_mode='Markdown'
                )
                return

            # Set cooldown for user
            USER_COOLDOWNS[target_user_id] = {
                'cooldown_seconds': cooldown_seconds,
                'last_message_time': None  # Will be set when they first message
            }

            await update.message.reply_text(
                f"⏱️ **Cooldown Set**\n\n"
                f"User `{target_user_id}` can now only message once every **{duration} {unit_display}**.\n\n"
                f"This restriction will persist until changed or removed.",
                parse_mode='Markdown'
            )

            logger.info(
                f"AC-003: Cooldown set for user {target_user_id}: {duration} {unit_display} "
                f"({cooldown_seconds}s) by admin {update.effective_user.id}"
            )

        except Exception as e:
            logger.error(f"AC-003: Error setting cooldown: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error setting cooldown: {str(e)}"
            )


def check_user_cooldown(user_id: int) -> Tuple[bool, Optional[int]]:
    """
    AC-003: Check if user is within their cooldown period.

    Args:
        user_id: Telegram user ID

    Returns:
        Tuple of (is_allowed, seconds_until_allowed)
        - is_allowed: True if user can message, False if in cooldown
        - seconds_until_allowed: How many seconds until user can message again (None if allowed)
    """
    if user_id not in USER_COOLDOWNS:
        return True, None

    cooldown_data = USER_COOLDOWNS[user_id]
    cooldown_seconds = cooldown_data['cooldown_seconds']
    last_message_time = cooldown_data['last_message_time']

    # First message - allow it and record timestamp
    if last_message_time is None:
        return True, None

    # Check if enough time has passed
    now = datetime.utcnow()
    time_since_last = (now - last_message_time).total_seconds()

    if time_since_last >= cooldown_seconds:
        return True, None
    else:
        seconds_remaining = int(cooldown_seconds - time_since_last)
        return False, seconds_remaining


def record_user_message(user_id: int):
    """
    AC-003: Record that a user sent a message (for cooldown tracking).

    Args:
        user_id: Telegram user ID
    """
    if user_id in USER_COOLDOWNS:
        USER_COOLDOWNS[user_id]['last_message_time'] = datetime.utcnow()


def setup_admin_handlers(application):
    """
    Register admin command handlers with the Telegram application.

    Args:
        application: Telegram Application instance
    """
    from telegram.ext import CommandHandler

    admin_handler = AdminHandler()

    # Register /admin command
    application.add_handler(
        CommandHandler('admin', admin_handler.handle_admin_command)
    )

    logger.info("Admin handlers registered")

    return admin_handler
