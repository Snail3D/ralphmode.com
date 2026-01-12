#!/usr/bin/env python3
"""
YouTube Live Chat Poller - Polls comments and analyzes for PRD suggestions

People comment on YouTube → AI analyzes → Adds to PRD if it's a feature request!
"""

import os
import json
import time
import re
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = Path(__file__).parent
PRD_FILE = PROJECT_DIR / "scripts/ralph/prd.json"
PROCESSED_FILE = PROJECT_DIR / "scripts/ralph/.processed_comments"
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5555")

# YouTube API
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_VIDEO_ID = os.getenv("YOUTUBE_VIDEO_ID", "")  # The live stream video ID

# Groq for analysis
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def get_live_chat_id(video_id: str) -> str:
    """Get the live chat ID for a video."""
    if not YOUTUBE_API_KEY:
        print("[YT] No API key configured")
        return ""

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "liveStreamingDetails",
        "id": video_id,
        "key": YOUTUBE_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        items = data.get("items", [])
        if items:
            return items[0].get("liveStreamingDetails", {}).get("activeLiveChatId", "")
    except Exception as e:
        print(f"[YT] Error getting chat ID: {e}")

    return ""


def get_live_chat_messages(chat_id: str, page_token: str = "") -> tuple[list, str]:
    """Get messages from live chat."""
    if not YOUTUBE_API_KEY or not chat_id:
        return [], ""

    url = "https://www.googleapis.com/youtube/v3/liveChat/messages"
    params = {
        "liveChatId": chat_id,
        "part": "snippet,authorDetails",
        "key": YOUTUBE_API_KEY
    }
    if page_token:
        params["pageToken"] = page_token

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        messages = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            author = item.get("authorDetails", {})

            messages.append({
                "id": item.get("id", ""),
                "text": snippet.get("displayMessage", ""),
                "author": author.get("displayName", "Anonymous"),
                "timestamp": snippet.get("publishedAt", "")
            })

        next_token = data.get("nextPageToken", "")
        return messages, next_token

    except Exception as e:
        print(f"[YT] Error getting messages: {e}")
        return [], ""


def load_processed():
    """Load set of processed comment IDs."""
    if PROCESSED_FILE.exists():
        try:
            return set(json.loads(PROCESSED_FILE.read_text()))
        except:
            pass
    return set()


def save_processed(processed: set):
    """Save processed comment IDs."""
    # Keep only last 1000 to prevent file from growing too large
    processed_list = list(processed)[-1000:]
    PROCESSED_FILE.write_text(json.dumps(processed_list))


def analyze_comment(text: str, author: str) -> tuple[bool, dict]:
    """
    Analyze if a comment is a feature suggestion.
    Returns (is_suggestion, task_data)
    """
    # Quick filters
    text_lower = text.lower()

    # Skip very short or obvious non-suggestions
    if len(text) < 15:
        return False, {}

    # Keywords that indicate a suggestion
    suggestion_keywords = [
        "add", "should", "could you", "would be cool", "feature",
        "suggestion", "idea", "please", "can you", "make it",
        "i want", "we need", "how about", "what if", "build"
    ]

    has_keyword = any(kw in text_lower for kw in suggestion_keywords)

    # Skip obvious non-suggestions
    skip_patterns = [
        r'^(hi|hello|hey|lol|lmao|nice|cool|wow|great|awesome)[\s!]*$',
        r'^[^a-zA-Z]*$',  # No letters
        r'^(first|second|third)[\s!]*$',
    ]

    for pattern in skip_patterns:
        if re.match(pattern, text_lower):
            return False, {}

    # If no keyword and short, skip
    if not has_keyword and len(text) < 30:
        return False, {}

    # Use AI to analyze if we have Groq
    if GROQ_API_KEY:
        return ai_analyze_comment(text, author)

    # Fallback: if has keyword, treat as suggestion
    if has_keyword:
        task_id = f"YT-{int(time.time()) % 10000:04d}"
        return True, {
            "id": task_id,
            "title": text[:60],
            "description": f"YouTube suggestion from {author}: {text}",
            "suggested_by": author,
            "source": "youtube"
        }

    return False, {}


