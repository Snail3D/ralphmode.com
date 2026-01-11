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


# ============================================================================
# HR-006: Memory Fade System
# ============================================================================
# Let non-critical things fade over time gracefully.
# Critical memories (requirements, key decisions) stay fresh.
# Non-critical memories (old observations, minor details) fade.


def calculate_memory_relevance(memory_item: Dict[str, Any], current_time: datetime = None) -> float:
    """Calculate relevance score for a memory item (0.0 = faded, 1.0 = fresh).

    HR-006: Memory Fade System scores memories based on:
    - Age (older = lower score)
    - Importance type (requirements > observations)
    - Task completion status

    Args:
        memory_item: Session summary dict or worker memory dict
        current_time: Reference time (defaults to now)

    Returns:
        Relevance score between 0.0 and 1.0
    """
    if current_time is None:
        current_time = datetime.now()

    # Base score starts at 1.0 (fully relevant)
    score = 1.0

    # Age decay: newer memories are more relevant
    timestamp_str = memory_item.get('timestamp', '')
    if timestamp_str:
        try:
            memory_time = datetime.fromisoformat(timestamp_str)
            age_days = (current_time - memory_time).days

            # Decay curve:
            # 0-7 days: 100% relevance
            # 7-30 days: linear decay to 70%
            # 30-90 days: linear decay to 40%
            # 90+ days: linear decay to 20% floor
            if age_days <= 7:
                age_factor = 1.0
            elif age_days <= 30:
                age_factor = 1.0 - ((age_days - 7) / 23) * 0.3  # 100% → 70%
            elif age_days <= 90:
                age_factor = 0.7 - ((age_days - 30) / 60) * 0.3  # 70% → 40%
            else:
                age_factor = max(0.2, 0.4 - ((age_days - 90) / 180) * 0.2)  # 40% → 20% floor

            score *= age_factor
        except (ValueError, TypeError):
            # If timestamp parsing fails, treat as moderately old
            score *= 0.5

    # Importance boost: critical memory types get higher scores
    memory_type = memory_item.get('type', '').lower()

    if memory_type in ['requirement', 'key_decision', 'ceo_feedback']:
        # Critical memories: boost by 20%
        score *= 1.2
    elif memory_type in ['learning', 'suggestion']:
        # Important memories: no change
        score *= 1.0
    elif memory_type in ['observation', 'issue']:
        # Normal memories: slight penalty
        score *= 0.9

    # Task completion boost: completed tasks are more memorable
    if memory_item.get('tasks_completed', 0) > 0:
        completion_rate = memory_item.get('tasks_completed', 0) / max(1, memory_item.get('tasks_total', 1))
        if completion_rate >= 0.8:
            score *= 1.1  # High completion = more memorable

    # Cap at 1.0
    return min(1.0, score)


def apply_memory_fade(memories: List[Dict[str, Any]], relevance_threshold: float = 0.3) -> List[Dict[str, Any]]:
    """Filter memories by relevance, letting low-relevance items fade away.

    HR-006: Memory Fade System removes memories that have faded below threshold.

    Args:
        memories: List of memory items (sessions or worker memories)
        relevance_threshold: Minimum relevance score to keep (default 0.3)

    Returns:
        Filtered list of memories above threshold, sorted by relevance
    """
    current_time = datetime.now()

    # Calculate relevance for each memory
    scored_memories = []
    for mem in memories:
        relevance = calculate_memory_relevance(mem, current_time)
        if relevance >= relevance_threshold:
            # Add relevance score to memory for sorting
            mem_with_score = mem.copy()
            mem_with_score['_relevance'] = relevance
            scored_memories.append(mem_with_score)

    # Sort by relevance (highest first)
    scored_memories.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

    # Remove the _relevance score before returning
    return [
        {k: v for k, v in mem.items() if k != '_relevance'}
        for mem in scored_memories
    ]


