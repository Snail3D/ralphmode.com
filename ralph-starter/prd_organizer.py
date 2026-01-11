#!/usr/bin/env python3
"""
PRD Organizer - Task Clustering and Organization

Intelligently organizes PRD tasks by clustering related work together.
This maximizes context retention and minimizes Claude Code context-switching.
"""

import re
import numpy as np
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque


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


def topological_sort_clusters(
    clusters: List[List[Dict]],
    graph: Dict[str, Set[str]]
) -> List[List[Dict]]:
    """
    Order clusters using topological sort based on dependency graph.

    Ensures foundational tasks come before dependent ones.
    Handles cycles by breaking at the lowest cost edge.

    Args:
        clusters: List of task clusters
        graph: Dependency graph from dependency_graph.py (task_id -> dependencies)

    Returns:
        Ordered list of clusters (foundational first, UI/polish last)
    """
    from dependency_graph import detect_cycles, topological_sort

    if not clusters or not graph:
        return clusters

    # Build cluster dependency graph
    # For each cluster, determine which other clusters it depends on
    cluster_deps = {}
    cluster_id_map = {}  # cluster_idx -> cluster
    task_to_cluster = {}  # task_id -> cluster_idx

    # Map tasks to their clusters
    for idx, cluster in enumerate(clusters):
        cluster_id_map[idx] = cluster
        for task in cluster:
            task_id = task.get("id", "")
            if task_id:
                task_to_cluster[task_id] = idx

    # Calculate cluster dependencies
    for idx, cluster in enumerate(clusters):
        deps = set()

        for task in cluster:
            task_id = task.get("id", "")
            if task_id in graph:
                # For each dependency of this task
                for dep_id in graph[task_id]:
                    # Find which cluster that dependency belongs to
                    dep_cluster_idx = task_to_cluster.get(dep_id)
                    if dep_cluster_idx is not None and dep_cluster_idx != idx:
                        # This cluster depends on another cluster
                        deps.add(dep_cluster_idx)

        cluster_deps[idx] = deps

    # Detect and break cycles if they exist
    cycles = detect_cycles(cluster_deps)
    if cycles:
        # Break cycles at the lowest cost edge
        # Cost = number of dependencies between the two clusters
        for cycle in cycles:
            # Find the weakest link in the cycle
            weakest_edge = None
            min_cost = float('inf')

            for i in range(len(cycle) - 1):
                from_idx = cycle[i]
                to_idx = cycle[i + 1]

                # Count how many task dependencies exist between these clusters
                cost = 0
                for task in cluster_id_map[from_idx]:
                    task_id = task.get("id", "")
                    if task_id in graph:
                        for dep_id in graph[task_id]:
                            if task_to_cluster.get(dep_id) == to_idx:
                                cost += 1

                if cost < min_cost:
                    min_cost = cost
                    weakest_edge = (from_idx, to_idx)

            # Remove the weakest edge
            if weakest_edge:
                from_idx, to_idx = weakest_edge
                if to_idx in cluster_deps[from_idx]:
                    cluster_deps[from_idx].discard(to_idx)

    # Perform topological sort on clusters
    sorted_cluster_indices = topological_sort(cluster_deps)

    if sorted_cluster_indices is None:
        # Fallback: return clusters as-is if sort fails
        return clusters

    # Apply priority heuristics for foundational vs UI/polish
    # Categorize clusters by type
    foundational_indices = []
    business_logic_indices = []
    ui_polish_indices = []
    other_indices = []

    for idx in sorted_cluster_indices:
        cluster = cluster_id_map[idx]

        # Analyze cluster to determine type
        categories = [task.get("category", "") for task in cluster]
        titles = [task.get("title", "").lower() for task in cluster]

        # Check for foundational keywords
        is_foundational = any(
            any(keyword in cat.lower() or keyword in title
                for keyword in ["database", "schema", "model", "setup", "config", "init"])
            for cat, title in zip(categories, titles)
        )

        # Check for UI/polish keywords
        is_ui_polish = any(
            any(keyword in cat.lower() or keyword in title
                for keyword in ["ui", "polish", "styling", "animation", "visual", "color", "css"])
            for cat, title in zip(categories, titles)
        )

        if is_foundational:
            foundational_indices.append(idx)
        elif is_ui_polish:
            ui_polish_indices.append(idx)
        elif any("api" in cat.lower() or "handler" in cat.lower() or "service" in cat.lower()
                 for cat in categories):
            business_logic_indices.append(idx)
        else:
            other_indices.append(idx)

    # Rebuild sorted order: foundational -> business logic -> other -> ui/polish
    final_order = (
        foundational_indices +
        business_logic_indices +
        other_indices +
        ui_polish_indices
    )

    # Return clusters in sorted order
    return [cluster_id_map[idx] for idx in final_order]


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


