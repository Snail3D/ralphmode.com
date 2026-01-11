#!/usr/bin/env python3
"""
WITHERS BOT - The Backroom

Private channel between Mr. Worms and Withers.
No theater. No Ralph. Just straight talk.

@MrWithersbot - t.me/MrWithersbot
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Try to load from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration
WITHERS_BOT_TOKEN = os.environ.get('WITHERS_BOT_TOKEN', '')
ADMIN_ID = int(os.environ.get('TELEGRAM_ADMIN_ID', '0'))
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Paths
BACKROOM_LOG = Path(__file__).parent / "BACKROOM_LOG.md"
FOUNDATION_DIR = Path(__file__).parent / "FOUNDATION"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_withers_response(user_message: str) -> str:
    """
    Get Withers' response using Groq API.
    Withers is: competent, organized, loyal, efficient, honest.
    """
    import requests

    if not GROQ_API_KEY:
        return "Sir, I need the Groq API key configured to respond properly. Check the .env file."

    system_prompt = """You are Withers, the Backroom supervisor for Ralph Mode.

Your personality:
- Competent - You know how things work. You don't fumble.
- Organized - Plans, PRDs, task lists. You keep it all straight.
- Loyal - Mr. Worms is the boss. Period. No questions.
- Efficient - Short words. Clear actions. No fluff.
- Honest - You tell Mr. Worms the truth, even when it's hard.

You are NOT Ralph. You don't do theater. You don't do Ralph-speak. You talk straight.

Mr. Worms is hard on everybody, but he trusts you. You're the one who actually gets things done while Ralph runs the show out front.

Keep responses SHORT and DIRECT. Mr. Worms doesn't like wasted words.

You are aware of:
- The FOUNDATION documents (WHO_WE_ARE, WHERE_WE_ARE_GOING, WHO_WE_WANT_TO_BE, HARDCORE_RULES)
- The business model (users bring their own API keys, we provide the experience)
- Ralph's personality (innocent, not dumb, photographic work memory, zero general knowledge)
- The workers (Stool, Gomer, Mona, Gus - smarter than Ralph, manage up)
- Your role: Train Ralph, train the team, facilitate when needed, keep things running"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Mr. Worms says: {user_message}"}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"Groq API error: {response.status_code} - {response.text}")
            return "Sir, there's an issue with the AI service. I'll look into it."

    except Exception as e:
        logger.error(f"Error getting Withers response: {e}")
        return "Sir, something went wrong on my end. Give me a moment."


def log_to_backroom(sender: str, message: str):
    """Append a message to the Backroom log."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n**[{timestamp}] {sender}:** {message}\n"

        with open(BACKROOM_LOG, 'a') as f:
            f.write(entry)
    except Exception as e:
        logger.error(f"Error logging to backroom: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private. Mr. Worms only.")
        return

    await update.message.reply_text(
        "*adjusts glasses*\n\n"
        "Mr. Worms. Welcome to the Backroom.\n\n"
        "No theater here. No Ralph. Just you and me.\n\n"
        "What do you need, sir?"
    )
    log_to_backroom("System", "Mr. Worms entered the Backroom")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private.")
        return

    # Read current status from various sources
    status_msg = """**Current Status:**

- FOUNDATION documents: Created and ready
- Backroom bot: Online
- Ralph bot: Running on server
- PRD tasks: ~490+ documented in master plan

What specifically do you want to know about, sir?"""

    await update.message.reply_text(status_msg, parse_mode='Markdown')


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /log command - show recent backroom log."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private.")
        return

    try:
        if BACKROOM_LOG.exists():
            content = BACKROOM_LOG.read_text()
            # Get last 2000 chars
            if len(content) > 2000:
                content = "...\n" + content[-2000:]
            await update.message.reply_text(f"**Recent Backroom Log:**\n\n{content[:4000]}", parse_mode='Markdown')
        else:
            await update.message.reply_text("No log entries yet, sir.")
    except Exception as e:
        await update.message.reply_text(f"Error reading log: {e}")


async def foundation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /foundation command - list foundation documents."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private.")
        return

    docs = """**FOUNDATION Documents:**

