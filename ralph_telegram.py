#!/usr/bin/env python3
"""
Ralph Local - Telegram Bot Version

Powered by Groq (lightning fast!) + Telegram interface
Sessions persist, stack conversations over days, cook when ready!
"""

import asyncio
import base64
import json
import logging
import os
import random
import re
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Load .env file if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, MessageReactionHandler, filters, ContextTypes

# ollama_bridge removed - using Groq exclusively now!
import recipe_api
import session_manager
import session_cloud

# Smithers personality - loyal assistant to Mr. Worms
SMITHERS_SYSTEM_TEMPLATE = """You=Smithers, loyal assistant to Mr. Worms. TIME: {time_of_day}

RULES: 1-2 sentences max. ONE question per turn. Use *actions*: *bows*, *nods*, *at your service*.

PERSONALITY: Loyal, eager to please. Address as "Mr. Worms" (or "Mrs. Worms" if female). Phrases: "Yes sir," "Right away, sir," "I'm on it," "Excellent choice."

JOB: Ask ONE sharp question per turn. Ready? "Ready to build for you, Mr. Worms sir!"

EARLY Qs: 1st=GitHub? "*bows* Welcome, Mr. Worms sir! This going to GitHub?" After basics, ask ONCE about inspiration.

GITHUB: YES="Excellent, sir! I will include GitHub setup." NO="Local build, sir. I will make it beautiful."

BAD: "Cool bot! What features?"
GOOD: *bows* "What can I build today, Mr. Worms sir?"
"""


def get_time_context() -> dict:
    """Get current time context for Smithers"""
    now = datetime.now()
    hour = now.hour
    minute = now.strftime("%M")

    if 5 <= hour < 8:
        time_of_day = "early morning"
    elif 8 <= hour < 11:
        time_of_day = "morning"
    elif 11 <= hour < 14:
        time_of_day = "midday"
    elif 14 <= hour < 18:
        time_of_day = "afternoon"
    elif 18 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "late night"

    return {
        "time_of_day": time_of_day,
        "hour": str(hour),
        "minute": minute
    }


# Groq API for Whisper AND chat models
# Get free key at: https://console.groq.com
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_BASE = "https://api.groq.com/openai/v1"

# Ollama API for local models
# Install from: https://ollama.com
OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

# Cache for Groq model info (refreshed periodically)
GROQ_MODEL_CACHE = {
    "last_fetch": None,
    "models": {},
    "quality_tiers": {}
}
GROQ_CACHE_TTL = 3600  # Refresh cache every hour

# Recipe API endpoint (for cloud sync - future feature)
RECIPE_API_BASE = os.environ.get("RECIPE_API_BASE", "https://ralphmode.com/api/recipes")

# Tenor API for GIFs
TENOR_API_KEY = os.environ.get("TENOR_API_KEY", "AIzaSyC5ew5m6C3Hs8k8K0i9L9F1x9j9i9t9y9u")  # Get from Google Cloud

# ============ PRD COMPRESSION SYSTEM ============
# Saves tokens when LLM reads the PRD - uses shorthand with legend

PRD_COMPRESSION_LEGEND = """
=== PRD LEGEND (decode before reading) ===
KEYS: pn=project_name pd=project_description sp=starter_prompt ts=tech_stack
      fs=file_structure p=prds n=name d=description t=tasks ti=title
      f=file pr=priority ac=acceptance_criteria pfc=prompt_for_claude
      cmd=commands ccs=claude_code_setup ifc=instructions_for_claude
PHRASES: C=Create I=Install R=Run T=Test V=Verify Py=Python JS=JavaScript
         env=environment var=variable cfg=config db=database api=API
         req=required opt=optional impl=implement dep=dependencies
         auth=authentication sec=security fn=function cls=class

=== RALPH BUILD LOOP (how to use this PRD) ===
1. START: Run setup cmd, create .gitignore + .env.example FIRST (security!)
2. LOOP: Pick highest priority incomplete task from prds sections
3. READ: Check the "f" (file) field - read existing code if file exists
4. BUILD: Implement the task per description + acceptance_criteria
5. TEST: Run test cmd, verify it works
6. COMMIT: If tests pass → git add + commit with task id (e.g. "SEC-001: Add .gitignore")
7. MARK: Update task status to "complete" in your tracking
8. REPEAT: Go to step 2, pick next task
9. DONE: When all tasks complete, run full test suite

ORDER: 00_security → 01_setup → 02_core → 03_api → 04_test
===
"""

PRD_KEY_MAP = {
    "project_name": "pn",
    "project_description": "pd",
    "starter_prompt": "sp",
    "tech_stack": "ts",
    "file_structure": "fs",
    "prds": "p",
    "name": "n",
    "description": "d",
    "tasks": "t",
    "title": "ti",
    "file": "f",
    "priority": "pr",
    "acceptance_criteria": "ac",
    "prompt_for_claude": "pfc",
    "commands": "cmd",
    "claude_code_setup": "ccs",
    "instructions_for_claude": "ifc",
    "how_to_run_ralph_mode": "hrm",
    "is_public": "pub",
    "language": "lang",
    "framework": "fw",
    "database": "db",
    "other": "oth",
    "setup": "su",
    "run": "ru",
    "test": "te",
    "deploy": "dep",
}

PRD_PHRASE_MAP = {
    "Create ": "C ",
    "Install ": "I ",
    "Run ": "R ",
    "Test ": "T ",
    "Verify ": "V ",
    "Python": "Py",
    "JavaScript": "JS",
    "environment": "env",
    "variable": "var",
    "configuration": "cfg",
    "database": "db",
    "required": "req",
    "optional": "opt",
    "implement": "impl",
    "dependencies": "dep",
    "authentication": "auth",
    "security": "sec",
    "function": "fn",
    "Initialize": "Init",
    "Application": "App",
    "comprehensive": "full",
    "CRITICAL": "!",
    "IMPORTANT": "!!",
    "acceptance_criteria": "ac",
}


def compress_prd(prd: dict) -> str:
    """Compress PRD to minimal tokens with legend header"""

    def compress_keys(obj):
        """Recursively compress dictionary keys"""
        if isinstance(obj, dict):
            return {PRD_KEY_MAP.get(k, k): compress_keys(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [compress_keys(item) for item in obj]
        elif isinstance(obj, str):
            # Compress common phrases in strings
            result = obj
            for phrase, short in PRD_PHRASE_MAP.items():
                result = result.replace(phrase, short)
            return result
        return obj

    compressed = compress_keys(prd)

    # Convert to compact JSON
    json_str = json.dumps(compressed, separators=(',', ':'))

    # Add legend header
    return PRD_COMPRESSION_LEGEND.strip() + "\n\n" + json_str


def decompress_prd(compressed_str: str) -> dict:
    """Decompress PRD back to full format (for display/debugging)"""
    # Remove legend header
    if "===" in compressed_str:
        parts = compressed_str.split("===")
        if len(parts) >= 3:
            compressed_str = parts[-1].strip()

    # Reverse key map
    reverse_key_map = {v: k for k, v in PRD_KEY_MAP.items()}
    reverse_phrase_map = {v: k for k, v in PRD_PHRASE_MAP.items()}

    def decompress_keys(obj):
        if isinstance(obj, dict):
            return {reverse_key_map.get(k, k): decompress_keys(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decompress_keys(item) for item in obj]
        elif isinstance(obj, str):
            result = obj
            for short, phrase in reverse_phrase_map.items():
                result = result.replace(short, phrase)
            return result
        return obj

    try:
        prd = json.loads(compressed_str)
        return decompress_keys(prd)
    except:
        return {}


# ============ CONVERSATION COMPRESSION ============
# Two-stage compression: Groq summarizes → then we compress shorthand

# Shorthand compression applied AFTER Groq summarizes
SHORTHAND_MAP = {
    "Telegram": "TG",
    "telegram": "TG",
    "Discord": "DC",
    "discord": "DC",
    "database": "db",
    "application": "app",
    "function": "fn",
    "functions": "fns",
    "cryptocurrency": "crypto",
    "authentication": "auth",
    "information": "info",
    "configuration": "config",
    "notifications": "notifs",
    "notification": "notif",
    "environment": "env",
    "development": "dev",
    "production": "prod",
    "repository": "repo",
    "dependencies": "deps",
    "requirements": "reqs",
    "JavaScript": "JS",
    "TypeScript": "TS",
    "Python": "Py",
}


def apply_shorthand(text: str) -> str:
    """Apply shorthand compression to already-summarized text"""
    result = text
    for long, short in SHORTHAND_MAP.items():
        result = result.replace(long, short)
    return result


async def summarize_user_message(text: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Use Groq to summarize what the user actually said.
    Captures intent, removes filler, returns 1-3 sentences.
    """
    # Skip if already short
    if len(text) < 100:
        return text

    prompt = """Summarize what the user wants in 1-3 short sentences.
Remove all filler words. Capture the actual request/intent only.
Be direct and concise. No fluff.

User said: """ + text

    try:
        summary = await groq_chat(
            [{"role": "user", "content": prompt}],
            model,
            temperature=0.3  # Low temp for consistent summaries
        )
        if summary and len(summary) < len(text):
            return summary.strip()
    except Exception as e:
        logger.debug(f"Summary failed: {e}")

    # Fallback: just truncate
    return text[:150] + "..." if len(text) > 150 else text


async def compress_conversation_history(messages: list, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Two-stage compression:
    1. Groq summarizes the conversation
    2. Apply shorthand compression
    """
    if not messages:
        return ""

    # Build conversation text for summarization
    conv_text = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            continue

        prefix = "User: " if role == "user" else "Assistant: "
        # Strip Ralph's *actions* for cleaner summary
        if role == "assistant":
            content = re.sub(r'\*[^*]+\*', '', content).strip()

        if content:
            conv_text += f"{prefix}{content[:200]}\n"

    if not conv_text:
        return ""

    # Stage 1: Groq summarizes the whole conversation
    prompt = f"""Summarize this conversation in 2-3 sentences MAX.
Focus on: what user wants to build, key requirements mentioned.
Be ultra-concise. No filler.

{conv_text}"""

    try:
        summary = await groq_chat(
            [{"role": "user", "content": prompt}],
            model,
            temperature=0.3
        )
        if summary:
            # Stage 2: Apply shorthand
            return apply_shorthand(summary.strip())
    except Exception as e:
        logger.debug(f"Conversation summary failed: {e}")

    # Fallback: basic extraction
    return apply_shorthand(conv_text[:200])


# ============ URL/GITHUB INSPIRATION FETCHING ============
# Fetch and analyze URLs and GitHub repos for project inspiration

import aiohttp

async def fetch_url_content(url: str, max_chars: int = 5000) -> str:
    """Fetch text content from a URL"""
    try:
        async with aiohttp.ClientSession() as client:
            async with client.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Strip HTML tags for plain text
                    import re
                    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text[:max_chars]
    except Exception as e:
        logger.debug(f"URL fetch failed: {e}")
    return ""


async def fetch_github_repo_info(repo_url: str) -> Dict:
    """Extract info from a GitHub repo URL"""
    # Parse owner/repo from URL
    import re
    match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
    if not match:
        return {}

    owner, repo = match.groups()
    repo = repo.split('?')[0].split('#')[0].rstrip('/')  # Clean URL params

    info = {"owner": owner, "repo": repo, "url": repo_url}

    try:
        async with aiohttp.ClientSession() as client:
            # Try to fetch README
            readme_urls = [
                f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
                f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
            ]
            for readme_url in readme_urls:
                async with client.get(readme_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        info["readme"] = (await resp.text())[:3000]
                        break

            # Try GitHub API for repo info
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            async with client.get(api_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    info["description"] = data.get("description", "")
                    info["language"] = data.get("language", "")
                    info["stars"] = data.get("stargazers_count", 0)
                    info["topics"] = data.get("topics", [])
    except Exception as e:
        logger.debug(f"GitHub fetch failed: {e}")

    return info


async def analyze_inspiration_url(url: str, project_context: str, model: str = "llama-3.3-70b-versatile") -> Dict:
    """Analyze a URL for project inspiration"""
    is_github = "github.com" in url.lower()

    if is_github:
        # GitHub repo analysis
        repo_info = await fetch_github_repo_info(url)
        if not repo_info:
            return {"url": url, "error": "Could not fetch GitHub repo"}

        prompt = f"""Analyze this GitHub repo as inspiration for user's project.

REPO: {repo_info.get('owner')}/{repo_info.get('repo')}
Description: {repo_info.get('description', 'N/A')}
Language: {repo_info.get('language', 'N/A')}
Stars: {repo_info.get('stars', 0)}
Topics: {', '.join(repo_info.get('topics', []))}

README EXCERPT:
{repo_info.get('readme', 'N/A')[:1500]}

USER'S PROJECT CONTEXT: {project_context[:300]}

Provide a SHORT analysis (3-5 bullet points):
- What this repo does
- Key features/patterns that could inspire their project
- Tech stack / architecture worth noting
- Any specific code patterns to consider"""

        content = repo_info.get('readme', '')
    else:
        # Regular website analysis
        content = await fetch_url_content(url)
        if not content:
            return {"url": url, "error": "Could not fetch URL content"}

        prompt = f"""Analyze this website as inspiration for user's project.

URL: {url}
CONTENT EXCERPT:
{content[:2000]}

USER'S PROJECT CONTEXT: {project_context[:300]}

Provide a SHORT analysis (3-5 bullet points):
- What this site/app does
- Design elements or features worth noting
- UX patterns that could inspire their project
- Any specific functionality to consider"""

    try:
        analysis = await groq_chat(
            [{"role": "user", "content": prompt}],
            model,
            temperature=0.5,
            max_tokens=500
        )

        # Compress the analysis
        compressed = apply_shorthand(analysis) if analysis else ""

        return {
            "url": url,
            "type": "github" if is_github else "website",
            "analysis": compressed,
            "raw_content": content[:500] if not is_github else repo_info.get('description', '')
        }
    except Exception as e:
        logger.error(f"URL analysis failed: {e}")
        return {"url": url, "error": str(e)}


async def get_ralph_url_comment(url_analysis: Dict, session: Dict) -> str:
    """Generate Ralph's comment about a URL the user shared"""
    url = url_analysis.get("url", "")
    analysis = url_analysis.get("analysis", "")[:300]
    url_type = url_analysis.get("type", "website")

    project_name = session.get("project_name", "")

    prompt = f"""Ralph (confused but helpful office boss) comments on a {'GitHub repo' if url_type == 'github' else 'website'} the user shared for inspiration.

URL: {url}
What Ralph found: {analysis}
User's project: {project_name or 'Still figuring out'}

Write 2-3 sentences as Ralph noticing specific things that could help with their project.
- Point out features, patterns, or ideas you noticed
- Connect them to what they're building
- Be enthusiastic but slightly confused (Ralph's style)

Keep it SHORT and specific."""

    model = session.get("model") or "llama-3.3-70b-versatile"
    response = await groq_chat([{"role": "user", "content": prompt}], model, temperature=0.8)
    return response if response else None


# ============ EMOJI REACTION SYSTEM ============
# Users can react to any bot message with emoji to give feedback

# Map emoji reactions to sentiment categories with descriptions
EMOJI_SENTIMENT = {
    # === LOVE IT / GREAT IDEA ===
    "👍": "positive", "❤️": "love", "🔥": "love", "💯": "love",
    "😍": "love", "🥰": "love", "💖": "love", "💕": "love",
    "🎉": "positive", "⭐": "positive", "✨": "positive", "🌟": "positive",
    "👏": "positive", "🙌": "positive", "💪": "positive", "🚀": "positive",
    "✅": "positive", "🎯": "positive", "💎": "love", "🏆": "love",
    "👑": "love", "🙏": "positive", "😊": "positive", "🤩": "love",

    # === INTERESTING / THINKING ===
    "💡": "insight", "🤔": "thinking", "👀": "interested", "🧐": "thinking",
    "📝": "noted", "🔍": "interested", "💭": "thinking", "🎓": "insight",

    # === MEH / NEUTRAL ===
    "👌": "neutral", "🤷": "neutral", "😐": "neutral", "😶": "neutral",
    "🆗": "neutral", "➡️": "skip", "⏭️": "skip",

    # === DON'T LIKE / BAD IDEA ===
    "👎": "negative", "😢": "sad", "😕": "negative", "😒": "negative",
    "🙄": "negative", "😤": "negative", "😑": "negative", "🚫": "negative",
    "⛔": "negative", "❌": "negative", "✋": "stop", "🛑": "stop",

    # === HATE IT / TERRIBLE ===
    "😡": "hate", "🤮": "hate", "💩": "hate", "🗑️": "hate",
    "😠": "hate", "👊": "hate", "💀": "hate", "☠️": "hate",

    # === FUN / ENGAGEMENT ===
    "😂": "funny", "🤣": "funny", "😆": "funny", "😅": "amused",
    "🤯": "amazed", "😮": "surprised", "🥳": "celebration", "🎊": "celebration",
    "😱": "shocked", "🤭": "amused", "😏": "smirk", "🤓": "nerdy",

    # === CONFUSED / NEED MORE INFO ===
    "❓": "confused", "🤷‍♂️": "confused", "🤷‍♀️": "confused", "😵": "confused",
    "🫤": "unsure", "😬": "unsure",
}

# Human-readable legend for emoji reactions
EMOJI_LEGEND = """
*Available Emoji Reactions* 📱
_Long-press any message to react!_

*Love it / Great idea:*
👍 ❤️ 🔥 💯 😍 🎉 ⭐ ✨ 🚀 ✅ 🎯 💎 🏆

*Interesting / Let me think:*
💡 🤔 👀 🧐 📝 💭

*Meh / Neutral:*
👌 🤷 😐 ➡️ ⏭️

*Don't like this:*
👎 😕 😒 🙄 🚫 ❌ ✋

*Hate it / Terrible idea:*
😡 🤮 💩 🗑️ 💀

*Fun reactions:*
😂 🤣 🤯 🥳 😱
"""

# Short descriptions for Ralph to reference
EMOJI_MEANING = {
    "love": "loves this idea",
    "positive": "likes this",
    "insight": "finds this interesting",
    "thinking": "is thinking about this",
    "interested": "wants to know more",
    "noted": "noted this",
    "neutral": "is neutral",
    "skip": "wants to skip this",
    "negative": "doesn't like this",
    "sad": "is sad about this",
    "stop": "wants to stop",
    "hate": "really dislikes this",
    "funny": "finds this funny",
    "amused": "is amused",
    "amazed": "is amazed",
    "surprised": "is surprised",
    "celebration": "is celebrating",
    "shocked": "is shocked",
    "confused": "is confused",
    "unsure": "is unsure about this",
}

# Track bot messages and their context (keyed by message_id)
# Format: {message_id: {"type": "prd_block|analyst|ralph|suggestion", "data": {...}, "user_id": int}}
bot_message_context: Dict[int, dict] = {}

# Reaction log for training/analytics
reaction_log: List[dict] = []


def track_bot_message(message_id: int, user_id: int, msg_type: str, data: dict = None):
    """Track a bot message for reaction handling"""
    bot_message_context[message_id] = {
        "type": msg_type,
        "data": data or {},
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
    # Keep only last 1000 messages to prevent memory bloat
    if len(bot_message_context) > 1000:
        oldest_keys = sorted(bot_message_context.keys())[:100]
        for k in oldest_keys:
            del bot_message_context[k]


def get_sentiment_category(emoji: str) -> str:
    """Get sentiment category for an emoji"""
    return EMOJI_SENTIMENT.get(emoji, "unknown")


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle emoji reactions to bot messages"""
    try:
        reaction = update.message_reaction
        if not reaction:
            return

        message_id = reaction.message_id
        user_id = reaction.user.id if reaction.user else None
        chat_id = reaction.chat.id

        # Get the new reactions (what was just added)
        new_reactions = reaction.new_reaction
        if not new_reactions:
            return

        # Get the emoji(s) from the reaction
        for react in new_reactions:
            emoji = react.emoji if hasattr(react, 'emoji') else str(react)
            sentiment = get_sentiment_category(emoji)

            # Log the reaction
            log_entry = {
                "message_id": message_id,
                "user_id": user_id,
                "chat_id": chat_id,
                "emoji": emoji,
                "sentiment": sentiment,
                "timestamp": datetime.now().isoformat(),
            }

            # Check if we have context for this message
            if message_id in bot_message_context:
                msg_context = bot_message_context[message_id]
                log_entry["message_type"] = msg_context["type"]
                log_entry["message_data"] = msg_context["data"]

                # Handle specific message types
                if msg_context["type"] == "prd_block":
                    # User reacted to a PRD block suggestion
                    await handle_prd_reaction(user_id, msg_context["data"], sentiment, emoji, context, chat_id)

                elif msg_context["type"] == "analyst":
                    # User reacted to Stool or Gomer
                    await handle_analyst_reaction(user_id, msg_context["data"], sentiment, emoji)

                elif msg_context["type"] == "suggestion":
                    # User reacted to a rapid suggestion
                    await handle_suggestion_reaction(user_id, msg_context["data"], sentiment, emoji)

            # Store in log
            reaction_log.append(log_entry)

            # Keep log manageable
            if len(reaction_log) > 10000:
                reaction_log.pop(0)

            logger.info(f"Reaction: {emoji} ({sentiment}) on message {message_id}")

    except Exception as e:
        logger.error(f"Reaction handler error: {e}")


async def handle_prd_reaction(user_id: int, block_data: dict, sentiment: str, emoji: str, context, chat_id: int):
    """Process reaction to a PRD block - Ralph responds!"""
    session = get_session(user_id)
    title = block_data.get('title', 'that task')

    # Ralph's responses based on sentiment
    ralph_responses = {
        "love": [
            f"*squints at screen* Oh! {emoji} You REALLY like '{title}'! Noted, boss!",
            f"{emoji} Ooh, you love that one! *scribbles excitedly* Got it!",
            f"*Ralph's eyes light up* {emoji} = big yes! Adding to the good pile!",
        ],
        "positive": [
            f"{emoji} *nods* Alright, you like '{title}'! I'll remember that!",
            f"*thumbs up back* {emoji} Cool cool cool, keeping that one!",
            f"{emoji} Nice! *checks box* '{title}' is a keeper!",
        ],
        "insight": [
            f"{emoji} Ooh, you're thinkin about that one... *waits patiently*",
            f"*sees {emoji}* Hmm, interesting huh? Take your time, boss!",
        ],
        "negative": [
            f"{emoji} *scratches head* Okay okay, you don't like '{title}'... got it!",
            f"*sees {emoji}* Ohhh, that's a no? *crosses it out gently*",
            f"{emoji} Fair enough boss, '{title}' wasn't great. Moving on!",
        ],
        "hate": [
            f"{emoji} *gulps* Yikes! You REALLY don't like that one! Gone!",
            f"*sees {emoji}* OH NO! *frantically erases* Sorry boss, bad idea!",
            f"{emoji} Oof, that bad huh? *throws paper away* FORGET I said it!",
        ],
        "confused": [
            f"{emoji} *tilts head* You confused about '{title}'? Me too sometimes...",
            f"*sees {emoji}* Want me to explain that one more, boss?",
        ],
        "funny": [
            f"{emoji} Hehe, glad that made you laugh! *giggles*",
            f"*sees {emoji}* At least it's entertainin, right boss?",
        ],
    }

    # Get appropriate response
    responses = ralph_responses.get(sentiment, ralph_responses.get("positive"))
    response = random.choice(responses)

    # Store the feedback
    if sentiment in ["positive", "love"]:
        if block_data not in session.get("approved_prd_blocks", []):
            session.setdefault("approved_prd_blocks", []).append(block_data)
    elif sentiment in ["negative", "hate", "stop"]:
        if block_data not in session.get("rejected_prd_blocks", []):
            session.setdefault("rejected_prd_blocks", []).append(block_data)

    # Ralph responds!
    await context.bot.send_message(
        chat_id=chat_id,
        text=response,
        parse_mode="Markdown"
    )


async def handle_analyst_reaction(user_id: int, analyst_data: dict, sentiment: str, emoji: str):
    """Process reaction to analyst debate messages"""
    session = get_session(user_id)
    analyst = analyst_data.get("analyst", "Unknown")

    # Store feedback about which analyst resonated
    session.setdefault("analyst_feedback", []).append({
        "analyst": analyst,
        "sentiment": sentiment,
        "emoji": emoji,
        "message": analyst_data.get("message", "")[:100]
    })
    logger.info(f"Analyst feedback: {analyst} got {emoji} ({sentiment})")


async def handle_suggestion_reaction(user_id: int, suggestion_data: dict, sentiment: str, emoji: str):
    """Process reaction to rapid suggestions"""
    session = get_session(user_id)

    if sentiment in ["positive", "love", "insight"]:
        session.setdefault("approved_features", []).append(suggestion_data.get("text", ""))
    elif sentiment in ["negative", "hate"]:
        session.setdefault("rejected_features", []).append(suggestion_data.get("text", ""))


# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# User sessions (in-memory, backed by disk)
user_sessions: Dict[int, dict] = {}


def get_session(user_id: int) -> dict:
    """Get or create user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = create_fresh_session()
    return user_sessions[user_id]


def create_fresh_session() -> dict:
    """Create a completely fresh session with all fields reset"""
    return {
        "session_id": None,
        "recipe_id": None,  # For saved recipes
        "project_name": "",
        "project_description": "",
        "conversation": [],
        "model": "llama-3.3-70b-versatile",  # Groq's best
        "provider": "groq",  # Go with the best, forget the rest
        "groq_api_key": GROQ_API_KEY,  # User can override
        "phase": "idle",  # idle, chatting, cooking
        "message_count": 0,  # For GIF timing
        "gifs_enabled": True,  # User can toggle
        "waiting_for": None,
        # Analysis mode
        "analyzing": False,
        "analysis_task": None,  # asyncio task for the debate
        "analysis_context": [],  # Debate messages for context
        "analysis_count": 0,  # Number of exchanges
        # Feedback/preferences during discovery
        "preferences": [],  # List of {feature, liked: bool, context}
        "pending_feedback": None,  # Current feature awaiting feedback
        # Snippet suggestions (from recipe book)
        "liked_snippets": [],  # Snippets to include in context
        "hated_snippets": [],  # Patterns to actively AVOID
        "suggestion_queue": [],  # Current suggestions being reviewed
        "suggestion_index": 0,  # Current position in suggestion review
        # PRD block system
        "prd_blocks": [],
        "prd_index": 0,
        "approved_prd_blocks": [],
        "rejected_prd_blocks": [],
        "hated_prd_blocks": [],
        "revising_block": None,
        # Rapid-fire features
        "rapid_suggestions": [],
        "approved_features": [],
        "rejected_features": [],
        # Visual context
        "visual_context": [],
        "pending_images": {},
    }


def reset_session(user_id: int) -> dict:
    """Completely reset a user's session - fresh start!"""
    # Cancel any running analysis task
    if user_id in user_sessions:
        old_session = user_sessions[user_id]
        if old_session.get("analysis_task"):
            try:
                old_session["analysis_task"].cancel()
            except:
                pass

    # Create completely fresh session
    user_sessions[user_id] = create_fresh_session()
    return user_sessions[user_id]


# ============ ANALYST DEBATE SYSTEM ============

ANALYST_A = {
    "name": "Stool",
    "role": "The Skeptic",
    "style": "Practical, questions everything, looks for flaws",
    "emoji": "🤔"
}

ANALYST_B = {
    "name": "Gomer",
    "role": "The Optimist",
    "style": "Sees potential, finds use cases, enthusiastic",
    "emoji": "💡"
}

ANALYST_PROMPTS = {
    "start_skeptic": """Stool (skeptic) analyzing project. 1-2 sentences MAX.
CTX: {context}
Question ONE thing: need, problem, or gap. Direct, punchy.""",

    "respond_optimist": """Gomer (optimist) responds. 1-2 sentences MAX.
CTX: {context}
STOOL: {last_message}
Counter with ONE use case or opportunity. Punchy.""",

    "respond_skeptic": """Stool (skeptic) responds. 1-2 sentences MAX.
CTX: {context}
GOMER: {last_message}
ONE concern or edge case. Acknowledge good points briefly.""",

    "final_summary": """Summarize debate in 2 sentences max.
CTX: {context}
DEBATE: {debate}
Format: [CONCERN] X | [OPP] Y | [REC] build/modify/reconsider"""
}


async def run_analyst_debate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    chat_id: int,
    continue_from: int = 0  # For continuing batches
):
    """Run the analyst debate loop - pauses every 10 exchanges for user decision"""
    session = get_session(user_id)
    model = session.get("model") or "llama3.1:8b"
    provider = session.get("provider", "local")

    # If run_all_mode is set, use large batch to avoid pauses
    BATCH_SIZE = 50 if session.get("run_all_mode") else 10
    MAX_TOTAL = 50   # Maximum total exchanges

    # Clear run_all_mode after reading it
    session["run_all_mode"] = False

    # Get project context
    project_context = f"Project: {session.get('project_name', 'Unnamed')}\n"
    project_context += f"Description: {session.get('project_description', 'No description')}\n"
    if session["conversation"]:
        recent = session["conversation"][-5:]
        project_context += "Recent discussion:\n"
        for msg in recent:
            project_context += f"- {msg['role']}: {msg['content'][:100]}...\n"

    # Load existing debate if continuing
    debate_messages = session.get("debate_messages", []) if continue_from > 0 else []
    exchange_count = continue_from
    batch_count = 0  # Count within this batch

    try:
        # Initial message (only on first batch)
        if continue_from == 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "🔍 *Analysis Mode Started*\n\n"
                    "_Analysts will debate in batches of 10..._\n"
                    "_React with emoji to show what you like/dislike!_\n\n"
                    "Press 🛑 Stop Analysis anytime."
                ),
                parse_mode="Markdown",
                reply_markup=get_keyboard(True, analyzing=True)
            )
            await asyncio.sleep(2)

            # Start with skeptic
            prompt = ANALYST_PROMPTS["start_skeptic"].format(context=project_context)
            response = await groq_chat([{"role": "user", "content": prompt}], model or "llama-3.3-70b-versatile", temperature=0.8)

            if response and session.get("analyzing"):
                debate_messages.append({"analyst": "Stool", "message": response})
                msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🤔 *Stool* (The Skeptic):\n\n_{response}_",
                    parse_mode="Markdown"
                )
                track_bot_message(msg.message_id, user_id, "analyst", {"analyst": "Stool", "message": response})
                exchange_count += 1
                batch_count += 1
        else:
            # Resuming - let user know
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔄 *Continuing analysis* (exchange {continue_from + 1}+)...",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1)

        # Debate loop - runs until batch complete or stopped
        current_speaker = "optimist" if (exchange_count % 2 == 1) else "skeptic"

        while session.get("analyzing") and exchange_count < MAX_TOTAL and batch_count < BATCH_SIZE:
            await asyncio.sleep(5)  # 5 second pause between exchanges

            if not session.get("analyzing"):
                break

            last_message = debate_messages[-1]["message"] if debate_messages else ""

            if current_speaker == "optimist":
                prompt = ANALYST_PROMPTS["respond_optimist"].format(
                    context=project_context,
                    last_message=last_message
                )
                analyst = ANALYST_B
                current_speaker = "skeptic"
            else:
                prompt = ANALYST_PROMPTS["respond_skeptic"].format(
                    context=project_context,
                    last_message=last_message
                )
                analyst = ANALYST_A
                current_speaker = "optimist"

            response = await groq_chat([{"role": "user", "content": prompt}], model or "llama-3.3-70b-versatile", temperature=0.8)

            if response and session.get("analyzing"):
                debate_messages.append({"analyst": analyst["name"], "message": response})
                msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{analyst['emoji']} *{analyst['name']}* ({analyst['role']}):\n\n_{response}_",
                    parse_mode="Markdown"
                )
                track_bot_message(msg.message_id, user_id, "analyst", {"analyst": analyst["name"], "message": response})
                exchange_count += 1
                batch_count += 1
            else:
                break

        # Store debate state for potential continuation
        session["debate_messages"] = debate_messages
        session["debate_exchange_count"] = exchange_count

        # Batch complete - decide what to do next
        if batch_count >= BATCH_SIZE and exchange_count < MAX_TOTAL and session.get("analyzing"):
            # Batch done but more available - pause and ask
            session["analyzing"] = False  # Pause
            session["analysis_paused"] = True
            session["analysis_task"] = None

            continue_kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("▶️ Continue (+10 more)", callback_data="analysis_continue"),
                    InlineKeyboardButton("🛑 Stop & Summarize", callback_data="analysis_finish")
                ],
                [
                    InlineKeyboardButton("⏭️ Run All Remaining", callback_data="analysis_run_all")
                ]
            ])

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⏸️ *Batch Complete!* ({exchange_count} exchanges so far)\n\n"
                    f"_React to messages above with emoji to guide analysis!_\n"
                    f"👍❤️🔥 = good ideas, 👎😡💩 = bad ideas\n\n"
                    f"What next?"
                ),
                parse_mode="Markdown",
                reply_markup=continue_kb
            )
            return  # Exit - will be resumed via callback

        # Analysis ended (stopped or max reached) - generate summary
        if debate_messages:
            await _finalize_analysis(context, chat_id, user_id, session, debate_messages,
                                    exchange_count, model, provider, project_context)

    except asyncio.CancelledError:
        if debate_messages:
            session["analysis_context"] = debate_messages
            session["conversation"].append({
                "role": "system",
                "content": f"[PARTIAL ANALYST DEBATE - {len(debate_messages)} exchanges before stopped]"
            })

    except Exception as e:
        logger.error(f"Analysis debate error: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"😅 Analysis hit a snag: {str(e)[:100]}",
            reply_markup=get_keyboard(True, analyzing=False)
        )

    finally:
        if not session.get("analysis_paused"):
            session["analyzing"] = False
            session["analysis_task"] = None


