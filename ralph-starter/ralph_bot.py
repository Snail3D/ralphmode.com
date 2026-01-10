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

    # Ralph-themed GIF search terms for different moods
    RALPH_GIFS = {
        "happy": ["ralph wiggum happy", "simpsons celebrate", "ralph wiggum yay", "excited cartoon"],
        "confused": ["ralph wiggum confused", "simpsons confused", "thinking cartoon"],
        "approved": ["thumbs up cartoon", "simpsons approved", "good job cartoon", "ralph wiggum"],
        "working": ["typing fast", "coding", "simpsons working", "busy cartoon"],
        "problem": ["this is fine", "simpsons fire", "panic cartoon", "oh no cartoon"],
        "thinking": ["ralph wiggum thinking", "simpsons thinking", "hmm cartoon"],
    }

    def __init__(self):
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.boss_queue: Dict[int, list] = {}  # Queued messages for boss
        self.gif_chance = 0.3  # 30% chance to send a GIF after messages

    # ==================== GIF SUPPORT ====================

    def get_gif(self, mood: str = "happy") -> Optional[str]:
        """Get a random GIF URL from Tenor based on mood."""
        try:
            search_terms = self.RALPH_GIFS.get(mood, self.RALPH_GIFS["happy"])
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

    def detect_mood(self, text: str) -> str:
        """Detect the mood from text to pick appropriate GIF."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["approved", "great", "good", "yes", "ship it", "nice", "yay"]):
            return "approved"
        elif any(w in text_lower for w in ["problem", "issue", "error", "bug", "broken", "situation"]):
            return "problem"
        elif any(w in text_lower for w in ["confused", "what", "huh", "don't understand", "?"]):
            return "confused"
        elif any(w in text_lower for w in ["working", "implementing", "building", "coding"]):
            return "working"
        elif any(w in text_lower for w in ["think", "hmm", "maybe", "consider"]):
            return "thinking"
        return "happy"

    async def send_gif(self, context, chat_id: int, mood: str = "happy"):
        """Send a mood-appropriate GIF to the chat."""
        gif_url = self.get_gif(mood)
        if gif_url:
            try:
                await context.bot.send_animation(chat_id=chat_id, animation=gif_url)
            except Exception as e:
                logger.error(f"Failed to send GIF: {e}")

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

    def call_boss(self, message: str) -> str:
        """Get response from Ralph Wiggum, the boss."""
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
        return self.call_groq(BOSS_MODEL, messages, max_tokens=150)

    def call_worker(self, message: str, context: str = "") -> str:
        """Get response from a Worker (smart dev)."""
        messages = [
            {"role": "system", "content": f"""You're a smart software developer working under Ralph Wiggum (yes, THAT Ralph from The Simpsons).
Ralph is your boss now. He's sweet but clueless. You genuinely like him.
Sometimes you accidentally call him "Ralphie" then quickly correct yourself: "I mean, sir" or "sorry, Mr. Wiggum"
Explain technical things simply - Ralph won't understand jargon.
Focus on customer value. Be patient with his weird questions.
You can gently push back once if you disagree, but ultimately respect his verdict.
{context}
2-3 sentences max. Be professional but warm."""},
            {"role": "user", "content": message}
        ]
        return self.call_groq(WORKER_MODEL, messages, max_tokens=200)

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

    async def _generate_prd(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PRD from codebase analysis."""
        analysis = session.get("analysis", {})

        prompt = f"""Analyze this codebase and suggest 5-10 improvements or features to add.

Codebase info:
{analysis.get('summary', '')}

Languages: {', '.join(analysis.get('languages', []))}

For each task, provide:
1. A short title
2. Why it adds value
3. Complexity (Low/Medium/High)

Focus on:
- Bug fixes
- Performance improvements
- UX improvements
- Missing features
- Code quality

Format as a numbered list."""

        response = self.call_groq(ANALYZER_MODEL, [
            {"role": "user", "content": prompt}
        ], max_tokens=800)

        return {
            "summary": response,
            "generated": datetime.now().isoformat()
        }

    async def _start_ralph_session(self, context, chat_id: int, user_id: int):
        """Start the Ralph work session with Boss/Worker drama."""
        session = self.active_sessions.get(user_id)
        if not session:
            return

        # Opening scene with GIF
        await context.bot.send_message(
            chat_id=chat_id,
            text="""
*THE OFFICE* 🏢

_Ralph Wiggum walks in with a juice box, wearing his new "Manager" badge upside down_

*Ralph:* I'm the boss now! My cat's breath smells like cat food.

""",
            parse_mode="Markdown"
        )

        # Opening GIF - Ralph being Ralph
        if self.should_send_gif():
            await self.send_gif(context, chat_id, "happy")

        await asyncio.sleep(2)

        # Boss reviews the project
        boss_response = self.call_boss(
            f"You just received a new project called '{session.get('project_name', 'Project')}'. "
            f"The team analyzed it and found these tasks:\n{session.get('prd', {}).get('summary', 'No tasks yet')}\n\n"
            "What do you think? Ask the team about it."
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*Ralph:* {boss_response}",
            parse_mode="Markdown"
        )

        # Maybe a confused GIF if Ralph asks a weird question
        mood = self.detect_mood(boss_response)
        if self.should_send_gif():
            await self.send_gif(context, chat_id, mood)

        await asyncio.sleep(2)

        # Worker responds
        worker_response = self.call_worker(
            f"Ralph (your boss) just said: {boss_response}\n\nExplain the project and tasks to him.",
            context=f"Project: {session.get('project_name')}"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*Worker:* {worker_response}",
            parse_mode="Markdown"
        )

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

            await update.message.reply_text(
                f"*Ralph:* {ralph_response}",
                parse_mode="Markdown"
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