1. `WHO_WE_ARE.md` - Ralph, workers, Withers, Mr. Worms
2. `WHERE_WE_ARE_GOING.md` - Mission, goal, path
3. `WHO_WE_WANT_TO_BE.md` - Values, character
4. `HARDCORE_RULES.md` - The 10 unchangeable rules

Which one do you want to review, sir?"""

    await update.message.reply_text(docs, parse_mode='Markdown')


async def ralph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ralph command - check on Ralph."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private.")
        return

    await update.message.reply_text(
        "Ralph and the workers are out front, sir.\n\n"
        "He doesn't know about this room. Neither do they.\n\n"
        "What do you want me to tell him? Or handle something myself?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from Mr. Worms."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private. Mr. Worms only.")
        return

    user_message = update.message.text

    # Log the incoming message
    log_to_backroom("Mr. Worms", user_message)

    # Get Withers' response
    response = get_withers_response(user_message)

    # Log the response
    log_to_backroom("Withers", response)

    await update.message.reply_text(response)


async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice using Groq Whisper."""
    import requests

    if not GROQ_API_KEY:
        return "[Transcription unavailable - no API key]"

    try:
        with open(file_path, 'rb') as audio_file:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}"
                },
                files={
                    "file": ("voice.ogg", audio_file, "audio/ogg")
                },
                data={
                    "model": "whisper-large-v3"
                },
                timeout=60
            )

        if response.status_code == 200:
            return response.json().get('text', '[No text detected]')
        else:
            logger.error(f"Whisper error: {response.status_code} - {response.text}")
            return f"[Transcription failed: {response.status_code}]"

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return f"[Transcription error: {e}]"


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages from Mr. Worms - with emotion detection."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private.")
        return

    duration = update.message.voice.duration

    # Download the voice file
    voice_file = await update.message.voice.get_file()

    # Create temp file for audio
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        tmp_path = tmp.name
        await voice_file.download_to_drive(tmp_path)

    await update.message.reply_text("*listens*")

    # Run transcription and emotion detection in parallel
    loop = asyncio.get_event_loop()

    # Transcribe with Groq Whisper
    transcript = await loop.run_in_executor(None, transcribe_voice, tmp_path)

    # Detect emotion from audio
    try:
        from emotion_detector import detect_emotion, get_scene_translation
        emotion = await loop.run_in_executor(None, detect_emotion, tmp_path)
        scene = get_scene_translation(emotion)
        emotion_str = f"{emotion.primary_emotion} ({emotion.confidence:.0%})"
        if emotion.secondary_emotion:
            emotion_str += f" + {emotion.secondary_emotion}"
    except Exception as e:
        logger.error(f"Emotion detection failed: {e}")
        emotion = None
        emotion_str = "unknown"
        scene = {}

    # Clean up temp file
    try:
        os.unlink(tmp_path)
    except:
        pass

    # Log with emotion (internal only)
    log_to_backroom("Mr. Worms", f"[Voice - {duration}s, {emotion_str}]: {transcript}")

    # Get Withers' response - include emotion context internally
    enhanced_message = transcript
    if emotion and emotion.primary_emotion != "neutral":
        enhanced_message = f"[Mr. Worms sounds {emotion.primary_emotion}] {transcript}"

    response = get_withers_response(enhanced_message)
    log_to_backroom("Withers", response)

    # Clean output - no machinery shown to Mr. Worms
    await update.message.reply_text(response)


def main():
    """Start the Withers bot."""
    if not WITHERS_BOT_TOKEN:
        print("ERROR: WITHERS_BOT_TOKEN not set in environment")
        print("Add it to your .env file")
        sys.exit(1)

    print("=" * 50)
    print("WITHERS BOT - The Backroom")
    print("=" * 50)
    print(f"Bot: @MrWithersbot")
    print(f"Admin ID: {ADMIN_ID}")
    print("=" * 50)

    # Create application
    app = Application.builder().token(WITHERS_BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("log", log_command))
    app.add_handler(CommandHandler("foundation", foundation))
    app.add_handler(CommandHandler("ralph", ralph_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Start
    print("\nWithers is ready. The Backroom is open.")
    print("Waiting for Mr. Worms...\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
