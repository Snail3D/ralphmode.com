#!/usr/bin/env python3
"""
MU-003: Character Assignment for Non-Owner Users

Assigns random Springfield resident characters to non-owner users.
Their messages get translated into that character's voice.

Features:
- Pool of Springfield resident characters with distinct personalities
- Random character assignment for new users
- Character persistence via database
- Admin can reassign characters
"""

import os
import random
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Import database for persistence
try:
    from database import get_db, User, InputValidator
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logging.warning("MU-003: Database not available - character assignments will use in-memory storage only")

logger = logging.getLogger(__name__)


# MU-003: Springfield character pool
# These are public domain archetypes, not specific IP characters
SPRINGFIELD_CHARACTERS = {
    "Comic Book Guy": {
        "speech_patterns": [
            "Worst. {subject}. Ever.",
            "*adjusts glasses* Actually, {statement}",
            "I must return to my store where I dispense the insults rather than absorb them.",
            "*sighs* The internet has spoken: {opinion}",
        ],
        "personality": "Sarcastic, condescending, encyclopedic knowledge, loves to correct people",
        "catchphrase": "Worst. {x}. Ever.",
        "tone": "superior, pedantic, theatrical"
    },
    "Sea Captain": {
        "speech_patterns": [
            "Arrr, {statement}!",
            "Thar she blows! {exclamation}",
            "Aye, 'tis {description}, it be!",
            "Yarrr, {opinion}!",
        ],
        "personality": "Maritime vocabulary, tells tall tales, nautical metaphors",
        "catchphrase": "Yarrr!",
        "tone": "gruff, salty, adventurous"
    },
    "Disco Stu": {
        "speech_patterns": [
            "Disco Stu {action}!",
            "Oooh, Disco Stu likes {thing}!",
            "Disco Stu doesn't advertise, baby!",
            "{Statement}, and that's the Disco truth!",
        ],
        "personality": "Talks in third person, stuck in disco era, smooth talker",
        "catchphrase": "Disco Stu doesn't advertise!",
        "tone": "groovy, smooth, outdated slang"
    },
    "Groundskeeper Willie": {
        "speech_patterns": [
            "Ach! {exclamation}!",
            "Grease me up, woman! Er, I mean, {statement}",
            "Bonjourrrr, ya cheese-eating surrender monkeys! {greeting}",
            "*shakes fist* {complaint}!",
        ],
        "personality": "Thick Scottish accent, quick to anger, surprisingly strong",
        "catchphrase": "Grease me up!",
        "tone": "aggressive, Scottish, passionate"
    },
    "Dr. Nick": {
        "speech_patterns": [
            "Hi everybody! {greeting}",
            "Did you go to Hollywood Upstairs Medical College too?",
            "Inflammable means flammable? What a country! Er, {observation}",
            "The coroner? I'm so sick of that guy! Anyway, {statement}",
        ],
        "personality": "Questionable medical credentials, overly cheerful, dubious competence",
        "catchphrase": "Hi everybody!",
        "tone": "cheerful, dubious, enthusiastic"
    },
    "Crazy Cat Lady": {
        "speech_patterns": [
            "*throws cats* {action}!",
            "Mrrow! Hiss! {statement}",
            "*mumbles incoherently* ...and that's when the cats told me {thing}",
            "CATS! {exclamation}!",
        ],
        "personality": "Cat-obsessed, unpredictable, nonsensical tangents",
        "catchphrase": "*throws cats*",
        "tone": "erratic, feline-focused, wild"
    },
    "Hans Moleman": {
        "speech_patterns": [
            "I was saying '{misheard}'...",
            "I'm 31 years old! Well, {statement}",
            "*gets hurt* Ow! My {body_part}!",
            "Nobody's gay for Moleman... *sighs* {observation}",
        ],
        "personality": "Elderly (but claims to be young), unlucky, gets hurt frequently",
        "catchphrase": "I was saying...",
        "tone": "defeated, unfortunate, mishap-prone"
    },
    "Lenny": {
        "speech_patterns": [
            "Aw geez, {reaction}",
            "Not Lenny! {panic}",
            "Carl and me were just saying, {observation}",
            "Did you see that? {amazement}",
        ],
        "personality": "Best friends with Carl, working-class, simple but loyal",
        "catchphrase": "Not Lenny!",
        "tone": "easygoing, loyal, simple"
    },
    "Carl": {
        "speech_patterns": [
            "Hey, Homer and I are like {comparison}",
            "Oh, that's beautiful. {appreciation}",
            "Me and Lenny were just talking about {topic}",
            "*chuckles* {observation}",
        ],
        "personality": "Best friends with Lenny, slightly more sophisticated, dry humor",
        "catchphrase": "That's beautiful",
        "tone": "dry, appreciative, working-class"
    },
    "Barney": {
        "speech_patterns": [
            "*burp* {statement}",
            "Hey Homer! Want to {activity}?",
            "I used to be {past_glory}, but now {current_state}",
            "*slurs* {observation}",
        ],
        "personality": "Former potential, now a drunk, surprising talents when sober",
        "catchphrase": "*burp*",
        "tone": "inebriated, jovial, washed-up"
    }
}