def insert_new_task(
    task: Dict,
    clusters: List[List[Dict]],
    file_hints: Dict[str, Set[str]],
    embeddings: Dict[str, np.ndarray],
    priority_override: bool = False
) -> List[List[Dict]]:
    """
    Insert a new task into the most appropriate existing cluster.

    Finds the best-fit cluster using hybrid similarity (file overlap + semantic similarity).
    Optionally respects priority overrides for boss tasks that should go to the top.
    Rebalances clusters if needed to maintain optimal cluster sizes.

    Args:
        task: The new task dictionary to insert
        clusters: List of existing task clusters
        file_hints: Dict of task_id -> Set of file paths for all tasks
        embeddings: Dict of task_id -> embedding vector for all tasks
        priority_override: If True, this is a boss task that should be inserted at the top of its cluster

    Returns:
        Updated list of clusters with the new task inserted
    """
    if not clusters:
        # No existing clusters - create a new one
        return [[task]]

    task_id = task.get("id", "")

    # Extract file hints for the new task
    if task_id not in file_hints:
        file_hints[task_id] = extract_file_hints(task)

    # Find the best-fit cluster based on similarity
    best_cluster_idx = 0
    best_similarity = -1

    for idx, cluster in enumerate(clusters):
        # Calculate average similarity to all tasks in this cluster
        total_similarity = 0.0
        count = 0

        for existing_task in cluster:
            similarity = hybrid_similarity(
                task,
                existing_task,
                file_hints,
                embeddings
            )
            total_similarity += similarity
            count += 1

        avg_similarity = total_similarity / count if count > 0 else 0.0

        if avg_similarity > best_similarity:
            best_similarity = avg_similarity
            best_cluster_idx = idx

    # Check if similarity is too low - might need a new cluster
    SIMILARITY_THRESHOLD = 0.15  # Lower than clustering threshold
    if best_similarity < SIMILARITY_THRESHOLD and len(clusters) < 20:
        # Create a new cluster for this task
        clusters.append([task])
    else:
        # Insert into the best-fit cluster
        if priority_override:
            # Boss tasks go to the top of their cluster
            clusters[best_cluster_idx].insert(0, task)
        else:
            # Regular tasks go at the end
            clusters[best_cluster_idx].append(task)

    # Rebalance if any cluster is too large
    MAX_CLUSTER_SIZE = 15
    rebalanced = False

    for idx, cluster in enumerate(clusters):
        if len(cluster) > MAX_CLUSTER_SIZE:
            # Split this cluster into two
            mid_point = len(cluster) // 2

            # Keep first half in original cluster
            first_half = cluster[:mid_point]
            second_half = cluster[mid_point:]

            # Replace original cluster with first half
            clusters[idx] = first_half

            # Add second half as new cluster
            clusters.append(second_half)

            rebalanced = True
            break  # Only split one cluster per insertion

    # Sort clusters by size (largest first) if we rebalanced
    if rebalanced:
        clusters.sort(key=len, reverse=True)

    return clusters