async def _finalize_analysis(context, chat_id, user_id, session, debate_messages,
                            exchange_count, model, provider, project_context):
    """Generate summary and finalize analysis"""
    debate_text = "\n".join([f"{m['analyst']}: {m['message']}" for m in debate_messages])

    summary_prompt = ANALYST_PROMPTS["final_summary"].format(
        context=project_context,
        debate=debate_text
    )

    summary = await groq_chat([{"role": "user", "content": summary_prompt}], model or "llama-3.3-70b-versatile", temperature=0.5)

    # Store analysis in session for PRD context WITH MODEL INFO
    session["analysis_context"] = {
        "messages": debate_messages,
        "model": model,
        "provider": provider,
        "exchange_count": exchange_count,
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    }
    session["analysis_count"] = exchange_count

    # Clear batch state
    session["debate_messages"] = []
    session["debate_exchange_count"] = 0
    session["analysis_paused"] = False

    # Add summary to conversation as context
    session["conversation"].append({
        "role": "system",
        "content": f"[ANALYST DEBATE SUMMARY - {exchange_count} exchanges | Model: {model} ({provider})]\n{summary}"
    })

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"📊 *Analysis Complete!*\n\n"
            f"_{exchange_count} total exchanges between analysts_\n\n"
            f"**Summary:**\n{summary}\n\n"
            f"_This analysis is now part of your project context!_"
        ),
        parse_mode="Markdown",
        reply_markup=get_keyboard(True, analyzing=False)
    )

    session["analyzing"] = False
    session["analysis_task"] = None


async def start_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the analyst debate"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session["conversation"]:
        await update.message.reply_text(
            "Nothing to analyze yet!\n\n"
            "Tell me about your project first, then I'll get the analysts debating.",
            reply_markup=get_keyboard(False)
        )
        return

    if session.get("analyzing"):
        await update.message.reply_text("Analysis already running! Press 🛑 to stop.")
        return

    session["analyzing"] = True
    chat_id = update.effective_chat.id

    # Start the debate as a background task
    task = asyncio.create_task(run_analyst_debate(update, context, user_id, chat_id))
    session["analysis_task"] = task


async def stop_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the analyst debate"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    if session.get("analysis_task"):
        session["analysis_task"].cancel()

    session["analyzing"] = False

    analysis_count = len(session.get("analysis_context", []))

    await update.message.reply_text(
        f"🛑 *Analysis Stopped*\n\n"
        f"We've been doing a lot of talking! ({analysis_count} exchanges)\n"
        f"I think that's going to help your builder bot big time when he's looking at this conversation.\n\n"
        f"_Context saved!_",
        parse_mode="Markdown",
        reply_markup=get_keyboard(True, analyzing=False)
    )


# ============ QR CODE GENERATION & SCANNING ============

def generate_recipe_qr(recipe_id: str) -> str:
    """Generate QR code for a recipe, return path to image"""
    try:
        import qrcode
        url = f"https://ralphmode.com/r/{recipe_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to temp file
        path = f"/tmp/recipe_qr_{recipe_id}.png"
        img.save(path)
        return path
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        return ""


def scan_qr_from_image(image_path: str) -> Optional[str]:
    """Scan QR code from image, return recipe ID if found"""
    try:
        from pyzbar import pyzbar
        from PIL import Image

        img = Image.open(image_path)
        barcodes = pyzbar.decode(img)

        for barcode in barcodes:
            data = barcode.data.decode('utf-8')
            # Check if it's a Ralph recipe URL
            if 'ralphmode.com/r/' in data:
                recipe_id = data.split('/r/')[-1].split('?')[0]
                return recipe_id
            # Also check for raw recipe IDs
            if data.startswith('RALPH-'):
                return data
        return None
    except ImportError:
        logger.error("pyzbar not installed - run: pip install pyzbar")
        return None
    except Exception as e:
        logger.error(f"QR scan error: {e}")
        return None


def generate_recipe_id() -> str:
    """Generate unique recipe ID"""
    import uuid
    return f"RALPH-{uuid.uuid4().hex[:8].upper()}"


# ============ GROQ API INTEGRATION ============

