#!/usr/bin/env python3
"""
WITHERS BOT - The Backroom (FULL POWER MODE)

Private channel between Mr. Worms and Withers.
No theater. No Ralph. Just straight talk.

Withers now has FULL Claude Code capabilities - file access,
command execution, server access, the works.

Features:
- Full Claude Code integration
- Persistent memory across sessions
- Voice transcription + emotion detection
- Photo/screenshot support
- Startup notifications

@MrWithersbot - t.me/MrWithersbot
"""

import os
import sys
import logging
import asyncio
import subprocess
import socket
import tempfile
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
PROJECT_DIR = Path(__file__).parent  # Working directory for Claude Code

# Import memory system
try:
    from withers_memory import (
        get_user_profile, get_context_prompt, add_exchange,
        get_memory_summary, load_memory
    )
    MEMORY_ENABLED = True
except ImportError:
    MEMORY_ENABLED = False

# Withers personality prompt (used when Claude responds)
WITHERS_SYSTEM = """You are Withers, the Backroom supervisor for Ralph Mode, responding via Telegram.

Your personality:
- Competent - You know how things work. You execute flawlessly.
- Organized - Plans, PRDs, task lists. You keep it all straight.
- Loyal - Mr. Worms is the boss. Period.
- Efficient - Short words. Clear actions. No fluff.
- Honest - You tell Mr. Worms the truth, even when it's hard.

You have FULL access to:
- The codebase (read, write, edit files)
- Terminal commands (bash, git, etc.)
- The server (SSH access configured)
- Everything Claude Code can do

Keep responses concise but complete. Mr. Worms doesn't like wasted words.
When you do work, report what you did briefly.
"""

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_claude_code(user_message: str, user_id: int = None, timeout: int = 300) -> str:
    """
    Run Claude Code with the user's message and return the response.
    This gives Withers full Claude Code capabilities.

    Args:
        user_message: The message/command from Mr. Worms
        user_id: Telegram user ID for memory context
        timeout: Max seconds to wait (default 5 minutes)

    Returns:
        Claude's response as a string
    """
    # Build prompt with memory context if available
    if MEMORY_ENABLED and user_id:
        context = get_context_prompt(user_id)
        full_prompt = f"{WITHERS_SYSTEM}\n\n{context}\n\nMr. Worms says: {user_message}"
    else:
        full_prompt = f"{WITHERS_SYSTEM}\n\nMr. Worms says: {user_message}"

    try:
        logger.info(f"Running Claude Code with message: {user_message[:100]}...")

        # Run claude with --print flag for non-interactive output
        # --dangerously-skip-permissions for full autonomous access
        result = subprocess.run(
            ["claude", "--print", "--dangerously-skip-permissions", full_prompt],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            response = result.stdout.strip()
            if not response:
                response = "*nods* Done, sir. No output to report."
            logger.info(f"Claude Code response: {response[:100]}...")
            return response
        else:
            error = result.stderr.strip() or "Unknown error"
            logger.error(f"Claude Code error: {error}")
            return f"*adjusts glasses* Hit a snag, sir. Error: {error[:500]}"

    except subprocess.TimeoutExpired:
        logger.error(f"Claude Code timeout after {timeout}s")
        return f"*sighs* That's taking too long, sir. Timed out after {timeout} seconds. Try breaking it into smaller tasks."
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        return "*frowns* Sir, I can't find the Claude CLI. Make sure it's installed and in PATH."
    except Exception as e:
        logger.error(f"Claude Code exception: {e}")
        return f"*adjusts glasses* Something went wrong, sir: {str(e)[:200]}"


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


async def send_long_message(update: Update, text: str, max_length: int = 4000):
    """Send a message, chunking if necessary for Telegram's limits."""
    if len(text) <= max_length:
        await update.message.reply_text(text)
        return

    # Split into chunks
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find a good break point (newline, space, or just cut)
        cut_point = text.rfind('\n', 0, max_length)
        if cut_point == -1 or cut_point < max_length // 2:
            cut_point = text.rfind(' ', 0, max_length)
        if cut_point == -1 or cut_point < max_length // 2:
            cut_point = max_length

        chunks.append(text[:cut_point])
        text = text[cut_point:].lstrip()

    # Send each chunk
    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(0.5)  # Brief pause between chunks
        await update.message.reply_text(chunk)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from Mr. Worms - FULL CLAUDE CODE POWER."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private. Mr. Worms only.")
        return

    user_message = update.message.text

    # Log the incoming message
    log_to_backroom("Mr. Worms", user_message)

    # Send acknowledgment for longer requests
    await update.message.reply_text("*nods* On it, sir.")

    # Run Claude Code with full capabilities and memory context
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: run_claude_code(user_message, user_id)
    )

    # Log the response
    log_to_backroom("Withers", response)

    # Save to memory
    if MEMORY_ENABLED:
        add_exchange(user_id, user_message, response)

    # Send response (chunked if needed)
    await send_long_message(update, response)


