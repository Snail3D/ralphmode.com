#!/usr/bin/env python3
"""
Withers Memory System

Persistent context memory for Mr. Worms (Boss).
Conversation history persists across sessions.
Based on Trust Generator's smithers_memory.py
"""

import os
import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path(__file__).parent / "withers_memories"
MEMORY_DIR.mkdir(exist_ok=True)

# User profiles - can add more users later
USERS = {
    7340030703: {
        "name": "Mr. Worms",
        "nickname": "Boss",
        "style": "direct",  # No fluff, get to the point
        "max_history": 50,  # Remember last 50 exchanges
    },
}


def get_user_profile(user_id: int) -> dict:
    """Get user profile or return default."""
    return USERS.get(user_id, {
        "name": f"User_{user_id}",
        "nickname": "Sir",
        "style": "neutral",
        "max_history": 20,
    })


def get_memory_file(user_id: int) -> Path:
    """Get path to user's memory file."""
    return MEMORY_DIR / f"{user_id}_memory.json"


def load_memory(user_id: int) -> list:
    """Load conversation history for user."""
    memory_file = get_memory_file(user_id)
    if memory_file.exists():
        try:
            with open(memory_file, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def save_memory(user_id: int, memory: list):
    """Save conversation history for user."""
    profile = get_user_profile(user_id)
    max_history = profile.get("max_history", 50)

    # Trim to max history
    if len(memory) > max_history:
        memory = memory[-max_history:]

    memory_file = get_memory_file(user_id)
    with open(memory_file, 'w') as f:
        json.dump(memory, f, indent=2)


def add_exchange(user_id: int, user_message: str, bot_response: str, emotion: str = None):
    """Add a conversation exchange to memory."""
    memory = load_memory(user_id)

    exchange = {
        "timestamp": datetime.now().isoformat(),
        "user": user_message[:500],  # Truncate long messages
        "bot": bot_response[:1000],  # Truncate long responses
    }
    if emotion:
        exchange["emotion"] = emotion

    memory.append(exchange)
    save_memory(user_id, memory)


def get_context_prompt(user_id: int) -> str:
    """Build context prompt from memory for Claude."""
    profile = get_user_profile(user_id)
    memory = load_memory(user_id)

    # Style instruction based on user
    if profile["style"] == "direct":
        style_instruction = f"""
You're talking to {profile['name']} (the Boss). Be direct, efficient.
He knows the codebase. Get to the point. No hand-holding.
"""
    else:
        style_instruction = f"You're talking to {profile['name']}."

    # Build recent conversation context
    context_lines = []
    if memory:
        context_lines.append("\n--- Recent conversation history ---")
        for ex in memory[-10:]:  # Last 10 exchanges for context
            timestamp = ex.get("timestamp", "")[:16].replace("T", " ")
            emotion = f" [{ex['emotion']}]" if ex.get("emotion") else ""
            context_lines.append(f"[{timestamp}]{emotion} {profile['name']}: {ex['user'][:200]}")
            context_lines.append(f"Withers: {ex['bot'][:200]}")
        context_lines.append("--- End history ---\n")

    return style_instruction + "\n".join(context_lines)


def get_memory_summary(user_id: int) -> str:
    """Get a summary of memory for status command."""
    memory = load_memory(user_id)
    profile = get_user_profile(user_id)

    if not memory:
        return "No conversation history yet."

    oldest = memory[0].get("timestamp", "")[:10]
    newest = memory[-1].get("timestamp", "")[:10]

    return f"Memory: {len(memory)} exchanges ({oldest} to {newest})"


def clear_memory(user_id: int):
    """Clear all memory for a user."""
    memory_file = get_memory_file(user_id)
    if memory_file.exists():
        memory_file.unlink()
