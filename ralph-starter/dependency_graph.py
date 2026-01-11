#!/usr/bin/env python3
"""
Dependency Graph - Task Dependency Mapping

Maps dependencies between tasks to enable intelligent ordering.
Some tasks must be completed before others (e.g., database schema before queries).

Returns a DAG (Directed Acyclic Graph) and detects circular dependencies.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque


def extract_explicit_dependencies(task: Dict) -> Set[str]:
    """
    Extract explicit task dependencies from task description and acceptance criteria.

    Looks for patterns like:
    - "Requires TC-001"
    - "Depends on SEC-005"
    - "After RM-003"
    - "Blocked by API-001"

    Args:
        task: Task dictionary

    Returns:
        Set of task IDs this task depends on
    """
    dependencies = set()

    # Combine text sources
    text_parts = [
        task.get("description", ""),
        task.get("title", ""),
    ]

    if "acceptance_criteria" in task:
        text_parts.extend(task["acceptance_criteria"])

    combined_text = " ".join(text_parts)

    # Pattern for task ID references (e.g., TC-001, RM-034, SEC-005, AUTH-001)
    # Allows 2-5 uppercase letters, then hyphen, then 1-3 digits
    task_id_pattern = r'\b([A-Z]{2,5}-\d{1,3})\b'

    # Dependency keywords with flexible task ID pattern
    dependency_keywords = [
        r'requires?\s+([A-Z]{2,5}-\d{1,3})',
        r'depends?\s+on\s+([A-Z]{2,5}-\d{1,3})',
        r'after\s+([A-Z]{2,5}-\d{1,3})',
        r'blocked\s+by\s+([A-Z]{2,5}-\d{1,3})',
        r'needs\s+([A-Z]{2,5}-\d{1,3})',
        r'following\s+([A-Z]{2,5}-\d{1,3})',
    ]

    for pattern in dependency_keywords:
        for match in re.finditer(pattern, combined_text, re.IGNORECASE):
            dep_id = match.group(1).upper()
            dependencies.add(dep_id)

    # Also look for standalone task IDs after dependency keywords
    # This catches "Requires AUTH-001." or "Requires: AUTH-001" or after periods
    general_pattern = r'(?:require|depends?|after|blocked|needs?|following)[\s:]+([A-Z]{2,5}-\d{1,3})'
    for match in re.finditer(general_pattern, combined_text, re.IGNORECASE):
        dep_id = match.group(1).upper()
        dependencies.add(dep_id)

    return dependencies


def infer_implicit_dependencies(task: Dict, all_tasks: List[Dict]) -> Set[str]:
    """
    Infer implicit dependencies based on task patterns.

    Common patterns:
    - Database schema tasks must come before query tasks
    - Model/handler tasks must come before API endpoint tasks
    - Authentication must come before authorization
    - Setup tasks must come before usage tasks

    Args:
        task: Current task
        all_tasks: All tasks in the PRD

    Returns:
        Set of task IDs this task implicitly depends on
    """
    dependencies = set()
    task_id = task.get("id", "")
    task_title = task.get("title", "").lower()
    task_desc = task.get("description", "").lower()

    # Build lookup map
    task_map = {t.get("id"): t for t in all_tasks}

    # Pattern 1: Database schema before queries
    if any(keyword in task_title or keyword in task_desc
           for keyword in ["query", "select", "insert", "update", "delete"]):
        # Depends on schema/model tasks
        for other_task in all_tasks:
            other_id = other_task.get("id", "")
            other_title = other_task.get("title", "").lower()
            other_desc = other_task.get("description", "").lower()

            if other_id != task_id and any(
                keyword in other_title or keyword in other_desc
                for keyword in ["schema", "model", "table", "database setup"]
            ):
                dependencies.add(other_id)

    # Pattern 2: API endpoints depend on handlers
    if "endpoint" in task_title or "api" in task_title:
        for other_task in all_tasks:
            other_id = other_task.get("id", "")
            other_title = other_task.get("title", "").lower()

            if other_id != task_id and ("handler" in other_title or "service" in other_title):
                # Check if they touch similar domains
                task_files = set(task.get("files_likely_modified", []))
                other_files = set(other_task.get("files_likely_modified", []))

                # If they share files, endpoint likely depends on handler
                if task_files & other_files:
                    dependencies.add(other_id)

    # Pattern 3: Authorization depends on authentication
    if "authorization" in task_title or "permission" in task_title or "rbac" in task_title:
        for other_task in all_tasks:
            other_id = other_task.get("id", "")
            other_title = other_task.get("title", "").lower()

            if other_id != task_id and ("authentication" in other_title or "login" in other_title):
                dependencies.add(other_id)

    # Pattern 4: File-based dependencies (same file, earlier task comes first)
    # If two tasks modify the same file and one creates it, the other depends on it
    task_files = set(task.get("files_likely_modified", []))
    for other_task in all_tasks:
        other_id = other_task.get("id", "")
        other_title = other_task.get("title", "").lower()
        other_files = set(other_task.get("files_likely_modified", []))

        if other_id != task_id and task_files & other_files:
            # If other task is about "creating" or "adding" a file, depend on it
            if any(keyword in other_title for keyword in ["create", "add", "setup", "initialize"]):
                dependencies.add(other_id)

    # Pattern 5: Testing depends on implementation
    if "test" in task_title and not "test" in task_desc.split()[0]:
        # Find the implementation task for this test
        test_subject = task_title.replace("test", "").replace("testing", "").strip()

        for other_task in all_tasks:
            other_id = other_task.get("id", "")
            other_title = other_task.get("title", "").lower()

            if other_id != task_id and test_subject in other_title and "test" not in other_title:
                dependencies.add(other_id)

    # Pattern 6: Sequential task IDs in same category often have dependencies
    # E.g., TC-001 -> TC-002 -> TC-003
    if "-" in task_id:
        prefix, num_str = task_id.rsplit("-", 1)
        try:
            task_num = int(num_str)
            # Check if previous task in sequence exists
            if task_num > 1:
                prev_id = f"{prefix}-{(task_num - 1):03d}"
                if prev_id in task_map:
                    prev_task = task_map[prev_id]
                    # Only add dependency if they're in same category
                    if prev_task.get("category") == task.get("category"):
                        dependencies.add(prev_id)
        except ValueError:
            pass

    return dependencies


def build_dependency_graph(tasks: List[Dict]) -> Dict[str, Set[str]]:
    """
    Build a dependency graph for all tasks.

    Returns a dictionary mapping task_id -> set of task_ids it depends on.

    Args:
        tasks: List of task dictionaries

    Returns:
        Dict mapping task_id to set of dependencies
    """
    graph = {}

    for task in tasks:
        task_id = task.get("id", "")
        if not task_id:
            continue

        # Combine explicit and implicit dependencies
        explicit_deps = extract_explicit_dependencies(task)
        implicit_deps = infer_implicit_dependencies(task, tasks)

        all_deps = explicit_deps | implicit_deps

        # Only keep dependencies that actually exist in our task list
        valid_task_ids = {t.get("id") for t in tasks if t.get("id")}
        all_deps = all_deps & valid_task_ids

        # Don't allow self-dependencies
        all_deps.discard(task_id)

        graph[task_id] = all_deps

    return graph


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Detect circular dependencies in the graph using DFS.

    Args:
        graph: Dependency graph (task_id -> dependencies)

    Returns:
        List of cycles found (each cycle is a list of task IDs)
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: str) -> bool:
        """DFS helper that returns True if cycle found"""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle!
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    # Check all nodes
    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def topological_sort(graph: Dict[str, Set[str]]) -> Optional[List[str]]:
    """
    Perform topological sort on the dependency graph.

    Returns tasks in order such that all dependencies come before dependents.
    Uses Kahn's algorithm.

    Args:
        graph: Dependency graph (task_id -> dependencies)

    Returns:
        List of task IDs in dependency order, or None if cycles exist
    """
    # Check for cycles first
    cycles = detect_cycles(graph)
    if cycles:
        return None

    # Build reverse graph (who depends on me?)
    reverse_graph = defaultdict(set)
    in_degree = defaultdict(int)

    # Initialize all nodes with 0 in-degree
    for node in graph:
        in_degree[node] = 0

    # Build reverse graph and calculate in-degrees
    for node, deps in graph.items():
        for dep in deps:
            reverse_graph[dep].add(node)
            in_degree[node] += 1

    # Find all nodes with no dependencies
    queue = deque([node for node in graph if in_degree[node] == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)

        # Reduce in-degree for all dependents
        for dependent in reverse_graph[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # If we didn't process all nodes, there's a cycle
    if len(result) != len(graph):
        return None

    return result


def visualize_dependencies(graph: Dict[str, Set[str]], task_map: Dict[str, Dict]) -> str:
    """
    Create a text visualization of the dependency graph.

    Args:
        graph: Dependency graph
        task_map: Map of task_id -> task dict

    Returns:
        Formatted string showing dependencies
    """
    lines = []
    lines.append("=== Task Dependency Graph ===\n")

    # Sort by task ID
    sorted_tasks = sorted(graph.keys())

    for task_id in sorted_tasks:
        deps = graph[task_id]
        task_title = task_map.get(task_id, {}).get("title", "Unknown")

        lines.append(f"{task_id}: {task_title}")

        if deps:
            lines.append(f"  Depends on: {', '.join(sorted(deps))}")
            for dep_id in sorted(deps):
                dep_title = task_map.get(dep_id, {}).get("title", "Unknown")
                lines.append(f"    - {dep_id}: {dep_title}")
        else:
            lines.append("  No dependencies (can start immediately)")

        lines.append("")

    return "\n".join(lines)


def test_dependency_graph():
    """Test dependency graph with sample tasks"""

    sample_tasks = [
        {
            "id": "DB-001",
            "title": "Create Database Schema",
            "description": "Set up initial database tables",
            "category": "Database"
        },
        {
            "id": "DB-002",
            "title": "Add User Queries",
            "description": "Create SQL queries for user operations",
            "category": "Database"
        },
        {
            "id": "AUTH-001",
            "title": "Implement Authentication",
            "description": "Add login and session management",
            "category": "Security"
        },
        {
            "id": "AUTH-002",
            "title": "Add Authorization (RBAC)",
            "description": "Implement role-based access control",
            "category": "Security"
        },
        {
            "id": "API-001",
            "title": "Create User Endpoint",
            "description": "Add POST /api/users endpoint. Requires AUTH-001",
            "category": "API"
        },
    ]

    print("=== Dependency Graph Test ===\n")

    # Debug: Test explicit dependency extraction
    api_task = [t for t in sample_tasks if t["id"] == "API-001"][0]
    explicit_deps = extract_explicit_dependencies(api_task)
    print(f"DEBUG: API-001 explicit deps: {explicit_deps}")
    print(f"DEBUG: API-001 description: '{api_task['description']}'")

    # Build graph
    graph = build_dependency_graph(sample_tasks)

    print("Dependency graph built:")
    task_map = {t["id"]: t for t in sample_tasks}

    for task_id, deps in sorted(graph.items()):
        print(f"  {task_id}: depends on {deps if deps else 'nothing'}")

    # Check for cycles
    cycles = detect_cycles(graph)
    if cycles:
        print(f"\n❌ Detected {len(cycles)} cycle(s):")
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}")
    else:
        print("\n✅ No cycles detected (valid DAG)")

    # Topological sort
    sorted_tasks = topological_sort(graph)
    if sorted_tasks:
        print("\n✅ Topological sort successful:")
        print(f"  Execution order: {' -> '.join(sorted_tasks)}")
    else:
        print("\n❌ Cannot perform topological sort (cycles exist)")

    # Visualize
    print("\n" + visualize_dependencies(graph, task_map))

    # Verify expected dependencies
    assert "AUTH-001" in graph["API-001"], "API-001 should depend on AUTH-001 (explicit)"
    assert "AUTH-001" in graph["AUTH-002"], "AUTH-002 should depend on AUTH-001 (implicit)"
    assert "DB-001" in graph["DB-002"], "DB-002 should depend on DB-001 (sequential)"

    print("✅ All tests passed!")


if __name__ == "__main__":
    test_dependency_graph()
