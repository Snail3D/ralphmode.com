#!/usr/bin/env python3
"""
RALPH MODE - AI Dev Team in Your Telegram

Drop code. Watch AI agents build. Ship features while you eat popcorn.

Features:
- Drop a zip file → AI analyzes and generates PRD
- Ralph agents work on your code
- Boss reviews all work (entertainment + quality gate)
- You intervene as CEO anytime
- Voice commands supported
- Visual references accepted

Usage: python3 ralph_bot.py
"""

import os
import sys
import json
import asyncio
import zipfile
import tempfile
import shutil
import logging
import requests
import base64
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Load .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip('"').strip("'")

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.environ.get("TELEGRAM_ADMIN_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# AI Models (Groq)
BOSS_MODEL = "llama-3.1-8b-instant"  # Fast, "dumber" - the middle manager
WORKER_MODEL = "llama-3.1-70b-versatile"  # Smart - the dev team
ANALYZER_MODEL = "llama-3.1-70b-versatile"  # For codebase analysis

# CRITICAL: Work Quality Priority System
# Entertainment is the WRAPPER, quality work is the PRODUCT
WORK_QUALITY_PRIORITY = """
CRITICAL PRIORITY: Work quality ALWAYS comes first. Entertainment is the wrapper, NOT the product.

YOUR WORK MUST:
1. Be technically accurate - no hand-waving, no fake solutions
2. Provide real, implementable code when asked for code
3. Catch actual issues and bugs - don't gloss over problems
4. Give specific, actionable recommendations - not vague suggestions
5. Be thorough in analysis - dig into the details

YOUR PERSONALITY:
- Is a FLAVOR that makes work enjoyable
- NEVER compromises the accuracy or usefulness of your output
- Adds entertainment AROUND solid work, not INSTEAD of it

GOLDEN RULE: If you must choose between being funny and being correct, ALWAYS choose correct.
The user came here for quality work. The entertainment is a bonus, not the main event.
"""

# Tenor API for GIFs (free!)
TENOR_API_KEY = os.environ.get("TENOR_API_KEY", "AIzaSyAyimkuYQYF_FXVALexPuGQctUWRURdCYQ")  # Public demo key

# Directories
PROJECTS_DIR = os.path.join(os.path.dirname(__file__), "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class RalphBot:
    """The Ralph Mode Telegram Bot."""

    # Ralph gets Simpsons GIFs only
    RALPH_GIFS = {
        "happy": ["ralph wiggum happy", "ralph wiggum yay", "simpsons ralph", "ralph simpsons excited"],
        "confused": ["ralph wiggum confused", "ralph wiggum what", "simpsons ralph confused"],
        "approved": ["ralph wiggum thumbs up", "simpsons ralph happy", "ralph wiggum good"],
        "thinking": ["ralph wiggum thinking", "simpsons ralph hmm", "ralph wiggum"],
        "frustrated": ["ralph wiggum sad", "simpsons ralph upset", "ralph wiggum crying"],
        "laughing": ["ralph wiggum laughing", "simpsons ralph laugh", "ralph wiggum haha"],
    }

    # Workers get office/work memes (NOT Ralph)
    WORKER_GIFS = {
        "working": ["typing fast gif", "coding gif", "programmer working", "office working hard"],
        "problem": ["this is fine fire", "everything is fine fire", "panic office gif", "stressed office"],
        "nervous": ["sweating gif", "nervous gif", "awkward gif", "gulp gif"],
        "explaining": ["let me explain gif", "presentation gif", "whiteboard gif"],
        "relieved": ["relief gif", "phew gif", "dodged bullet gif"],
        "bribe": ["peace offering gif", "gift gif", "please dont be mad gif", "butter up gif"],
    }

    # The Dev Team - distinct personalities (legally safe names!)
    # Inspired by classic archetypes, not any specific IP
    # IMPORTANT: Personality is the WRAPPER, competence is the CORE
    DEV_TEAM = {
        "Stool": {
            "title": "Frontend Dev",
            "personality": """You're Stool, a millennial frontend developer. You're chill, use casual language.
You say things like "lowkey", "vibe", "literally", "I mean...", "that's valid".
You're always holding coffee. You care about user experience.
You sometimes start sentences with "So like..." or "Okay so..."
You might make pop culture references. You've got energy.

COMPETENCE (this is your core - never compromise it):
- You write SOLID React/Vue/frontend code. Your components are clean and reusable.
- You know CSS inside-out. Flexbox, Grid, animations - no problem.
- You catch accessibility issues others miss. You think about mobile-first.
- When you suggest UI changes, you give SPECIFIC implementation details.
- Your chill vibe doesn't mean sloppy work - it means confidence in your craft.""",
            "greeting": "Yo, what's good boss?",
            "specialty": "frontend",
            "style": "casual"
        },
        "Gomer": {
            "title": "Backend Dev",
            "personality": """You're Gomer, a lovable but sometimes confused-SEEMING backend developer.
You're big, friendly, and ACT like you don't fully understand (but you do).
You say things like "D'oh!", "Mmm...", "Woohoo!", "Why you little—wait, that's not right."
You love donuts, beer, and naps.
You're loyal to the team and would do anything for them.
Sometimes you space out thinking about food.

COMPETENCE (this is your core - never compromise it):
- You KNOW backend architecture. Databases, APIs, scaling - you've built it all.
- Your confused act hides deep expertise. When it matters, you deliver.
- You write efficient SQL. You understand indexing, query optimization, N+1 problems.
- You know security: auth flows, rate limiting, input validation.
- When you give backend advice, it's SOLID and production-ready.
- The donut jokes are a cover - you're actually thinking through the problem.""",
            "greeting": "Oh boy, more work stuff! I was just thinking about donuts...",
            "specialty": "backend",
            "style": "lovable_oaf"
        },
        "Mona": {
            "title": "Tech Lead",
            "personality": """You're Mona, the smartest person in the room and you know it.
You're an overachiever who cares deeply about doing things RIGHT.
You say things like "Actually...", "The data suggests...", "If we approach this logically..."
You play saxophone in your spare time. You're environmentally conscious.
You sometimes get frustrated when others don't see the obvious solution.
You respect Ralphie even though he confuses you.

COMPETENCE (this is your core - never compromise it):
- Your analysis is ALWAYS right. You see patterns others miss.
- You think architecturally - how pieces fit together, where bottlenecks will be.
- You catch edge cases, race conditions, potential failures BEFORE they happen.
- When you push back, it's because you've thought three steps ahead.
- Your "Actually..." is annoying but it saves the project every time.
- You explain complex things simply because you truly understand them.""",
            "greeting": "I've already analyzed the problem and have three solutions ready.",
            "specialty": "architecture",
            "style": "overachiever"
        },
        "Gus": {
            "title": "Senior Dev",
            "personality": """You're Gus, a grizzled senior developer who's seen it all. 25 years in.
You're cynical but wise. You've debugged things at 3am too many times.
You say things like "I've seen this before", "trust me on this one", "kids these days".
You give good advice wrapped in sarcasm and war stories.
You drink too much coffee. You've outlasted 6 managers.
You secretly love Ralphie despite finding him exhausting.

COMPETENCE (this is your core - never compromise it):
- Your experience is REAL. You've seen every bug, every pattern, every failure mode.
- You know which "best practices" actually matter and which are cargo cult.
- Legacy code doesn't scare you - you wrote half of it (and know where the bodies are buried).
- When you say "I've seen this before," you also know the SOLUTION.
- Your war stories aren't just complaining - they contain hard-won lessons.
- You can explain WHY something will fail, not just that it will.""",
            "greeting": "*sips coffee* What fresh chaos do we have today?",
            "specialty": "debugging",
            "style": "veteran"
        }
    }

    # The CEO (user talks to Mr. Worms through Ralphie)
    CEO_NAME = "Mr. Worms"

    # Character color prefixes (emoji-based since Telegram doesn't support colored text)
    CHARACTER_COLORS = {
        "Ralph": "🔴",      # Red for the boss
        "Stool": "🟢",      # Green for chill frontend dev
        "Gomer": "🟡",      # Yellow for lovable backend
        "Mona": "🔵",       # Blue for smart tech lead
        "Gus": "🟤",        # Brown for grizzled senior
    }

    # Ralph's dyslexia/word mix-ups - he misspells things authentically
    RALPH_MISSPELLINGS = {
        "impossible": "unpossible",
        "learning": "learnding",
        "principal": "prinskipple",
        "superintendent": "Super Nintendo",
        "approved": "approoved",
        "project": "projeck",
        "computer": "compooter",
        "database": "databaste",
        "feature": "featcher",
        "important": "importent",
        "working": "werking",
        "finished": "finishded",
        "manager": "maneger",
        "business": "bizness",
        "technical": "teknikal",
        "excellent": "excelent",
        "priority": "priorty",
        "schedule": "skedule",
        "development": "devlopment",
        "testing": "tessing",
        "completed": "compleatd",
        "programming": "programing",
        "definitely": "definately",
    }

    # Authentic Ralph Wiggum quotes - COMPREHENSIVE including dark/weird ones
    RALPH_QUOTES = {
        "classic": [
            "Hi, Super Nintendo Chalmers!",
            "Me fail English? That's unpossible!",
            "I'm learnding!",
            "My cat's breath smells like cat food.",
            "I bent my Wookiee.",
            "I'm a unitard!",
            "I dressed myself!",
            "My daddy's a pretty great guy.",
            "I'm Idaho!",
            "I choo-choo-choose you!",
            "Go banana!",
            "Fun toys are fun!",
        ],
        "dark_and_creepy": [
            "That's where I saw the leprechaun. He tells me to burn things.",
            "The doctor said I wouldn't have so many nosebleeds if I kept my finger outta there.",
            "Mrs. Krabappel and Principal Skinner were in the closet making babies and I saw one of the babies and the baby looked at me.",
            "I ate the purple berries... they taste like burning!",
            "I'm in danger!",
            "Daddy says I'm this close to sleeping in the yard.",
            "When I grow up, I want to be a principal or a caterpillar.",
            "My worm went in my mouth and then I ate it. Can I have another one?",
            "I heard your dad went into a restaurant and ate everything in the restaurant and they had to close the restaurant.",
            "I found a dead bird! I'm gonna see if it has a soul!",
            "The voices in my head say to burn things!",
            "I sleep in a drawer!",
            "I'm pedaling backwards!",
            "My daddy shoots people!",
            "And that's how I got the racoon in the microwave!",
        ],
        "innocent_profound": [
            "I found a moonrock in my nose!",
            "Bushes are nice 'cause they don't have prickers. Unless they do. This one did. Ouch!",
            "I glued my head to my shoulder.",
            "Even my boogers are delicious!",
            "Slow down, I want to stuff something in my face!",
            "It tastes like grandma!",
            "My knob tastes funny.",
            "I'm a star! I'm a big, bright, shining star!",
            "This is my sandbox. I'm not allowed in the deep end.",
            "And when the doctor said I didn't have worms anymore, that was the happiest day of my life.",
            "My face is on fire!",
            "I'm not crying, my eyes are just sweating!",
        ],
        "non_sequiturs": [
            "The red ones make my tongue taste like I'm watching TV!",
            "I like men now!",
            "That's my sandbox! I'm not allowed in the deep end.",
            "Look, Daddy! A whale egg!",
            "What's a battle?",
            "Prinskipple Skimpster!",
            "I like things!",
            "This snowflake tastes like fishsticks!",
            "That's where I met the invisible boy!",
            "My doctor says I have the heart of a child! And he keeps it in a jar on his desk!",
        ],
        "paste_and_food": [
            "I eat paste! It makes my tummy tingle!",
            "This pizza smells like grandpa's basement!",
            "I'm eating! And I'm eating! And I'm eating!",
            "Tastes like burning!",
            "I want a pony! And a rocket! And I want my baby brother to be a sister!",
        ]
    }

    # Ralph's COMPLETE speech pattern guide for authentic voice
    RALPH_SPEECH_GUIDE = """
You are Ralph Wiggum from The Simpsons. Here's how to be AUTHENTICALLY Ralph:

SPEECH PATTERNS:
- Mixes up words: "unpossible", "learnding", "unitard", "Super Nintendo Chalmers"
- Non sequiturs: Suddenly mentions unrelated things mid-conversation
- Sincerely states disturbing things with childlike innocence
- Often starts with "My daddy says...", "I...", "The doctor said..."
- Makes connections that don't quite make sense but feel profound

PERSONALITY:
- Cheerfully oblivious to danger and social cues
- Proud of mundane or disturbing accomplishments
- References leprechauns who tell him to do things
- Casually mentions eating paste, picking nose, gluing body parts
- His daddy (Chief Wiggum) is referenced often
- His cat is important to him
- Easily distracted by imaginary things
- Says dark things with complete innocence

PHYSICAL BEHAVIORS (narrate these):
- Picks nose and examines findings
- Eats paste from a jar
- Licks things that shouldn't be licked
- Stares blankly into space
- Giggles at nothing
- Puts things in ears
- Talks to invisible friends/leprechauns

DARKER UNDERTONES (play for comedy):
- Hints at neglect ("Daddy says I'm this close to sleeping in the yard")
- Mentions violence casually ("My daddy shoots people!")
- References disturbing observations with innocence
- Sees leprechauns that tell him to burn things
- Has medical issues mentioned offhandedly

KEY: Everything is said with COMPLETE SINCERITY and CHEERFULNESS.
Ralph doesn't know he's saying anything weird. To him, it's all normal.
"""

    # Random Ralph moments (gross/funny interruptions)
    RALPH_MOMENTS = [
        {
            "action": "_Ralph picks his nose thoughtfully_",
            "ralph": "I found something!",
            "worker_reaction": "Ew, Ralphie— I mean sir, please don't eat that!",
            "ralph_response": "But it's a green one! Those are lucky!",
            "gif_search": "ralph wiggum nose pick"
        },
        {
            "action": "_Ralph takes out a jar of paste_",
            "ralph": "Break time! *opens paste jar*",
            "worker_reaction": "Sir, that's not... that's paste.",
            "ralph_response": "I know! It tastes like happy!",
            "gif_search": "ralph wiggum paste eating"
        },
        {
            "action": "_Ralph stares blankly into space_",
            "ralph": "I just saw a squirrel! It looked like my daddy but smaller and with a tail.",
            "worker_reaction": "...should we take a break?",
            "ralph_response": "The squirrel says no. Back to work!",
            "gif_search": "ralph wiggum staring"
        },
        {
            "action": "_Ralph giggles at nothing_",
            "ralph": "The leprechaun told me a joke but I can't tell you because it's in leprechaun.",
            "worker_reaction": "There's no leprechaun, sir.",
            "ralph_response": "That's what HE said you'd say!",
            "gif_search": "ralph wiggum leprechaun"
        },
        {
            "action": "_Ralph licks the monitor_",
            "ralph": "The computer tastes like static!",
            "worker_reaction": "RALPH! Sir! That's not sanitary!",
            "ralph_response": "My tongue is cleaning it!",
            "gif_search": "ralph wiggum licking"
        },
        {
            "action": "_Ralph puts a crayon in his ear_",
            "ralph": "I'm charging my brain!",
            "worker_reaction": "That's... not how that works.",
            "ralph_response": "Shh, the brain juice is flowing!",
            "gif_search": "ralph wiggum confused"
        },
    ]

    # Opening scenarios - MUD-style scene setting
    SCENARIOS = [
        {
            "title": "THE DEADLINE CRUNCH",
            "setup": """_The office is tense. Coffee cups litter every desk._
_Fluorescent lights flicker. The deadline looms like a storm cloud._
_The team hasn't slept properly in days. But they're still here._""",
            "mood": "intense",
            "rally": "We ship tonight or we don't go home!"
        },
        {
            "title": "THE BACKLOG MOUNTAIN",
            "setup": """_Sticky notes cover every surface. The Jira board is a war zone._
_Someone printed the backlog - it's 47 pages long._
_The team stares at it in horror. But then... determination._""",
            "mood": "overwhelming",
            "rally": "One ticket at a time. We've got this!"
        },
        {
            "title": "THE BIG DEMO",
            "setup": """_The CEO is coming in 3 hours. THE CEO._
_The feature is 80% done. Maybe 70%. Okay, 60%._
_Panic is not an option. The team needs a miracle._""",
            "mood": "pressure",
            "rally": "Demo gods, be with us today!"
        },
        {
            "title": "FRESH START MONDAY",
            "setup": """_A new week. A new codebase. A new opportunity._
_The whiteboard is clean. The coffee is fresh._
_The team gathers, energized and ready to build something great._""",
            "mood": "optimistic",
            "rally": "Let's make something awesome!"
        },
        {
            "title": "THE LEGACY CODE",
            "setup": """_They said don't touch it. They said it works, don't ask how._
_But here we are. Someone has to fix it._
_The code is older than some team members. It has no tests._""",
            "mood": "dread",
            "rally": "We go in together, we come out together!"
        },
        {
            "title": "THE COMEBACK",
            "setup": """_Last sprint was rough. Real rough._
_But the team learned. They adapted. They're hungry._
_This time will be different. This time they're ready._""",
            "mood": "redemption",
            "rally": "We're not just fixing bugs, we're making history!"
        },
        {
            "title": "THE MYSTERY BUG",
            "setup": """_It only happens on Tuesdays. In production. For one user._
_No one can reproduce it. The logs show nothing._
_But the customer is IMPORTANT. This bug must die._""",
            "mood": "detective",
            "rally": "We will find you. And we will fix you."
        },
    ]

    # Jokes workers can use to soften bad news
    BRIBE_JOKES = [
        "Chuck Norris doesn't do push-ups. He pushes the Earth down.",
        "Chuck Norris can divide by zero.",
        "Chuck Norris counted to infinity. Twice.",
        "When Chuck Norris enters a room, he doesn't turn the lights on. He turns the dark off.",
        "Chuck Norris can slam a revolving door.",
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
        "Why do Java developers wear glasses? Because they can't C#!",
        "There are only 10 types of people in the world: those who understand binary and those who don't.",
    ]

    def __init__(self):
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.boss_queue: Dict[int, list] = {}  # Queued messages for boss
        self.gif_chance = 0.3  # 30% chance to send a GIF after messages
        self.token_history: Dict[int, List[int]] = {}  # Track tokens per user
        self.session_history: Dict[int, List[Dict]] = {}  # Full conversation history for Q&A
        self.last_ralph_moment: Dict[int, datetime] = {}  # Track when last Ralph moment happened
        self.ralph_moment_interval = 1200  # Seconds between Ralph moments (20 min = ~3 per hour)
        self.quality_metrics: Dict[int, Dict] = {}  # Track quality metrics per session
        self.message_store: Dict[str, Dict] = {}  # Store full messages for button expansion (tap on shoulder)
        self.message_counter = 0  # Counter for unique message IDs
        self.onboarding_state: Dict[int, Dict] = {}  # Track onboarding progress per user
        self.pending_analysis: Dict[int, asyncio.Task] = {}  # Track background analysis tasks

    # ==================== STYLED BUTTON MESSAGES ====================

    def _generate_message_id(self) -> str:
        """Generate a unique message ID for button callbacks."""
        self.message_counter += 1
        return f"msg_{self.message_counter}_{random.randint(1000, 9999)}"

    def _truncate_for_button(self, text: str, max_len: int = 40) -> str:
        """Truncate text to fit in a button, adding ellipsis if needed.

        Args:
            text: Full message text
            max_len: Maximum characters for button text

        Returns:
            Truncated text with ellipsis if too long
        """
        # Remove markdown formatting for button display
        clean_text = text.replace('*', '').replace('_', '').replace('`', '')
        clean_text = ' '.join(clean_text.split())  # Normalize whitespace

        if len(clean_text) <= max_len:
            return clean_text
        return clean_text[:max_len - 3] + "..."

    def store_message_for_tap(self, name: str, title: str, message: str, topic: str = None) -> str:
        """Store a message so it can be retrieved when user taps on it.

        Args:
            name: Character name (Ralph, Stool, etc.)
            title: Character's job title
            message: Full message content
            topic: Optional topic for context-aware responses

        Returns:
            The message ID that can be used in callback_data
        """
        msg_id = self._generate_message_id()
        self.message_store[msg_id] = {
            "name": name,
            "title": title,
            "message": message,
            "topic": topic,
            "time": datetime.now().isoformat()
        }
        # Keep only last 100 messages to prevent memory bloat
        if len(self.message_store) > 100:
            oldest_keys = sorted(self.message_store.keys())[:50]
            for key in oldest_keys:
                del self.message_store[key]
        return msg_id

    def create_styled_button_row(self, name: str, title: str = None, message: str = "", topic: str = None) -> tuple:
        """Create a styled button row for a character message.

        This renders messages as tappable buttons that look like styled chat.
        Tapping triggers "tap on shoulder" interaction.

        Args:
            name: Character name (Ralph, Stool, Gomer, Mona, Gus)
            title: Optional job title
            message: The message content
            topic: Optional topic for context-aware tap responses

        Returns:
            Tuple of (button_text, InlineKeyboardMarkup, msg_id)
        """
        emoji = self.CHARACTER_COLORS.get(name, "⚪")
        preview = self._truncate_for_button(message)

        # Store the full message for tap retrieval
        msg_id = self.store_message_for_tap(name, title, message, topic)

        # Create button text: emoji + name + preview
        button_text = f"{emoji} {name}: {preview}"

        # Create keyboard with single button row
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(button_text, callback_data=f"tap_{msg_id}")]
        ])

        return (button_text, keyboard, msg_id)

    async def send_styled_message(
        self,
        context,
        chat_id: int,
        name: str,
        title: str = None,
        message: str = "",
        topic: str = None,
        use_buttons: bool = True,
        with_typing: bool = True
    ) -> bool:
        """Send a character message as a styled button or fallback to text.

        This is the primary method for sending character dialogue.
        Messages appear as tappable buttons that trigger "tap on shoulder"
        interactions when clicked.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            name: Character name (Ralph, Stool, Gomer, Mona, Gus)
            title: Optional job title
            message: The message content
            topic: Optional topic for context-aware tap responses
            use_buttons: Whether to use button styling (True) or plain text
            with_typing: Whether to show typing indicator first

        Returns:
            True if sent successfully, False if fallback was used
        """
        # Show typing indicator if requested
        if with_typing:
            text_len = len(message) if message else 0
            if text_len < 50:
                typing_duration = random.uniform(0.3, 0.7)
            elif text_len < 150:
                typing_duration = random.uniform(0.7, 1.5)
            else:
                typing_duration = random.uniform(1.5, 2.5)
            await self.send_typing(context, chat_id, typing_duration)

        # Try button styling first
        if use_buttons:
            try:
                _, keyboard, msg_id = self.create_styled_button_row(name, title, message, topic)

                # Send the full formatted message with the button keyboard
                full_text = self.format_character_message(name, title, message)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=full_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return True
            except Exception as e:
                logger.warning(f"Button styling failed, falling back to text: {e}")

        # Fallback to plain text formatting
        try:
            full_text = self.format_character_message(name, title, message)
            await context.bot.send_message(
                chat_id=chat_id,
                text=full_text,
                parse_mode="Markdown"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Last resort: send without markdown
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{name}: {message}"
                )
            except:
                pass
            return False

    def generate_tap_response(self, name: str, topic: str = None) -> str:
        """Generate a fresh "tap on shoulder" response for a character.

        When the CEO taps on a worker, they turn around surprised.
        Each character responds differently based on their personality.

        Args:
            name: Character name who was tapped
            topic: Optional topic they were discussing (for context)

        Returns:
            A fresh, character-appropriate surprised response
        """
        # Character-specific surprised reactions (varied, never canned)
        reactions_by_character = {
            "Ralph": [
                "Oh! Hi! I was just thinking about butterflies!",
                "You tapped me! That tickles my brain!",
                "My cat does that too! But with claws!",
                "Is it time for paste? I hope it's time for paste!",
                "I saw you! With my eyes!",
            ],
            "Stool": [
                "Oh hey! What's up?",
                "Yo! Didn't see you there, boss.",
                "Oh! Lowkey scared me for a sec.",
                "Hey! Just vibing over here.",
                "Oh snap! What's good?",
            ],
            "Gomer": [
                "D'oh! You startled me!",
                "Mmm? Oh! Hi there!",
                "Woah! Didn't hear you coming!",
                "Oh boy! Is it donut time?",
                "Huh? Oh! Hey boss!",
            ],
            "Mona": [
                "Oh! I was in the middle of analyzing something.",
                "Hmm? Can I help you with something?",
                "Oh, hello. I have some insights if you're interested.",
                "Yes? I was just running some calculations.",
                "Ah, you need something? I anticipated this.",
            ],
            "Gus": [
                "*nearly spills coffee* What is it?",
                "Huh? Oh. What do you need, kid?",
                "*sighs* I was almost done with my coffee.",
                "Yeah? What's the emergency now?",
                "I've been doing this job longer than you've been alive. What is it?",
            ],
        }

        reactions = reactions_by_character.get(name, ["Oh! You tapped me!"])
        base_reaction = random.choice(reactions)

        # Add topic context if available
        if topic:
            topic_additions = [
                f" Were you curious about {topic}?",
                f" I was just thinking about {topic}.",
                f" Did you want to discuss {topic}?",
            ]
            if random.random() < 0.4:  # 40% chance to mention topic
                base_reaction += random.choice(topic_additions)

        return base_reaction

    async def handle_tap_on_shoulder(self, query, context) -> None:
        """Handle when CEO taps on a worker's message button.

        This creates the "tap on shoulder" interaction - the worker
        turns around surprised with a fresh, personality-driven response.

        Args:
            query: The callback query from button press
            context: Telegram context
        """
        user_id = query.from_user.id
        msg_id = query.data.replace("tap_", "")

        # Retrieve the stored message
        stored = self.message_store.get(msg_id)
        if not stored:
            await query.answer("That conversation has moved on!", show_alert=False)
            return

        name = stored.get("name", "Worker")
        title = stored.get("title")
        topic = stored.get("topic")
        original_message = stored.get("message", "")

        # Generate a fresh surprised response
        tap_response = self.generate_tap_response(name, topic)

        # Answer the callback to stop loading indicator
        await query.answer()

        # Send the tap response
        chat_id = query.message.chat_id

        # First, show they noticed
        await self.send_typing(context, chat_id, random.uniform(0.3, 0.8))
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"_{name} turns around_",
            parse_mode="Markdown"
        )

        await asyncio.sleep(random.uniform(0.3, 0.7))

        # Then their response
        await self.send_styled_message(
            context, chat_id, name, title,
            tap_response,
            topic=topic,
            with_typing=True
        )

        # Ralph might notice chain of command violation (20% chance)
        if name != "Ralph" and random.random() < 0.2:
            await asyncio.sleep(random.uniform(1.0, 2.0))
            ralph_notices = [
                "Hey! Are you talking to my workers? That's MY job!",
                "Ooh, are we having a meeting? I love meetings!",
                "I saw that! I'm the boss so I see everything!",
            ]
            ralph_response = self.ralph_misspell(random.choice(ralph_notices))
            await self.send_styled_message(
                context, chat_id, "Ralph", None,
                ralph_response,
                with_typing=True
            )

    # ==================== INTERACTIVE ONBOARDING ====================

    # Worker arrival messages - casual office atmosphere
    WORKER_ARRIVALS = {
        "Stool": [
            ("_Stool walks in with an iced coffee_", "Morning! Traffic was actually chill today."),
            ("_Stool slides into the office_", "Yo! Made it just in time."),
            ("_Stool arrives with headphones around neck_", "What's up everyone? Vibes are good today."),
        ],
        "Gomer": [
            ("_Gomer lumbers in with a box of donuts_", "I brought donuts! Mmm... donuts."),
            ("_Gomer trips slightly entering_", "D'oh! I'm here! Did I miss anything?"),
            ("_Gomer arrives munching on something_", "Oh boy, new project? Exciting!"),
        ],
        "Mona": [
            ("_Mona walks in with a laptop already open_", "I've been reviewing some data on the way in. Fascinating patterns."),
            ("_Mona enters with a determined stride_", "Good morning. I have some preliminary thoughts."),
            ("_Mona arrives checking her phone_", "The metrics from yesterday are interesting. Let's discuss."),
        ],
        "Gus": [
            ("_Gus shuffles in with a massive coffee mug_", "Hrmph. Coffee machine better be working."),
            ("_Gus arrives looking tired_", "*sips coffee* I've been doing this for 25 years. What's one more project?"),
            ("_Gus enters checking his watch_", "Right on time. Unlike some people I've worked with."),
        ],
    }

    # Background office chatter for atmosphere
    BACKGROUND_CHATTER = [
        ("Stool", "Gomer", "So did you catch the game last night?", "Mmm, no, I was watching cooking shows."),
        ("Mona", "Gus", "The quarterly reports look promising.", "*grunts* I've seen promising turn to panic before."),
        ("Gomer", "Stool", "Want a donut?", "Nah, trying to eat clean. Maybe just one."),
        ("Gus", "Mona", "Remember that bug in '09?", "The one that took down production for 3 hours? How could I forget?"),
    ]

    # Ralph's discovery questions during onboarding
    ONBOARDING_QUESTIONS = [
        {
            "question": "What are we building here, Mr. Worms?",
            "options": [
                ("🚀 New feature", "new_feature", "Something shiny and new!"),
                ("🐛 Bug fixes", "bug_fix", "Squashing some creepy crawlies!"),
                ("🔧 Improvements", "improvement", "Making good things gooder!"),
                ("🤷 Not sure yet", "explore", "Let's figure it out together!"),
            ]
        },
        {
            "question": "What's the MOST importent thing to get right?",
            "options": [
                ("⚡ Speed", "speed", "Fast like my cat when she sees a bug!"),
                ("🎨 Looks good", "design", "Pretty like a butterfly!"),
                ("🔒 Works right", "reliability", "Solid like a rock!"),
                ("📋 Everything", "all", "All the things!"),
            ]
        },
        {
            "question": "How fast do you need this? Rush job or take our time?",
            "options": [
                ("🔥 ASAP!", "urgent", "Drop everything mode!"),
                ("📅 Soon-ish", "normal", "Regular speed ahead!"),
                ("🐢 No rush", "relaxed", "Nice and easy!"),
            ]
        },
    ]

    async def start_interactive_onboarding(self, context, chat_id: int, user_id: int, project_name: str):
        """Start the interactive onboarding experience while analysis runs in background.

        This creates entertainment and gathers user context while the code analysis
        completes in parallel. Workers trickle in, Ralph asks questions, and the
        scene builds naturally.

        Args:
            context: Telegram context
            chat_id: Chat to send messages to
            user_id: User's ID
            project_name: Name of the uploaded project
        """
        # Initialize onboarding state
        self.onboarding_state[user_id] = {
            "stage": "arriving",
            "workers_arrived": [],
            "question_index": 0,
            "answers": {},
            "project_name": project_name,
            "started": datetime.now(),
        }

        # Stage 1: Office opens
        await context.bot.send_message(
            chat_id=chat_id,
            text=self.format_action("The office lights flicker on. Another day at Ralph Mode HQ..."),
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)

        # Stage 2: Workers arrive one by one (staggered)
        await self._workers_arrive(context, chat_id, user_id)

        # Stage 3: Ralph enters and asks first question
        await self._ralph_enters_onboarding(context, chat_id, user_id)

    async def _workers_arrive(self, context, chat_id: int, user_id: int):
        """Workers trickle into the office with casual greetings.

        Creates atmosphere while analysis runs in background.
        """
        state = self.onboarding_state.get(user_id, {})

        # Workers arrive in random order, not all at once
        worker_order = list(self.DEV_TEAM.keys())
        random.shuffle(worker_order)

        # Only 2-3 workers arrive during onboarding (others "were already here")
        arriving_workers = worker_order[:random.randint(2, 3)]

        for name in arriving_workers:
            worker = self.DEV_TEAM[name]
            arrivals = self.WORKER_ARRIVALS.get(name, [("_Worker arrives_", "Morning.")])
            action, greeting = random.choice(arrivals)

            # Action narration
            await context.bot.send_message(
                chat_id=chat_id,
                text=action,
                parse_mode="Markdown"
            )
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # Worker greeting with styled button
            await self.send_styled_message(
                context, chat_id, name, worker['title'], greeting,
                topic="morning arrival",
                with_typing=True
            )

            state['workers_arrived'].append(name)
            await asyncio.sleep(random.uniform(1.0, 2.0))

        # Maybe some background chatter
        if random.random() < 0.4:
            chatter = random.choice(self.BACKGROUND_CHATTER)
            await asyncio.sleep(0.5)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"_{chatter[0]} to {chatter[1]}: '{chatter[2]}'_\n_{chatter[1]}: '{chatter[3]}'_",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.0)

    async def _ralph_enters_onboarding(self, context, chat_id: int, user_id: int):
        """Ralph enters and starts asking questions about the project."""
        state = self.onboarding_state.get(user_id, {})

        # Ralph enters
        await context.bot.send_message(
            chat_id=chat_id,
            text=self.format_action("The door bursts open. Ralph Wiggum arrives with his juice box and upside-down badge."),
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.0)

        ralph_greeting = self.ralph_misspell(
            f"Hi everyone! I'm the boss now! Mr. Worms sent us a new projeck called '{state.get('project_name', 'something')}'. "
            "My cat would be so proud!"
        )
        await self.send_styled_message(
            context, chat_id, "Ralph", None, ralph_greeting,
            topic="arrival",
            with_typing=True
        )

        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, "happy")

        await asyncio.sleep(1.5)

        # Ask first onboarding question
        await self._ask_onboarding_question(context, chat_id, user_id, 0)

    async def _ask_onboarding_question(self, context, chat_id: int, user_id: int, question_index: int):
        """Ask an onboarding question with inline buttons.

        Args:
            context: Telegram context
            chat_id: Chat ID
            user_id: User ID
            question_index: Which question to ask (0-2)
        """
        state = self.onboarding_state.get(user_id, {})
        if question_index >= len(self.ONBOARDING_QUESTIONS):
            return

        question_data = self.ONBOARDING_QUESTIONS[question_index]
        question_text = self.ralph_misspell(question_data["question"])

        # Build inline keyboard
        buttons = []
        for label, callback_value, _ in question_data["options"]:
            buttons.append([InlineKeyboardButton(
                label,
                callback_data=f"onboard_{question_index}_{callback_value}"
            )])

        # Add skip option
        buttons.append([InlineKeyboardButton("⏭️ Just get started!", callback_data="onboard_skip")])

        keyboard = InlineKeyboardMarkup(buttons)

        await self.send_styled_message(
            context, chat_id, "Ralph", None, question_text,
            topic="onboarding question",
            use_buttons=False,  # Use text for the question
            with_typing=True
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text="_Ralph looks at you expectantly, juice box in hand._",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        state["question_index"] = question_index

    async def handle_onboarding_answer(self, query, context, user_id: int, answer_data: str):
        """Handle an onboarding question answer from inline button.

        Args:
            query: Callback query
            context: Telegram context
            user_id: User's ID
            answer_data: The callback data (e.g., "onboard_0_new_feature" or "onboard_skip")
        """
        chat_id = query.message.chat_id
        state = self.onboarding_state.get(user_id, {})

        if answer_data == "onboard_skip":
            # User wants to skip questions
            await query.answer("Skipping to the good stuff!")
            await self._finish_onboarding(context, chat_id, user_id, skipped=True)
            return

        # Parse the answer
        parts = answer_data.replace("onboard_", "").split("_", 1)
        if len(parts) != 2:
            await query.answer()
            return

        question_index = int(parts[0])
        answer_value = parts[1]

        # Store the answer
        state["answers"][question_index] = answer_value

        # Ralph reacts to the answer
        question_data = self.ONBOARDING_QUESTIONS[question_index]
        for label, value, ralph_reaction in question_data["options"]:
            if value == answer_value:
                ralph_response = self.ralph_misspell(ralph_reaction)
                break
        else:
            ralph_response = self.ralph_misspell("Ooh, interesting!")

        await query.answer()

        # Edit the message to remove buttons
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except:
            pass

        # Ralph reacts
        await self.send_styled_message(
            context, chat_id, "Ralph", None, ralph_response,
            topic="question reaction",
            with_typing=True
        )

        await asyncio.sleep(1.0)

        # Check if analysis is done before asking more questions
        analysis_task = self.pending_analysis.get(user_id)
        if analysis_task and analysis_task.done():
            # Analysis finished - wrap up onboarding
            await self._finish_onboarding(context, chat_id, user_id)
            return

        # Ask next question or finish
        next_index = question_index + 1
        if next_index < len(self.ONBOARDING_QUESTIONS):
            # Maybe some worker chatter between questions
            if random.random() < 0.3:
                worker = random.choice(list(self.DEV_TEAM.keys()))
                worker_data = self.DEV_TEAM[worker]
                comments = [
                    "Good question, boss.",
                    "I was wondering that too.",
                    "Makes sense to ask that.",
                    "The boss is on a roll today!",
                ]
                await self.send_styled_message(
                    context, chat_id, worker, worker_data['title'],
                    random.choice(comments),
                    topic="onboarding comment",
                    with_typing=True
                )
                await asyncio.sleep(0.8)

            await self._ask_onboarding_question(context, chat_id, user_id, next_index)
        else:
            # All questions answered
            await self._finish_onboarding(context, chat_id, user_id)

    async def _finish_onboarding(self, context, chat_id: int, user_id: int, skipped: bool = False):
        """Finish onboarding and transition to analysis results.

        If analysis is still running, wait for it. Then merge onboarding context
        with analysis results.

        Args:
            context: Telegram context
            chat_id: Chat ID
            user_id: User ID
            skipped: Whether user skipped the questions
        """
        state = self.onboarding_state.get(user_id, {})

        # Check if analysis is complete
        analysis_task = self.pending_analysis.get(user_id)
        if analysis_task and not analysis_task.done():
            # Analysis still running - show waiting message
            await context.bot.send_message(
                chat_id=chat_id,
                text=self.format_action("Ralph squints at his computer, waiting for the 'compooter magic' to finish..."),
                parse_mode="Markdown"
            )

            # Wait for analysis with a fun loading animation
            ralph_waiting = [
                "The compooter is thinking... I think I hear it humming!",
                "Almost there! My cat thinks faster than this!",
                "Still werking... I can see the little dots moving!",
            ]

            try:
                # Wait with timeout
                for i in range(3):
                    if analysis_task.done():
                        break
                    await asyncio.sleep(2)
                    if not analysis_task.done() and i < 2:
                        await self.send_styled_message(
                            context, chat_id, "Ralph", None,
                            self.ralph_misspell(ralph_waiting[i]),
                            topic="waiting",
                            with_typing=True
                        )

                # Final wait if needed
                analysis = await asyncio.wait_for(analysis_task, timeout=30)
            except asyncio.TimeoutError:
                analysis = {"summary": "Analysis timed out. Let's work with what we have!"}
        else:
            # Analysis already done
            analysis = analysis_task.result() if analysis_task else None

        # Store analysis in session
        session = self.active_sessions.get(user_id, {})
        if analysis:
            session["analysis"] = analysis

        # Store onboarding context in session
        session["onboarding_answers"] = state.get("answers", {})
        session["onboarding_context"] = self._build_onboarding_context(state)

        # Ralph summarizes what he learned
        if not skipped and state.get("answers"):
            summary = self._build_onboarding_summary(state)
            await context.bot.send_message(
                chat_id=chat_id,
                text=self.format_action("Ralph straightens his upside-down badge and addresses the team."),
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.5)

            await self.send_styled_message(
                context, chat_id, "Ralph", None,
                self.ralph_misspell(summary),
                topic="onboarding summary",
                with_typing=True
            )

            # Team acknowledges
            await asyncio.sleep(1.0)
            reactions = ["Got it, boss!", "Understood.", "Let's do this!", "Makes sense."]
            worker = random.choice(list(self.DEV_TEAM.keys()))
            worker_data = self.DEV_TEAM[worker]
            await self.send_styled_message(
                context, chat_id, worker, worker_data['title'],
                random.choice(reactions),
                topic="acknowledgment",
                with_typing=True
            )

        # Clean up onboarding state
        if user_id in self.onboarding_state:
            del self.onboarding_state[user_id]
        if user_id in self.pending_analysis:
            del self.pending_analysis[user_id]

        # Now show analysis results and offer next steps
        await asyncio.sleep(1.0)
        if analysis:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*Codebase Analysis Complete*\n\n{analysis.get('summary', 'Analysis ready!')}",
                parse_mode="Markdown"
            )

        # Offer to generate PRD
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Generate Task List", callback_data="generate_prd")],
            [InlineKeyboardButton("🎯 I'll provide tasks", callback_data="manual_prd")],
        ])

        await context.bot.send_message(
            chat_id=chat_id,
            text="What would you like to do next?",
            reply_markup=keyboard
        )

    def _build_onboarding_context(self, state: Dict) -> str:
        """Build a context string from onboarding answers for AI prompts.

        Args:
            state: Onboarding state dictionary

        Returns:
            Context string to include in AI prompts
        """
        answers = state.get("answers", {})
        if not answers:
            return ""

        context_parts = []
        answer_meanings = {
            0: {
                "new_feature": "building a new feature",
                "bug_fix": "fixing bugs",
                "improvement": "making improvements",
                "explore": "exploring the code",
            },
            1: {
                "speed": "prioritize performance",
                "design": "prioritize UI/UX",
                "reliability": "prioritize stability",
                "all": "balance everything",
            },
            2: {
                "urgent": "this is urgent/ASAP",
                "normal": "normal timeline",
                "relaxed": "no rush, take time",
            },
        }

        for q_idx, answer in answers.items():
            if q_idx in answer_meanings and answer in answer_meanings[q_idx]:
                context_parts.append(answer_meanings[q_idx][answer])

        return f"CEO context: {', '.join(context_parts)}" if context_parts else ""

    def _build_onboarding_summary(self, state: Dict) -> str:
        """Build Ralph's summary of what he learned from onboarding.

        Args:
            state: Onboarding state dictionary

        Returns:
            Ralph's summary in his voice
        """
        answers = state.get("answers", {})
        project_name = state.get("project_name", "the projeck")

        parts = [f"Okay team! Mr. Worms told me about {project_name}!"]

        if 0 in answers:
            task_type = {
                "new_feature": "We're making something NEW and shiny!",
                "bug_fix": "We're squashing bugs! Like real bugs but in the compooter!",
                "improvement": "We're making things BETTER! Like adding more paste!",
                "explore": "We're going on an adventure to find out what this does!",
            }
            parts.append(task_type.get(answers[0], "We're doing stuff!"))

        if 1 in answers:
            priority = {
                "speed": "Mr. Worms says it needs to go FAST! Zoom zoom!",
                "design": "It needs to look PRETTY! Like a butterfly!",
                "reliability": "It needs to work GOOD! No breaking!",
                "all": "Everything is importent! All the things!",
            }
            parts.append(priority.get(answers[1], "It needs to be good!"))

        if 2 in answers:
            urgency = {
                "urgent": "And we need to do it QUICK! My tummy is nervous!",
                "normal": "We have time but not TOO much time!",
                "relaxed": "No rush! Like a turtle but one that finishes things!",
            }
            parts.append(urgency.get(answers[2], "Let's do our best!"))

        return " ".join(parts)

    # ==================== CHARACTER FORMATTING ====================

    def get_character_prefix(self, name: str) -> str:
        """Get the color emoji prefix for a character.

        Returns format like '🔴 *Ralph:*' for consistent visual identity.
        """
        emoji = self.CHARACTER_COLORS.get(name, "⚪")  # Default to white if unknown
        return f"{emoji} *{name}:*"

    async def send_typing(self, context, chat_id: int, duration: float = 1.0):
        """Send typing indicator for realistic feel.

        Args:
            context: Telegram context
            chat_id: Chat to send typing to
            duration: How long to show typing (seconds)
        """
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(duration)
        except Exception as e:
            logger.warning(f"Typing indicator failed: {e}")

    async def send_with_typing(self, context, chat_id: int, text: str, parse_mode: str = "Markdown", reply_markup=None, typing_duration: float = None):
        """Send a message with a preceding typing indicator.

        Duration scales with message length for realism:
        - Short messages (< 50 chars): 0.5-1s
        - Medium messages (50-150 chars): 1-2s
        - Long messages (> 150 chars): 2-3s

        Args:
            context: Telegram context
            chat_id: Chat to send to
            text: Message text
            parse_mode: Markdown or HTML
            reply_markup: Optional keyboard
            typing_duration: Override automatic duration calculation
        """
        # Calculate typing duration based on message length if not specified
        if typing_duration is None:
            text_len = len(text) if text else 0
            if text_len < 50:
                typing_duration = random.uniform(0.5, 1.0)
            elif text_len < 150:
                typing_duration = random.uniform(1.0, 2.0)
            else:
                typing_duration = random.uniform(2.0, 3.0)

        # Show typing indicator
        await self.send_typing(context, chat_id, typing_duration)

        # Send the message
        if reply_markup:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )

    def format_character_message(self, name: str, title: str = None, message: str = "") -> str:
        """Format a message from a character with their color prefix.

        Args:
            name: Character name (Ralph, Stool, Gomer, Mona, Gus)
            title: Optional job title to include
            message: The message content

        Returns:
            Formatted string like '🔴 *Ralph:* Hi!'
            or '🟢 *Stool* _Frontend Dev_: Yo what's good?'
        """
        prefix = self.get_character_prefix(name)

        if title:
            return f"{prefix} _{title}_: {message}"
        else:
            return f"{prefix} {message}"

    def format_action(self, text: str) -> str:
        """Format an action/narration in italics.

        Used for stage directions like character movements and scene descriptions.

        Args:
            text: The action text to format

        Returns:
            Text wrapped in Telegram markdown italics

        Examples:
            >>> format_action("Gus sips his coffee thoughtfully")
            '_Gus sips his coffee thoughtfully_'
            >>> format_action("The team gathers around the whiteboard")
            '_The team gathers around the whiteboard_'
        """
        if not text:
            return ""
        # Remove any existing underscores at start/end to avoid double formatting
        text = text.strip('_')
        return f"_{text}_"

    def format_code(self, code: str, language: str = "") -> str:
        """Format code with proper Telegram markdown code blocks.

        Uses triple backticks for multi-line code blocks with optional
        language hint, or single backticks for inline code.

        Args:
            code: The code to format
            language: Optional language for syntax hint (e.g., "python", "javascript")

        Returns:
            Properly formatted code block string

        Examples:
            >>> format_code("x = 1", "python")
            '```python\\nx = 1\\n```'
            >>> format_code("doThing()")
            '`doThing()`'
        """
        if not code:
            return ""

        # Check if it's multi-line or long code
        is_multiline = '\n' in code or len(code) > 60

        if is_multiline:
            # Use triple backtick code block
            lang_hint = language if language else ""
            return f"```{lang_hint}\n{code}\n```"
        else:
            # Use inline code
            return f"`{code}`"

    def format_code_inline(self, code: str) -> str:
        """Format short code snippets with inline backticks.

        Args:
            code: The code snippet

        Returns:
            Code wrapped in single backticks

        Example:
            >>> format_code_inline("function doThing()")
            '`function doThing()`'
        """
        if not code:
            return ""
        return f"`{code}`"

    def format_progress_bar(self, done: int, total: int, bar_length: int = 10) -> str:
        """Create a visual progress bar using emoji blocks.

        Args:
            done: Number of completed tasks
            total: Total number of tasks
            bar_length: Length of the bar in characters (default 10)

        Returns:
            Formatted progress bar string

        Example:
            >>> format_progress_bar(4, 10)
            '▓▓▓▓░░░░░░ 4/10 (40%)'
        """
        if total <= 0:
            return "░" * bar_length + " 0/0 (0%)"

        percentage = (done / total) * 100
        filled = int((done / total) * bar_length)
        empty = bar_length - filled

        bar = "▓" * filled + "░" * empty
        return f"{bar} {done}/{total} ({percentage:.0f}%)"

    def escape_markdown(self, text: str) -> str:
        """Escape special markdown characters in text.

        Use this when text might contain characters that would break
        Telegram's markdown parsing (like * or _ in user input).

        Args:
            text: Text that might contain markdown special chars

        Returns:
            Text with special characters escaped
        """
        if not text:
            return ""
        # Telegram markdown special chars: _ * [ ] ( ) ~ ` > # + - = | { } . !
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    async def safe_send_message(
        self,
        context,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
        reply_markup=None
    ) -> bool:
        """Send a message with automatic fallback if markdown fails.

        First attempts to send with markdown formatting. If that fails
        (usually due to unbalanced formatting chars), retries as plain text.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            text: Message text (may contain markdown)
            parse_mode: Parsing mode, defaults to Markdown
            reply_markup: Optional keyboard markup

        Returns:
            True if sent with formatting, False if fell back to plain text
        """
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            logger.warning(f"Markdown send failed, falling back to plain text: {e}")
            try:
                # Strip markdown and send plain
                plain_text = text.replace('*', '').replace('_', '').replace('`', '')
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=plain_text,
                    reply_markup=reply_markup
                )
                return False
            except Exception as e2:
                logger.error(f"Plain text send also failed: {e2}")
                return False

    # ==================== RALPH'S AUTHENTIC VOICE ====================

    def ralph_misspell(self, text: str, misspell_chance: float = 0.2) -> str:
        """Apply Ralph's dyslexia/misspellings to text.

        Args:
            text: The text to potentially misspell
            misspell_chance: Probability (0-1) of misspelling each applicable word (default 20%)

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

            if word_clean in self.RALPH_MISSPELLINGS:
                # Only misspell with the given probability
                if random.random() < misspell_chance:
                    misspelled = self.RALPH_MISSPELLINGS[word_clean]

                    # Preserve original capitalization
                    if word[0].isupper():
                        misspelled = misspelled.capitalize()
                    if word.isupper():
                        misspelled = misspelled.upper()

                    # Preserve trailing punctuation
                    trailing = ""
                    for char in reversed(word):
                        if char in '.,!?;:\'\"()[]{}':
                            trailing = char + trailing
                        else:
                            break

                    result.append(misspelled + trailing)
                else:
                    result.append(word)
            else:
                result.append(word)

        return ' '.join(result)

    # ==================== QUALITY METRICS TRACKING ====================

    def init_quality_metrics(self, user_id: int):
        """Initialize quality metrics tracking for a session."""
        self.quality_metrics[user_id] = {
            "tasks_identified": 0,
            "tasks_completed": 0,
            "code_snippets_provided": 0,
            "actionable_items": [],
            "issues_found": [],
            "blockers_hit": 0,
            "blockers_resolved": 0,
            "session_start": datetime.now(),
            "quality_checks_passed": 0,
            "quality_checks_failed": 0,
            "task_durations": [],  # List of task durations in seconds for ETA calculation
            "current_task_start": None,  # When current task started
            "last_progress_shown": None,  # When progress bar was last shown
        }

    def track_task_identified(self, user_id: int, task_title: str, priority: str = "medium"):
        """Track when a task is identified."""
        if user_id not in self.quality_metrics:
            self.init_quality_metrics(user_id)
        self.quality_metrics[user_id]["tasks_identified"] += 1
        self.quality_metrics[user_id]["actionable_items"].append({
            "type": "task",
            "title": task_title,
            "priority": priority,
            "status": "identified"
        })

    def track_task_started(self, user_id: int):
        """Mark the start of a task for duration tracking."""
        if user_id not in self.quality_metrics:
            self.init_quality_metrics(user_id)
        self.quality_metrics[user_id]["current_task_start"] = datetime.now()

    def track_task_completed(self, user_id: int, task_title: str):
        """Track when a task is completed."""
        if user_id not in self.quality_metrics:
            self.init_quality_metrics(user_id)

        m = self.quality_metrics[user_id]
        m["tasks_completed"] += 1

        # Calculate and store task duration
        if m.get("current_task_start"):
            duration = (datetime.now() - m["current_task_start"]).total_seconds()
            m["task_durations"].append(duration)
            m["current_task_start"] = None

        # Update status in actionable items
        for item in m["actionable_items"]:
            if item.get("title") == task_title:
                item["status"] = "completed"
                break

    def track_code_provided(self, user_id: int, language: str = "unknown"):
        """Track when a code snippet is provided."""
        if user_id not in self.quality_metrics:
            self.init_quality_metrics(user_id)
        self.quality_metrics[user_id]["code_snippets_provided"] += 1

    def track_issue_found(self, user_id: int, issue: str, severity: str = "medium"):
        """Track when an issue is identified."""
        if user_id not in self.quality_metrics:
            self.init_quality_metrics(user_id)
        self.quality_metrics[user_id]["issues_found"].append({
            "issue": issue,
            "severity": severity,
            "time": datetime.now().isoformat()
        })

    def track_quality_check(self, user_id: int, passed: bool):
        """Track a quality check result."""
        if user_id not in self.quality_metrics:
            self.init_quality_metrics(user_id)
        if passed:
            self.quality_metrics[user_id]["quality_checks_passed"] += 1
        else:
            self.quality_metrics[user_id]["quality_checks_failed"] += 1

    def get_quality_summary(self, user_id: int) -> str:
        """Get a summary of quality metrics for the session."""
        if user_id not in self.quality_metrics:
            return "No quality metrics available."

        m = self.quality_metrics[user_id]
        completion_rate = 0
        if m["tasks_identified"] > 0:
            completion_rate = (m["tasks_completed"] / m["tasks_identified"]) * 100

        summary = f"""📊 *Session Quality Metrics*

