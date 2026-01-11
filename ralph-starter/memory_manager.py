#!/usr/bin/env python3
"""
Memory Manager for Ralph Mode

BM-001: Between-Session Memory Gap
Ralph forgets PREVIOUS sessions, remembers CURRENT session.

This module handles persistent memory across sessions for Ralph and his team.
Each user gets a session history that tracks:
- Project names and codebases worked on
- Key decisions and requirements
- Worker discoveries and insights
- Completed tasks and outcomes
- Session summaries

When a new session starts, Ralph can reference what happened before.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

MEMORY_DIR = Path(__file__).parent / "ralph_memories"
MEMORY_DIR.mkdir(exist_ok=True)


def get_memory_file(user_id: int) -> Path:
    """Get path to user's Ralph session memory file."""
    return MEMORY_DIR / f"{user_id}_sessions.json"


def load_session_history(user_id: int) -> List[Dict[str, Any]]:
    """Load all previous session summaries for a user.

    Returns:
        List of session summary dicts, newest first
    """
    memory_file = get_memory_file(user_id)
    if memory_file.exists():
        try:
            with open(memory_file, 'r') as f:
                data = json.load(f)
                # Return sessions in reverse chronological order
                return data.get('sessions', [])
        except Exception as e:
            print(f"Error loading session history: {e}")
            return []
    return []


def save_session_summary(user_id: int, session_data: Dict[str, Any]):
    """Save a session summary to persistent memory.

    Args:
        user_id: Telegram user ID
        session_data: Dict containing session summary info
    """
    memory_file = get_memory_file(user_id)

    # Load existing history
    history = load_session_history(user_id)

    # Add new session at the beginning (newest first)
    session_summary = {
        "session_id": len(history) + 1,
        "timestamp": datetime.now().isoformat(),
        "project_name": session_data.get('project_name', 'Unknown Project'),
        "tasks_completed": session_data.get('tasks_completed', 0),
        "tasks_total": session_data.get('tasks_total', 0),
        "key_decisions": session_data.get('key_decisions', []),
        "requirements": session_data.get('requirements', []),
        "codebase_insights": session_data.get('codebase_insights', {}),
        "outcome": session_data.get('outcome', 'Session ended'),
        "duration_minutes": session_data.get('duration_minutes', 0),
        "workers_involved": session_data.get('workers_involved', []),
    }

    history.insert(0, session_summary)

    # Keep last 20 sessions max
    if len(history) > 20:
        history = history[:20]

    # Save back to file
    with open(memory_file, 'w') as f:
        json.dump({'sessions': history}, f, indent=2)


def get_previous_session_context(user_id: int, max_sessions: int = 3) -> str:
    """Build context string about previous sessions for AI prompts.

    Args:
        user_id: Telegram user ID
        max_sessions: How many recent sessions to include

    Returns:
        Formatted string describing previous sessions
    """
    history = load_session_history(user_id)

    if not history:
        return ""

    # Take most recent sessions
    recent = history[:max_sessions]

    context_parts = ["\n--- Ralph's Memory of Previous Sessions ---"]

    for i, session in enumerate(recent, 1):
        timestamp = session.get('timestamp', '')[:10]  # Just the date
        project = session.get('project_name', 'Unknown Project')
        tasks_done = session.get('tasks_completed', 0)
        tasks_total = session.get('tasks_total', 0)
        outcome = session.get('outcome', 'Session ended')

        context_parts.append(
            f"\nSession {i} ({timestamp}) - {project}:"
        )
        context_parts.append(
            f"  Completed {tasks_done}/{tasks_total} tasks. {outcome}"
        )

        # Include key decisions if any
        decisions = session.get('key_decisions', [])
        if decisions:
            context_parts.append(f"  Key decisions: {', '.join(decisions[:3])}")

        # Include requirements if any
        requirements = session.get('requirements', [])
        if requirements:
            req_summary = [r.get('directive', r) if isinstance(r, dict) else r for r in requirements[:3]]
            context_parts.append(f"  Requirements: {', '.join(req_summary)}")

    context_parts.append("--- End Previous Sessions ---\n")

    return "\n".join(context_parts)


def get_project_history(user_id: int, project_name: str) -> List[Dict[str, Any]]:
    """Get all previous sessions for a specific project.

    Args:
        user_id: Telegram user ID
        project_name: Name of the project to find

    Returns:
        List of session summaries for that project
    """
    history = load_session_history(user_id)
    return [s for s in history if s.get('project_name', '').lower() == project_name.lower()]


def extract_session_summary_from_active(active_session: Dict[str, Any]) -> Dict[str, Any]:
    """Extract summary data from an active session for storage.

    Args:
        active_session: Current session dict from ralph_bot.active_sessions

    Returns:
        Summary dict ready for save_session_summary
    """
    start_time = active_session.get('started') or active_session.get('start_time')
    duration_minutes = 0
    if start_time:
        duration = datetime.now() - start_time
        duration_minutes = int(duration.total_seconds() / 60)

    # Extract key decisions from requirements
    requirements = active_session.get('requirements', [])
    key_decisions = [
        req.get('directive', req) if isinstance(req, dict) else req
        for req in requirements[:10]  # Top 10 requirements
    ]

    # Get workers who were involved (from worker_statuses if available)
    workers_involved = list(active_session.get('worker_statuses', {}).keys())
    if not workers_involved:
        workers_involved = ['Stool', 'Gomer', 'Mona', 'Gus']  # Default team

    return {
        'project_name': active_session.get('project_name', 'Unknown Project'),
        'tasks_completed': active_session.get('tasks_completed', 0),
        'tasks_total': active_session.get('tasks_total', 0),
        'key_decisions': key_decisions,
        'requirements': [req.get('directive', req) if isinstance(req, dict) else req for req in requirements],
        'codebase_insights': active_session.get('codebase_insights', {}),
        'outcome': active_session.get('outcome', 'Session ended normally'),
        'duration_minutes': duration_minutes,
        'workers_involved': workers_involved,
    }


def clear_all_memories(user_id: int):
    """Clear all session memories for a user (for testing/reset)."""
    memory_file = get_memory_file(user_id)
    if memory_file.exists():
        memory_file.unlink()


def get_memory_stats(user_id: int) -> Dict[str, Any]:
    """Get statistics about user's session memory.

    Returns:
        Dict with stats like total sessions, total tasks, most worked project
    """
    history = load_session_history(user_id)

    if not history:
        return {
            'total_sessions': 0,
            'total_tasks_completed': 0,
            'projects_worked_on': 0,
        }

    total_tasks = sum(s.get('tasks_completed', 0) for s in history)
    projects = set(s.get('project_name', 'Unknown') for s in history)

    # Find most worked project
    project_counts = {}
    for s in history:
        proj = s.get('project_name', 'Unknown')
        project_counts[proj] = project_counts.get(proj, 0) + 1

    most_worked = max(project_counts.items(), key=lambda x: x[1])[0] if project_counts else None

    return {
        'total_sessions': len(history),
        'total_tasks_completed': total_tasks,
        'projects_worked_on': len(projects),
        'most_worked_project': most_worked,
    }