def ai_analyze_comment(text: str, author: str) -> tuple[bool, dict]:
    """Use Groq to analyze if comment is a suggestion."""
    prompt = f"""Analyze this YouTube comment to determine if it's a feature suggestion for a coding/development project.

Comment from "{author}":
"{text}"

Is this a feature suggestion, enhancement request, or idea for the project?

Respond in JSON:
{{
    "is_suggestion": true/false,
    "confidence": 0.0-1.0,
    "title": "Short title if suggestion",
    "description": "What they want built"
}}

Only mark as suggestion if it's clearly asking for something to be built/added/changed."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",  # Fast model for quick analysis
                "messages": [
                    {"role": "system", "content": "You analyze comments. Respond only in JSON."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=10
        )

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())

            if data.get("is_suggestion") and data.get("confidence", 0) > 0.6:
                task_id = f"YT-{int(time.time()) % 10000:04d}"
                return True, {
                    "id": task_id,
                    "title": data.get("title", text[:50]),
                    "description": f"YouTube: {data.get('description', text)}",
                    "suggested_by": author,
                    "source": "youtube"
                }

    except Exception as e:
        print(f"[AI] Error: {e}")

    return False, {}


def add_to_prd(task_data: dict) -> bool:
    """Add task to PRD."""
    try:
        with open(PRD_FILE, 'r') as f:
            prd = json.load(f)

        task = {
            "id": task_data["id"],
            "title": task_data["title"],
            "description": task_data["description"],
            "acceptance_criteria": ["Implement as suggested", "Test thoroughly"],
            "passes": False,
            "suggested_by": task_data.get("suggested_by", "youtube"),
            "source": task_data.get("source", "youtube"),
            "suggested_at": datetime.now().isoformat()
        }

        prd["tasks"].append(task)

        if "priority_order" in prd:
            prd["priority_order"].append(task_data["id"])

        with open(PRD_FILE, 'w') as f:
            json.dump(prd, f, indent=2)

        return True
    except Exception as e:
        print(f"[PRD] Error: {e}")
        return False


def notify_dashboard(author: str, suggestion: str, task_id: str):
    """Send message to dashboard."""
    try:
        # Send multiple messages for theatrical effect
        messages = [
            {"character": "Gomer", "text": "Someone's commenting!", "action": "points at screen"},
            {"character": "Ralph", "text": f"Ooh! {author} wants something!", "action": "squints"},
            {"character": "Stool", "text": f"Adding {task_id} to the list.", "action": "types"},
            {"character": "Ralph", "text": f"Thank you {author}!", "action": "waves"},
        ]

        for msg in messages:
            requests.post(f"{DASHBOARD_URL}/api/message", json=msg, timeout=5)
            time.sleep(1)

    except Exception as e:
        print(f"[DASH] Error: {e}")


def poll_loop():
    """Main polling loop."""
    print("=" * 60)
    print("YouTube Live Chat Poller")
    print("=" * 60)

    if not YOUTUBE_API_KEY:
        print("[WARN] No YOUTUBE_API_KEY - using simulation mode")
        print("Set YOUTUBE_API_KEY and YOUTUBE_VIDEO_ID in .env")
        print("=" * 60)
        return simulation_mode()

    if not YOUTUBE_VIDEO_ID:
        print("[WARN] No YOUTUBE_VIDEO_ID set")
        return

    print(f"Video ID: {YOUTUBE_VIDEO_ID}")

    # Get live chat ID
    chat_id = get_live_chat_id(YOUTUBE_VIDEO_ID)
    if not chat_id:
        print("[ERROR] Could not get live chat ID - is the stream live?")
        return

    print(f"Chat ID: {chat_id}")
    print("Polling for comments...")
    print("=" * 60)

    processed = load_processed()
    page_token = ""

    while True:
        try:
            messages, page_token = get_live_chat_messages(chat_id, page_token)

            for msg in messages:
                if msg["id"] in processed:
                    continue

                processed.add(msg["id"])

                print(f"[CHAT] {msg['author']}: {msg['text'][:50]}...")

                # Analyze the comment
                is_suggestion, task_data = analyze_comment(msg["text"], msg["author"])

                if is_suggestion:
                    print(f"[SUGGESTION] Found from {msg['author']}: {task_data['title']}")

                    # Add to PRD
                    if add_to_prd(task_data):
                        print(f"[PRD] Added {task_data['id']}")
                        notify_dashboard(msg["author"], msg["text"], task_data["id"])

            save_processed(processed)

            # Poll every 5 seconds
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n[EXIT] Stopping poller")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(10)


def simulation_mode():
    """Simulation mode when no YouTube API is available."""
    print("Running in SIMULATION mode")
    print("Comments can be submitted via /suggest page")
    print("=" * 60)

    # Just keep running to show we're alive
    while True:
        try:
            time.sleep(60)
            print(f"[SIM] Waiting for YouTube API config... ({datetime.now().strftime('%H:%M:%S')})")
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    poll_loop()
