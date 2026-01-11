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

    @staticmethod
    def get_embarrassed_memory_prompt() -> str:
        """Get one of 50+ embarrassed variations of Ralph asking 'what were we doing?'

        Used when Ralph doesn't remember what the user was working on between sessions.
        These are genuine, embarrassed admissions that feel human and relatable.

        Returns:
            A random embarrassed memory prompt from Ralph
        """
        prompts = [
            # Direct admissions
            "Uh... Ralph forget what we were doing. What was it again?",
            "Me sorry! Ralph's brain is like sieve! What were we working on?",
            "This is embarrassing... Ralph don't remember! Can you remind me?",
            "Oh no! Ralph forgot again! What was the thing we were doing?",
            "Me feel bad... Ralph can't remember! What was our project?",

            # Blame deflection (Ralph style)
            "Ralph's brain took nap! What were we building?",
            "The forget monster got Ralph again! What was we doing?",
            "Ralph's memory went on vacation! Remind me?",
            "Me think Ralph's head is full of clouds today! What was the task?",
            "Ralph's brain is playing hide and seek! What were we working on?",

            # Self-deprecating
            "Ralph is not good at remembering! What were we doing again?",
            "Me have goldfish memory! Can you tell Ralph what we were working on?",
            "Ralph's memory is like Etch-a-Sketch - someone shook it! What was it?",
            "Me tried to remember but Ralph's brain said no! What was the project?",
            "Ralph's memory card is corrupted! What were we building?",

            # Hopeful/optimistic despite forgetting
            "Ralph forgot but me excited to hear what we're doing! Tell me?",
            "Me don't remember but Ralph ready to help! What was it?",
            "Ralph's memory is fuzzy but me happy to be here! What are we working on?",
            "Me forget but that okay! Ralph learn fast! What was the thing?",
            "Ralph need little reminder but then me remember everything! What was it?",

            # Physical comedy references
            "Ralph bumped head and forgot! What were we doing?",
            "Me ate too much paste, brain foggy! What was the project?",
            "Ralph fell asleep and dream erased memory! What were we working on?",
            "Me spun in circle and got dizzy! What was we doing?",
            "Ralph's brain went on coffee break! What was the task?",

            # Apologetic but sweet
            "Me really sorry! Ralph forget! Can you tell me again?",
            "Ralph feel bad for forgetting! What was we working on?",
            "Me don't want to disappoint but Ralph can't remember! What was it?",
            "Sorry Mr. Worms! Ralph forgot what we were doing! Remind me?",
            "Me embarrassed to ask but... what was the project again?",

            # Comparison to other things Ralph forgot
            "Ralph forget this like me forget where Ralph put his lunchbox! What was it?",
            "Me forgot like the time Ralph forgot his own birthday! What were we doing?",
            "Ralph can't remember this like me can't remember math! What was the task?",
            "Me forget like Ralph forgets to chew! What were we working on?",
            "Ralph's memory left like when Ralph left his backpack on bus! What was it?",

            # Hopeful recovery attempts
            "Was it... no Ralph don't remember! Can you tell me?",
            "Me think it was... nope! Ralph need help! What was we doing?",
            "Ralph almost remember but not quite! What was the project?",
            "Me remember your face but not what we were doing! Tell Ralph?",
            "Ralph remember being excited but forget why! What was it?",

            # Worker involvement
            "Ralph forgot to write it down! What were we building?",
            "Me lost my notes! What was the task again?",
            "Ralph's todo list disappeared! What were we working on?",
            "Me tried to remember but the workers forgot too! What was it?",
            "Ralph and the team need reminder! What was the project?",

            # Time-based confusion
            "Was that today or yesterday? Ralph confused! What were we doing?",
            "Me lose track of time and forgot! What was the task?",
            "Ralph's brain clock stopped! What were we working on?",
            "Me don't know if me coming or going! What was it?",
            "Ralph forget if we started already! What was the project?",

            # Genuine concern
            "Me really want to help but Ralph can't remember! What was we doing?",
            "Ralph worried me let you down! What was the task?",
            "Me don't want to waste your time! Can you remind Ralph?",
            "Ralph ready to work but forget what on! Tell me?",
            "Me eager to start but don't remember what! What was it?",

            # Creative/unique
            "Ralph's memory went poof like magic! What were we doing?",
            "Me brain did the spinny thing! What was the project?",
            "Ralph's think-box is empty! What were we working on?",
            "Me head is like balloon - floaty and empty! What was it?",
            "Ralph's remember-machine is broken! What was the task?",

            # Additional variations for 50+
            "Oopsie! Ralph's brain rebooted! What were we doing?",
            "Me forget faster than Ralph forgets his shoes! What was it?",
            "Ralph's memory is like sandwich with no filling! Remind me?",
            "Me tried to write it down but ate the paper! What was the project?",
            "Ralph's brain took wrong bus! What were we working on?",
            "Me remember something but not what! Tell Ralph?",
            "Ralph's thinking cap fell off! What was the task?",
            "Me brain went on strike! What were we doing?",
            "Ralph forgot but me good at re-learning! What was it?",
            "Me memory is like broken crayon! What was the project?",
            "Ralph's brain did factory reset! What were we working on?",
        ]

        return RalphNarrator.misspell(random.choice(prompts), chance=0.3)


def get_ralph_narrator() -> RalphNarrator:
    """Get the Ralph narrator instance (singleton pattern).

    Returns:
        RalphNarrator instance
    """
    return RalphNarrator()
