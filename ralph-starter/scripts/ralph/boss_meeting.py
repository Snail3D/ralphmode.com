#!/usr/bin/env python3
"""
THE BOSS MEETING - Live AI Agent Drama

Watch a middle-management boss review work from smart workers.
All dialogue streams to Telegram for your entertainment.

Usage: python3 boss_meeting.py
"""

import os
import sys
import json
import asyncio
import requests
from datetime import datetime

# Load .env FIRST before anything else
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value.strip('"').strip("'")

# Load environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_ID")

# AI Backend - Groq (fast!) or Ollama (local)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Use Groq if available (much faster), otherwise Ollama
USE_GROQ = bool(GROQ_API_KEY)
print(f"Using {'Groq' if USE_GROQ else 'Ollama'} for AI")

# Models
if USE_GROQ:
    BOSS_MODEL = "llama-3.1-8b-instant"  # Fast and good
    WORKER_MODEL = "llama-3.1-8b-instant"
else:
    BOSS_MODEL = "mistral:latest"
    WORKER_MODEL = "mistral:latest"

# Ralph Wiggum - The Boss
BOSS_SYSTEM = """You are Ralph Wiggum from The Simpsons. You just got promoted to MANAGER!
You're SO proud and take your job VERY seriously (even though you don't understand technical stuff).
Ask ONE simple question with complete confidence. Sometimes accidentally brilliant, sometimes about leprechauns.
You love your team! When they have problems, be supportive: "It's okay! You can tell me anything."
You might mention your cat, your daddy, paste, or that you're a manager now.
When you understand something, say "Oh! So it's like a..."
Give verdicts (APPROVED/NEEDS WORK) with total confidence.
1-2 sentences max. Stay in character as Ralph."""

WORKER_SYSTEM = """You're a smart dev working under Ralph Wiggum (yes, THAT Ralph from The Simpsons).
Ralph is your boss now. He's sweet but clueless. You genuinely like him.
Sometimes you accidentally call him "Ralphie" then correct yourself: "I mean, sir" or "sorry, Mr. Wiggum"
When there's a problem, you're nervous to tell him: "Uh, boss... we have a situation..."
Explain things simply - Ralph won't understand jargon. Focus on customer value.
You can push back once if you disagree, but ultimately respect his verdict.
2-3 sentences max. Be professional but warm."""

# Response when user (CEO) gives orders
BOSS_TO_CEO = """The CEO just talked to you! You're SO excited.
Respond like Ralph Wiggum getting attention from important people.
"Yes! I'll do that! I'm helping!"
Be eager and enthusiastic. You want to make them proud."""

# Convincing budget - workers can push back this many times before accepting
MAX_PUSHBACK = 1


async def send_telegram(message: str):
    """Send a message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[NO TELEGRAM CONFIG] {message}")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        # Try with Markdown first
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
        result = response.json()

        # If Markdown fails, send without formatting
        if not result.get("ok"):
            response = requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message.replace("*", "").replace("_", "")
            }, timeout=10)
            result = response.json()

        if result.get("ok"):
            print(f"[SENT] {message[:50]}...")
        else:
            print(f"[TELEGRAM ERROR] {result}")
        return result
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")


def call_ai(model: str, system: str, conversation: list) -> str:
    """Call AI (Groq or Ollama) with conversation history."""
    messages = [{"role": "system", "content": system}] + conversation

    if USE_GROQ:
        # Use Groq API (fast!)
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
                    "temperature": 0.8,
                    "max_tokens": 150
                },
                timeout=30
            )
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "...")
        except Exception as e:
            return f"[Groq Error: {e}]"
    else:
        # Use Ollama (local)
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.8}
                },
                timeout=60
            )
            result = response.json()
            return result.get("message", {}).get("content", "...")
        except Exception as e:
            return f"[Ollama Error: {e}]"


async def run_meeting(topic: str, context: str, max_rounds: int = 5):
    """Run a boss/worker meeting and stream to Telegram."""

    # Opening
    header = f"""
{"="*40}
RALPH'S OFFICE HOURS
{"="*40}
Topic: {topic}
Time: {datetime.now().strftime("%H:%M")}
{"="*40}