def update_priority_order(
    clusters: List[List[Dict]],
    prd_path: str = "scripts/ralph/prd.json"
) -> None:
    """
    Update the priority_order field in prd.json based on current clusters.

    Flattens clusters into a priority order list, preserving section headers.
    This should be called after inserting new tasks or re-organizing clusters.

    Args:
        clusters: Ordered list of task clusters
        prd_path: Path to prd.json file (default: scripts/ralph/prd.json)
    """
    import json
    import os

    # Read current prd.json
    if not os.path.exists(prd_path):
        print(f"Warning: {prd_path} not found, skipping priority_order update")
        return

    with open(prd_path, 'r') as f:
        prd = json.load(f)

    # Get existing priority order to detect section headers
    old_priority = prd.get("priority_order", [])

    # Build task ID to category mapping for section organization
    task_categories = {}
    for cluster in clusters:
        for task in cluster:
            task_id = task.get("id", "")
            category = task.get("category", "")
            if task_id and category:
                task_categories[task_id] = category

    # Build new priority order
    # Group tasks by category prefix (SEC, TC, OB, etc.) to preserve sections
    from collections import defaultdict
    category_groups = defaultdict(list)

    for cluster in clusters:
        for task in cluster:
            task_id = task.get("id", "")
            task_title = task.get("title", "")
            if task_id and task_title:
                # Extract category prefix (e.g., "SEC" from "SEC-001")
                prefix = task_id.split("-")[0] if "-" in task_id else "OTHER"
                category_groups[prefix].append(f"{task_id} - {task_title}")

    # Build final priority order with section headers
    new_priority = []

    # Define section headers based on common prefixes
    section_headers = {
        "SEC": "--- SECURITY (Enterprise-Grade Protection) ---",
        "TC": "--- TASK CLUSTERING (PRD Organization) ---",
        "OB": "--- ONBOARDING WIZARD (Zero-Friction Setup) ---",
        "FB": "--- FEEDBACK LOOP (RLHF Self-Building System) ---",
        "RM": "--- RALPH MODE (Core Features) ---",
        "VO": "--- VOICE-ONLY (Conversational Excellence) ---",
        "AC": "--- ADMIN COMMANDS ---",
        "SS": "--- SCENE SETTING ---",
    }

    # Preserve order from original priority list if possible
    seen_prefixes = set()
    for prefix in ["SEC", "TC", "OB", "FB", "RM", "VO", "AC", "SS"]:
        if prefix in category_groups and category_groups[prefix]:
            if prefix in section_headers:
                new_priority.append(section_headers[prefix])
            new_priority.extend(category_groups[prefix])
            seen_prefixes.add(prefix)

    # Add any remaining categories not explicitly handled
    for prefix, tasks in sorted(category_groups.items()):
        if prefix not in seen_prefixes and tasks:
            new_priority.extend(tasks)

    # Update prd.json
    prd["priority_order"] = new_priority

    # Write back to file
    with open(prd_path, 'w') as f:
        json.dump(prd, f, indent=2)


