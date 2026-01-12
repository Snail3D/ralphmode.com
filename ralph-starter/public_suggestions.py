#!/usr/bin/env python3
"""
Public Suggestions System - Crowd-sourced PRD contributions!

People scan QR code → Submit suggestion → AI screens it → Added to PRD → Telegram announces

Rate limited: 1 suggestion per hour per IP
"""

import os
import json
import time
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Config
PROJECT_DIR = Path(__file__).parent
PRD_FILE = PROJECT_DIR / "scripts/ralph/prd.json"
RATE_LIMIT_FILE = PROJECT_DIR / "scripts/ralph/.suggestion_ratelimit"
SUGGESTIONS_LOG = PROJECT_DIR / "scripts/ralph/suggestions.log"

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_ADMIN_ID", ""))

# GLM/Groq for screening
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Rate limit: 1 hour in seconds
RATE_LIMIT_SECONDS = 3600


def get_ip_hash(ip: str) -> str:
    """Hash IP for privacy."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def check_rate_limit(ip: str) -> tuple[bool, int]:
    """Check if IP is rate limited. Returns (allowed, seconds_remaining)."""
    ip_hash = get_ip_hash(ip)

    # Load rate limit data
    rate_data = {}
    if RATE_LIMIT_FILE.exists():
        try:
            rate_data = json.loads(RATE_LIMIT_FILE.read_text())
        except:
            rate_data = {}

    now = time.time()
    last_submit = rate_data.get(ip_hash, 0)

    if now - last_submit < RATE_LIMIT_SECONDS:
        remaining = int(RATE_LIMIT_SECONDS - (now - last_submit))
        return False, remaining

    return True, 0


def record_submission(ip: str):
    """Record submission time for rate limiting."""
    ip_hash = get_ip_hash(ip)

    rate_data = {}
    if RATE_LIMIT_FILE.exists():
        try:
            rate_data = json.loads(RATE_LIMIT_FILE.read_text())
        except:
            rate_data = {}

    rate_data[ip_hash] = time.time()

    # Clean old entries (older than 2 hours)
    cutoff = time.time() - (RATE_LIMIT_SECONDS * 2)
    rate_data = {k: v for k, v in rate_data.items() if v > cutoff}

    RATE_LIMIT_FILE.write_text(json.dumps(rate_data))


def send_telegram(message: str) -> bool:
    """Send message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.json().get("ok", False)
    except Exception as e:
        print(f"[TELEGRAM] Error: {e}")
        return False