def get_faded_session_context(user_id: int, max_sessions: int = 3, relevance_threshold: float = 0.3) -> str:
    """Build context string about previous sessions with memory fade applied.

    HR-006: Like get_previous_session_context, but only includes relevant memories.
    Old, non-critical sessions gracefully fade away.

    Args:
        user_id: Telegram user ID
        max_sessions: Maximum sessions to include (after fade)
        relevance_threshold: Minimum relevance to include

    Returns:
        Formatted string describing relevant previous sessions
    """
    history = load_session_history(user_id)

    if not history:
        return ""

    # Apply memory fade
    relevant_history = apply_memory_fade(history, relevance_threshold)

    if not relevant_history:
        return ""

    # Take most relevant sessions (already sorted by relevance)
    recent = relevant_history[:max_sessions]

    context_parts = ["\n--- Ralph's Memory of Previous Sessions (Relevant Only) ---"]

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

    context_parts.append("--- End Relevant Sessions (older non-critical sessions have faded) ---\n")

    return "\n".join(context_parts)


def cleanup_faded_memories(user_id: int, relevance_threshold: float = 0.2):
    """Permanently remove memories that have faded below threshold.

    HR-006: Memory Fade System cleanup - remove very old, irrelevant memories.
    This is a maintenance function to keep memory files from growing forever.

    Args:
        user_id: Telegram user ID
        relevance_threshold: Minimum relevance to keep (default 0.2 = very faded)
    """
    memory_file = get_memory_file(user_id)

    if not memory_file.exists():
        return

    history = load_session_history(user_id)

    # Apply fade filter with low threshold
    relevant_history = apply_memory_fade(history, relevance_threshold)

    # Always keep at least the 5 most recent sessions, regardless of relevance
    # (so we don't accidentally delete everything)
    if len(history) > 5:
        recent_sessions = history[:5]
        # Merge recent + relevant (remove duplicates)
        session_ids = {s.get('session_id') for s in recent_sessions}
        for s in relevant_history:
            if s.get('session_id') not in session_ids:
                recent_sessions.append(s)
                session_ids.add(s.get('session_id'))

        relevant_history = recent_sessions
    else:
        relevant_history = history  # Keep all if fewer than 5

    # Save cleaned history
    with open(memory_file, 'w') as f:
        json.dump({'sessions': relevant_history}, f, indent=2)

    removed_count = len(history) - len(relevant_history)
    if removed_count > 0:
        print(f"Memory fade cleanup: removed {removed_count} old sessions for user {user_id}")