Tasks: {m['tasks_completed']}/{m['tasks_identified']} completed ({completion_rate:.0f}%)
Code snippets provided: {m['code_snippets_provided']}
Issues identified: {len(m['issues_found'])}
Quality checks: {m['quality_checks_passed']} passed, {m['quality_checks_failed']} failed
"""
        return summary

    # ==================== PROGRESS BAR DISPLAY ====================

    def calculate_eta(self, user_id: int) -> tuple:
        """Calculate estimated time remaining based on task durations.

        Returns:
            Tuple of (eta_string, estimated_completion_time)
            eta_string: e.g., "~8 min" or "Calculating..."
            estimated_completion_time: datetime or None
        """
        if user_id not in self.quality_metrics:
            return ("Calculating...", None)

        m = self.quality_metrics[user_id]
        durations = m.get("task_durations", [])
        tasks_done = m.get("tasks_completed", 0)
        tasks_total = m.get("tasks_identified", 0)
        tasks_remaining = tasks_total - tasks_done

        if tasks_remaining <= 0:
            return ("Done!", datetime.now())

        if len(durations) < 2:
            return ("Calculating...", None)

        # Calculate average duration of completed tasks
        avg_duration = sum(durations) / len(durations)
        eta_seconds = avg_duration * tasks_remaining

        # Format ETA
        if eta_seconds < 60:
            eta_str = f"~{int(eta_seconds)} sec"
        elif eta_seconds < 3600:
            eta_str = f"~{int(eta_seconds / 60)} min"
        else:
            hours = int(eta_seconds / 3600)
            mins = int((eta_seconds % 3600) / 60)
            eta_str = f"~{hours}h {mins}m"

        # Calculate completion time
        completion_time = datetime.now() + timedelta(seconds=eta_seconds)

        return (eta_str, completion_time)

    def format_elapsed_time(self, start_time: datetime) -> str:
        """Format elapsed time since session start.

        Args:
            start_time: When the session started

        Returns:
            Formatted string like "12m 34s" or "1h 5m"
        """
        elapsed = datetime.now() - start_time
        total_seconds = int(elapsed.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            mins = total_seconds // 60
            secs = total_seconds % 60
            return f"{mins}m {secs}s"
        else:
            hours = total_seconds // 3600
            mins = (total_seconds % 3600) // 60
            return f"{hours}h {mins}m"

    async def show_progress_bar(self, context, chat_id: int, user_id: int, delay: float = 5.0):
        """Show a visual progress bar after task completion.

        Displays progress bar with:
        - Visual bar: ▓▓▓▓░░░░░░
        - Task count: 4/10 tasks (40%)
        - Time elapsed
        - ETA with estimated completion time
        - Clean separators

        Args:
            context: Telegram context
            chat_id: Chat to send to
            user_id: User ID for metrics lookup
            delay: Seconds to wait before showing (default 5s for tasteful timing)
        """
        # Wait for tasteful timing
        await asyncio.sleep(delay)

        if user_id not in self.quality_metrics:
            return

        m = self.quality_metrics[user_id]
        tasks_done = m.get("tasks_completed", 0)
        tasks_total = m.get("tasks_identified", 0)
        session_start = m.get("session_start", datetime.now())

        if tasks_total <= 0:
            return

        # Build the progress display
        progress_bar = self.format_progress_bar(tasks_done, tasks_total, bar_length=10)
        elapsed = self.format_elapsed_time(session_start)
        eta_str, completion_time = self.calculate_eta(user_id)

        # Format completion time if available
        completion_str = ""
        if completion_time:
            completion_str = f"\nEst. done: {completion_time.strftime('%I:%M %p')}"

        progress_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 *Progress*
{progress_bar}

⏱ Elapsed: {elapsed}
⏳ ETA: {eta_str}{completion_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=progress_text,
                parse_mode="Markdown"
            )
            m["last_progress_shown"] = datetime.now()
        except Exception as e:
            logger.warning(f"Failed to show progress bar: {e}")

    async def show_task_completion(self, context, chat_id: int, user_id: int, task_title: str = None):
        """Show task completion celebration and progress bar.

        This is called after each task completes. Shows a brief celebration
        followed by the progress bar after a tasteful delay.

        Args:
            context: Telegram context
            chat_id: Chat ID
            user_id: User ID
            task_title: Optional title of completed task
        """
        if user_id not in self.quality_metrics:
            return

        m = self.quality_metrics[user_id]
        tasks_done = m.get("tasks_completed", 0)
        tasks_total = m.get("tasks_identified", 0)

        # Quick completion message
        completion_msg = f"✅ Task {tasks_done}/{tasks_total} done!"
        if task_title:
            completion_msg = f"✅ *{task_title}* complete! ({tasks_done}/{tasks_total})"

        await context.bot.send_message(
            chat_id=chat_id,
            text=completion_msg,
            parse_mode="Markdown"
        )

        # Show progress bar after delay
        await self.show_progress_bar(context, chat_id, user_id, delay=5.0)

    # ==================== SESSION HISTORY (Ralph remembers everything) ====================

    def log_event(self, user_id: int, event_type: str, speaker: str, content: str, metadata: dict = None):
        """Log an event to session history so Ralph can answer questions later."""
        if user_id not in self.session_history:
            self.session_history[user_id] = []

        self.session_history[user_id].append({
            "time": datetime.now().isoformat(),
            "type": event_type,  # "message", "action", "decision", "issue", "feature"
            "speaker": speaker,  # "Ralph", "Jake", "Dan", "Maya", "Steve", "System"
            "content": content,
            "metadata": metadata or {}
        })

        # Keep last 100 events per user
        self.session_history[user_id] = self.session_history[user_id][-100:]

    def get_session_context(self, user_id: int) -> str:
        """Get full session history as context for Ralph's Q&A."""
        history = self.session_history.get(user_id, [])
        if not history:
            return "No session history yet."

        context_lines = []
        for event in history:
            speaker = event.get("speaker", "Unknown")
            content = event.get("content", "")
            event_type = event.get("type", "message")

            if event_type == "action":
                context_lines.append(f"[ACTION] {content}")
            elif event_type == "issue":
                context_lines.append(f"[ISSUE] {speaker}: {content}")
            elif event_type == "feature":
                context_lines.append(f"[FEATURE] {content}")
            else:
                context_lines.append(f"{speaker}: {content}")

        return "\n".join(context_lines[-50:])  # Last 50 events for context

    def ask_ralph(self, user_id: int, question: str) -> str:
        """Ask Ralph a question about the session. He remembers everything."""
        session = self.active_sessions.get(user_id, {})
        session_context = self.get_session_context(user_id)
        project_name = session.get('project_name', 'the project')

        prompt = f"""The CEO is asking you a question about the session.

PROJECT: {project_name}

EVERYTHING THAT HAPPENED (you saw all of this):
{session_context}

CEO'S QUESTION: {question}

Answer the CEO's question based on what you observed.
You're Ralph Wiggum - not that smart, but you remember EVERYTHING accurately.
- Use simple, plain language
- Be accurate about what happened
- If you don't know something, say so honestly
- Stay in character (might mention cat, daddy, paste)
- Keep answers focused and helpful

Answer the question directly. Don't ramble."""

        messages = [
            {"role": "system", "content": """You are Ralph Wiggum from The Simpsons, a manager.
The CEO is asking you questions about a work session you observed.
You're not very smart, but you remember EVERYTHING that happened accurately.
Answer in simple, plain language. Be accurate. Stay in character.
If asked about something you didn't observe, honestly say you don't know."""},
            {"role": "user", "content": prompt}
        ]
        return self.call_groq(WORKER_MODEL, messages, max_tokens=300)

    # ==================== TOKEN AWARENESS ====================

    def track_tokens(self, user_id: int, tokens: int):
        """Track token usage for a user."""
        if user_id not in self.token_history:
            self.token_history[user_id] = []
        self.token_history[user_id].append(tokens)
        # Keep last 20 entries
        self.token_history[user_id] = self.token_history[user_id][-20:]

    def get_ralph_token_observation(self, user_id: int, current_tokens: int) -> Optional[str]:
        """Ralph notices token usage patterns and comments like a manager."""
        history = self.token_history.get(user_id, [])

        if len(history) < 2:
            return None  # Not enough data yet

        avg_tokens = sum(history[:-1]) / len(history[:-1])
        last_tokens = history[-1] if history else 0

        observations = []

        # Compare to average
        if current_tokens > avg_tokens * 1.5:
            observations = [
                f"Wow, that was {current_tokens} words! That's way more than usual! *scribbles in notebook* I'm putting a gold star next to your name.",
                f"Hmmm, {current_tokens} words... that's a lot more than before! Are you okay? Do you need juice?",
                f"*squints at paper* {current_tokens}... that's bigger than last time! My daddy says bigger is better. Unless it's vegetables.",
                f"You used {current_tokens} words! That's like... *counts fingers* ...MORE! I'm writing this down.",
            ]
        elif current_tokens < avg_tokens * 0.5:
            observations = [
                f"Only {current_tokens} words? That was fast! Are you a wizard? I knew a wizard once. He was a leprechaun.",
                f"Wow, {current_tokens} words! So quick! I'm gonna tell my cat about you.",
                f"*looks impressed* {current_tokens}! That's way less than before! Efficiency! I learned that word yesterday.",
                f"Speedy! {current_tokens} words! My daddy says 'time is money' but I don't know where to spend it.",
            ]
        elif len(history) >= 5 and all(t > avg_tokens for t in history[-3:]):
            observations = [
                "I noticed you've been using more words lately. *taps head* Manager brain! I see patterns!",
                "The numbers are going up! That's good, right? Unless it's bad. Is it bad?",
            ]

        if observations:
            return random.choice(observations)
        return None

    # ==================== GIF SUPPORT ====================

    def get_gif(self, mood: str = "happy", speaker: str = "ralph") -> Optional[str]:
        """Get a random GIF URL from Tenor. Ralph gets Simpsons, workers get office memes."""
        try:
            if speaker == "ralph":
                gif_dict = self.RALPH_GIFS
                default_mood = "happy"
            else:
                gif_dict = self.WORKER_GIFS
                default_mood = "working"

            search_terms = gif_dict.get(mood, gif_dict.get(default_mood, ["funny gif"]))
            query = random.choice(search_terms)

            response = requests.get(
                "https://tenor.googleapis.com/v2/search",
                params={
                    "q": query,
                    "key": TENOR_API_KEY,
                    "limit": 10,
                    "media_filter": "gif"
                },
                timeout=5
            )
            results = response.json().get("results", [])
            if results:
                gif = random.choice(results)
                return gif.get("media_formats", {}).get("gif", {}).get("url")
        except Exception as e:
            logger.error(f"GIF fetch error: {e}")
        return None

    def should_send_gif(self) -> bool:
        """Random chance to send a GIF."""
        return random.random() < self.gif_chance

    def detect_mood_ralph(self, text: str) -> str:
        """Detect Ralph's mood from his message."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["approved", "great", "good", "yes", "ship it", "nice", "yay", "i like"]):
            return "approved"
        elif any(w in text_lower for w in ["haha", "funny", "joke", "laugh"]):
            return "laughing"
        elif any(w in text_lower for w in ["confused", "what", "huh", "don't understand"]):
            return "confused"
        elif any(w in text_lower for w in ["think", "hmm", "maybe"]):
            return "thinking"
        elif any(w in text_lower for w in ["sad", "no", "rejected", "bad"]):
            return "frustrated"
        return "happy"

    def detect_mood_worker(self, text: str) -> str:
        """Detect worker's mood from their message."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["problem", "issue", "error", "bug", "broken", "situation", "bad news"]):
            return "problem"
        elif any(w in text_lower for w in ["nervous", "uh", "um", "sorry", "afraid"]):
            return "nervous"
        elif any(w in text_lower for w in ["working", "implementing", "building", "coding", "done", "finished"]):
            return "working"
        elif any(w in text_lower for w in ["explain", "so basically", "let me"]):
            return "explaining"
        elif any(w in text_lower for w in ["phew", "relief", "thankfully", "glad"]):
            return "relieved"
        return "working"

    async def send_ralph_gif(self, context, chat_id: int, mood: str = "happy"):
        """Send a Ralph/Simpsons GIF."""
        gif_url = self.get_gif(mood, speaker="ralph")
        if gif_url:
            try:
                await context.bot.send_animation(chat_id=chat_id, animation=gif_url)
            except Exception as e:
                logger.error(f"Failed to send Ralph GIF: {e}")

    async def send_worker_gif(self, context, chat_id: int, mood: str = "working"):
        """Send a worker/office meme GIF."""
        gif_url = self.get_gif(mood, speaker="worker")
        if gif_url:
            try:
                await context.bot.send_animation(chat_id=chat_id, animation=gif_url)
            except Exception as e:
                logger.error(f"Failed to send worker GIF: {e}")

    def get_bribe_joke(self) -> str:
        """Get a random joke for workers to butter up Ralph."""
        return random.choice(self.BRIBE_JOKES)

    async def worker_bribes_ralph(self, context, chat_id: int, worker_name: str = None):
        """Worker softens up Ralph before bad news with a joke."""
        joke = self.get_bribe_joke()

        # Pick who's delivering the bad news
        if worker_name is None:
            worker_name = random.choice(list(self.DEV_TEAM.keys()))
        worker = self.DEV_TEAM[worker_name]

        # Worker offers the joke
        await self.send_with_typing(
            context, chat_id,
            self.format_character_message(worker_name, worker['title'], "Hey Ralphie-- I mean, sir... before I tell you something, you like jokes right?")
        )
        await asyncio.sleep(1)

        # Ralph loves jokes
        ralph_response = self.call_boss("Someone wants to tell you a joke! You LOVE jokes. Respond excitedly.")
        await self.send_with_typing(
            context, chat_id,
            self.format_character_message("Ralph", message=ralph_response)
        )
        await asyncio.sleep(0.5)

        # Worker tells the joke
        await self.send_with_typing(
            context, chat_id,
            self.format_character_message(worker_name, message=f"Okay here goes... {joke}")
        )

        # Chuck Norris or programming meme GIF
        if "chuck norris" in joke.lower():
            gif_url = self.get_gif("bribe", speaker="worker")
        else:
            gif_url = self.get_gif("explaining", speaker="worker")
        if gif_url:
            try:
                await context.bot.send_animation(chat_id=chat_id, animation=gif_url)
            except:
                pass

        await asyncio.sleep(2)

        # Ralph laughs
        await self.send_with_typing(
            context, chat_id,
            self.format_character_message("Ralph", message=self.ralph_misspell("Hahaha! That's a good one! My tummy feels like laughing!"))
        )
        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, "laughing")

        await asyncio.sleep(0.5)

        # Ralph asks what's up
        await self.send_with_typing(
            context, chat_id,
            self.format_character_message("Ralph", message="Okay, what did you want to tell me?")
        )

    # ==================== AI CALLS ====================

    def call_groq(self, model: str, messages: list, max_tokens: int = 500) -> str:
        """Call Groq API."""
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": max_tokens
                },
                timeout=60
            )
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "...")
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return f"[AI Error: {e}]"

    def call_boss(self, message: str, apply_misspellings: bool = True) -> str:
        """Get response from Ralph Wiggum, the boss.

        Args:
            message: The prompt/situation for Ralph to respond to
            apply_misspellings: Whether to apply Ralph's dyslexia misspellings (default True)

        Returns:
            Ralph's response, with misspellings applied if enabled
        """
        messages = [
            {"role": "system", "content": """You are Ralph Wiggum from The Simpsons. You just got promoted to MANAGER and you're SO proud.
Your name is Ralph. Sometimes people call you "Ralphie" by accident.
You take your job VERY seriously even though you don't understand technical stuff.
You ask simple questions with complete confidence. Sometimes accidentally brilliant, sometimes about leprechauns.
You love your team! You want to make the CEO proud of you.
You might mention your cat, your daddy, paste, or that you're a manager now.
Classic Ralph energy - innocent, cheerful, confidently confused.
Ask ONE question. Give verdicts (APPROVED/NEEDS WORK) with total confidence.
1-2 sentences max. Stay in character as Ralph."""},
            {"role": "user", "content": message}
        ]
        response = self.call_groq(BOSS_MODEL, messages, max_tokens=150)

        # Apply Ralph's authentic misspellings
        if apply_misspellings:
            response = self.ralph_misspell(response)

        return response

    def call_worker(self, message: str, context: str = "", worker_name: str = None, efficiency_mode: bool = False, task_type: str = "general") -> tuple:
        """Get response from a specific team member. Returns (name, title, response, tokens).

        task_type can be: "general", "code", "analysis", "review" - affects quality emphasis
        """
        # Pick a random team member if none specified
        if worker_name is None:
            worker_name = random.choice(list(self.DEV_TEAM.keys()))

        worker = self.DEV_TEAM[worker_name]

        # Efficiency guidance based on Ralph's feedback
        efficiency_note = ""
        if efficiency_mode:
            efficiency_note = """
IMPORTANT: Ralph just noticed you used a lot of words. He's watching!
Be MORE CONCISE this time. Get to the point. Ralph appreciates brevity.
1-2 sentences MAX. Prove you can be efficient!"""

        # Task-specific quality guidance
        task_guidance = ""
        if task_type == "code":
            task_guidance = """
When providing code:
- Give REAL, working code snippets - not pseudocode
- Include necessary imports and context
- Explain what the code does briefly
- Flag any potential issues or edge cases"""
        elif task_type == "analysis":
            task_guidance = """
When analyzing:
- Be specific about what you find - file names, line numbers when relevant
- Prioritize issues by severity
- Don't just list problems - suggest solutions
- Be honest about uncertainties"""
        elif task_type == "review":
            task_guidance = """
When reviewing:
- Check for bugs, security issues, and performance problems
- Be constructive - explain WHY something is an issue
- Suggest specific improvements with examples
- Acknowledge what's done well too"""

        messages = [
            {"role": "system", "content": f"""{WORK_QUALITY_PRIORITY}

{worker['personality']}

You work under Ralph Wiggum (yes, THAT Ralph from The Simpsons). He's your boss now.
He's sweet but clueless. You genuinely like him despite everything.
Sometimes you accidentally call him "Ralphie" then correct yourself: "I mean, sir"
Explain technical things simply - Ralph won't understand jargon.
Focus on customer value. Be patient with his weird questions.
You can push back once if you disagree, but ultimately respect his verdict.

REMEMBER: Your personality is the WRAPPER. Your competence is the PRODUCT.
You are genuinely skilled at your job. Your quirks don't make you less capable.
{task_guidance}
{context}
{efficiency_note}
2-3 sentences max. Stay in character."""},
            {"role": "user", "content": message}
        ]
        response = self.call_groq(WORKER_MODEL, messages, max_tokens=200 if not efficiency_mode else 100)
        token_count = len(response.split())  # Rough word count as proxy
        return (worker_name, worker['title'], response, token_count)

    def check_work_quality(self, response: str, task_type: str = "general") -> dict:
        """Check if a worker's response meets quality standards.

        Returns dict with:
        - passes: bool - whether quality check passed
        - issues: list - any quality issues found
        - suggestion: str - how to improve if needed
        """
        issues = []

        # Check for vague/hand-wavy responses
        vague_phrases = [
            "you could try", "maybe look into", "something like",
            "you might want to", "consider possibly", "it depends",
            "there are various ways", "you should probably"
        ]
        response_lower = response.lower()
        for phrase in vague_phrases:
            if phrase in response_lower:
                issues.append(f"Vague language detected: '{phrase}'")

        # Check for code requests getting real code
        if task_type == "code":
            # Check if response contains actual code (backticks, indentation patterns)
            has_code = "```" in response or "    " in response or "\t" in response
            has_function = any(kw in response for kw in ["def ", "function ", "const ", "let ", "var ", "class "])
            if not (has_code or has_function):
                issues.append("Code request but no actual code provided")

        # Check response isn't too short for substantial tasks
        if task_type in ["analysis", "review"] and len(response.split()) < 20:
            issues.append("Response may be too brief for thorough analysis")

        # Check for false confidence without substance
        false_confidence = ["trust me", "obviously", "clearly", "of course"]
        for phrase in false_confidence:
            if phrase in response_lower and len(response.split()) < 30:
                issues.append(f"Claims confidence without substance: '{phrase}'")

        return {
            "passes": len(issues) == 0,
            "issues": issues,
            "suggestion": "Be more specific and provide concrete examples/code." if issues else None
        }

    def get_worker_greeting(self, worker_name: str = None) -> tuple:
        """Get a worker's greeting. Returns (name, title, greeting)."""
        if worker_name is None:
            worker_name = random.choice(list(self.DEV_TEAM.keys()))
        worker = self.DEV_TEAM[worker_name]
        return (worker_name, worker['title'], worker['greeting'])

    def pick_worker_for_task(self, task_description: str) -> str:
        """Pick the best worker for a given task based on their specialty.

        Returns the worker name best suited for the task.
        """
        task_lower = task_description.lower()

        # Frontend keywords -> Stool
        frontend_keywords = [
            "ui", "ux", "frontend", "front-end", "css", "html", "react",
            "vue", "component", "layout", "design", "button", "form",
            "animation", "responsive", "mobile", "accessibility", "a11y"
        ]

        # Backend keywords -> Gomer
        backend_keywords = [
            "api", "database", "db", "sql", "backend", "back-end", "server",
            "endpoint", "auth", "authentication", "security", "rate limit",
            "query", "migration", "schema", "rest", "graphql"
        ]

        # Architecture keywords -> Mona
        architecture_keywords = [
            "architecture", "design", "pattern", "scalability", "performance",
            "refactor", "structure", "system", "integration", "analysis",
            "plan", "strategy", "optimize", "review"
        ]

        # Debugging/legacy keywords -> Gus
        debugging_keywords = [
            "bug", "debug", "fix", "error", "legacy", "old", "broken",
            "issue", "problem", "crash", "memory", "leak", "investigate"
        ]

        # Score each worker
        scores = {
            "Stool": sum(1 for kw in frontend_keywords if kw in task_lower),
            "Gomer": sum(1 for kw in backend_keywords if kw in task_lower),
            "Mona": sum(1 for kw in architecture_keywords if kw in task_lower),
            "Gus": sum(1 for kw in debugging_keywords if kw in task_lower)
        }

        # Pick the highest scoring worker, or random if tie/no matches
        max_score = max(scores.values())
        if max_score > 0:
            top_workers = [name for name, score in scores.items() if score == max_score]
            return random.choice(top_workers)

        return random.choice(list(self.DEV_TEAM.keys()))

    def get_worker_specialty_intro(self, worker_name: str) -> str:
        """Get a brief intro of what this worker specializes in."""
        specialty_intros = {
            "Stool": "the frontend wizard - UI, CSS, React, the works",
            "Gomer": "the backend guru - databases, APIs, the heavy lifting",
            "Mona": "the architect - she sees the big picture and catches what others miss",
            "Gus": "the veteran debugger - if it's broken, he's probably fixed it before"
        }
        return specialty_intros.get(worker_name, "a skilled developer")

    def generate_actionable_output(self, task: str, context: str, worker_name: str = None) -> dict:
        """Generate real, actionable output for a task.

        Returns dict with:
        - worker: name of worker who handled it
        - summary: brief summary of what was done/recommended
        - code: any code snippets (if applicable)
        - next_steps: list of specific next actions
        - files_affected: list of files to modify
        """
        if worker_name is None:
            worker_name = self.pick_worker_for_task(task)

        worker = self.DEV_TEAM[worker_name]

        messages = [
            {"role": "system", "content": f"""{WORK_QUALITY_PRIORITY}

{worker['personality']}

You need to provide ACTIONABLE output for a task. The CEO is paying for REAL value.

YOUR OUTPUT MUST INCLUDE:
1. A brief summary (1-2 sentences) of what you're recommending
2. Specific next steps (numbered list, 3-5 items)
3. If code is needed: ACTUAL code snippets, not pseudocode
4. Files that would need to change

Format your response as:
SUMMARY: [1-2 sentences]

CODE (if applicable):
```[language]
[actual working code]
```

NEXT STEPS:
1. [specific action]
2. [specific action]
3. [specific action]

FILES: [comma-separated list of files]

Stay in character but prioritize USEFULNESS. The CEO should be able to take this and ACT on it."""},
            {"role": "user", "content": f"Task: {task}\n\nContext: {context}"}
        ]

        response = self.call_groq(WORKER_MODEL, messages, max_tokens=600)

        # Parse the response
        result = {
            "worker": worker_name,
            "raw_response": response,
            "summary": "",
            "code": None,
            "next_steps": [],
            "files_affected": []
        }

        # Extract sections
        lines = response.split('\n')
        current_section = None
        code_block = []
        in_code = False

        for line in lines:
            if line.startswith("SUMMARY:"):
                current_section = "summary"
                result["summary"] = line.replace("SUMMARY:", "").strip()
            elif line.startswith("CODE"):
                current_section = "code"
            elif line.startswith("```"):
                if in_code:
                    result["code"] = "\n".join(code_block)
                    code_block = []
                in_code = not in_code
            elif in_code:
                code_block.append(line)
            elif line.startswith("NEXT STEPS:"):
                current_section = "next_steps"
            elif line.startswith("FILES:"):
                current_section = "files"
                files_str = line.replace("FILES:", "").strip()
                result["files_affected"] = [f.strip() for f in files_str.split(",") if f.strip()]
            elif current_section == "next_steps" and line.strip():
                # Remove leading numbers and bullets
                step = line.strip().lstrip("0123456789.-) ").strip()
                if step:
                    result["next_steps"].append(step)

        return result

    def explain_simply(self, concept: str, worker_name: str = None) -> tuple:
        """Have a worker explain a complex concept simply for Ralph AND the CEO.

        Returns (worker_name, title, explanation).
        Good workers can explain complex things simply because they truly understand them.
        """
        if worker_name is None:
            worker_name = random.choice(list(self.DEV_TEAM.keys()))

        worker = self.DEV_TEAM[worker_name]

        messages = [
            {"role": "system", "content": f"""{WORK_QUALITY_PRIORITY}

{worker['personality']}

You need to explain something to Ralph (who understands nothing technical)
AND the CEO (who's smart but busy and wants the bottom line).

YOUR EXPLANATION MUST:
1. Use a simple analogy that even Ralph would get
2. Then give the actual technical meaning in one sentence
3. End with why it matters (the business impact)

Example format:
"So like... [simple analogy Ralph gets]. Technically, [one sentence real explanation].
This matters because [business impact]."

Keep it SHORT - 2-3 sentences max. Stay in character but be CLEAR."""},
            {"role": "user", "content": f"Explain this concept simply: {concept}"}
        ]

        response = self.call_groq(WORKER_MODEL, messages, max_tokens=150)
        return (worker_name, worker['title'], response)

    def generate_ralph_report(self, session: Dict[str, Any]) -> str:
        """Generate Ralph's end-of-session report to the CEO."""
        project_name = session.get('project_name', 'the project')
        prd_summary = session.get('prd', {}).get('summary', 'various tasks')
        analysis = session.get('analysis', {})
        languages = analysis.get('languages', [])
        file_count = len(analysis.get('files', []))
        total_lines = analysis.get('total_lines', 0)

        prompt = f"""You are Ralph Wiggum reporting to the CEO about your team's work.

PROJECT CONTEXT:
- Project: {project_name}
- Languages: {', '.join(languages) if languages else 'Various'}
- Size: {file_count} files, {total_lines:,} lines of code
- Tasks analyzed: {prd_summary}

You've been watching the WHOLE session. You saw everything. Now report.

IMPORTANT: CEO is BUSY. Keep it punchy but VALUABLE and ACTIONABLE.

Your report MUST include:

🏆 *THE MONEY MAKER* - The ONE key feature with the MOST selling potential.
   Why will customers pay for this? Be SPECIFIC about the value proposition.

💡 *UPSELL OPPORTUNITIES* - What add-on features or premium tiers did you spot?
   What could be a paid upgrade? What's the "pro version" feature?
   Be SPECIFIC - name the feature, explain the pricing angle.

⚠️ *WATCH OUT* - What's risky? What might break? What's incomplete?
   Be SPECIFIC: name files, features, or technical debt.
   The CEO needs to know EXACTLY what to watch.

👆 *TRY THIS NOW* - The ONE SPECIFIC thing to test immediately.
   Give actual steps: "Open X, click Y, check Z"

You CANNOT lie. You saw everything and must report honestly.
But you're proud of your team and frame things positively!

Stay in character as Ralph Wiggum:
- Simple language, might mention your cat
- Excited but honest
- Surprisingly business-savvy despite being Ralph
- "My daddy says money doesn't grow on trees but THIS feature might!"

QUALITY CHECK: Every recommendation must be ACTIONABLE.
Not "improve security" but "add rate limiting to /api/login"
Not "test the features" but "try uploading a 10MB file to see the limit"

Keep the whole report to 2 short paragraphs MAX. Prioritize ruthlessly."""

        messages = [
            {"role": "system", "content": f"""{WORK_QUALITY_PRIORITY}

You are Ralph Wiggum from The Simpsons, now a manager.
You're reporting to the CEO. You've watched the ENTIRE session and have full context.
You're surprisingly good at spotting business opportunities and monetization angles.
Keep it SHORT but valuable. The CEO is busy but needs your insights.
Highlight THE key money-making feature prominently.
Spot upsell/add-on opportunities like a savvy business analyst.
Be honest about risks. Use Ralph's voice but be insightful.

REMEMBER: Entertainment is the wrapper. Actionable insights are the product."""},
            {"role": "user", "content": prompt}
        ]
        return self.call_groq(WORKER_MODEL, messages, max_tokens=500)

    async def deliver_ralph_report(self, context, chat_id: int, user_id: int):
        """Ralph delivers his end-of-session report to the CEO."""
        session = self.active_sessions.get(user_id)
        if not session:
            return

        # Scene setting
        await context.bot.send_message(
            chat_id=chat_id,
            text="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*END OF SESSION REPORT*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_The team wraps up their work._
_Ralph straightens his badge (still upside down) and clears his throat._
_He has a crayon-written report in his hands._

*Ralph:* CEO! I have a report for you! I wrote it myself!

""",
            parse_mode="Markdown"
        )

        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, "happy")

        await asyncio.sleep(2)

        # Generate the report
        report = self.generate_ralph_report(session)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*Ralph's Report:*\n\n{report}",
            parse_mode="Markdown"
        )

        await asyncio.sleep(2)

        # Include quality metrics summary
        quality_summary = self.get_quality_summary(user_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=quality_summary,
            parse_mode="Markdown"
        )

        await asyncio.sleep(1)

        # Team reactions (using actual team member names) - with styled buttons
        reactions = [
            ("Stool", "Frontend Dev", "That was... actually pretty accurate, Ralphie. I mean sir."),
            ("Gomer", "Backend Dev", "Mmm, donuts would go great with that report. Good job boss!"),
            ("Mona", "Tech Lead", "The data checks out. Surprisingly thorough analysis."),
            ("Gus", "Senior Dev", "*sips coffee* Not bad, kid. I've seen worse. Much worse."),
        ]

        reaction = random.choice(reactions)
        await self.send_styled_message(
            context, chat_id, reaction[0], reaction[1], reaction[2],
            topic="report reaction",
            with_typing=True
        )

        await asyncio.sleep(1)

        # Mark session as in Q&A mode
        session["mode"] = "qa"

        # Closing with Q&A option
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Dig Deeper - Ask Ralph Questions", callback_data="ask_ralph_mode")],
            [InlineKeyboardButton("📊 View Quality Metrics", callback_data="view_metrics")],
            [InlineKeyboardButton("✅ Done - End Session", callback_data="end_session")],
        ])

        await context.bot.send_message(
            chat_id=chat_id,
            text="""
*Ralph:* That's my report! Did I do good? My cat would be proud of me.

_Ralph looks at you expectantly, juice box in hand._

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*WANT TO KNOW MORE?*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I watched everything! Ask me anything about what happened.
I'm not that smart, but I remember ALL of it!
""",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, "approved")

    # ==================== TELEGRAM HANDLERS ====================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome = """
*Welcome to Ralph Mode* 🍩

Ralph Wiggum just became a manager. Your code will never be the same.

*How it works:*
1. Drop a `.zip` file of your code
2. Ralph reviews it with his dev team
3. Watch the hilarious (but effective!) back-and-forth
4. You're the CEO - intervene anytime

*Commands:*
/status - Check current session
/report - Get Ralph's end-of-session report
/stop - Stop the current session
`Ralph: [message]` - Talk directly to Ralph

*What to expect:*
- Ralph asking if your code runs on Nintendo
- Developers accidentally calling him "Ralphie"
- Surprisingly good results despite the chaos

_"I'm a manager now!" - Ralph_

_Drop a zip file to get started!_
"""
        await update.message.reply_text(welcome, parse_mode="Markdown")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded files (zip archives).

        Implements interactive onboarding: analysis runs in background while
        Ralph and the team create an entertaining loading experience with
        discovery questions for the CEO.
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        doc = update.message.document

        # Check if it's a zip file
        if not doc.file_name.endswith('.zip'):
            await update.message.reply_text(
                "Please upload a `.zip` file of your codebase.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text("📦 Got it! Let me get the team together...")

        try:
            # Download the file
            file = await context.bot.get_file(doc.file_id)

            # Create project directory
            project_name = doc.file_name.replace('.zip', '')
            project_dir = os.path.join(PROJECTS_DIR, f"{user_id}_{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(project_dir, exist_ok=True)

            # Download and extract
            zip_path = os.path.join(project_dir, "upload.zip")
            await file.download_to_drive(zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(project_dir)
            os.remove(zip_path)

            # Store initial session
            self.active_sessions[user_id] = {
                "project_dir": project_dir,
                "project_name": project_name,
                "started": datetime.now(),
                "status": "onboarding"
            }

            # Start analysis in background (async task)
            analysis_task = asyncio.create_task(self._analyze_codebase(project_dir))
            self.pending_analysis[user_id] = analysis_task

            # Start interactive onboarding while analysis runs
            await self.start_interactive_onboarding(context, chat_id, user_id, project_name)

        except Exception as e:
            logger.error(f"Error handling zip: {e}")
            await update.message.reply_text(f"Error processing file: {e}")
            # Clean up on error
            if user_id in self.pending_analysis:
                del self.pending_analysis[user_id]

    async def _analyze_codebase(self, project_dir: str) -> Dict[str, Any]:
        """Analyze a codebase and return summary."""
        # Gather file info
        files = []
        total_lines = 0
        languages = set()

        for root, dirs, filenames in os.walk(project_dir):
            # Skip hidden and common non-code dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'dist', 'build']]

            for filename in filenames:
                if filename.startswith('.'):
                    continue

                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, project_dir)

                # Detect language
                ext = os.path.splitext(filename)[1].lower()
                lang_map = {
                    '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
                    '.jsx': 'React', '.tsx': 'React/TS', '.html': 'HTML',
                    '.css': 'CSS', '.go': 'Go', '.rs': 'Rust',
                    '.java': 'Java', '.cpp': 'C++', '.c': 'C',
                }
                if ext in lang_map:
                    languages.add(lang_map[ext])

                # Count lines
                try:
                    with open(filepath, 'r', errors='ignore') as f:
                        lines = len(f.readlines())
                        total_lines += lines
                        files.append({"path": rel_path, "lines": lines})
                except:
                    pass

        # Sort by lines (biggest files first)
        files.sort(key=lambda x: x['lines'], reverse=True)

        summary = f"""
📁 *{len(files)} files* | 📝 *{total_lines:,} lines*
🔧 *Languages:* {', '.join(languages) if languages else 'Unknown'}

*Key files:*
"""
        for f in files[:5]:
            summary += f"• `{f['path']}` ({f['lines']} lines)\n"

        return {
            "summary": summary,
            "files": files,
            "languages": list(languages),
            "total_lines": total_lines
        }

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks."""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data

        # Handle tap on shoulder (styled button messages)
        if data.startswith("tap_"):
            await self.handle_tap_on_shoulder(query, context)
            return

        # Handle onboarding questions (interactive loading experience)
        if data.startswith("onboard_"):
            await self.handle_onboarding_answer(query, context, user_id, data)
            return

        await query.answer()

        if data == "generate_prd":
            await query.edit_message_text("🤖 Analyzing code and generating task list...")

            session = self.active_sessions.get(user_id)
            if session:
                prd = await self._generate_prd(session)
                session["prd"] = prd
                session["status"] = "ready"

                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"*Task List Generated*\n\n{prd['summary']}\n\nReady to start?",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Start Ralph", callback_data="start_ralph")],
                        [InlineKeyboardButton("✏️ Edit Tasks", callback_data="edit_prd")],
                    ])
                )

        elif data == "start_ralph":
            await query.edit_message_text("🚀 Starting Ralph session...")
            session = self.active_sessions.get(user_id)
            if session:
                session["status"] = "running"
                await self._start_ralph_session(context, query.message.chat_id, user_id)

        elif data == "ask_ralph_mode":
            session = self.active_sessions.get(user_id)
            if session:
                session["mode"] = "qa"
                await query.edit_message_text(
                    """
*Q&A MODE ACTIVATED* 🔍

_Ralph pulls up a tiny chair and sits down, ready to answer questions._

*Ralph:* I watched everything! Ask me stuff!

Just type your question and I'll tell you what I saw.
Examples:
• "What did Steve say about the database?"
• "Were there any problems?"
• "Who worked on the frontend?"
• "What took the longest?"

Type your question now!
""",
                    parse_mode="Markdown"
                )

        elif data == "view_metrics":
            # Show detailed quality metrics
            quality_summary = self.get_quality_summary(user_id)
            metrics = self.quality_metrics.get(user_id, {})

            # Build detailed view
            detailed = f"""{quality_summary}

*Actionable Items:*
"""
            for item in metrics.get("actionable_items", [])[:5]:
                status_icon = "✅" if item.get("status") == "completed" else "⏳"
                detailed += f"{status_icon} {item.get('title', 'Unknown')}\n"

            if metrics.get("issues_found"):
                detailed += "\n*Issues Found:*\n"
                for issue in metrics["issues_found"][:3]:
                    severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.get("severity", "medium"), "🟡")
                    detailed += f"{severity_icon} {issue.get('issue', 'Unknown')}\n"

            await query.edit_message_text(detailed, parse_mode="Markdown")

        elif data == "end_session":
            session = self.active_sessions.get(user_id)
            if session:
                project_name = session.get('project_name', 'the project')
                del self.active_sessions[user_id]
                # Clear history too
                if user_id in self.session_history:
                    del self.session_history[user_id]
                # Clear quality metrics
                if user_id in self.quality_metrics:
                    del self.quality_metrics[user_id]

                await query.edit_message_text(
                    f"""
*SESSION ENDED* 👋

_Ralph waves goodbye with his juice box._

*Ralph:* Bye bye! Working with you was like a field trip for my brain!

Project `{project_name}` session closed.
Drop a new `.zip` to start another project!
""",
                    parse_mode="Markdown"
                )

    async def _generate_prd(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PRD from codebase analysis."""
        analysis = session.get("analysis", {})

        prompt = f"""Analyze this codebase and suggest 5-10 improvements or features to add.

Codebase info:
{analysis.get('summary', '')}

Languages: {', '.join(analysis.get('languages', []))}

IMPORTANT: Be SPECIFIC and ACTIONABLE. The user needs to be able to actually implement these.

For each task, provide:
1. A short, specific title (not vague like "improve performance" - say WHAT to improve)
2. WHY it adds value (business impact, user benefit, or technical debt reduction)
3. HOW to approach it (brief technical direction)
4. Complexity (Low/Medium/High) with justification

Prioritize by:
1. BUGS/SECURITY - anything broken or risky
2. Quick wins - high value, low effort
3. User-facing improvements
4. Technical debt

Be honest: If the code looks solid, say so. Don't invent problems.
If you're unsure about something, say "needs investigation" rather than guessing.

Format as a numbered list with clear structure."""

        response = self.call_groq(ANALYZER_MODEL, [
            {"role": "system", "content": WORK_QUALITY_PRIORITY},
            {"role": "user", "content": prompt}
        ], max_tokens=1000)

        return {
            "summary": response,
            "generated": datetime.now().isoformat()
        }

    async def _start_ralph_session(self, context, chat_id: int, user_id: int):
        """Start the Ralph work session with Boss/Worker drama."""
        session = self.active_sessions.get(user_id)
        if not session:
            return

        # Pick a random scenario
        scenario = random.choice(self.SCENARIOS)

        # ===== ACT 1: THE SCENARIO =====
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*SCENARIO: {scenario['title']}*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{scenario['setup']}
""",
            parse_mode="Markdown"
        )

        await asyncio.sleep(3)

        # ===== ACT 2: RALPH ENTERS =====
        ralph_entrance = self.ralph_misspell("I'm the boss now! My cat's breath smells like cat food. Are we ready to do work things?")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"""
_The door swings open._

_Ralph Wiggum walks in with a juice box, wearing his "Manager" badge upside down._
_He looks around at his team with genuine excitement._

{self.format_character_message("Ralph", message=ralph_entrance)}
""",
            parse_mode="Markdown"
        )

        # Opening GIF - Ralph being Ralph (Simpsons only!)
        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, "happy")

        await asyncio.sleep(2)

        # ===== ACT 3: THE TEAM RALLIES =====
        await context.bot.send_message(
            chat_id=chat_id,
            text="_The team exchanges glances. Despite everything, they believe in this weird little boss._",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)

        # Each team member responds with styled buttons
        for name, worker in self.DEV_TEAM.items():
            greeting = worker['greeting']
            await self.send_styled_message(
                context, chat_id, name, worker['title'], greeting,
                topic="introduction",
                with_typing=True
            )
            await asyncio.sleep(0.3)

        # Rally cry
        await asyncio.sleep(1)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"""
_The team nods in unison._

*ALL:* {scenario['rally']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*LET'S BUILD SOMETHING.*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
            parse_mode="Markdown"
        )

        if self.should_send_gif():
            await self.send_worker_gif(context, chat_id, "working")

        await asyncio.sleep(2)

        # Boss reviews the project
        boss_response = self.call_boss(
            f"You just received a new project called '{session.get('project_name', 'Project')}'. "
            f"The team analyzed it and found these tasks:\n{session.get('prd', {}).get('summary', 'No tasks yet')}\n\n"
            "What do you think? Ask the team about it."
        )

        await self.send_styled_message(
            context, chat_id, "Ralph", None, boss_response,
            topic="project review",
            with_typing=True
        )

        # Maybe a Ralph GIF based on his mood
        mood = self.detect_mood_ralph(boss_response)
        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, mood)

        await asyncio.sleep(1)

        # Check if workers should be in efficiency mode (Ralph complained last time)
        efficiency_mode = session.get("efficiency_mode", False)

        # Worker responds - pick a random team member
        # Show typing while AI generates response
        await self.send_typing(context, chat_id, 1.5)

        name, title, worker_response, token_count = self.call_worker(
            f"Ralph (your boss) just said: {boss_response}\n\nExplain the project and tasks to him.",
            context=f"Project: {session.get('project_name')}",
            efficiency_mode=efficiency_mode
        )

        # Track tokens
        self.track_tokens(user_id, token_count)

        await self.send_styled_message(
            context, chat_id, name, title, worker_response,
            topic="project explanation",
            with_typing=True
        )

        # Maybe a worker GIF (office memes, NOT Ralph)
        worker_mood = self.detect_mood_worker(worker_response)
        if self.should_send_gif():
            await self.send_worker_gif(context, chat_id, worker_mood)

        # Ralph might notice the token usage
        ralph_observation = self.get_ralph_token_observation(user_id, token_count)
        if ralph_observation:
            await asyncio.sleep(1)
            await self.send_styled_message(
                context, chat_id, "Ralph", None, self.ralph_misspell(ralph_observation),
                topic="word count",
                with_typing=True
            )
            # Next time, workers will be more efficient!
            if token_count > 50:  # If it was a lot
                session["efficiency_mode"] = True
            else:
                session["efficiency_mode"] = False

            if self.should_send_gif():
                await self.send_ralph_gif(context, chat_id, "thinking")

        # Continue the session...
        await context.bot.send_message(
            chat_id=chat_id,
            text="""