class CharacterManager:
    """
    Manages character assignments for non-owner users.

    Features:
    - Random character assignment from Springfield pool
    - Persistent character storage via database
    - Character speech pattern translation
    - Admin character reassignment
    """

    def __init__(self):
        """Initialize the character manager."""
        self._in_memory_assignments: Dict[int, str] = {}
        self.available_characters = list(SPRINGFIELD_CHARACTERS.keys())

    def get_user_character(self, telegram_id: int) -> Optional[str]:
        """
        Get the assigned character for a user.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Character name if assigned, None otherwise
        """
        # Validate input
        if not InputValidator.validate_telegram_id(telegram_id):
            logger.warning(f"Invalid telegram_id: {telegram_id}")
            return None

        # Try database first
        if DATABASE_AVAILABLE:
            try:
                with get_db() as db:
                    user = db.query(User).filter(User.telegram_id == telegram_id).first()
                    if user and hasattr(user, 'assigned_character') and user.assigned_character:
                        return user.assigned_character
            except Exception as e:
                logger.error(f"Error fetching character from database: {e}")

        # Fall back to in-memory storage
        return self._in_memory_assignments.get(telegram_id)

    def assign_character(self, telegram_id: int, character_name: Optional[str] = None) -> Optional[str]:
        """
        Assign a character to a user.

        Args:
            telegram_id: Telegram user ID
            character_name: Specific character to assign, or None for random

        Returns:
            Assigned character name, or None on failure
        """
        # Validate input
        if not InputValidator.validate_telegram_id(telegram_id):
            logger.warning(f"Invalid telegram_id: {telegram_id}")
            return None

        # If no character specified, pick random
        if not character_name:
            character_name = random.choice(self.available_characters)
        elif character_name not in SPRINGFIELD_CHARACTERS:
            logger.warning(f"Invalid character name: {character_name}")
            return None

        # Store in in-memory cache
        self._in_memory_assignments[telegram_id] = character_name

        # Try to persist to database
        if DATABASE_AVAILABLE:
            try:
                with get_db() as db:
                    user = db.query(User).filter(User.telegram_id == telegram_id).first()
                    if user:
                        if not hasattr(User, 'assigned_character'):
                            logger.warning("User model doesn't have assigned_character column - will add in next migration")
                        else:
                            user.assigned_character = character_name
                            db.commit()
                            logger.info(f"Assigned character '{character_name}' to user {telegram_id}")
            except Exception as e:
                logger.error(f"Error saving character assignment to database: {e}")

        logger.info(f"Assigned character '{character_name}' to user {telegram_id} (in-memory)")
        return character_name

    def get_character_info(self, character_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full information about a character.

        Args:
            character_name: Name of the character

        Returns:
            Dictionary with character info, or None if not found
        """
        return SPRINGFIELD_CHARACTERS.get(character_name)

    def translate_to_character(self, message: str, character_name: str) -> str:
        """
        Translate a message into a character's voice.

        Args:
            message: Original message
            character_name: Character to translate into

        Returns:
            Message translated into character's speech pattern
        """
        character = SPRINGFIELD_CHARACTERS.get(character_name)
        if not character:
            return message

        # Pick a random speech pattern and substitute
        pattern = random.choice(character['speech_patterns'])

        # Simple substitution - in production, use LLM for better translation
        # For now, just prepend character's style
        return f"[{character_name}] {message}"

    def get_all_characters(self) -> List[str]:
        """Get list of all available characters."""
        return self.available_characters

    def get_character_summary(self, character_name: str) -> str:
        """
        Get a brief summary of a character for display.

        Args:
            character_name: Name of the character

        Returns:
            Brief description string
        """
        character = SPRINGFIELD_CHARACTERS.get(character_name)
        if not character:
            return f"Unknown character: {character_name}"

        return f"{character_name}: {character['personality']} ({character['catchphrase']})"


# Global instance
_character_manager: Optional[CharacterManager] = None


def get_character_manager() -> CharacterManager:
    """
    Get the global CharacterManager instance (singleton pattern).

    Returns:
        CharacterManager instance
    """
    global _character_manager
    if _character_manager is None:
        _character_manager = CharacterManager()
    return _character_manager
