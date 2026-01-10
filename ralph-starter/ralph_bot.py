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

# SS-001 & SS-003: Import scene manager for opening scene generation and time-aware scenes
try:
    from scene_manager import generate_opening_scene, get_worker_arrival, get_time_of_day_context
    SCENE_MANAGER_AVAILABLE = True
except ImportError:
    SCENE_MANAGER_AVAILABLE = False
    logging.warning("SS-001: Scene manager not available - using simple opening")

# TL-002 & TL-003: Import translation engine for character translation and scene output
try:
    from translation_engine import (
        translate_to_scene,
        format_scene_output,
        add_scene_atmosphere,
        get_translation_engine
    )
    TRANSLATION_ENGINE_AVAILABLE = True
except ImportError:
    TRANSLATION_ENGINE_AVAILABLE = False
    logging.warning("TL-002/TL-003: Translation engine not available - theatrical formatting disabled")

# BC-001: Import sanitizer for broadcast-safe output
try:
    from sanitizer import sanitize_for_groq, sanitize_for_telegram, get_sanitizer
    SANITIZER_AVAILABLE = True
except ImportError:
    SANITIZER_AVAILABLE = False
    def sanitize_for_groq(text): return text
    def sanitize_for_telegram(text): return text
    def get_sanitizer(): return None

# SEC-029: Import LLM security for prompt injection prevention
try:
    from llm_security import (
        validate_llm_input,
        validate_llm_output,
        check_rate_limit,
        record_api_call,
        get_fallback_response,
        get_security_stats
    )
    LLM_SECURITY_AVAILABLE = True
except ImportError:
    LLM_SECURITY_AVAILABLE = False
    def validate_llm_input(text, context="unknown"): return (True, None, [])
    def validate_llm_output(text): return (text, [])
    def check_rate_limit(): return (True, None)
    def record_api_call(model, input_tokens=0, output_tokens=0): pass
    def get_fallback_response(context="general"): return "Service unavailable"
    def get_security_stats(): return {}
    logging.warning("SEC-029: LLM security module not available - protection disabled")

# SEC-019: Import GDPR compliance handlers
try:
    from user_data_controller import register_gdpr_handlers
    GDPR_AVAILABLE = True
except ImportError:
    GDPR_AVAILABLE = False
    logging.warning("SEC-019: GDPR module not available - compliance features disabled")

# FB-001: Import feedback collector
try:
    from feedback_collector import get_feedback_collector
    FEEDBACK_COLLECTOR_AVAILABLE = True
except ImportError:
    FEEDBACK_COLLECTOR_AVAILABLE = False
    logging.warning("FB-001: Feedback collector not available - feedback features disabled")

# NT-001: Import feedback scorer for quality/priority notification
try:
    from feedback_scorer import get_feedback_scorer, get_priority_tier, get_priority_tier_emoji
    FEEDBACK_SCORER_AVAILABLE = True
except ImportError:
    FEEDBACK_SCORER_AVAILABLE = False
    logging.warning("NT-001: Feedback scorer not available - feedback notifications will be limited")

# SF-003: Import admin handler for override controls
try:
    from admin_handler import setup_admin_handlers
    ADMIN_HANDLER_AVAILABLE = True
except ImportError:
    ADMIN_HANDLER_AVAILABLE = False
    logging.warning("SF-003: Admin handler not available - admin commands disabled")

# FB-002: Import subscription manager
try:
    from subscription_manager import get_subscription_manager
    SUBSCRIPTION_MANAGER_AVAILABLE = True
except ImportError:
    SUBSCRIPTION_MANAGER_AVAILABLE = False
    logging.warning("FB-002: Subscription manager not available - subscription features disabled")

# QS-003 & FQ-003: Import database for /mystatus command
try:
    from database import get_db, User, Feedback
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logging.warning("Database not available - /mystatus command will be disabled")

# SEC-020: Import PII masking for safe logging
try:
    from pii_handler import PIIMasker, mask_for_logs, PIIField
    PII_MASKING_AVAILABLE = True
except ImportError:
    PII_MASKING_AVAILABLE = False
    def mask_for_logs(value, field_name=None): return str(value)
    logging.warning("SEC-020: PII masking not available - logs may contain unmasked PII")

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


class ComedicTiming:
    """Timing system for creating natural, comedic conversation flow.

    Comedic timing is EVERYTHING. This class provides presets for:
    - Rapid banter (quick exchanges)
    - Dramatic pauses (build anticipation)
    - Interruptions (someone cuts in)
    - Natural conversation flow
    """

    # Timing presets in seconds
    RAPID_BANTER = (0.3, 0.7)       # Quick back and forth
    NORMAL_RESPONSE = (0.8, 1.5)   # Standard reply timing
    DRAMATIC_PAUSE = (2.0, 3.0)    # Build anticipation
    INTERRUPTION = (0.1, 0.3)      # Cut someone off
    PUNCHLINE_SETUP = (1.0, 1.5)   # Before the joke lands
    REALIZATION = (1.5, 2.5)       # "Wait a minute..."
    AWKWARD_SILENCE = (2.5, 4.0)   # When something goes wrong

    @staticmethod
    def rapid_banter() -> float:
        """Quick back-and-forth timing for banter exchanges.

        Use for: worker jokes, Ralph's quick responses, playful exchanges.

        Returns:
            Random delay between 0.3-0.7 seconds
        """
        return random.uniform(*ComedicTiming.RAPID_BANTER)

    @staticmethod
    def normal() -> float:
        """Standard response timing for regular conversation.

        Use for: explanations, task discussions, general dialogue.

        Returns:
            Random delay between 0.8-1.5 seconds
        """
        return random.uniform(*ComedicTiming.NORMAL_RESPONSE)

    @staticmethod
    def dramatic_pause() -> float:
        """Dramatic pause to build anticipation before important reveal.

        Use for: before bad news, before punchlines, big announcements.

        Returns:
            Random delay between 2.0-3.0 seconds
        """
        return random.uniform(*ComedicTiming.DRAMATIC_PAUSE)

    @staticmethod
    def interruption() -> float:
        """Very quick timing for when someone cuts in mid-sentence.

        Use for: "Wait!" moments, Ralph noticing something, urgent interrupts.

        Returns:
            Random delay between 0.1-0.3 seconds
        """
        return random.uniform(*ComedicTiming.INTERRUPTION)

    @staticmethod
    def punchline_setup() -> float:
        """Pause before a joke lands for better comedic effect.

        Use for: before punchline delivery, before Ralph says something absurd.

        Returns:
            Random delay between 1.0-1.5 seconds
        """
        return random.uniform(*ComedicTiming.PUNCHLINE_SETUP)

    @staticmethod
    def realization() -> float:
        """Pause for "Wait a minute..." moments of dawning understanding.

        Use for: when someone realizes something, aha moments.

        Returns:
            Random delay between 1.5-2.5 seconds
        """
        return random.uniform(*ComedicTiming.REALIZATION)

    @staticmethod
    def awkward_silence() -> float:
        """Long awkward pause for when things go wrong.

        Use for: after mistakes, awkward revelations, uncomfortable moments.

        Returns:
            Random delay between 2.5-4.0 seconds
        """
        return random.uniform(*ComedicTiming.AWKWARD_SILENCE)

    @staticmethod
    def for_message_length(text: str) -> float:
        """Calculate appropriate typing/pause time based on message length.

        Longer messages = longer typing time (more realistic).

        Args:
            text: The message that will be sent

        Returns:
            Appropriate delay in seconds
        """
        length = len(text) if text else 0
        if length < 30:
            return random.uniform(0.3, 0.6)
        elif length < 80:
            return random.uniform(0.6, 1.2)
        elif length < 150:
            return random.uniform(1.0, 1.8)
        else:
            return random.uniform(1.5, 2.5)