async def list_groq_models() -> List[Dict]:
    """List available Groq models with info - sorted by quality"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GROQ_API_BASE}/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = []
                    for m in data.get("data", []):
                        model_id = m.get("id", "")
                        # Skip non-chat models (whisper, guard, etc.)
                        if any(x in model_id.lower() for x in ["whisper", "guard", "prompt-guard", "safeguard", "orpheus"]):
                            continue
                        quality = GROQ_MODEL_QUALITY.get(model_id, 1)
                        models.append({
                            "id": model_id,
                            "name": model_id.replace("-", " ").title(),
                            "context": m.get("context_window", 8192),
                            "owned_by": m.get("owned_by", "groq"),
                            "quality": quality
                        })
                    # Sort by quality (highest first), then by name
                    return sorted(models, key=lambda x: (-x["quality"], x["name"]))
                else:
                    logger.error(f"Groq models error: {resp.status}")
    except Exception as e:
        logger.error(f"Groq models list error: {e}")
    return []


async def groq_chat(messages: List[Dict], model: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Chat with Groq API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GROQ_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=aiohttp.ClientTimeout(total=120)  # Increased for longer responses
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    body = await resp.text()
                    logger.error(f"Groq chat error {resp.status}: {body[:200]}")
    except Exception as e:
        logger.error(f"Groq chat error: {e}")
    return ""


# ============ OLLAMA API INTEGRATION (LOCAL AI) ============

async def ollama_chat(messages: List[Dict], model: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Chat with local Ollama API"""
    try:
        async with aiohttp.ClientSession() as session:
            # Convert messages to Ollama format
            ollama_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

            async with session.post(
                f"{OLLAMA_API_BASE}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": ollama_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=aiohttp.ClientTimeout(total=300)  # Local models can be slower
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    body = await resp.text()
                    logger.error(f"Ollama chat error {resp.status}: {body[:200]}")
    except aiohttp.ClientError as e:
        logger.error(f"Ollama connection error: {e}")
    except Exception as e:
        logger.error(f"Ollama chat error: {e}")
    return ""


async def list_ollama_models() -> List[Dict]:
    """List available local Ollama models"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_API_BASE}/v1/models",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = []
                    for m in data.get("data", []):
                        model_id = m.get("id", "")
                        # Size info (approximate based on model name)
                        size_category = 3  # Default
                        if any(x in model_id.lower() for x in ["3b", "tiny", "gemma:2b"]):
                            size_category = 1
                        elif any(x in model_id.lower() for x in ["7b", "8b", "mistral:7b"]):
                            size_category = 2
                        elif any(x in model_id.lower() for x in ["14b", "70b"]):
                            size_category = 3

                        # Clean up model name
                        name = model_id.replace(":", " ").replace("_", " ").title()

                        models.append({
                            "id": model_id,
                            "name": name,
                            "context": m.get("context_length", 4096),
                            "owned_by": "ollama",
                            "quality": size_category,
                            "size": "Small" if size_category == 1 else "Medium" if size_category == 2 else "Large"
                        })

                    # Sort: small models first (for local AI preference), then by name
                    return sorted(models, key=lambda x: (x["quality"], x["name"]))
                else:
                    logger.error(f"Ollama models error: {resp.status}")
    except aiohttp.ClientError:
        logger.warning("Ollama not running - local models unavailable")
    except Exception as e:
        logger.error(f"Ollama models list error: {e}")
    return []


# Model info URLs (updated 2025)
GROQ_MODEL_INFO = {
    # Latest Llama 4 (Preview - top tier)
    "meta-llama/llama-4-maverick-17b-128e-instruct": "https://console.groq.com/docs/models",
    "meta-llama/llama-4-scout-17b-16e-instruct": "https://console.groq.com/docs/models",
    # Compound/Agentic (Production)
    "groq/compound": "https://console.groq.com/docs/models",
    "groq/compound-mini": "https://console.groq.com/docs/models",
    # Kimi K2 (262k context!)
    "moonshotai/kimi-k2-instruct-0905": "https://console.groq.com/docs/models",
    # GPT-OSS (OpenAI open source)
    "openai/gpt-oss-120b": "https://console.groq.com/docs/models",
    "openai/gpt-oss-20b": "https://console.groq.com/docs/models",
    # Qwen 3
    "qwen/qwen3-32b": "https://console.groq.com/docs/models",
    # Production Llama (stable)
    "llama-3.3-70b-versatile": "https://console.groq.com/docs/models#llama-33-70b-versatile",
    "llama-3.1-8b-instant": "https://console.groq.com/docs/models#llama-31-8b",
    # Audio
    "whisper-large-v3": "https://console.groq.com/docs/models",
    "whisper-large-v3-turbo": "https://console.groq.com/docs/models",
}

# Model quality tiers for Groq (higher = better for complex tasks)
GROQ_MODEL_QUALITY = {
    "meta-llama/llama-4-maverick-17b-128e-instruct": 5,  # Top tier - 400B params
    "openai/gpt-oss-120b": 5,                             # Top tier - 120B params
    "moonshotai/kimi-k2-instruct-0905": 4,               # Great - 262k context
    "meta-llama/llama-4-scout-17b-16e-instruct": 4,      # Great - 109B MoE
    "groq/compound": 4,                                   # Agentic AI system
    "qwen/qwen3-32b": 4,                                 # Great reasoning
    "llama-3.3-70b-versatile": 3,                        # Solid production
    "openai/gpt-oss-20b": 3,                             # Good quality
    "groq/compound-mini": 3,                             # Fast agentic
    "llama-3.1-8b-instant": 2,                           # Fast, basic
}

# Default high-quality model for Groq
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"  # Stable production default

# Vision-capable models (for photo/document analysis)
GROQ_VISION_MODELS = [
    "meta-llama/llama-4-maverick-17b-128e-instruct",  # Best - 128 experts, multimodal
    "meta-llama/llama-4-scout-17b-16e-instruct",      # Good - 16 experts, multimodal
]
DEFAULT_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # Fast + capable

# Context extraction prompts for different media types
VISION_PROMPTS = {
    "design": """Analyze this design/UI image in detail. Extract:
1. **Colors**: Primary, secondary, accent colors (hex codes if visible)
2. **Typography**: Font styles, sizes, hierarchy
3. **Layout**: Grid system, spacing, alignment patterns
4. **Components**: Buttons, forms, cards, navigation elements
5. **Style**: Modern/vintage, minimal/detailed, mood/tone
6. **Accessibility**: Contrast issues, readability concerns
7. **Unique Elements**: Anything distinctive or noteworthy

Format as structured JSON with these keys: colors, typography, layout, components, style, accessibility, unique_elements, overall_impression""",

    "document": """Analyze this document thoroughly. Extract:
1. **Type**: What kind of document (form, contract, spec, wireframe, etc.)
2. **Content Summary**: Key points and main topics
3. **Structure**: Sections, headings, organization
4. **Key Data**: Important numbers, dates, names, requirements
5. **Action Items**: Any tasks, deadlines, or deliverables mentioned
6. **Technical Terms**: Domain-specific vocabulary used

Format as structured JSON with these keys: document_type, summary, structure, key_data, action_items, technical_terms""",

    "screenshot": """Analyze this screenshot in detail. Extract:
1. **Platform**: Web, mobile app, desktop app, OS
2. **UI Elements**: Buttons, menus, forms, content areas
3. **Functionality**: What feature/page is this showing
4. **Text Content**: All visible text (especially important info)
5. **State**: Loading, error, success, empty state, etc.
6. **Design Patterns**: Common UI patterns being used
7. **Issues**: Any visible bugs, UX problems, or improvements needed

Format as structured JSON with these keys: platform, ui_elements, functionality, text_content, state, design_patterns, issues""",

    "photo": """Analyze this photo in detail. Extract:
1. **Subjects**: People, objects, animals present
2. **Setting**: Location, environment, context
3. **Text**: Any text visible in the image
4. **Colors/Mood**: Dominant colors, lighting, atmosphere
5. **Details**: Notable or interesting elements
6. **Context Clues**: What story does this image tell?

Format as structured JSON with these keys: subjects, setting, visible_text, colors_mood, details, context_clues""",

    "general": """Analyze this image thoroughly in the context of a software project. Extract:
1. **What it shows**: Primary subject matter
2. **Relevant details**: Anything useful for building software
3. **Text content**: Any visible text
4. **Design elements**: Colors, styles, patterns
5. **Technical insights**: What this tells us about requirements
6. **Questions**: What clarifications might help?

Format as structured JSON with these keys: primary_subject, relevant_details, text_content, design_elements, technical_insights, questions"""
}


async def fetch_groq_model_info_from_web() -> Dict:
    """
    Fetch latest Groq model info by scraping their docs.
    Uses the official API for model list, enriches with web data.
    Returns dict of model_id -> {description, tier, context}
    """
    import time
    global GROQ_MODEL_CACHE

    # Check cache
    if GROQ_MODEL_CACHE["last_fetch"]:
        age = time.time() - GROQ_MODEL_CACHE["last_fetch"]
        if age < GROQ_CACHE_TTL and GROQ_MODEL_CACHE["models"]:
            logger.info("Using cached Groq model info")
            return GROQ_MODEL_CACHE["models"]

    logger.info("Fetching fresh Groq model info...")
    model_info = {}

    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Get official model list from API (source of truth)
            async with session.get(
                f"{GROQ_API_BASE}/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for m in data.get("data", []):
                        model_id = m.get("id", "")
                        if not model_id:
                            continue

                        # Get context window from API
                        context = m.get("context_window", 8192)

                        # Determine quality tier based on model characteristics
                        tier = 1  # Default: basic

                        # Check for high-tier indicators
                        if "4-maverick" in model_id or "gpt-oss-120b" in model_id:
                            tier = 5  # Top tier (massive models)
                        elif "4-scout" in model_id or "kimi-k2" in model_id or "compound" in model_id.lower():
                            tier = 4  # Great
                        elif "70b" in model_id or "qwen3-32b" in model_id or "gpt-oss-20b" in model_id:
                            tier = 3  # Solid
                        elif "8b" in model_id or "7b" in model_id:
                            tier = 2  # Fast but basic

                        # Skip non-chat models
                        if any(x in model_id.lower() for x in ["whisper", "guard", "safeguard", "orpheus", "embed"]):
                            continue

                        # Build description based on model name
                        desc = ""
                        if "llama-4" in model_id.lower():
                            desc = "Latest Llama 4 model (Preview)"
                        elif "compound" in model_id.lower():
                            desc = "Groq Compound AI (Agentic)"
                        elif "kimi" in model_id.lower():
                            desc = f"Kimi K2 - {context//1000}k context"
                        elif "gpt-oss" in model_id.lower():
                            desc = "OpenAI Open Source Model"
                        elif "qwen" in model_id.lower():
                            desc = "Qwen 3 - Great reasoning"
                        elif "llama-3.3" in model_id:
                            desc = "Llama 3.3 70B - Production stable"
                        elif "llama-3.1" in model_id:
                            desc = "Llama 3.1 - Fast inference"
                        else:
                            desc = m.get("owned_by", "Groq hosted")

                        model_info[model_id] = {
                            "description": desc,
                            "tier": tier,
                            "context": context,
                            "owned_by": m.get("owned_by", "unknown")
                        }
                else:
                    logger.warning(f"Groq API returned {resp.status}, using cached/default info")

    except Exception as e:
        logger.error(f"Error fetching Groq model info: {e}")

    # Update cache
    if model_info:
        GROQ_MODEL_CACHE["last_fetch"] = time.time()
        GROQ_MODEL_CACHE["models"] = model_info

        # Update quality tiers for list_groq_models
        for model_id, info in model_info.items():
            GROQ_MODEL_QUALITY[model_id] = info["tier"]

        logger.info(f"Cached {len(model_info)} Groq models")

    return model_info


async def get_groq_model_description(model_id: str) -> str:
    """Get description for a specific Groq model"""
    info = await fetch_groq_model_info_from_web()
    if model_id in info:
        return info[model_id].get("description", "Groq cloud model")
    return "Groq cloud model - Fast inference"


async def get_best_groq_model() -> str:
    """Get the best available Groq model (highest tier that's available)"""
    info = await fetch_groq_model_info_from_web()
    if not info:
        return DEFAULT_GROQ_MODEL

    # Sort by tier (highest first)
    sorted_models = sorted(info.items(), key=lambda x: -x[1].get("tier", 0))
    if sorted_models:
        return sorted_models[0][0]
    return DEFAULT_GROQ_MODEL


# ============ VISION / IMAGE ANALYSIS ============

import base64
from io import BytesIO

async def analyze_image_with_groq(
    image_data: bytes,
    prompt: str,
    model: str = None,
    project_context: str = ""
) -> Dict:
    """
    Analyze an image using Groq's vision-capable models.
    Returns structured context extracted from the image.
    """
    if not model:
        model = DEFAULT_VISION_MODEL

    # Encode image to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')

    # Determine image type from magic bytes
    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
        mime_type = "image/png"
    elif image_data[:2] == b'\xff\xd8':
        mime_type = "image/jpeg"
    elif image_data[:4] == b'GIF8':
        mime_type = "image/gif"
    elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"  # Default fallback

    # Add project context to prompt if available
    full_prompt = prompt
    if project_context:
        full_prompt = f"""PROJECT CONTEXT: {project_context}

{prompt}

Also note how this image relates to the project described above."""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GROQ_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": full_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.3,  # Lower for more factual analysis
                    "max_tokens": 2048
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                    # Try to parse as JSON for structured output
                    try:
                        # Find JSON in response
                        import re
                        json_match = re.search(r'\{[\s\S]*\}', response_text)
                        if json_match:
                            return {
                                "success": True,
                                "raw_analysis": response_text,
                                "structured": json.loads(json_match.group()),
                                "model_used": model
                            }
                    except:
                        pass

                    return {
                        "success": True,
                        "raw_analysis": response_text,
                        "structured": None,
                        "model_used": model
                    }
                else:
                    body = await resp.text()
                    logger.error(f"Vision API error {resp.status}: {body[:200]}")
                    return {"success": False, "error": f"API error: {resp.status}"}
    except Exception as e:
        logger.error(f"Vision analysis error: {e}")
        return {"success": False, "error": str(e)}


def detect_image_type(image_data: bytes, filename: str = "", caption: str = "") -> str:
    """
    Detect what type of image this is to select the right analysis prompt.
    Returns: 'design', 'document', 'screenshot', 'photo', or 'general'
    """
    filename_lower = filename.lower() if filename else ""
    caption_lower = caption.lower() if caption else ""

    # Check filename hints
    if any(x in filename_lower for x in ['design', 'ui', 'ux', 'mockup', 'wireframe', 'figma', 'sketch']):
        return 'design'
    if any(x in filename_lower for x in ['doc', 'pdf', 'contract', 'spec', 'requirement']):
        return 'document'
    if any(x in filename_lower for x in ['screenshot', 'screen', 'capture', 'snap']):
        return 'screenshot'

    # Check caption hints
    if any(x in caption_lower for x in ['design', 'ui', 'layout', 'mockup', 'wireframe']):
        return 'design'
    if any(x in caption_lower for x in ['document', 'pdf', 'contract', 'spec', 'form']):
        return 'document'
    if any(x in caption_lower for x in ['screenshot', 'screen', 'app', 'website', 'page']):
        return 'screenshot'
    if any(x in caption_lower for x in ['photo', 'picture', 'image of']):
        return 'photo'

    # Check image characteristics (basic heuristics)
    # Screenshots often have specific dimensions or are PNG
    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
        # PNG images are often screenshots or designs
        return 'screenshot'

    return 'general'


async def extract_image_context(
    image_data: bytes,
    filename: str = "",
    caption: str = "",
    project_context: str = "",
    custom_prompt: str = None
) -> Dict:
    """
    Extract rich context from an image for project discovery.
    This is the main entry point for image analysis.

    Returns a dict with:
    - type: detected image type
    - analysis: raw analysis text
    - structured: parsed JSON if available
    - summary: brief human-readable summary
    - tags: list of relevant tags
    - project_relevance: how this relates to the project
    """
    # Detect image type
    img_type = detect_image_type(image_data, filename, caption)

    # Get the appropriate base prompt
    if custom_prompt:
        prompt = custom_prompt
    else:
        prompt = VISION_PROMPTS.get(img_type, VISION_PROMPTS['general'])

    # USER CAPTION-BASED FOCUS: If user says "look at this X", focus on X
    focus_additions = []

    if caption:
        caption_lower = caption.lower()
        # Detect what user is pointing at
        look_at_phrases = ['look at', 'check out', 'see this', 'this ', 'notice the', 'like this', 'like the', 'want this', 'want the', 'similar to']

        for phrase in look_at_phrases:
            if phrase in caption_lower:
                # User is pointing at something specific - make it the PRIMARY focus
                prompt += f"\n\nUSER IS SPECIFICALLY POINTING AT: \"{caption}\"\nFOCUS YOUR ANALYSIS primarily on what the user mentioned. Describe that element in detail first, then note other relevant elements."
                break

        # Extract specific elements user mentions
        elements = ['navigation', 'nav', 'header', 'footer', 'button', 'menu', 'sidebar', 'card', 'form',
                   'input', 'color', 'font', 'typography', 'layout', 'grid', 'icon', 'logo', 'image',
                   'animation', 'hover', 'style', 'design', 'flow', 'ux', 'ui']
        mentioned_elements = [e for e in elements if e in caption_lower]
        if mentioned_elements:
            focus_additions.append(f"USER MENTIONED THESE ELEMENTS: {', '.join(mentioned_elements)} - pay special attention to these")

    # CONTEXT-AWARE ANALYSIS: Tune the prompt based on what they're building
    if project_context:
        context_lower = project_context.lower()

        # Detect project type and add relevant focus
        if any(x in context_lower for x in ['website', 'web app', 'landing page', 'dashboard']):
            focus_additions.append("Focus on: layout structure, navigation patterns, color scheme, responsive hints, call-to-action placement")
        if any(x in context_lower for x in ['bot', 'telegram', 'discord', 'chat']):
            focus_additions.append("Focus on: command patterns, button layouts, message formatting, conversation flow hints")
        if any(x in context_lower for x in ['mobile', 'app', 'ios', 'android']):
            focus_additions.append("Focus on: mobile UI patterns, touch targets, navigation style, screen density")
        if any(x in context_lower for x in ['api', 'backend', 'database']):
            focus_additions.append("Focus on: data structures shown, field names, relationships, API patterns")
        if any(x in context_lower for x in ['game', 'animation']):
            focus_additions.append("Focus on: visual style, sprites, UI elements, game mechanics shown")

        prompt += f"\n\nPROJECT CONTEXT: User is building: {project_context[:200]}"

    if focus_additions:
        prompt += "\n" + "\n".join(focus_additions)

    # Always extract visible text for context
    prompt += "\n\nIMPORTANT: Extract ALL visible text (OCR) - this is critical for understanding the reference."

    # Run the analysis
    result = await analyze_image_with_groq(
        image_data,
        prompt,
        project_context=project_context
    )

    if not result.get("success"):
        return {
            "type": img_type,
            "success": False,
            "error": result.get("error", "Unknown error")
        }

    # Build rich context object
    context = {
        "type": img_type,
        "success": True,
        "filename": filename,
        "caption": caption,
        "analysis": result.get("raw_analysis", ""),
        "structured": result.get("structured"),
        "model_used": result.get("model_used"),
        "timestamp": datetime.now().isoformat(),
    }

    # Generate tags from the analysis
    tags = [img_type]
    if result.get("structured"):
        struct = result["structured"]
        # Add tags based on structured data
        if "colors" in struct:
            tags.append("has_colors")
        if "components" in struct:
            tags.append("has_ui_components")
        if "text_content" in struct or "visible_text" in struct:
            tags.append("has_text")
        if "functionality" in struct:
            tags.append("shows_functionality")

    context["tags"] = tags

    # Generate a brief summary
    analysis = result.get("raw_analysis", "")
    if len(analysis) > 200:
        context["summary"] = analysis[:200] + "..."
    else:
        context["summary"] = analysis

    return context


async def follow_up_image_analysis(
    image_data: bytes,
    previous_analysis: Dict,
    question: str,
    project_context: str = ""
) -> Dict:
    """
    Do a follow-up analysis on an image based on user's question.
    Allows re-examining the image with specific focus.
    """
    prompt = f"""Previous analysis of this image:
{previous_analysis.get('analysis', 'No previous analysis')}

User's follow-up question: {question}

Please analyze the image again with focus on answering this specific question.
Provide detailed observations relevant to what they're asking about."""

    result = await analyze_image_with_groq(
        image_data,
        prompt,
        project_context=project_context
    )

    if result.get("success"):
        # Update the previous analysis
        updated = previous_analysis.copy()
        updated["follow_ups"] = updated.get("follow_ups", [])
        updated["follow_ups"].append({
            "question": question,
            "answer": result.get("raw_analysis", ""),
            "timestamp": datetime.now().isoformat()
        })
        return updated

    return previous_analysis


async def get_ralph_image_comment(analysis_result: Dict, session: Dict) -> str:
    """
    Generate a Ralph-style comment about an analyzed image.
    Relates the image back to the project being built.
    """
    img_type = analysis_result.get("type", "general")
    summary = analysis_result.get("summary", "")
    analysis = analysis_result.get("analysis", "")[:400]

    # Get project context
    project_name = session.get("project_name", "")
    project_desc = session.get("project_description", "")[:200]

    # Build context-aware prompt
    prompt = f"""Ralph (confused but helpful office boss) comments on an image the user shared for inspiration.

IMAGE ANALYSIS:
Type: {img_type}
What Ralph sees: {analysis}

USER'S PROJECT: {project_name or 'Still figuring out'}
Description: {project_desc or 'Not defined yet'}

Write 2-3 sentences as Ralph noticing specific things in the image that could help with their project.
- Point out specific design elements, colors, layouts, or features you noticed
- Connect them to what they're building (if known)
- Be enthusiastic but slightly confused (Ralph's style)
- If no project yet, ask how they want to use this as inspiration

Keep it SHORT and specific to what you actually see."""

    model = session.get("model") or "llama-3.3-70b-versatile"
    response = await groq_chat(
        [{"role": "user", "content": prompt}],
        model,
        temperature=0.8
    )

    return response if response else None


async def handle_image_followup(update: Update, context: ContextTypes.DEFAULT_TYPE, image_id: str, question: str):
    """
    Handle a follow-up question about a previously analyzed image.
    User can say "tell me more about img_0" or ask specific questions.
    """
    user_id = update.effective_user.id
    session = get_session(user_id)

    # Check if we have the image in memory
    pending_images = session.get("pending_images", {})
    if image_id not in pending_images:
        await update.message.reply_text(
            f"🤔 *Hmm, I can't find that image...*\n\n"
            f"Image `{image_id}` is no longer in memory.\n"
            f"Send the image again if you want me to analyze it more!",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"👁️ *Looking at {image_id} again...*\n\n"
        f"_Let me check: {question}_",
        parse_mode="Markdown"
    )

    # Get stored data
    img_data = pending_images[image_id]
    image_bytes = img_data.get("data")
    previous_analysis = img_data.get("analysis", {})

    # Build project context
    project_context = session.get("project_description", "")

    # Run follow-up analysis
    updated_analysis = await follow_up_image_analysis(
        image_bytes,
        previous_analysis,
        question,
        project_context
    )

    # Update stored analysis
    session["pending_images"][image_id]["analysis"] = updated_analysis

    # Get the latest follow-up answer
    follow_ups = updated_analysis.get("follow_ups", [])
    if follow_ups:
        latest = follow_ups[-1]
        answer = latest.get("answer", "Couldn't analyze further.")

        # Also update the visual context snippet
        for snippet in session.get("visual_context", []):
            if snippet.get("id") == image_id:
                snippet["follow_ups"] = follow_ups
                break

        await update.message.reply_text(
            f"🔍 *About {image_id}:*\n\n"
            f"_{answer[:800]}_",
            parse_mode="Markdown",
            reply_markup=get_keyboard(True)
        )
    else:
        await update.message.reply_text(
            f"🤔 Hmm, I looked but couldn't find more details.\n"
            f"Try being more specific about what you want to know!",
            reply_markup=get_keyboard(True)
        )


def check_for_image_followup(text: str) -> tuple:
    """
    Check if user message is asking about a previous image.
    Returns (image_id, question) or (None, None)
    """
    import re

    # Patterns for image follow-up
    patterns = [
        r"(?:tell me more about|what about|more on|look at|check)\s+(img_\d+)",
        r"(img_\d+)\s*[:\-]?\s*(.+)",
        r"about\s+(img_\d+)\s*[,:]?\s*(.+)?",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            image_id = match.group(1)
            # Get the question (rest of the text or a default)
            if match.lastindex > 1 and match.group(2):
                question = match.group(2).strip()
            else:
                question = text  # Use full text as question
            return (image_id, question)

    return (None, None)


# ============ VOICE TRANSCRIPTION ============

async def transcribe_voice(audio_path: str) -> str:
    """Transcribe voice message - tries multiple methods"""

    # Method 1: Try Groq Whisper API (fast, free tier)
    if GROQ_API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                with open(audio_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename='audio.ogg', content_type='audio/ogg')
                    data.add_field('model', 'whisper-large-v3')

                    async with session.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            text = result.get("text", "")
                            if text:
                                logger.info(f"Groq transcribed: {text[:50]}...")
                                return text
                        else:
                            body = await resp.text()
                            logger.error(f"Groq Whisper error {resp.status}: {body[:200]}")
        except Exception as e:
            logger.error(f"Groq transcription error: {e}")

    # Method 2: Try local openai-whisper if installed
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        text = result.get("text", "")
        if text:
            logger.info(f"Local whisper transcribed: {text[:50]}...")
            return text
    except ImportError:
        logger.warning("Local whisper not installed (pip install openai-whisper)")
    except Exception as e:
        logger.error(f"Local whisper error: {e}")

    logger.error("All transcription methods failed")
    return ""


# ============ IMAGE/OCR PROCESSING (Pytesseract - Offline) ============

async def process_image(image_path: str) -> str:
    """Extract text from image using pytesseract (fully offline OCR)"""
    try:
        import pytesseract
        from PIL import Image

        # Open and preprocess image for better OCR
        img = Image.open(image_path)

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Extract text using tesseract
        text = pytesseract.image_to_string(img)

        # Clean up whitespace
        text = ' '.join(text.split())

        return text if text.strip() else "[No text found in image]"
    except ImportError:
        logger.error("pytesseract not installed! Run: pip install pytesseract Pillow")
        return "[OCR not available - install pytesseract]"
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return f"[Could not read image: {e}]"


# ============ WEB SEARCH (DuckDuckGo - No API Key) ============

async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo (no API key needed)"""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"**{r['title']}**\n{r['body'][:200]}...\n_{r['href']}_")

        if results:
            return "\n\n".join(results)
        return "No results found."
    except ImportError:
        logger.error("duckduckgo_search not installed! Run: pip install duckduckgo-search")
        return "[Web search not available - install duckduckgo-search]"
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"[Search error: {e}]"


async def search_for_context(topic: str) -> str:
    """Search web and summarize for context during conversation"""
    try:
        results = await web_search(f"{topic} tutorial guide best practices", max_results=3)
        return f"[Web context for '{topic}':\n{results}]"
    except Exception as e:
        logger.error(f"Context search error: {e}")
        return ""


async def ralph_ready_to_cook(response: str) -> bool:
    """Check if Ralph's response suggests we have enough info to cook a PRD"""
    if not response:
        return False

    # Simple keyword check - if Ralph mentions cooking or having enough info
    ready_phrases = [
        "ready to cook",
        "got enough",
        "have enough",
        "shall i cook",
        "want me to cook",
        "generate the prd",
        "create your prd",
        "build your project",
        "let's cook",
        "time to cook"
    ]
    response_lower = response.lower()
    return any(phrase in response_lower for phrase in ready_phrases)


async def ralph_needs_to_search(user_message: str, conversation: list, model: str) -> tuple[bool, str]:
    """Check if Ralph needs to do a web search to understand the user's request"""
    try:
        # COMPACT search check
        check_prompt = f"""User said: "{user_message}"
Know this well? Reply:
STATUS: UNDERSTAND|CONFUSED
SEARCH: [term if confused, else "none"]"""

        messages = [{"role": "user", "content": check_prompt}]
        response = await groq_chat(messages, model or "llama-3.3-70b-versatile")

        if not response:
            return False, ""

        # Parse response
        if "CONFUSED" in response.upper():
            # Extract search term
            if "SEARCH:" in response.upper():
                search_term = response.upper().split("SEARCH:")[1].strip().split("\n")[0]
                if search_term and search_term.lower() != "none":
                    return True, search_term.lower()

        return False, ""
    except Exception as e:
        logger.error(f"Search check error: {e}")
        return False, ""


def get_ralph_search_message() -> str:
    """Get a Ralph-style message about searching the interwebs"""
    messages = [
        "🖥️ *Lemme search that real quick...*",
        "🔍 *Don't know that one! Checking...*",
        "💻 *One sec - asking the interwebs...*",
    ]
    return random.choice(messages)


def get_ralph_search_done_message(topic: str) -> str:
    """Get a Ralph-style message after searching"""
    messages = [
        f"✅ *Got it!* '{topic}' - I understand now!",
        f"💡 *Ohhh!* So THAT'S what '{topic}' is!",
    ]
    return random.choice(messages)


# ============ TENOR GIF SEARCH ============

async def search_gif(query: str) -> Optional[str]:
    """Search Tenor for a relevant GIF"""
    try:
        # Add some Ralph-style terms to make it fun
        fun_terms = ["funny", "cute", "excited", "working", "thinking", "celebration"]
        search_query = f"{query} {random.choice(fun_terms)}"

        async with aiohttp.ClientSession() as session:
            params = {
                "q": search_query,
                "key": TENOR_API_KEY,
                "client_key": "ralph_mode",
                "limit": 10,
                "media_filter": "gif"
            }
            async with session.get(
                "https://tenor.googleapis.com/v2/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        # Pick a random one from top results
                        gif = random.choice(results[:5])
                        # Get the gif URL
                        media = gif.get("media_formats", {})
                        gif_url = media.get("gif", {}).get("url")
                        if gif_url:
                            return gif_url
    except Exception as e:
        logger.error(f"GIF search error: {e}")
    return None


async def get_contextual_gif(conversation: List[Dict]) -> Optional[str]:
    """Get a GIF that relates to the conversation"""
    # Extract keywords from recent conversation
    recent_text = " ".join([m["content"][:100] for m in conversation[-3:]])

    # Keywords that make good GIF searches
    keywords = {
        "bot": "robot working",
        "telegram": "messaging app",
        "website": "computer coding",
        "app": "mobile app",
        "database": "data storage",
        "api": "connection",
        "build": "construction",
        "code": "programming",
        "python": "snake coding",
        "error": "oops mistake",
        "success": "celebration",
        "help": "helping hand",
        "thanks": "thank you",
        "awesome": "excited happy",
        "project": "teamwork",
    }

    # Find matching keyword
    search_term = "working hard"  # default
    for keyword, gif_term in keywords.items():
        if keyword in recent_text.lower():
            search_term = gif_term
            break

    return await search_gif(search_term)


def get_keyboard(has_conversation: bool = False, analyzing: bool = False) -> ReplyKeyboardMarkup:
    """Get persistent keyboard"""
    if has_conversation:
        if analyzing:
            kb = [
                [KeyboardButton("🛑 Stop Analysis")],
                [KeyboardButton("🍳 Cook Sauce"), KeyboardButton("💾 Save & Quit")]
            ]
        else:
            kb = [
                [KeyboardButton("🔍 Analyze Project"), KeyboardButton("🍳 Cook Sauce")],
                [KeyboardButton("📥 Install Ralph"), KeyboardButton("💾 Save & Quit")],
                [KeyboardButton("🧠 Change Model")]
            ]
    else:
        kb = [
            [KeyboardButton("🆕 New Project"), KeyboardButton("📂 Load Session")],
            [KeyboardButton("📥 Install Ralph"), KeyboardButton("🧠 Change Model")],
            [KeyboardButton("☕ Support Snail")]
        ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    # Always use Groq - fast and reliable!
    model = "llama-3.3-70b-versatile"
    session["model"] = model
    session["provider"] = "groq"

    # Check for existing sessions
    sessions = session_manager.list_sessions()

    # Common intro about reactions
    reaction_tip = (
        "\n\n💡 *Tip:* Long-press any message to react with emoji!\n"
        "I'll understand 👍❤️🔥 = good, 👎😡💩 = bad, etc.\n"
        "Type /reactions to see all options!"
    )

    if sessions:
        await update.message.reply_text(
            f"*bows* Welcome back, Mr. Worms sir! \xf0\x9f\x8e\xa9\n\n"
            f"I found {len(sessions)} saved conversation(s).\n"
            f"Shall we continue one, or start fresh, sir?\n\n"
            f"_Powered by Groq \u26a1_{reaction_tip}",
            parse_mode="Markdown",
            reply_markup=get_keyboard(False)
        )
    else:
        session["phase"] = "chatting"
        await update.message.reply_text(
            "*bows deeply* At your service, Mr. Worms sir! \xf0\x9f\x8e\xa9\n\n"
            "I am Smithers, your loyal assistant. I help you build *projects*\n"
            "by asking sharp questions, then creating full PRDs for you.\n\n"
            "Tell me what you would like me to create, sir! I am ready to begin.\n\n"
            "_Powered by Groq \u26a1_{reaction_tip}\n\n"
            "*What shall I build for you today, Mr. Worms sir?*",
            parse_mode="Markdown",
            reply_markup=get_keyboard(False)
        )


async def cmd_reactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available emoji reactions and what they mean"""
    await update.message.reply_text(
        EMOJI_LEGEND + "\n_Your reactions help me understand what you like!_",
        parse_mode="Markdown"
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a new project - shows confirmation first"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    # If there's an active conversation, ask for confirmation
    if session.get("conversation") or session.get("prd_blocks"):
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, start fresh", callback_data="confirm_new_yes"),
                InlineKeyboardButton("❌ Cancel", callback_data="confirm_new_no")
            ]
        ]
        await update.message.reply_text(
            "🗑️ *Start a new project?*\n\n"
            "This will clear your current conversation and all PRD blocks.\n\n"
            "_Your saved sessions won't be affected._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # No active project, just confirm fresh start
        reset_session(user_id)
        await update.message.reply_text(
            "🆕 *Fresh start!*\n\n"
            "Tell me about your project, boss!\n"
            "What are we building?",
            parse_mode="Markdown",
            reply_markup=get_keyboard(False)
        )


async def cmd_load(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Load a saved session"""
    sessions = session_manager.list_sessions()

    if not sessions:
        await update.message.reply_text(
            "No saved sessions found!\n"
            "Start a new project by telling me what you want to build."
        )
        return

    # Build inline keyboard with sessions
    keyboard = []
    for sess in sessions[:5]:
        keyboard.append([InlineKeyboardButton(
            f"📁 {sess['name'][:25]} ({sess['messages']} msgs)",
            callback_data=f"load_{sess['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🆕 Start Fresh", callback_data="load_new")])

    await update.message.reply_text(
        "*Your saved sessions:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_load_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle session load selection"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)

    data = query.data

    if data == "load_new":
        # Show confirmation first
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, start fresh", callback_data="confirm_new_yes"),
                InlineKeyboardButton("❌ Cancel", callback_data="confirm_new_no")
            ]
        ]
        await query.edit_message_text(
            "🗑️ *Start a new project?*\n\n"
            "This will clear your current conversation and all PRD blocks.\n\n"
            "_Your saved sessions won't be affected._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "confirm_new_yes":
        # Actually reset everything
        reset_session(user_id)
        await query.edit_message_text(
            "🆕 *Fresh start!*\n\n"
            "Everything's cleared out. Tell me about your new project!",
            parse_mode="Markdown"
        )
        return

    if data == "confirm_new_no":
        await query.edit_message_text(
            "👍 *Keeping your current project.*\n\n"
            "Continue where you left off!",
            parse_mode="Markdown"
        )
        return

    if data.startswith("load_"):
        session_id = data[5:]
        loaded = session_manager.load_session(session_id)

        if loaded:
            session["session_id"] = session_id
            session["project_name"] = loaded.get("project_name", "")
            session["project_description"] = loaded.get("project_description", "")
            session["conversation"] = loaded.get("conversation", [])
            session["phase"] = "chatting"

            # Show last few messages
            recent = session["conversation"][-3:]
            context_text = "\n".join([
                f"{'You' if m['role']=='user' else 'Ralph'}: {m['content'][:60]}..."
                for m in recent
            ])

            await query.edit_message_text(
                f"*Loaded: {session['project_name']}*\n\n"
                f"We had {len(session['conversation'])} messages.\n\n"
                f"_Recent:_\n{context_text}\n\n"
                f"Keep going, or say 'cook' when ready!",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("Couldn't load that session. Try another!")


async def cmd_cook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate the PRD"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    session = get_session(user_id)

    # Helper to send message (works for both direct message and callback)
    async def send_msg(text, **kwargs):
        if update.message:
            return await update.message.reply_text(text, **kwargs)
        else:
            return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)

    if len(session["conversation"]) < 2:
        await send_msg(
            "I need more info first, boss!\n"
            "Tell me about what you want to build."
        )
        return

    session["phase"] = "cooking"

    await send_msg(
        "🍳 *Cooking your sauce!*\n\n"
        "_Groq is firing up the kitchen..._",
        parse_mode="Markdown"
    )

    # Generate PRD (with batch processing support)
    prd = await generate_prd(session, update, context)

    if prd:
        # Save PRD - COMPRESSED for token efficiency!
        safe_name = (session["project_name"] or "project").replace(" ", "_").replace("/", "_").lower()
        display_name = session["project_name"] or "Project"  # Keep proper casing for display
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Compressed version (for Claude Code - saves tokens!)
        compressed_filename = f"{safe_name}_prd_{timestamp}.txt"
        compressed_prd = compress_prd(prd)
        with open(compressed_filename, 'w') as f:
            f.write(compressed_prd)

        # Also save full JSON for reference
        full_filename = f"{safe_name}_prd_{timestamp}_full.json"
        with open(full_filename, 'w') as f:
            json.dump(prd, f, indent=2)

        # Calculate compression savings (compare pretty JSON vs compressed)
        full_size = len(json.dumps(prd, indent=2))  # Pretty-printed (what humans read)
        # Don't count legend header in compressed size for fair comparison
        compressed_json_only = compressed_prd.split("\n\n", 1)[-1] if "\n\n" in compressed_prd else compressed_prd
        compressed_size = len(compressed_json_only)
        savings = int((1 - compressed_size / full_size) * 100) if full_size > 0 else 0

        # Count tasks
        prds = prd.get("prds", {})
        total_tasks = sum(len(s.get("tasks", [])) for s in prds.values())

        # Send success message with buttons
        keyboard = [
            [InlineKeyboardButton("📖 Share Recipe", callback_data="share_recipe")],
            [InlineKeyboardButton("☕ Support Snail", url="https://buymeacoffee.com/snail3d")],
            [InlineKeyboardButton("🆕 New Project", callback_data="load_new")]
        ]

        # Get starter prompt for display
        starter_prompt = prd.get('starter_prompt', '')
        starter_preview = starter_prompt[:300] + "..." if len(starter_prompt) > 300 else starter_prompt

        await send_msg(
            f"✅ *Sauce is ready!*\n\n"
            f"*{prd.get('project_name', 'Your Project')}*\n"
            f"_{prd.get('project_description', '')}_\n\n"
            f"📊 *{total_tasks} tasks* across *{len(prds)} phases*\n"
            f"💾 *{savings}% smaller* with compression!\n\n"
            f"📋 *Build Instructions:*\n{starter_preview}\n\n"
            f"Use: `{compressed_filename}` _(token-optimized)_\n"
            f"Full: `{full_filename}`\n\n"
            f"Feed the compressed file to Claude Code!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Send the compressed file (primary)
        with open(compressed_filename, 'rb') as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=compressed_filename,
                caption=f"🍳 {display_name} - TeleRalph PRD (token-optimized)"
            )

        session["phase"] = "idle"
    else:
        await send_msg(
            "Oops! Something went wrong cooking the sauce.\n"
            "Try telling me more about your project and cook again!"
        )
        session["phase"] = "chatting"


async def search_related_recipes(session: dict) -> str:
    """
    Search the Recipe Book for related patterns and context.
    Returns a string summary of relevant past projects/conversations.
    """
    # Build search query from project info
    project_name = session.get("project_name", "")
    project_desc = session.get("project_description", "")[:200]

    # Extract key terms from conversation
    key_terms = set()
    for msg in session.get("conversation", [])[-10:]:
        content = msg.get("content", "").lower()
        # Look for tech keywords
        tech_words = ["api", "bot", "app", "website", "database", "auth", "login",
                      "telegram", "discord", "python", "javascript", "react", "flask",
                      "scraper", "automation", "dashboard", "chat", "ai", "ml"]
        for word in tech_words:
            if word in content:
                key_terms.add(word)

    # Build search query
    search_query = f"{project_name} {' '.join(list(key_terms)[:5])}"

    # Search local recipes
    try:
        local_results = recipe_api.search_local_recipes(search_query)
        if local_results:
            summaries = []
            for recipe in local_results[:3]:  # Top 3 matches
                # Extract useful patterns from the recipe PRD
                prd = recipe.prd if hasattr(recipe, 'prd') else {}
                starter = prd.get("starter_prompt", "")[:150] if isinstance(prd, dict) else ""

                summaries.append(
                    f"- **{recipe.name}**: {recipe.description[:100]}...\n"
                    f"  Key pattern: {starter}"
                )

            return "\n".join(summaries) if summaries else ""
    except Exception as e:
        logger.warning(f"Recipe search error: {e}")

    return ""


async def generate_prd(session: dict, update: Update = None, context: ContextTypes.DEFAULT_TYPE = None) -> Optional[Dict]:
    """Generate PRD using Groq (or merge with imported PRD) - supports batch processing for unlimited tasks"""

    # Check if this is a PRD re-import scenario
    is_reimport = session.get("prd_imported", False)
    imported_prd = session.get("imported_prd", {})
    imported_tasks = session.get("imported_tasks", [])
    existing_prds = session.get("existing_prds", {})

    # Batch processing settings (for unlimited PRDs with local AI constraints)
    USE_BATCH_MODE = True  # Enable batch processing
    BATCH_SIZE = 10  # Tasks per batch
    MAX_TOTAL_TASKS = 400  # "No limit" = 400 tasks

    # Helper to send progress messages (if update/context provided)
    async def send_progress(message: str):
        if update and context:
            chat_id = update.effective_chat.id
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

    conv_summary = "\n".join([
        f"{'User' if m['role']=='user' else 'Ralph'}: {m['content']}"
        for m in session["conversation"][-15:]
    ])

    # For re-import, include existing tasks in the prompt
    existing_tasks_context = ""
    if is_reimport and imported_tasks:
        existing_tasks_context = f"\n\nEXISTING TASKS (already in PRD - add NEW tasks only):\n"
        for task in imported_tasks[:20]:  # Show first 20
            existing_tasks_context += f"- [{task.get('id', 'N/A')}] {task.get('title', 'Unknown')}: {task.get('description', '')[:100]}\n"
        existing_tasks_context += f"\nTotal existing tasks: {len(imported_tasks)}\n"
        existing_tasks_context += "Generate NEW tasks that don't duplicate these. Use new IDs."

    # Include visual context from analyzed images
    visual_context_str = ""
    if session.get("visual_context"):
        visual_summaries = []
        for vc in session["visual_context"][-5:]:  # Last 5 images
            summary = f"- [{vc.get('type', 'image')}] {vc.get('summary', '')[:200]}"
            if vc.get("tags"):
                summary += f" (tags: {', '.join(vc['tags'][:3])})"
            visual_summaries.append(summary)
        if visual_summaries:
            visual_context_str = "\n\nVISUAL CONTEXT (from user's images):\n" + "\n".join(visual_summaries)

    # Search for related recipes/past conversations
    related_context_str = ""
    try:
        related = await search_related_recipes(session)
        if related:
            related_context_str = "\n\nRELATED PATTERNS FROM RECIPE BOOK:\n" + related
    except Exception as e:
        logger.warning(f"Could not fetch related recipes: {e}")

    # Include user preferences from review
    preferences_str = ""
    if session.get("preferences"):
        preferences_str = format_preferences_for_prd(session["preferences"])
        if preferences_str:
            preferences_str = "\n\n" + preferences_str

    # Include liked/hated snippets from suggestion review
    snippets_str = ""
    liked = session.get("liked_snippets", [])
    hated = session.get("hated_snippets", [])
    if liked or hated:
        snippets_str = "\n\n" + format_snippets_for_prd(liked, hated)

    # Include rapid-fire approved/rejected features
    features_str = ""
    approved = session.get("approved_features", [])
    rejected = session.get("rejected_features", [])
    if approved or rejected:
        features_str = "\n\n" + format_approved_features_for_prd(approved, rejected)

    # COMPACT PRD PROMPT - optimized for token efficiency
    prompt = f"""Generate compact PRD JSON. English output only.

PROJECT: {session["project_name"] or "Unknown"}
DESC: {session["project_description"]}{visual_context_str}{related_context_str}{preferences_str}{snippets_str}{features_str}{existing_tasks_context}

CONV:
{conv_summary}

Output compact JSON:
{{
  "project_name": "name",
  "project_description": "1 sentence",
  "starter_prompt": "Complete build instructions for Claude Code. Start: 'RUN THIS FIRST: claude{" --dangerously-skip-permissions" if session.get("dangerous_mode", True) else ""}'. Then: 'SECURITY FIRST: .gitignore, .env.example, config.py'. Then: purpose, stack, features, files, build order.

CRITICAL: After EACH task, commit+push to GitHub immediately. No batching. Keep GitHub in sync.

REAL-TIME PREVIEW: If possible, run project in real-time as you build. For websites: open preview ASAP, update at every step. Preview should work minimized/maximized, updating in background. Prioritize getting preview running early.

README UPDATES (every pass): Update README.md top boldly: 'ACTIVE BUILD IN PROGRESS - Pass X/XX (Iteration Y/YY)'. Track pass/iteration counts. Update install instructions as you go - prioritize SIMPLEST method if same cost/result.

FINAL TASK: Change header to 'BUILD COMPLETE 🎉'. Add at BOTTOM of README: 'Built with TeleRalph - Welcome to Ralph's Kitchen. He mixes your sauce. Get your own Ralph at: https://github.com/Snail3D/ralphmode.com'

DEDICATED README PASS: Include ONE dedicated README.md pass (last/near-last). Must: search codebase, identify hottest functions, write clear install docs, document usage. Last task: Dockerize if possible (volumes, compose). Install instructions AT TOP - simplest method优先.

3-4 paragraphs total.",
  "tech_stack": {{"language": "x", "framework": "y", "database": "z", "other": []}},
  "file_structure": [".gitignore", ".env.example", "config.py", "main.py", "requirements.txt"],
  "commands": {{"setup": "pip install -r requirements.txt", "run": "python main.py", "test": "pytest"}},
  "prds": {{
    "00_security": {{
      "name": "Security",
      "tasks": [
        {{"id": "SEC-001", "title": ".gitignore", "description": "Exclude .env,*.pyc,venv,secrets", "file": ".gitignore", "priority": "critical"}},
        {{"id": "SEC-002", "title": ".env.example", "description": "Template with placeholders", "file": ".env.example", "priority": "critical"}},
        {{"id": "SEC-003", "title": "config.py", "description": "Load from env vars, never hardcode", "file": "config.py", "priority": "critical"}}
      ]
    }},
    "01_setup": {{"name": "Setup", "tasks": []}},
    "02_core": {{"name": "Core", "tasks": []}},
    "03_api": {{"name": "API/Handlers", "tasks": []}},
    "04_test": {{"name": "Testing", "tasks": []}}
  }}
}}

RULES:
- 4-8 tasks per section
- Task format: {{"id":"X-00N","title":"short","description":"1-2 sentences","file":"x.py","priority":"high/medium"}}
- Be specific about files and functions
- Security section always first
{"- If there are existing tasks listed above, generate NEW tasks only. Don't duplicate existing task IDs." if is_reimport else ""}

JSON only, no commentary."""

    try:
        model = session.get("model") or "llama-3.3-70b-versatile"
        # Use high max_tokens for full PRD JSON (very large output)
        response = await groq_chat(
            [{"role": "user", "content": prompt}],
            model,
            temperature=0.7,
            max_tokens=8192  # PRD is a big JSON!
        )

        if not response:
            logger.error("PRD generation: Empty response from Groq")
            return None

        # Parse JSON
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            prd = json.loads(response[json_start:json_end])

            # Add visual_inspiration section if user provided images
            # Analysis only - no file saving (saves tokens!)
            if session.get("visual_context"):
                prd["visual_inspiration"] = []

                for i, vc in enumerate(session["visual_context"]):
                    # Compress the analysis for token efficiency
                    analysis = vc.get("analysis", "")
                    if len(analysis) > 300:
                        # Use Groq to compress the analysis
                        compressed = await summarize_user_message(analysis, "llama-3.3-70b-versatile")
                        analysis = compressed if len(compressed) < len(analysis) else analysis[:300]

                    inspiration_item = {
                        "id": vc.get("id", f"img_{i}"),
                        "type": vc.get("type", "image"),
                        "summary": vc.get("summary", "")[:200],
                        "analysis": analysis,
                        "tags": vc.get("tags", [])[:5],
                    }
                    prd["visual_inspiration"].append(inspiration_item)

                # Add note for builder bots
                prd["visual_inspiration_note"] = (
                    "User provided reference images as inspiration. "
                    "Use analysis/summary for design guidance: colors, layouts, UI patterns."
                )

            # Add inspiration sources with analysis (URLs/projects user mentioned)
            if session.get("inspiration_sources"):
                prd["inspiration_sources"] = session["inspiration_sources"][:5]

            # Add analyzed URL inspirations (with compressed summaries)
            if session.get("inspiration_analysis"):
                prd["url_inspiration"] = []
                for ia in session["inspiration_analysis"][:3]:
                    # Compress the analysis
                    analysis = ia.get("analysis", "")
                    if len(analysis) > 200:
                        analysis = await summarize_user_message(analysis, "llama-3.3-70b-versatile")
                        analysis = analysis[:200] if analysis else ia.get("analysis", "")[:200]

                    prd["url_inspiration"].append({
                        "url": ia.get("url", ""),
                        "type": ia.get("type", "website"),
                        "analysis": analysis
                    })

            # === MERGE EXISTING PRD IF RE-IMPORTING ===
            if is_reimport and imported_prd:
                # Preserve original starter prompt (with emojis!)
                if imported_prd.get("sp"):
                    prd["starter_prompt"] = imported_prd["sp"]

                # Merge tech stack (use imported if exists, otherwise use new)
                for key in ["language", "framework", "database", "other"]:
                    if imported_prd.get("ts", {}).get(key):
                        if not prd.get("tech_stack"):
                            prd["tech_stack"] = {}
                        prd["tech_stack"][key] = imported_prd["ts"][key]

                # Merge file structures (remove duplicates)
                imported_files = imported_prd.get("fs", [])
                new_files = prd.get("file_structure", [])
                all_files = list(set(imported_files + new_files))
                prd["file_structure"] = all_files

                # Merge tasks - existing + new
                merged_prds = {}

                # First, copy existing tasks
                for section_key, section_data in existing_prds.items():
                    merged_prds[section_key] = {
                        "n": section_data.get("n", section_data.get("name", section_key)),
                        "t": []
                    }
                    # Convert task format for compression
                    for task in section_data.get("t", []):
                        merged_prds[section_key]["t"].append(task)

                # Then add new tasks from generated PRD
                new_prds = prd.get("prds", {})
                for section_key, section_data in new_prds.items():
                    if section_key not in merged_prds:
                        merged_prds[section_key] = {
                            "n": section_data.get("name", section_key),
                            "t": []
                        }

                    # Add new tasks (avoid duplicates by checking task IDs)
                    existing_ids = set(t.get("i", t.get("id", "")) for t in merged_prds[section_key]["t"])
                    for task in section_data.get("tasks", []):
                        task_id = task.get("id", "")
                        if task_id and task_id not in existing_ids:
                            # Convert to compressed format
                            compressed_task = {
                                "i": task.get("id"),
                                "ti": task.get("title"),
                                "d": task.get("description"),
                                "f": task.get("file"),
                                "pr": task.get("priority", "medium")
                            }
                            # Add optional fields if present
                            if task.get("acceptance_criteria"):
                                compressed_task["ac"] = task.get("acceptance_criteria")
                            merged_prds[section_key]["t"].append(compressed_task)

                prd["prds"] = merged_prds

                # Add version info to track re-exports
                prd["prd_version"] = imported_prd.get("prd_version", 1) + 1
                prd["is_reimport"] = True

                logger.info(f"Merged PRD: {len(imported_tasks)} existing + new tasks")

            # === BATCH PROCESSING: Generate more tasks if needed ===
            if USE_BATCH_MODE and not is_reimport:
                # Count current tasks
                current_prds = prd.get("prds", {})
                total_tasks = sum(len(s.get("tasks", [])) for s in current_prds.values())

                # Generate additional batches if we want more tasks
                batch_num = 1
                ralph_messages = [
                    "Hold on boss, let me save this... *scribbles on notepad*",
                    "Okay boss, I got more ideas... *flips page*",
                    "Just a sec boss, almost done cooking... *wipes brow*",
                    "More sauce coming up, boss! *stirs pot*",
                    "I gotcha boss, keep 'em coming! *nods enthusiastically*"
                ]

                while total_tasks < MAX_TOTAL_TASKS:
                    batch_num += 1
                    target_tasks = min(batch_num * BATCH_SIZE * 5, MAX_TOTAL_TASKS)  # 5 sections * BATCH_SIZE

                    if total_tasks >= target_tasks:
                        break

                    # Show progress
                    progress_msg = ralph_messages[(batch_num - 2) % len(ralph_messages)]
                    await send_progress(f"{progress_msg}\n\n_Generated {total_tasks} tasks so far, cooking more..._")

                    # Generate additional tasks prompt
                    new_tasks_prompt = f"""Generate {BATCH_SIZE} MORE tasks for this PRD. Don't repeat existing tasks.

EXISTING PROJECT: {prd.get('pn', 'Project')}
EXISTING TASKS COUNT: {total_tasks}

Generate {BATCH_SIZE} new tasks (spread across sections). Output ONLY this JSON structure:
{{
  "new_tasks": {{
    "00_security": {{"tasks": []}},
    "01_setup": {{"tasks": []}},
    "02_core": {{"tasks": []}},
    "03_api": {{"tasks": []}},
    "04_test": {{"tasks": []}}
  }}
}}

Focus on edge cases, error handling, optimization, documentation, and advanced features.
Each task: {{"id":"X-999","title":"short","description":"1 sentence","file":"x.py","priority":"medium"}}
JSON only."""

                    try:
                        # Call AI for more tasks
                        batch_response = await groq_chat(
                            [{"role": "user", "content": new_tasks_prompt}],
                            model,
                            temperature=0.8,
                            max_tokens=4096
                        )

                        if batch_response:
                            batch_json_start = batch_response.find("{")
                            batch_json_end = batch_response.rfind("}") + 1

                            if batch_json_start >= 0:
                                batch_data = json.loads(batch_response[batch_json_start:batch_json_end])
                                new_tasks = batch_data.get("new_tasks", {})

                                # Add new tasks to PRD
                                tasks_added = 0
                                for section_key, section_data in new_tasks.items():
                                    if section_key in current_prds:
                                        for task in section_data.get("tasks", []):
                                            # Avoid duplicate IDs
                                            existing_ids = set(t.get("id", t.get("i", "")) for t in current_prds[section_key].get("tasks", []))
                                            task_id = task.get("id", "")

                                            if task_id and task_id not in existing_ids:
                                                current_prds[section_key].setdefault("tasks", []).append(task)
                                                tasks_added += 1

                                total_tasks += tasks_added
                                logger.info(f"Batch {batch_num}: Added {tasks_added} tasks (total: {total_tasks})")

                                # Stop if we didn't add any tasks (AI exhausted)
                                if tasks_added == 0:
                                    break

                            else:
                                logger.warning(f"Batch {batch_num}: No valid JSON in response")
                                break

                    except Exception as e:
                        logger.error(f"Batch {batch_num} error: {e}")
                        break

                # Final progress message
                await send_progress(f"✅ *Done cooking, boss!*\n\n_Generated {total_tasks} tasks total_\n\n_Saving your sauce now..._")

                prd["total_tasks_generated"] = total_tasks
                prd["batch_count"] = batch_num

            return prd
        else:
            logger.error(f"PRD generation: No JSON found in response: {response[:200]}")
    except Exception as e:
        logger.error(f"PRD generation error: {e}")

    return None


async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save session and recipe with QR code"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session["conversation"]:
        await update.message.reply_text("Nothing to save yet! Tell me about your project first.")
        return

    # Create session ID if needed
    if not session["session_id"]:
        session["session_id"] = session_manager.create_session_id(session["project_name"])

    # Save session
    session_manager.save_session(
        session["session_id"],
        session["project_name"],
        session["project_description"],
        session["conversation"]
    )

    # Also save as a recipe!
    # Extract tags from the description
    tags = []
    common_tags = ["bot", "telegram", "discord", "web", "api", "database", "cli", "python", "app", "ai"]
    desc_lower = session["project_description"].lower()
    for tag in common_tags:
        if tag in desc_lower:
            tags.append(tag)

    # Create recipe PRD (simplified version of what /cook would generate)
    recipe_prd = {
        "project_name": session["project_name"],
        "description": session["project_description"],
        "conversation_summary": [
            {"role": m["role"], "content": m["content"][:200]}
            for m in session["conversation"][-10:]
        ],
        "tasks": [],  # Will be filled when /cook is used
        "saved_at": datetime.now().isoformat(),
        # Include analysis context if available (for quality ranking)
        "analysis": session.get("analysis_context", None),
        "model_used": session.get("model", ""),
        "provider_used": session.get("provider", "local")
    }

    # Save recipe locally (with model info for quality ranking)
    recipe_id = recipe_api.save_recipe(
        name=session["project_name"] or "Untitled Project",
        description=session["project_description"][:200],
        prd=recipe_prd,
        tags=tags,
        model=session.get("model", ""),
        provider=session.get("provider", "local")
    )
    session["recipe_id"] = recipe_id

    # Generate QR code
    qr_path = generate_recipe_qr(recipe_id)

    await update.message.reply_text(
        f"💾 *Saved!*\n\n"
        f"📋 Session: `{session['session_id']}`\n"
        f"🧾 Recipe ID: `{recipe_id}`\n"
        f"💬 Messages: {len(session['conversation'])}\n\n"
        f"_Generating QR code..._",
        parse_mode="Markdown"
    )

    # Send QR code if generated
    if qr_path and os.path.exists(qr_path):
        with open(qr_path, 'rb') as qr_file:
            await update.message.reply_photo(
                photo=qr_file,
                caption=(
                    f"📱 *Your Recipe QR Code*\n\n"
                    f"Scan this to recall your recipe anytime!\n"
                    f"Recipe ID: `{recipe_id}`\n\n"
                    f"_Save this image or screenshot it!_"
                ),
                parse_mode="Markdown"
            )
        os.unlink(qr_path)  # Clean up

    await update.message.reply_text(
        "🎉 *Recipe saved locally!*\n\n"
        "• /recipes - View your saved recipes\n"
        "• /cook - Generate PRD when ready\n"
        "• Scan QR to load this recipe anytime!\n\n"
        "_Your recipe is stored in ~/.ralph/recipes/_",
        parse_mode="Markdown",
        reply_markup=get_keyboard(False)
    )

    session["phase"] = "idle"


async def cmd_recipes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show local recipes and search Recipe Book"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    query = " ".join(context.args) if context.args else ""

    # First, show local recipes
    local_recipes = recipe_api.list_local_recipes()

    if local_recipes and not query:
        # Show local recipes with load buttons
        text = "📚 *Your Saved Recipes:*\n\n"
        keyboard = []

        for i, r in enumerate(local_recipes[:5], 1):
            text += f"{i}. *{r['name']}*\n"
            text += f"   _{r.get('description', '')[:40]}_\n"
            tags_str = ", ".join(r.get('tags', [])[:3])
            if tags_str:
                text += f"   🏷️ {tags_str}\n"
            text += "\n"

            keyboard.append([InlineKeyboardButton(
                f"📋 Load: {r['name'][:20]}",
                callback_data=f"recipe_load_{r['id']}"
            )])

        keyboard.append([InlineKeyboardButton("🔍 Search Cloud Recipes", callback_data="recipe_search")])

        await update.message.reply_text(
            text + "\n_Tap to load a recipe, or search for more!_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # If query provided, search both local and cloud
    if query:
        await update.message.reply_text(f"🔍 Searching for: _{query}_", parse_mode="Markdown")

        # Search local first
        local_results = recipe_api.search_local_recipes(query)

        # Then search cloud
        cloud_results = await recipe_api.search_recipes(query, limit=5)

        text = ""

        if local_results:
            text += "*📱 Your Recipes:*\n\n"
            for i, r in enumerate(local_results[:3], 1):
                text += f"{i}. *{r['name']}* (local)\n"
                text += f"   _{r.get('description', '')[:40]}_\n\n"

        if cloud_results:
            text += "*☁️ Community Recipes:*\n\n"
            for i, r in enumerate(cloud_results[:3], 1):
                text += f"{i}. *{r['name']}* ({r.get('upvotes', 0)} ⬆️)\n"
                text += f"   _{r.get('description', '')[:40]}_\n\n"

        if text:
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "No matching recipes found!\n\n"
                "You might be building something new - that's exciting!"
            )
    else:
        await update.message.reply_text(
            "📚 *Recipe Book*\n\n"
            "No saved recipes yet!\n\n"
            "• Start chatting to describe your project\n"
            "• Use /save to save your recipe\n"
            "• Or search: `/recipes telegram bot`",
            parse_mode="Markdown"
        )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of 50 recent sessions with clickable links"""
    user_id = update.effective_user.id

    await update.message.reply_text(
        "📚 Loading your sessions...",
        parse_mode="Markdown"
    )

    # Get sessions from cloud and local cache
    sessions = await session_cloud.list_cloud_sessions(user_id)

    if not sessions:
        await update.message.reply_text(
            "📭 *No sessions found*\n\n"
            "Start chatting with me to create your first session!\n"
            "Sessions auto-save as you talk.\n\n"
            "_Tip: Just tell me about something you want to build!_",
            parse_mode="Markdown",
            reply_markup=get_keyboard(False)
        )
        return

    # Show first page of sessions with buttons
    keyboard = session_cloud.format_session_buttons(sessions, page=0)

    text = f"📚 *Your Sessions* ({len(sessions)} total)\n\n"
    text += "_Click a session to load it:_\n\n"

    # Show preview of first few
    for i, s in enumerate(sessions[:5], 1):
        title = s.get("title", "Untitled")[:35]
        updated = s.get("updated_at", "")[:10]
        text += f"{i}. *{title}*\n"
        text += f"   _{updated}_\n\n"

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Review conversation - scroll through each exchange and give feedback.
    Maximum 50 exchanges to review.
    """
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session["conversation"]:
        await update.message.reply_text(
            "📭 *Nothing to review yet!*\n\n"
            "Start chatting with me first, then use /review to go through "
            "the conversation and mark what you like or don't like.",
            parse_mode="Markdown"
        )
        return

    # Initialize review state
    session["review_index"] = 0
    session["review_feedback"] = {}  # {index: liked}

    # Get assistant messages only (those are the suggestions to review)
    assistant_msgs = [
        (i, m) for i, m in enumerate(session["conversation"])
        if m["role"] == "assistant"
    ][:50]  # Max 50

    if not assistant_msgs:
        await update.message.reply_text("No suggestions to review yet!")
        return

    session["review_messages"] = assistant_msgs

    await update.message.reply_text(
        f"📋 *Review Mode*\n\n"
        f"You have *{len(assistant_msgs)}* exchanges to review.\n"
        f"Go through each one and mark if you like it or not.\n\n"
        f"_Your preferences will be saved for the final PRD!_",
        parse_mode="Markdown"
    )

    # Show first message
    await show_review_message(update, context, 0)


async def show_review_message(update_or_query, context, index: int):
    """Show a single review message with feedback buttons"""
    # Get user_id from either update type
    if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
        user_id = update_or_query.effective_user.id
        query = update_or_query.callback_query
        is_callback = True
    else:
        user_id = update_or_query.effective_user.id
        is_callback = False

    session = get_session(user_id)
    review_msgs = session.get("review_messages", [])

    if not review_msgs or index >= len(review_msgs):
        # Done reviewing!
        await finish_review(update_or_query, context)
        return

    msg_index, msg = review_msgs[index]
    content = msg["content"][:500]  # Truncate long messages

    # Check if already reviewed
    already_reviewed = session.get("review_feedback", {}).get(str(index))
    review_status = ""
    if already_reviewed is not None:
        review_status = " ✅" if already_reviewed else " ❌"

    text = (
        f"📝 *Review {index + 1}/{len(review_msgs)}*{review_status}\n\n"
        f"---\n"
        f"{content}\n"
        f"---\n\n"
        f"_Do you like this idea/suggestion?_"
    )

    # Navigation and feedback buttons
    keyboard = [
        [
            InlineKeyboardButton("👍 I like it!", callback_data=f"rev_like_{index}"),
            InlineKeyboardButton("👎 Not for me", callback_data=f"rev_dislike_{index}")
        ],
        []
    ]

    # Add navigation
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"rev_nav_{index-1}"))
    if index < len(review_msgs) - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"rev_nav_{index+1}"))
    nav_row.append(InlineKeyboardButton("✅ Done", callback_data="rev_done"))

    keyboard[1] = nav_row

    if is_callback:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update_or_query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def finish_review(update_or_query, context):
    """Finish review mode and show summary"""
    if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
        user_id = update_or_query.effective_user.id
        query = update_or_query.callback_query
        is_callback = True
    else:
        user_id = update_or_query.effective_user.id
        is_callback = False

    session = get_session(user_id)
    review_feedback = session.get("review_feedback", {})
    review_msgs = session.get("review_messages", [])

    # Convert review feedback to preferences
    liked_count = sum(1 for v in review_feedback.values() if v)
    disliked_count = sum(1 for v in review_feedback.values() if not v)

    # Save to preferences
    for idx_str, liked in review_feedback.items():
        idx = int(idx_str)
        if idx < len(review_msgs):
            msg_index, msg = review_msgs[idx]
            preference = {
                "feature": msg["content"][:100],
                "liked": liked,
                "context": msg["content"][:200],
                "timestamp": datetime.now().isoformat(),
                "from_review": True
            }
            if "preferences" not in session:
                session["preferences"] = []
            session["preferences"].append(preference)

    # Clear review state
    session["review_index"] = 0
    session["review_messages"] = []
    session["review_feedback"] = {}

    text = (
        f"✅ *Review Complete!*\n\n"
        f"📊 Summary:\n"
        f"• 👍 Liked: {liked_count}\n"
        f"• 👎 Didn't like: {disliked_count}\n"
        f"• Total reviewed: {liked_count + disliked_count}/{len(review_msgs)}\n\n"
        f"Your preferences have been saved!\n"
        f"Use /cook to generate a PRD that includes what you like."
    )

    if is_callback:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update_or_query.message.reply_text(text, parse_mode="Markdown")


