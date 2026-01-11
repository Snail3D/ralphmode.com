#!/usr/bin/env python3
"""
PRD Manager - Rule Awareness System

Ensures PRD generators know what they can and CANNOT touch.
Protects foundational files from casual modification.
"""

import os
import logging
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path


class ProtectedResource:
    """Represents a protected file or directory that cannot be casually modified."""

    def __init__(self, path: str, reason: str, change_process: str):
        """
        Initialize a protected resource.

        Args:
            path: Relative path from project root (e.g., "FOUNDATION/HARDCORE_RULES.md")
            reason: Why this resource is protected
            change_process: What process must be followed to change it
        """
        self.path = path
        self.reason = reason
        self.change_process = change_process

    def matches(self, file_path: str) -> bool:
        """Check if a file path matches this protected resource."""
        # Normalize paths for comparison
        protected = Path(self.path)
        target = Path(file_path)

        # Check for exact match
        if protected == target:
            return True

        # Check if file is within protected directory
        try:
            target.relative_to(protected)
            return True
        except ValueError:
            return False


class PRDRuleAwareness:
    """
    Manages awareness of what PRD generators can and cannot touch.

    This class defines the boundaries for automated code generation and PRD creation.
    Some files are FOUNDATIONAL and require human deliberation before changes.
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize rule awareness system.

        Args:
            project_root: Root directory of the project. If None, uses current directory.
        """
        self.project_root = project_root or os.getcwd()
        self.logger = logging.getLogger(__name__)

        # Initialize protected resources
        self.protected_resources = self._define_protected_resources()

    def _define_protected_resources(self) -> List[ProtectedResource]:
        """
        Define all protected resources in the project.

        These are files/directories that require special care before modification.
        """
        return [
            # FOUNDATION documents - Core identity and values
            ProtectedResource(
                path="FOUNDATION/HARDCORE_RULES.md",
                reason="Defines the 10 foundational rules that cannot change lightly",
                change_process="Must follow HARDCORE_RULES.md change protocol (git history review, impact analysis, deliberation with Mr. Worms)"
            ),
            ProtectedResource(
                path="FOUNDATION/WHO_WE_ARE.md",
                reason="Defines character identities and personalities",
                change_process="Requires Mr. Worms approval and review of how it affects character behavior"
            ),
            ProtectedResource(
                path="FOUNDATION/WHERE_WE_ARE_GOING.md",
                reason="Defines mission and strategic direction",
                change_process="Requires Mr. Worms approval and alignment check with current work"
            ),
            ProtectedResource(
                path="FOUNDATION/WHO_WE_WANT_TO_BE.md",
                reason="Defines values and aspirational character",
                change_process="Requires Mr. Worms approval and impact analysis"
            ),
            ProtectedResource(
                path="FOUNDATION/README_PROTOCOL.md",
                reason="Defines how to maintain README properly",
                change_process="Can be updated if protocol improvements are clear, but requires review"
            ),
            ProtectedResource(
                path="FOUNDATION/",
                reason="Contains all foundational documents",
                change_process="No new files should be added without deliberation. Existing files require their specific change processes."
            ),

            # Core system files that define Ralph's behavior
            ProtectedResource(
                path=".env",
                reason="Contains secrets and API keys",
                change_process="NEVER commit to git. Only modify locally with proper key rotation."
            ),
            ProtectedResource(
                path="scripts/ralph/prompt.md",
                reason="Core instructions for Ralph agent",
                change_process="Changes affect Ralph's behavior across ALL projects. Requires testing and Mr. Worms approval."
            ),

            # Git and version control
            ProtectedResource(
                path=".git/",
                reason="Version control history",
                change_process="NEVER modify .git directory directly. Use git commands only."
            ),
            ProtectedResource(
                path=".gitignore",
                reason="Controls what gets committed to version control",
                change_process="Can add entries, but removal requires review (might expose secrets)"
            ),
        ]

    def is_protected(self, file_path: str) -> Tuple[bool, Optional[ProtectedResource]]:
        """
        Check if a file path is protected.

        Args:
            file_path: Path to check (relative or absolute)

        Returns:
            Tuple of (is_protected, protected_resource or None)
        """
        # Convert to relative path if absolute
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(self.project_root)
            except ValueError:
                # Path is outside project root
                return False, None

        # Check against all protected resources
        for resource in self.protected_resources:
            if resource.matches(str(path)):
                return True, resource

        return False, None

    def validate_prd_task(self, task: Dict) -> Tuple[bool, List[str]]:
        """
        Validate that a PRD task doesn't violate protection rules.

        Args:
            task: PRD task dictionary with 'files_likely_modified' field

        Returns:
            Tuple of (is_valid, list of warning messages)
        """
        warnings = []
        files_to_check = task.get('files_likely_modified', [])

        for file_path in files_to_check:
            is_protected, resource = self.is_protected(file_path)

            if is_protected:
                warnings.append(
                    f"⚠️  PROTECTED FILE: {file_path}\n"
                    f"   Reason: {resource.reason}\n"
                    f"   Change Process: {resource.change_process}\n"
                    f"   Task: {task.get('id', 'UNKNOWN')} - {task.get('title', 'No title')}"
                )

        return len(warnings) == 0, warnings

    def validate_prd_tasks(self, tasks: List[Dict]) -> Dict[str, any]:
        """
        Validate all tasks in a PRD.

        Args:
            tasks: List of PRD task dictionaries

        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'total_tasks': int,
                'tasks_with_protected_files': int,
                'warnings': List[str],
                'protected_tasks': List[str]  # Task IDs that touch protected files
            }
        """
        all_warnings = []
        protected_task_ids = []

        for task in tasks:
            is_valid, warnings = self.validate_prd_task(task)
            if not is_valid:
                all_warnings.extend(warnings)
                protected_task_ids.append(task.get('id', 'UNKNOWN'))

        return {
            'valid': len(all_warnings) == 0,
            'total_tasks': len(tasks),
            'tasks_with_protected_files': len(protected_task_ids),
            'warnings': all_warnings,
            'protected_tasks': protected_task_ids
        }

    def can_auto_generate_task(self, file_path: str) -> bool:
        """
        Check if a PRD generator can automatically create tasks for a file.

        Args:
            file_path: Path to the file

        Returns:
            True if auto-generation is allowed, False if human review required
        """
        is_protected, _ = self.is_protected(file_path)
        return not is_protected

    def get_safe_task_template(self) -> Dict:
        """
        Get a task template that PRD generators should use.

        Ensures tasks have the right structure and include file awareness.
        """
        return {
            "id": "EXAMPLE-001",
            "category": "Example Category",
            "title": "Example Task Title",
            "description": "Detailed description of what needs to be done",
            "acceptance_criteria": [
                "Specific, measurable criterion 1",
                "Specific, measurable criterion 2",
                "Specific, measurable criterion 3"
            ],
            "files_likely_modified": [
                "path/to/file.py"  # PRD generators MUST check these against protected resources
            ],
            "passes": False
        }

    def filter_protected_tasks(self, tasks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Separate tasks into safe and protected lists.

        Args:
            tasks: List of PRD tasks

        Returns:
            Tuple of (safe_tasks, protected_tasks)
        """
        safe_tasks = []
        protected_tasks = []

        for task in tasks:
            is_valid, _ = self.validate_prd_task(task)
            if is_valid:
                safe_tasks.append(task)
            else:
                protected_tasks.append(task)

        return safe_tasks, protected_tasks

    def get_protection_report(self) -> str:
        """
        Generate a human-readable report of all protected resources.

        Returns:
            Formatted string listing all protected resources and their rules
        """
        report = ["# PROTECTED RESOURCES - DO NOT TOUCH LIGHTLY\n"]
        report.append("These files require special change processes:\n")

        for resource in self.protected_resources:
            report.append(f"\n## {resource.path}")
            report.append(f"**Reason**: {resource.reason}")
            report.append(f"**Change Process**: {resource.change_process}\n")

        return "\n".join(report)


# Singleton instance
_prd_rule_awareness_instance = None


def get_prd_rule_awareness(project_root: Optional[str] = None) -> PRDRuleAwareness:
    """Get singleton PRD rule awareness instance."""
    global _prd_rule_awareness_instance
    if _prd_rule_awareness_instance is None:
        _prd_rule_awareness_instance = PRDRuleAwareness(project_root)
    return _prd_rule_awareness_instance


if __name__ == "__main__":
    # Example usage and testing
    import json

    awareness = get_prd_rule_awareness()

    # Print protection report
    print(awareness.get_protection_report())
    print("\n" + "="*80 + "\n")

    # Test some paths
    test_paths = [
        "FOUNDATION/HARDCORE_RULES.md",
        "FOUNDATION/WHO_WE_ARE.md",
        "ralph_bot.py",
        "scripts/ralph/prompt.md",
        ".env",
        "some_random_file.py"
    ]

    print("TESTING FILE PROTECTION:\n")
    for path in test_paths:
        is_protected, resource = awareness.is_protected(path)
        if is_protected:
            print(f"❌ PROTECTED: {path}")
            print(f"   Reason: {resource.reason}")
        else:
            print(f"✅ SAFE: {path}")

    print("\n" + "="*80 + "\n")

    # Test task validation
    test_task = {
        "id": "TEST-001",
        "category": "Test",
        "title": "Modify Hardcore Rules",
        "description": "Update the hardcore rules",
        "files_likely_modified": ["FOUNDATION/HARDCORE_RULES.md"],
        "passes": False
    }

    print("TESTING TASK VALIDATION:\n")
    is_valid, warnings = awareness.validate_prd_task(test_task)

    if is_valid:
        print("✅ Task is safe to auto-generate")
    else:
        print("❌ Task requires human review:")
        for warning in warnings:
            print(warning)