class RalphBot:
    """The Ralph Mode Telegram Bot."""

    # Reference to ComedicTiming for easy access
    timing = ComedicTiming

    def __init__(self):
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.boss_queue: Dict[int, list] = {}  # Queued messages for boss
        self.gif_chance = 0.3  # 30% chance to send a GIF after messages
        self.token_history: Dict[int, List[int]] = {}  # Track tokens per user
        self.session_history: Dict[int, List[Dict]] = {}  # Full conversation history for Q&A
        self.last_ralph_moment: Dict[int, datetime] = {}  # Track when last Ralph moment happened
        self.ralph_moment_interval = 1200  # Seconds between Ralph moments (20 min = ~3 per hour)
        self.last_bonus_banter: Dict[int, datetime] = {}  # RM-005: Track when last bonus banter happened
        self.last_deleted_message: Dict[int, datetime] = {}  # RM-006: Track when last deleted message happened
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
                # BC-002: Sanitize before sending
                full_text = self._sanitize_output(full_text)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=full_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )

                # RM-005: Bonus Banter Easter Egg (10-15% chance)
                # Only trigger for worker messages (not Ralph), and not too frequently
                if name != "Ralph" and name in self.DEV_TEAM:
                    # Get user_id from chat_id (for tracking purposes)
                    user_id = chat_id  # In DM, chat_id == user_id

                    # Check if enough time has passed since last bonus banter (at least 5 minutes)
                    now = datetime.now()
                    last_banter = self.last_bonus_banter.get(user_id)
                    time_since_last = (now - last_banter).total_seconds() if last_banter else 9999

                    # 12% chance (middle of 10-15% range) and at least 5 minutes since last one
                    if random.random() < 0.12 and time_since_last > 300:
                        self.last_bonus_banter[user_id] = now
                        # Trigger bonus banter in background (don't block current message)
                        asyncio.create_task(self.bonus_banter_moment(context, chat_id))

                # RM-006: Deleted Message Simulation Easter Egg (5-10% chance)
                # Worker types something then "deletes" it - Ralph might notice
                if name != "Ralph" and name in self.DEV_TEAM:
                    user_id = chat_id  # In DM, chat_id == user_id

                    # Check if enough time has passed since last deleted message (at least 8 minutes)
                    now = datetime.now()
                    last_deleted = self.last_deleted_message.get(user_id)
                    time_since_last = (now - last_deleted).total_seconds() if last_deleted else 9999

                    # 7.5% chance (middle of 5-10% range) and at least 8 minutes since last one
                    if random.random() < 0.075 and time_since_last > 480:
                        self.last_deleted_message[user_id] = now
                        # Trigger deleted message in background (don't block current message)
                        asyncio.create_task(self.deleted_message_moment(context, chat_id, name))

                return True
            except Exception as e:
                logger.warning(f"Button styling failed, falling back to text: {e}")

        # Fallback to plain text formatting
        try:
            full_text = self.format_character_message(name, title, message)
            # BC-002: Sanitize before sending
            full_text = self._sanitize_output(full_text)
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
                fallback_text = f"{name}: {message}"
                # BC-002: Sanitize before sending
                fallback_text = self._sanitize_output(fallback_text)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=fallback_text
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
        # SS-001: Generate opening scene
        scene = None
        worker_order = None
        if SCENE_MANAGER_AVAILABLE:
            scene = generate_opening_scene(project_name)
            worker_order = scene["worker_order"]

        # Initialize onboarding state
        self.onboarding_state[user_id] = {
            "stage": "arriving",
            "workers_arrived": [],
            "question_index": 0,
            "answers": {},
            "project_name": project_name,
            "started": datetime.now(),
            "scene": scene,  # SS-001: Store scene for worker arrivals
        }

        # Stage 1: Office opens with generated scene
        if scene:
            # SS-001: Use atmospheric scene generation
            await context.bot.send_message(
                chat_id=chat_id,
                text=scene["full_text"],
                parse_mode="Markdown"
            )
        else:
            # Fallback if scene manager not available
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
        scene = state.get("scene")

        # SS-001: Use scene's worker order if available
        if scene and "worker_order" in scene:
            worker_order = scene["worker_order"]
            # Don't include Ralph in the worker arrivals (he comes later)
            worker_order = [w for w in worker_order if w != "Ralph"]
        else:
            # Fallback: random order
            worker_order = list(self.DEV_TEAM.keys())
            random.shuffle(worker_order)

        # Only 2-3 workers arrive during onboarding (others "were already here")
        arriving_workers = worker_order[:random.randint(2, 3)]

        for name in arriving_workers:
            worker = self.DEV_TEAM[name]

            # SS-001: Use scene manager arrivals if available
            if SCENE_MANAGER_AVAILABLE and scene:
                action = get_worker_arrival(name)
                # Action narration
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"_{action}_",
                    parse_mode="Markdown"
                )
            else:
                # Fallback to old format
                arrivals = self.WORKER_ARRIVALS.get(name, [("_Worker arrives_", "Morning.")])
                action, greeting_text = random.choice(arrivals)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=action,
                    parse_mode="Markdown"
                )

            await asyncio.sleep(random.uniform(0.5, 1.0))

            # Worker greeting with styled button
            greeting = worker.get('greeting', 'Morning.')
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

    async def handle_priority_selection(self, query, context, user_id: int, data: str):
        """Handle CEO order priority button selection.

        When CEO sends 'Ralph: [order]', Ralph asks about priority with buttons.
        This handles the button click and stores the priority.

        Args:
            query: Callback query
            context: Telegram context
            user_id: User's ID
            data: Callback data (e.g., "priority_first_order_123_4567")
        """
        chat_id = query.message.chat_id

        # Parse the callback data: priority_LEVEL_ORDER_ID
        parts = data.split("_", 2)  # ['priority', 'first/normal/low', 'order_id']
        if len(parts) < 3:
            await query.answer("Something went wrong!")
            return

        priority_level = parts[1]
        order_id = parts[2]

        # Find the order in boss_queue
        order_text = None
        if user_id in self.boss_queue:
            for order in self.boss_queue[user_id]:
                if order.get("order_id") == order_id:
                    order["priority"] = priority_level
                    order_text = order.get("order")
                    break

        await query.answer()

        # Remove buttons
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except:
            pass

        # Ralph reacts based on priority level
        if priority_level == "first":
            ralph_reaction = self.ralph_misspell(
                "FIRST PRIORITY! Got it! I'll tell the team to drop EVERYTHING! "
                "This is like when my cat sees a bird - total focus!"
            )
            # Move to front of queue
            if user_id in self.boss_queue and order_text:
                # Find and move to front
                for i, order in enumerate(self.boss_queue[user_id]):
                    if order.get("order_id") == order_id:
                        high_priority_order = self.boss_queue[user_id].pop(i)
                        self.boss_queue[user_id].insert(0, high_priority_order)
                        break

        elif priority_level == "normal":
            ralph_reaction = self.ralph_misspell(
                "Added to the list! We'll get to it in order. "
                "Like waiting in line for paste at school!"
            )

        else:  # low priority - just a thought
            ralph_reaction = self.ralph_misspell(
                "Okie dokie! I'll keep it in my brain pocket for later. "
                "Sometimes my best ideas come from brain pockets!"
            )

        await self.send_styled_message(
            context, chat_id, "Ralph", None, ralph_reaction,
            topic="priority set",
            with_typing=True
        )

        # If there's an active session, inform about the task
        session = self.active_sessions.get(user_id)
        if session and order_text:
            # Optionally let a worker acknowledge
            if random.random() < 0.5:  # 50% chance
                worker = random.choice(list(self.DEV_TEAM.keys()))
                worker_data = self.DEV_TEAM[worker]
                acknowledgments = {
                    "first": ["On it, boss!", "Dropping everything!", "Top priority, got it!"],
                    "normal": ["Added to the backlog!", "We'll get there!", "Noted!"],
                    "low": ["Keeping it in mind.", "Food for thought!", "Interesting idea..."],
                }
                ack = random.choice(acknowledgments.get(priority_level, ["Got it!"]))
                await asyncio.sleep(self.timing.rapid_banter())
                await self.send_styled_message(
                    context, chat_id, worker, worker_data['title'], ack,
                    topic="task acknowledgment",
                    with_typing=True
                )

    async def handle_feedback_type_selection(self, query, context, user_id: int, data: str):
        """FB-003: Handle feedback type selection and collect type-specific fields.

        Args:
            query: Callback query
            context: Telegram context
            user_id: User's ID
            data: Callback data (e.g., "feedback_type_bug_report")
        """
        chat_id = query.message.chat_id
        telegram_id = query.from_user.id

        # Parse feedback type from callback data
        feedback_type = data.replace("feedback_type_", "")

        await query.answer()

        # Store the feedback type in user_data for later use
        context.user_data['feedback_type'] = feedback_type
        context.user_data['feedback_state'] = 'awaiting_content'

        # Remove the type selection buttons
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except:
            pass

        # FB-003: Show type-specific prompts
        prompts = {
            "bug_report": self.ralph_misspell(
                "Ooh a bug! Those are tricky! Tell me:\n\n"
                "1️⃣ What did you try to do?\n"
                "2️⃣ What happened instead?\n"
                "3️⃣ What should have happened?\n\n"
                "Just type it all out and I'll make sure the team knows! "
                "You can also send a screenshot if that helps!"
            ),
            "feature_request": self.ralph_misspell(
                "A new feture! I love new fetures! Tell me:\n\n"
                "1️⃣ What do you want to be able to do?\n"
                "2️⃣ Why would this be helpful?\n\n"
                "Type your idea and I'll tell the team! My cat's breath smells like cat food!"
            ),
            "enhancement": self.ralph_misspell(
                "Making something better! That's so smart! Tell me:\n\n"
                "1️⃣ What exists now?\n"
                "2️⃣ How should it be better?\n\n"
                "Just type it out! I'm learnding!"
            ),
            "ux_issue": self.ralph_misspell(
                "UX means 'User Xperience' I think! Tell me:\n\n"
                "1️⃣ What part of the app is confusing or hard to use?\n"
                "2️⃣ What would make it easier?\n\n"
                "Type your thoughts and I'll pass them along! I bent my wookie!"
            ),
            "performance": self.ralph_misspell(
                "Performance means making things fast! I like fast! Tell me:\n\n"
                "1️⃣ What is slow?\n"
                "2️⃣ When does it happen?\n\n"
                "Type the details! My nose makes its own sauce!"
            ),
            "other": self.ralph_misspell(
                "Other feedbak! That's okay! Sometimes the best ideas don't fit in boxes! "
                "Just tell me what you're thinking and I'll make sure the team hears it!\n\n"
                "Type away!"
            )
        }

        prompt_text = prompts.get(feedback_type, prompts["other"])

        await self.send_styled_message(
            context, chat_id, "Ralph", None, prompt_text,
            topic=f"feedback {feedback_type} prompt",
            with_typing=True
        )

        # Maybe send a GIF to keep things fun
        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, "thinking")

    async def handle_satisfaction_feedback(self, query, context, user_id: int, data: str):
        """
        AN-001: Handle user satisfaction feedback (thumbs up/down).

        Args:
            query: Callback query
            context: Telegram context
            user_id: User's ID
            data: Callback data (e.g., "sat_up_123" or "sat_down_123")
        """
        from database import get_db, User, Feedback, UserSatisfaction

        await query.answer()

        # Parse the callback data: "sat_up_123" or "sat_down_123"
        parts = data.split("_")
        if len(parts) != 3:
            logger.error(f"AN-001: Invalid satisfaction callback data: {data}")
            return

        satisfaction_type = parts[1]  # "up" or "down"
        feedback_id = int(parts[2])
        satisfied = (satisfaction_type == "up")

        try:
            with get_db() as db:
                # Get the user from database
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if not user:
                    await query.edit_message_text("Error: User not found in database.")
                    return

                # Check if feedback exists
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
                if not feedback:
                    await query.edit_message_text("Error: Feedback not found.")
                    return

                # Check if user already rated this feedback
                existing = db.query(UserSatisfaction).filter(
                    UserSatisfaction.user_id == user.id,
                    UserSatisfaction.feedback_id == feedback_id
                ).first()

                if existing:
                    # Update existing rating
                    existing.satisfied = satisfied
                    existing.created_at = datetime.utcnow()
                    logger.info(f"AN-001: Updated satisfaction for feedback {feedback_id} by user {user_id}: {satisfied}")
                else:
                    # Create new satisfaction entry
                    satisfaction_entry = UserSatisfaction(
                        user_id=user.id,
                        feedback_id=feedback_id,
                        satisfied=satisfied
                    )
                    db.add(satisfaction_entry)
                    logger.info(f"AN-001: Recorded satisfaction for feedback {feedback_id} by user {user_id}: {satisfied}")

                db.commit()

            # Generate Ralph's response based on satisfaction
            if satisfied:
                responses = [
                    "🎉 Yay! I'm so happy you like it Mr. Worms!\n\nMe and my team did our bestest!",
                    "👍 That makes me feel all warm and fuzzy inside!\n\nI'm gonna tell the team you're happy!",
                    "🌟 Oh boy! You're pleased! That's the best feeling!\n\nWe worked real hard on this one!",
                    "💪 Yes! We did good!\n\nI'll make sure to tell everyone you said nice things!",
                    "🏆 This is going on the fridge at home!\n\nThanks for the encouragement Mr. Worms!"
                ]
            else:
                responses = [
                    "😔 Oh no... I thought we did good on this one.\n\nWanna tell me what needs work? Just send a message!",
                    "🤔 Dang it... okay, we can make it better!\n\nWhat would help? Send me your thoughts!",
                    "😓 Sorry Mr. Worms... my team tried real hard.\n\nLet us know what to fix and we'll get right on it!",
                    "😞 That's disappointing... but I appreciate your honesty!\n\nTell me what's wrong and we'll do better!",
                    "😕 Aw man... well, nobody's perfect I guess.\n\nSend feedback on what needs improving and we'll handle it!"
                ]

            import random
            response = self.ralph_misspell(random.choice(responses))

            # Update the message to remove buttons and show response
            original_text = query.message.text or query.message.caption
            updated_text = f"{original_text}\n\n{response}"

            try:
                await query.edit_message_text(
                    text=updated_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
            except Exception as e:
                logger.error(f"AN-001: Failed to edit message: {e}")
                # Fallback: send as new message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=response,
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"AN-001: Error handling satisfaction feedback: {e}", exc_info=True)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Oops! Something went wrong recording your feedback. Sorry about that!"
            )

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

    # ==================== COMEDIC TIMING HELPERS ====================

    async def rapid_banter_send(self, context, chat_id: int, name: str, title: str, message: str, topic: str = None):
        """Send a message with rapid banter timing for quick exchanges.

        Use for: joke responses, playful back-and-forth, quick reactions.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            name: Character name
            title: Character title
            message: Message content
            topic: Optional topic for tap responses
        """
        await self.send_typing(context, chat_id, self.timing.rapid_banter())
        await self.send_styled_message(
            context, chat_id, name, title, message,
            topic=topic, with_typing=False
        )

    async def dramatic_reveal(self, context, chat_id: int, name: str, title: str, message: str, topic: str = None):
        """Send a message after a dramatic pause for impact.

        Use for: bad news, big announcements, important revelations.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            name: Character name
            title: Character title
            message: Message content
            topic: Optional topic for tap responses
        """
        await self.send_typing(context, chat_id, self.timing.dramatic_pause())
        await self.send_styled_message(
            context, chat_id, name, title, message,
            topic=topic, with_typing=False
        )

    async def interruption_send(self, context, chat_id: int, name: str, title: str, message: str, topic: str = None):
        """Send a message as an interruption - very quick, cuts in.

        Use for: "Wait!" moments, urgent news, Ralph noticing something.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            name: Character name
            title: Character title
            message: Message content
            topic: Optional topic for tap responses
        """
        await asyncio.sleep(self.timing.interruption())
        await self.send_styled_message(
            context, chat_id, name, title, message,
            topic=topic, with_typing=False
        )

    async def punchline_delivery(self, context, chat_id: int, name: str, title: str, setup: str, punchline: str, topic: str = None):
        """Deliver a joke with proper comedic timing (setup, pause, punchline).

        Args:
            context: Telegram context
            chat_id: Chat to send to
            name: Character name
            title: Character title
            setup: The setup line
            punchline: The punchline
            topic: Optional topic for tap responses
        """
        # Setup
        await self.send_styled_message(
            context, chat_id, name, title, setup,
            topic=topic, with_typing=True
        )

        # Pause for effect
        await asyncio.sleep(self.timing.punchline_setup())

        # Punchline
        await self.send_styled_message(
            context, chat_id, name, title, punchline,
            topic=topic, with_typing=False
        )

    async def awkward_moment(self, context, chat_id: int, action_text: str):
        """Create an awkward silence moment (action + long pause).

        Use for: after mistakes, uncomfortable revelations.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            action_text: Action description (e.g., "Everyone stares at Ralph")
        """
        await context.bot.send_message(
            chat_id=chat_id,
            text=self.format_action(action_text),
            parse_mode="Markdown"
        )
        await asyncio.sleep(self.timing.awkward_silence())

    async def rapid_exchange(self, context, chat_id: int, exchanges: list):
        """Execute a rapid back-and-forth conversation sequence.

        Perfect for banter between workers or workers and Ralph.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            exchanges: List of tuples: (name, title, message)

        Example:
            await bot.rapid_exchange(context, chat_id, [
                ("Stool", "Frontend Dev", "Did you see that?"),
                ("Gomer", "Backend Dev", "See what?"),
                ("Stool", "Frontend Dev", "The bug! It moved!"),
            ])
        """
        for name, title, message in exchanges:
            await self.rapid_banter_send(context, chat_id, name, title, message)

    async def shh_moment(self, context, chat_id: int, whisperer: str, listener: str, secret: str, caught_by: str = "Ralph"):
        """Create a 'caught gossiping' moment.

        Workers whisper something, get caught, quickly change subject.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            whisperer: Worker who starts the whisper
            listener: Worker who responds
            secret: The secret message
            caught_by: Who catches them (default: Ralph)
        """
        whisperer_data = self.DEV_TEAM.get(whisperer, {"title": ""})
        listener_data = self.DEV_TEAM.get(listener, {"title": ""})

        # Whispered message
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"_{whisperer} whispers to {listener}: '{secret}'_",
            parse_mode="Markdown"
        )
        await asyncio.sleep(self.timing.rapid_banter())

        # Someone notices
        await self.interruption_send(
            context, chat_id, listener, listener_data.get('title'),
            f"Shh! {caught_by}!"
        )
        await asyncio.sleep(self.timing.interruption())

        # The caught reaction
        if caught_by == "Ralph":
            ralph_response = self.ralph_misspell(random.choice([
                "What are you whispering about? Is it about me?",
                "I heard my name! Are you talking about paste?",
                "Secrets? I like secrets! Tell me!",
            ]))
            await self.rapid_banter_send(
                context, chat_id, "Ralph", None, ralph_response
            )

        # Quick cover-up
        await asyncio.sleep(self.timing.rapid_banter())
        await self.rapid_banter_send(
            context, chat_id, whisperer, whisperer_data.get('title'),
            random.choice([
                "Nothing, boss! Just talking about... uh... work stuff!",
                "We were discussing the, uh, project!",
                "Nothing important! Back to work!",
            ])
        )

    async def bonus_banter_moment(self, context, chat_id: int):
        """Easter egg: Workers whisper about bonuses, Ralph overhears, they change subject.

        RM-005: Employee Bonus Banter
        Triggered randomly (10-15% chance) during active sessions.
        Creates a fun caught-in-the-act moment with comedic timing.
        """
        # Pick two random workers
        workers = random.sample(list(self.DEV_TEAM.keys()), 2)
        whisperer = workers[0]
        listener = workers[1]

        whisperer_data = self.DEV_TEAM[whisperer]
        listener_data = self.DEV_TEAM[listener]

        # Worker 1 whispers about bonuses
        bonus_whispers = [
            "...so the bonuses this quarter...",
            "Do you think we'll get bonuses for this one?",
            "I heard the bonuses might be better this year...",
            "...if we finish early, maybe a bonus...",
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"_{whisperer} whispers to {listener}: '{random.choice(bonus_whispers)}'_",
            parse_mode="Markdown"
        )
        await asyncio.sleep(self.timing.rapid_banter())

        # Worker 2 notices Ralph and alerts
        await self.interruption_send(
            context, chat_id, listener, listener_data.get('title'),
            "Shh! The boss!"
        )
        await asyncio.sleep(self.timing.interruption())

        # Ralph overhears and reacts
        ralph_responses = [
            "Bonuses? What bonuses?",
            "Did someone say bonuses? I love bonuses!",
            "Bonuses?! I didn't approve any bonuses!",
            "Wait, are we giving out bonuses? Nobody told me!",
        ]
        await self.rapid_banter_send(
            context, chat_id, "Ralph", None,
            self.ralph_misspell(random.choice(ralph_responses))
        )
        await asyncio.sleep(self.timing.rapid_banter())

        # Workers quickly change subject
        cover_ups = [
            "Nothing sir! Back to work!",
            "We were just... talking about the codebase! Yeah, the codebase!",
            "Nothing, boss! Just discussing project milestones!",
            "Uh, we said 'components', not 'bonuses'! Easy to confuse!",
        ]
        await self.rapid_banter_send(
            context, chat_id, whisperer, whisperer_data.get('title'),
            random.choice(cover_ups)
        )

    async def deleted_message_moment(self, context, chat_id: int, worker_name: str):
        """Easter egg: Worker types message then 'deletes' it. Ralph might notice.

        RM-006: Deleted Message Simulation
        Triggered randomly (5-10% chance) during active sessions.
        Creates illusion of catching a worker trying to hide something.
        """
        worker_data = self.DEV_TEAM[worker_name]

        # Embarrassing or gossipy things workers might type then delete
        deleted_messages = [
            "I still don't understand what a closure i--",
            "Why is Ralph always eating glue tho--",
            "Honestly this code is kinda mes--",
            "Does anyone else think this feature is point--",
            "My cat just walked across the keybo--",
            "Wait, are we supposed to be testing thi--",
            "I might have broken something in produ--",
            "Is it just me or does this seem overenginee--",
            "I need coffee so bad right no--",
            "Ralph's code is... actually not ba-- wait",
            "This would be easier if we just use--",
            "I'm not sure I understand what the CEO wan--",
        ]

        # Show the message being typed
        message_text = random.choice(deleted_messages)
        full_text = self.format_character_message(worker_name, worker_data['title'], message_text)

        # Send original message
        sent_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=full_text,
            parse_mode="Markdown"
        )

        # Short pause - just enough to read it
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # 50/50 chance: strikethrough OR [deleted]
        if random.random() < 0.5:
            # Use strikethrough
            deleted_text = self.format_character_message(
                worker_name,
                worker_data['title'],
                f"~{message_text}~"
            )
        else:
            # Use [deleted]
            deleted_text = self.format_character_message(
                worker_name,
                worker_data['title'],
                "_[message deleted]_"
            )

        # Edit the message to show it's deleted
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=sent_msg.message_id,
                text=deleted_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not edit message for deletion effect: {e}")
            # Fallback: send new message
            await context.bot.send_message(
                chat_id=chat_id,
                text=deleted_text,
                parse_mode="Markdown"
            )

        # 40% chance Ralph notices and reacts
        if random.random() < 0.4:
            await asyncio.sleep(self.timing.interruption())

            ralph_reactions = [
                "What did that say?",
                "Hey, I saw that!",
                "What'd you just delete?",
                "I seen that message!",
                "You can't un-type that!",
                "My eyes work, you know!",
                "What were you gonna say?",
            ]

            await self.rapid_banter_send(
                context, chat_id, "Ralph", None,
                self.ralph_misspell(random.choice(ralph_reactions))
            )
            await asyncio.sleep(self.timing.rapid_banter())

            # Worker plays innocent
            worker_responses = [
                "Nothing sir!",
                "Just a typo, boss!",
                "Finger slipped!",
                "Autocorrect, you know how it is!",
                "Technical difficulties!",
                "Nothing important!",
                "I didn't say anything!",
                "Must've been a glitch!",
            ]

            await self.rapid_banter_send(
                context, chat_id, worker_name, worker_data.get('title'),
                random.choice(worker_responses)
            )

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

    def _sanitize_output(self, text: str) -> str:
        """BC-002: Sanitize text before sending to Telegram.

        This is a belt-and-suspenders approach - catches anything that
        slipped through earlier sanitization layers.

        Args:
            text: The text to sanitize

        Returns:
            Sanitized text safe for Telegram display
        """
        if not text:
            return text

        if SANITIZER_AVAILABLE:
            try:
                sanitized = sanitize_for_telegram(text)
                return sanitized
            except Exception as e:
                logger.error(f"BC-002: Sanitization failed: {e}")
                # If sanitization fails, better to block than leak
                return "[Message sanitization error - content hidden for safety]"

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

        BC-002: All messages are sanitized before sending to Telegram.

        Args:
            context: Telegram context
            chat_id: Chat to send to
            text: Message text (may contain markdown)
            parse_mode: Parsing mode, defaults to Markdown
            reply_markup: Optional keyboard markup

        Returns:
            True if sent with formatting, False if fell back to plain text
        """
        # BC-002: Belt-and-suspenders - sanitize before sending to Telegram
        text = self._sanitize_output(text)

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
            "last_progress_report_task": 0,  # Task count when last report was given
            "last_reported_milestone": 0,  # Last milestone reported (25, 50, 75)
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

        Includes:
        - Quick completion message
        - Occasional Ralph comments (~30%)
        - Occasional worker high-fives (~20%)
        - Big celebration for final task
        - Progress bar after delay
        - Mid-session reports at milestones

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

        # Check if this is the final task
        is_final_task = tasks_done >= tasks_total and tasks_total > 0

        if is_final_task:
            # BIG celebration for final task!
            await self._final_task_celebration(context, chat_id, user_id, task_title)
            return

        # Quick completion message
        completion_msg = f"✅ Task {tasks_done}/{tasks_total} done!"
        if task_title:
            completion_msg = f"✅ *{task_title}* complete! ({tasks_done}/{tasks_total})"

        await context.bot.send_message(
            chat_id=chat_id,
            text=completion_msg,
            parse_mode="Markdown"
        )

        # Ralph occasionally comments (~30% chance)
        if random.random() < 0.3:
            ralph_comments = [
                "We did a thing!",
                "Another one! We're like a machine!",
                "My tummy feels accomplished!",
                "That was fun! More more more!",
                "Yay! My cat would be proud!",
                "I helped! Probably!",
                "Check us out, Mr. Worms!",
            ]
            ralph_comment = self.ralph_misspell(random.choice(ralph_comments))
            await asyncio.sleep(self.timing.rapid_banter())
            await self.send_styled_message(
                context, chat_id, "Ralph", None, ralph_comment,
                topic="celebration", with_typing=False
            )

        # Workers occasionally high-five (~20% chance)
        elif random.random() < 0.25:  # 20% of remaining 70% = ~17.5%
            workers = list(self.DEV_TEAM.keys())
            random.shuffle(workers)
            worker1, worker2 = workers[0], workers[1]
            high_five_actions = [
                f"*{worker1} and {worker2} fist bump*",
                f"*{worker1} high-fives {worker2}*",
                f"*{worker1} nods approvingly at {worker2}*",
                f"*{worker2} gives {worker1} a thumbs up*",
            ]
            await asyncio.sleep(self.timing.rapid_banter())
            await context.bot.send_message(
                chat_id=chat_id,
                text=self.format_action(random.choice(high_five_actions).strip('*')),
                parse_mode="Markdown"
            )

        # Show progress bar after delay
        await self.show_progress_bar(context, chat_id, user_id, delay=5.0)

        # Check if we should give a mid-session progress report
        await self.maybe_give_progress_report(context, chat_id, user_id)

    async def _final_task_celebration(self, context, chat_id: int, user_id: int, task_title: str = None):
        """Big celebration for completing the final task!

        This is a special celebration when ALL tasks are done.
        More elaborate than regular task completions.

        Args:
            context: Telegram context
            chat_id: Chat ID
            user_id: User ID
            task_title: Optional title of final task
        """
        m = self.quality_metrics.get(user_id, {})
        tasks_total = m.get("tasks_identified", 0)

        # Big announcement
        if task_title:
            final_msg = f"🎉🎉🎉 *{task_title}* - FINAL TASK COMPLETE! 🎉🎉🎉"
        else:
            final_msg = "🎉🎉🎉 *FINAL TASK COMPLETE!* 🎉🎉🎉"

        await context.bot.send_message(
            chat_id=chat_id,
            text=final_msg,
            parse_mode="Markdown"
        )

        await asyncio.sleep(1.0)

        # Team celebration
        await context.bot.send_message(
            chat_id=chat_id,
            text=self.format_action("The entire team erupts in celebration!"),
            parse_mode="Markdown"
        )

        await asyncio.sleep(0.5)

        # Each team member reacts
        team_reactions = [
            ("Stool", "LET'S GOOO! We did it!"),
            ("Gomer", "Woohoo! Donuts for everyone!"),
            ("Mona", "Excellent work, team. All objectives achieved."),
            ("Gus", "*raises coffee mug* Not bad. Not bad at all."),
        ]

        for name, reaction in team_reactions:
            worker = self.DEV_TEAM.get(name, {})
            await asyncio.sleep(self.timing.rapid_banter())
            await self.send_styled_message(
                context, chat_id, name, worker.get('title'), reaction,
                topic="final celebration", with_typing=False
            )

        await asyncio.sleep(1.0)

        # Ralph's special celebration
        ralph_finals = [
            "WE DID IT! All the tasks! My brain is so happy it might leak out my ears!",
            "FINISHED! This calls for paste! The GOOD paste!",
            "Mr. Worms! Mr. Worms! We did ALL the things! I'm going to tell my cat!",
            "YAY! I'm the best manager ever! Probably! My daddy will be so proud!",
        ]
        ralph_celebration = self.ralph_misspell(random.choice(ralph_finals))

        await self.send_styled_message(
            context, chat_id, "Ralph", None, ralph_celebration,
            topic="final celebration", with_typing=True
        )

        # Maybe a GIF
        if self.should_send_gif():
            await self.send_ralph_gif(context, chat_id, "happy")

        # Final progress bar
        await self.show_progress_bar(context, chat_id, user_id, delay=2.0)

    def should_give_progress_report(self, user_id: int) -> bool:
        """Check if it's time for a mid-session progress report.

        Reports trigger at 25%, 50%, and 75% completion, but not if:
        - A report was given in the last 3 tasks
        - There are fewer than 4 tasks total (too short)

        Args:
            user_id: User ID

        Returns:
            True if a report should be given
        """
        if user_id not in self.quality_metrics:
            return False

        m = self.quality_metrics[user_id]
        tasks_done = m.get("tasks_completed", 0)
        tasks_total = m.get("tasks_identified", 0)
        last_report_task = m.get("last_progress_report_task", 0)

        # Need at least 4 tasks for meaningful reports
        if tasks_total < 4:
            return False

        # Don't report if we just reported (within last 3 tasks)
        if tasks_done - last_report_task < 3:
            return False

        # Calculate completion percentage
        pct = (tasks_done / tasks_total) * 100

        # Check if we're at a milestone (25%, 50%, 75%)
        milestones = [25, 50, 75]
        last_reported_milestone = m.get("last_reported_milestone", 0)

        for milestone in milestones:
            if pct >= milestone and last_reported_milestone < milestone:
                return True

        return False

    async def maybe_give_progress_report(self, context, chat_id: int, user_id: int):
        """Give a mid-session progress report if we're at a milestone.

        Ralph summarizes progress to Mr. Worms at key milestones.

        Args:
            context: Telegram context
            chat_id: Chat ID
            user_id: User ID
        """
        if not self.should_give_progress_report(user_id):
            return

        m = self.quality_metrics[user_id]
        tasks_done = m.get("tasks_completed", 0)
        tasks_total = m.get("tasks_identified", 0)
        pct = (tasks_done / tasks_total) * 100

        # Update tracking
        m["last_progress_report_task"] = tasks_done

        # Determine which milestone we're at
        if pct >= 75:
            milestone = 75
            milestone_text = "three-quarters"
            ralph_excitement = "We're almost there!"
        elif pct >= 50:
            milestone = 50
            milestone_text = "halfway"
            ralph_excitement = "We're at the middle part!"
        else:
            milestone = 25
            milestone_text = "quarter"
            ralph_excitement = "We started good!"

        m["last_reported_milestone"] = milestone

        # Wait a bit before the report
        await asyncio.sleep(2.0)

        # Ralph announces the report
        announcement = self.ralph_misspell(
            f"Mr. Worms! Mr. Worms! I have a progress report! "
            f"We're {milestone_text} done! {ralph_excitement}"
        )

        await self.send_styled_message(
            context, chat_id, "Ralph", None, announcement,
            topic="progress report",
            with_typing=True
        )

        await asyncio.sleep(1.5)

        # Build the mini report
        session = self.active_sessions.get(user_id, {})
        blockers = m.get("blockers_hit", 0) - m.get("blockers_resolved", 0)

        # Mini progress bar
        progress_bar = self.format_progress_bar(tasks_done, tasks_total, bar_length=8)

        # Build report content
        report_lines = [
            f"📊 *Progress Report* ({milestone}%)",
            "",
            progress_bar,
            "",
            f"✅ Done: {tasks_done} tasks",
            f"📋 Remaining: {tasks_total - tasks_done} tasks",
        ]

        # Add ETA if available
        eta_str, completion_time = self.calculate_eta(user_id)
        if completion_time:
            report_lines.append(f"⏳ ETA: {eta_str} (~{completion_time.strftime('%I:%M %p')})")

        # Add blocker warning if any
        if blockers > 0:
            report_lines.append(f"⚠️ Blockers: {blockers}")

        report_text = "\n".join(report_lines)

        await context.bot.send_message(
            chat_id=chat_id,
            text=report_text,
            parse_mode="Markdown"
        )

        # Ralph's summary comment
        await asyncio.sleep(1.0)
        summary_options = [
            "The team is werking very hard! I can hear their keyboards clicking!",
            "My daddy would be proud of how much we did!",
            "Even my cat couldn't do this much work! She mostly sleeps.",
            "We're making good progress! Like a turtle but faster!",
        ]
        ralph_summary = self.ralph_misspell(random.choice(summary_options))

        await self.send_styled_message(
            context, chat_id, "Ralph", None, ralph_summary,
            topic="progress summary",
            with_typing=True
        )

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
        """Call Groq API with BC-001 sanitization and SEC-029 security."""
        try:
            # SEC-029: Check rate limits BEFORE making API call
            allowed, rate_reason = check_rate_limit()
            if not allowed:
                logger.warning(f"SEC-029: Rate limit exceeded - {rate_reason}")
                return get_fallback_response("general")

            # SEC-029: Validate input for prompt injection
            sanitized_messages = []
            for msg in messages:
                sanitized_msg = msg.copy()
                if 'content' in sanitized_msg:
                    content = sanitized_msg['content']

                    # SEC-029: Check for prompt injection
                    is_safe, injection_reason, warnings = validate_llm_input(content, f"groq_{msg.get('role', 'unknown')}")
                    if not is_safe:
                        logger.error(f"SEC-029: Prompt injection blocked - {injection_reason}")
                        return get_fallback_response("general")

                    # Log warnings but continue
                    if warnings:
                        for warning in warnings:
                            logger.warning(f"SEC-029: {warning}")

                    # BC-001: Sanitize for secrets after validation
                    sanitized_msg['content'] = sanitize_for_groq(content)
                sanitized_messages.append(sanitized_msg)

            # Estimate input tokens (rough approximation: 1 token ≈ 4 chars)
            input_text = " ".join([m.get('content', '') for m in sanitized_messages])
            estimated_input_tokens = len(input_text) // 4

            # Make API call
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": sanitized_messages,
                    "temperature": 0.7,
                    "max_tokens": max_tokens
                },
                timeout=60
            )
            result = response.json()

            # SEC-029: Record API call for rate limiting and cost tracking
            output_tokens = result.get("usage", {}).get("completion_tokens", max_tokens // 2)
            actual_input_tokens = result.get("usage", {}).get("prompt_tokens", estimated_input_tokens)
            record_api_call(model, actual_input_tokens, output_tokens)

            # SEC-029: Check cost alerts
            cost_warning = get_security_stats().get('rate_limiting', {}).get('current_hour_cost', 0)
            if cost_warning > 8.0:  # Alert at $8 (80% of default $10 limit)
                logger.warning(f"SEC-029: High API cost this hour: ${cost_warning:.2f}")

            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "...")

            # SEC-029: Validate output
            validated_text, output_warnings = validate_llm_output(response_text)
            if output_warnings:
                for warning in output_warnings:
                    logger.warning(f"SEC-029: Output validation - {warning}")

            # BC-002: Sanitize output too (belt and suspenders)
            return sanitize_for_telegram(validated_text)

        except requests.exceptions.Timeout:
            logger.error("SEC-029: Groq API timeout")
            return get_fallback_response("general")
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC-029: Groq API error: {e}")
            return get_fallback_response("general")
        except Exception as e:
            logger.error(f"SEC-029: Unexpected error in call_groq: {e}")
            return get_fallback_response("general")

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

        # AN-001: Handle satisfaction feedback (thumbs up/down)
        if data.startswith("sat_"):
            await self.handle_satisfaction_feedback(query, context, user_id, data)
            return

        # Handle tap on shoulder (styled button messages)
        if data.startswith("tap_"):
            await self.handle_tap_on_shoulder(query, context)
            return

        # Handle onboarding questions (interactive loading experience)
        if data.startswith("onboard_"):
            await self.handle_onboarding_answer(query, context, user_id, data)
            return

        # Handle CEO order priority selection
        if data.startswith("priority_"):
            await self.handle_priority_selection(query, context, user_id, data)
            return

        # FB-003: Handle feedback type selection
        if data.startswith("feedback_type_"):
            await self.handle_feedback_type_selection(query, context, user_id, data)
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
        telegram_id = update.effective_user.id
        chat_id = update.effective_chat.id
        text = update.message.text

        # FB-003: Check if user is in feedback collection mode
        if context.user_data.get('feedback_state') == 'awaiting_content':
            feedback_type = context.user_data.get('feedback_type')

            # Clear the feedback state
            context.user_data['feedback_state'] = None

            # Process the feedback
            await self._process_feedback_submission(
                update, context, user_id, telegram_id, chat_id,
                text, feedback_type
            )
            return

        # Check if addressing Ralph
        if text.lower().startswith("ralph:"):
            order = text[6:].strip()

            if not order:
                await self.send_styled_message(
                    context, chat_id, "Ralph", None,
                    self.ralph_misspell("You said my name but didn't say anything! My cat does that too!"),
                    with_typing=True
                )
                return

            # Store the order temporarily for priority selection
            if user_id not in self.boss_queue:
                self.boss_queue[user_id] = []

            # Generate unique order ID for callback
            order_id = f"order_{user_id}_{len(self.boss_queue[user_id])}_{random.randint(1000, 9999)}"

            # Store order with pending priority
            self.boss_queue[user_id].append({
                "order": order,
                "order_id": order_id,
                "time": datetime.now().isoformat(),
                "priority": "pending"  # Will be set by button click
            })

            # Ralph asks about priority with inline buttons
            ralph_question = self.ralph_misspell(
                f"Ooh! Mr. Worms wants: '{order[:50]}{'...' if len(order) > 50 else ''}' "
                "This sounds importent! How importent is this?"
            )

            await self.send_styled_message(
                context, chat_id, "Ralph", None, ralph_question,
                topic=order[:30] if order else "CEO order",
                with_typing=True
            )

            # Show priority buttons
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔥 Do this FIRST!", callback_data=f"priority_first_{order_id}")],
                [InlineKeyboardButton("📋 Add to list", callback_data=f"priority_normal_{order_id}")],
                [InlineKeyboardButton("💭 Just a thought", callback_data=f"priority_low_{order_id}")],
            ])

            await context.bot.send_message(
                chat_id=chat_id,
                text="_Ralph looks at you expectantly, paste jar in hand._",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

            return

        # Default response
        await update.message.reply_text(
            "Drop a `.zip` file to start a new project, or use:\n"
            "• `Ralph: [message]` - Talk to Ralph directly\n"
            "• `/status` - Check current session",
            parse_mode="Markdown"
        )

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages - FB-001: Support voice feedback."""
        # Check if this is feedback (caption contains 'feedback')
        caption = update.message.caption or ""
        if "feedback" in caption.lower() and FEEDBACK_COLLECTOR_AVAILABLE:
            user_id = update.effective_user.id
            telegram_id = update.effective_user.id
            chat_id = update.message.chat_id

            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

            # Collect voice feedback
            collector = get_feedback_collector(self.groq_api_key)
            feedback_id = await collector.collect_voice_feedback(
                update, context, user_id, telegram_id
            )

            if feedback_id:
                ralph_response = self.ralph_misspell(
                    f"I heard your voice message! I wrote down what you said! "
                    f"Feedback #{feedback_id}. Listening is my favoritest!"
                )
                await self.send_styled_message(
                    context, chat_id, "Ralph", None, ralph_response,
                    topic="voice feedback received",
                    with_typing=True
                )

                # NT-001: Send notification for voice feedback
                await self._send_feedback_notification(
                    context, chat_id, feedback_id, telegram_id
                )
            else:
                error_response = self.ralph_misspell(
                    "I couldn't hear you very good! Can you try again? My ears are funny sometimes."
                )
                await self.send_styled_message(
                    context, chat_id, "Ralph", None, error_response,
                    topic="voice feedback error",
                    with_typing=True
                )
        else:
            await update.message.reply_text(
                "🎤 Voice commands coming soon! For now, type your message or use `Boss: [message]`\n\n"
                "💡 Tip: Send voice with caption 'feedback' to submit voice feedback!",
                parse_mode="Markdown"
            )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads (visual references) - FB-001: Support screenshot feedback."""
        user_id = update.effective_user.id
        telegram_id = update.effective_user.id
        chat_id = update.message.chat_id
        caption = update.message.caption or ""

        # Check if this is feedback
        if "feedback" in caption.lower() and FEEDBACK_COLLECTOR_AVAILABLE:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

            # Collect screenshot feedback
            collector = get_feedback_collector(self.groq_api_key)
            feedback_id = await collector.collect_screenshot_feedback(
                update, context, user_id, telegram_id, caption
            )

            if feedback_id:
                ralph_response = self.ralph_misspell(
                    f"I see the picture! I put it in my special folder! "
                    f"Feedback #{feedback_id}. Pictures are better than words sometimes!"
                )
                await self.send_styled_message(
                    context, chat_id, "Ralph", None, ralph_response,
                    topic="screenshot feedback received",
                    with_typing=True
                )

                # NT-001: Send notification for screenshot feedback
                await self._send_feedback_notification(
                    context, chat_id, feedback_id, telegram_id
                )
            else:
                error_response = self.ralph_misspell(
                    "The picture didn't work! Maybe try again? My eyes hurt a little."
                )
                await self.send_styled_message(
                    context, chat_id, "Ralph", None, error_response,
                    topic="screenshot feedback error",
                    with_typing=True
                )
            return

        # Regular photo handling (session-based)
        session = self.active_sessions.get(user_id)

        if session:
            await update.message.reply_text(
                "📸 Got the visual reference! I'll pass it to the team.",
                parse_mode="Markdown"
            )
            # TODO: Store photo for reference
        else:
            await update.message.reply_text(
                "📸 Nice image! Start a project first by dropping a `.zip` file.\n\n"
                "💡 Tip: Send a photo with caption 'feedback' to submit screenshot feedback!",
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

    async def mystatus_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mystatus command - FQ-003: Show user's feedback queue status and quality score (QS-003)."""
        telegram_id = update.effective_user.id
        chat_id = update.message.chat_id

        try:
            with get_db() as db:
                # Get user
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if not user:
                    await update.message.reply_text(
                        "You haven't submitted any feedback yet, Mr. Worms! Use /feedback to get started!",
                        parse_mode="Markdown"
                    )
                    return

                # QS-003: Get quality stats
                quality_stats = None
                try:
                    from user_quality_tracker import get_user_quality_tracker
                    tracker = get_user_quality_tracker()
                    quality_stats = tracker.get_user_quality_stats(user.id)
                except Exception as e:
                    logger.error(f"Failed to get quality stats: {e}")

                # FQ-003: Get all user's feedback items
                from feedback_queue import get_feedback_queue
                queue = get_feedback_queue(db)
                feedback_items = queue.get_user_feedback(user.id)

                # Ralph's greeting
                ralph_greetings = [
                    "Hi Mr. Worms! Here's what my team is workin' on:",
                    "Me and the boys are checkin' your requests, Mr. Worms:",
                    "Lemme show you what we got, boss:",
                ]
                greeting = random.choice(ralph_greetings)

                # Build status message
                status_parts = [f"*{greeting}*\n"]

                # QS-003: Quality Score Section
                if quality_stats:
                    status_parts.append(f"{quality_stats['tier_emoji']} *Quality Score: {quality_stats['quality_score']:.1f}/100* ({quality_stats['tier']})")
                    status_parts.append(f"{quality_stats['description']}\n")

                    if quality_stats['boost_percentage'] > 0:
                        status_parts.append(f"🚀 Priority Boost: +{quality_stats['boost_percentage']}%")
                    elif quality_stats['flagged']:
                        status_parts.append(f"⚠️ _Your feedback needs improvement to earn priority boosts._")

                    status_parts.append(f"\n📊 Feedback Stats:")
                    status_parts.append(f"  • Total submitted: {quality_stats['total_feedback']}")
                    status_parts.append(f"  • Scored: {quality_stats['scored_feedback']}")
                else:
                    status_parts.append(f"📊 Quality Score: {user.quality_score:.1f}/100")

                # FQ-003: Individual Feedback Items
                if feedback_items:
                    status_parts.append(f"\n📋 *Your Feedback Items*:\n")

                    # Status emoji mapping
                    status_emoji = {
                        "pending": "⏳",
                        "screening": "🔍",
                        "scored": "📊",
                        "queued": "📥",
                        "in_progress": "🔨",
                        "testing": "🧪",
                        "deployed": "✅",
                        "rejected": "❌"
                    }

                    # Get queue position for queued items
                    queued_items = queue.get_queue_by_status("queued", limit=1000)
                    queue_positions = {item.id: idx + 1 for idx, item in enumerate(queued_items)}

                    for idx, item in enumerate(feedback_items[:10], 1):  # Show max 10
                        # Truncate content for display
                        title = item.content[:50] + "..." if len(item.content) > 50 else item.content
                        emoji = status_emoji.get(item.status, "📝")

                        status_parts.append(f"{idx}. {emoji} *{item.status.upper()}*")
                        status_parts.append(f"   _{title}_")

                        # Show queue position if queued
                        if item.status == "queued" and item.id in queue_positions:
                            position = queue_positions[item.id]
                            status_parts.append(f"   Position in queue: #{position}")

                            # Estimate time to build (rough heuristic: 5 min per item ahead)
                            est_minutes = position * 5
                            if est_minutes < 60:
                                status_parts.append(f"   Estimated wait: ~{est_minutes} min")
                            else:
                                est_hours = est_minutes / 60
                                status_parts.append(f"   Estimated wait: ~{est_hours:.1f} hours")

                        # Show priority score if scored
                        if item.priority_score:
                            status_parts.append(f"   Priority: {item.priority_score:.1f}/10")

                        status_parts.append("")  # Blank line between items

                    if len(feedback_items) > 10:
                        status_parts.append(f"_...and {len(feedback_items) - 10} more items_\n")
                else:
                    status_parts.append(f"\n📋 No feedback submitted yet!")

                # Subscription tier
                status_parts.append(f"💎 Tier: {user.subscription_tier.title()}")

                # Ralph's sign-off
                ralph_signoffs = [
                    "\n_That's unpossible to mess up! - Ralph_ 🎭",
                    "\n_Me fail feedbak? That's unpossible! - Ralph_ 🎭",
                    "\n_I'm a project managerer! - Ralph_ 🎭",
                ]
                status_parts.append(random.choice(ralph_signoffs))

                status_message = "\n".join(status_parts)
                await update.message.reply_text(status_message, parse_mode="Markdown")

        except Exception as e:
            # SEC-020: Mask telegram_id in logs
            masked_id = mask_for_logs(telegram_id, PIIField.TELEGRAM_ID)
            logger.error(f"Failed to get feedback status for user {masked_id}: {e}")
            await update.message.reply_text(
                "Me fail status? That's unpossible! Try again, Mr. Worms.",
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

    async def _send_feedback_notification(
        self, context: ContextTypes.DEFAULT_TYPE,
        chat_id: int, feedback_id: int, telegram_id: int
    ):
        """NT-001: Send notification to user after feedback is processed.

        Shows:
        - Quality score (0-100)
        - Priority tier (HIGH/MEDIUM/LOW)
        - Position in queue
        - In-character from Ralph

        Args:
            context: Telegram context
            chat_id: Chat ID
            feedback_id: Feedback database ID
            telegram_id: Telegram user ID
        """
        if not DATABASE_AVAILABLE or not FEEDBACK_SCORER_AVAILABLE:
            # Can't send full notification without these modules
            return

        try:
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

            # Score the feedback
            scorer = get_feedback_scorer(self.groq_api_key)
            scores = scorer.score_feedback_by_id(feedback_id)

            if not scores:
                logger.warning(f"NT-001: Failed to score feedback {feedback_id}")
                return

            quality_score = scores.get('total', 0)

            # Get feedback from database to check priority_score
            with get_db() as db:
                feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

                if not feedback:
                    logger.warning(f"NT-001: Feedback {feedback_id} not found")
                    return

                priority_score = feedback.priority_score or 0

                # Get priority tier
                priority_tier = get_priority_tier(priority_score)
                tier_emoji = get_priority_tier_emoji(priority_tier)

                # Calculate position in queue (count pending/queued feedback with higher priority)
                queue_position = db.query(Feedback).filter(
                    Feedback.status.in_(['pending', 'screening', 'scored', 'queued']),
                    Feedback.priority_score > priority_score
                ).count() + 1

            # Build in-character notification from Ralph
            tier_descriptions = {
                "HIGH": "the really importent pile",
                "MEDIUM": "the middle pile",
                "LOW": "the 'we'll get to it' pile"
            }
            tier_desc = tier_descriptions.get(priority_tier, "a pile")

            # Ralph's quality score interpretation
            if quality_score >= 80:
                quality_comment = "That's a really good feedbak! I can understand it!"
            elif quality_score >= 60:
                quality_comment = "That's pretty good feedbak! I think I get it!"
            elif quality_score >= 40:
                quality_comment = "That's okay feedbak! I'm trying to understand!"
            else:
                quality_comment = "That's... feedbak! My brain is working hard!"

            # Queue position comment
            if queue_position == 1:
                queue_comment = "You're at the FRONT of the line! That's the best spot!"
            elif queue_position <= 5:
                queue_comment = f"You're #{queue_position} in line! That's pretty close to the front!"
            elif queue_position <= 20:
                queue_comment = f"You're #{queue_position} in line! There's {queue_position - 1} people ahead of you!"
            else:
                queue_comment = f"You're #{queue_position} in line! That's a lot of feedbak! My team is busy!"

            notification = self.ralph_misspell(
                f"\n📊 *Feedbak Report for #{feedback_id}*\n\n"
                f"✨ *Quality Score:* {quality_score:.0f}/100\n"
                f"{quality_comment}\n\n"
                f"{tier_emoji} *Priority:* {priority_tier}\n"
                f"I put this in {tier_desc}!\n\n"
                f"📍 *Queue Position:* #{queue_position}\n"
                f"{queue_comment}\n\n"
                f"I'll make sure the team works on it! My cat's breath smells like cat food!"
            )

            await context.bot.send_message(
                chat_id=chat_id,
                text=notification,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"NT-001: Failed to send feedback notification: {e}")
            # Don't fail the whole feedback process if notification fails

    async def _process_feedback_submission(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
        user_id: int, telegram_id: int, chat_id: int,
        content: str, feedback_type: str
    ):
        """FB-003: Process feedback submission with type-specific storage.

        Args:
            update: Telegram update
            context: Telegram context
            user_id: User ID
            telegram_id: Telegram ID
            chat_id: Chat ID
            content: Feedback content
            feedback_type: Type of feedback (bug_report, feature_request, etc.)
        """
        if not FEEDBACK_COLLECTOR_AVAILABLE:
            await update.message.reply_text(
                "Feedback collection is currently unavailable. Please try again later.",
                parse_mode="Markdown"
            )
            return

        # FB-002: Check subscription tier before accepting feedback
        if SUBSCRIPTION_MANAGER_AVAILABLE:
            sub_manager = get_subscription_manager()
            can_submit, tier_name, weight = sub_manager.can_submit_feedback(telegram_id)

            if not can_submit:
                # User is Viewer tier - show upgrade prompt
                upgrade_prompt = self.ralph_misspell(
                    "Oh wait! My boss is saying only Builders can give feedbak! "
                    "You need to upgrade to be a Builder! Use /subscribe to see how!"
                )
                await self.send_styled_message(
                    context, chat_id, "Ralph", None, upgrade_prompt,
                    topic="subscription gate",
                    with_typing=True
                )
                upgrade_msg = sub_manager.get_upgrade_message("free")
                await update.message.reply_text(upgrade_msg, parse_mode="Markdown")
                return

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # FB-002: Get feedback weight based on subscription tier
        feedback_weight = 1.0
        if SUBSCRIPTION_MANAGER_AVAILABLE:
            sub_manager = get_subscription_manager()
            feedback_weight = sub_manager.get_feedback_weight(telegram_id)

        # Collect the feedback
        collector = get_feedback_collector(self.groq_api_key)

        # FB-003: Store feedback with selected type
        metadata = {"source": "interactive", "type": feedback_type}
        feedback_id = await collector.collect_text_feedback(
            user_id=user_id,
            telegram_id=telegram_id,
            content=content,
            feedback_type=feedback_type,
            metadata=metadata,
            weight=feedback_weight,
            update=update  # For rate limiting
        )

        # SP-001: Handle spam rejection (-2)
        if feedback_id == -2:
            spam_reason = collector.get_spam_rejection_message(metadata)
            error_response = self.ralph_misspell(
                f"Hmm... my brain is confused! That doesn't look like real feedbak! "
                f"Can you try again with something about Ralph Mode? I promise I'm paying attention!"
            )
            await self.send_styled_message(
                context, chat_id, "Ralph", None, error_response,
                topic="spam rejection",
                with_typing=True
            )
            return

        # Handle rate limiting (-1)
        if feedback_id == -1:
            rate_limit_msg = collector.get_rate_limit_message(metadata)
            error_response = self.ralph_misspell(
                f"Whoa! Slow down! My hand is tired from writing! "
                f"You're giving feedbak too fast! Take a little break and try again!"
            )
            await self.send_styled_message(
                context, chat_id, "Ralph", None, error_response,
                topic="rate limit exceeded",
                with_typing=True
            )
            return

        if feedback_id and feedback_id > 0:
            # Success! Ralph confirms receipt in-character with type-specific response
            type_names = {
                "bug_report": "bug report",
                "feature_request": "feture request",
                "enhancement": "enhancement idea",
                "ux_issue": "UX feedbak",
                "performance": "performance feedbak",
                "other": "feedbak"
            }

            type_name = type_names.get(feedback_type, "feedbak")

            confirmations = [
                f"Ooh! I got your {type_name}! I wrote it down in my special notebook! "
                f"Feedback #{feedback_id}. My cat's breath smells like cat food!",

                f"I'm learnding about your {type_name}! I'll tell the team right away! "
                f"This is feedback number {feedback_id}!",

                f"Yay! {type_name.title()}! I'll put this in the importent pile! "
                f"Your feedback is #{feedback_id}. I dressed myself today!",
            ]

            ralph_response = self.ralph_misspell(random.choice(confirmations))

            await self.send_styled_message(
                context, chat_id, "Ralph", None, ralph_response,
                topic="feedback received",
                with_typing=True
            )

            # Maybe send a GIF
            if self.should_send_gif():
                await self.send_ralph_gif(context, chat_id, "happy")

            # NT-001: Send notification with quality score, priority tier, and queue position
            await self._send_feedback_notification(
                context, chat_id, feedback_id, telegram_id
            )

        else:
            # Failed to store feedback
            error_response = self.ralph_misspell(
                "Uh oh! I tried to write it down but my pencil broke! "
                "Can you try again? My brain hurts a little."
            )
            await self.send_styled_message(
                context, chat_id, "Ralph", None, error_response,
                topic="feedback error",
                with_typing=True
            )

    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /feedback command - Collect user feedback for RLHF loop (FB-001)."""
        if not FEEDBACK_COLLECTOR_AVAILABLE:
            await update.message.reply_text(
                "Feedback collection is currently unavailable. Please try again later.",
                parse_mode="Markdown"
            )
            return

        user_id = update.effective_user.id
        telegram_id = update.effective_user.id
        chat_id = update.message.chat_id

        # Check if they provided feedback text
        feedback_text = " ".join(context.args) if context.args else None

        if not feedback_text:
            # FB-003: Show feedback type selection with inline buttons
            help_text = self.ralph_misspell(
                "Ooh! You want to give feedbak? That's so nice! What kind of feedbak do you have?\n\n"
                "Pick one of the buttons below and I'll help you tell us all about it!"
            )

            # FB-003: Inline buttons for feedback type selection
            keyboard = [
                [
                    InlineKeyboardButton("🐛 Bug Report", callback_data="feedback_type_bug_report"),
                    InlineKeyboardButton("✨ Feature Request", callback_data="feedback_type_feature_request")
                ],
                [
                    InlineKeyboardButton("⚡ Enhancement", callback_data="feedback_type_enhancement"),
                    InlineKeyboardButton("🎨 UX Issue", callback_data="feedback_type_ux_issue")
                ],
                [
                    InlineKeyboardButton("🚀 Performance", callback_data="feedback_type_performance"),
                    InlineKeyboardButton("💬 Other", callback_data="feedback_type_other")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await self.send_styled_message(
                context, chat_id, "Ralph", None, help_text,
                topic="feedback type selection",
                with_typing=True
            )

            await update.message.reply_text(
                "Pick a feedbak type:",
                reply_markup=reply_markup
            )
            return

        # FB-002: Check subscription tier before accepting feedback
        if SUBSCRIPTION_MANAGER_AVAILABLE:
            sub_manager = get_subscription_manager()
            can_submit, tier_name, weight = sub_manager.can_submit_feedback(telegram_id)

            if not can_submit:
                # User is Viewer tier - show upgrade prompt with Ralph personality
                upgrade_prompts = [
                    "Ooh feedbak! I love feedbak! But my boss says only Builders can tell us what to build. "
                    "You're a Viewer right now, which means you can watch but not help build! "
                    "Want to upgrade? I think you'd make a great Builder! My nose makes its own sauce!",

                    "That's so nice you want to help! But Mr. Worms says feedback is only for Builders and Priority members! "
                    "You're watching right now which is super fun, but if you want to tell us what to make, "
                    "you gotta be a Builder! Use /subscribe and I'll show you how! I eated the purple berries!",

                    "Yay feedback! Oh wait... my boss is saying something in my ear... he says you need to be a Builder first! "
                    "Right now you're a Viewer which is cool and all, but to help us build stuff you need to upgrade! "
                    "Type /subscribe and I'll explain! My cat's breath smells like cat food!",
                ]

                ralph_response = self.ralph_misspell(random.choice(upgrade_prompts))

                await self.send_styled_message(
                    context, chat_id, "Ralph", None, ralph_response,
                    topic="subscription gate",
                    with_typing=True
                )

                # Show upgrade options
                upgrade_msg = sub_manager.get_upgrade_message("free")
                await update.message.reply_text(upgrade_msg, parse_mode="Markdown")

                return

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # FB-002: Get feedback weight based on subscription tier
        feedback_weight = 1.0
        if SUBSCRIPTION_MANAGER_AVAILABLE:
            sub_manager = get_subscription_manager()
            feedback_weight = sub_manager.get_feedback_weight(telegram_id)

        # Collect the feedback
        collector = get_feedback_collector(self.groq_api_key)

        # Classify feedback type
        feedback_type = collector.classify_feedback_type(feedback_text)

        # Store feedback with subscription weight
        feedback_id = await collector.collect_text_feedback(
            user_id=user_id,
            telegram_id=telegram_id,
            content=feedback_text,
            feedback_type=feedback_type,
            metadata={"source": "command"},
            weight=feedback_weight  # FB-002: Subscription tier weight
        )

        if feedback_id:
            # Success! Ralph confirms receipt in-character
            confirmations = [
                f"Ooh! I got your {feedback_type}! I wrote it down in my special notebook! "
                f"Feedback #{feedback_id}. My cat's breath smells like cat food!",

                f"I'm learnding about your {feedback_type}! I'll tell the team right away! "
                f"This is feedback number {feedback_id}!",

                f"Yay! {feedback_type.title()} feedback! I'll put this in the importent pile! "
                f"Your feedback is #{feedback_id}. I dressed myself today!",
            ]

            ralph_response = self.ralph_misspell(random.choice(confirmations))

            await self.send_styled_message(
                context, chat_id, "Ralph", None, ralph_response,
                topic="feedback received",
                with_typing=True
            )

            # Maybe send a GIF
            if self.should_send_gif():
                await self.send_ralph_gif(context, chat_id, "happy")

            # NT-001: Send notification for command feedback
            await self._send_feedback_notification(
                context, chat_id, feedback_id, telegram_id
            )

        else:
            # Failed to store feedback
            error_response = self.ralph_misspell(
                "Uh oh! I tried to write it down but my pencil broke! "
                "Can you try again? My brain hurts a little."
            )
            await self.send_styled_message(
                context, chat_id, "Ralph", None, error_response,
                topic="feedback error",
                with_typing=True
            )

    async def version_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /version command - VM-003: Version Selection for Users."""
        telegram_id = update.effective_user.id
        chat_id = update.message.chat_id

        # Parse command arguments
        args = context.args

        # Get current version from VERSION file
        try:
            from version_manager import VersionManager
            vm = VersionManager()
            current_version = vm.get_current_version()
        except Exception as e:
            logger.error(f"Error reading version: {e}")
            current_version = "unknown"

        # If no arguments, show current version and preference
        if not args:
            try:
                with get_db() as db:
                    user = db.query(User).filter(User.telegram_id == telegram_id).first()

                    if not user:
                        # Create user if doesn't exist
                        user = User(telegram_id=telegram_id)
                        db.add(user)
                        db.commit()

                    preference = user.version_preference or "stable"

                    status_text = f"""
*📦 Ralph Mode Version Info*

🔢 Current Version: `{current_version}`
⚙️ Your Preference: `{preference}`

*Available Versions:*
• `/version stable` - Stable release (recommended)
• `/version beta` - Beta testing (new features)
• `/version alpha` - Alpha testing (cutting edge, Priority tier only)

Use `/version <type>` to switch!
"""

                    await update.message.reply_text(status_text, parse_mode="Markdown")

            except Exception as e:
                logger.error(f"Error in version command: {e}")
                await update.message.reply_text(
                    "Uh oh! Something went wrong checking your version preference. Try again?",
                    parse_mode="Markdown"
                )
            return

        # Handle version selection
        version_type = args[0].lower()

        if version_type not in ["stable", "beta", "alpha"]:
            error_msg = self.ralph_misspell(
                f"Hmm, I don't know what '{version_type}' version is! "
                "I only know about stable, beta, and alpha. Pick one of those!"
            )
            await self.send_styled_message(
                context, chat_id, "Ralph", None, error_msg,
                topic="version error",
                with_typing=True
            )
            return

        # Check if alpha requires Priority tier
        if version_type == "alpha":
            try:
                with get_db() as db:
                    user = db.query(User).filter(User.telegram_id == telegram_id).first()

                    if not user or user.subscription_tier not in ["priority", "enterprise"]:
                        restriction_msg = self.ralph_misspell(
                            "Ooh! Alpha versions are special! Only Priority and Enterprise members can use those! "
                            "They get to test the super new stuff before everyone else! "
                            "You can use /subscribe to upgrade, or pick 'stable' or 'beta' instead!"
                        )
                        await self.send_styled_message(
                            context, chat_id, "Ralph", None, restriction_msg,
                            topic="version restriction",
                            with_typing=True
                        )
                        return
            except Exception as e:
                logger.error(f"Error checking subscription tier: {e}")

        # Update user's version preference
        try:
            with get_db() as db:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()

                if not user:
                    user = User(telegram_id=telegram_id)
                    db.add(user)

                old_preference = user.version_preference or "stable"
                user.version_preference = version_type
                db.commit()

                # Confirm the change
                if old_preference == version_type:
                    confirm_msg = self.ralph_misspell(
                        f"You're already using {version_type} version! That's a good choice!"
                    )
                else:
                    confirm_msg = self.ralph_misspell(
                        f"Okay! I switched you from {old_preference} to {version_type}! "
                        f"You'll get {version_type} versions from now on! My cat's breath smells like cat food!"
                    )

                await self.send_styled_message(
                    context, chat_id, "Ralph", None, confirm_msg,
                    topic="version changed",
                    with_typing=True
                )

                # Maybe send a GIF
                if self.should_send_gif():
                    await self.send_ralph_gif(context, chat_id, "happy")

        except Exception as e:
            logger.error(f"Error updating version preference: {e}")
            error_msg = self.ralph_misspell(
                "Uh oh! I tried to remember your choice but I forgot already! "
                "Can you try again? My brain makes its own choices sometimes!"
            )
            await self.send_styled_message(
                context, chat_id, "Ralph", None, error_msg,
                topic="version update error",
                with_typing=True
            )

    def run(self):
        """Start the bot."""
        if not TELEGRAM_BOT_TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
            return

        print("🚀 Ralph Mode starting...")
        print(f"   Groq API: {'✅' if GROQ_API_KEY else '❌'}")

        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # BC-002: Wrap bot.send_message to sanitize ALL outgoing messages
        original_send_message = app.bot.send_message
        original_edit_message_text = app.bot.edit_message_text

        async def sanitized_send_message(*args, **kwargs):
            """BC-002: Sanitize all messages before sending to Telegram."""
            # Sanitize the 'text' parameter
            if 'text' in kwargs:
                kwargs['text'] = self._sanitize_output(kwargs['text'])
            elif len(args) > 1:
                # text is the second positional argument (after chat_id)
                args = list(args)
                args[1] = self._sanitize_output(args[1])
                args = tuple(args)

            return await original_send_message(*args, **kwargs)

        async def sanitized_edit_message_text(*args, **kwargs):
            """BC-002: Sanitize edited messages before sending to Telegram."""
            # Sanitize the 'text' parameter
            if 'text' in kwargs:
                kwargs['text'] = self._sanitize_output(kwargs['text'])
            elif len(args) > 0:
                # text is the first positional argument for edit_message_text
                args = list(args)
                args[0] = self._sanitize_output(args[0])
                args = tuple(args)

            return await original_edit_message_text(*args, **kwargs)

        app.bot.send_message = sanitized_send_message
        app.bot.edit_message_text = sanitized_edit_message_text
        logger.info("BC-002: Output filter installed - all messages will be sanitized")

        # Handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("mystatus", self.mystatus_command))  # QS-003 & FQ-003
        app.add_handler(CommandHandler("report", self.report_command))
        app.add_handler(CommandHandler("feedback", self.feedback_command))  # FB-001
        app.add_handler(CommandHandler("version", self.version_command))  # VM-003
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        app.add_handler(CallbackQueryHandler(self.handle_callback))

        # SEC-019: Register GDPR compliance handlers
        if GDPR_AVAILABLE:
            register_gdpr_handlers(app)
            print("✅ GDPR compliance handlers registered")

        # SF-003: Register admin override controls
        if ADMIN_HANDLER_AVAILABLE:
            setup_admin_handlers(app)
            print("✅ Admin override controls registered")

        print("🤖 Bot is running! Send /start in Telegram.")
        app.run_polling()


if __name__ == "__main__":
    bot = RalphBot()
    bot.run()