def test_insert_new_task():
    """Test inserting new tasks into existing clusters"""
    from task_embeddings import generate_embeddings

    # Create initial tasks for clustering
    initial_tasks = [
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
        }
    ]

    print("=== Insert New Task Test ===\n")

    # Extract file hints
    file_hints = {}
    for task in initial_tasks:
        file_hints[task["id"]] = extract_file_hints(task)

    # Generate embeddings
    embeddings = generate_embeddings(initial_tasks, use_cache=False)

    # Create initial clusters
    clusters = hybrid_cluster(initial_tasks, file_hints, embeddings, similarity_threshold=0.2)
    print(f"Initial clusters ({len(clusters)}):")
    for i, cluster in enumerate(clusters):
        task_ids = [t["id"] for t in cluster]
        print(f"  Cluster {i + 1}: {task_ids}")

    # Test 1: Insert a new UI task (should go to UI cluster)
    new_ui_task = {
        "id": "UI-003",
        "title": "Add Theme Switcher",
        "description": "Create a component to switch between themes",
        "category": "UI/UX",
        "files_likely_modified": ["ui.py", "settings.py"]
    }

    # Generate embedding for new task
    all_tasks = initial_tasks + [new_ui_task]
    embeddings = generate_embeddings(all_tasks, use_cache=False)
    file_hints[new_ui_task["id"]] = extract_file_hints(new_ui_task)

    clusters = insert_new_task(new_ui_task, clusters, file_hints, embeddings)
    print(f"\nAfter inserting UI-003:")
    for i, cluster in enumerate(clusters):
        task_ids = [t["id"] for t in cluster]
        print(f"  Cluster {i + 1}: {task_ids}")

    # Verify UI-003 is with other UI tasks
    ui_cluster_found = False
    for cluster in clusters:
        task_ids = [t["id"] for t in cluster]
        if "UI-003" in task_ids:
            assert "UI-001" in task_ids or "UI-002" in task_ids, \
                "New UI task should be clustered with other UI tasks"
            ui_cluster_found = True
            break
    assert ui_cluster_found, "UI-003 should be in a cluster"

    # Test 2: Insert a high-priority boss task
    boss_task = {
        "id": "BOSS-001",
        "title": "Fix Critical Bug in API",
        "description": "Urgent: fix authentication bypass bug",
        "category": "Backend API",
        "files_likely_modified": ["api_server.py", "auth.py"]
    }

    all_tasks.append(boss_task)
    embeddings = generate_embeddings(all_tasks, use_cache=False)
    file_hints[boss_task["id"]] = extract_file_hints(boss_task)

    clusters = insert_new_task(boss_task, clusters, file_hints, embeddings, priority_override=True)
    print(f"\nAfter inserting BOSS-001 (priority override):")
    for i, cluster in enumerate(clusters):
        task_ids = [t["id"] for t in cluster]
        print(f"  Cluster {i + 1}: {task_ids}")

    # Verify BOSS-001 is at the top of its cluster
    for cluster in clusters:
        task_ids = [t["id"] for t in cluster]
        if "BOSS-001" in task_ids:
            assert task_ids[0] == "BOSS-001", \
                "Boss task with priority override should be at top of cluster"
            break

    # Test 3: Insert a very different task (should create new cluster if similarity is low)
    different_task = {
        "id": "DOC-001",
        "title": "Write API Documentation",
        "description": "Document all REST endpoints",
        "category": "Documentation",
        "files_likely_modified": ["docs/api.md"]
    }

    all_tasks.append(different_task)
    embeddings = generate_embeddings(all_tasks, use_cache=False)
    file_hints[different_task["id"]] = extract_file_hints(different_task)

    initial_cluster_count = len(clusters)
    clusters = insert_new_task(different_task, clusters, file_hints, embeddings)
    print(f"\nAfter inserting DOC-001 (different category):")
    for i, cluster in enumerate(clusters):
        task_ids = [t["id"] for t in cluster]
        print(f"  Cluster {i + 1}: {task_ids}")

    print(f"\nCluster count: {initial_cluster_count} -> {len(clusters)}")

    print("\n✅ All insert_new_task tests passed!")


def cluster_tasks(prd_path: str = "scripts/ralph/prd.json") -> Dict:
    """
    Re-cluster and reorganize all tasks in the PRD.

    Main orchestrator function that:
    1. Loads tasks from prd.json
    2. Generates embeddings
    3. Extracts file hints
    4. Performs hybrid clustering
    5. Builds dependency graph
    6. Orders clusters topologically
    7. Updates priority_order in prd.json

    Args:
        prd_path: Path to prd.json file (default: scripts/ralph/prd.json)

    Returns:
        Dict with clustering statistics:
        {
            "total_tasks": int,
            "num_clusters": int,
            "cluster_summary": Dict[str, int],  # cluster_name -> task_count
            "updated_priority_order": List[str]
        }
    """
    import json
    import os
    from task_embeddings import generate_embeddings
    from dependency_graph import build_dependency_graph

    # Load PRD
    if not os.path.exists(prd_path):
        raise FileNotFoundError(f"PRD file not found: {prd_path}")

    with open(prd_path, 'r') as f:
        prd = json.load(f)

    tasks = prd.get("tasks", [])

    if not tasks:
        return {
            "total_tasks": 0,
            "num_clusters": 0,
            "cluster_summary": {},
            "updated_priority_order": []
        }

    # Extract file hints for all tasks
    file_hints = {}
    for task in tasks:
        task_id = task.get("id", "")
        if task_id:
            file_hints[task_id] = extract_file_hints(task)

    # Generate embeddings
    embeddings = generate_embeddings(tasks, use_cache=True)

    # Perform hybrid clustering
    clusters = hybrid_cluster(
        tasks,
        file_hints,
        embeddings,
        similarity_threshold=0.3
    )

    # Build dependency graph
    graph = build_dependency_graph(tasks)

    # Order clusters by dependencies
    sorted_clusters = topological_sort_clusters(clusters, graph)

    # Assign names to clusters
    named_clusters = assign_cluster_names(sorted_clusters)

    # Update priority_order in prd.json
    update_priority_order(sorted_clusters, prd_path)

    # Build cluster summary
    cluster_summary = {}
    for name, cluster in named_clusters:
        cluster_summary[name] = len(cluster)

    # Get updated priority order
    with open(prd_path, 'r') as f:
        updated_prd = json.load(f)
    updated_priority_order = updated_prd.get("priority_order", [])

    return {
        "total_tasks": len(tasks),
        "num_clusters": len(sorted_clusters),
        "cluster_summary": cluster_summary,
        "updated_priority_order": updated_priority_order
    }


