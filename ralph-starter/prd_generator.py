#!/usr/bin/env python3
"""
PRD Template Generator for Ralph Mode

Generates starting PRD based on project type.
Pre-populated with common tasks for different project types.

RULE AWARENESS: This generator knows what it CANNOT touch.
See prd_manager.py for protected resources.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Import rule awareness system
try:
    from prd_manager import get_prd_rule_awareness
    RULE_AWARENESS_AVAILABLE = True
except ImportError:
    RULE_AWARENESS_AVAILABLE = False


class PRDGenerator:
    """Generates PRD templates for different project types."""

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the PRD generator.

        Args:
            project_root: Root directory of the project (for rule awareness)
        """
        self.logger = logging.getLogger(__name__)
        self.project_root = project_root

        # Initialize rule awareness
        if RULE_AWARENESS_AVAILABLE:
            self.rule_awareness = get_prd_rule_awareness(project_root)
            self.logger.info("Rule awareness system initialized")
        else:
            self.rule_awareness = None
            self.logger.warning("Rule awareness system not available")

    def get_project_types(self) -> List[Dict[str, str]]:
        """Get available project types with descriptions."""
        return [
            {
                "id": "telegram_bot",
                "name": "Telegram Bot",
                "description": "Interactive bot with commands, callbacks, and AI integration",
                "emoji": "🤖"
            },
            {
                "id": "web_app",
                "name": "Web Application",
                "description": "Full-stack web app with frontend and backend",
                "emoji": "🌐"
            },
            {
                "id": "api",
                "name": "REST API",
                "description": "Backend API service with endpoints and database",
                "emoji": "🔌"
            },
            {
                "id": "cli_tool",
                "name": "CLI Tool",
                "description": "Command-line application or utility",
                "emoji": "⌨️"
            },
            {
                "id": "data_pipeline",
                "name": "Data Pipeline",
                "description": "ETL, data processing, or ML pipeline",
                "emoji": "📊"
            },
            {
                "id": "mobile_app",
                "name": "Mobile App",
                "description": "iOS/Android app or React Native project",
                "emoji": "📱"
            },
            {
                "id": "library",
                "name": "Library/Package",
                "description": "Reusable library or npm/pip package",
                "emoji": "📦"
            },
            {
                "id": "custom",
                "name": "Custom Project",
                "description": "Start with minimal template and add your own tasks",
                "emoji": "✨"
            }
        ]

    def generate_prd(self, project_type: str, project_name: str = "My Project", validate: bool = True) -> Dict[str, Any]:
        """
        Generate a PRD template for the given project type.

        Args:
            project_type: Type of project (telegram_bot, web_app, etc.)
            project_name: Name of the project
            validate: Whether to validate tasks against protected resources

        Returns:
            Dictionary containing the complete PRD structure
        """
        # Base PRD structure
        prd = {
            "project": project_name,
            "version": "1.0",
            "updated": datetime.now().strftime("%Y-%m-%d"),
            "description": self._get_project_description(project_type),
            "tasks": [],
            "priority_order": []
        }

        # Add project-specific tasks
        tasks = self._get_tasks_for_type(project_type)

        # Validate tasks if rule awareness is available
        if validate and self.rule_awareness:
            validation_result = self.rule_awareness.validate_prd_tasks(tasks)
            if not validation_result['valid']:
                self.logger.warning(
                    f"Generated PRD contains {validation_result['tasks_with_protected_files']} "
                    f"tasks that touch protected files"
                )
                for warning in validation_result['warnings']:
                    self.logger.warning(warning)

        prd["tasks"] = tasks

        # Generate priority order
        prd["priority_order"] = self._generate_priority_order(tasks)

        return prd

    def _get_project_description(self, project_type: str) -> str:
        """Get description based on project type."""
        descriptions = {
            "telegram_bot": "A Telegram bot built with python-telegram-bot",
            "web_app": "A full-stack web application",
            "api": "A RESTful API service",
            "cli_tool": "A command-line tool",
            "data_pipeline": "A data processing pipeline",
            "mobile_app": "A mobile application",
            "library": "A reusable software library",
            "custom": "A custom software project"
        }
        return descriptions.get(project_type, "A software project")

    def _get_tasks_for_type(self, project_type: str) -> List[Dict[str, Any]]:
        """Get common tasks for the given project type."""

        if project_type == "telegram_bot":
            return self._telegram_bot_tasks()
        elif project_type == "web_app":
            return self._web_app_tasks()
        elif project_type == "api":
            return self._api_tasks()
        elif project_type == "cli_tool":
            return self._cli_tool_tasks()
        elif project_type == "data_pipeline":
            return self._data_pipeline_tasks()
        elif project_type == "mobile_app":
            return self._mobile_app_tasks()
        elif project_type == "library":
            return self._library_tasks()
        else:  # custom
            return self._custom_tasks()

    def _telegram_bot_tasks(self) -> List[Dict[str, Any]]:
        """Common tasks for Telegram bot projects."""
        return [
            {
                "id": "TB-001",
                "category": "Setup",
                "title": "Bot Initialization",
                "description": "Set up basic bot structure with python-telegram-bot",
                "acceptance_criteria": [
                    "Bot responds to /start command",
                    "Environment variables configured (.env)",
                    "Basic error handling in place",
                    "Bot token properly secured"
                ],
                "files_likely_modified": ["bot.py", ".env.example"],
                "passes": False
            },
            {
                "id": "TB-002",
                "category": "Core Features",
                "title": "Command Handlers",
                "description": "Implement essential bot commands",
                "acceptance_criteria": [
                    "/help command shows available commands",
                    "/settings command for user preferences",
                    "Commands have proper descriptions",
                    "Error messages are user-friendly"
                ],
                "files_likely_modified": ["bot.py", "handlers/"],
                "passes": False
            },
            {
                "id": "TB-003",
                "category": "User Experience",
                "title": "Interactive Menus",
                "description": "Add inline keyboards for better UX",
                "acceptance_criteria": [
                    "Inline keyboards for common actions",
                    "Callback query handlers implemented",
                    "Button states properly managed",
                    "Navigation is intuitive"
                ],
                "files_likely_modified": ["bot.py", "keyboards.py"],
                "passes": False
            },
            {
                "id": "TB-004",
                "category": "Data",
                "title": "User State Management",
                "description": "Track user sessions and preferences",
                "acceptance_criteria": [
                    "User data persists between sessions",
                    "State machine for conversation flow",
                    "Data stored securely",
                    "GDPR-compliant data handling"
                ],
                "files_likely_modified": ["bot.py", "database.py"],
                "passes": False
            },
            {
                "id": "TB-005",
                "category": "Testing",
                "title": "Unit Tests",
                "description": "Add test coverage for bot functionality",
                "acceptance_criteria": [
                    "Tests for all command handlers",
                    "Mock Telegram API calls",
                    "Test coverage >70%",
                    "CI/CD pipeline runs tests"
                ],
                "files_likely_modified": ["tests/"],
                "passes": False
            }
        ]

    def _web_app_tasks(self) -> List[Dict[str, Any]]:
        """Common tasks for web application projects."""
        return [
            {
                "id": "WA-001",
                "category": "Setup",
                "title": "Project Scaffolding",
                "description": "Set up frontend and backend structure",
                "acceptance_criteria": [
                    "Frontend framework configured (React/Vue/etc)",
                    "Backend framework set up (Express/Django/etc)",
                    "Build tools configured",
                    "Development server runs"
                ],
                "files_likely_modified": ["package.json", "requirements.txt"],
                "passes": False
            },
            {
                "id": "WA-002",
                "category": "Frontend",
                "title": "Landing Page",
                "description": "Create homepage with hero section",
                "acceptance_criteria": [
                    "Responsive design (mobile + desktop)",
                    "Hero section with CTA",
                    "Navigation bar implemented",
                    "Loading states handled"
                ],
                "files_likely_modified": ["src/pages/", "src/components/"],
                "passes": False
            },
            {
                "id": "WA-003",
                "category": "Backend",
                "title": "Database Setup",
                "description": "Configure database and ORM",
                "acceptance_criteria": [
                    "Database connection established",
                    "Initial schema/models created",
                    "Migrations set up",
                    "Seed data for development"
                ],
                "files_likely_modified": ["models/", "migrations/"],
                "passes": False
            },
            {
                "id": "WA-004",
                "category": "Authentication",
                "title": "User Auth",
                "description": "Implement user registration and login",
                "acceptance_criteria": [
                    "Registration form with validation",
                    "Login with JWT/sessions",
                    "Password hashing (bcrypt)",
                    "Protected routes"
                ],
                "files_likely_modified": ["auth/", "middleware/"],
                "passes": False
            },
            {
                "id": "WA-005",
                "category": "Deployment",
                "title": "Production Setup",
                "description": "Deploy to production environment",
                "acceptance_criteria": [
                    "Environment variables configured",
                    "SSL/HTTPS enabled",
                    "Database backups scheduled",
                    "Monitoring/logging in place"
                ],
                "files_likely_modified": ["docker-compose.yml", ".github/workflows/"],
                "passes": False
            }
        ]

    def _api_tasks(self) -> List[Dict[str, Any]]:
        """Common tasks for REST API projects."""
        return [
            {
                "id": "API-001",
                "category": "Setup",
                "title": "API Framework Setup",
                "description": "Initialize API framework and structure",
                "acceptance_criteria": [
                    "Framework installed (Express/FastAPI/etc)",
                    "Route structure defined",
                    "Middleware configured",
                    "Health check endpoint (/health)"
                ],
                "files_likely_modified": ["app.py", "routes/"],
                "passes": False
            },
            {
                "id": "API-002",
                "category": "Endpoints",
                "title": "CRUD Endpoints",
                "description": "Implement basic CRUD operations",
                "acceptance_criteria": [
                    "GET /items - List all items",
                    "POST /items - Create item",
                    "PUT /items/:id - Update item",
                    "DELETE /items/:id - Delete item",
                    "Proper HTTP status codes"
                ],
                "files_likely_modified": ["routes/items.py"],
                "passes": False
            },
            {
                "id": "API-003",
                "category": "Validation",
                "title": "Input Validation",
                "description": "Validate and sanitize all inputs",
                "acceptance_criteria": [
                    "Request body validation",
                    "Query parameter validation",
                    "Type checking",
                    "Error messages are clear"
                ],
                "files_likely_modified": ["validators/", "schemas/"],
                "passes": False
            },
            {
                "id": "API-004",
                "category": "Security",
                "title": "API Authentication",
                "description": "Secure endpoints with auth",
                "acceptance_criteria": [
                    "API key or JWT authentication",
                    "Rate limiting implemented",
                    "CORS configured",
                    "Security headers set"
                ],
                "files_likely_modified": ["middleware/auth.py"],
                "passes": False
            },
            {
                "id": "API-005",
                "category": "Documentation",
                "title": "API Documentation",
                "description": "Generate OpenAPI/Swagger docs",
                "acceptance_criteria": [
                    "All endpoints documented",
                    "Request/response schemas defined",
                    "Example requests included",
                    "Swagger UI accessible"
                ],
                "files_likely_modified": ["docs/", "swagger.json"],
                "passes": False
            }
        ]

    def _cli_tool_tasks(self) -> List[Dict[str, Any]]:
        """Common tasks for CLI tool projects."""
        return [
            {
                "id": "CLI-001",
                "category": "Setup",
                "title": "CLI Framework",
                "description": "Set up argument parsing and commands",
                "acceptance_criteria": [
                    "Argument parser configured (argparse/click)",
                    "Subcommands work",
                    "--help flag shows usage",
                    "--version flag works"
                ],
                "files_likely_modified": ["cli.py"],
                "passes": False
            },
            {
                "id": "CLI-002",
                "category": "Core Features",
                "title": "Main Commands",
                "description": "Implement primary CLI commands",
                "acceptance_criteria": [
                    "Commands perform intended actions",
                    "Progress indicators for long operations",
                    "Colorized output for readability",
                    "Exit codes are correct"
                ],
                "files_likely_modified": ["commands/"],
                "passes": False
            },
            {
                "id": "CLI-003",
                "category": "Configuration",
                "title": "Config File Support",
                "description": "Allow configuration via file",
                "acceptance_criteria": [
                    "Config file format chosen (YAML/JSON/TOML)",
                    "Default config created if missing",
                    "CLI args override config file",
                    "Config validation"
                ],
                "files_likely_modified": ["config.py"],
                "passes": False
            },
            {
                "id": "CLI-004",
                "category": "User Experience",
                "title": "Interactive Mode",
                "description": "Add interactive prompts for complex inputs",
                "acceptance_criteria": [
                    "Prompts for missing required args",
                    "Confirmation for destructive actions",
                    "Tab completion support",
                    "Graceful Ctrl+C handling"
                ],
                "files_likely_modified": ["interactive.py"],
                "passes": False
            },
            {
                "id": "CLI-005",
                "category": "Distribution",
                "title": "Package for Distribution",
                "description": "Make tool installable via package manager",
                "acceptance_criteria": [
                    "setup.py or pyproject.toml configured",
                    "Entry point defined",
                    "README with installation instructions",
                    "Installable with pip/npm"
                ],
                "files_likely_modified": ["setup.py", "README.md"],
                "passes": False
            }
        ]

    def _data_pipeline_tasks(self) -> List[Dict[str, Any]]:
        """Common tasks for data pipeline projects."""
        return [
            {
                "id": "DP-001",
                "category": "Setup",
                "title": "Pipeline Framework",
                "description": "Set up data processing framework",
                "acceptance_criteria": [
                    "Framework chosen (Airflow/Prefect/Luigi)",
                    "Task orchestration configured",
                    "Logging set up",
                    "Error handling in place"
                ],
                "files_likely_modified": ["pipeline.py", "dags/"],
                "passes": False
            },
            {
                "id": "DP-002",
                "category": "Extraction",
                "title": "Data Extraction",
                "description": "Extract data from sources",
                "acceptance_criteria": [
                    "Connect to data sources",
                    "Handle API rate limits",
                    "Incremental extraction",
                    "Data validation on extraction"
                ],
                "files_likely_modified": ["extractors/"],
                "passes": False
            },
            {
                "id": "DP-003",
                "category": "Transformation",
                "title": "Data Transformation",
                "description": "Clean and transform data",
                "acceptance_criteria": [
                    "Data cleaning logic implemented",
                    "Type conversions handled",
                    "Null values processed",
                    "Data quality checks"
                ],
                "files_likely_modified": ["transformers/"],
                "passes": False
            },
            {
                "id": "DP-004",
                "category": "Loading",
                "title": "Data Loading",
                "description": "Load data to destination",
                "acceptance_criteria": [
                    "Database/warehouse connection",
                    "Batch insert/upsert logic",
                    "Rollback on failure",
                    "Load performance optimized"
                ],
                "files_likely_modified": ["loaders/"],
                "passes": False
            },
            {
                "id": "DP-005",
                "category": "Monitoring",
                "title": "Pipeline Monitoring",
                "description": "Monitor pipeline health and performance",
                "acceptance_criteria": [
                    "Metrics collected (runtime, rows processed)",
                    "Alerts on failures",
                    "Dashboard for pipeline status",
                    "Data quality metrics tracked"
                ],
                "files_likely_modified": ["monitoring/"],
                "passes": False
            }
        ]

    def _mobile_app_tasks(self) -> List[Dict[str, Any]]:
        """Common tasks for mobile app projects."""
        return [
            {
                "id": "MA-001",
                "category": "Setup",
                "title": "Mobile App Initialization",
                "description": "Set up mobile development environment",
                "acceptance_criteria": [
                    "React Native/Flutter/Swift project created",
                    "Development build runs on simulator",
                    "Hot reload working",
                    "Dependencies installed"
                ],
                "files_likely_modified": ["App.js", "package.json"],
                "passes": False
            },
            {
                "id": "MA-002",
                "category": "UI",
                "title": "Home Screen",
                "description": "Create main app screen",
                "acceptance_criteria": [
                    "Responsive layout",
                    "Navigation working",
                    "App icon and splash screen",
                    "Consistent styling"
                ],
                "files_likely_modified": ["screens/Home.js", "navigation/"],
                "passes": False
            },
            {
                "id": "MA-003",
                "category": "Features",
                "title": "Core Functionality",
                "description": "Implement main app features",
                "acceptance_criteria": [
                    "Primary user flows work",
                    "State management in place",
                    "Offline support",
                    "Loading states handled"
                ],
                "files_likely_modified": ["components/", "store/"],
                "passes": False
            },
            {
                "id": "MA-004",
                "category": "Integration",
                "title": "Backend Integration",
                "description": "Connect to backend API",
                "acceptance_criteria": [
                    "API client configured",
                    "Authentication flow",
                    "Error handling",
                    "Network status checks"
                ],
                "files_likely_modified": ["api/", "services/"],
                "passes": False
            },
            {
                "id": "MA-005",
                "category": "Testing",
                "title": "Mobile Testing",
                "description": "Test on multiple devices",
                "acceptance_criteria": [
                    "iOS and Android tested",
                    "Different screen sizes checked",
                    "Unit tests written",
                    "E2E tests for critical flows"
                ],
                "files_likely_modified": ["__tests__/"],
                "passes": False
            }
        ]

    def _library_tasks(self) -> List[Dict[str, Any]]:
        """Common tasks for library/package projects."""
        return [
            {
                "id": "LIB-001",
                "category": "Setup",
                "title": "Library Structure",
                "description": "Set up library project structure",
                "acceptance_criteria": [
                    "Package structure created",
                    "Build tools configured",
                    "TypeScript/type hints set up",
                    "Entry point defined"
                ],
                "files_likely_modified": ["src/", "package.json"],
                "passes": False
            },
            {
                "id": "LIB-002",
                "category": "Core API",
                "title": "Public API",
                "description": "Define library's public interface",
                "acceptance_criteria": [
                    "Core functions/classes implemented",
                    "Clear API surface",
                    "Backward compatibility considered",
                    "Type definitions included"
                ],
                "files_likely_modified": ["src/index.ts", "types/"],
                "passes": False
            },
            {
                "id": "LIB-003",
                "category": "Documentation",
                "title": "API Documentation",
                "description": "Document all public APIs",
                "acceptance_criteria": [
                    "JSDoc/docstrings for all public APIs",
                    "Usage examples included",
                    "API reference generated",
                    "Getting started guide"
                ],
                "files_likely_modified": ["docs/", "README.md"],
                "passes": False
            },
            {
                "id": "LIB-004",
                "category": "Testing",
                "title": "Comprehensive Tests",
                "description": "Ensure library works correctly",
                "acceptance_criteria": [
                    "Unit tests for all functions",
                    "Integration tests",
                    "Edge cases covered",
                    "Test coverage >90%"
                ],
                "files_likely_modified": ["tests/"],
                "passes": False
            },
            {
                "id": "LIB-005",
                "category": "Publishing",
                "title": "Package Publishing",
                "description": "Publish to package registry",
                "acceptance_criteria": [
                    "Version number set",
                    "Package.json/setup.py complete",
                    "CI/CD for releases",
                    "Published to npm/PyPI"
                ],
                "files_likely_modified": [".github/workflows/", "package.json"],
                "passes": False
            }
        ]

    def _custom_tasks(self) -> List[Dict[str, Any]]:
        """Minimal tasks for custom projects."""
        return [
            {
                "id": "CUSTOM-001",
                "category": "Setup",
                "title": "Project Setup",
                "description": "Initialize project structure",
                "acceptance_criteria": [
                    "Repository created",
                    "Dependencies installed",
                    "Basic structure in place",
                    "README created"
                ],
                "files_likely_modified": ["README.md"],
                "passes": False
            },
            {
                "id": "CUSTOM-002",
                "category": "Core",
                "title": "Core Functionality",
                "description": "Implement main features",
                "acceptance_criteria": [
                    "Primary features working",
                    "Error handling in place",
                    "Code is documented",
                    "Basic tests written"
                ],
                "files_likely_modified": ["src/"],
                "passes": False
            },
            {
                "id": "CUSTOM-003",
                "category": "Quality",
                "title": "Testing and Documentation",
                "description": "Ensure code quality",
                "acceptance_criteria": [
                    "Test coverage adequate",
                    "Documentation complete",
                    "Code reviewed",
                    "Ready for use"
                ],
                "files_likely_modified": ["tests/", "docs/"],
                "passes": False
            }
        ]

    def _generate_priority_order(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        Generate priority order from tasks.
        Groups tasks by category and orders them logically.
        """
        # Group tasks by category
        categories = {}
        for task in tasks:
            category = task["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(task)

        # Build priority order
        priority_order = []

        # Define category priority (setup first, deployment last)
        category_priority = ["Setup", "Core", "Features", "Testing", "Documentation", "Deployment"]

        # Process categories in order
        for cat_name in category_priority:
            if cat_name in categories:
                priority_order.append(f"--- {cat_name.upper()} ---")
                for task in categories[cat_name]:
                    priority_order.append(f"{task['id']} - {task['title']}")
                del categories[cat_name]

        # Add remaining categories
        for cat_name, cat_tasks in categories.items():
            priority_order.append(f"--- {cat_name.upper()} ---")
            for task in cat_tasks:
                priority_order.append(f"{task['id']} - {task['title']}")

        return priority_order

    def save_prd(self, prd: Dict[str, Any], output_path: str) -> bool:
        """
        Save PRD to JSON file.

        Args:
            prd: PRD dictionary
            output_path: Path to save the file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(prd, f, indent=2)
            self.logger.info(f"PRD saved to {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save PRD: {e}")
            return False

    def get_prd_explanation(self) -> str:
        """Get explanation of PRD structure for users."""
        return """
📋 **What's a PRD?**

A PRD (Product Requirements Document) is your project's task list. It tells Ralph what to build!

**Structure:**
• **Tasks**: Features to implement, with acceptance criteria
• **Categories**: Tasks grouped by theme (Setup, Features, Testing, etc.)
• **Priority Order**: The sequence Ralph will work on tasks
• **Status**: Each task tracks whether it's done (`passes: true/false`)

**How Ralph uses it:**
1. Reads the PRD
2. Finds the first task with `passes: false`
3. Implements it
4. Marks it as `passes: true`
5. Repeats until all tasks pass

You can edit the PRD anytime to add, remove, or reorder tasks!
"""

    def validate_task_files(self, files: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if a list of files contains any protected resources.

        Args:
            files: List of file paths to check

        Returns:
            Tuple of (all_safe, list of protected files with warnings)
        """
        if not self.rule_awareness:
            return True, []

        warnings = []
        for file_path in files:
            is_protected, resource = self.rule_awareness.is_protected(file_path)
            if is_protected:
                warnings.append(
                    f"⚠️  PROTECTED: {file_path}\n"
                    f"   Reason: {resource.reason}\n"
                    f"   Change Process: {resource.change_process}"
                )

        return len(warnings) == 0, warnings

    def can_auto_modify_file(self, file_path: str) -> bool:
        """
        Check if PRD generators can auto-create tasks to modify this file.

        Args:
            file_path: Path to check

        Returns:
            True if safe for auto-generation, False if requires human review
        """
        if not self.rule_awareness:
            return True  # If no rule awareness, allow everything

        return self.rule_awareness.can_auto_generate_task(file_path)

    def get_protected_files_report(self) -> str:
        """
        Get a report of all protected files.

        Returns:
            Human-readable string listing protected resources
        """
        if not self.rule_awareness:
            return "Rule awareness system not available."

        return self.rule_awareness.get_protection_report()


# Singleton instance
_prd_generator_instance = None


def get_prd_generator() -> PRDGenerator:
    """Get singleton PRD generator instance."""
    global _prd_generator_instance
    if _prd_generator_instance is None:
        _prd_generator_instance = PRDGenerator()
    return _prd_generator_instance


if __name__ == "__main__":
    # Example usage
    generator = get_prd_generator()

    # Show available project types
    print("Available project types:")
    for pt in generator.get_project_types():
        print(f"  {pt['emoji']} {pt['name']}: {pt['description']}")

    # Generate example PRD
    prd = generator.generate_prd("telegram_bot", "My Awesome Bot")

    # Save it
    generator.save_prd(prd, "example_prd.json")
    print(f"\nGenerated PRD with {len(prd['tasks'])} tasks")
    print(f"Priority order: {len(prd['priority_order'])} items")