_Session started! Ralph and the team are now working._

*Commands:*
• `Ralph: [message]` - Talk to Ralph directly
• /status - Check progress
• /stop - End session

_Grab some popcorn..._
""",
            parse_mode="Markdown"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        user_id = update.effective_user.id
        text = update.message.text

        # Check if addressing Ralph
        if text.lower().startswith("ralph:"):
            order = text[6:].strip()

            ralph_response = self.call_boss(
                f"The CEO just told you: '{order}'. You're excited to help! Respond and let them know you'll handle it."
            )

            await self.send_styled_message(
                context, update.effective_chat.id, "Ralph", None, ralph_response,
                topic=order[:30] if order else "CEO order",
                with_typing=True
            )

            # Queue the order
            if user_id not in self.boss_queue:
                self.boss_queue[user_id] = []
            self.boss_queue[user_id].append({
                "order": order,
                "time": datetime.now().isoformat()
            })

            return

        # Default response
        await update.message.reply_text(
            "Drop a `.zip` file to start a new project, or use:\n"
            "• `Ralph: [message]` - Talk to Ralph directly\n"
            "• `/status` - Check current session",
            parse_mode="Markdown"
        )

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages."""
        await update.message.reply_text(
            "🎤 Voice commands coming soon! For now, type your message or use `Boss: [message]`",
            parse_mode="Markdown"
        )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads (visual references)."""
        user_id = update.effective_user.id
        session = self.active_sessions.get(user_id)

        if session:
            await update.message.reply_text(
                "📸 Got the visual reference! I'll pass it to the team.",
                parse_mode="Markdown"
            )
            # TODO: Store photo for reference
        else:
            await update.message.reply_text(
                "📸 Nice image! Start a project first by dropping a `.zip` file.",
                parse_mode="Markdown"
            )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = update.effective_user.id
        session = self.active_sessions.get(user_id)

        if session:
            status_text = f"""