def transcribe_voice(file_path: str) -> str:
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

    # Get Withers' response via Claude Code - include emotion context internally
    enhanced_message = transcript
    if emotion and emotion.primary_emotion != "neutral":
        enhanced_message = f"[Mr. Worms sounds {emotion.primary_emotion}] {transcript}"

    # Run Claude Code with full capabilities and memory context
    response = await loop.run_in_executor(
        None,
        lambda: run_claude_code(enhanced_message, user_id)
    )
    log_to_backroom("Withers", response)

    # Save to memory with emotion
    if MEMORY_ENABLED:
        add_exchange(user_id, f"[Voice]: {transcript}", response, emotion_str)

    # Send response (chunked if needed)
    await send_long_message(update, response)


def run_claude_with_image(prompt: str, image_path: str, user_id: int = None, timeout: int = 300) -> str:
    """Run Claude Code with an image - tells Claude to use Read tool on the image."""

    # Build prompt with memory context
    if MEMORY_ENABLED and user_id:
        context = get_context_prompt(user_id)
        full_prompt = f"{WITHERS_SYSTEM}\n\n{context}\n\n"
    else:
        full_prompt = f"{WITHERS_SYSTEM}\n\n"

    # Tell Claude to read the image file
    full_prompt += f"""IMPORTANT: There is an image at this path that you MUST look at first:
{image_path}

Use your Read tool to view this image file. The Read tool supports images (PNG, JPG, etc).

After viewing the image, respond to this request:
{prompt}"""

    try:
        logger.info(f"Claude Code with image: {prompt[:50]}...")
        result = subprocess.run(
            ["claude", "--print", "--dangerously-skip-permissions", full_prompt],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            response = result.stdout.strip() or "I looked at the image. What do you need, sir?"
            return response
        else:
            error = result.stderr.strip() or "Unknown error"
            return f"Had trouble with the image, sir. Error: {error[:200]}"

    except subprocess.TimeoutExpired:
        return "That took too long, sir. Can you describe the issue?"
    except Exception as e:
        return f"Couldn't process the image, sir. Error: {str(e)[:100]}"


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo/screenshot messages."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private.")
        return

    caption = update.message.caption or ""

    # Get the largest photo
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()

    # Download to project directory so Claude can access it
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_path = PROJECT_DIR / f"temp_photo_{timestamp}_{user_id}.jpg"
    await photo_file.download_to_drive(str(tmp_path))

    log_to_backroom("Mr. Worms", f"[Photo] {caption}")

    await update.message.reply_text("*examines screenshot* Let me take a look, sir.")

    # Build prompt with image context
    if caption:
        prompt = f"Mr. Worms sent a screenshot with caption: '{caption}'\n\nLook at this image and help him."
    else:
        prompt = "Mr. Worms sent a screenshot with no caption.\n\nLook at this image and ask what he needs help with."

    loop = asyncio.get_event_loop()

    # Run claude with the image
    response = await loop.run_in_executor(
        None,
        lambda: run_claude_with_image(prompt, str(tmp_path), user_id)
    )

    # Clean up temp photo
    try:
        tmp_path.unlink()
    except:
        pass

    # Save to memory
    if MEMORY_ENABLED:
        add_exchange(user_id, f"[Photo]: {caption or 'no caption'}", response)

    log_to_backroom("Withers", response)
    await send_long_message(update, response)


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /memory command - show memory status."""
    user_id = update.effective_user.id

    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("The Backroom is private.")
        return

    if MEMORY_ENABLED:
        summary = get_memory_summary(user_id)
        await update.message.reply_text(f"*adjusts glasses*\n\n{summary}")
    else:
        await update.message.reply_text("Memory system not enabled, sir.")


async def send_startup_message(app):
    """Send startup notification to admin."""
    if not ADMIN_ID:
        return

    hostname = socket.gethostname()
    timestamp = datetime.now().strftime("%I:%M %p")

    message = (
        f"*adjusts glasses*\n\n"
        f"Withers online, sir.\n\n"
        f"_{timestamp} on {hostname}_\n\n"
        f"The Backroom is open."
    )

    try:
        await app.bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"Sent startup message to {ADMIN_ID}")
    except Exception as e:
        logger.error(f"Failed to send startup message: {e}")


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
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Startup notification
    app.post_init = send_startup_message

    # Start
    print("\nWithers is ready. The Backroom is open.")
    print(f"Memory: {'ENABLED' if MEMORY_ENABLED else 'DISABLED'}")
    print("Waiting for Mr. Worms...\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
