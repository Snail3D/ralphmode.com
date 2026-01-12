#!/usr/bin/env python3
"""
Audience Interaction - Characters acknowledge chat without getting distracted

- Polls YouTube chat or suggestion submissions periodically
- Characters react to interesting comments naturally
- Big celebration when suggestions are accepted
- Never interrupts the actual building work
"""

import os
import json
import time
import random
import requests
import threading
from pathlib import Path
from datetime import datetime
from collections import deque
from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = Path(__file__).parent
SUGGESTIONS_LOG = PROJECT_DIR / "scripts/ralph/.suggestions_log"
ACKNOWLEDGED_FILE = PROJECT_DIR / "scripts/ralph/.acknowledged_comments"
PRD_FILE = PROJECT_DIR / "scripts/ralph/prd.json"

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5555")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Track what we've acknowledged
acknowledged = set()

# How often to check (seconds)
CHECK_INTERVAL = 15  # Every 15 seconds - responsive to chat!


def load_acknowledged():
    """Load acknowledged comment IDs."""
    global acknowledged
    if ACKNOWLEDGED_FILE.exists():
        try:
            acknowledged = set(json.loads(ACKNOWLEDGED_FILE.read_text()))
        except:
            acknowledged = set()


def save_acknowledged():
    """Save acknowledged comment IDs."""
    # Keep only last 500
    ack_list = list(acknowledged)[-500:]
    ACKNOWLEDGED_FILE.write_text(json.dumps(ack_list))


def send_to_dashboard(character: str, text: str, action: str = ""):
    """Send message to stream dashboard."""
    try:
        requests.post(
            f"{DASHBOARD_URL}/api/message",
            json={"character": character, "text": text, "action": action},
            timeout=5
        )
        return True
    except:
        return False


def get_recent_suggestions() -> list:
    """Get suggestions that haven't been acknowledged yet."""
    suggestions = []

    # Check the suggestions log
    if SUGGESTIONS_LOG.exists():
        try:
            for line in SUGGESTIONS_LOG.read_text().strip().split('\n'):
                if not line:
                    continue
                entry = json.loads(line)
                suggestion_id = f"sug_{entry.get('timestamp', '')}"

                if suggestion_id not in acknowledged and entry.get('approved'):
                    suggestions.append({
                        "id": suggestion_id,
                        "nickname": entry.get('nickname', 'someone'),
                        "text": entry.get('suggestion', ''),
                        "task_id": entry.get('task_id', ''),
                        "type": "suggestion"
                    })
        except Exception as e:
            print(f"[AUDIENCE] Error reading suggestions: {e}")

    return suggestions[-5:]  # Last 5 unacknowledged


def get_new_prd_additions() -> list:
    """Check for newly added suggestions in PRD."""
    additions = []

    try:
        with open(PRD_FILE, 'r') as f:
            prd = json.load(f)

        for task in prd.get("tasks", []):
            # Check if this is a user suggestion
            if task.get("suggested_by") and task.get("source") in ["youtube", "web", None]:
                task_id = task.get("id", "")
                ack_id = f"prd_{task_id}"

                if ack_id not in acknowledged:
                    additions.append({
                        "id": ack_id,
                        "task_id": task_id,
                        "nickname": task.get("suggested_by", "someone"),
                        "title": task.get("title", ""),
                        "type": "prd_addition"
                    })
    except Exception as e:
        print(f"[AUDIENCE] Error reading PRD: {e}")

    return additions[-3:]  # Last 3 unacknowledged


def translate_to_simpsonese(text: str, nickname: str) -> str:
    """
    Translate a comment into Simpsonese - how the characters would describe it.
    Makes the chat feel like part of the show!
    """
    # Simplify and translate common concepts
    text_lower = text.lower()

    # Create a Simpsonese summary
    if any(w in text_lower for w in ['add', 'feature', 'want', 'need', 'should']):
        return f"wants us to build somethin'"
    elif any(w in text_lower for w in ['bug', 'fix', 'broken', 'error']):
        return f"says somethin's broken"
    elif any(w in text_lower for w in ['love', 'great', 'awesome', 'cool', 'nice']):
        return f"thinks we're doin' good!"
    elif any(w in text_lower for w in ['help', 'how', 'what', 'why']):
        return f"is askin' a question"
    elif any(w in text_lower for w in ['hi', 'hello', 'hey', 'sup']):
        return f"is sayin' hello!"
    else:
        # Generic translation - keep it simple
        words = text.split()[:4]
        if words:
            return f"said somethin' about {words[0]}"
        return f"is talkin' to us"