def screen_suggestion(suggestion: str, nickname: str) -> tuple[bool, str, dict]:
    """
    Use AI to screen the suggestion.
    Returns: (approved, reason, task_data)
    """
    if not GROQ_API_KEY:
        # No API key - do basic screening
        if len(suggestion) < 10:
            return False, "Suggestion too short", {}
        if len(suggestion) > 1000:
            return False, "Suggestion too long", {}
        # Auto-approve for now if no AI available
        return True, "Basic screening passed", {
            "title": suggestion[:50],
            "description": suggestion
        }

    # AI screening prompt
    screen_prompt = f"""You are screening a public suggestion for the Ralph Mode project.

Ralph Mode is a Telegram bot that helps people build software using AI. It has characters (Ralph, Stool, Gomer) that make development fun and theatrical.

SUGGESTION FROM "{nickname}":
{suggestion}

Evaluate this suggestion. It should be:
1. Relevant to Ralph Mode (AI coding assistant, Telegram bot, theatrical dev experience)
2. Not harmful, offensive, or spam
3. Technically feasible
4. Won't break the user experience for others
5. Adds value to the project

Respond in JSON format:
{{
    "approved": true/false,
    "reason": "Brief explanation",
    "task_id": "SUG-XXX" (if approved, use format SUG-001, SUG-002, etc.),
    "title": "Short task title" (if approved),
    "description": "Clear description of what to build" (if approved),
    "category": "feature/enhancement/fix/ui" (if approved)
}}

Be generous but filter out spam, off-topic, or harmful suggestions."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that screens suggestions. Respond only in valid JSON."},
                    {"role": "user", "content": screen_prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.3
            },
            timeout=30
        )

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            approved = data.get("approved", False)
            reason = data.get("reason", "Unknown")

            if approved:
                task_data = {
                    "id": data.get("task_id", f"SUG-{int(time.time()) % 10000:04d}"),
                    "title": data.get("title", suggestion[:50]),
                    "description": data.get("description", suggestion),
                    "category": data.get("category", "feature"),
                    "suggested_by": nickname,
                    "suggested_at": datetime.now().isoformat()
                }
                return True, reason, task_data
            else:
                return False, reason, {}

        return False, "Could not parse AI response", {}

    except Exception as e:
        print(f"[SCREEN] Error: {e}")
        # Fallback: basic approval for valid-looking suggestions
        if 10 < len(suggestion) < 500:
            return True, "Fallback approval", {
                "id": f"SUG-{int(time.time()) % 10000:04d}",
                "title": suggestion[:50],
                "description": suggestion,
                "category": "feature",
                "suggested_by": nickname,
                "suggested_at": datetime.now().isoformat()
            }
        return False, f"Screening error: {e}", {}


def add_to_prd(task_data: dict) -> bool:
    """Add approved suggestion to PRD."""
    try:
        with open(PRD_FILE, 'r') as f:
            prd = json.load(f)

        # Add to tasks
        task = {
            "id": task_data["id"],
            "title": task_data["title"],
            "description": task_data["description"],
            "acceptance_criteria": [
                f"Implement feature as suggested by {task_data.get('suggested_by', 'anonymous')}",
                "Ensure it integrates well with existing features",
                "Test thoroughly before marking complete"
            ],
            "passes": False,
            "suggested_by": task_data.get("suggested_by", "anonymous"),
            "suggested_at": task_data.get("suggested_at", datetime.now().isoformat())
        }

        prd["tasks"].append(task)

        # Add to priority order (at the end)
        if "priority_order" in prd:
            prd["priority_order"].append(task_data["id"])

        with open(PRD_FILE, 'w') as f:
            json.dump(prd, f, indent=2)

        return True
    except Exception as e:
        print(f"[PRD] Error: {e}")
        return False


def log_suggestion(nickname: str, suggestion: str, approved: bool, reason: str):
    """Log all suggestions for review."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "nickname": nickname,
        "suggestion": suggestion,
        "approved": approved,
        "reason": reason
    }

    with open(SUGGESTIONS_LOG, 'a') as f:
        f.write(json.dumps(entry) + "\n")


# HTML Template
SUGGESTION_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Suggest a Feature - Ralph Mode</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            border: 2px solid rgba(255, 215, 0, 0.3);
        }
        h1 {
            color: #ffd700;
            text-align: center;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #aaa;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .live-badge {
            display: inline-block;
            background: #ff4757;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 20px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 10px #ff4757; }
            50% { opacity: 0.8; box-shadow: 0 0 20px #ff4757; }
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #fff;
            margin-bottom: 8px;
            font-weight: 500;
        }
        input, textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #ffd700;
        }
        input::placeholder, textarea::placeholder {
            color: rgba(255, 255, 255, 0.5);
        }
        textarea {
            min-height: 120px;
            resize: vertical;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            border: none;
            border-radius: 10px;
            color: #1a1a2e;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(255, 215, 0, 0.3);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            display: none;
        }
        .result.success {
            background: rgba(46, 213, 115, 0.2);
            border: 2px solid #2ed573;
            color: #2ed573;
        }
        .result.error {
            background: rgba(255, 71, 87, 0.2);
            border: 2px solid #ff4757;
            color: #ff4757;
        }
        .result.waiting {
            background: rgba(255, 215, 0, 0.2);
            border: 2px solid #ffd700;
            color: #ffd700;
        }
        .info {
            color: #888;
            font-size: 12px;
            text-align: center;
            margin-top: 20px;
        }
        .ralph-quote {
            color: #4ecdc4;
            font-style: italic;
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div style="text-align: center;">
            <span class="live-badge">● LIVE BUILD</span>
        </div>
        <h1>🍩 Suggest a Feature!</h1>
        <p class="subtitle">Your idea could be built LIVE on stream!</p>

        <form id="suggestionForm">
            <div class="form-group">
                <label for="nickname">Your Nickname</label>
                <input type="text" id="nickname" name="nickname" placeholder="e.g. CoolCoder42" maxlength="30" required>
            </div>

            <div class="form-group">
                <label for="suggestion">Your Suggestion</label>
                <textarea id="suggestion" name="suggestion" placeholder="Describe a feature you'd like to see in Ralph Mode! Be specific about what it should do..." maxlength="500" required></textarea>
            </div>

            <button type="submit" id="submitBtn">🚀 Submit Suggestion</button>
        </form>

        <div id="result" class="result"></div>

        <p class="info">Rate limit: 1 suggestion per hour. AI will screen for relevance.</p>

        <p class="ralph-quote">"I'm helping! I'm a helper!" - Ralph</p>
    </div>

    <script>
        document.getElementById('suggestionForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const btn = document.getElementById('submitBtn');
            const result = document.getElementById('result');
            const nickname = document.getElementById('nickname').value.trim();
            const suggestion = document.getElementById('suggestion').value.trim();

            btn.disabled = true;
            btn.textContent = '⏳ Screening...';

            result.className = 'result waiting';
            result.style.display = 'block';
            result.textContent = 'Ralph is looking at your suggestion...';

            try {
                const response = await fetch('/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nickname, suggestion })
                });

                const data = await response.json();

                if (data.success) {
                    result.className = 'result success';
                    result.innerHTML = `✅ ${data.message}<br><br>Task ID: <strong>${data.task_id}</strong>`;
                    document.getElementById('suggestionForm').reset();
                } else {
                    result.className = 'result error';
                    result.textContent = `❌ ${data.message}`;
                }
            } catch (err) {
                result.className = 'result error';
                result.textContent = '❌ Something went wrong. Try again!';
            }

            btn.disabled = false;
            btn.textContent = '🚀 Submit Suggestion';
        });
    </script>
