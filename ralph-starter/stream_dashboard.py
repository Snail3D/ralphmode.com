#!/usr/bin/env python3
"""
Ralph Mode Stream Dashboard - Live build viewer for YouTube streaming

This serves a beautiful dashboard that:
1. Shows real-time office chatter
2. Displays current task progress
3. Has suggestion QR code
4. Gets captured and streamed to YouTube

Run: python stream_dashboard.py
Then: ./stream-to-youtube.sh (captures and streams)
"""

import os
import json
import time
import asyncio
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from collections import deque
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS
from dotenv import load_dotenv
import threading

load_dotenv()

app = Flask(__name__)
CORS(app)

# Config
PROJECT_DIR = Path(__file__).parent
PRD_FILE = PROJECT_DIR / "scripts/ralph/prd.json"
RATE_LIMIT_FILE = PROJECT_DIR / "scripts/ralph/.suggestion_ratelimit"

# Message queue for real-time updates (last 50 messages)
message_queue = deque(maxlen=50)
current_task = {"id": "---", "title": "Waiting...", "description": ""}
stats = {"done": 0, "total": 0, "percent": 0}

# Groq for screening
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SUGGESTIONS_LOG = PROJECT_DIR / "scripts/ralph/.suggestions_log"

# Server URL for QR code
SERVER_URL = os.getenv("STREAM_SERVER_URL", "http://69.164.201.191:5555")


def add_message(character: str, text: str, action: str = ""):
    """Add a message to the queue."""
    message_queue.append({
        "id": int(time.time() * 1000),
        "character": character,
        "text": text,
        "action": action,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })


def update_stats():
    """Update task statistics from PRD."""
    global stats, current_task
    try:
        with open(PRD_FILE, 'r') as f:
            prd = json.load(f)

        tasks = prd.get("tasks", [])
        stats["total"] = len(tasks)
        stats["done"] = sum(1 for t in tasks if t.get("passes", False))
        stats["percent"] = int((stats["done"] / stats["total"]) * 100) if stats["total"] > 0 else 0

        # Find current task
        priority_order = prd.get("priority_order", [])
        task_map = {t["id"]: t for t in tasks}

        for task_id in priority_order:
            if task_id in task_map and not task_map[task_id].get("passes", False):
                current_task = task_map[task_id]
                break
    except:
        pass


