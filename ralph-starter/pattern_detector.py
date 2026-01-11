import os
from collections import defaultdict

def detect_pattern(root_path):
    """
    Detects project patterns (MVC, Monorepo, Microservices) from folder structure.
    Returns a list of detected patterns.
    """
    if not os.path.isdir(root_path):
        raise ValueError("Invalid directory path")

    detected = []
    structure = _get_structure(root_path)
    top_level_dirs = [d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))]
    
    # 1. MVC Detection
    mvc_indicators = {'models', 'views', 'controllers', 'app', 'templates', 'static'}
    if mvc_indicators.intersection(top_level_dirs):
        detected.append("MVC")

    # 2. Monorepo Detection
    # Heuristic: Multiple subdirectories containing project metadata files
    project_files = ['package.json', 'setup.py', 'pyproject.toml', 'pom.xml', 'build.gradle', 'go.mod']
    sub_projects = 0
    
    for root, dirs, files in os.walk(root_path):
        # Limit depth to avoid scanning node_modules too deeply if present
        depth = root[len(root_path):].count(os.sep)
        if depth > 3:
            continue
            
        if any(f in files for f in project_files):
            sub_projects += 1

    # If we find multiple project definition files, it's likely a monorepo
    if sub_projects > 1:
        detected.append("Monorepo")

    # 3. Microservices Detection
    # Heuristic: Distinct 'services' folder or multiple top-level app-like folders
    service_keywords = {'services', 'microservices', 'api'}
    if service_keywords.intersection(top_level_dirs):
        detected.append("Microservices")
    elif "Monorepo" in detected and sub_projects > 3:
        # Distinguish from simple monorepo by scale/separation
        detected.append("Microservices")

    return detected if detected else ["Unknown"]

def _get_structure(path):
    """Helper to visualize structure (optional for debugging, kept minimal)."""
    return None