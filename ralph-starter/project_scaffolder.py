#!/usr/bin/env python3
"""
Project Scaffolder - OB-029

Creates standard project folder structure for Ralph Mode projects.
Guides users through setting up their workspace in a friendly way.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class ProjectScaffolder:
    """Handles creation of project folder structure."""

    # Standard folder structure
    STANDARD_FOLDERS = {
        'scripts/ralph': 'Ralph automation scripts and PRD files',
        'config': 'Configuration files for your project',
        'tests': 'Test files and test data',
        'src': 'Source code for your application',
        'docs': 'Documentation and guides',
    }

    # Standard .gitignore entries
    GITIGNORE_ENTRIES = [
        '# Python',
        '__pycache__/',
        '*.py[cod]',
        '*$py.class',
        '*.so',
        '.Python',
        'build/',
        'develop-eggs/',
        'dist/',
        'downloads/',
        'eggs/',
        '.eggs/',
        'lib/',
        'lib64/',
        'parts/',
        'sdist/',
        'var/',
        'wheels/',
        '*.egg-info/',
        '.installed.cfg',
        '*.egg',
        '',
        '# Virtual Environment',
        'venv/',
        'env/',
        'ENV/',
        '',
        '# IDEs',
        '.vscode/',
        '.idea/',
        '*.swp',
        '*.swo',
        '*~',
        '.DS_Store',
        '',
        '# Secrets - NEVER COMMIT THESE!',
        '.env',
        '.env.local',
        'secrets/',
        'credentials.json',
        '*.pem',
        '*.key',
        '',
        '# Logs',
        '*.log',
        'logs/',
        '',
        '# Test coverage',
        '.coverage',
        'htmlcov/',
        '',
        '# Ralph specific',
        'scripts/ralph/progress.txt',
        'deploy_manager.log',
    ]

    def __init__(self):
        """Initialize the scaffolder."""
        self.logger = logging.getLogger(__name__)

    def create_folder_structure(
        self,
        base_path: str,
        custom_folders: Optional[List[str]] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Create standard project folder structure.

        Args:
            base_path: Root directory for the project
            custom_folders: Additional custom folders to create

        Returns:
            Tuple of (success, created_folders, errors)
        """
        created = []
        errors = []
        base = Path(base_path)

        # Create standard folders
        for folder, purpose in self.STANDARD_FOLDERS.items():
            folder_path = base / folder
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                created.append(f"{folder} ({purpose})")
                self.logger.info(f"Created folder: {folder}")
            except Exception as e:
                error_msg = f"Failed to create {folder}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        # Create custom folders if specified
        if custom_folders:
            for folder in custom_folders:
                folder_path = base / folder
                try:
                    folder_path.mkdir(parents=True, exist_ok=True)
                    created.append(f"{folder} (custom)")
                    self.logger.info(f"Created custom folder: {folder}")
                except Exception as e:
                    error_msg = f"Failed to create {folder}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

        success = len(errors) == 0
        return success, created, errors

    def create_gitignore(self, base_path: str) -> Tuple[bool, str]:
        """
        Create or update .gitignore file.

        Args:
            base_path: Root directory for the project

        Returns:
            Tuple of (success, message)
        """
        gitignore_path = Path(base_path) / '.gitignore'

        try:
            # Check if .gitignore already exists
            if gitignore_path.exists():
                with open(gitignore_path, 'r') as f:
                    existing_content = f.read()

                # Only add missing entries
                missing_entries = []
                for entry in self.GITIGNORE_ENTRIES:
                    if entry and entry not in existing_content:
                        missing_entries.append(entry)

                if missing_entries:
                    with open(gitignore_path, 'a') as f:
                        f.write('\n# Added by Ralph Mode\n')
                        f.write('\n'.join(missing_entries))
                        f.write('\n')
                    message = f"Updated .gitignore with {len(missing_entries)} new entries"
                else:
                    message = ".gitignore already exists and is up to date"
            else:
                # Create new .gitignore
                with open(gitignore_path, 'w') as f:
                    f.write('\n'.join(self.GITIGNORE_ENTRIES))
                    f.write('\n')
                message = "Created .gitignore with standard ignores"

            self.logger.info(message)
            return True, message

        except Exception as e:
            error_msg = f"Failed to create/update .gitignore: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def explain_folder_structure(self) -> Dict[str, str]:
        """
        Return explanations for each folder.

        Returns:
            Dictionary mapping folder names to their purposes
        """
        return self.STANDARD_FOLDERS.copy()

    def get_ralph_explanation(self) -> str:
        """
        Get Ralph's friendly explanation of the folder structure.

        Returns:
            Ralph's narration about the folders
        """
        explanations = [
            "Hi diddly ho! I'm gonna make some folders for your project!",
            "",
            "📁 scripts/ralph/ - This is where I keep my special brain stuff! PRD files and automation magic!",
            "",
            "📁 config/ - Configuration files go here. Like settings and stuff that control how things work!",
            "",
            "📁 tests/ - This is where we put test files. Testing is important! (I think... what's testing?)",
            "",
            "📁 src/ - Your actual code lives here! The important stuff that makes your app work!",
            "",
            "📁 docs/ - Documentation! I'm not great at spelling but docs are super helpful!",
            "",
            "📄 .gitignore - This tells git what NOT to push. Like secrets! We don't want bad guys getting your passwords!",
        ]
        return '\n'.join(explanations)

    def scaffold_project(
        self,
        base_path: str,
        create_gitignore: bool = True,
        custom_folders: Optional[List[str]] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        Complete project scaffolding - folders + .gitignore.

        Args:
            base_path: Root directory for the project
            create_gitignore: Whether to create/update .gitignore
            custom_folders: Additional custom folders to create

        Returns:
            Tuple of (success, summary_message, created_items)
        """
        all_created = []

        # Create folders
        folder_success, created_folders, folder_errors = self.create_folder_structure(
            base_path, custom_folders
        )
        all_created.extend(created_folders)

        # Create .gitignore if requested
        gitignore_success = True
        gitignore_msg = ""
        if create_gitignore:
            gitignore_success, gitignore_msg = self.create_gitignore(base_path)
            if gitignore_success:
                all_created.append(f".gitignore ({gitignore_msg})")

        # Generate summary
        overall_success = folder_success and gitignore_success

        if overall_success:
            summary = f"✅ Project scaffolding complete! Created {len(all_created)} items."
        else:
            errors = folder_errors
            if not gitignore_success:
                errors.append(gitignore_msg)
            summary = f"⚠️ Scaffolding completed with {len(errors)} errors: {', '.join(errors)}"

        return overall_success, summary, all_created


def get_project_scaffolder() -> ProjectScaffolder:
    """
    Factory function to get ProjectScaffolder instance.

    Returns:
        ProjectScaffolder instance
    """
    return ProjectScaffolder()


# Module-level instance for convenience
_scaffolder_instance = None


def scaffold_project(
    base_path: str,
    create_gitignore: bool = True,
    custom_folders: Optional[List[str]] = None
) -> Tuple[bool, str, List[str]]:
    """
    Convenience function for project scaffolding.

    Args:
        base_path: Root directory for the project
        create_gitignore: Whether to create/update .gitignore
        custom_folders: Additional custom folders to create

    Returns:
        Tuple of (success, summary_message, created_items)
    """
    global _scaffolder_instance
    if _scaffolder_instance is None:
        _scaffolder_instance = ProjectScaffolder()

    return _scaffolder_instance.scaffold_project(
        base_path, create_gitignore, custom_folders
    )
