"""
Session Cloud - Sync sessions to server for cross-device access

Features:
- Auto-save sessions to cloud server
- Generate shareable links
- AI-generated titles for easy discovery
- List of 50 recent sessions with hyperlinks
"""

import os
import json
import aiohttp
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Cloud server URL (configurable)
CLOUD_SERVER = os.environ.get("RALPH_CLOUD_SERVER", "https://chatformed.com/api/ralph")

# Local cache for offline access
CACHE_DIR = Path.home() / ".ralph" / "cloud_cache"
MAX_SESSIONS = 50


def ensure_cache_dir():
    """Create cache directory if it doesn't exist"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def generate_session_id(user_id: int, timestamp: str = None) -> str:
    """Generate a unique, shareable session ID"""
    if not timestamp:
        timestamp = datetime.now().isoformat()
    unique_str = f"{user_id}_{timestamp}"
    return hashlib.sha256(unique_str.encode()).hexdigest()[:16]


async def generate_title(conversation: List[Dict], model: str = None) -> str:
    """Generate a descriptive title from conversation using AI"""
    if not conversation:
        return "New Session"

    # Get first few exchanges
    preview = conversation[:6]
    text = "\n".join([
        f"{m['role']}: {m['content'][:100]}"
        for m in preview
    ])

    # Try to use Groq for title generation (fast)
    try:
        from ralph_telegram import groq_chat, GROQ_API_KEY

        if GROQ_API_KEY:
            messages = [{
                "role": "system",
                "content": "Generate a short, memorable title (4-6 words max) for this conversation. Just respond with the title, nothing else."
            }, {
                "role": "user",
                "content": f"Conversation:\n{text}"
            }]

            title = await groq_chat(messages, "llama-3.1-8b-instant")
            if title:
                # Clean up the title
                title = title.strip().strip('"').strip("'")[:50]
                return title
    except Exception as e:
        logger.debug(f"Groq title generation failed: {e}")

    # Fallback: extract key words from first user message
    for msg in conversation:
        if msg["role"] == "user" and msg["content"]:
            words = msg["content"][:50].split()[:6]
            return " ".join(words) + "..."

    return "Untitled Session"


async def save_to_cloud(
    user_id: int,
    session_data: Dict,
    conversation: List[Dict]
) -> Optional[str]:
    """
    Save session to cloud server.
    Returns the shareable URL or None if failed.
    """
    ensure_cache_dir()

    # Generate session ID and title
    session_id = session_data.get("session_id") or generate_session_id(user_id)
    title = await generate_title(conversation)

    # Prepare payload
    payload = {
        "session_id": session_id,
        "user_id": str(user_id),
        "title": title,
        "project_name": session_data.get("project_name", ""),
        "project_description": session_data.get("project_description", ""),
        "conversation": conversation,
        "metadata": {
            "model": session_data.get("model"),
            "provider": session_data.get("provider"),
            "visual_context": session_data.get("visual_context", []),
            "created_at": session_data.get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "message_count": len(conversation)
        }
    }

    # Save locally first (backup)
    cache_file = CACHE_DIR / f"{session_id}.json"
    with open(cache_file, 'w') as f:
        json.dump(payload, f, indent=2)

    # Update local index
    await update_local_index(session_id, title, user_id)

    # Try to sync to cloud
    try:
        async with aiohttp.ClientSession() as client:
            async with client.post(
                f"{CLOUD_SERVER}/sessions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    url = data.get("url", f"{CLOUD_SERVER}/s/{session_id}")
                    logger.info(f"Session synced to cloud: {url}")
                    return url
                else:
                    logger.warning(f"Cloud sync failed: {resp.status}")
    except Exception as e:
        logger.debug(f"Cloud sync unavailable: {e}")

    # Return local reference if cloud failed
    return f"local://{session_id}"


async def update_local_index(session_id: str, title: str, user_id: int):
    """Update local session index for quick listing"""
    ensure_cache_dir()
    index_file = CACHE_DIR / "index.json"

    # Load existing index
    if index_file.exists():
        with open(index_file) as f:
            index = json.load(f)
    else:
        index = {"sessions": []}

    # Add/update session entry
    now = datetime.now().isoformat()
    entry = {
        "session_id": session_id,
        "title": title,
        "user_id": str(user_id),
        "updated_at": now
    }

    # Remove existing entry if present
    index["sessions"] = [
        s for s in index["sessions"]
        if s["session_id"] != session_id
    ]

    # Add to front
    index["sessions"].insert(0, entry)

    # Keep only MAX_SESSIONS
    index["sessions"] = index["sessions"][:MAX_SESSIONS]

    # Save
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)


async def list_cloud_sessions(user_id: int = None) -> List[Dict]:
    """
    Get list of recent sessions with shareable links.
    Returns up to 50 sessions.
    """
    ensure_cache_dir()
    sessions = []

    # Try cloud first
    try:
        async with aiohttp.ClientSession() as client:
            params = {"user_id": str(user_id)} if user_id else {}
            async with client.get(
                f"{CLOUD_SERVER}/sessions",
                params=params,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sessions = data.get("sessions", [])[:MAX_SESSIONS]
                    logger.info(f"Got {len(sessions)} sessions from cloud")
    except Exception as e:
        logger.debug(f"Cloud list unavailable: {e}")

    # Merge with local cache
    index_file = CACHE_DIR / "index.json"
    if index_file.exists():
        with open(index_file) as f:
            local_index = json.load(f)

        # Add local sessions not in cloud list
        cloud_ids = {s.get("session_id") for s in sessions}
        for local_session in local_index.get("sessions", []):
            if local_session["session_id"] not in cloud_ids:
                if user_id is None or local_session.get("user_id") == str(user_id):
                    sessions.append(local_session)

    # Sort by updated time and limit
    sessions.sort(
        key=lambda x: x.get("updated_at", ""),
        reverse=True
    )
    return sessions[:MAX_SESSIONS]


async def load_from_cloud(session_id: str) -> Optional[Dict]:
    """Load a session from cloud or local cache"""
    # Try cloud first
    try:
        async with aiohttp.ClientSession() as client:
            async with client.get(
                f"{CLOUD_SERVER}/sessions/{session_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.debug(f"Cloud load unavailable: {e}")

    # Fall back to local cache
    ensure_cache_dir()
    cache_file = CACHE_DIR / f"{session_id}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    return None


def get_shareable_link(session_id: str) -> str:
    """Get shareable link for a session"""
    return f"{CLOUD_SERVER}/s/{session_id}"


def format_session_list(sessions: List[Dict]) -> str:
    """Format sessions as a clickable markdown list"""
    if not sessions:
        return "No saved sessions yet. Start chatting to create one!"

    lines = ["📚 *Your Sessions* (click to load)\n"]

    for i, s in enumerate(sessions[:MAX_SESSIONS], 1):
        title = s.get("title", "Untitled")[:40]
        session_id = s.get("session_id", "")
        updated = s.get("updated_at", "")[:10]
        msg_count = s.get("metadata", {}).get("message_count", 0) or s.get("message_count", 0)

        # Create clickable callback data reference
        # Telegram doesn't support real hyperlinks in messages,
        # so we'll use inline buttons instead
        lines.append(f"`{i}.` *{title}*")
        lines.append(f"    _{updated}_ • {msg_count} msgs • `/load {session_id[:8]}`")
        lines.append("")

    lines.append("---")
    lines.append("_Use `/load <id>` or click a session above_")

    return "\n".join(lines)


def format_session_buttons(sessions: List[Dict], page: int = 0) -> List[List]:
    """Format sessions as inline keyboard buttons (paginated)"""
    from telegram import InlineKeyboardButton

    per_page = 10
    start = page * per_page
    end = start + per_page
    page_sessions = sessions[start:end]

    buttons = []
    for s in page_sessions:
        title = s.get("title", "Untitled")[:30]
        session_id = s.get("session_id", "")[:8]
        buttons.append([
            InlineKeyboardButton(
                f"📄 {title}",
                callback_data=f"cloud_load_{session_id}"
            )
        ])

    # Navigation buttons
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cloud_page_{page-1}"))
    if end < len(sessions):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"cloud_page_{page+1}"))
    if nav:
        buttons.append(nav)

    return buttons
