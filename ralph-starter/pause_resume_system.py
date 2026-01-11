# AU-006 through AU-010: Pause/Resume System Implementation
# These functions should be added to RalphBot class in ralph_bot.py

from datetime import datetime
import logging
import random

logger = logging.getLogger(__name__)


def is_work_allowed(self, user_id: int) -> bool:
    """AU-006: Check if work is currently allowed for this session.

    Args:
        user_id: User session ID

    Returns:
        True if work is allowed, False if paused
    """
    session = self.active_sessions.get(user_id, {})
    return session.get('work_allowed', True)


def pause_work(self, user_id: int, reason: str = None) -> bool:
    """AU-006/AU-007: Pause work for a session.

    Args:
        user_id: User session ID
        reason: Optional reason for logging

    Returns:
        True if successfully paused, False if no session or already paused
    """
    session = self.active_sessions.get(user_id)
    if not session:
        logger.warning(f"AU-006: No active session for user {user_id}")
        return False

    if not session.get('work_allowed', True):
        logger.info(f"AU-006: Work already paused for user {user_id}")
        return False

    session['work_allowed'] = False
    session['work_paused_at'] = datetime.now()
    session['pause_reason'] = reason

    log_msg = f"AU-006: Work paused for user {user_id}"
    if reason:
        log_msg += f": {reason}"
    logger.info(log_msg)

    return True


def resume_work(self, user_id: int, reason: str = None) -> bool:
    """AU-006/AU-008: Resume work for a session.

    Args:
        user_id: User session ID
        reason: Optional reason for logging

    Returns:
        True if successfully resumed, False if no session or already running
    """
    session = self.active_sessions.get(user_id)
    if not session:
        logger.warning(f"AU-006: No active session for user {user_id}")
        return False

    if session.get('work_allowed', True):
        logger.info(f"AU-006: Work already running for user {user_id}")
        return False

    # Calculate pause duration for logging
    pause_duration = None
    if session.get('work_paused_at'):
        pause_duration = (datetime.now() - session['work_paused_at']).total_seconds()

    session['work_allowed'] = True
    session['work_paused_at'] = None
    session['pause_reason'] = None

    log_msg = f"AU-006: Work resumed for user {user_id}"
    if pause_duration:
        log_msg += f" (paused for {pause_duration:.1f}s)"
    if reason:
        log_msg += f": {reason}"
    logger.info(log_msg)

    return True


def detect_pause_command(self, message: str, user_id: int) -> bool:
    """AU-007: Detect natural language commands to pause work.

    Detects phrases like:
    - "hold on" / "wait" / "pause"
    - "stop for now" / "hang on"
    - "let me think" / "give me a minute"

    Args:
        message: User's message
        user_id: User session ID

    Returns:
        True if pause command detected, False otherwise
    """
    message_lower = message.lower().strip()

    pause_indicators = [
        "hold on", "wait", "pause", "stop for now", "hang on",
        "give me a minute", "give me a sec", "let me think",
        "hold up", "stop", "wait a sec", "wait a minute",
        "one sec", "one second", "just a sec", "just a second",
        "hold that thought", "pause that"
    ]

    for indicator in pause_indicators:
        if indicator in message_lower:
            return True

    return False


def detect_resume_command(self, message: str, user_id: int) -> bool:
    """AU-008: Detect natural language commands to resume work.

    Detects phrases like:
    - "continue" / "go ahead" / "resume"
    - "keep going" / "carry on"
    - "ok go" / "proceed"

    Args:
        message: User's message
        user_id: User session ID

    Returns:
        True if resume command detected, False otherwise
    """
    message_lower = message.lower().strip()

    resume_indicators = [
        "continue", "go ahead", "resume", "keep going", "carry on",
        "ok go", "proceed", "let's go", "get back to it",
        "back to work", "keep working", "you can continue",
        "go on", "move forward", "start again", "unpause"
    ]

    for indicator in resume_indicators:
        if indicator in message_lower:
            return True

    return False


async def generate_idle_scene(self, context, chat_id: int, user_id: int):
    """AU-009: Generate idle scene when work is paused.

    Workers are waiting around, natural dialog while paused.
    Ralph might be eating paste, workers chatting casually.

    Args:
        context: Telegram context
        chat_id: Chat ID for sending messages
        user_id: User session ID
    """
    idle_scenarios = [
        {
            "speaker": "Ralph",
            "message": "Me just gonna eat my paste while we wait, Mr. Worms!"
        },
        {
            "speaker": "Stool",
            "message": "I'll grab a coffee. Holler when you need us, boss."
        },
        {
            "speaker": "Gomer",
            "message": "Taking a quick stretch break. Ready when you are!"
        },
        {
            "speaker": "Mona",
            "message": "Perfect timing - I'll review my notes while we wait."
        },
        {
            "speaker": "Gus",
            "message": "I'm here, just chilling. No rush!"
        },
        {
            "speaker": "Ralph",
            "message": "This is my thinking time! Me thinks about... um... paste flavors!"
        },
    ]

    scenario = random.choice(idle_scenarios)

    await self.send_styled_message(
        context, chat_id,
        scenario["speaker"], "Boss",
        scenario["message"],
        topic="idle waiting",
        with_typing=True
    )


async def generate_resume_scene(self, context, chat_id: int, user_id: int):
    """AU-010: Generate resume scene when work is resumed.

    Workers spring back to action naturally - energetic, ready to go.

    Args:
        context: Telegram context
        chat_id: Chat ID for sending messages
        user_id: User session ID
    """
    resume_scenarios = [
        {
            "speaker": "Ralph",
            "message": "Yay! Back to work! Me put away my paste and everything!"
        },
        {
            "speaker": "Stool",
            "message": "Alright, let's do this. Where were we?"
        },
        {
            "speaker": "Gomer",
            "message": "Refreshed and ready! What's next, chief?"
        },
        {
            "speaker": "Mona",
            "message": "OK, back at it. I've got some ideas while I was waiting."
        },
        {
            "speaker": "Gus",
            "message": "Let's roll! I'm pumped."
        },
        {
            "speaker": "Ralph",
            "message": "The team is back! That's unpossible exciting!"
        },
    ]

    scenario = random.choice(resume_scenarios)

    await self.send_styled_message(
        context, chat_id,
        scenario["speaker"], "Boss",
        scenario["message"],
        topic="resume work",
        with_typing=True
    )
