#!/usr/bin/env python3
"""
Ralph Personality Module

Provides Ralph's characteristic narration, misspellings, and personality traits
for use throughout the bot, especially in onboarding.
"""

import random
from typing import List


class RalphNarrator:
    """Ralph's personality and narration engine for onboarding."""

    # Ralph's misspellings (matching ralph_bot.py)
    MISSPELLINGS = {
        "possible": "unpossible",
        "impossible": "unpossible",
        "the": "teh",
        "you": "u",
        "your": "ur",
        "are": "r",
        "completed": "compleatd",
        "complete": "compleat",
        "repository": "repozitory",
        "computer": "computor",
        "configure": "configur",
        "configuration": "configur-ation",
        "congratulations": "congradulations",
        "success": "sucess",
        "successful": "sucessful",
        "excellent": "exellent",
        "definitely": "definately",
    }

    @staticmethod
    def misspell(text: str, chance: float = 0.2) -> str:
        """Apply Ralph's dyslexia misspellings to text.

        Args:
            text: The text to potentially misspell
            chance: Probability (0-1) of misspelling each applicable word

        Returns:
            Text with Ralph-style misspellings applied randomly
        """
        if not text:
            return text

        words = text.split()
        result = []

        for word in words:
            # Check if this word (lowercase, stripped of punctuation) has a misspelling
            word_clean = word.lower().strip('.,!?;:\'\"()[]{}')

            if word_clean in RalphNarrator.MISSPELLINGS:
                # Only misspell with the given probability
                if random.random() < chance:
                    misspelled = RalphNarrator.MISSPELLINGS[word_clean]

                    # Preserve original capitalization
                    if word and word[0].isupper():
                        misspelled = misspelled.capitalize()
                    if word.isupper():
                        misspelled = misspelled.upper()

                    # Preserve punctuation
                    punctuation = ''
                    for char in reversed(word):
                        if char in '.,!?;:\'\"()[]{}':
                            punctuation = char + punctuation
                        else:
                            break

                    result.append(misspelled + punctuation)
                else:
                    result.append(word)
            else:
                result.append(word)

        return ' '.join(result)

    @staticmethod
    def get_encouragement(context: str = "general") -> str:
        """Get an encouraging message from Ralph.

        Args:
            context: The context for encouragement (e.g., 'progress', 'error', 'milestone')

        Returns:
            A random encouraging message from Ralph
        """
        encouragements = {
            "general": [
                "You doing great!",
                "Ralph proud of you!",
                "This going super good!",
                "Me happy!",
                "You smart like Principal Skinner!",
            ],
            "progress": [
                "We almost there!",
                "Looking good so far!",
                "You're naturals at this!",
                "Ralph think you doing awesome!",
                "This easier than eating glue!",
            ],
            "error": [
                "That okay! Ralph mess up all the time!",
                "No problem! We fix together!",
                "Me not worried! You got this!",
                "Ralph's dad says trying is important!",
                "Mistakes make us learn! Like when Ralph ate paint!",
            ],
            "milestone": [
                "Yay! We did it!",
                "Ralph so happy!",
                "You're a super star!",
                "High five! ✋",
                "Me think you're the bestest!",
            ]
        }

        messages = encouragements.get(context, encouragements["general"])
        return RalphNarrator.misspell(random.choice(messages))

    @staticmethod
    def get_celebration(achievement: str) -> str:
        """Get a celebration message for completing a milestone.

        Args:
            achievement: What was just accomplished

        Returns:
            A celebratory message from Ralph
        """
        celebrations = [
            f"🎉 Yay! {achievement}! Ralph so proud!",
            f"✨ We did it! {achievement}! Me happy dance!",
            f"🌟 {achievement}! You're super smart!",
            f"🎊 {achievement}! That was easy peasy!",
            f"🎈 Hooray! {achievement}! Ralph love success!",
        ]
        return RalphNarrator.misspell(random.choice(celebrations))

    @staticmethod
    def get_error_message(error_type: str = "general") -> str:
        """Get a humorous error message from Ralph.

        Args:
            error_type: Type of error (e.g., 'connection', 'permission', 'not_found')

        Returns:
            A Ralph-style error message that's helpful but funny
        """
        errors = {
            "general": [
                "Uh oh! Something went wonky! But no worry, Ralph help fix!",
                "Me see problem! Like when Ralph's cat ate his homework!",
                "Oopsie! Ralph's computor confused! Let's try again!",
                "That not supposed to happen! But Ralph know what to do!",
            ],
            "connection": [
                "Uh oh! Ralph can't reach that place! Check your internets?",
                "The computor says 'no' to Ralph! Maybe try again?",
                "Connection is being shy! Ralph wait and try again!",
            ],
            "permission": [
                "Ralph not allowed in that room! Need special key!",
                "The door is locked! Ralph need permission to go in!",
                "Access denied! Like when Ralph tried to drive bus!",
            ],
            "not_found": [
                "Ralph can't find that! Like when Ralph lost his lunchbox!",
                "That thing is hiding! Ralph look everywhere but no see it!",
                "Where did it go? Ralph confused!",
            ]
        }

        messages = errors.get(error_type, errors["general"])
        return RalphNarrator.misspell(random.choice(messages))

    @staticmethod
    def get_step_intro(step_name: str) -> str:
        """Get an introduction message for a setup step.

        Args:
            step_name: The name/title of the step

        Returns:
            Ralph's narration introducing the step
        """
        intros = [
            f"Okay! Now Ralph gonna help with: {step_name}!",
            f"Next up: {step_name}! This part is fun!",
            f"Time for {step_name}! Ralph show you how!",
            f"Let's do {step_name} now! Me know how to do this!",
            f"{step_name} time! Ralph make it easy!",
        ]
        return RalphNarrator.misspell(random.choice(intros))

    @staticmethod
    def get_thinking_message() -> str:
        """Get a message showing Ralph is thinking/working.

        Returns:
            A Ralph-style thinking message
        """
        thinking = [
            "Ralph thinking...",
            "Me figuring it out...",
            "Let Ralph check...",
            "One second... Ralph looking!",
            "Ralph's brain working hard!",
        ]
        return random.choice(thinking)

    @staticmethod
    def get_goodbye_message() -> str:
        """Get a goodbye/completion message.

        Returns:
            Ralph's sign-off message
        """
        goodbyes = [
            "Okay bye! Have fun making code! 👋",
            "Ralph happy to help! See you later! 🍩",
            "All done! Me go eat paste now! 👋",
            "You all set! Ralph proud! 🌟",
            "Setup complete! Ralph's work is done! ✨",
        ]
        return RalphNarrator.misspell(random.choice(goodbyes))

    @staticmethod
    def get_skip_message() -> str:
        """Get a message for when user wants to skip onboarding.

        Returns:
            Ralph's response to skipping
        """
        skips = [
            "Okay! You already know this stuff! Ralph understand!",
            "No problem! Skip the boring parts!",
            "Smart! Ralph like when people know things already!",
            "You must be super experienced! Go ahead!",
        ]
        return RalphNarrator.misspell(random.choice(skips))


def get_ralph_narrator() -> RalphNarrator:
    """Get the Ralph narrator instance (singleton pattern).

    Returns:
        RalphNarrator instance
    """
    return RalphNarrator()