</body>
</html>
"""


@app.route('/')
def home():
    """Suggestion form page."""
    return render_template_string(SUGGESTION_PAGE)


@app.route('/submit', methods=['POST'])
def submit():
    """Handle suggestion submission."""
    # Get client IP
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()

    # Check rate limit
    allowed, remaining = check_rate_limit(ip)
    if not allowed:
        minutes = remaining // 60
        return jsonify({
            "success": False,
            "message": f"Rate limited! Try again in {minutes} minutes."
        }), 429

    # Get data
    data = request.get_json()
    nickname = data.get('nickname', 'anonymous')[:30].strip()
    suggestion = data.get('suggestion', '')[:500].strip()

    if not nickname:
        nickname = 'anonymous'

    if len(suggestion) < 10:
        return jsonify({
            "success": False,
            "message": "Suggestion too short! Please be more specific."
        }), 400

    # Screen the suggestion
    approved, reason, task_data = screen_suggestion(suggestion, nickname)

    # Log it
    log_suggestion(nickname, suggestion, approved, reason)

    if not approved:
        return jsonify({
            "success": False,
            "message": f"Not approved: {reason}"
        }), 400

    # Add to PRD
    if not add_to_prd(task_data):
        return jsonify({
            "success": False,
            "message": "Failed to add to PRD. Try again!"
        }), 500

    # Record rate limit
    record_submission(ip)

    # Send to Telegram!
    telegram_msg = f"""🎉 *NEW SUGGESTION ADDED!*

👤 *From*: {nickname}
📝 *Task*: [{task_data['id']}] {task_data['title']}

_{task_data['description'][:200]}_

*Ralph squints at screen*
"Ooh! Someone wants us to build something!"

*Stool* "Let me see... yeah, we can do that."

*Ralph jumps up and down*
"YAY! More stuff to make! Thank you {nickname}!"

━━━━━━━━━━━━━
_Added to the PRD queue!_"""

    send_telegram(telegram_msg)

    return jsonify({
        "success": True,
        "message": f"Added to PRD! Ralph will build it!",
        "task_id": task_data['id']
    })


@app.route('/health')
def health():
    """Health check."""
    return jsonify({"status": "ok", "service": "ralph-suggestions"})


if __name__ == '__main__':
    print("=" * 60)
    print("Ralph Mode - Public Suggestions Server")
    print("=" * 60)
    print(f"PRD File: {PRD_FILE}")
    print(f"Rate Limit: {RATE_LIMIT_SECONDS}s (1 hour)")
    print("=" * 60)

    # Run on port 5555
    app.run(host='0.0.0.0', port=5555, debug=False)