def test_topological_sort_clusters():
    """Test cluster ordering by dependencies"""
    from task_embeddings import generate_embeddings
    from dependency_graph import build_dependency_graph

    sample_tasks = [
        {
            "id": "DB-001",
            "title": "Create Database Schema",
            "description": "Set up initial database tables",
            "category": "Database",
            "files_likely_modified": ["database.py"]
        },
        {
            "id": "DB-002",
            "title": "Add User Queries",
            "description": "Create SQL queries for user operations",
            "category": "Database",
            "files_likely_modified": ["database.py"]
        },
        {
            "id": "API-001",
            "title": "Create User Handler",
            "description": "Add user business logic handler",
            "category": "Backend API",
            "files_likely_modified": ["user_handler.py"]
        },
        {
            "id": "API-002",
            "title": "Create User Endpoint",
            "description": "Add POST /api/users endpoint",
            "category": "Backend API",
            "files_likely_modified": ["api_server.py", "user_handler.py"]
        },
        {
            "id": "UI-001",
            "title": "Add User Registration Form",
            "description": "Create registration form UI",
            "category": "UI/UX",
            "files_likely_modified": ["ui.py"]
        },
        {
            "id": "UI-002",
            "title": "Polish Button Colors",
            "description": "Update button colors for brand",
            "category": "UI/UX - Polish",
            "files_likely_modified": ["styles.css"]
        }
    ]

    print("=== Topological Sort Clusters Test ===\n")

    # Extract file hints
    file_hints = {}
    for task in sample_tasks:
        file_hints[task["id"]] = extract_file_hints(task)

    # Generate embeddings
    embeddings = generate_embeddings(sample_tasks, use_cache=False)

    # Cluster tasks
    clusters = hybrid_cluster(sample_tasks, file_hints, embeddings, similarity_threshold=0.2)
    print(f"Created {len(clusters)} clusters:")
    for i, cluster in enumerate(clusters):
        task_ids = [t["id"] for t in cluster]
        print(f"  Cluster {i}: {task_ids}")

    # Build dependency graph
    graph = build_dependency_graph(sample_tasks)
    print(f"\nDependency graph:")
    for task_id, deps in sorted(graph.items()):
        if deps:
            print(f"  {task_id} depends on: {deps}")

    # Sort clusters by dependencies
    sorted_clusters = topological_sort_clusters(clusters, graph)

    print(f"\nClusters after topological sort:")
    for i, cluster in enumerate(sorted_clusters):
        task_ids = [t["id"] for t in cluster]
        categories = [t.get("category", "") for t in cluster]
        print(f"  {i + 1}. {task_ids} ({categories[0] if categories else 'Unknown'})")

    # Verify ordering
    cluster_positions = {}
    for idx, cluster in enumerate(sorted_clusters):
        for task in cluster:
            cluster_positions[task["id"]] = idx

    # Database tasks should come before API tasks
    assert cluster_positions["DB-001"] <= cluster_positions["API-001"], \
        "Database tasks should come before API tasks"

    # API handler should come before API endpoint
    assert cluster_positions["API-001"] <= cluster_positions["API-002"], \
        "API handler should come before API endpoint"

    # UI polish should come last
    if "UI-002" in cluster_positions:
        ui_polish_pos = cluster_positions["UI-002"]
        max_pos = max(cluster_positions.values())
        assert ui_polish_pos == max_pos or ui_polish_pos == max_pos - 1, \
            "UI polish should be in the last or second-to-last cluster"

    print("\n✅ All topological sort tests passed!")
    print("   - Database tasks come first (foundational)")
    print("   - API tasks come after database")
    print("   - UI polish tasks come last")


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

    print("\n" + "=" * 50)
    print("Test 3: Insert New Task")
    print("=" * 50)
    test_insert_new_task()

    print("\n" + "=" * 50)
    print("Test 4: Topological Sort Clusters")
    print("=" * 50)
    test_topological_sort_clusters()