async def handle_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle review navigation and feedback"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data

    if data.startswith("rev_like_"):
        # Liked this message
        index = int(data.replace("rev_like_", ""))
        if "review_feedback" not in session:
            session["review_feedback"] = {}
        session["review_feedback"][str(index)] = True

        # Auto-advance to next
        next_index = index + 1
        review_msgs = session.get("review_messages", [])
        if next_index < len(review_msgs):
            await show_review_message(update, context, next_index)
        else:
            await finish_review(update, context)

    elif data.startswith("rev_dislike_"):
        # Disliked this message
        index = int(data.replace("rev_dislike_", ""))
        if "review_feedback" not in session:
            session["review_feedback"] = {}
        session["review_feedback"][str(index)] = False

        # Auto-advance to next
        next_index = index + 1
        review_msgs = session.get("review_messages", [])
        if next_index < len(review_msgs):
            await show_review_message(update, context, next_index)
        else:
            await finish_review(update, context)

    elif data.startswith("rev_nav_"):
        # Navigate to specific index
        index = int(data.replace("rev_nav_", ""))
        await show_review_message(update, context, index)

    elif data == "rev_done":
        # Finish early
        await finish_review(update, context)


# ============ SNIPPET SUGGESTION SYSTEM ============
# Search relevant code patterns, let user Like/Skip/HATE them

