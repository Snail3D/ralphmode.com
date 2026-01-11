#!/usr/bin/env python3
"""
PD-003: Enhanced Codebase Sweep

Analyzes project context files (CLAUDE.md, README, package.json, .env.example, etc.)
to build a comprehensive understanding of the codebase for better discovery.
"""

import os
import json
import logging
from datetime import datetime
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

    def _infer_tech_stack(self) -> Dict[str, Any]:
        """
        Infer comprehensive technology stack from files and configs.

        Detects:
        - Programming languages
        - Web frameworks
        - Databases
        - ORMs
        - Testing frameworks
        - Deployment tools
        - Frontend libraries
        - Build tools

        Returns:
            Dict with technology categories and detected tools
        """
        stack = {
            # Core languages
            "languages": {
                "python": False,
                "javascript": False,
                "typescript": False,
                "go": False,
                "rust": False,
                "ruby": False,
                "php": False,
            },

            # Python frameworks
            "python_frameworks": {
                "django": False,
                "flask": False,
                "fastapi": False,
                "tornado": False,
                "sanic": False,
                "bottle": False,
            },

            # JavaScript frameworks
            "js_frameworks": {
                "react": False,
                "vue": False,
                "angular": False,
                "next": False,
                "astro": False,
                "svelte": False,
                "express": False,
                "nest": False,
            },

            # Databases
            "databases": {
                "postgresql": False,
                "mysql": False,
                "mariadb": False,
                "sqlite": False,
                "mongodb": False,
                "redis": False,
                "elasticsearch": False,
                "dynamodb": False,
            },

            # ORMs/Database Tools
            "orm_tools": {
                "sqlalchemy": False,
                "django_orm": False,
                "prisma": False,
                "typeorm": False,
                "mongoose": False,
                "sequelize": False,
            },

            # Testing frameworks
            "testing": {
                "pytest": False,
                "unittest": False,
                "jest": False,
                "mocha": False,
                "vitest": False,
                "playwright": False,
                "cypress": False,
            },

            # Deployment/Infrastructure
            "infrastructure": {
                "docker": False,
                "kubernetes": False,
                "terraform": False,
                "ansible": False,
            },

            # Messaging/Queue systems
            "messaging": {
                "telegram_bot": False,
                "rabbitmq": False,
                "kafka": False,
                "celery": False,
            },

            # AI/ML libraries
            "ai_ml": {
                "anthropic": False,
                "openai": False,
                "groq": False,
                "ollama": False,
                "pytorch": False,
                "tensorflow": False,
                "transformers": False,
            },
        }

        # Check for Python
        if (self.root_path / "requirements.txt").exists() or \
           (self.root_path / "setup.py").exists() or \
           (self.root_path / "pyproject.toml").exists():
            stack["languages"]["python"] = True

        # Check for other languages
        if (self.root_path / "go.mod").exists():
            stack["languages"]["go"] = True
        if (self.root_path / "Cargo.toml").exists():
            stack["languages"]["rust"] = True
        if (self.root_path / "Gemfile").exists():
            stack["languages"]["ruby"] = True
        if (self.root_path / "composer.json").exists():
            stack["languages"]["php"] = True

        # Check for JS/TS
        if (self.root_path / "package.json").exists():
            stack["languages"]["javascript"] = True

            # Check package.json for frameworks and libraries
            package_json_path = self.root_path / "package.json"
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                    deps = {**package_data.get("dependencies", {}),
                           **package_data.get("devDependencies", {})}

                    # TypeScript
                    if "typescript" in deps or (self.root_path / "tsconfig.json").exists():
                        stack["languages"]["typescript"] = True

                    # JS Frameworks
                    if "react" in deps:
                        stack["js_frameworks"]["react"] = True
                    if "vue" in deps:
                        stack["js_frameworks"]["vue"] = True
                    if "@angular/core" in deps:
                        stack["js_frameworks"]["angular"] = True
                    if "next" in deps:
                        stack["js_frameworks"]["next"] = True
                    if "astro" in deps:
                        stack["js_frameworks"]["astro"] = True
                    if "svelte" in deps:
                        stack["js_frameworks"]["svelte"] = True
                    if "express" in deps:
                        stack["js_frameworks"]["express"] = True
                    if "@nestjs/core" in deps:
                        stack["js_frameworks"]["nest"] = True

                    # Databases (client libraries)
                    if "pg" in deps or "postgres" in deps:
                        stack["databases"]["postgresql"] = True
                    if "mysql" in deps or "mysql2" in deps:
                        stack["databases"]["mysql"] = True
                    if "mongodb" in deps:
                        stack["databases"]["mongodb"] = True
                    if "redis" in deps or "ioredis" in deps:
                        stack["databases"]["redis"] = True
                    if "@elastic/elasticsearch" in deps:
                        stack["databases"]["elasticsearch"] = True

                    # ORMs
                    if "prisma" in deps:
                        stack["orm_tools"]["prisma"] = True
                    if "typeorm" in deps:
                        stack["orm_tools"]["typeorm"] = True
                    if "mongoose" in deps:
                        stack["orm_tools"]["mongoose"] = True
                    if "sequelize" in deps:
                        stack["orm_tools"]["sequelize"] = True

                    # Testing
                    if "jest" in deps:
                        stack["testing"]["jest"] = True
                    if "mocha" in deps:
                        stack["testing"]["mocha"] = True
                    if "vitest" in deps:
                        stack["testing"]["vitest"] = True
                    if "playwright" in deps or "@playwright/test" in deps:
                        stack["testing"]["playwright"] = True
                    if "cypress" in deps:
                        stack["testing"]["cypress"] = True

            except Exception as e:
                logger.warning(f"Error parsing package.json: {e}")

        # Check for Python dependencies in requirements.txt
        if (self.root_path / "requirements.txt").exists():
            try:
                with open(self.root_path / "requirements.txt", 'r') as f:
                    requirements = f.read().lower()

                    # Python frameworks
                    if "django" in requirements:
                        stack["python_frameworks"]["django"] = True
                        stack["orm_tools"]["django_orm"] = True
                    if "flask" in requirements:
                        stack["python_frameworks"]["flask"] = True
                    if "fastapi" in requirements:
                        stack["python_frameworks"]["fastapi"] = True
                    if "tornado" in requirements:
                        stack["python_frameworks"]["tornado"] = True
                    if "sanic" in requirements:
                        stack["python_frameworks"]["sanic"] = True
                    if "bottle" in requirements:
                        stack["python_frameworks"]["bottle"] = True

                    # Databases
                    if "psycopg" in requirements or "postgresql" in requirements:
                        stack["databases"]["postgresql"] = True
                    if "mysqlclient" in requirements or "pymysql" in requirements:
                        stack["databases"]["mysql"] = True
                    if "sqlite" in requirements:
                        stack["databases"]["sqlite"] = True
                    if "pymongo" in requirements or "motor" in requirements:
                        stack["databases"]["mongodb"] = True
                    if "redis" in requirements:
                        stack["databases"]["redis"] = True
                    if "elasticsearch" in requirements:
                        stack["databases"]["elasticsearch"] = True

                    # ORMs
                    if "sqlalchemy" in requirements:
                        stack["orm_tools"]["sqlalchemy"] = True

                    # Testing
                    if "pytest" in requirements:
                        stack["testing"]["pytest"] = True
                    if "unittest" in requirements:
                        stack["testing"]["unittest"] = True
                    if "playwright" in requirements:
                        stack["testing"]["playwright"] = True

                    # Messaging
                    if "python-telegram-bot" in requirements or "telegram" in requirements:
                        stack["messaging"]["telegram_bot"] = True
                    if "pika" in requirements or "rabbitmq" in requirements:
                        stack["messaging"]["rabbitmq"] = True
                    if "kafka" in requirements:
                        stack["messaging"]["kafka"] = True
                    if "celery" in requirements:
                        stack["messaging"]["celery"] = True

                    # AI/ML
                    if "anthropic" in requirements:
                        stack["ai_ml"]["anthropic"] = True
                    if "openai" in requirements:
                        stack["ai_ml"]["openai"] = True
                    if "groq" in requirements:
                        stack["ai_ml"]["groq"] = True
                    if "ollama" in requirements:
                        stack["ai_ml"]["ollama"] = True
                    if "torch" in requirements or "pytorch" in requirements:
                        stack["ai_ml"]["pytorch"] = True
                    if "tensorflow" in requirements:
                        stack["ai_ml"]["tensorflow"] = True
                    if "transformers" in requirements:
                        stack["ai_ml"]["transformers"] = True

            except Exception as e:
                logger.warning(f"Error parsing requirements.txt: {e}")

        # Check for Docker/K8s
        if (self.root_path / "Dockerfile").exists():
            stack["infrastructure"]["docker"] = True
        if (self.root_path / "docker-compose.yml").exists() or \
           (self.root_path / "docker-compose.yaml").exists():
            stack["infrastructure"]["docker"] = True
        if list(self.root_path.glob("*.tf")):  # Terraform files
            stack["infrastructure"]["terraform"] = True
        if list(self.root_path.glob("*.yml")) and \
           any("kind:" in f.read_text() for f in self.root_path.glob("*.yml") if f.is_file() and f.stat().st_size < 1000000):
            # Detect Kubernetes yamls by presence of "kind:" field
            stack["infrastructure"]["kubernetes"] = True
        if (self.root_path / "ansible.cfg").exists() or list(self.root_path.glob("playbook*.yml")):
            stack["infrastructure"]["ansible"] = True

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

        # Tech stack - handle new nested structure
        tech_stack = self.context.get("tech_stack", {})

        # Languages
        if "languages" in tech_stack:
            active_langs = [lang for lang, active in tech_stack["languages"].items() if active]
            if active_langs:
                summary_lines.append(f"Languages: {', '.join(active_langs)}")

        # Frameworks
        frameworks = []
        if "python_frameworks" in tech_stack:
            frameworks.extend([f for f, active in tech_stack["python_frameworks"].items() if active])
        if "js_frameworks" in tech_stack:
            frameworks.extend([f for f, active in tech_stack["js_frameworks"].items() if active])
        if frameworks:
            summary_lines.append(f"Frameworks: {', '.join(frameworks)}")

        # Databases
        if "databases" in tech_stack:
            active_dbs = [db for db, active in tech_stack["databases"].items() if active]
            if active_dbs:
                summary_lines.append(f"Databases: {', '.join(active_dbs)}")

        # ORMs
        if "orm_tools" in tech_stack:
            active_orms = [orm for orm, active in tech_stack["orm_tools"].items() if active]
            if active_orms:
                summary_lines.append(f"ORMs: {', '.join(active_orms)}")

        # Testing
        if "testing" in tech_stack:
            active_test = [test for test, active in tech_stack["testing"].items() if active]
            if active_test:
                summary_lines.append(f"Testing: {', '.join(active_test)}")

        # Infrastructure
        if "infrastructure" in tech_stack:
            active_infra = [infra for infra, active in tech_stack["infrastructure"].items() if active]
            if active_infra:
                summary_lines.append(f"Infrastructure: {', '.join(active_infra)}")

        # Messaging
        if "messaging" in tech_stack:
            active_msg = [msg for msg, active in tech_stack["messaging"].items() if active]
            if active_msg:
                summary_lines.append(f"Messaging: {', '.join(active_msg)}")

        # AI/ML
        if "ai_ml" in tech_stack:
            active_ai = [ai for ai, active in tech_stack["ai_ml"].items() if active]
            if active_ai:
                summary_lines.append(f"AI/ML: {', '.join(active_ai)}")

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