def generate_acknowledgment(item: dict) -> list:
    """Generate character responses for an item - translated into Simpsonese!"""
    nickname = item.get("nickname", "someone")
    text = item.get("text", item.get("title", "something"))[:100]
    item_type = item.get("type", "suggestion")

    # Translate the comment into Simpsonese
    simpsonese = translate_to_simpsonese(text, nickname)

    if item_type == "prd_addition":
        # Big celebration for accepted suggestions!
        task_id = item.get("task_id", "???")
        responses = [
            [
                ("Ralph", f"Mr. Worms! {nickname} tapped us!", "tugs on sleeve"),
                ("Stool", f"They {simpsonese}.", "reads screen"),
                ("Ralph", f"We're gonna build it!", "excited"),
                ("Stool", f"Added as {task_id}.", "nods"),
            ],
            [
                ("Gomer", f"Golly! {nickname} sent us somethin'!", "points at screen"),
                ("Stool", f"Let me see... they {simpsonese}.", "leans in"),
                ("Ralph", f"THANK YOU {nickname.upper()}!", "yells happily"),
            ],
            [
                ("Ralph", f"Someone poked us! It was {nickname}!", "looks around"),
                ("Stool", f"They {simpsonese}. {task_id}.", "types"),
                ("Gomer", f"This is so cool!", "grins"),
            ],
        ]
    else:
        # Regular chat acknowledgment - make it feel natural
        responses = [
            [
                ("Ralph", f"{nickname} tapped Mr. Worms!", "looks up"),
                ("Stool", f"They {simpsonese}.", "glances at screen"),
                ("Ralph", f"Hi {nickname}!", "waves at camera"),
            ],
            [
                ("Gomer", f"Hey! {nickname}'s in the chat!", "excited"),
                ("Ralph", f"What'd they say?", "curious"),
                ("Stool", f"They {simpsonese}.", "shrugs"),
                ("Ralph", f"Hello friend!", "waves"),
            ],
            [
                ("Stool", f"Got a message from {nickname}.", "reads"),
                ("Ralph", f"Ooh! What is it?", "leans over"),
                ("Stool", f"They {simpsonese}.", "nods"),
                ("Ralph", f"Thank you for watchin'!", "beams"),
            ],
            [
                ("Ralph", f"Someone's talkin' to us!", "perks up"),
                ("Gomer", f"It's {nickname}!", "points"),
                ("Stool", f"Says they {simpsonese}.", "reads"),
                ("Ralph", f"We hear you {nickname}!", "cups hands around mouth"),
            ],
        ]

    return random.choice(responses)


def check_and_acknowledge():
    """Check for new items to acknowledge."""
    load_acknowledged()

    # Get new PRD additions first (these are the big ones!)
    prd_additions = get_new_prd_additions()
    for item in prd_additions:
        responses = generate_acknowledgment(item)

        for character, text, action in responses:
            send_to_dashboard(character, text, action)
            time.sleep(2)  # Pause between lines for readability

        acknowledged.add(item["id"])
        print(f"[AUDIENCE] Celebrated PRD addition from {item.get('nickname')}")

        # Only do one big celebration per check
        break

    # Then check regular suggestions
    suggestions = get_recent_suggestions()
    if suggestions and not prd_additions:  # Don't overlap with PRD celebration
        item = random.choice(suggestions)  # Pick one to acknowledge
        responses = generate_acknowledgment(item)

        for character, text, action in responses:
            send_to_dashboard(character, text, action)
            time.sleep(1.5)

        acknowledged.add(item["id"])
        print(f"[AUDIENCE] Acknowledged {item.get('nickname')}")

    save_acknowledged()


def random_audience_shoutout():
    """Occasionally do a random shoutout to the audience."""
    shoutouts = [
        [
            ("Ralph", "Are people watching us?", "looks at camera"),
            ("Stool", "Probably.", "shrugs"),
            ("Ralph", "Hi watchers! I'm building stuff!", "waves"),
        ],
        [
            ("Gomer", "Do you think anyone's out there?", "looks around"),
            ("Stool", "It's a livestream. Someone's always watching.", "types"),
            ("Ralph", "HELLO INTERNET!", "yells at screen"),
        ],
        [
            ("Ralph", "If you're watching, you can suggest things!", "excited"),
            ("Stool", "Scan the QR code.", "points"),
            ("Gomer", "We build your ideas!", "nods"),
        ],
        [
            ("Ralph", "I hope the watchers are having a good day!", "smiles"),
            ("Stool", "Focus, Ralph.", "sighs"),
            ("Ralph", "I AM focusing! On being NICE!", "defensive"),
        ],
    ]

    responses = random.choice(shoutouts)
    for character, text, action in responses:
        send_to_dashboard(character, text, action)
        time.sleep(2)


def audience_loop():
    """Main loop for audience interaction."""
    print("=" * 60)
    print("Audience Interaction System")
    print(f"Check interval: {CHECK_INTERVAL}s")
    print("=" * 60)

    iteration = 0

    while True:
        try:
            iteration += 1

            # Check for new suggestions/additions to acknowledge
            check_and_acknowledge()

            # Every 5th check, do a random audience shoutout
            if iteration % 5 == 0:
                random_audience_shoutout()

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n[EXIT] Stopping audience interaction")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(30)


def run_in_background():
    """Run audience interaction in a background thread."""
    thread = threading.Thread(target=audience_loop, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    audience_loop()