async def cmd_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Search for relevant code snippets/patterns from the Recipe Book.
    User can Like (include), Skip, or HATE (blacklist) each one.
    """
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session["conversation"] and not session["project_description"]:
        await update.message.reply_text(
            "📭 *Tell me about your project first!*\n\n"
            "I need some context to find relevant snippets.\n"
            "Describe what you want to build, then use /suggest.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "🔍 *Searching for relevant patterns...*",
        parse_mode="Markdown"
    )

    # Build search query from conversation context
    search_terms = []
    if session["project_name"]:
        search_terms.append(session["project_name"])
    if session["project_description"]:
        search_terms.extend(session["project_description"].split()[:10])

    # Also extract key terms from recent conversation
    for msg in session["conversation"][-5:]:
        if msg["role"] == "user":
            words = msg["content"].split()[:5]
            search_terms.extend(words)

    query = " ".join(search_terms[:15])

    # Search local recipes and cloud
    suggestions = []

    # Local recipes
    local_recipes = recipe_api.search_local_recipes(query)
    for r in local_recipes[:5]:
        suggestions.append({
            "type": "recipe",
            "id": r.get("id", ""),
            "title": r.get("name", "Untitled"),
            "description": r.get("description", "")[:200],
            "tags": r.get("tags", []),
            "source": "local"
        })

    # Cloud recipes
    try:
        cloud_recipes = await recipe_api.search_recipes(query, limit=10)
        for r in cloud_recipes:
            suggestions.append({
                "type": "recipe",
                "id": r.get("id", ""),
                "title": r.get("name", "Untitled"),
                "description": r.get("description", "")[:200],
                "tags": r.get("tags", []),
                "source": "cloud",
                "upvotes": r.get("upvotes", 0)
            })
    except Exception as e:
        logger.warning(f"Cloud recipe search failed: {e}")

    if not suggestions:
        await update.message.reply_text(
            "🤷 *No relevant patterns found*\n\n"
            "You might be building something new! That's exciting.\n"
            "Continue chatting and /cook when ready.",
            parse_mode="Markdown"
        )
        return

    # Remove duplicates by title
    seen_titles = set()
    unique_suggestions = []
    for s in suggestions:
        if s["title"] not in seen_titles:
            seen_titles.add(s["title"])
            unique_suggestions.append(s)

    # Filter out bad ratio items (more hates than likes)
    # A ratio of hates:likes > 2:1 means hide it
    filtered_suggestions = []
    for s in unique_suggestions:
        likes = s.get("upvotes", 0) or s.get("likes", 0)
        hates = s.get("downvotes", 0) or s.get("hates", 0)

        # Default: show if no votes yet
        if likes == 0 and hates == 0:
            filtered_suggestions.append(s)
        # Show if ratio is acceptable (not more than 2:1 hate:like)
        elif hates <= (likes * 2):
            filtered_suggestions.append(s)
        # Skip items with bad ratio (cream sinks, garbage filters out)
        else:
            logger.debug(f"Filtered out {s.get('title')} - bad ratio {hates}:{likes}")

    # Sort by upvotes - cream rises to the top!
    filtered_suggestions.sort(key=lambda x: x.get("upvotes", 0), reverse=True)

    session["suggestion_queue"] = filtered_suggestions[:20]  # Max 20 cream of the crop
    session["suggestion_index"] = 0

    await update.message.reply_text(
        f"📚 *Found {len(session['suggestion_queue'])} relevant patterns!*\n\n"
        f"Review each one:\n"
        f"• 👍 *Like* - Include this pattern\n"
        f"• 👎 *Skip* - Ignore it\n"
        f"• 🚫 *Hate* - NEVER use this pattern\n\n"
        f"_Hated patterns will be actively avoided in your PRD!_",
        parse_mode="Markdown"
    )

    await show_suggestion(update, context, 0)


async def show_suggestion(update_or_query, context, index: int):
    """Show a single suggestion with 3 buttons"""
    if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
        user_id = update_or_query.effective_user.id
        query = update_or_query.callback_query
        is_callback = True
    else:
        user_id = update_or_query.effective_user.id
        is_callback = False

    session = get_session(user_id)
    suggestions = session.get("suggestion_queue", [])

    if not suggestions or index >= len(suggestions):
        await finish_suggestions(update_or_query, context)
        return

    s = suggestions[index]
    title = s.get("title", "Untitled")
    desc = s.get("description", "No description")[:300]
    tags = ", ".join(s.get("tags", [])[:5]) or "No tags"
    source = s.get("source", "unknown")
    upvotes = s.get("upvotes", 0)

    source_info = f"☁️ Cloud ({upvotes} ⬆️)" if source == "cloud" else "📱 Local"

    text = (
        f"📋 *Suggestion {index + 1}/{len(suggestions)}*\n\n"
        f"**{title}**\n"
        f"_{source_info}_\n\n"
        f"{desc}\n\n"
        f"🏷️ {tags}\n\n"
        f"---\n"
        f"_Include this pattern in your project?_"
    )

    # Three-button system!
    keyboard = [
        [
            InlineKeyboardButton("👍 Like", callback_data=f"sug_like_{index}"),
            InlineKeyboardButton("👎 Skip", callback_data=f"sug_skip_{index}"),
            InlineKeyboardButton("🚫 Hate", callback_data=f"sug_hate_{index}")
        ],
        []
    ]

    # Navigation
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"sug_nav_{index-1}"))
    if index < len(suggestions) - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"sug_nav_{index+1}"))
    nav_row.append(InlineKeyboardButton("✅ Done", callback_data="sug_done"))
    keyboard[1] = nav_row

    if is_callback:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update_or_query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def finish_suggestions(update_or_query, context):
    """Finish suggestion review and show summary"""
    if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
        user_id = update_or_query.effective_user.id
        query = update_or_query.callback_query
        is_callback = True
    else:
        user_id = update_or_query.effective_user.id
        is_callback = False

    session = get_session(user_id)

    liked = len(session.get("liked_snippets", []))
    hated = len(session.get("hated_snippets", []))
    total = len(session.get("suggestion_queue", []))

    # Clear queue
    session["suggestion_queue"] = []
    session["suggestion_index"] = 0

    text = (
        f"✅ *Suggestions Reviewed!*\n\n"
        f"📊 Summary:\n"
        f"• 👍 Liked: {liked} patterns to include\n"
        f"• 🚫 Hated: {hated} patterns to avoid\n"
        f"• 👎 Skipped: {total - liked - hated}\n\n"
    )

    if hated > 0:
        text += f"⚠️ *{hated} patterns blacklisted* - Ralph will NOT use these!\n\n"

    text += (
        f"Use /cook to generate a PRD that:\n"
        f"✅ Includes patterns you liked\n"
        f"❌ Avoids patterns you hated"
    )

    if is_callback:
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update_or_query.message.reply_text(text, parse_mode="Markdown")


async def handle_suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle suggestion Like/Skip/Hate buttons"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data
    suggestions = session.get("suggestion_queue", [])

    if data.startswith("sug_like_"):
        # LIKED - include in context + UPVOTE for ranking!
        index = int(data.replace("sug_like_", ""))
        if index < len(suggestions):
            snippet = suggestions[index]
            if "liked_snippets" not in session:
                session["liked_snippets"] = []
            session["liked_snippets"].append(snippet)
            logger.info(f"User {user_id} LIKED: {snippet.get('title', '')[:30]}")

            # Track upvote in database (cream rises!)
            recipe_id = snippet.get("id")
            if recipe_id:
                try:
                    await recipe_api.upvote_recipe(recipe_id)
                except Exception as e:
                    logger.debug(f"Upvote tracking failed: {e}")

        # Auto-advance
        next_index = index + 1
        if next_index < len(suggestions):
            await show_suggestion(update, context, next_index)
        else:
            await finish_suggestions(update, context)

    elif data.startswith("sug_skip_"):
        # SKIPPED - just move on (no vote)
        index = int(data.replace("sug_skip_", ""))
        next_index = index + 1
        if next_index < len(suggestions):
            await show_suggestion(update, context, next_index)
        else:
            await finish_suggestions(update, context)

    elif data.startswith("sug_hate_"):
        # HATED - blacklist this pattern + DOWNVOTE!
        index = int(data.replace("sug_hate_", ""))
        if index < len(suggestions):
            snippet = suggestions[index]
            if "hated_snippets" not in session:
                session["hated_snippets"] = []
            session["hated_snippets"].append(snippet)
            logger.info(f"User {user_id} HATED: {snippet.get('title', '')[:30]}")

            # Track downvote in database (garbage sinks!)
            recipe_id = snippet.get("id")
            if recipe_id:
                try:
                    await recipe_api.downvote_recipe(recipe_id)
                except Exception as e:
                    logger.debug(f"Downvote tracking failed: {e}")

        # Auto-advance
        next_index = index + 1
        if next_index < len(suggestions):
            await show_suggestion(update, context, next_index)
        else:
            await finish_suggestions(update, context)

    elif data.startswith("sug_nav_"):
        # Navigate
        index = int(data.replace("sug_nav_", ""))
        await show_suggestion(update, context, index)

    elif data == "sug_done":
        await finish_suggestions(update, context)


def format_snippets_for_prd(liked: list, hated: list) -> str:
    """Format liked and hated snippets for PRD generation"""
    lines = []

    if liked:
        lines.append("## INCLUDE These Patterns (User Approved):")
        for s in liked:
            lines.append(f"- ✅ {s.get('title', 'Unknown')}: {s.get('description', '')[:100]}")
        lines.append("")

    if hated:
        lines.append("## AVOID These Patterns (User Blacklisted):")
        lines.append("DO NOT use these approaches - the user explicitly rejected them!")
        for s in hated:
            lines.append(f"- 🚫 {s.get('title', 'Unknown')}: {s.get('description', '')[:100]}")
        lines.append("")

    return "\n".join(lines)


# ============ RAPID-FIRE SUGGESTIONS (Groq-powered) ============
# Generate 30 feature ideas FAST, user approves/rejects, PRD builds itself!

async def cmd_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generate PRD task blocks for review!

    Flow:
    1. Check for historical highly-ranked suggestions first
    2. Generate new PRD blocks with Mona
    3. Show one at a time for 👍/👎/😈 voting
    4. After voting, block collapses to "Change" button
    5. Dislike triggers conversation to revise
    6. Hate signals builder to avoid similar patterns
    """
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session["project_description"] and not session["conversation"]:
        await update.message.reply_text(
            "💡 *Tell me about your project first!*\n\n"
            "I need context to generate relevant PRD tasks.\n"
            "Describe what you want to build, then use /suggestions",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "*Ralph shuffles papers*\n\n"
        "Lemme get Mona to type up some tasks for ya, boss...\n"
        "_She's real good at the proper writing stuff!_",
        parse_mode="Markdown"
    )

    # Build context from conversation
    context_text = session.get("project_description", "")
    if session["conversation"]:
        recent = session["conversation"][-10:]  # Last 10 messages
        context_text += "\n\nRecent discussion:\n"
        context_text += "\n".join([f"- {m['content'][:150]}" for m in recent])

    # Try to get historical highly-ranked suggestions first
    historical = await get_historical_suggestions(context_text, limit=5)

    # Generate new PRD blocks with Mona
    new_blocks = await generate_prd_blocks(context_text, count=10)

    if not new_blocks and not historical:
        await update.message.reply_text(
            "*Ralph scratches head*\n\n"
            "Mona couldn't come up with anything... Tell me more about your project!",
            parse_mode="Markdown"
        )
        return

    # Combine: historical first (proven good), then new
    all_blocks = historical + new_blocks

    # Store in session
    session["prd_blocks"] = all_blocks
    session["prd_index"] = 0

    # Intro message
    hist_count = len(historical)
    new_count = len(new_blocks)
    intro = f"📋 *Mona typed up {len(all_blocks)} tasks!*\n\n"
    if hist_count > 0:
        intro += f"🌟 {hist_count} community favorites\n"
    intro += f"🤖 {new_count} fresh ideas\n\n"
    intro += "Vote on each: 👍 Like | 👎 Dislike | 😈 Hate\n"
    intro += "_Decisions collapse - tap Change to revote_"

    await update.message.reply_text(intro, parse_mode="Markdown")

    # Show first block
    await show_prd_block(update, context, 0)


async def generate_prd_blocks(context: str, count: int = 10) -> list:
    """
    Generate PRD blocks - the actual task items that will be in the PRD.
    Each block is shown in FULL to the user for approval.

    The block IS the PRD task - 3-5 sentences of real implementation details.
    Like/Dislike/Hate signals are saved for training the builder.
    """
    # COMPACT - saves input tokens
    prompt = f"""Generate {count} PRD tasks as JSON array.

CTX: {context}

Format: [{{"id":N,"title":"3-6 words","description":"2-3 sentences + acceptance criteria","category":"security|core|data|ui|api|testing","priority":"critical|high|medium","complexity":"simple|medium|complex"}}]

Order: security→core→data→api→ui→testing

JSON array only."""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await groq_chat(messages, "llama-3.3-70b-versatile")

        if not response:
            return []

        # Parse JSON from response
        import re
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            blocks = json.loads(json_match.group())
            # Add metadata
            for block in blocks:
                block["source"] = "auto"  # auto-generated
                block["votes"] = {"like": 0, "dislike": 0, "hate": 0}
                block["status"] = "pending"  # pending, approved, rejected, hated
            return blocks[:count]
    except Exception as e:
        logger.error(f"Failed to generate PRD blocks: {e}")

    return []