def get_ip_hash(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def check_rate_limit(ip: str) -> tuple[bool, int]:
    ip_hash = get_ip_hash(ip)
    rate_data = {}
    if RATE_LIMIT_FILE.exists():
        try:
            rate_data = json.loads(RATE_LIMIT_FILE.read_text())
        except:
            pass

    now = time.time()
    last_submit = rate_data.get(ip_hash, 0)
    if now - last_submit < 3600:
        return False, int(3600 - (now - last_submit))
    return True, 0


def record_submission(ip: str):
    ip_hash = get_ip_hash(ip)
    rate_data = {}
    if RATE_LIMIT_FILE.exists():
        try:
            rate_data = json.loads(RATE_LIMIT_FILE.read_text())
        except:
            pass
    rate_data[ip_hash] = time.time()
    cutoff = time.time() - 7200
    rate_data = {k: v for k, v in rate_data.items() if v > cutoff}
    RATE_LIMIT_FILE.write_text(json.dumps(rate_data))


def screen_and_add_suggestion(nickname: str, suggestion: str, build_tag: str = "") -> tuple[bool, str, str]:
    """
    Screen suggestion and add to PRD.
    We're gracious - we accept everything and at minimum make a note of it.
    Security/hotfix suggestions get priority but need scrutiny.
    """
    if len(suggestion) < 5:
        return False, "Just a bit more detail please!", ""

    # Generate task ID
    task_id = f"SUG-{int(time.time()) % 10000:04d}"

    # Extract priority if mentioned (look for numbers like 8/10, priority 7, etc.)
    import re
    priority_match = re.search(r'priority[:\s]*(\d+)|(\d+)\s*/\s*10', suggestion.lower())
    priority = 5  # Default medium priority
    if priority_match:
        priority = int(priority_match.group(1) or priority_match.group(2))
        priority = min(10, max(1, priority))

    # Detect security/hotfix keywords - these get scrutinized AND priority boost
    suggestion_lower = suggestion.lower()
    security_keywords = ['security', 'vulnerability', 'exploit', 'xss', 'injection',
                        'breach', 'leak', 'password', 'auth', 'csrf', 'attack']
    hotfix_keywords = ['hotfix', 'critical', 'urgent', 'broken', 'crash', 'down',
                      'emergency', 'fix immediately', 'production issue', 'blocking']

    is_security = any(kw in suggestion_lower for kw in security_keywords)
    is_hotfix = any(kw in suggestion_lower for kw in hotfix_keywords)
    needs_scrutiny = is_security or is_hotfix

    # Boost priority for security/hotfix but mark for scrutiny
    if needs_scrutiny:
        priority = max(priority, 9)  # Bump to high priority

    # Generate the GitHub release URL for this build
    github_release_url = f"https://github.com/Snail3D/ralphmode.com/releases/tag/user-{build_tag}" if build_tag else ""

    # Create the task - we're accepting, we'll figure out implementation later
    task = {
        "id": task_id,
        "title": suggestion.split('\n')[0][:80] if '\n' in suggestion else suggestion[:80],
        "description": f"Community suggestion from {nickname}:\n\n{suggestion}",
        "acceptance_criteria": [
            "Review and understand the user's intent",
            "Implement if feasible within Ralph Mode's scope",
            "Respond gracefully if not implementable"
        ],
        "passes": False,
        "suggested_by": nickname,
        "source": "web",
        "priority": priority,
        "suggested_at": datetime.now().isoformat(),
        "build_tag": build_tag,
        "github_release_url": github_release_url,
        "needs_scrutiny": needs_scrutiny,
        "is_security": is_security,
        "is_hotfix": is_hotfix
    }

    try:
        with open(PRD_FILE, 'r') as f:
            prd = json.load(f)

        prd["tasks"].append(task)
        if "priority_order" in prd:
            # Add based on priority - higher priority = earlier in list
            if priority >= 8:
                # High priority - add near the front (but not first)
                insert_pos = min(5, len(prd["priority_order"]))
                prd["priority_order"].insert(insert_pos, task_id)
            else:
                prd["priority_order"].append(task_id)

        with open(PRD_FILE, 'w') as f:
            json.dump(prd, f, indent=2)

        # Log the suggestion for audience interaction
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "nickname": nickname,
            "suggestion": suggestion,
            "task_id": task_id,
            "priority": priority,
            "build_tag": build_tag,
            "needs_scrutiny": needs_scrutiny,
            "is_security": is_security,
            "is_hotfix": is_hotfix,
            "approved": True
        }
        with open(SUGGESTIONS_LOG, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")

        # Celebration messages - make the user feel valued!
        add_message("Ralph", f"OOOOH! Someone's talking to us!", "perks up")
        add_message("Stool", f"It's {nickname}. They have an idea.", "reads screen")
        add_message("Gomer", f"What do they want?", "excited")
        add_message("Ralph", f"They said... they said...", "squints hard")
        add_message("Ralph", f"Something about {suggestion[:30].split()[0] if suggestion.split() else 'stuff'}!", "proud")

        if build_tag:
            add_message("Stool", f"They called it '{build_tag}'. Noted as {task_id}.", "types")
        else:
            add_message("Stool", f"Noted. {task_id}. We'll look into it.", "types")

        add_message("Ralph", f"Thank you {nickname}! We heard you!", "waves enthusiastically")

        if priority >= 8:
            add_message("Stool", f"They said it's important. Moving it up.", "adjusts list")
            add_message("Ralph", f"IMPORTANT! Like... like breakfast!", "nods seriously")

        # Security/hotfix items need scrutiny before action
        if needs_scrutiny:
            if is_security:
                add_message("Stool", f"Hold up. This mentions security. Need to verify first.", "puts on glasses")
                add_message("Gomer", f"Scrutiny mode activated!", "salutes")
                add_message("Ralph", f"We gotta check our brakes before we drive!", "nods wisely")
            elif is_hotfix:
                add_message("Stool", f"Marked as urgent. But we check before we wreck.", "raises eyebrow")
                add_message("Ralph", f"Measure twice, cut once! ...wait, what are we cutting?", "confused")

        return True, f"Thank you! We've noted your idea as {task_id}!", task_id

    except Exception as e:
        # Even on error, log it
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "nickname": nickname,
                "suggestion": suggestion,
                "error": str(e),
                "approved": False
            }
            with open(SUGGESTIONS_LOG, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except:
            pass

        return False, "Oops! Let me try again...", ""


# Dashboard HTML - Clean, mobile-friendly, prominent chat
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ralph Mode - Live Build</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --accent-gold: #fbbf24;
            --accent-cyan: #22d3ee;
            --accent-purple: #a78bfa;
            --accent-green: #34d399;
            --accent-red: #f87171;
            --text-primary: #ffffff;
            --text-secondary: #94a3b8;
        }

        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
        }

        .container {
            display: grid;
            grid-template-rows: auto 1fr auto;
            height: 100vh;
            max-width: 1920px;
            margin: 0 auto;
        }

        /* Header - Compact */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            background: linear-gradient(180deg, rgba(251,191,36,0.1) 0%, transparent 100%);
            border-bottom: 1px solid rgba(251,191,36,0.2);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .logo-icon {
            font-size: 40px;
        }

        .logo-text {
            font-size: 28px;
            font-weight: 700;
            color: var(--accent-gold);
            letter-spacing: -1px;
        }

        .live-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(248,113,113,0.15);
            border: 1px solid var(--accent-red);
            padding: 10px 20px;
            border-radius: 30px;
        }

        .live-dot {
            width: 12px;
            height: 12px;
            background: var(--accent-red);
            border-radius: 50%;
            animation: livePulse 1.5s infinite;
        }

        @keyframes livePulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }

        .live-text {
            font-weight: 600;
            color: var(--accent-red);
            font-size: 16px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .stats-row {
            display: flex;
            gap: 30px;
        }

        .stat {
            text-align: center;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: var(--accent-cyan);
        }

        .stat-label {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Main Content */
        .main {
            display: grid;
            grid-template-columns: 1fr 320px;
            gap: 30px;
            padding: 30px 40px;
            overflow: hidden;
        }

        /* Chat - THE STAR */
        .chat-section {
            display: flex;
            flex-direction: column;
            background: var(--bg-card);
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .chat-header {
            padding: 20px 25px;
            background: rgba(34,211,238,0.1);
            border-bottom: 1px solid rgba(34,211,238,0.2);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .chat-header-icon {
            font-size: 24px;
        }

        .chat-header-text {
            font-size: 18px;
            font-weight: 600;
            color: var(--accent-cyan);
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .message {
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 16px 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            border-left: 4px solid var(--accent-gold);
            animation: messageIn 0.4s ease-out;
        }

        @keyframes messageIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.ralph { border-left-color: var(--accent-gold); }
        .message.stool { border-left-color: var(--accent-cyan); }
        .message.gomer { border-left-color: var(--accent-purple); }

        .message-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .character-name {
            font-weight: 700;
            font-size: 18px;
        }

        .character-name.ralph { color: var(--accent-gold); }
        .character-name.stool { color: var(--accent-cyan); }
        .character-name.gomer { color: var(--accent-purple); }

        .message-action {
            font-size: 14px;
            color: var(--text-secondary);
            font-style: italic;
        }

        .message-text {
            font-size: 22px;
            line-height: 1.5;
            color: var(--text-primary);
        }

        /* Sidebar */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card {
            background: var(--bg-card);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .card-icon {
            font-size: 20px;
        }

        .card-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .task-card .card-header { border-bottom-color: rgba(251,191,36,0.3); }
        .suggest-card .card-header { border-bottom-color: rgba(167,139,250,0.3); }

        .current-task-id {
            font-size: 14px;
            color: var(--accent-cyan);
            font-weight: 600;
            margin-bottom: 8px;
        }

        .current-task-title {
            font-size: 18px;
            font-weight: 600;
            line-height: 1.4;
        }

        .qr-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }

        .qr-code {
            background: #fff;
            padding: 12px;
            border-radius: 16px;
            margin-bottom: 15px;
        }

        .qr-code img {
            display: block;
            width: 140px;
            height: 140px;
        }

        .qr-label {
            font-size: 16px;
            font-weight: 600;
            color: var(--accent-purple);
        }

        .qr-sublabel {
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: 5px;
        }

        /* Footer - Progress */
        .footer {
            padding: 25px 40px;
            background: var(--bg-card);
            border-top: 1px solid rgba(255,255,255,0.05);
        }

        .progress-container {
            display: flex;
            align-items: center;
            gap: 25px;
        }

        .progress-label {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 120px;
        }

        .progress-icon {
            font-size: 24px;
        }

        .progress-text {
            font-size: 14px;
            font-weight: 600;
            color: var(--accent-green);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .progress-bar {
            flex: 1;
            height: 20px;
            background: rgba(52,211,153,0.15);
            border-radius: 10px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-green), var(--accent-cyan));
            border-radius: 10px;
            transition: width 0.5s ease-out;
            position: relative;
        }

        .progress-fill::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .progress-percent {
            font-size: 28px;
            font-weight: 700;
            color: var(--accent-green);
            min-width: 80px;
            text-align: right;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <span class="logo-icon">🍩</span>
                <span class="logo-text">RALPH MODE</span>
            </div>

            <div class="live-indicator">
                <div class="live-dot"></div>
                <span class="live-text">Building Live</span>
            </div>

            <div class="stats-row">
                <div class="stat">
                    <div class="stat-value" id="tasksDone">0</div>
                    <div class="stat-label">Complete</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="tasksTotal">0</div>
                    <div class="stat-label">Total</div>
                </div>
            </div>
        </header>

        <main class="main">
            <section class="chat-section">
                <div class="chat-header">
                    <span class="chat-header-icon">💬</span>
                    <span class="chat-header-text">The Office</span>
                </div>
                <div class="messages" id="messages"></div>
            </section>

            <aside class="sidebar">
                <div class="card task-card">
                    <div class="card-header">
                        <span class="card-icon">🔧</span>
                        <span class="card-title">Currently Building</span>
                    </div>
                    <div class="current-task-id" id="taskId">---</div>
                    <div class="current-task-title" id="taskTitle">Waiting...</div>
                </div>

                <div class="card suggest-card">
                    <div class="card-header">
                        <span class="card-icon">💡</span>
                        <span class="card-title">Your Ideas</span>
                    </div>
                    <div class="qr-section">
                        <div class="qr-code">
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data={{ suggest_url }}" alt="QR">
                        </div>
                        <div class="qr-label">Suggest a Feature!</div>
                        <div class="qr-sublabel">Scan or visit link in description</div>
                    </div>
                </div>
            </aside>
        </main>

        <footer class="footer">
            <div class="progress-container">
                <div class="progress-label">
                    <span class="progress-icon">📊</span>
                    <span class="progress-text">Progress</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                </div>
                <div class="progress-percent" id="progressText">0%</div>
            </div>
        </footer>
    </div>

    <script>
        async function fetchUpdates() {
            try {
                const res = await fetch('/api/state');
                const data = await res.json();

                document.getElementById('tasksDone').textContent = data.stats.done;
                document.getElementById('tasksTotal').textContent = data.stats.total;
                document.getElementById('progressFill').style.width = data.stats.percent + '%';
                document.getElementById('progressText').textContent = data.stats.percent + '%';

                document.getElementById('taskId').textContent = data.current_task.id;
                document.getElementById('taskTitle').textContent = data.current_task.title;

                const messagesDiv = document.getElementById('messages');
                const currentIds = new Set([...messagesDiv.querySelectorAll('.message')].map(m => m.dataset.id));

                data.messages.forEach(msg => {
                    if (!currentIds.has(String(msg.id))) {
                        const div = document.createElement('div');
                        const charClass = msg.character.toLowerCase();
                        div.className = 'message ' + charClass;
                        div.dataset.id = msg.id;

                        div.innerHTML = `
                            <div class="message-header">
                                <span class="character-name ${charClass}">${msg.character}</span>
                                ${msg.action ? `<span class="message-action">*${msg.action}*</span>` : ''}
                            </div>
                            <div class="message-text">"${msg.text}"</div>
                        `;

                        messagesDiv.appendChild(div);
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;

                        while (messagesDiv.children.length > 15) {
                            messagesDiv.removeChild(messagesDiv.firstChild);
                        }
                    }
                });
            } catch (e) {
                console.error('Update error:', e);
            }
        }

        fetchUpdates();
        setInterval(fetchUpdates, 2000);
    </script>
</body>
</html>
"""

SUGGEST_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Suggest a Feature - Ralph Mode</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --accent-gold: #fbbf24;
            --accent-cyan: #22d3ee;
            --accent-red: #f87171;
            --accent-green: #34d399;
            --text-primary: #ffffff;
            --text-secondary: #94a3b8;
        }

        body {
            font-family: 'Space Grotesk', sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            min-height: -webkit-fill-available;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            touch-action: manipulation;
            -webkit-user-select: none;
            user-select: none;
        }

        .header {
            padding: 15px 20px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            flex-shrink: 0;
        }

        .logo {
            font-size: 22px;
            font-weight: 700;
            color: var(--accent-gold);
        }

        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 15px;
            overflow: hidden;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding-bottom: 15px;
            -webkit-overflow-scrolling: touch;
        }

        .message {
            max-width: 90%;
            padding: 14px 18px;
            border-radius: 20px;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.bot {
            background: var(--bg-card);
            border: 1px solid rgba(255,255,255,0.1);
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }

        .message.user {
            background: linear-gradient(135deg, var(--accent-gold), #f59e0b);
            color: #000;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }

        .message .sender {
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 5px;
            opacity: 0.7;
        }

        .message .text {
            font-size: 15px;
            line-height: 1.4;
        }

        /* Voice Input Area */
        .voice-area {
            padding: 20px 10px;
            border-top: 1px solid rgba(255,255,255,0.1);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
            flex-shrink: 0;
        }

        .voice-hint {
            font-size: 14px;
            color: var(--text-secondary);
            text-align: center;
        }

        .mic-button {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-gold), #f59e0b);
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 20px rgba(251, 191, 36, 0.3);
            -webkit-tap-highlight-color: transparent;
        }

        .mic-button:active, .mic-button.recording {
            transform: scale(1.1);
            background: linear-gradient(135deg, var(--accent-red), #ef4444);
            box-shadow: 0 4px 30px rgba(248, 113, 113, 0.5);
        }

        .mic-button.recording {
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0%, 100% { box-shadow: 0 4px 30px rgba(248, 113, 113, 0.5); }
            50% { box-shadow: 0 4px 50px rgba(248, 113, 113, 0.8); }
        }

        .mic-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .recording-indicator {
            display: none;
            align-items: center;
            gap: 8px;
            color: var(--accent-red);
            font-weight: 600;
        }

        .recording-indicator.active {
            display: flex;
        }

        .recording-dot {
            width: 10px;
            height: 10px;
            background: var(--accent-red);
            border-radius: 50%;
            animation: blink 0.8s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .transcribing {
            display: none;
            color: var(--accent-cyan);
            font-size: 14px;
        }

        .transcribing.active {
            display: block;
        }

        .success-card {
            background: rgba(52,211,153,0.1);
            border: 2px solid var(--accent-green);
            border-radius: 20px;
            padding: 25px;
            text-align: center;
            margin-top: 15px;
        }

        .success-card h2 {
            color: var(--accent-green);
            margin-bottom: 8px;
            font-size: 20px;
        }

        .success-card .task-id {
            font-size: 22px;
            font-weight: 700;
            color: var(--accent-cyan);
        }

        .typing {
            display: flex;
            gap: 4px;
            padding: 8px 0;
        }

        .typing span {
            width: 8px;
            height: 8px;
            background: var(--text-secondary);
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }

        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-8px); }
        }

        /* Waveform visualization */
        .waveform {
            display: none;
            height: 40px;
            gap: 3px;
            align-items: center;
            justify-content: center;
        }

        .waveform.active {
            display: flex;
        }

        .wave-bar {
            width: 4px;
            background: var(--accent-red);
            border-radius: 2px;
            animation: wave 0.5s ease-in-out infinite;
        }

        .wave-bar:nth-child(1) { animation-delay: 0s; height: 15px; }
        .wave-bar:nth-child(2) { animation-delay: 0.1s; height: 25px; }
        .wave-bar:nth-child(3) { animation-delay: 0.2s; height: 35px; }
        .wave-bar:nth-child(4) { animation-delay: 0.3s; height: 25px; }
        .wave-bar:nth-child(5) { animation-delay: 0.4s; height: 15px; }

        @keyframes wave {
            0%, 100% { transform: scaleY(1); }
            50% { transform: scaleY(0.5); }
        }

        /* Error state */
        .error-msg {
            background: rgba(248, 113, 113, 0.1);
            border: 1px solid var(--accent-red);
            color: var(--accent-red);
            padding: 12px 16px;
            border-radius: 12px;
            font-size: 14px;
            text-align: center;
            display: none;
        }

        .error-msg.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🍩 Ralph Mode</div>
    </div>

    <div class="chat-container">
        <div class="messages" id="messages"></div>

        <div class="voice-area" id="voiceArea">
            <div class="voice-hint" id="voiceHint">Hold to talk</div>

            <div class="waveform" id="waveform">
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
                <div class="wave-bar"></div>
            </div>

            <div class="recording-indicator" id="recordingIndicator">
                <div class="recording-dot"></div>
                <span>Listening...</span>
            </div>

            <div class="transcribing" id="transcribing">Processing your voice...</div>

            <button class="mic-button" id="micButton">🎤</button>

            <div class="error-msg" id="errorMsg"></div>
        </div>
    </div>

    <script>
        // Conversation flow
        const questions = [
            { key: 'nickname', q: "Hi! I'm Ralph! Hold the button and tell me your name! 🍩" },
            { key: 'idea', q: "Nice to meet you, {nickname}! What feature would you like us to build?" },
            { key: 'problem', q: "Interesting! What problem does this solve? Why do you need it?" },
            { key: 'vision', q: "I think I'm getting it! How would you imagine this working?" },
            { key: 'priority', q: "How important is this? Say a number from 1 to 10!" },
            { key: 'buildTag', q: "Last one! Give your build a short name so you can find it later! Like 'dark-mode' or 'speed-boost'!" }
        ];

        let currentStep = 0;
        let answers = {};
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;

        const micButton = document.getElementById('micButton');
        const voiceHint = document.getElementById('voiceHint');
        const waveform = document.getElementById('waveform');
        const recordingIndicator = document.getElementById('recordingIndicator');
        const transcribing = document.getElementById('transcribing');
        const errorMsg = document.getElementById('errorMsg');

        function addMessage(text, isBot, sender = '') {
            const messages = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'message ' + (isBot ? 'bot' : 'user');
            div.innerHTML = `
                ${sender ? `<div class="sender">${sender}</div>` : ''}
                <div class="text">${text}</div>
            `;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function showTyping() {
            const messages = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'message bot';
            div.id = 'typing';
            div.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function hideTyping() {
            const typing = document.getElementById('typing');
            if (typing) typing.remove();
        }

        function showError(msg) {
            errorMsg.textContent = msg;
            errorMsg.classList.add('active');
            setTimeout(() => errorMsg.classList.remove('active'), 3000);
        }

        function askQuestion(step) {
            const q = questions[step];
            let text = q.q;

            for (const [key, val] of Object.entries(answers)) {
                text = text.replace(`{${key}}`, val);
            }

            showTyping();
            setTimeout(() => {
                hideTyping();
                addMessage(text, true, 'Ralph');
            }, 600);
        }

        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (e) => {
                    audioChunks.push(e.data);
                };

                mediaRecorder.onstop = async () => {
                    stream.getTracks().forEach(track => track.stop());
                    await processAudio();
                };

                mediaRecorder.start();
                isRecording = true;

                micButton.classList.add('recording');
                waveform.classList.add('active');
                recordingIndicator.classList.add('active');
                voiceHint.textContent = 'Release when done';

            } catch (err) {
                console.error('Mic error:', err);
                showError('Please allow microphone access!');
            }
        }

        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;

                micButton.classList.remove('recording');
                waveform.classList.remove('active');
                recordingIndicator.classList.remove('active');
                transcribing.classList.add('active');
                voiceHint.textContent = '';
                micButton.disabled = true;
            }
        }

        async function processAudio() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

            // Send to server for transcription
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');

            try {
                const res = await fetch('/api/transcribe', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();

                transcribing.classList.remove('active');
                micButton.disabled = false;
                voiceHint.textContent = 'Hold to talk';

                if (data.success && data.text) {
                    handleUserResponse(data.text);
                } else {
                    showError(data.error || "Couldn't hear that. Try again!");
                }
            } catch (err) {
                console.error('Transcribe error:', err);
                transcribing.classList.remove('active');
                micButton.disabled = false;
                voiceHint.textContent = 'Hold to talk';
                showError("Oops! Something went wrong.");
            }
        }

        async function handleUserResponse(text) {
            addMessage(text, false);

            answers[questions[currentStep].key] = text;
            currentStep++;

            if (currentStep < questions.length) {
                setTimeout(() => askQuestion(currentStep), 500);
            } else {
                await submitSuggestion();
            }
        }

        async function submitSuggestion() {
            showTyping();
            micButton.disabled = true;
            voiceHint.textContent = 'Submitting...';

            // Clean up the build tag - lowercase, replace spaces with dashes
            const cleanTag = answers.buildTag
                .toLowerCase()
                .replace(/[^a-z0-9\s-]/g, '')
                .replace(/\s+/g, '-')
                .substring(0, 30);

            const suggestion = `
Feature: ${answers.idea}
Problem: ${answers.problem}
Vision: ${answers.vision}
Priority: ${answers.priority}/10
Build Tag: ${cleanTag}
            `.trim();

            try {
                const res = await fetch('/api/suggest', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        nickname: answers.nickname,
                        suggestion: suggestion,
                        build_tag: cleanTag
                    })
                });
                const data = await res.json();

                hideTyping();

                if (data.success) {
                    addMessage(`WOW! Thank you ${answers.nickname}! Your idea is now in our build queue! 🎉`, true, 'Ralph');

                    // Build the GitHub release URL they can bookmark
                    const releaseUrl = `https://github.com/Snail3D/ralphmode.com/releases/tag/user-${cleanTag}`;

                    setTimeout(() => {
                        const messages = document.getElementById('messages');
                        const card = document.createElement('div');
                        card.className = 'success-card';
                        card.innerHTML = `
                            <h2>🎉 Suggestion Added!</h2>
                            <p>Your task ID:</p>
                            <div class="task-id">${data.task_id}</div>
                            <p style="margin-top: 15px; color: var(--text-secondary); font-size: 13px;">
                                If we build it, find your release at:
                            </p>
                            <a href="${releaseUrl}" target="_blank" style="color: var(--accent-cyan); word-break: break-all; font-size: 12px; display: block; margin-top: 8px;">
                                ${releaseUrl}
                            </a>
                            <p style="margin-top: 12px; font-size: 11px; color: var(--text-secondary);">
                                📌 Bookmark it!
                            </p>
                        `;
                        messages.appendChild(card);
                        messages.scrollTop = messages.scrollHeight;
                    }, 800);

                    document.getElementById('voiceArea').style.display = 'none';
                } else {
                    addMessage(`Oops! ${data.message}. Let's try again!`, true, 'Ralph');
                    currentStep = 0;
                    answers = {};
                    micButton.disabled = false;
                    voiceHint.textContent = 'Hold to talk';
                    setTimeout(() => askQuestion(0), 1000);
                }
            } catch (e) {
                hideTyping();
                micButton.disabled = false;
                voiceHint.textContent = 'Hold to talk';
                showError("Network error. Try again!");
            }
        }

        // Touch/mouse events for hold-to-talk
        micButton.addEventListener('mousedown', (e) => {
            e.preventDefault();
            startRecording();
        });

        micButton.addEventListener('mouseup', (e) => {
            e.preventDefault();
            stopRecording();
        });

        micButton.addEventListener('mouseleave', (e) => {
            if (isRecording) stopRecording();
        });

        // Touch events for mobile
        micButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            startRecording();
        });

        micButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            stopRecording();
        });

        // Start conversation
        setTimeout(() => askQuestion(0), 500);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Main dashboard for streaming."""
    return render_template_string(DASHBOARD_HTML, suggest_url=f"{SERVER_URL}/suggest")


@app.route('/suggest')
def suggest_page():
    """Suggestion form page."""
    return render_template_string(SUGGEST_PAGE)


@app.route('/api/state')
def api_state():
    """Get current state for dashboard."""
    update_stats()
    return jsonify({
        "messages": list(message_queue),
        "current_task": current_task,
        "stats": stats
    })


@app.route('/api/suggest', methods=['POST'])
def api_suggest():
    """Handle suggestion submission."""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()

    allowed, remaining = check_rate_limit(ip)
    if not allowed:
        return jsonify({"success": False, "message": f"Wait {remaining//60} minutes"}), 429

    data = request.get_json()
    nickname = data.get('nickname', 'anonymous')[:30].strip() or 'anonymous'
    suggestion = data.get('suggestion', '')[:500].strip()
    build_tag = data.get('build_tag', '')[:30].strip()

    if len(suggestion) < 10:
        return jsonify({"success": False, "message": "Too short!"}), 400

    success, message, task_id = screen_and_add_suggestion(nickname, suggestion, build_tag)

    if success:
        record_submission(ip)
        return jsonify({"success": True, "message": message, "task_id": task_id, "build_tag": build_tag})
    else:
        return jsonify({"success": False, "message": message}), 400


@app.route('/api/message', methods=['POST'])
def api_message():
    """Add a message (called by glm_builder)."""
    data = request.get_json()
    add_message(
        data.get('character', 'Ralph'),
        data.get('text', ''),
        data.get('action', '')
    )
    return jsonify({"success": True})


@app.route('/api/transcribe', methods=['POST'])
def api_transcribe():
    """Transcribe audio using Groq Whisper."""
    if 'audio' not in request.files:
        return jsonify({"success": False, "error": "No audio file"}), 400

    audio_file = request.files['audio']

    if not GROQ_API_KEY:
        return jsonify({"success": False, "error": "Transcription not configured"}), 500

    try:
        # Save temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        # Call Groq Whisper API
        import subprocess

        # Convert webm to wav for better compatibility
        wav_path = tmp_path.replace('.webm', '.wav')
        try:
            subprocess.run([
                'ffmpeg', '-y', '-i', tmp_path, '-ar', '16000', '-ac', '1', wav_path
            ], capture_output=True, timeout=10)
        except Exception as e:
            print(f"[TRANSCRIBE] ffmpeg error: {e}, using original file")
            wav_path = tmp_path

        # Send to Groq
        with open(wav_path, 'rb') as f:
            response = requests.post(
                'https://api.groq.com/openai/v1/audio/transcriptions',
                headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
                files={'file': ('audio.wav', f, 'audio/wav')},
                data={'model': 'whisper-large-v3-turbo'},
                timeout=30
            )

        # Cleanup
        import os
        try:
            os.unlink(tmp_path)
            if wav_path != tmp_path:
                os.unlink(wav_path)
        except:
            pass

        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '').strip()
            if text:
                return jsonify({"success": True, "text": text})
            else:
                return jsonify({"success": False, "error": "No speech detected"})
        else:
            print(f"[TRANSCRIBE] Groq error: {response.status_code} - {response.text}")
            return jsonify({"success": False, "error": "Transcription failed"}), 500

    except Exception as e:
        print(f"[TRANSCRIBE] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health')
def health():
    return jsonify({"status": "ok"})


# Background thread to add periodic messages
def background_updates():
    """Add occasional updates."""
    import random

    idle_messages = [
        ("Ralph", "Are we there yet?", "looks around"),
        ("Stool", "Still working.", "types"),
        ("Gomer", "This is exciting!", "watches screen"),
        ("Ralph", "I like computers.", "pats monitor"),
        ("Stool", "Don't touch that.", "sighs"),
        ("Ralph", "My chair squeaks!", "spins"),
    ]

    while True:
        time.sleep(30)  # Every 30 seconds
        if len(message_queue) > 0:
            # Only add idle chatter if no recent messages
            last_msg_time = message_queue[-1].get('id', 0) / 1000
            if time.time() - last_msg_time > 20:
                char, text, action = random.choice(idle_messages)
                add_message(char, text, action)


if __name__ == '__main__':
    print("=" * 60)
    print("Ralph Mode - Stream Dashboard")
    print("=" * 60)
    print(f"Dashboard: http://0.0.0.0:5555")
    print(f"Suggest:   http://0.0.0.0:5555/suggest")
    print("=" * 60)

    # Start background thread
    bg_thread = threading.Thread(target=background_updates, daemon=True)
    bg_thread.start()

    # Add welcome messages
    add_message("Ralph", "Good morning Mr. Worms!", "waves at camera")
    add_message("Stool", "Starting up the systems.", "types")
    add_message("Gomer", "Golly, we're live!", "looks excited")

    app.run(host='0.0.0.0', port=5555, debug=False, threaded=True)
