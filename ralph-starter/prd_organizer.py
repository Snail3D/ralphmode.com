#!/usr/bin/env python3
"""
PRD Organizer - Task Clustering and Organization

Intelligently organizes PRD tasks by clustering related work together.
This maximizes context retention and minimizes Claude Code context-switching.
"""

import re
from typing import List, Dict, Set


def extract_file_hints(task: Dict) -> Set[str]:
    """
    Extract likely file paths from a task description.

    Analyzes:
    - files_likely_modified field (explicit)
    - Task title and description (implicit)
    - Common patterns like "in ralph_bot.py", "modify the handler"

    Args:
        task: Task dictionary with id, title, description, files_likely_modified, etc.

    Returns:
        Set of file paths that this task will likely touch
    """
    files = set()

    # 1. Explicit files_likely_modified field
    if "files_likely_modified" in task:
        for file_pattern in task["files_likely_modified"]:
            files.add(file_pattern)

    # 2. Parse title and description for file mentions
    text = f"{task.get('title', '')} {task.get('description', '')}"

    # Pattern: "in <filename>"
    in_file_pattern = r'\bin\s+([a-zA-Z0-9_]+\.py)'
    for match in re.finditer(in_file_pattern, text, re.IGNORECASE):
        files.add(match.group(1))

    # Pattern: "<filename>.py"
    file_pattern = r'\b([a-zA-Z0-9_]+\.py)\b'
    for match in re.finditer(file_pattern, text):
        files.add(match.group(1))

    # Pattern: "ralph_bot", "scene_manager" (common module names)
    module_pattern = r'\b(ralph_bot|scene_manager|admin_handler|weather_service|deploy_manager|api_server|sanitizer|user_manager|session_manager|context_handler|translation_engine|atmosphere_detector|character_data|config|database|logging_config|content_filter|rate_limiter|task_embeddings|dependency_graph|prd_organizer)\b'
    for match in re.finditer(module_pattern, text, re.IGNORECASE):
        # Convert module name to likely file name
        module_name = match.group(1).lower()
        files.add(f"{module_name}.py")

    # 3. Parse acceptance_criteria for file mentions
    if "acceptance_criteria" in task:
        for criterion in task["acceptance_criteria"]:
            # Look for file patterns in criteria
            for match in re.finditer(file_pattern, criterion):
                files.add(match.group(1))

            # Look for "in X" patterns
            for match in re.finditer(in_file_pattern, criterion, re.IGNORECASE):
                files.add(match.group(1))

    # 4. Infer from task category
    category = task.get("category", "")

    # Security tasks likely touch sanitizer, api_server
    if "Security" in category:
        files.add("sanitizer.py")
        files.add("api_server.py")

    # Admin command tasks touch admin_handler
    if "Admin" in category:
        files.add("admin_handler.py")

    # Scene setting tasks touch scene_manager
    if "Scene" in category:
        files.add("scene_manager.py")

    # Voice-related tasks touch ralph_bot (main handler)
    if "Voice" in category or "Overhear" in category:
        files.add("ralph_bot.py")

    # PRD Organization tasks touch prd_organizer
    if "PRD Organization" in category:
        files.add("prd_organizer.py")

    # Specialist tasks touch ralph_bot (character definitions)
    if "Specialist" in category:
        files.add("ralph_bot.py")

    # Team Dynamics touch ralph_bot
    if "Team Dynamics" in category or "Core Quality" in category:
        files.add("ralph_bot.py")

    # Good News tasks likely need dedicated module
    if "Good News" in category:
        files.add("good_news.py")
        files.add("ralph_bot.py")

    # 5. Infer from task ID prefix
    task_id = task.get("id", "")

    if task_id.startswith("RM-"):
        # Ralph Mode core tasks - usually ralph_bot
        files.add("ralph_bot.py")
    elif task_id.startswith("SEC-"):
        # Security tasks
        files.add("sanitizer.py")
        files.add("api_server.py")
    elif task_id.startswith("AC-"):
        # Admin command tasks
        files.add("admin_handler.py")
    elif task_id.startswith("SS-"):
        # Scene setting tasks
        files.add("scene_manager.py")
    elif task_id.startswith("VO-"):
        # Voice-only tasks
        files.add("ralph_bot.py")
    elif task_id.startswith("TC-"):
        # Task clustering tasks
        files.add("prd_organizer.py")
    elif task_id.startswith("FB-"):
        # Feedback tasks
        files.add("feedback_handler.py")
        files.add("ralph_bot.py")

    return files


def test_extract_file_hints():
    """Test the file hint extraction with sample tasks"""

    # Test 1: Explicit files_likely_modified
    task1 = {
        "id": "RM-001",
        "title": "Ralph Dyslexia Misspellings",
        "description": "Create ralph_misspell() function",
        "files_likely_modified": ["ralph_bot.py"],
        "category": "Ralph Authenticity"
    }
    result1 = extract_file_hints(task1)
    print(f"Test 1 - Explicit files: {result1}")
    assert "ralph_bot.py" in result1

    # Test 2: Implicit from description
    task2 = {
        "id": "TC-001",
        "title": "Task File Extraction",
        "description": "Extract likely files from task descriptions. Analyze task titles in prd_organizer.py",
        "category": "PRD Organization",
        "files_likely_modified": ["prd_organizer.py"]
    }
    result2 = extract_file_hints(task2)
    print(f"Test 2 - Implicit from description: {result2}")
    assert "prd_organizer.py" in result2

    # Test 3: From acceptance criteria
    task3 = {
        "id": "AC-001",
        "title": "Admin Commands",
        "description": "Add admin commands",
        "category": "Admin Commands",
        "acceptance_criteria": [
            "Create command handler in admin_handler.py",
            "Update ralph_bot.py to call handler"
        ]
    }
    result3 = extract_file_hints(task3)
    print(f"Test 3 - From criteria: {result3}")
    assert "admin_handler.py" in result3
    assert "ralph_bot.py" in result3

    # Test 4: Category inference
    task4 = {
        "id": "SEC-001",
        "title": "SQL Injection Prevention",
        "description": "Prevent SQL injection",
        "category": "Security - OWASP Top 10"
    }
    result4 = extract_file_hints(task4)
    print(f"Test 4 - Category inference: {result4}")
    assert "sanitizer.py" in result4
    assert "api_server.py" in result4

    # Test 5: No clear hints
    task5 = {
        "id": "TEST-001",
        "title": "Some Generic Task",
        "description": "Do something",
        "category": "Unknown"
    }
    result5 = extract_file_hints(task5)
    print(f"Test 5 - No clear hints: {result5}")
    # Should return empty or minimal set

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    print("=== PRD Organizer - File Hint Extraction ===\n")
    test_extract_file_hints()