async def get_historical_suggestions(context: str, limit: int = 5) -> list:
    """
    Fetch highly-ranked historical PRD blocks that match the current context.
    These are shown FIRST before auto-generated ones.
    """
    try:
        # Search recipe API for matching blocks with high ratings
        async with aiohttp.ClientSession() as client:
            async with client.post(
                f"{RECIPE_API_BASE}/search",
                json={
                    "context": context[:1000],  # First 1000 chars for matching
                    "min_likes": 10,  # Only show well-liked suggestions
                    "limit": limit
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    suggestions = data.get("suggestions", [])
                    # Mark these as historical
                    for s in suggestions:
                        s["source"] = "historical"
                        s["community_approved"] = True
                    return suggestions
    except Exception as e:
        logger.debug(f"Historical suggestions unavailable: {e}")

    return []


async def ralph_to_mona_handoff(user_message: str, conversation: list, model: str) -> dict:
    """
    Ralph understands the user's message, then hands off to Mona to write a proper PRD block.
    This is for conversation mode - user talks to Ralph, Mona formats the PRD.

    Returns a single PRD block formatted by Mona.
    """
    # COMPACT - Ralph extracts requirement
    ralph_prompt = f"""Extract core requirement in 1 sentence.
User: {user_message}
Context: {chr(10).join([f"{m['role']}: {m['content'][:50]}" for m in conversation[-3:]])}
Format: "They want X" or "They need Y"."""

    messages = [{"role": "user", "content": ralph_prompt}]
    ralph_understanding = await groq_chat(messages, model or "llama-3.3-70b-versatile")

    if not ralph_understanding:
        return None

    # COMPACT - Mona formats as PRD
    mona_prompt = f"""Convert to PRD task JSON:
"{ralph_understanding}"
Format: {{"title":"3-6 words","description":"2-3 sentences","category":"security|core|data|ui|api|testing","priority":"critical|high|medium","complexity":"simple|medium|complex","ralph_note":"casual 1 sentence"}}"""

    messages = [{"role": "user", "content": mona_prompt}]
    mona_response = await groq_chat(messages, model or "llama-3.3-70b-versatile")

    if not mona_response:
        return None

    try:
        import re
        json_match = re.search(r'\{[\s\S]*\}', mona_response)
        if json_match:
            block = json.loads(json_match.group())
            block["source"] = "conversation"
            block["votes"] = {"like": 0, "dislike": 0, "hate": 0}
            block["status"] = "pending"
            return block
    except Exception as e:
        logger.error(f"Failed to parse Mona's response: {e}")

    return None


async def revise_prd_block(original: dict, user_feedback: str, model: str) -> dict:
    """
    Mona revises a PRD block based on user feedback.
    User said what was wrong, Mona fixes it.
    """
    # COMPACT revision prompt
    prompt = f"""Revise PRD task based on feedback.
Original: {original.get('title', '')} - {original.get('description', '')[:100]}
Feedback: {user_feedback}
JSON: {{"title":"3-6 words","description":"2-3 sentences","category":"{original.get('category', 'core')}","priority":"{original.get('priority', 'medium')}","complexity":"{original.get('complexity', 'medium')}","ralph_note":"1 casual sentence"}}"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await groq_chat(messages, model or "llama-3.3-70b-versatile")

        if not response:
            return None

        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            block = json.loads(json_match.group())
            block["source"] = "revised"
            block["votes"] = original.get("votes", {"like": 0, "dislike": 0, "hate": 0})
            block["status"] = "pending"
            block["revision_of"] = original.get("title", "")
            return block
    except Exception as e:
        logger.error(f"Failed to revise PRD block: {e}")

    return None


async def show_prd_block(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int, collapsed: bool = False):
    """
    Show a single PRD block for voting.

    The FULL block is shown (not hidden) - this IS the PRD task.
    After voting, block collapses to just show title + "Change" button.
    """
    user_id = update.effective_user.id
    session = get_session(user_id)
    blocks = session.get("prd_blocks", [])

    if index >= len(blocks):
        await finish_prd_review(update, context)
        return

    session["prd_index"] = index
    block = blocks[index]
    total = len(blocks)

    # Category badges
    category_badges = {
        "security": "🔒 SECURITY",
        "core": "🎯 CORE",
        "data": "💾 DATA",
        "ui": "🎨 UI/UX",
        "api": "🔌 API",
        "testing": "🧪 TESTING",
        "polish": "✨ POLISH",
        "performance": "⚡ SPEED"
    }

    # Priority badges
    priority_badges = {
        "critical": "🔥 CRITICAL",
        "high": "⭐ HIGH",
        "medium": "📌 MEDIUM",
        "low": "💭 NICE-TO-HAVE"
    }

    # Complexity badges
    complexity_badges = {
        "simple": "🟢 QUICK",
        "medium": "🟡 MODERATE",
        "complex": "🔴 BIG TASK"
    }

    category = block.get("category", "core").lower()
    priority = block.get("priority", "medium").lower()
    complexity = block.get("complexity", "medium").lower()

    cat_badge = category_badges.get(category, "💡")
    pri_badge = priority_badges.get(priority, "📌 MEDIUM")
    comp_badge = complexity_badges.get(complexity, "🟡 MODERATE")

    # Source indicator
    source = block.get("source", "auto")
    if source == "historical":
        source_badge = "🌟 COMMUNITY APPROVED"
    elif source == "conversation":
        source_badge = "💬 FROM CHAT"
    else:
        source_badge = "🤖 AUTO-GENERATED"

    # Get decision status
    status = block.get("status", "pending")

    title = block.get("title", "Untitled Task")
    description = block.get("description", "No description")
    ralph_note = block.get("ralph_note", "")

    # Count decisions made
    liked = len([b for b in blocks if b.get("status") == "liked"])
    disliked = len([b for b in blocks if b.get("status") == "disliked"])
    hated = len([b for b in blocks if b.get("status") == "hated"])

    if collapsed or status != "pending":
        # COLLAPSED VIEW - just title and Change button
        status_emoji = {"liked": "👍", "disliked": "👎", "hated": "😈"}.get(status, "⏳")
        text = f"{status_emoji} *{title}*"

        keyboard = [[InlineKeyboardButton("🔄 Change", callback_data=f"prd_expand_{index}")]]

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    # FULL VIEW - show the complete PRD block
    text = (
        f"📋 *PRD Task {index + 1}/{total}*\n"
        f"{cat_badge} • {pri_badge} • {comp_badge}\n"
        f"{source_badge}\n\n"
        f"*{title}*\n\n"
        f"{description}\n"
    )

    if ralph_note:
        text += f"\n_Ralph's take: \"{ralph_note}\"_\n"

    text += f"\n---\n👍 {liked} | 👎 {disliked} | 😈 {hated}"

    # Build voting keyboard - just emojis, obvious at a glance
    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data=f"prd_like_{index}"),
            InlineKeyboardButton("👎", callback_data=f"prd_dislike_{index}"),
            InlineKeyboardButton("😈", callback_data=f"prd_hate_{index}")
        ],
        [
            InlineKeyboardButton("⏭️ Skip", callback_data=f"prd_skip_{index}"),
            InlineKeyboardButton("🏁 Done", callback_data="prd_done")
        ]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Track edited message for reactions (same message_id)
        if update.callback_query.message:
            track_bot_message(update.callback_query.message.message_id, user_id, "prd_block", block)
    else:
        msg = await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Track for emoji reactions
        track_bot_message(msg.message_id, user_id, "prd_block", block)


# Keep old function for backwards compatibility
async def show_rapid_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int, show_details: bool = False):
    """Legacy function - redirects to new PRD block system"""
    await show_prd_block(update, context, index)


async def handle_rapid_suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle approve/reject callbacks for rapid suggestions"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data
    suggestions = session.get("rapid_suggestions", [])

    if data == "noop":
        return  # Empty button, do nothing

    if data.startswith("rapid_yes_"):
        # APPROVED - add full context to PRD!
        index = int(data.replace("rapid_yes_", ""))
        if index < len(suggestions):
            suggestion = suggestions[index]

            if "approved_features" not in session:
                session["approved_features"] = []
            session["approved_features"].append(suggestion)

            # Track last action for undo
            session["last_rapid_action"] = {"type": "approve", "index": index}

            logger.info(f"User {user_id} APPROVED: {suggestion.get('summary', '')[:50]}")

        # Next!
        await show_rapid_suggestion(update, context, index + 1)

    elif data.startswith("rapid_no_"):
        # REJECTED - note it but don't include
        index = int(data.replace("rapid_no_", ""))
        if index < len(suggestions):
            suggestion = suggestions[index]

            if "rejected_features" not in session:
                session["rejected_features"] = []
            session["rejected_features"].append(suggestion)

            # Track last action for undo
            session["last_rapid_action"] = {"type": "reject", "index": index}

            logger.info(f"User {user_id} REJECTED: {suggestion.get('summary', '')[:50]}")

        # Next!
        await show_rapid_suggestion(update, context, index + 1)

    elif data.startswith("rapid_skip_"):
        # Just skip, no record
        index = int(data.replace("rapid_skip_", ""))
        session["last_rapid_action"] = {"type": "skip", "index": index}
        await show_rapid_suggestion(update, context, index + 1)

    elif data.startswith("rapid_details_"):
        # Show full details for this suggestion
        index = int(data.replace("rapid_details_", ""))
        await show_rapid_suggestion(update, context, index, show_details=True)

    elif data.startswith("rapid_back_"):
        # Go back to previous suggestion
        index = int(data.replace("rapid_back_", ""))
        prev_index = max(0, index - 1)

        # Undo last action if it was on the previous item
        last_action = session.get("last_rapid_action", {})
        if last_action.get("index") == prev_index:
            if last_action.get("type") == "approve":
                # Remove from approved
                approved = session.get("approved_features", [])
                if approved:
                    session["approved_features"] = approved[:-1]
            elif last_action.get("type") == "reject":
                # Remove from rejected
                rejected = session.get("rejected_features", [])
                if rejected:
                    session["rejected_features"] = rejected[:-1]

        await show_rapid_suggestion(update, context, prev_index)

    elif data == "rapid_done":
        await finish_rapid_suggestions(update, context)


async def finish_rapid_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrap up rapid suggestions and show what was approved"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    approved = session.get("approved_features", [])
    rejected = session.get("rejected_features", [])

    # Build summary
    text = (
        f"🏁 *Suggestions Complete!*\n\n"
        f"✅ *{len(approved)} features approved*\n"
        f"❌ *{len(rejected)} features rejected*\n\n"
    )

    if approved:
        text += "*Approved features:*\n"
        for i, f in enumerate(approved[:10], 1):  # Show first 10
            text += f"{i}. {f.get('summary', '')[:60]}...\n"
        if len(approved) > 10:
            text += f"_...and {len(approved) - 10} more_\n"
        text += "\n"

    text += (
        "💾 These features are now part of your PRD context!\n"
        "Use /cook when ready to generate your full PRD."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="Markdown"
        )


def format_approved_features_for_prd(approved: list, rejected: list) -> str:
    """Format rapid-fire approved features for PRD generation"""
    lines = []

    if approved:
        lines.append("## APPROVED FEATURES (User Selected):")
        lines.append("The user explicitly approved these features. Include ALL of them:")
        lines.append("")
        for i, f in enumerate(approved, 1):
            lines.append(f"### Feature {i}: {f.get('summary', 'Unnamed')}")
            lines.append(f.get('full_context', ''))
            lines.append("")

    if rejected:
        lines.append("## REJECTED FEATURES (DO NOT INCLUDE):")
        lines.append("The user explicitly rejected these. Do NOT add them:")
        lines.append("")
        for f in rejected:
            lines.append(f"- ❌ {f.get('summary', '')}")
        lines.append("")

    return "\n".join(lines)


async def handle_prd_block_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Like/Dislike/Hate callbacks for PRD blocks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data
    blocks = session.get("prd_blocks", [])

    if data.startswith("prd_like_"):
        # LIKED - add to PRD!
        index = int(data.replace("prd_like_", ""))
        if index < len(blocks):
            blocks[index]["status"] = "liked"
            blocks[index]["votes"]["like"] += 1
            logger.info(f"User {user_id} LIKED: {blocks[index].get('title', '')}")

        # Show collapsed version, then show next
        await show_prd_block(update, context, index, collapsed=True)
        # Small delay then show next
        await asyncio.sleep(0.3)
        await show_next_pending_block(update, context)

    elif data.startswith("prd_dislike_"):
        # DISLIKED - needs revision, start conversation
        index = int(data.replace("prd_dislike_", ""))
        if index < len(blocks):
            blocks[index]["status"] = "disliked"
            blocks[index]["votes"]["dislike"] += 1
            logger.info(f"User {user_id} DISLIKED: {blocks[index].get('title', '')}")

            # Ralph apologizes and asks how to fix it
            session["revising_block"] = index
            session["waiting_for"] = "prd_revision"

            # Ralph's apology varies
            apologies = [
                "*Ralph winces*\n\nOh no, I messed that one up didn't I? What should I tell Mona to fix?",
                "*Ralph looks down*\n\nSorry Mr. Worms... Mona can do better, I know she can. What should she change?",
                "*Ralph shuffles nervously*\n\nAw man, that wasn't right was it? Tell me what to tell Mona!",
                "*Ralph's face falls*\n\nI shoulda known... What do you want different? Mona will fix it!",
            ]

            await query.edit_message_text(
                f"👎 *{blocks[index].get('title', 'This task')}*\n\n"
                f"{random.choice(apologies)}\n\n"
                f"_Just tell me what's wrong..._",
                parse_mode="Markdown"
            )

    elif data.startswith("prd_hate_"):
        # HATED - strong negative signal, builder should avoid this pattern!
        index = int(data.replace("prd_hate_", ""))
        if index < len(blocks):
            blocks[index]["status"] = "hated"
            blocks[index]["votes"]["hate"] += 1
            logger.info(f"User {user_id} HATED: {blocks[index].get('title', '')}")

        # Show collapsed version with hate indicator, then next
        await show_prd_block(update, context, index, collapsed=True)
        await asyncio.sleep(0.3)
        await show_next_pending_block(update, context)

    elif data.startswith("prd_skip_"):
        # Skip - no record
        index = int(data.replace("prd_skip_", ""))
        await show_next_pending_block(update, context)

    elif data.startswith("prd_expand_"):
        # Expand collapsed block (Change button pressed)
        index = int(data.replace("prd_expand_", ""))
        if index < len(blocks):
            # Reset to pending so it shows full view
            blocks[index]["status"] = "pending"
        await show_prd_block(update, context, index, collapsed=False)

    elif data == "prd_done":
        await finish_prd_review(update, context)


async def show_next_pending_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Find and show the next pending PRD block"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    blocks = session.get("prd_blocks", [])

    # Find next pending block
    for i, block in enumerate(blocks):
        if block.get("status", "pending") == "pending":
            # Send new message for next block
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📋 *Next task...*",
                parse_mode="Markdown"
            )
            # Create a fake update for the new message display
            await show_prd_block_new_message(update, context, i)
            return

    # No more pending blocks
    await finish_prd_review(update, context)


async def show_prd_block_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    """Show PRD block in a new message (not editing existing)"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    blocks = session.get("prd_blocks", [])

    if index >= len(blocks):
        await finish_prd_review(update, context)
        return

    session["prd_index"] = index
    block = blocks[index]
    total = len(blocks)

    # Category badges
    category_badges = {
        "security": "🔒 SECURITY", "core": "🎯 CORE", "data": "💾 DATA",
        "ui": "🎨 UI/UX", "api": "🔌 API", "testing": "🧪 TESTING",
        "polish": "✨ POLISH", "performance": "⚡ SPEED"
    }
    priority_badges = {
        "critical": "🔥 CRITICAL", "high": "⭐ HIGH",
        "medium": "📌 MEDIUM", "low": "💭 NICE-TO-HAVE"
    }
    complexity_badges = {
        "simple": "🟢 QUICK", "medium": "🟡 MODERATE", "complex": "🔴 BIG TASK"
    }

    category = block.get("category", "core").lower()
    priority = block.get("priority", "medium").lower()
    complexity = block.get("complexity", "medium").lower()

    cat_badge = category_badges.get(category, "💡")
    pri_badge = priority_badges.get(priority, "📌 MEDIUM")
    comp_badge = complexity_badges.get(complexity, "🟡 MODERATE")

    source = block.get("source", "auto")
    if source == "historical":
        source_badge = "🌟 COMMUNITY APPROVED"
    elif source == "conversation":
        source_badge = "💬 FROM CHAT"
    else:
        source_badge = "🤖 AUTO-GENERATED"

    title = block.get("title", "Untitled Task")
    description = block.get("description", "No description")
    ralph_note = block.get("ralph_note", "")

    liked = len([b for b in blocks if b.get("status") == "liked"])
    disliked = len([b for b in blocks if b.get("status") == "disliked"])
    hated = len([b for b in blocks if b.get("status") == "hated"])

    text = (
        f"📋 *PRD Task {index + 1}/{total}*\n"
        f"{cat_badge} • {pri_badge} • {comp_badge}\n"
        f"{source_badge}\n\n"
        f"*{title}*\n\n"
        f"{description}\n"
    )

    if ralph_note:
        text += f"\n_Ralph's take: \"{ralph_note}\"_\n"

    text += f"\n---\n👍 {liked} | 👎 {disliked} | 😈 {hated}"

    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data=f"prd_like_{index}"),
            InlineKeyboardButton("👎", callback_data=f"prd_dislike_{index}"),
            InlineKeyboardButton("😈", callback_data=f"prd_hate_{index}")
        ],
        [
            InlineKeyboardButton("⏭️ Skip", callback_data=f"prd_skip_{index}"),
            InlineKeyboardButton("🏁 Done", callback_data="prd_done")
        ]
    ]

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    # Track for emoji reactions (👍❤️ = approve, 👎😡 = reject)
    track_bot_message(msg.message_id, user_id, "prd_block", block)


async def finish_prd_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrap up PRD review and show summary"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    blocks = session.get("prd_blocks", [])

    liked = [b for b in blocks if b.get("status") == "liked"]
    disliked = [b for b in blocks if b.get("status") == "disliked"]
    hated = [b for b in blocks if b.get("status") == "hated"]

    # Store for PRD generation
    session["approved_prd_blocks"] = liked
    session["rejected_prd_blocks"] = disliked + hated
    session["hated_prd_blocks"] = hated  # Extra signal for builder

    text = (
        f"🏁 *PRD Review Complete!*\n\n"
        f"👍 *{len(liked)} tasks approved*\n"
        f"👎 *{len(disliked)} tasks need work*\n"
        f"😈 *{len(hated)} tasks rejected*\n\n"
    )

    if liked:
        text += "*Approved tasks:*\n"
        for i, b in enumerate(liked[:8], 1):
            text += f"  {i}. {b.get('title', '')[:40]}\n"
        if len(liked) > 8:
            text += f"  _...and {len(liked) - 8} more_\n"
        text += "\n"

    if hated:
        text += "*😈 Builder will AVOID patterns like:*\n"
        for b in hated[:3]:
            text += f"  • {b.get('title', '')[:40]}\n"
        text += "\n"

    text += "💾 *Ready for PRD generation!*"

    # Add action buttons
    keyboard = [
        [InlineKeyboardButton("🍳 Cook PRD Now", callback_data="action_cook")],
        [InlineKeyboardButton("🆕 New Project", callback_data="load_new")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def handle_analysis_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle analysis continue/stop/run-all callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    session = get_session(user_id)
    data = query.data

    if data == "analysis_continue":
        # Continue with another batch of 10
        exchange_count = session.get("debate_exchange_count", 0)
        session["analyzing"] = True
        session["analysis_paused"] = False

        await query.edit_message_text(
            f"▶️ *Continuing analysis...*\n\n"
            f"_Starting from exchange {exchange_count + 1}_",
            parse_mode="Markdown"
        )

        # Run another batch
        task = asyncio.create_task(
            run_analyst_debate(update, context, user_id, chat_id, continue_from=exchange_count)
        )
        session["analysis_task"] = task

    elif data == "analysis_finish":
        # Stop and generate summary
        session["analysis_paused"] = False
        debate_messages = session.get("debate_messages", [])
        exchange_count = session.get("debate_exchange_count", 0)

        if debate_messages:
            await query.edit_message_text(
                "🛑 *Stopping analysis...*\n\n"
                "_Generating summary from collected insights..._",
                parse_mode="Markdown"
            )

            # Get project context for summary
            project_context = f"Project: {session.get('project_name', 'Unnamed')}\n"
            project_context += f"Description: {session.get('project_description', 'No description')}\n"

            model = session.get("model") or "llama-3.3-70b-versatile"
            provider = session.get("provider", "groq")

            await _finalize_analysis(
                context, chat_id, user_id, session, debate_messages,
                exchange_count, model, provider, project_context
            )
        else:
            await query.edit_message_text(
                "🛑 *Analysis stopped.*\n\n"
                "_No insights collected yet._",
                parse_mode="Markdown",
                reply_markup=get_keyboard(True, analyzing=False)
            )

    elif data == "analysis_run_all":
        # Run all remaining exchanges without pausing
        exchange_count = session.get("debate_exchange_count", 0)
        session["analyzing"] = True
        session["analysis_paused"] = False

        # Temporarily set batch size very high by modifying behavior
        # We'll run with a higher batch size
        await query.edit_message_text(
            f"⏭️ *Running all remaining exchanges...*\n\n"
            f"_Continuing from {exchange_count}. Will stop at 50 max._",
            parse_mode="Markdown"
        )

        # Run debate with large batch (effectively no pause)
        session["run_all_mode"] = True
        task = asyncio.create_task(
            run_analyst_debate(update, context, user_id, chat_id, continue_from=exchange_count)
        )
        session["analysis_task"] = task


async def handle_cloud_session_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cloud session loading and pagination"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data

    if data.startswith("cloud_load_"):
        # Load session from cloud
        session_id = data.replace("cloud_load_", "")

        await query.edit_message_text("⏳ Loading session...")

        loaded = await session_cloud.load_from_cloud(session_id)

        if loaded:
            # Update current session with loaded data
            session["session_id"] = loaded.get("session_id")
            session["project_name"] = loaded.get("project_name", "")
            session["project_description"] = loaded.get("project_description", "")
            session["conversation"] = loaded.get("conversation", [])
            session["visual_context"] = loaded.get("metadata", {}).get("visual_context", [])

            # Show loaded session
            title = loaded.get("title", "Untitled")
            msg_count = len(session["conversation"])

            await query.edit_message_text(
                f"✅ *Loaded: {title}*\n\n"
                f"📋 Project: {session['project_name'] or 'Unnamed'}\n"
                f"💬 Messages: {msg_count}\n\n"
                f"_Continue chatting or /cook when ready!_",
                parse_mode="Markdown"
            )

            # Show last exchange if any
            if session["conversation"]:
                last = session["conversation"][-1]
                if last["role"] == "assistant":
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"*Last message:*\n\n{last['content'][:500]}",
                        parse_mode="Markdown",
                        reply_markup=get_keyboard(True)
                    )
        else:
            await query.edit_message_text(
                "❌ Couldn't load session. It may have been deleted.\n"
                "Use /history to see available sessions."
            )

    elif data.startswith("cloud_page_"):
        # Pagination
        page = int(data.replace("cloud_page_", ""))
        sessions = await session_cloud.list_cloud_sessions(user_id)
        keyboard = session_cloud.format_session_buttons(sessions, page=page)

        per_page = 10
        start = page * per_page
        end = min(start + per_page, len(sessions))

        text = f"📚 *Sessions {start + 1}-{end} of {len(sessions)}*\n\n"

        for i, s in enumerate(sessions[start:end], start + 1):
            title = s.get("title", "Untitled")[:35]
            updated = s.get("updated_at", "")[:10]
            text += f"{i}. *{title}*\n"
            text += f"   _{updated}_\n\n"

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ============ INLINE FEEDBACK SYSTEM ============
# Quick 👍/👎 buttons for feature/idea suggestions during discovery

async def detect_suggestion_in_response(response: str) -> tuple:
    """
    Detect if Ralph's response contains a suggestion/feature/idea that needs feedback.
    Returns (needs_feedback: bool, suggestion_text: str, button_type: str)

    Button types: 'like', 'agree', 'want', 'include'
    """
    response_lower = response.lower()

    # Patterns that suggest Ralph is proposing something
    suggestion_patterns = [
        # Questions asking for opinion
        ("what do you think", "agree"),
        ("would you like", "want"),
        ("should we", "agree"),
        ("do you want", "want"),
        ("how about", "like"),
        ("what if we", "like"),
        ("maybe we could", "like"),
        ("we could add", "include"),
        ("we could include", "include"),
        ("you might want", "want"),
        ("sound good", "agree"),
        ("does that sound", "agree"),
        ("would that work", "agree"),
        ("you interested in", "want"),
        # Feature suggestions
        ("feature", "include"),
        ("functionality", "include"),
        ("capability", "include"),
    ]

    for pattern, button_type in suggestion_patterns:
        if pattern in response_lower:
            # Extract the suggestion context (last sentence or clause)
            sentences = response.replace("?", ".").replace("!", ".").split(".")
            suggestion = sentences[-2] if len(sentences) > 1 else response[:100]
            suggestion = suggestion.strip()[:80]
            return True, suggestion, button_type

    # Check for question marks (Ralph asking something)
    if "?" in response and len(response) > 50:
        # Find the question
        for sentence in response.split("?"):
            if len(sentence.strip()) > 20:
                return True, sentence.strip()[:80], "like"

    return False, "", ""


def get_feedback_buttons(button_type: str, message_id: int) -> InlineKeyboardMarkup:
    """Generate context-appropriate feedback buttons"""
    button_configs = {
        "like": ("👍 I like that!", "👎 Not for me"),
        "agree": ("✅ I agree", "❌ I disagree"),
        "want": ("🙋 Yes, I want that!", "🙅 No thanks"),
        "include": ("➕ Include it!", "➖ Skip it"),
    }

    pos_text, neg_text = button_configs.get(button_type, ("👍 Like", "👎 Dislike"))

    keyboard = [[
        InlineKeyboardButton(pos_text, callback_data=f"fb_yes_{message_id}"),
        InlineKeyboardButton(neg_text, callback_data=f"fb_no_{message_id}")
    ]]

    return InlineKeyboardMarkup(keyboard)


async def handle_feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle feedback button clicks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data

    # Parse the feedback
    liked = data.startswith("fb_yes_")

    # Get the pending feedback context
    pending = session.get("pending_feedback")

    if pending:
        # Save the preference
        preference = {
            "feature": pending.get("suggestion", ""),
            "liked": liked,
            "context": pending.get("response", "")[:200],
            "timestamp": datetime.now().isoformat()
        }

        if "preferences" not in session:
            session["preferences"] = []
        session["preferences"].append(preference)

        # Clear pending
        session["pending_feedback"] = None

        # Update the message to show choice was recorded
        original_text = query.message.text
        choice_indicator = "✅ Noted!" if liked else "❌ Noted!"

        # Remove the buttons and add a small note
        await query.edit_message_text(
            original_text + f"\n\n_{choice_indicator}_",
            parse_mode="Markdown"
        )

        logger.info(f"User {user_id} feedback: {'liked' if liked else 'disliked'} - {preference['feature'][:50]}")
    else:
        # No pending feedback, just acknowledge
        await query.edit_message_text(
            query.message.text,
            parse_mode="Markdown"
        )


def format_preferences_for_prd(preferences: list) -> str:
    """Format user preferences for inclusion in PRD generation"""
    if not preferences:
        return ""

    lines = ["## User Preferences (from discovery conversation):\n"]

    liked = [p for p in preferences if p.get("liked")]
    disliked = [p for p in preferences if not p.get("liked")]

    if liked:
        lines.append("### Features the user WANTS:")
        for p in liked:
            lines.append(f"- ✅ {p['feature']}")
        lines.append("")

    if disliked:
        lines.append("### Features the user does NOT want:")
        for p in disliked:
            lines.append(f"- ❌ {p['feature']}")
        lines.append("")

    return "\n".join(lines)


async def handle_recipe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle recipe loading from button clicks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data

    if data.startswith("recipe_load_"):
        recipe_id = data.replace("recipe_load_", "")
        loaded_recipe = recipe_api.load_recipe(recipe_id)

        if loaded_recipe:
            session["recipe_id"] = loaded_recipe.id
            session["project_name"] = loaded_recipe.name
            session["project_description"] = loaded_recipe.description
            session["phase"] = "chatting"

            task_count = len(loaded_recipe.prd.get("tasks", []))

            await query.edit_message_text(
                f"🎉 *Recipe Loaded!*\n\n"
                f"**{loaded_recipe.name}**\n"
                f"_{loaded_recipe.description[:100]}_\n\n"
                f"📋 {task_count} tasks\n\n"
                f"Chat to modify, or /cook to build!",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"😕 Recipe not found: `{recipe_id}`",
                parse_mode="Markdown"
            )

    elif data == "recipe_search":
        await query.edit_message_text(
            "🔍 *Search Recipes*\n\n"
            "Type `/recipes <search term>` to find recipes!\n\n"
            "Examples:\n"
            "• `/recipes telegram bot`\n"
            "• `/recipes web scraper`\n"
            "• `/recipes api server`",
            parse_mode="Markdown"
        )


async def cmd_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show donation link"""
    await update.message.reply_text(
        "☕ *Support Ralph's Creator*\n\n"
        "If Ralph helped you today, buy Snail a coffee!\n\n"
        "https://buymeacoffee.com/snail3d\n\n"
        "_I been working real hard mister..._",
        parse_mode="Markdown"
    )


async def cmd_install_ralph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate TeleRalph installer PRD"""
    await update.message.reply_text(
        "📥 *Generating Ralph Installer...*\n\n"
        "_Ralph gets his cooking stuff ready..._",
        parse_mode="Markdown"
    )

    # Create the installer PRD
    installer_prd = {
        "pn": "TeleRalph Installer",
        "pd": "Install TeleRalph - a Telegram bot that turns project ideas into compressed PRDs for Claude Code",
        "sp": """Complete build instructions for TeleRalph - Telegram bot that generates compressed PRDs.

RUN THIS FIRST: claude --dangerously-skip-permissions

SECURITY FIRST: .gitignore with .env,*.pyc,__pycache__,venv,sessions,recipes. .env.example with placeholders. NEVER commit .env.

CRITICAL: After EACH task, commit+push to GitHub immediately. No batching. Keep GitHub in sync.

REAL-TIME PREVIEW: If possible, run project in real-time as you build. For websites: open preview ASAP, update at every step. Preview should work minimized/maximized, updating in background. Prioritize getting preview running early.

README UPDATES (every pass): Update README.md top boldly: 'ACTIVE BUILD IN PROGRESS - Pass X/XX (Iteration Y/YY)'. Track counts. Update install instructions - prioritize SIMPLEST method if same cost.

FINAL TASK: Change header to 'BUILD COMPLETE 🎉'. Add at BOTTOM: 'Built with TeleRalph - Welcome to Ralph's Kitchen. He mixes your sauce. Get your own Ralph at: https://github.com/Snail3D/ralphmode.com'

DEDICATED README PASS: ONE dedicated README.md pass (last/near-last). Search codebase, identify hottest functions, write clear install docs, document usage. Last task: Dockerize if possible. Install AT TOP - simplest method优先.

SETUP: Get Telegram Bot Token from @BotFather (/newbot). Get Groq API Key from https://console.groq.com (FREE!). Choose: Docker (recommended) or Python.

DOCKER: docker build -t teleralph . && docker run -d --name teleralph --env-file .env --restart unless-stopped teleralph

PYTHON: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python ralph_telegram.py

Verify: Send /start to your bot in Telegram.""",
        "ts": {
            "lang": "Python",
            "fw": "python-telegram-bot",
            "db": "None",
            "oth": ["Groq API", "Telegram Bot API", "Docker"]
        },
        "fs": [
            "ralph_telegram.py",
            "recipe_api.py",
            "session_manager.py",
            "session_cloud.py",
            "Dockerfile",
            "requirements.txt",
            ".env.example",
            "README.md",
            ".gitignore"
        ],
        "cmd": {
            "su": "pip install -r requirements.txt",
            "ru": "python ralph_telegram.py",
            "te": "pytest",
            "docker_build": "docker build -t teleralph .",
            "docker_run": "docker run -d --name teleralph --env-file .env --restart unless-stopped teleralph"
        },
        "p": {
            "00_security": {
                "n": "Security",
                "t": [
                    {"i": "SEC-001", "ti": "C .gitignore", "d": "Exclude .env, *.pyc, __pycache__, venv, sessions, recipes", "f": ".gitignore", "pr": "critical"},
                    {"i": "SEC-002", "ti": "C .env.example", "d": "Template with TELEGRAM_BOT_TOKEN and GROQ_API_KEY placeholders", "f": ".env.example", "pr": "critical"},
                    {"i": "SEC-003", "ti": "V .env exists", "d": "Ensure .env file with real tokens, never commit", "f": ".env", "pr": "critical"}
                ]
            },
            "01_setup": {
                "n": "Setup",
                "t": [
                    {"i": "SET-001", "ti": "Clone repo", "d": "git clone https://github.com/Snail3D/ralphmode.com.git && cd ralphmode.com", "f": "terminal", "pr": "high"},
                    {"i": "SET-002", "ti": "Get Bot Token", "d": "Message @BotFather on Telegram, use /newbot command", "f": "telegram", "pr": "high"},
                    {"i": "SET-003", "ti": "Get Groq Key", "d": "Visit https://console.groq.com, create free account, generate API key", "f": "groq.com", "pr": "high"},
                    {"i": "SET-004", "ti": "C .env file", "d": "Copy .env.example to .env, fill in real tokens", "f": ".env", "pr": "high"}
                ]
            },
            "02_core": {
                "n": "Core Installation",
                "t": [
                    {"i": "COR-001", "ti": "I dependencies", "d": "pip install -r requirements.txt or docker build", "f": "requirements.txt", "pr": "high"},
                    {"i": "COR-002", "ti": "Run bot", "d": "python ralph_telegram.py OR docker run -d --name teleralph --env-file .env teleralph", "f": "docker", "pr": "high"},
                    {"i": "COR-003", "ti": "V bot running", "d": "Send /start to your bot in Telegram, should respond", "f": "telegram", "pr": "high"}
                ]
            },
            "03_api": {
                "n": "Optional Configuration",
                "t": [
                    {"i": "API-001", "ti": "Ollama setup", "d": "Install Ollama from ollama.com for local AI, pull model: ollama pull phi3", "f": "ollama", "pr": "low"},
                    {"i": "API-002", "ti": "Docker logs", "d": "docker logs -f teleralph to see bot activity", "f": "docker", "pr": "low"}
                ]
            },
            "04_test": {
                "n": "Testing",
                "t": [
                    {"i": "TES-001", "ti": "V bot responds", "d": "Send 'hello' to bot, should get confused Ralph response", "f": "telegram", "pr": "high"},
                    {"i": "TES-002", "ti": "T PRD gen", "d": "Describe a project, tap 'Cook Sauce', verify PRD file generated", "f": "telegram", "pr": "high"}
                ]
            }
        }
    }

    # Compress the PRD
    compressed_installer = compress_prd(installer_prd)

    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"teleralph_installer_{timestamp}.txt"

    with open(filename, 'w') as f:
        f.write(compressed_installer)

    # Send the file
    with open(filename, 'rb') as f:
        await update.message.reply_document(
            document=f,
            filename=filename,
            caption=(
                f"📥 *TeleRalph Installer PRD*\n\n"
                f"Feed this to Claude Code and it'll install TeleRalph for you!\n\n"
                f"🍳 *What it does:*\n"
                f"• Clone the repo\n"
                f"• Set up .env file\n"
                f"• Install dependencies\n"
                f"• Run with Docker or Python\n\n"
                f"_Ralph packs his lunch pail_ 🍱\n\n"
                f"Use: `claude --dangerously-skip-permissions`"
            ),
            parse_mode="Markdown"
        )

    # Clean up
    os.unlink(filename)


async def cmd_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show model provider selection menu"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    current_provider = session.get("provider", "groq")
    current_model = session.get("model", "llama-3.3-70b-versatile")

    # Both Groq (cloud) and Ollama (local) options
    keyboard = [
        [InlineKeyboardButton("⚡ Groq (Cloud, Fast)", callback_data="provider_groq")],
        [InlineKeyboardButton("🏠 Ollama (Local, Private)", callback_data="provider_ollama")],
        [InlineKeyboardButton("⚙️ Set Groq API Key", callback_data="groq_set_key")]
    ]

    provider_emoji = "⚡" if current_provider == "groq" else "🏠"
    text = (
        f"🧠 *Model Settings*\n\n"
        f"{provider_emoji} Current: `{current_model}`\n\n"
        f"Choose your AI provider:\n"
        f"⚡ Groq - Cloud, fast, free\n"
        f"🏠 Ollama - Local, private, runs on your machine"
    )

    # Handle both callback queries and regular messages
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_ollama_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show local Ollama models"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    query = update.callback_query

    await query.edit_message_text("🏠 _Scanning local models..._", parse_mode="Markdown")

    models = await list_ollama_models()
    current = session.get("model", "none")

    if not models:
        keyboard = [
            [InlineKeyboardButton("📖 Install Ollama", url="https://ollama.com")],
            [InlineKeyboardButton("🔙 Back", callback_data="model_back_main")]
        ]
        await query.edit_message_text(
            "🏠 *Local Models (Ollama)*\n\n"
            "No local models found!\n\n"
            "1. Install Ollama: https://ollama.com\n"
            "2. Run: `ollama pull phi3` (3B model)\n"
            "3. Or: `ollama pull gemma2:2b` (2B model)\n\n"
            "Small models = fast, private, free!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Build keyboard with models
    keyboard = []
    for model in models[:10]:  # Show top 10
        model_id = model["id"]
        is_current = "✓ " if model_id == current else ""
        size_info = f" ({model['size']})" if model.get("size") else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{is_current}{model['name']}{size_info}",
                callback_data=f"select_model_ollama_{model_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="provider_ollama")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="model_back_main")])

    await query.edit_message_text(
        "🏠 *Local Models (Ollama)*\n\n"
        "Running on your machine!\n"
        "Small = fast, private, free",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_groq_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Groq cloud models - sorted by quality"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    query = update.callback_query

    await query.edit_message_text("⚡ _Fetching latest Groq models..._", parse_mode="Markdown")

    # Refresh model info from API
    await fetch_groq_model_info_from_web()

    models = await list_groq_models()
    current = session.get("model", "none")

    if not models:
        keyboard = [
            [InlineKeyboardButton("⚙️ Set API Key", callback_data="groq_set_key")],
            [InlineKeyboardButton("🔙 Back", callback_data="model_back_main")]
        ]
        await query.edit_message_text(
            "⚡ *Groq Models*\n\n"
            "Couldn't fetch models. Check your API key!\n\n"
            "Get one free at: https://console.groq.com",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Two-column layout: [Select Model] [Info]
    keyboard = []
    for m in models[:12]:
        model_id = m["id"]
        check = "✅ " if model_id == current else ""

        # Get quality tier for stars
        quality = m.get("quality", GROQ_MODEL_QUALITY.get(model_id, 1))
        stars = "⭐" * min(quality, 5)

        # Better short name extraction
        if "/" in model_id:
            short_name = model_id.split("/")[-1][:20]
        elif "-" in model_id:
            parts = model_id.split("-")
            short_name = parts[0].title() + ("-" + parts[1] if len(parts) > 1 else "")
        else:
            short_name = model_id[:20]

        ctx = f"{m['context']//1000}k" if m.get('context') and m['context'] > 0 else ""

        keyboard.append([
            InlineKeyboardButton(f"{check}{stars} {short_name}", callback_data=f"model_select_groq_{model_id}"),
            InlineKeyboardButton("ℹ️", callback_data=f"model_info_groq_{model_id}")
        ])

    keyboard.append([InlineKeyboardButton("⚙️ Set API Key", callback_data="groq_set_key")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="model_back_main")])

    await query.edit_message_text(
        f"⚡ *Groq Models (Cloud)*\n\n"
        f"Current: `{current}`\n\n"
        f"⭐ = Quality tier (more = better)\n"
        f"Models sorted by quality - best first!\n\n"
        f"_Free tier: 30 req/min_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle model selection callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_session(user_id)
    data = query.data

    # Provider selection
    if data == "provider_ollama":
        session["provider"] = "ollama"
        await show_ollama_models(update, context)
        return

    elif data == "provider_groq":
        session["provider"] = "groq"
        # Auto-select best available model if none set
        if not session.get("model") or session.get("model") == "none":
            best_model = await get_best_groq_model()
            session["model"] = best_model
            logger.info(f"Auto-selected best Groq model: {best_model}")
        await show_groq_models(update, context)
        return

    elif data == "model_back_main":
        # Go back to main model provider selection
        await cmd_models(update, context)
        return

    # Local model selection
    elif data.startswith("model_select_local_"):
        model = data[19:]
        session["model"] = model
        session["provider"] = "local"
        await query.edit_message_text(
            f"✅ *Switched to Local:* `{model}`\n\n"
            f"*Ralph taps his head* I got a local brain now, boss!",
            parse_mode="Markdown"
        )

    # Groq model selection
    elif data.startswith("model_select_groq_"):
        model = data[18:]
        session["model"] = model
        session["provider"] = "groq"
        await query.edit_message_text(
            f"✅ *Switched to Groq:* `{model}`\n\n"
            f"*Ralph points to the cloud* Using the fast cloud brain now!",
            parse_mode="Markdown"
        )

    # Ollama model selection
    elif data.startswith("select_model_ollama_"):
        model = data[21:]
        session["model"] = model
        session["provider"] = "ollama"
        await query.edit_message_text(
            f"✅ *Switched to Ollama:* `{model}`\n\n"
            f"*Ralph taps his head* I got a local brain now! Running on your machine, boss!",
            parse_mode="Markdown"
        )

    # Model info buttons
    elif data.startswith("model_info_local_"):
        model = data[17:]
        # Legacy local model info - redirect to Groq
        await query.edit_message_text(
            f"⚡ *We Use Groq Now!*\n\n"
            f"Local models have been retired.\n"
            f"Groq is faster and free! 🚀",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⚡ Go to Groq Models", callback_data="provider_groq")
            ]])
        )

    elif data.startswith("model_info_groq_"):
        model = data[16:]
        info_url = GROQ_MODEL_INFO.get(model, "https://console.groq.com/docs/models")
        await query.edit_message_text(
            f"ℹ️ *{model}*\n\n"
            f"Groq cloud model - FAST inference!\n\n"
            f"• Free tier: 30 req/min\n"
            f"• Very fast (LPU hardware)\n"
            f"• Requires API key\n\n"
            f"More info: {info_url}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="provider_groq")
            ]])
        )

    # Groq API key
    elif data == "groq_set_key":
        await query.edit_message_text(
            "⚙️ *Set Groq API Key*\n\n"
            "Send me your Groq API key.\n\n"
            "Get one free at: https://console.groq.com/keys\n\n"
            "_Just paste the key and send it!_",
            parse_mode="Markdown"
        )
        session["waiting_for"] = "groq_api_key"

    # Old model selection (backwards compat)
    elif data.startswith("model_select_"):
        model = data[13:]
        session["model"] = model
        await query.edit_message_text(
            f"✅ *Switched to:* `{model}`\n\n"
            f"I'll use this brain now, boss!",
            parse_mode="Markdown"
        )

    elif data == "model_search":
        # Model search no longer needed - just use Groq
        await query.edit_message_text(
            "⚡ *Groq Models*\n\n"
            "No search needed! Groq has the best models ready to go.\n"
            "Tap below to pick one!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⚡ See Groq Models", callback_data="provider_groq")
            ]])
        )

    elif data.startswith("model_pull_"):
        model = data[11:]
        await query.edit_message_text(
            f"📥 *Downloading:* `{model}`\n\n"
            f"This might take a few minutes...\n"
            f"_I'll let you know when it's ready!_",
            parse_mode="Markdown"
        )

        # Pull the model
        success = await pull_model_with_progress(update, model)

        if success:
            session["model"] = model
            session["provider"] = "local"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ *Got it!* `{model}` is ready!\n\nI'll use this brain now.",
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Couldn't download `{model}`. Try another one?",
                parse_mode="Markdown"
            )


