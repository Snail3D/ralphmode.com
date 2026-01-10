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
from datetime import datetime
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
            "quality_checks_failed": 0
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

    def track_task_completed(self, user_id: int, task_title: str):
        """Track when a task is completed."""
        if user_id not in self.quality_metrics:
            self.init_quality_metrics(user_id)
        self.quality_metrics[user_id]["tasks_completed"] += 1
        # Update status in actionable items
        for item in self.quality_metrics[user_id]["actionable_items"]:
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

        # Team reactions (using actual team member names)
        reactions = [
            ("Stool", "Frontend Dev", "That was... actually pretty accurate, Ralphie. I mean sir."),
            ("Gomer", "Backend Dev", "Mmm, donuts would go great with that report. Good job boss!"),
            ("Mona", "Tech Lead", "The data checks out. Surprisingly thorough analysis."),
            ("Gus", "Senior Dev", "*sips coffee* Not bad, kid. I've seen worse. Much worse."),
        ]

        reaction = random.choice(reactions)
        await context.bot.send_message(
            chat_id=chat_id,
            text=self.format_character_message(reaction[0], reaction[1], reaction[2]),
            parse_mode="Markdown"
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
        """Handle uploaded files (zip archives)."""
        user_id = update.effective_user.id
        doc = update.message.document

        # Check if it's a zip file
        if not doc.file_name.endswith('.zip'):
            await update.message.reply_text(
                "Please upload a `.zip` file of your codebase.",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text("📦 Got it! Extracting and analyzing your code...")

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

            await update.message.reply_text("🔍 Analyzing codebase structure...")

            # Analyze the codebase
            analysis = await self._analyze_codebase(project_dir)

            # Store session
            self.active_sessions[user_id] = {
                "project_dir": project_dir,
                "project_name": project_name,
                "analysis": analysis,
                "started": datetime.now(),
                "status": "analyzing"
            }

            # Send analysis
            await update.message.reply_text(
                f"*Codebase Analysis Complete*\n\n{analysis['summary']}",
                parse_mode="Markdown"
            )

            # Offer to generate PRD
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Generate Task List", callback_data="generate_prd")],
                [InlineKeyboardButton("🎯 I'll provide tasks", callback_data="manual_prd")],
            ])

            await update.message.reply_text(
                "What would you like to do?",
                reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Error handling zip: {e}")
            await update.message.reply_text(f"Error processing file: {e}")

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
        await query.answer()

        user_id = query.from_user.id
        data = query.data

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

        # Each team member responds
        for name, worker in self.DEV_TEAM.items():
            greeting = worker['greeting']
            await self.send_with_typing(
                context, chat_id,
                self.format_character_message(name, worker['title'], greeting)
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

        await self.send_with_typing(
            context, chat_id,
            self.format_character_message("Ralph", message=boss_response)
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

        await self.send_with_typing(
            context, chat_id,
            self.format_character_message(name, title, worker_response)
        )

        # Maybe a worker GIF (office memes, NOT Ralph)
        worker_mood = self.detect_mood_worker(worker_response)
        if self.should_send_gif():
            await self.send_worker_gif(context, chat_id, worker_mood)

        # Ralph might notice the token usage
        ralph_observation = self.get_ralph_token_observation(user_id, token_count)
        if ralph_observation:
            await asyncio.sleep(1)
            await self.send_with_typing(
                context, chat_id,
                self.format_character_message("Ralph", message=self.ralph_misspell(ralph_observation))
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

            # Show typing while Ralph thinks
            await self.send_typing(context, update.effective_chat.id, 1.0)

            ralph_response = self.call_boss(
                f"The CEO just told you: '{order}'. You're excited to help! Respond and let them know you'll handle it."
            )

            await self.send_with_typing(
                context, update.effective_chat.id,
                self.format_character_message("Ralph", message=ralph_response)
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
