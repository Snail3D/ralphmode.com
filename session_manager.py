"""
Session Manager - Save and load conversations for long-term PRD building

Users can:
- Stack conversations over days/weeks
- Save progress anytime
- Come back and continue
- Generate PRD when ready
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

# Default session directory
SESSIONS_DIR = Path.home() / ".ralph" / "sessions"


def ensure_sessions_dir():
    """Create sessions directory if it doesn't exist"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def list_sessions() -> List[Dict]:
    """List all saved sessions"""
    ensure_sessions_dir()
    sessions = []

    for file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(file) as f:
                data = json.load(f)
                sessions.append({
                    "id": file.stem,
                    "name": data.get("project_name", "Unnamed"),
                    "messages": len(data.get("conversation", [])),
                    "created": data.get("created_at", "Unknown"),
                    "updated": data.get("updated_at", "Unknown"),
                    "file": str(file)
                })
        except:
            pass

    # Sort by last updated
    return sorted(sessions, key=lambda x: x.get("updated", ""), reverse=True)


def save_session(
    session_id: str,
    project_name: str,
    project_description: str,
    conversation: List[Dict],
    metadata: Dict = None
) -> str:
    """Save a session to disk"""
    ensure_sessions_dir()

    filepath = SESSIONS_DIR / f"{session_id}.json"

    # Load existing or create new
    if filepath.exists():
        with open(filepath) as f:
            data = json.load(f)
        data["updated_at"] = datetime.now().isoformat()
    else:
        data = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    # Update fields
    data["project_name"] = project_name
    data["project_description"] = project_description
    data["conversation"] = conversation
    if metadata:
        data["metadata"] = metadata

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    return str(filepath)


def load_session(session_id: str) -> Optional[Dict]:
    """Load a session from disk"""
    ensure_sessions_dir()
    filepath = SESSIONS_DIR / f"{session_id}.json"

    if not filepath.exists():
        return None

    with open(filepath) as f:
        return json.load(f)


def delete_session(session_id: str) -> bool:
    """Delete a session"""
    ensure_sessions_dir()
    filepath = SESSIONS_DIR / f"{session_id}.json"

    if filepath.exists():
        filepath.unlink()
        return True
    return False


def create_session_id(project_name: str = None) -> str:
    """Generate a unique session ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if project_name:
        safe_name = "".join(c for c in project_name if c.isalnum() or c == " ")[:20]
        safe_name = safe_name.replace(" ", "_").lower()
        return f"{safe_name}_{timestamp}"
    return f"session_{timestamp}"


def get_session_summary(session: Dict) -> str:
    """Get a human-readable summary of a session"""
    name = session.get("project_name", "Unnamed Project")
    desc = session.get("project_description", "")[:100]
    msgs = len(session.get("conversation", []))
    updated = session.get("updated_at", "Unknown")

    # Parse the date for nicer display
    try:
        dt = datetime.fromisoformat(updated)
        updated = dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        pass

    return f"""
Project: {name}
Description: {desc}...
Messages: {msgs} in conversation
Last updated: {updated}
"""


def export_conversation_as_text(session: Dict) -> str:
    """Export conversation as readable text (for feeding to other AIs)"""
    lines = [
        f"# Project: {session.get('project_name', 'Unnamed')}",
        f"# Description: {session.get('project_description', '')}",
        "",
        "## Conversation:",
        ""
    ]

    for msg in session.get("conversation", []):
        role = "User" if msg["role"] == "user" else "Ralph"
        lines.append(f"**{role}:** {msg['content']}")
        lines.append("")

    return "\n".join(lines)