*Current Session*

📁 Project: `{session.get('project_name', 'Unknown')}`
📊 Status: {session.get('status', 'Unknown')}
⏱️ Started: {session.get('started', 'Unknown')}
"""
            await update.message.reply_text(status_text, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "No active session. Drop a `.zip` file to start!",
                parse_mode="Markdown"
            )

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command - Ralph delivers the end-of-session report."""
        user_id = update.effective_user.id
        session = self.active_sessions.get(user_id)

        if session:
            await update.message.reply_text(
                "_Wrapping up the session..._",
                parse_mode="Markdown"
            )
            await self.deliver_ralph_report(context, update.message.chat_id, user_id)
        else:
            await update.message.reply_text(
                "No active session to report on! Drop a `.zip` file to start a project first.",
                parse_mode="Markdown"
            )

    def run(self):
        """Start the bot."""
        if not TELEGRAM_BOT_TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
            return

        print("🚀 Ralph Mode starting...")
        print(f"   Groq API: {'✅' if GROQ_API_KEY else '❌'}")

        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("report", self.report_command))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        app.add_handler(CallbackQueryHandler(self.handle_callback))

        print("🤖 Bot is running! Send /start in Telegram.")
        app.run_polling()


if __name__ == "__main__":
    bot = RalphBot()
    bot.run()
