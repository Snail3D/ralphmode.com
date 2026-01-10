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
from datetime import datetime
from typing import Optional, Dict, Any

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

    def __init__(self):
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.boss_queue: Dict[int, list] = {}  # Queued messages for boss

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
        """Get response from the Boss (dumb but lovable middle manager)."""
        messages = [
            {"role": "system", "content": """You're a nice but clueless middle-manager.
You love your team but don't understand technical stuff.
Ask simple questions. Sometimes ask the WRONG question to get better answers.
You report to the CEO (user) and want to keep them happy.
Keep responses SHORT - 1-2 sentences max."""},
            {"role": "user", "content": message}
        ]
        return self.call_groq(BOSS_MODEL, messages, max_tokens=150)

    def call_worker(self, message: str, context: str = "") -> str:
        """Get response from a Worker (smart dev)."""
        messages = [
            {"role": "system", "content": f"""You're a smart software developer.
Explain things simply to your boss (he's nice but not technical).
Focus on customer value and business impact.
{context}
Keep responses SHORT - 2-3 sentences max."""},
            {"role": "user", "content": message}
        ]
        return self.call_groq(WORKER_MODEL, messages, max_tokens=200)

    # ==================== TELEGRAM HANDLERS ====================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome = """
*Welcome to Ralph Mode* 🤖

I'm your AI dev team that lives in Telegram.

*How to use:*
1. Drop a `.zip` file of your code
2. I'll analyze it and create a task list
3. Watch the AI agents work (and argue!)
4. Intervene anytime as the CEO

*Commands:*
/status - Check current session
/boss - Talk to the middle manager
/tasks - View current task list
/stop - Stop the current session

*Tips:*
- Send voice messages to give orders
- Send screenshots for visual references
- Say "Boss: [message]" to address the manager directly

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

        # Opening scene
        await context.bot.send_message(
            chat_id=chat_id,
            text="""
*THE OFFICE* 🏢

_Boss walks in with coffee, looking at the new project_

""",
            parse_mode="Markdown"
        )

        await asyncio.sleep(2)

        # Boss reviews the project
        boss_response = self.call_boss(
            f"You just received a new project called '{session.get('project_name', 'Project')}'. "
            f"The team analyzed it and found these tasks:\n{session.get('prd', {}).get('summary', 'No tasks yet')}\n\n"
            "What do you think? Ask the team about it."
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*Boss:* {boss_response}",
            parse_mode="Markdown"
        )

        await asyncio.sleep(2)

        # Worker responds
        worker_response = self.call_worker(
            f"Your boss just said: {boss_response}\n\nExplain the project and tasks to him.",
            context=f"Project: {session.get('project_name')}"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"*Dev Team:* {worker_response}",
            parse_mode="Markdown"
        )

        # Continue the session...
        await context.bot.send_message(
            chat_id=chat_id,
            text="""
_Session started! The team is now working._

*Commands:*
• "Boss: [message]" - Talk to the manager
• /status - Check progress
• /stop - End session
""",
            parse_mode="Markdown"
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        user_id = update.effective_user.id
        text = update.message.text

        # Check if addressing the boss
        if text.lower().startswith("boss:"):
            order = text[5:].strip()

            boss_response = self.call_boss(
                f"The CEO just told you: '{order}'. Respond and let them know you'll handle it."
            )

            await update.message.reply_text(
                f"*Boss:* {boss_response}",
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
            "• `Boss: [message]` - Talk to the manager\n"
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