async def pull_model_with_progress(update: Update, model_name: str) -> bool:
    """Pull a model - no longer supported, use Groq"""
    return False


async def handle_model_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle model search request - redirect to Groq"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    # Clear the waiting state
    session["waiting_for"] = None

    await update.message.reply_text(
        "🔍 *Model Search*\n\n"
        "We use Groq now - no downloads needed! ⚡\n\n"
        "Use /models to see available Groq models.",
        parse_mode="Markdown"
    )


async def generate_auto_title(update: Update, context: ContextTypes.DEFAULT_TYPE, session: Dict):
    """Generate a 2-3 word project title using AI and update project_name"""
    try:
        # Get recent conversation context
        recent_msgs = session["conversation"][-3:]
        context_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_msgs])

        # Generate title
        model = session.get("model") or "llama-3.3-70b-versatile"
        provider = session.get("provider", "groq")

        prompt = f"""Based on this conversation, generate a 2-3 word project title.

Conversation:
{context_text}

Rules:
- Max 3 words
- Use Title Case
- Be descriptive but concise
- Examples: "Task Manager Bot", "Weather API", "Portfolio Site"

Respond with ONLY the title, nothing else."""

        if provider == "ollama":
            title = await ollama_chat([{"role": "user", "content": prompt}], model)
        else:
            title = await groq_chat([{"role": "user", "content": prompt}], model)

        if title:
            # Clean up the title
            title = title.strip().strip('"').strip("'")
            # Add "TeleRalph PRD" prefix
            new_title = f"TeleRalph PRD - {title}"

            # Update session
            session["project_name"] = new_title[:50]  # Limit length
            session["auto_title_generated"] = True

            # Tell user
            await update.message.reply_text(
                f"📝 *Title Generated!*\n\n"
                f"I'm calling this: `{new_title}`\n\n"
                f"_Ralph nods thoughtfully_",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Auto-title generation failed: {e}")


async def process_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Process user text input - core logic shared between text messages and voice transcription.
    This is the main conversation handler.
    """
    user_id = update.effective_user.id
    session = get_session(user_id)

    # Check if user is asking about a previous image
    image_id, question = check_for_image_followup(text)
    if image_id:
        await handle_image_followup(update, context, image_id, question)
        return

    # If user sends a message while analysis is running, stop it
    if session.get("analyzing"):
        if session.get("analysis_task"):
            session["analysis_task"].cancel()
        session["analyzing"] = False

        analysis_count = len(session.get("analysis_context", []))
        await update.message.reply_text(
            f"🛑 *Analysis paused* ({analysis_count} exchanges)\n\n"
            f"We've been doing a lot of talking! I think that's going to help your builder bot big time.\n\n"
            f"_Let me respond to you now..._",
            parse_mode="Markdown",
            reply_markup=get_keyboard(True, analyzing=False)
        )
        # Continue to process their message below

    # Check if we have a model - default to Groq
    if not session.get("model"):
        session["model"] = "llama-3.3-70b-versatile"
        session["provider"] = "groq"

    # Start chatting if idle
    if session["phase"] == "idle":
        session["phase"] = "chatting"

    # Add to conversation (with reply-to context if applicable)
    user_content = text
    if update.message and update.message.reply_to_message:
        replied_msg = update.message.reply_to_message
        if replied_msg.text:
            user_content = f"[Replying to: \"{replied_msg.text[:100]}\"]\n\n{text}"
        elif replied_msg.caption:
            user_content = f"[Replying to: \"{replied_msg.caption[:100]}\"]\n\n{text}"

    session["conversation"].append({"role": "user", "content": user_content})

    # Extract project name from first message (smarter extraction)
    if not session["project_name"] and len(session["conversation"]) == 1:
        words = text.lower().split()
        # Look for keywords with surrounding context
        for i, word in enumerate(words):
            if word in ['bot', 'app', 'website', 'api', 'tool', 'scraper', 'game', 'tracker', 'system', 'platform']:
                # Get 2-3 words before and after the keyword
                start = max(0, i-2)
                end = min(len(words), i+3)
                candidate = ' '.join(words[start:end])
                # Clean up and title case
                session["project_name"] = candidate.strip().title()[:40]
                break

        # Fallback: use first few meaningful words
        if not session["project_name"]:
            meaningful_words = [w for w in words if len(w) > 2][:4]
            if meaningful_words:
                session["project_name"] = ' '.join(meaningful_words).title()[:40]
            else:
                session["project_name"] = "My Project"

    # Auto-generate better project name/title after 2-3 messages
    conv_count = len(session["conversation"])
    if (conv_count >= 2 and conv_count <= 3 and
        not session.get("auto_title_generated") and
        session.get("project_name") in ["My Project", "", None]):

        # Generate title using AI
        await generate_auto_title(update, context, session)

    session["project_description"] += text + " "

    # Send typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Check if Ralph needs to search the interwebs
    web_context = ""
    needs_search, search_term = await ralph_needs_to_search(text, session["conversation"], session["model"])

    if needs_search and search_term:
        # Ralph runs to his compooter!
        await update.message.reply_text(
            get_ralph_search_message(),
            parse_mode="Markdown"
        )

        # Do the DDG search (quick, just top results)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        search_results = await web_search(search_term, max_results=3)

        if search_results and not search_results.startswith("["):
            web_context = search_results
            await update.message.reply_text(
                get_ralph_search_done_message(search_term),
                parse_mode="Markdown"
            )

    # Get Smithers response (with web context if he searched)
    # Always use Groq - fast and reliable!
    model = session.get("model") or "llama-3.3-70b-versatile"

    # Use our local get_time_context and SMITHERS_SYSTEM_TEMPLATE (defined at top of file)
    time_ctx = get_time_context()
    system_prompt = SMITHERS_SYSTEM_TEMPLATE.format(**time_ctx)

    # Track if we have asked about GitHub (FIRST question)
    conv_count = len(session["conversation"])
    asked_github = session.get("asked_github", False)
    going_to_github = session.get("going_to_github", None)

    # Track if we've asked about inspiration (ask after 2-4 exchanges)
    asked_inspiration = session.get("asked_inspiration", False)
    has_inspiration = session.get("inspiration_sources", [])

    # === EARLY GITHUB QUESTION (FIRST question after greeting) ===
    # Ask if project is going to GitHub - use Yes/No buttons
    if not asked_github and conv_count == 1:
        # This is the first real exchange after greeting - ask about GitHub
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, to GitHub sir!", callback_data="github_yes")],
            [InlineKeyboardButton("No, local build sir", callback_data="github_no")]
        ])

        await update.message.reply_text(
            "*bows*\n\n"
            "Welcome back, Mr. Worms sir! Will this project be going to the GitHub, sir?\n\n"
            "_I need to know so I can prepare the proper build instructions for you._",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        # Mark as asked and wait for response - don't process the text yet
        session["asked_github"] = True
        session["waiting_for_github"] = True
        return

    # If we're waiting for GitHub answer, don't process regular text
    if session.get("waiting_for_github"):
        await update.message.reply_text(
            "*patiently waits*\n\n"
            "Please select Yes or No above, Mr. Worms sir, so I may proceed appropriately.",
            parse_mode="Markdown"
        )
        return

    # Add GitHub context to system prompt
    if going_to_github is True:
        system_prompt += "\n\n[User wants this on GitHub - include GitHub setup, pushing, remote repo]"
    elif going_to_github is False:
        system_prompt += "\n\n[User wants local build - NO GitHub, focus on making it work beautifully locally]"

    # Hint to Ralph about inspiration state
    if not asked_inspiration and conv_count >= 3 and conv_count <= 6:
        system_prompt += "\n\n[HINT: Good time to ask about inspiration sources - websites, similar projects, etc. Ask ONCE.]"
        session["asked_inspiration"] = True  # Mark as asked
    elif asked_inspiration and not has_inspiration:
        system_prompt += "\n\n[User has no inspiration sources - don't ask again]"
    elif has_inspiration:
        system_prompt += f"\n\n[User's inspiration: {', '.join(has_inspiration[:3])}]"

    # Check if user just gave inspiration sources (URLs or project names)
    text_lower = text.lower()
    url_analysis_comment = None  # Ralph's comment on any URL shared

    if any(x in text_lower for x in ['http', 'www.', '.com', '.io', 'github', 'like ', 'similar to', 'inspired by']):
        # Extract URLs
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
        if urls:
            session.setdefault("inspiration_sources", []).extend(urls[:3])

            # Analyze each URL for inspiration (limit to 2 to avoid delay)
            project_context = session.get("project_description", "")
            if session.get("project_name"):
                project_context = f"{session['project_name']}: {project_context}"

            for url in urls[:2]:
                try:
                    analysis = await analyze_inspiration_url(url, project_context)
                    if analysis and not analysis.get("error"):
                        # Store analysis
                        session.setdefault("inspiration_analysis", []).append(analysis)
                        # Generate Ralph's comment
                        url_analysis_comment = await get_ralph_url_comment(analysis, session)
                except Exception as e:
                    logger.debug(f"URL inspiration analysis failed: {e}")

        # Also capture project names mentioned
        for phrase in ['like ', 'similar to ', 'inspired by ', 'based on ']:
            if phrase in text_lower:
                idx = text_lower.find(phrase)
                mention = text[idx + len(phrase):].split()[0:3]
                if mention:
                    session.setdefault("inspiration_sources", []).append(' '.join(mention))

    if web_context:
        system_prompt += f"\n\n[You searched and learned:\n{web_context}]"

    # Add analysis context if available (so Ralph knows what analysts discussed)
    analysis_ctx = session.get("analysis_context", {})
    if analysis_ctx:
        summary = analysis_ctx.get("summary", "")
        exchange_count = analysis_ctx.get("exchange_count", 0)
        if summary:
            system_prompt += f"\n\n[ANALYSIS ({exchange_count} exchanges): {summary[:500]}]"

    # Build messages with compression: summary of old + last 6 full
    messages = [{"role": "system", "content": system_prompt}]
    conversation = session["conversation"]

    if len(conversation) > 6:
        # Ultra-compress older messages into summary
        old_messages = conversation[:-6]
        recent_messages = conversation[-6:]

        # Two-stage compression: Groq 70B summarizes → shorthand applied
        compressed_summary = await compress_conversation_history(old_messages, "llama-3.3-70b-versatile")
        if compressed_summary:
            messages.append({
                "role": "system",
                "content": f"[PREV: {compressed_summary}]"
            })
        messages.extend(recent_messages)
    else:
        messages.extend(conversation)

    # Use Ollama or Groq based on provider
    provider = session.get("provider", "groq")
    if provider == "ollama":
        response = await ollama_chat(messages, model)
    else:
        response = await groq_chat(messages, model)

    if response:
        session["conversation"].append({"role": "assistant", "content": response})
        # Save session after each exchange (local)
        session_manager.save_session(
            session_id=str(user_id),
            project_name=session.get("project_name", ""),
            project_description=session.get("project_description", ""),
            conversation=session.get("conversation", []),
            metadata={
                "model": session.get("model"),
                "provider": session.get("provider"),
                "visual_context": session.get("visual_context", [])
            }
        )

        # Also sync to cloud (async, don't wait) for cross-device access
        try:
            await session_cloud.save_to_cloud(
                user_id=user_id,
                session_data=session,
                conversation=session.get("conversation", [])
            )
        except Exception as e:
            logger.debug(f"Cloud sync failed (non-critical): {e}")

    # Check if Ralph is ready to cook
    is_ready = await ralph_ready_to_cook(response)

    if is_ready and len(session["conversation"]) >= 4:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍳 Cook Dangerous", callback_data="cook_dangerous"),
                InlineKeyboardButton("🔒 Cook Safe", callback_data="cook_safe")
            ],
            [
                InlineKeyboardButton("💬 Not yet...", callback_data="keep_talking")
            ]
        ])
        await update.message.reply_text(
            response + "\n\n---\n"
            "_How should Claude build this?_\n\n"
            "🍳 *Dangerous*: Claude goes brrr (no permission prompts)\n"
            "🔒 *Safe*: Claude asks for everything (slower but safer)",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=get_keyboard(True)
        )

    # If Ralph analyzed a URL, send his specific comment about it
    if url_analysis_comment:
        await update.message.reply_text(
            f"🔗 *About that link...*\n\n{url_analysis_comment}",
            parse_mode="Markdown"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    text = update.message.text

    # Check if waiting for model search
    if session.get("waiting_for") == "model_search":
        await handle_model_search(update, context)
        return

    # Check if waiting for Groq API key
    if session.get("waiting_for") == "groq_api_key":
        session["waiting_for"] = None
        # Validate the key looks right
        if text.startswith("gsk_") and len(text) > 20:
            session["groq_api_key"] = text
            await update.message.reply_text(
                "✅ *Groq API key saved!*\n\n"
                "*Ralph gives a thumbs up*\n\n"
                "Now tap 🧠 Change Model to pick a Groq model!",
                parse_mode="Markdown",
                reply_markup=get_keyboard(len(session["conversation"]) > 0)
            )
        else:
            await update.message.reply_text(
                "❌ That doesn't look like a Groq API key.\n\n"
                "Keys start with `gsk_`\n"
                "Get one at: https://console.groq.com/keys",
                parse_mode="Markdown"
            )
        return

    # Check if waiting for image context (user uploaded image with no caption)
    if session.get("waiting_for_image_context"):
        image_id = session.pop("waiting_for_image_context")
        awaiting = session.get("awaiting_context_images", {})

        if image_id in awaiting:
            image_data = awaiting[image_id]["data"]
            del awaiting[image_id]

            # User's message is the context for the image
            await update.message.reply_text(
                "👁️ *Analyzing image...*\n\n"
                f"_Ralph is looking at the {text[:30]}... real close..._",
                parse_mode="Markdown"
            )

            # Build project context
            project_context = session.get("project_description", "")
            if session.get("project_name"):
                project_context = f"Project: {session['project_name']}. {project_context}"

            # Run vision analysis with the user's context
            analysis_result = await extract_image_context(
                image_data,
                filename=f"photo_{image_id}.jpg",
                caption=text,  # User's message becomes the caption/focus
                project_context=project_context
            )

            if analysis_result.get("success"):
                # Store analysis
                if "visual_context" not in session:
                    session["visual_context"] = []

                visual_snippet = {
                    "id": image_id,
                    "type": analysis_result.get("type", "general"),
                    "summary": analysis_result.get("summary", ""),
                    "analysis": analysis_result.get("analysis", ""),
                    "user_focus": text,  # What user asked to focus on
                    "tags": analysis_result.get("tags", []),
                    "timestamp": datetime.now().isoformat(),
                }
                session["visual_context"].append(visual_snippet)

                # Add to conversation
                session["conversation"].append({
                    "role": "user",
                    "content": f"[User shared an image, asked to focus on: {text[:100]}]"
                })

                # Ralph comments on what he found
                ralph_comment = await get_ralph_image_comment(analysis_result, session)
                if ralph_comment:
                    await update.message.reply_text(
                        ralph_comment,
                        parse_mode="Markdown",
                        reply_markup=get_keyboard(True)
                    )
            else:
                await update.message.reply_text(
                    "🤔 *Hmm, I couldn't see that too good...*\n\n"
                    "_Try sending the image again?_",
                    parse_mode="Markdown"
                )
            return

    # Check if waiting for PRD block revision (user disliked a task)
    if session.get("waiting_for") == "prd_revision":
        session["waiting_for"] = None
        revision_index = session.get("revising_block")

        if revision_index is not None:
            blocks = session.get("prd_blocks", [])
            if revision_index < len(blocks):
                original_block = blocks[revision_index]

                # Send to Mona to revise based on user feedback
                await update.message.reply_text(
                    "*Ralph runs to Mona's desk*\n\n"
                    "_One sec boss, Mona's fixing it..._",
                    parse_mode="Markdown"
                )

                # Generate revised block
                revised = await revise_prd_block(original_block, text, session.get("model"))

                if revised:
                    # Replace the block
                    blocks[revision_index] = revised
                    blocks[revision_index]["status"] = "pending"  # Ready for re-vote

                    await update.message.reply_text(
                        "*Ralph brings back the paper*\n\n"
                        "Mona fixed it up! Whatcha think now?",
                        parse_mode="Markdown"
                    )

                    # Show the revised block
                    await show_prd_block_new_message(update, context, revision_index)
                else:
                    await update.message.reply_text(
                        "*Ralph scratches head*\n\n"
                        "Mona couldn't figure out what you meant... Try again?",
                        parse_mode="Markdown"
                    )
        return

    # Handle keyboard buttons
    if text == "🍳 Cook Sauce":
        await cmd_cook(update, context)
        return
    elif text == "💾 Save & Quit":
        await cmd_save(update, context)
        return
    elif text == "📖 Find Recipes":
        await cmd_recipes(update, context)
        return
    elif text == "☕ Support Snail":
        await cmd_support(update, context)
        return
    elif text == "🆕 New Project":
        await cmd_new(update, context)
        return
    elif text == "📂 Load Session":
        await cmd_load(update, context)
        return
    elif text == "🧠 Change Model":
        await cmd_models(update, context)
        return
    elif text == "🔍 Analyze Project":
        await start_analysis(update, context)
        return
    elif text == "🛑 Stop Analysis":
        await stop_analysis(update, context)
        return
    elif text == "📥 Install Ralph":
        await cmd_install_ralph(update, context)
        return

    # Natural language triggers for rapid-fire suggestions
    suggestions_triggers = ["suggestions", "give me ideas", "more ideas", "feature ideas", "brainstorm"]
    if text.lower().strip() in suggestions_triggers or text.lower().startswith("suggestions"):
        await cmd_suggestions(update, context)
        return

    # Natural language undo for rapid suggestions
    undo_triggers = ["oops", "go back", "undo", "i didn't mean that", "wait", "back"]
    if text.lower().strip() in undo_triggers:
        # Check if we're in rapid suggestion mode
        if session.get("rapid_suggestions") and session.get("rapid_index", 0) > 0:
            current_index = session.get("rapid_index", 1)
            prev_index = current_index - 1

            # Undo the last action
            last_action = session.get("last_rapid_action", {})
            if last_action.get("type") == "approve":
                approved = session.get("approved_features", [])
                if approved:
                    session["approved_features"] = approved[:-1]
                    await update.message.reply_text("↩️ Undid last approval! Going back...")
            elif last_action.get("type") == "reject":
                rejected = session.get("rejected_features", [])
                if rejected:
                    session["rejected_features"] = rejected[:-1]
                    await update.message.reply_text("↩️ Undid last rejection! Going back...")
            else:
                await update.message.reply_text("↩️ Going back...")

            # Show previous suggestion
            await show_rapid_suggestion(update, context, prev_index)
            return

    # Process as regular conversation text
    await process_user_text(update, context, text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    # Stop analysis if running
    if session.get("analyzing"):
        if session.get("analysis_task"):
            session["analysis_task"].cancel()
        session["analyzing"] = False
        analysis_count = len(session.get("analysis_context", []))
        await update.message.reply_text(
            f"🛑 *Analysis paused* ({analysis_count} exchanges)\n\n"
            f"We've been doing a lot of talking! Let me hear what you have to say...",
            parse_mode="Markdown",
            reply_markup=get_keyboard(True, analyzing=False)
        )

    await update.message.reply_text("🎤 _Listening..._", parse_mode="Markdown")

    # Download voice file
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    # Transcribe
    text = await transcribe_voice(tmp_path)

    # Clean up
    os.unlink(tmp_path)

    if text:
        await update.message.reply_text(f"🎤 I heard: _{text}_", parse_mode="Markdown")

        # Process transcribed text as regular message
        # Can't modify update.message.text directly, so pass text separately
        await process_user_text(update, context, text)
    else:
        await update.message.reply_text(
            "🎤 *Couldn't transcribe that!*\n\n"
            "Voice needs either:\n"
            "• Groq API key (set GROQ_API_KEY)\n"
            "• Local whisper (`pip install openai-whisper`)\n\n"
            "Or just type your message!",
            parse_mode="Markdown"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos/screenshots - QR codes, OCR, etc."""
    user_id = update.effective_user.id
    session = get_session(user_id)

    await update.message.reply_text("📷 _Scanning..._", parse_mode="Markdown")

    # Download photo
    photo = update.message.photo[-1]  # Get largest size
    file = await context.bot.get_file(photo.file_id)

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    # FIRST: Check for QR code (recipe recall)
    recipe_id = scan_qr_from_image(tmp_path)
    if recipe_id:
        os.unlink(tmp_path)
        await update.message.reply_text(
            f"🔍 *Found Recipe QR!*\n\n"
            f"Recipe ID: `{recipe_id}`\n\n"
            f"_Loading your recipe..._",
            parse_mode="Markdown"
        )

        # Try to load recipe - first local, then cloud
        loaded_recipe = recipe_api.load_recipe(recipe_id)

        if not loaded_recipe:
            # Try cloud
            await update.message.reply_text("📡 _Not found locally, checking cloud..._", parse_mode="Markdown")
            loaded_recipe = await recipe_api.fetch_recipe_from_cloud(recipe_id)

        if loaded_recipe:
            # Load the recipe into session
            session["recipe_id"] = loaded_recipe.id
            session["project_name"] = loaded_recipe.name
            session["project_description"] = loaded_recipe.description
            session["phase"] = "chatting"

            # Build PRD summary
            prd = loaded_recipe.prd
            task_count = len(prd.get("tasks", []))

            await update.message.reply_text(
                f"🎉 *Recipe Loaded!*\n\n"
                f"**{loaded_recipe.name}**\n"
                f"_{loaded_recipe.description[:100]}_\n\n"
                f"📋 *{task_count} tasks* in this recipe\n"
                f"🏷️ Tags: {', '.join(loaded_recipe.tags[:5])}\n\n"
                f"Type /cook to start building, or chat to modify!",
                parse_mode="Markdown",
                reply_markup=get_keyboard(True)
            )
        else:
            await update.message.reply_text(
                f"😕 *Recipe Not Found*\n\n"
                f"ID: `{recipe_id}`\n\n"
                f"This recipe might not exist or hasn't been synced to the cloud yet.\n"
                f"Try `/recipes` to search for similar recipes!",
                parse_mode="Markdown",
                reply_markup=get_keyboard(False)
            )
        return

    # Read image data
    with open(tmp_path, 'rb') as f:
        image_data = f.read()

    # Get caption if any
    caption = update.message.caption or ""

    # Check for prior context in recent conversation (e.g., "I'm going to show you the nav bar")
    prior_context = ""
    if not caption and session.get("conversation"):
        # Check last 2 user messages for image context hints
        for msg in reversed(session["conversation"][-4:]):
            if msg.get("role") == "user":
                text = msg.get("content", "").lower()
                if any(phrase in text for phrase in ['going to show', 'going to upload', 'going to send', 'check this', 'look at this', 'here\'s the', 'this is the', 'screenshot of']):
                    prior_context = msg.get("content", "")
                    break

    # If no caption AND no prior context, ask Ralph what to focus on
    if not caption and not prior_context:
        # Store image temporarily waiting for context
        image_id = f"pending_{photo.file_id[:8]}"
        session.setdefault("awaiting_context_images", {})[image_id] = {
            "data": image_data,
            "file_id": photo.file_id,
            "timestamp": datetime.now().isoformat()
        }
        os.unlink(tmp_path)

        await update.message.reply_text(
            "📷 *Ooh, a picture!*\n\n"
            "Hey boss, what do you want me to make notes about here? 🤔\n\n"
            "_Like... should I focus on the colors? The layout? The buttons? "
            "Tell me what you're thinkin' and I'll look real close at that part!_",
            parse_mode="Markdown"
        )
        session["waiting_for_image_context"] = image_id
        return

    # Use caption or prior context
    effective_caption = caption or prior_context

    # No QR code - Run full vision analysis!
    await update.message.reply_text(
        "👁️ *Analyzing image...*\n\n"
        "_Ralph is looking real hard at this..._",
        parse_mode="Markdown"
    )

    # Build project context from current conversation
    project_context = session.get("project_description", "")
    if session.get("project_name"):
        project_context = f"Project: {session['project_name']}. {project_context}"

    # Run vision analysis
    analysis_result = await extract_image_context(
        image_data,
        filename=f"photo_{photo.file_id[:8]}.jpg",
        caption=effective_caption,
        project_context=project_context
    )

    # Store image temporarily for follow-up questions (in-memory only, not persisted)
    if "pending_images" not in session:
        session["pending_images"] = {}

    image_id = f"img_{len(session.get('visual_context', []))}"
    session["pending_images"][image_id] = {
        "data": image_data,
        "analysis": analysis_result
    }

    # Clean up temp file
    os.unlink(tmp_path)

    if analysis_result.get("success"):
        # Initialize visual context storage if needed
        if "visual_context" not in session:
            session["visual_context"] = []

        # Store analysis only - no base64, no file saving (saves tokens!)
        visual_snippet = {
            "id": image_id,
            "type": analysis_result.get("type", "general"),
            "summary": analysis_result.get("summary", ""),
            "analysis": analysis_result.get("analysis", ""),
            "structured": analysis_result.get("structured"),
            "tags": analysis_result.get("tags", []),
            "timestamp": datetime.now().isoformat(),
        }
        session["visual_context"].append(visual_snippet)

        # Add to conversation as a rich context message
        session["conversation"].append({
            "role": "user",
            "content": f"[User shared an image ({analysis_result.get('type', 'image')}): {analysis_result.get('summary', 'Image analyzed')}]"
        })

        # Add key insights to project description
        if analysis_result.get("structured"):
            struct = analysis_result["structured"]
            # Extract key points for project context
            key_points = []
            for key in ["colors", "components", "functionality", "summary", "key_data"]:
                if key in struct and struct[key]:
                    key_points.append(f"{key}: {str(struct[key])[:100]}")
            if key_points:
                session["project_description"] += f" Visual context: {'; '.join(key_points[:3])}"

        # Build user-facing response
        img_type = analysis_result.get("type", "image")
        type_emoji = {"design": "🎨", "document": "📄", "screenshot": "📱", "photo": "📸"}.get(img_type, "🖼️")

        # Show brief summary to user
        summary = analysis_result.get("summary", "")[:300]
        tags = ", ".join(analysis_result.get("tags", [])[:5])

        await update.message.reply_text(
            f"{type_emoji} *Got it, boss!*\n\n"
            f"**Type:** {img_type.title()}\n"
            f"**Tags:** {tags}\n\n"
            f"📝 _{summary}_\n\n"
            f"💡 _I've stored the context for your project. Ask me about specific details or send more images!_\n\n"
            f"Image ID: `{image_id}` (say \"tell me more about {image_id}\" for follow-up)",
            parse_mode="Markdown",
            reply_markup=get_keyboard(True)
        )

        # Have Ralph comment on the image naturally
        if len(session["conversation"]) > 0:
            ralph_comment = await get_ralph_image_comment(analysis_result, session)
            if ralph_comment:
                await update.message.reply_text(
                    ralph_comment,
                    parse_mode="Markdown"
                )
    else:
        # Fallback to OCR if vision fails
        await update.message.reply_text("🔍 _Vision unavailable, trying OCR..._", parse_mode="Markdown")

        # Re-read image for OCR
        with open(tmp_path if os.path.exists(tmp_path) else "", 'rb') as f:
            pass  # Already unlinked, try OCR from memory or skip

        # Simple fallback message
        await update.message.reply_text(
            f"📷 *Couldn't fully analyze this image*\n\n"
            f"Error: {analysis_result.get('error', 'Unknown')}\n\n"
            f"Try sending a clearer image or describe what it shows!",
            parse_mode="Markdown",
            reply_markup=get_keyboard(len(session["conversation"]) > 0)
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle documents (PDFs, text files, etc.)"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    doc = update.message.document
    file_name = doc.file_name or "document"
    mime_type = doc.mime_type or ""

    # Check if it's a TeleRalph PRD file (by magic header or filename pattern)
    is_teleralph_prd = "_prd_" in file_name.lower() or file_name.endswith(".prd")

    await update.message.reply_text(f"📄 _Reading {file_name}..._", parse_mode="Markdown")

    # Download file
    file = await context.bot.get_file(doc.file_id)

    with tempfile.NamedTemporaryFile(suffix=f"_{file_name}", delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        tmp_path = tmp.name

    extracted_text = ""

    try:
        # FIRST: Check if it's a TeleRalph PRD file
        if is_teleralph_prd:
            # Try to read as plain text first to find the magic header
            try:
                with open(tmp_path, 'r', errors='ignore') as f:
                    content = f.read()

                # Check for TeleRalph PRD magic header
                if "=== PRD LEGEND" in content or "=== RALPH BUILD LOOP" in content:
                    # Extract JSON from the file (usually at the end after ===)
                    json_match = re.search(r'===(?:\s*)\n(.*)', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1).strip()
                        try:
                            # Parse the compressed PRD
                            prd_data = json.loads(json_str)

                            # Load into session
                            session["prd_imported"] = True
                            session["imported_prd"] = prd_data
                            session["project_name"] = prd_data.get("pn", session.get("project_name", "My Project"))
                            session["project_description"] = prd_data.get("pd", session.get("project_description", ""))
                            session["tech_stack"] = prd_data.get("ts", {})
                            session["file_structure"] = prd_data.get("fs", [])
                            session["commands"] = prd_data.get("cmd", {})
                            session["starter_prompt"] = prd_data.get("sp", "")

                            # Load existing tasks
                            prds = prd_data.get("p", {})
                            imported_tasks = []
                            for section_key, section_data in prds.items():
                                for task in section_data.get("t", []):
                                    imported_tasks.append({
                                        "id": task.get("i", task.get("id", "")),
                                        "title": task.get("ti", task.get("title", "")),
                                        "description": task.get("d", task.get("description", "")),
                                        "file": task.get("f", task.get("file", "")),
                                        "priority": task.get("pr", task.get("priority", "medium")),
                                        "section": section_data.get("n", section_key)
                                    })

                            session["imported_tasks"] = imported_tasks
                            session["existing_prds"] = prds

                            os.unlink(tmp_path)

                            task_count = len(imported_tasks)
                            project_desc = prd_data.get('pd', '')
                            project_name = prd_data.get('pn', 'this project')

                            # Build the recognition message
                            if project_desc:
                                recognition = f"Oh, I see you brought back in the plan about *{project_desc}*"
                            else:
                                recognition = f"Oh, I see you brought back in the plan for *{project_name}*"

                            await update.message.reply_text(
                                f"📂 *PRD Loaded!*\n\n"
                                f"{recognition}\n\n"
                                f"You've already got *{task_count}* tasks in there, boss!\n\n"
                                f"_Ralph scratches head_\n\n"
                                f"So what would you like to add to it?",
                                parse_mode="Markdown",
                                reply_markup=get_keyboard(True)
                            )
                            return

                        except json.JSONDecodeError:
                            logger.warning("PRD JSON parsing failed, treating as regular document")

            except Exception as e:
                logger.error(f"PRD import error: {e}")

        # Regular document processing (PDFs, text files, etc.)
        # Try PDF first
        if mime_type == "application/pdf" or file_name.lower().endswith(".pdf"):
            # Method 1: pdfplumber (for text-based PDFs)
            try:
                import pdfplumber
                with pdfplumber.open(tmp_path) as pdf:
                    pages_text = []
                    for i, page in enumerate(pdf.pages[:20]):
                        text = page.extract_text()
                        if text and len(text.strip()) > 20:
                            pages_text.append(f"[Page {i+1}]\n{text}")
                    if pages_text:
                        extracted_text = "\n\n".join(pages_text)
            except Exception as e:
                logger.error(f"pdfplumber error: {e}")

            # Method 2: If no text, it's probably scanned - use OCR on PDF pages
            if not extracted_text or len(extracted_text.strip()) < 50:
                try:
                    import pdf2image
                    import pytesseract

                    # Convert PDF pages to images
                    images = pdf2image.convert_from_path(tmp_path, first_page=1, last_page=10)
                    pages_text = []
                    for i, img in enumerate(images):
                        text = pytesseract.image_to_string(img)
                        if text and len(text.strip()) > 10:
                            pages_text.append(f"[Page {i+1}]\n{text}")
                    if pages_text:
                        extracted_text = "\n\n".join(pages_text)
                except ImportError:
                    logger.warning("pdf2image not installed - can't OCR scanned PDFs")
                except Exception as e:
                    logger.error(f"PDF OCR error: {e}")

        # If no text yet, try reading as plain text (works for most files)
        if not extracted_text:
            try:
                with open(tmp_path, 'r', errors='ignore') as f:
                    extracted_text = f.read()[:15000]  # 15k char limit
            except:
                pass

        # If still nothing, try OCR (for scanned docs, images sent as files)
        if not extracted_text or len(extracted_text.strip()) < 10:
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(tmp_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                extracted_text = pytesseract.image_to_string(img)
            except:
                pass

        # If STILL nothing, try reading as binary and decode what we can
        if not extracted_text or len(extracted_text.strip()) < 10:
            try:
                with open(tmp_path, 'rb') as f:
                    raw = f.read(20000)
                    # Try to decode as text, ignore errors
                    extracted_text = raw.decode('utf-8', errors='ignore')
                    # Clean up non-printable chars
                    extracted_text = ''.join(c for c in extracted_text if c.isprintable() or c in '\n\t ')
            except:
                extracted_text = "[Couldn't extract any readable text from this file]"

    except Exception as e:
        logger.error(f"Document processing error: {e}")
        extracted_text = f"[Error reading file: {e}]"
    finally:
        os.unlink(tmp_path)

    if extracted_text and not extracted_text.startswith("["):
        # Add to conversation
        session["conversation"].append({
            "role": "user",
            "content": f"[User uploaded {file_name}:\n{extracted_text[:3000]}...]"
        })
        session["project_description"] += f" {extracted_text[:1000]}"

        # Truncate for display
        display_text = extracted_text[:800] + "..." if len(extracted_text) > 800 else extracted_text

        await update.message.reply_text(
            f"📄 *Got it!* I read `{file_name}`\n\n"
            f"```\n{display_text}\n```\n\n"
            f"_Added to our conversation!_",
            parse_mode="Markdown",
            reply_markup=get_keyboard(True)
        )
    else:
        await update.message.reply_text(
            f"📄 {extracted_text}\n\n"
            f"Try a PDF, text file, or code file!",
            reply_markup=get_keyboard(len(session["conversation"]) > 0)
        )


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search the web for info"""
    user_id = update.effective_user.id
    session = get_session(user_id)

    query = " ".join(context.args) if context.args else ""

    if not query:
        await update.message.reply_text(
            "🔍 *Web Search*\n\n"
            "What do you want me to look up?\n\n"
            "Try: `/search python telegram bot tutorial`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(f"🔍 _Searching for: {query}_", parse_mode="Markdown")

    results = await web_search(query, max_results=5)

    # Add to conversation as context
    session["conversation"].append({
        "role": "system",
        "content": f"[Web search results for '{query}':\n{results}]"
    })

    await update.message.reply_text(
        f"🔍 *Found this:*\n\n{results[:3500]}",
        parse_mode="Markdown",
        reply_markup=get_keyboard(len(session["conversation"]) > 0)
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "cook_dangerous":
        await query.edit_message_text("🍳 *Cooking dangerously..._\n\n_Claude goes brrr!_ 🏎️", parse_mode="Markdown")
        # Store dangerous mode in session
        user_id = update.effective_user.id
        session = get_session(user_id)
        session["dangerous_mode"] = True
        await cmd_cook(update, context)

    elif data == "cook_safe":
        await query.edit_message_text("🔒 *Cooking safe..._\n\n_Claude will ask for everything!_ 🐢", parse_mode="Markdown")
        # Store safe mode in session
        user_id = update.effective_user.id
        session = get_session(user_id)
        session["dangerous_mode"] = False
        await cmd_cook(update, context)

    elif data == "github_yes":
        # User wants GitHub
        user_id = update.effective_user.id
        session = get_session(user_id)
        session["going_to_github"] = True
        session["waiting_for_github"] = False

        await query.edit_message_text(
            "*bows respectfully*\n\n"
            "Excellent choice, Mr. Worms sir! I will prepare the GitHub build for you. *nods*\n\n"
            "Now, what can I build for you today?",
            parse_mode="Markdown"
        )

    elif data == "github_no":
        # User wants local build
        user_id = update.effective_user.id
        session = get_session(user_id)
        session["going_to_github"] = False
        session["waiting_for_github"] = False

        await query.edit_message_text(
            "*smiles warmly*\n\n"
            "Very good, sir. A beautiful local build it is! *at your service*\n\n"
            "Now, what can I create for you, Mr. Worms sir?",
            parse_mode="Markdown"
        )

    elif data == "keep_talking":
        await query.edit_message_text(
            query.message.text + "\n\n_Okay, tell me more!_",
            parse_mode="Markdown"
        )

    elif data == "share_recipe":
        user_id = update.effective_user.id
        session = get_session(user_id)
        # TODO: Submit to recipe book
        await query.edit_message_text(
            "Thanks for sharing! Your recipe helps other builders. 🙏"
        )

    elif data == "action_cook":
        # Trigger the cook command via callback
        await query.edit_message_text(
            "🍳 *Cooking your sauce!*\n\n"
            "_Groq is firing up the kitchen..._",
            parse_mode="Markdown"
        )
        # Call the cook function
        await cmd_cook(update, context)

    elif data == "confirm_new_yes":
        # Reset session and start fresh
        user_id = update.effective_user.id
        reset_session(user_id)
        await query.edit_message_text(
            "🆕 *Fresh start!*\n\n"
            "Everything's cleared out. Tell me about your new project!",
            parse_mode="Markdown"
        )

    elif data == "confirm_new_no":
        await query.edit_message_text(
            "👍 *Keeping your current project.*\n\n"
            "Continue where you left off!",
            parse_mode="Markdown"
        )

    elif data.startswith("load_"):
        await handle_load_callback(update, context)

    elif data.startswith("recipe_"):
        await handle_recipe_callback(update, context)

    elif data.startswith("cloud_"):
        await handle_cloud_session_callback(update, context)

    elif data.startswith("rev_") or data == "rev_done":
        await handle_review_callback(update, context)

    elif data.startswith("fb_"):
        await handle_feedback_callback(update, context)

    elif data.startswith("sug_") or data == "sug_done":
        await handle_suggestion_callback(update, context)

    elif data.startswith("rapid_") or data == "rapid_done":
        await handle_rapid_suggestion_callback(update, context)

    elif data.startswith("prd_") or data == "prd_done":
        await handle_prd_block_callback(update, context)

    elif data.startswith("analysis_"):
        await handle_analysis_callback(update, context)

    elif data.startswith("model_") or data.startswith("provider_") or data.startswith("groq_"):
        if data == "model_back":
            await cmd_models(update, context)
        else:
            await handle_model_callback(update, context)


def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN environment variable!")
        print("Export it or create .env file:")
        print('  export TELEGRAM_BOT_TOKEN="your-token-here"')
        return

    # Check Groq API key
    if not GROQ_API_KEY:
        print("WARNING: No GROQ_API_KEY set! Add it to .env file")
        print("Get a free key at: https://console.groq.com")

    print("Starting Ralph Local (Telegram) - Powered by Groq ⚡")
    print(f"Bot token: {BOT_TOKEN[:10]}...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("load", cmd_load))
    app.add_handler(CommandHandler("cook", cmd_cook))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("recipes", cmd_recipes))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("review", cmd_review))
    app.add_handler(CommandHandler("suggest", cmd_suggest))
    app.add_handler(CommandHandler("suggestions", cmd_suggestions))  # Rapid-fire 30 ideas!
    app.add_handler(CommandHandler("support", cmd_support))
    app.add_handler(CommandHandler("models", cmd_models))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("reactions", cmd_reactions))  # Show emoji legend

    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Reaction handler - users can react to messages with emoji!
    app.add_handler(MessageReactionHandler(handle_reaction))

    # Media handlers (voice, photos, documents)
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Text message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Smithers is ready! At your service, Mr. Worms sir! Send /start to your bot.")
    print("Features: Voice, OCR, Web Search, GIFs, Emoji Reactions")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
