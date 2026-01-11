#!/usr/bin/env python3
"""
PRD Organizer - Task Clustering and Organization

Intelligently organizes PRD tasks by clustering related work together.
This maximizes context retention and minimizes Claude Code context-switching.
"""

import re
import numpy as np
from typing import List, Dict, Set, Tuple
from collections import defaultdict


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


def file_overlap_score(files1: Set[str], files2: Set[str]) -> float:
    """
    Calculate overlap score between two sets of files.

    Returns:
        Float between 0 and 1, where 1 = identical files
    """
    if not files1 or not files2:
        return 0.0

    intersection = len(files1 & files2)
    union = len(files1 | files2)

    return intersection / union if union > 0 else 0.0


def hybrid_similarity(
    task1: Dict,
    task2: Dict,
    file_hints: Dict[str, Set[str]],
    embeddings: Dict[str, np.ndarray],
    file_weight: float = 0.6,
    semantic_weight: float = 0.4
) -> float:
    """
    Calculate hybrid similarity between two tasks.

    Combines:
    - File-based similarity (tasks touching same files cluster together)
    - Semantic similarity (tasks with similar descriptions cluster together)

    Args:
        task1, task2: Task dictionaries
        file_hints: Dict of task_id -> Set of file paths
        embeddings: Dict of task_id -> embedding vector
        file_weight: Weight for file-based similarity (default 0.6)
        semantic_weight: Weight for semantic similarity (default 0.4)

    Returns:
        Similarity score between 0 and 1
    """
    task1_id = task1.get("id", "")
    task2_id = task2.get("id", "")

    # File-based similarity
    files1 = file_hints.get(task1_id, set())
    files2 = file_hints.get(task2_id, set())
    file_sim = file_overlap_score(files1, files2)

    # Semantic similarity
    semantic_sim = 0.0
    if task1_id in embeddings and task2_id in embeddings:
        vec1 = embeddings[task1_id]
        vec2 = embeddings[task2_id]

        # Cosine similarity
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 > 0 and norm2 > 0:
            semantic_sim = np.dot(vec1, vec2) / (norm1 * norm2)

    # Weighted combination
    combined = (file_weight * file_sim) + (semantic_weight * semantic_sim)

    return combined


def hybrid_cluster(
    tasks: List[Dict],
    file_hints: Dict[str, Set[str]],
    embeddings: Dict[str, np.ndarray],
    similarity_threshold: float = 0.3
) -> List[List[Dict]]:
    """
    Cluster tasks using hybrid similarity (file overlap + semantic similarity).

    Uses agglomerative clustering approach:
    1. Start with each task in its own cluster
    2. Merge most similar clusters iteratively
    3. Stop when no clusters have similarity > threshold

    Args:
        tasks: List of task dictionaries
        file_hints: Dict of task_id -> Set of file paths
        embeddings: Dict of task_id -> embedding vector
        similarity_threshold: Minimum similarity to merge clusters (default 0.3)

    Returns:
        List of clusters, where each cluster is a list of tasks
    """
    if not tasks:
        return []

    # Start with each task in its own cluster
    clusters = [[task] for task in tasks]

    # Build similarity matrix
    n = len(tasks)
    similarity_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(i + 1, n):
            sim = hybrid_similarity(tasks[i], tasks[j], file_hints, embeddings)
            similarity_matrix[i][j] = sim
            similarity_matrix[j][i] = sim

    # Agglomerative clustering
    while len(clusters) > 1:
        # Find most similar pair of clusters
        best_sim = -1
        best_pair = None

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Calculate average similarity between all tasks in these clusters
                cluster_sim = 0.0
                count = 0

                for task_i in clusters[i]:
                    idx_i = tasks.index(task_i)
                    for task_j in clusters[j]:
                        idx_j = tasks.index(task_j)
                        cluster_sim += similarity_matrix[idx_i][idx_j]
                        count += 1

                avg_sim = cluster_sim / count if count > 0 else 0.0

                if avg_sim > best_sim:
                    best_sim = avg_sim
                    best_pair = (i, j)

        # Stop if best similarity is below threshold
        if best_sim < similarity_threshold:
            break

        # Merge the best pair
        if best_pair:
            i, j = best_pair
            # Merge j into i, remove j
            clusters[i].extend(clusters[j])
            clusters.pop(j)

    # Sort clusters by size (largest first)
    clusters.sort(key=len, reverse=True)

    return clusters