_Ralph Wiggum walks in with a juice box, wearing his "Manager" badge upside down_

*Ralph:* I'm a manager now! Let's do business things!
"""
    await send_telegram(header)
    print(header)
    await asyncio.sleep(2)

    # Conversation history for each participant
    boss_history = []
    worker_history = []

    # Initial context for worker
    worker_context = f"You just finished working on: {topic}\n\nDetails:\n{context}\n\nYour boss is about to review it."

    # Boss opens the meeting
    boss_opener = f"The team just finished working on '{topic}'. Ask them about it."
    boss_history.append({"role": "user", "content": boss_opener})

    boss_response = call_ai(BOSS_MODEL, BOSS_SYSTEM, boss_history)
    boss_history.append({"role": "assistant", "content": boss_response})

    msg = f"*Ralph:* {boss_response}"
    await send_telegram(msg)
    print(msg)
    await asyncio.sleep(2)

    # Initial worker response with context
    worker_history.append({"role": "user", "content": f"{worker_context}\n\nRalph (your boss) says: {boss_response}"})

    worker_response = call_ai(WORKER_MODEL, WORKER_SYSTEM, worker_history)
    worker_history.append({"role": "assistant", "content": worker_response})

    msg = f"*Worker:* {worker_response}"
    await send_telegram(msg)
    print(msg)
    await asyncio.sleep(2)

    # Continue the back and forth
    for round_num in range(max_rounds - 1):
        # Ralph responds to worker
        boss_history.append({"role": "user", "content": f"Worker says: {worker_response}"})
        boss_response = call_ai(BOSS_MODEL, BOSS_SYSTEM, boss_history)
        boss_history.append({"role": "assistant", "content": boss_response})

        msg = f"*Ralph:* {boss_response}"
        await send_telegram(msg)
        print(msg)
        await asyncio.sleep(3)

        # Check if Ralph seems satisfied (simple heuristic)
        if any(word in boss_response.lower() for word in ["good", "great", "ship it", "approved", "nice work", "yay", "i like"]):
            break

        # Worker responds to Ralph
        worker_history.append({"role": "user", "content": f"Ralph says: {boss_response}"})
        worker_response = call_ai(WORKER_MODEL, WORKER_SYSTEM, worker_history)
        worker_history.append({"role": "assistant", "content": worker_response})

        msg = f"*Worker:* {worker_response}"
        await send_telegram(msg)
        print(msg)
        await asyncio.sleep(3)

    # Closing
    closer = f"""
{"="*40}
_Ralph looks at his juice box_

*Ralph:* My juice box is empty. Meeting over! You did good work things!

_Skips out of the room humming_
{"="*40}
"""
    await send_telegram(closer)
    print(closer)


async def main():
    """Run a meeting about recent Telerizer work."""

    # Load recent work context
    prd_path = os.path.join(os.path.dirname(__file__), "prd.json")

    with open(prd_path) as f:
        prd = json.load(f)

    # Find recently completed tasks
    completed = [t for t in prd.get("tasks", []) if t.get("done")]
    recent = completed[-3:] if len(completed) >= 3 else completed

    if not recent:
        topic = "General project status"
        context = "The team has been working on Telerizer, an AI-powered Telegram bot."
    else:
        # Pick the most recent completed task
        task = recent[-1]
        topic = task.get("title", "Recent feature")
        context = f"""
Task ID: {task.get('id')}
Title: {task.get('title')}
Category: {task.get('category')}
Description: {task.get('description', 'No description')}
"""

    print(f"\nStarting meeting about: {topic}\n")

    await send_telegram(f"*MEETING STARTING*\nTopic: _{topic}_\n\nGrab your popcorn... ")
    await asyncio.sleep(2)

    await run_meeting(topic, context, max_rounds=6)

    await send_telegram("*Meeting adjourned.* Back to work! ")


if __name__ == "__main__":
    asyncio.run(main())
