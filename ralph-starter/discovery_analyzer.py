#!/usr/bin/env python3
"""
PD-003: Enhanced Codebase Sweep

Analyzes project context files (CLAUDE.md, README, package.json, .env.example, etc.)
to build a comprehensive understanding of the codebase for better discovery.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class CodebaseSweeper:
    """Sweeps codebase for project context and metadata."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.context = {}

    def sweep(self) -> Dict[str, Any]:
        """
        Perform comprehensive codebase sweep.

        Returns:
            Dict containing discovered project context
        """
        logger.info("Starting enhanced codebase sweep...")

        self.context = {
            "project_docs": self._analyze_documentation(),
            "config_files": self._analyze_config_files(),
            "environment": self._analyze_environment(),
            "structure": self._analyze_structure(),
            "tech_stack": self._infer_tech_stack(),
        }

        logger.info(f"Codebase sweep complete. Found {len(self.context)} context categories.")
        return self.context

    def _analyze_documentation(self) -> Dict[str, Any]:
        """Analyze README, CLAUDE.md, and other docs."""
        docs = {}

        # Check for common documentation files
        doc_files = [
            "README.md", "README.txt", "README",
            "CLAUDE.md",
            "CONTRIBUTING.md",
            "ARCHITECTURE.md",
            "DESIGN.md",
        ]

        for doc_file in doc_files:
            file_path = self.root_path / doc_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        docs[doc_file] = {
                            "exists": True,
                            "size": len(content),
                            "lines": len(content.split('\n')),
                            "preview": content[:500] if len(content) > 500 else content,
                        }
                        logger.info(f"Found documentation: {doc_file} ({len(content)} chars)")
                except Exception as e:
                    logger.warning(f"Error reading {doc_file}: {e}")
                    docs[doc_file] = {"exists": True, "error": str(e)}
            else:
                docs[doc_file] = {"exists": False}

        return docs

    def _analyze_config_files(self) -> Dict[str, Any]:
        """Analyze configuration files (package.json, requirements.txt, etc.)."""
        configs = {}

        # Python configs
        if (self.root_path / "requirements.txt").exists():
            configs["requirements.txt"] = self._parse_requirements()

        if (self.root_path / "pyproject.toml").exists():
            configs["pyproject.toml"] = {"exists": True, "type": "python-poetry"}

        if (self.root_path / "setup.py").exists():
            configs["setup.py"] = {"exists": True, "type": "python-setuptools"}

        # JavaScript/Node configs
        if (self.root_path / "package.json").exists():
            configs["package.json"] = self._parse_package_json()

        if (self.root_path / "tsconfig.json").exists():
            configs["tsconfig.json"] = {"exists": True, "type": "typescript"}

        # Docker
        if (self.root_path / "Dockerfile").exists():
            configs["Dockerfile"] = {"exists": True, "type": "docker"}

        if (self.root_path / "docker-compose.yml").exists():
            configs["docker-compose.yml"] = {"exists": True, "type": "docker-compose"}

        return configs

    def _analyze_environment(self) -> Dict[str, Any]:
        """Analyze .env.example and environment configuration."""
        env = {}

        env_files = [".env.example", ".env.template", ".env.sample"]

        for env_file in env_files:
            file_path = self.root_path / env_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Parse environment variables
                    env_vars = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key = line.split('=')[0].strip()
                            env_vars.append(key)

                    env[env_file] = {
                        "exists": True,
                        "variables": env_vars,
                        "count": len(env_vars),
                    }
                    logger.info(f"Found {len(env_vars)} env vars in {env_file}")
                except Exception as e:
                    logger.warning(f"Error reading {env_file}: {e}")
                    env[env_file] = {"exists": True, "error": str(e)}

        return env

    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze folder structure to understand project organization."""
        structure = {
            "directories": [],
            "python_files": 0,
            "javascript_files": 0,
            "test_files": 0,
        }

        # Count files and directories
        for item in self.root_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                structure["directories"].append(item.name)

        # Count file types
        for file_path in self.root_path.rglob("*"):
            if file_path.is_file():
                if file_path.suffix == ".py":
                    structure["python_files"] += 1
                    if "test" in file_path.name.lower():
                        structure["test_files"] += 1
                elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                    structure["javascript_files"] += 1

        logger.info(f"Project structure: {len(structure['directories'])} dirs, "
                   f"{structure['python_files']} .py files")

        return structure

    def _infer_tech_stack(self) -> Dict[str, bool]:
        """Infer technology stack from files and configs."""
        stack = {
            "python": False,
            "javascript": False,
            "typescript": False,
            "react": False,
            "django": False,
            "flask": False,
            "fastapi": False,
            "telegram_bot": False,
            "docker": False,
        }

        # Check for Python
        if (self.root_path / "requirements.txt").exists() or \
           (self.root_path / "setup.py").exists() or \
           (self.root_path / "pyproject.toml").exists():
            stack["python"] = True

        # Check for JS/TS
        if (self.root_path / "package.json").exists():
            stack["javascript"] = True

            # Check package.json for frameworks
            package_json_path = self.root_path / "package.json"
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                    deps = {**package_data.get("dependencies", {}),
                           **package_data.get("devDependencies", {})}

                    if "react" in deps:
                        stack["react"] = True
                    if "typescript" in deps or (self.root_path / "tsconfig.json").exists():
                        stack["typescript"] = True
            except Exception as e:
                logger.warning(f"Error parsing package.json: {e}")

        # Check for Python frameworks in requirements
        if (self.root_path / "requirements.txt").exists():
            try:
                with open(self.root_path / "requirements.txt", 'r') as f:
                    requirements = f.read().lower()
                    if "django" in requirements:
                        stack["django"] = True
                    if "flask" in requirements:
                        stack["flask"] = True
                    if "fastapi" in requirements:
                        stack["fastapi"] = True
                    if "python-telegram-bot" in requirements or "telegram" in requirements:
                        stack["telegram_bot"] = True
            except Exception as e:
                logger.warning(f"Error parsing requirements.txt: {e}")

        # Check for Docker
        if (self.root_path / "Dockerfile").exists():
            stack["docker"] = True

        return stack

    def _parse_requirements(self) -> Dict[str, Any]:
        """Parse requirements.txt for dependencies."""
        try:
            with open(self.root_path / "requirements.txt", 'r') as f:
                lines = f.readlines()

            dependencies = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before ==, >=, etc.)
                    pkg_name = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    dependencies.append(pkg_name)

            return {
                "exists": True,
                "dependencies": dependencies,
                "count": len(dependencies),
            }
        except Exception as e:
            logger.warning(f"Error parsing requirements.txt: {e}")
            return {"exists": True, "error": str(e)}

    def _parse_package_json(self) -> Dict[str, Any]:
        """Parse package.json for project info."""
        try:
            with open(self.root_path / "package.json", 'r') as f:
                data = json.load(f)

            return {
                "exists": True,
                "name": data.get("name"),
                "version": data.get("version"),
                "description": data.get("description"),
                "dependencies": list(data.get("dependencies", {}).keys()),
                "devDependencies": list(data.get("devDependencies", {}).keys()),
            }
        except Exception as e:
            logger.warning(f"Error parsing package.json: {e}")
            return {"exists": True, "error": str(e)}

    def get_summary(self) -> str:
        """Generate human-readable summary of the sweep."""
        if not self.context:
            return "No sweep data available. Run sweep() first."

        summary_lines = ["=== Enhanced Codebase Sweep Summary ===\n"]

        # Documentation
        docs = self.context.get("project_docs", {})
        found_docs = [name for name, data in docs.items() if data.get("exists")]
        if found_docs:
            summary_lines.append(f"Documentation: {', '.join(found_docs)}")

        # Tech stack
        tech_stack = self.context.get("tech_stack", {})
        active_tech = [tech for tech, active in tech_stack.items() if active]
        if active_tech:
            summary_lines.append(f"Tech Stack: {', '.join(active_tech)}")

        # Environment
        env = self.context.get("environment", {})
        total_env_vars = sum(data.get("count", 0) for data in env.values() if isinstance(data, dict))
        if total_env_vars:
            summary_lines.append(f"Environment Variables: {total_env_vars} defined")

        # Structure
        structure = self.context.get("structure", {})
        summary_lines.append(f"Structure: {structure.get('python_files', 0)} Python files, "
                           f"{structure.get('javascript_files', 0)} JS/TS files, "
                           f"{structure.get('test_files', 0)} test files")

        return "\n".join(summary_lines)


def sweep_codebase(root_path: str = ".") -> Dict[str, Any]:
    """
    Convenience function to perform codebase sweep.

    Args:
        root_path: Root directory of the project

    Returns:
        Dict containing project context
    """
    sweeper = CodebaseSweeper(root_path)
    return sweeper.sweep()


def get_project_context(root_path: str = ".") -> Dict[str, Any]:
    """
    Get comprehensive project context from codebase sweep.

    Args:
        root_path: Root directory of the project

    Returns:
        Dict containing project context and metadata
    """
    sweeper = CodebaseSweeper(root_path)
    context = sweeper.sweep()

    return {
        "context": context,
        "summary": sweeper.get_summary(),
        "timestamp": str(datetime.now()),
    }


# CLI interface for testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    root = sys.argv[1] if len(sys.argv) > 1 else "."

    print(f"Sweeping codebase at: {root}\n")

    sweeper = CodebaseSweeper(root)
    context = sweeper.sweep()

    print(sweeper.get_summary())
    print("\nFull context:")
    print(json.dumps(context, indent=2))