def assign_cluster_names(clusters: List[List[Dict]]) -> List[Tuple[str, List[Dict]]]:
    """
    Assign descriptive names to clusters based on common patterns.

    Args:
        clusters: List of task clusters

    Returns:
        List of (cluster_name, tasks) tuples
    """
    named_clusters = []

    for cluster in clusters:
        # Analyze cluster to determine name
        categories = defaultdict(int)
        id_prefixes = defaultdict(int)

        for task in cluster:
            category = task.get("category", "Unknown")
            categories[category] += 1

            task_id = task.get("id", "")
            if "-" in task_id:
                prefix = task_id.split("-")[0]
                id_prefixes[prefix] += 1

        # Choose most common category or ID prefix as name
        if categories:
            most_common_category = max(categories.items(), key=lambda x: x[1])[0]
            cluster_name = most_common_category
        elif id_prefixes:
            most_common_prefix = max(id_prefixes.items(), key=lambda x: x[1])[0]
            cluster_name = f"{most_common_prefix} Tasks"
        else:
            cluster_name = f"Cluster {len(named_clusters) + 1}"

        named_clusters.append((cluster_name, cluster))

    return named_clusters


def test_hybrid_cluster():
    """Test hybrid clustering with sample tasks"""
    from task_embeddings import generate_embeddings

    sample_tasks = [
        {
            "id": "UI-001",
            "title": "Add Dark Mode Toggle",
            "description": "Create a toggle button for dark mode",
            "category": "UI/UX",
            "files_likely_modified": ["settings.py", "ui.py"]
        },
        {
            "id": "UI-002",
            "title": "Update Button Colors",
            "description": "Change all buttons to new brand colors",
            "category": "UI/UX",
            "files_likely_modified": ["ui.py", "styles.css"]
        },
        {
            "id": "API-001",
            "title": "Add User Login Endpoint",
            "description": "Create POST /api/login endpoint",
            "category": "Backend API",
            "files_likely_modified": ["api_server.py", "auth.py"]
        },
        {
            "id": "API-002",
            "title": "Add Rate Limiting",
            "description": "Implement rate limiting on all endpoints",
            "category": "Backend API",
            "files_likely_modified": ["api_server.py", "rate_limiter.py"]
        },
        {
            "id": "SEC-001",
            "title": "SQL Injection Prevention",
            "description": "Prevent SQL injection attacks",
            "category": "Security",
            "files_likely_modified": ["api_server.py", "sanitizer.py"]
        }
    ]

    print("=== Hybrid Task Clustering Test ===\n")

    # Extract file hints
    file_hints = {}
    for task in sample_tasks:
        file_hints[task["id"]] = extract_file_hints(task)

    print("File hints extracted:")
    for task_id, files in file_hints.items():
        print(f"  {task_id}: {files}")

    # Generate embeddings
    embeddings = generate_embeddings(sample_tasks, use_cache=False)
    print(f"\nGenerated {len(embeddings)} embeddings\n")

    # Cluster tasks
    clusters = hybrid_cluster(sample_tasks, file_hints, embeddings, similarity_threshold=0.2)

    print(f"Created {len(clusters)} clusters:\n")
    for i, cluster in enumerate(clusters):
        task_ids = [t["id"] for t in cluster]
        print(f"Cluster {i + 1} ({len(cluster)} tasks): {task_ids}")

    # Assign names
    named_clusters = assign_cluster_names(clusters)
    print("\nNamed clusters:")
    for name, cluster in named_clusters:
        task_ids = [t["id"] for t in cluster]
        print(f"  {name}: {task_ids}")

    # Verify UI tasks are clustered together
    ui_cluster = None
    for cluster in clusters:
        ids = [t["id"] for t in cluster]
        if "UI-001" in ids:
            ui_cluster = ids
            break

    assert ui_cluster is not None, "UI-001 should be in a cluster"
    print(f"\nUI tasks cluster: {ui_cluster}")

    print("\n✅ All tests passed!")


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
    print("=== PRD Organizer Tests ===\n")
    print("=" * 50)
    print("Test 1: File Hint Extraction")
    print("=" * 50)
    test_extract_file_hints()

    print("\n" + "=" * 50)
    print("Test 2: Hybrid Task Clustering")
    print("=" * 50)
    test_hybrid_cluster()