def extract_context_from_user_reminder(user_text: str) -> Dict[str, Any]:
    """BM-003: Extract context from what user tells Ralph about previous work.

    When Ralph forgets and asks "what were we doing?", the user responds with
    a reminder. This function parses that reminder to extract key information
    that Ralph can use to restore context.

    Args:
        user_text: The user's response reminding Ralph about previous work

    Returns:
        Dict containing extracted context:
        {
            'project_name': str or None,
            'tasks_mentioned': List[str],
            'requirements': List[str],
            'technologies': List[str],
            'current_status': str or None,
            'next_steps': List[str],
            'raw_reminder': str  # Original text
        }
    """
    # Normalize text
    text_lower = user_text.lower()

    context = {
        'project_name': None,
        'tasks_mentioned': [],
        'requirements': [],
        'technologies': [],
        'current_status': None,
        'next_steps': [],
        'raw_reminder': user_text
    }

    # Extract project name patterns
    project_patterns = [
        'working on ',
        'building ',
        'project called ',
        'project named ',
        'developing ',
        'creating ',
        'making ',
    ]

    for pattern in project_patterns:
        if pattern in text_lower:
            idx = text_lower.index(pattern) + len(pattern)
            # Extract next few words as potential project name
            rest = user_text[idx:].split()
            if rest:
                # Take up to 4 words as project name
                potential_name = ' '.join(rest[:4]).rstrip('.,!?;:')
                if len(potential_name) > 2:
                    context['project_name'] = potential_name
                    break

    # Extract task mentions (action verbs + objects)
    task_patterns = [
        ('add', 'adding'),
        ('build', 'building'),
        ('create', 'creating'),
        ('implement', 'implementing'),
        ('fix', 'fixing'),
        ('update', 'updating'),
        ('improve', 'improving'),
        ('refactor', 'refactoring'),
        ('deploy', 'deploying'),
        ('test', 'testing'),
        ('integrate', 'integrating'),
        ('optimize', 'optimizing'),
    ]

    for base, gerund in task_patterns:
        if base in text_lower or gerund in text_lower:
            # Find the phrase around this verb
            for word in [base, gerund]:
                if word in text_lower:
                    idx = text_lower.index(word)
                    # Get 5 words after the verb
                    after_verb = user_text[idx:].split()[:6]
                    task = ' '.join(after_verb).rstrip('.,!?;:')
                    if len(task) > 3 and task not in context['tasks_mentioned']:
                        context['tasks_mentioned'].append(task)

    # Extract technology/framework mentions
    tech_keywords = [
        'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
        'node', 'express', 'django', 'flask', 'fastapi',
        'postgres', 'mysql', 'mongodb', 'redis',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'api', 'rest', 'graphql', 'websocket',
        'telegram', 'bot', 'cli', 'frontend', 'backend',
        'database', 'authentication', 'auth',
    ]

    for tech in tech_keywords:
        if tech in text_lower:
            context['technologies'].append(tech)

    # Extract requirement phrases (should/need/want/must + verb)
    requirement_indicators = [
        'need to ', 'needs to ', 'should ', 'must ', 'have to ',
        'want to ', 'wanted to ', 'trying to ', 'supposed to ',
        'going to ', 'planning to ',
    ]

    for indicator in requirement_indicators:
        if indicator in text_lower:
            idx = text_lower.index(indicator)
            # Get the requirement phrase
            after_indicator = user_text[idx:].split()[:8]
            requirement = ' '.join(after_indicator).rstrip('.,!?;:')
            if len(requirement) > 5 and requirement not in context['requirements']:
                context['requirements'].append(requirement)

    # Extract status mentions
    status_keywords = [
        ('almost done', 'Almost done'),
        ('half done', 'Half way done'),
        ('just started', 'Just started'),
        ('in progress', 'In progress'),
        ('working on', 'Currently working on'),
        ('stuck on', 'Stuck on'),
        ('finished', 'Finished'),
        ('completed', 'Completed'),
    ]

    for keyword, status_label in status_keywords:
        if keyword in text_lower:
            context['current_status'] = status_label
            break

    # Extract next steps (then/next/after)
    next_step_indicators = [
        'then ', 'next ', 'after that ', 'after this ',
        'then we ', 'next we ', 'afterwards ',
    ]

    for indicator in next_step_indicators:
        if indicator in text_lower:
            idx = text_lower.index(indicator)
            after_indicator = user_text[idx:].split()[:8]
            next_step = ' '.join(after_indicator).rstrip('.,!?;:')
            if len(next_step) > 5 and next_step not in context['next_steps']:
                context['next_steps'].append(next_step)

    return context


def format_extracted_context_for_ralph(context: Dict[str, Any]) -> str:
    """Format extracted context into a readable summary for Ralph's AI prompt.

    Args:
        context: Context dict from extract_context_from_user_reminder

    Returns:
        Formatted string that can be included in Ralph's system prompt
    """
    if not context or context.get('raw_reminder', '') == '':
        return ""

    parts = ["--- User Reminder About Previous Work ---"]
    parts.append(f"User said: \"{context['raw_reminder']}\"")
    parts.append("")

    if context.get('project_name'):
        parts.append(f"Project: {context['project_name']}")

    if context.get('tasks_mentioned'):
        parts.append(f"Tasks mentioned: {', '.join(context['tasks_mentioned'][:3])}")

    if context.get('requirements'):
        parts.append(f"Requirements: {', '.join(context['requirements'][:3])}")

    if context.get('technologies'):
        parts.append(f"Technologies: {', '.join(context['technologies'][:5])}")

    if context.get('current_status'):
        parts.append(f"Status: {context['current_status']}")

    if context.get('next_steps'):
        parts.append(f"Next steps: {', '.join(context['next_steps'][:2])}")

    parts.append("--- End User Reminder ---")
    parts.append("")

    return "\n".join(parts)
